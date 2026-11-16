"""Full-checkpoint PPO repair; all fourteen outputs remain learned actions."""
from pathlib import Path
import argparse,hashlib,json,sys,time
from dataclasses import asdict
import numpy as np
import torch
from omegaconf import OmegaConf
B=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--resume',type=Path,default=B/'source2700.pt');ap.add_argument('--updates',type=int,default=32);ap.add_argument('--num-envs',type=int,default=1024);ap.add_argument('--run',required=True);ap.add_argument('--lr',type=float,default=3e-5);ap.add_argument('--range-fraction',type=float,default=1.);ap.add_argument('--seed',type=int,default=2026110701);a=ap.parse_args()
run=(B/'runs'/a.run).resolve();assert run.is_relative_to((B/'runs').resolve());run.mkdir(exist_ok=True)
assert not (run/'final.pt').exists(),'Use a new run name; successful checkpoints are immutable'
from freeze_sources import freeze
source_manifest_sha256=freeze(B,run)
assert a.resume.resolve().is_relative_to(B.resolve()),'resume must be a frozen source or this repair branch checkpoint'
sys.path[:0]=[str(B/'project/src'),str(B/'project/scripts')]
import train_rsl_rl as E
from unilab.training.rsl_rl import RslRlVecEnvWrapper,attach_checkpoint_progress
from inference_policy import FrozenPolicy
E.ensure_registries();torch.set_num_threads(2);np.random.seed(a.seed);torch.manual_seed(a.seed)
c=OmegaConf.load(B/'configs/REPAIR.yaml');c.algo.num_envs=a.num_envs;c.algo.max_iterations=a.updates;c.algo.algorithm.learning_rate=a.lr;c.env.discovery_seed=a.seed;c.env.head_range_fraction=a.range_fraction;c.training.log_dir=str(run)
OmegaConf.save(c,run/'CONFIG.yaml');e=E.create_env(c,num_envs=a.num_envs,env_cfg_override=E.build_ppo_env_cfg_override(c))
(run/'FULL_ENV_CONFIG.json').write_text(json.dumps(asdict(e.cfg),indent=2,default=lambda x:x.tolist() if isinstance(x,np.ndarray) else str(x))+'\n')
try:
    wrapper=RslRlVecEnvWrapper(e,device='cuda:0');tc=E.normalize_ppo_train_cfg(OmegaConf.to_container(c.algo,resolve=True));E.apply_ppo_runtime_flags(tc,c,training_enabled=True)
    runner=E.OnPolicyRunner(wrapper,tc,log_dir=str(run),device='cuda:0')
    runner.load(str(a.resume),map_location='cuda:0');source=torch.load(a.resume,map_location='cpu',weights_only=True)
    for model,key in [(runner.alg.actor,'actor_state_dict'),(runner.alg.critic,'critic_state_dict')]:assert all(torch.equal(v.cpu(),source[key][k]) for k,v in model.state_dict().items())
    assert runner.alg.optimizer.state
    runner.alg.learning_rate=a.lr;runner.alg.schedule='fixed'
    for group in runner.alg.optimizer.param_groups:group['lr']=a.lr
    for model in [runner.alg.actor,runner.alg.critic]:model.obs_normalizer.eval();model.update_normalization=lambda *_args,**_kw:None
    def cap(*_args):
        with torch.no_grad():
            lp=runner.alg.actor.distribution.log_std_param;lp.clamp_(np.log(.12),np.log(.35))
            ids=torch.tensor([0,1,2,3,4,9,10,11,12,13],device=lp.device);lp[ids]=lp[ids].clamp(np.log(.18),np.log(.25))
            lp[5]=lp[5].clamp(np.log(.04),np.log(.12))
            hids=torch.tensor([6,7,8],device=lp.device);lp[hids]=lp[hids].clamp(np.log(.06),np.log(.18))
    cap();runner.alg.optimizer.register_step_post_hook(cap);attach_checkpoint_progress(e,runner)
    oldstep=e.step;stepcount=0
    def checked(actions):
        global stepcount
        out=oldstep(actions);stepcount+=1
        assert np.isfinite(out.reward).all() and all(np.isfinite(v).all() for v in out.obs.values())
        assert e.head_nonquiet_violations==0 and e.head_alignment_errors==0
        return out
    e.step=checked;before=runner.alg.actor.mlp[0].weight.detach().clone();start=time.time()
    runner.learn(num_learning_iterations=a.updates,init_at_random_ep_len=False);ck=run/'final.pt';runner.save(str(ck))
    assert stepcount==a.updates*20
    change=float((runner.alg.actor.mlp[0].weight-before).abs().max());assert change>0
    frozen=FrozenPolicy(ck,B/'model_contract.json',solver4=True)
    with torch.inference_mode():
        native=runner.alg.actor(wrapper.get_observations(),stochastic_output=False).cpu().numpy();deployment=frozen(torch.as_tensor(e.state.obs['obs'],dtype=torch.float32)).numpy()
    delta=float(np.max(abs(np.tanh(native)-np.tanh(deployment))*e._increments));assert delta<2e-6
    result=dict(checkpoint=str(ck),checkpoint_sha256=hashlib.sha256(ck.read_bytes()).hexdigest(),source=str(a.resume),source_sha256=hashlib.sha256(a.resume.read_bytes()).hexdigest(),source_manifest_sha256=source_manifest_sha256,updates=a.updates,num_envs=a.num_envs,samples=a.updates*a.num_envs*20,seconds=time.time()-start,optimizer_preserved=True,actor_weight_change_max=change,head_active_frames=e.head_active_frames,head_pause_frames=e.head_pause_frames,head_nonquiet_violations=e.head_nonquiet_violations,head_alignment_errors=e.head_alignment_errors,tilt_limit_deg=e.cfg.head_tilt_limit_deg,head_range_fraction=e.cfg.head_range_fraction,head_near_reset_fraction=e.cfg.head_near_reset_fraction,learned_std=runner.alg.actor.distribution.log_std_param.detach().exp().cpu().tolist(),inference_target_error_rad=delta)
    (run/'completion.json').write_text(json.dumps(result,indent=2)+'\n');print('TRAINING_COMPLETE',json.dumps(result),flush=True)
finally:e.close()
