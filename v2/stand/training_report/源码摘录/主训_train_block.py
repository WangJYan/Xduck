"""One isolated PPO block. Complete checkpoint resume, never historical weights."""
from pathlib import Path
import argparse,hashlib,json,sys,time
import numpy as np
import torch
from omegaconf import OmegaConf

B=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--index',type=int,required=True);ap.add_argument('--resume',type=Path);ap.add_argument('--smoke',action='store_true');ap.add_argument('--num-envs',type=int);ap.add_argument('--updates',type=int);ap.add_argument('--tag');a=ap.parse_args()
blocks=json.loads((B/'execution_blocks.json').read_text());block=blocks[a.index];start=int(block['start']);end=int(block['end']);owner=Path(block['owner'])
sys.path[:0]=[str(owner/'project/src'),str(owner/'project/scripts'),str(owner)]
import train_rsl_rl as E
from unilab.training.rsl_rl import RslRlVecEnvWrapper,attach_checkpoint_progress
E.ensure_registries()
torch.set_num_threads(2);seed=int(block['seed_numpy_torch']);np.random.seed(seed);torch.manual_seed(seed)
c=OmegaConf.load(block['config_path']);n=a.num_envs or (64 if a.smoke else int(block['envs']))
updates=a.updates or (5 if a.smoke else int(block['updates']))
run=B/'runs'/(a.tag or (f'smoke_{end:04d}' if a.smoke else f'block_{end:04d}'));run.mkdir(exist_ok=True)
c.algo.num_envs=n;c.algo.max_iterations=updates;c.training.log_dir=str(run)
if not a.smoke:
    if start==0:assert a.resume is None,'new model must start from random initialization'
    else:
        assert a.resume and a.resume.resolve().is_relative_to((B/'runs').resolve()),'only this branch checkpoints may initialize a block'
        assert a.resume.is_file()
        meta=json.loads(a.resume.with_name('completion.json').read_text())
        assert meta['end']==start and not meta['smoke'],(meta['end'],start)
OmegaConf.save(c,run/'CONFIG.yaml')
e=E.create_env(c,num_envs=n,env_cfg_override=E.build_ppo_env_cfg_override(c))
try:
    wrapper=RslRlVecEnvWrapper(e,device='cuda:0')
    assert e.state.obs['obs'].shape==(n,61) and e.state.obs['critic'].shape==(n,76)
    assert np.max(abs(e.default_angles-np.array(json.loads((B/'model_contract.json').read_text())['home_ctrl'])))<1e-7
    assert abs(e.cfg.goal_height_m-.322972)<1e-9
    tc=E.normalize_ppo_train_cfg(OmegaConf.to_container(c.algo,resolve=True));E.apply_ppo_runtime_flags(tc,c,training_enabled=True)
    runner=E.OnPolicyRunner(wrapper,tc,log_dir=str(run),device='cuda:0')
    if a.resume:
        runner.load(str(a.resume),map_location='cuda:0')
        assert len(runner.alg.optimizer.state)>0
        loaded=torch.load(a.resume,map_location='cpu',weights_only=True)
        for model,key in [(runner.alg.actor,'actor_state_dict'),(runner.alg.critic,'critic_state_dict')]:
            assert all(torch.equal(value.detach().cpu(),loaded[key][name]) for name,value in model.state_dict().items())
    else:
        torch.save(dict(actor_state_dict=runner.alg.actor.state_dict(),critic_state_dict=runner.alg.critic.state_dict(),started_from_scratch=True),run/'initial.pt')
    if start>=2200:
        # Commands have already been trained at full range; freeze their statistics now.
        for model in [runner.alg.actor,runner.alg.critic]:
            model.obs_normalizer.eval()
            model.update_normalization=lambda *_args,**_kwargs:None
    if start>=1300:
        runner.alg.learning_rate=float(c.algo.algorithm.learning_rate);runner.alg.schedule='fixed'
        for group in runner.alg.optimizer.param_groups:group['lr']=runner.alg.learning_rate
    if start>=300:
        if start<1300:lo,hi,other=.6,float('inf'),float('inf')
        elif start<1800:
            lo,hi,other=[(.30,.45,.50),(.25,.35,.45),(.20,.30,.40),(.18,.28,.35),(.18,.25,.35)][(start-1300)//100]
        elif start<2200:lo,hi,other=[(.20,.30,.35),(.20,.30,.35),(.18,.28,.35),(.18,.25,.35)][(start-1800)//100]
        else:lo,hi,other=.18,.25,.35
        def clamp_std(*_args):
            with torch.no_grad():
                lp=runner.alg.actor.distribution.log_std_param
                ids=torch.tensor([0,1,2,3,4,9,10,11,12,13],device=lp.device)
                lp.clamp_(min=np.log(.12),max=np.log(other))
                lp[ids]=lp[ids].clamp(min=np.log(lo),max=np.log(hi))
        clamp_std();runner.alg.optimizer.register_step_post_hook(clamp_std)
    attach_checkpoint_progress(e,runner)
    initial={k:v.detach().clone() for k,v in runner.alg.actor.state_dict().items() if k.startswith('mlp.')}
    # Capture finite state/reward invariants at the environment boundary.
    step=e.step;steps=0
    def checked_step(actions):
        global steps
        s=step(actions);steps+=1
        if not np.isfinite(s.reward).all() or not all(np.isfinite(v).all() for v in s.obs.values()):raise RuntimeError('nonfinite PPO rollout')
        if start>=300:
            assert e.head_nonquiet_violations==0 and e.head_alignment_errors==0
        return s
    e.step=checked_step
    begun=time.time();runner.learn(num_learning_iterations=updates,init_at_random_ep_len=False)
    ck=run/'final.pt';runner.save(str(ck))
    from inference_policy import FrozenPolicy
    frozen=FrozenPolicy(ck,B/'model_contract.json',solver4=start>=2200)
    obs=wrapper.get_observations()
    with torch.inference_mode():
        trained=runner.alg.actor(obs,stochastic_output=False).cpu().numpy()
        exported=frozen(torch.as_tensor(e.state.obs['obs'],dtype=torch.float32)).numpy()
    target_error=float(np.max(abs(np.tanh(trained)-np.tanh(exported))*e._increments))
    assert target_error<2e-6,target_error
    change=max(float((v-initial[k]).abs().max()) for k,v in runner.alg.actor.state_dict().items() if k in initial)
    assert change>0 and steps==updates*20,(change,steps)
    result=dict(start=start,end=end,updates=updates,smoke=a.smoke,num_envs=n,steps_per_env=20,
        samples=updates*n*20,seconds=time.time()-begun,checkpoint=str(ck),sha256=hashlib.sha256(ck.read_bytes()).hexdigest(),
        source=None if not a.resume else str(a.resume),started_from_scratch=not bool(a.resume),actor_weight_max_change=change,
        source_sha256=None if not a.resume else hashlib.sha256(a.resume.read_bytes()).hexdigest(),optimizer_resumed=bool(a.resume),
        actor_dim=61,critic_dim=76,goal_height_m=e.cfg.goal_height_m,reference_keyframe=e.cfg.reference_keyframe,
        deterministic_inference_target_error_mapped_rad=target_error,
        head_quiet_only=start>=300,head_active_frames=int(getattr(e,'head_active_frames',0)),
        head_nonquiet_violations=int(getattr(e,'head_nonquiet_violations',0)),head_alignment_errors=int(getattr(e,'head_alignment_errors',0)))
    (run/'completion.json').write_text(json.dumps(result,indent=2)+'\n');print('BLOCK_COMPLETE',json.dumps(result),flush=True)
finally:e.close()
