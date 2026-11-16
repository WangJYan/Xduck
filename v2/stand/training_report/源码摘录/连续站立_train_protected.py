"""Train a protected whole-body head expert with mapped optimizer moments."""
from pathlib import Path
import argparse,copy,hashlib,json,sys,time
from dataclasses import asdict
import numpy as np
import torch
from omegaconf import OmegaConf
from freeze_sources import freeze
from inference_policy import FrozenPolicy
B=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--resume',type=Path,default=B/'source_head576.pt');ap.add_argument('--run',required=True);ap.add_argument('--updates',type=int,default=64);ap.add_argument('--num-envs',type=int,default=1024);ap.add_argument('--lr',type=float,default=5e-5);ap.add_argument('--gain-lr',type=float,default=.0015);ap.add_argument('--seed',type=int,default=2026110711);ap.add_argument('--quiet-only',action='store_true');ap.add_argument('--range-fraction',type=float,default=1.);a=ap.parse_args();assert 0<a.range_fraction<=1.
run=B/'runs'/a.run;run.mkdir(exist_ok=True);assert not (run/'final.pt').exists();freeze(B,run)
sys.path[:0]=[str(B/'project/src'),str(B/'project/scripts')]
import train_rsl_rl as E
from unilab.training.rsl_rl import RslRlVecEnvWrapper,attach_checkpoint_progress
E.ensure_registries();torch.set_num_threads(2);np.random.seed(a.seed);torch.manual_seed(a.seed)
c=OmegaConf.load(B/'configs/PROTECTED.yaml');c.algo.num_envs=a.num_envs;c.algo.max_iterations=a.updates;c.env.discovery_seed=a.seed;c.training.log_dir=str(run)
c.env.head_range_fraction=a.range_fraction
if a.quiet_only:c.env.training_reset_weights=[1.,0.,0.,0.,0.]
OmegaConf.save(c,run/'CONFIG.yaml');e=E.create_env(c,num_envs=a.num_envs,env_cfg_override=E.build_ppo_env_cfg_override(c))
try:
    (run/'FULL_ENV_CONFIG.json').write_text(json.dumps(asdict(e.cfg),indent=2,default=str)+'\n')
    wrapper=RslRlVecEnvWrapper(e,device='cuda:0');tc=E.normalize_ppo_train_cfg(OmegaConf.to_container(c.algo,resolve=True));E.apply_ppo_runtime_flags(tc,c,training_enabled=True)
    runner=E.OnPolicyRunner(wrapper,tc,log_dir=str(run),device='cuda:0');actor=runner.alg.actor;critic=runner.alg.critic
    main=[p for name,p in actor.named_parameters() if p.requires_grad and name not in ['head_error_gain','head_command_gain']]
    groups=[dict(params=main,lr=a.lr),dict(params=[actor.head_error_gain,actor.head_command_gain],lr=a.gain_lr),dict(params=list(critic.parameters()),lr=2e-4)]
    old_optimizer=runner.alg.optimizer;runner.alg.optimizer=type(old_optimizer)(groups,**old_optimizer.defaults)
    source=torch.load(a.resume,map_location='cpu',weights_only=True)
    bootstrap='head_error_gain' not in source['actor_state_dict']
    if bootstrap:
        base=torch.load(B/'source2700.pt',map_location='cpu',weights_only=True)
        for name in ['obs_normalizer._mean','obs_normalizer._std','obs_normalizer._var','obs_normalizer.count']:assert torch.equal(source['actor_state_dict'][name],base['actor_state_dict'][name])
        state=actor.state_dict();state.update(source['actor_state_dict'])
        for name,value in base['actor_state_dict'].items():
            if name.startswith('mlp.'):state['base_mlp.'+name[4:]]=value
        actor.load_state_dict(state);critic.load_state_dict(source['critic_state_dict'])
        # Preserve moments for existing actor/critic parameters. New gains start with no moments.
        old_ids=[i for g in source['optimizer_state_dict']['param_groups'] for i in g['params']]
        old_objects=[p for name,p in actor.named_parameters() if name in source['actor_state_dict']]+list(critic.parameters())
        assert len(old_ids)==len(old_objects),(len(old_ids),len(old_objects))
        destination=runner.alg.optimizer.state_dict();idmap={}
        for objects,serialized in zip(runner.alg.optimizer.param_groups,destination['param_groups']):
            for p,i in zip(objects['params'],serialized['params']):idmap[id(p)]=i
        destination['state']={idmap[id(p)]:copy.deepcopy(source['optimizer_state_dict']['state'][i]) for i,p in zip(old_ids,old_objects) if i in source['optimizer_state_dict']['state']}
        runner.alg.optimizer.load_state_dict(destination);runner.current_learning_iteration=int(source.get('iter',0))
    else:runner.load(str(a.resume),map_location='cuda:0')
    runner.alg.schedule='fixed';runner.alg.learning_rate=a.lr
    for group,lr in zip(runner.alg.optimizer.param_groups,[a.lr,a.gain_lr,2e-4]):group['lr']=lr
    for model in [actor,critic]:model.obs_normalizer.eval();model.update_normalization=lambda *_x,**_y:None
    actor.base_mlp.requires_grad_(False);frozen_base={k:v.detach().cpu().clone() for k,v in actor.base_mlp.state_dict().items()}
    original=FrozenPolicy(B/'source2700.pt',B/'model_contract.json',solver4=True)
    def zero_identity():
        obs=wrapper.get_observations().clone();obs['actor'][:,51:55]=0.
        x=obs['actor'].cpu()
        with torch.inference_mode():native=actor(obs,stochastic_output=False).cpu().numpy();expected=original(x).numpy()
        return float(np.max(abs(np.tanh(native)-np.tanh(expected))*e._increments))
    identity_before=zero_identity();assert identity_before<2e-6,identity_before
    def cap(*_args):
        with torch.no_grad():
            lp=actor.distribution.log_std_param;lp.clamp_(np.log(.06),np.log(.25));lp[5]=lp[5].clamp(np.log(.04),np.log(.12));lp[6:9]=lp[6:9].clamp(np.log(.06),np.log(.18))
            ids=torch.tensor([0,1,2,3,4,9,10,11,12,13],device=lp.device);lp[ids]=lp[ids].clamp(np.log(.18),np.log(.25))
    cap();runner.alg.optimizer.register_step_post_hook(cap);attach_checkpoint_progress(e,runner)
    step=e.step;stepcount=0
    def checked(actions):
        global stepcount
        out=step(actions);stepcount+=1
        assert np.isfinite(out.reward).all() and all(np.isfinite(v).all() for v in out.obs.values())
        assert e.head_nonquiet_violations==0 and e.head_alignment_errors==0
        return out
    e.step=checked;start=time.time();runner.learn(num_learning_iterations=a.updates,init_at_random_ep_len=False)
    ck=run/'final.pt';runner.save(str(ck));assert stepcount==a.updates*20
    assert all(torch.equal(v.cpu(),frozen_base[k]) for k,v in actor.base_mlp.state_dict().items())
    identity_after=zero_identity();assert identity_after<2e-6,identity_after
    frozen=FrozenPolicy(ck,B/'model_contract.json',solver4=True)
    with torch.inference_mode():native=actor(wrapper.get_observations(),stochastic_output=False).cpu().numpy();deployment=frozen(torch.as_tensor(e.state.obs['obs'],dtype=torch.float32)).numpy()
    delta=float(np.max(abs(np.tanh(native)-np.tanh(deployment))*e._increments));assert delta<2e-6,delta
    result=dict(checkpoint=str(ck),checkpoint_sha256=hashlib.sha256(ck.read_bytes()).hexdigest(),source=str(a.resume),source_sha256=hashlib.sha256(a.resume.read_bytes()).hexdigest(),base_source_sha256=hashlib.sha256((B/'source2700.pt').read_bytes()).hexdigest(),updates=a.updates,num_envs=a.num_envs,samples=a.updates*a.num_envs*20,seconds=time.time()-start,structural_bootstrap=bootstrap,existing_optimizer_moments_preserved=True,base_all_tensors_unchanged=True,zero_head_identity_before_rad=identity_before,zero_head_identity_after_rad=identity_after,inference_target_error_rad=delta,head_nonquiet_violations=e.head_nonquiet_violations,head_alignment_errors=e.head_alignment_errors,head_error_gain=actor.head_error_gain.detach().cpu().tolist(),head_command_gain=actor.head_command_gain.detach().cpu().tolist())
    (run/'completion.json').write_text(json.dumps(result,indent=2)+'\n');print('PROTECTED_TRAINING_COMPLETE',json.dumps(result),flush=True)
finally:e.close()
