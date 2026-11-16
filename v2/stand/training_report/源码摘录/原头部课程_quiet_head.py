"""Quiet standing head commands learned jointly with the full body actor."""
from dataclasses import dataclass
import numpy as np
from unilab.base import registry
from .recovery_v2 import RecoveryV2Cfg,RecoveryV2Env
from .settle_repair import SettleRepairCfg,SettleRepairEnv

HEAD=np.array([5,6,7,8]);LEGS=np.array([0,1,2,3,4,9,10,11,12,13])
LOW=np.array([0.,-.6,-1.2,-.25]);HIGH=np.array([.6,.6,1.2,.25]);RATE=np.array([.8,1.,1.5,.6])

class QuietHeadMixin:
    def __init__(self,cfg,num_envs=1,backend_type='mjwarp'):
        self._qh_rng=np.random.default_rng(cfg.discovery_seed+703)
        self._qh_request=np.zeros((num_envs,4));self._qh_effective=np.zeros((num_envs,4))
        self._qh_consumed=np.zeros((num_envs,4));self._qh_timer=np.zeros(num_envs)
        self._qh_hold=np.zeros(num_envs);self._qh_normal=np.zeros(num_envs,bool)
        self._qh_gyro=np.zeros((num_envs,3));self._qh_velocity=np.zeros((num_envs,14))
        self._qh_bias=np.zeros((num_envs,4));self._qh_active=np.zeros(num_envs,bool)
        self.head_nonquiet_violations=0;self.head_alignment_errors=0;self.head_active_frames=0
        super().__init__(cfg,num_envs,backend_type)

    def reset(self,env_indices):
        ids=np.asarray(env_indices,int)
        for name in ['_qh_request','_qh_effective','_qh_consumed','_qh_timer','_qh_hold','_qh_gyro','_qh_velocity','_qh_bias']:getattr(self,name)[ids]=0.
        self._qh_normal[ids]=False;self._qh_active[ids]=False
        return super().reset(ids)

    def _sample_quiet_head(self,n):
        r=self._qh_rng.uniform(LOW*self.cfg.head_range_fraction,HIGH*self.cfg.head_range_fraction,(n,4))
        typ=self._qh_rng.random(n);r[typ<.2]=0.
        single=(typ>=.2)&(typ<.7);axes=self._qh_rng.integers(0,4,n);r[single]*=np.eye(4)[axes[single]]
        return r

    def _compute_obs(self,gyro,upvector,dof_pos,dof_vel,last_actions,commands,**kw):
        ids=np.arange(self.num_envs) if kw.get('env_ids') is None else np.asarray(kw['env_ids'],int)
        if kw.get('env_ids') is None:
            self._qh_gyro+=(gyro-self._qh_gyro)*(1-np.exp(-.02/.15))
            self._qh_velocity+=(dof_vel-self._qh_velocity)*(1-np.exp(-.02/.1))
            tilt=np.degrees(np.arccos(np.clip(upvector[:,2],-1,1)))
            leg=np.sqrt(np.mean(self._qh_velocity[:,LEGS]**2,axis=1));pose=np.sqrt(np.mean((dof_pos[:,LEGS]-self.default_angles[LEGS])**2,axis=1))
            xy=np.linalg.norm(gyro[:,:2],axis=1);ema_xy=np.linalg.norm(self._qh_gyro[:,:2],axis=1)
            # Eligibility must use the deployed observation contract, never critic-only root velocity.
            zero_twist=np.max(abs(commands[:,:3]),axis=1)<1e-6
            permission=(self._kind==0)&self.cfg.head_training_enabled&(self._force_left==0)
            finite=np.isfinite(gyro).all(1)&np.isfinite(upvector).all(1)&np.isfinite(dof_vel).all(1)
            enter=permission&finite&zero_twist&(tilt<8)&(ema_xy<.35)&(leg<.6)&(pose<.3)
            keep=permission&finite&zero_twist&(tilt<12)&(xy<.9)&(ema_xy<.65)&(abs(gyro[:,2])<1.8)&(abs(self._qh_gyro[:,2])<.8)&(leg<.9)&(pose<.45)
            self._qh_normal&=keep;self._qh_hold=np.where(enter,self._qh_hold+.02,0.)
            self._qh_normal|=(self._qh_hold>=.3-1e-9)&keep
            due=self._qh_timer<=0
            if due.any():
                self._qh_request[due]=self._sample_quiet_head(int(due.sum()));self._qh_timer[due]=self._qh_rng.uniform(2.,5.,int(due.sum()));self._qh_bias[due]=0.
            self._qh_timer-=.02
            self._qh_effective+=np.clip(self._qh_request-self._qh_effective,-RATE*.02,RATE*.02)
            self._qh_effective[~self._qh_normal]=0.;self._qh_bias[~self._qh_normal]=0.
        self._head_goal[ids]=self._qh_effective[ids]
        bad=(self._kind[ids]!=0)&np.any(abs(self._head_goal[ids])>0,axis=1)
        self.head_nonquiet_violations+=int(bad.sum())
        if bad.any():raise RuntimeError('head command enabled outside quiet standing')
        commands=commands.copy();commands[:,3:7]=self._head_goal[ids]
        return super()._compute_obs(gyro,upvector,dof_pos,dof_vel,last_actions,commands,**kw)

    def apply_action(self,actions,state):
        self._qh_consumed[:]=state.obs['obs'][:,51:55]
        self._qh_active[:]=self._qh_normal&(self._kind==0)&self.cfg.head_training_enabled
        return super().apply_action(actions,state)

    def _compute_reward(self,state,linvel,gyro,upvector,dof_pos):
        mismatch=np.any(abs(self._qh_consumed-state.obs['obs'][:,51:55])>1e-6,axis=1)
        self.head_alignment_errors+=int(mismatch.sum())
        if mismatch.any():raise RuntimeError('head reward used a command different from action observation')
        next_goal=self._head_goal.copy();self._head_goal[:]=self._qh_consumed
        try:reward=super()._compute_reward(state,linvel,gyro,upvector,dof_pos)
        finally:self._head_goal[:]=next_goal
        error=dof_pos[:,HEAD]-self.default_angles[HEAD]-self._qh_consumed
        active=self._qh_active&~self._nonfoot_ground&(upvector[:,2]>np.cos(np.deg2rad(12)))
        self._qh_bias+=(error-self._qh_bias)*(1-np.exp(-.02/1.));self._qh_bias[~active]=0.
        f=self.cfg.head_fine_weight
        score=((1-f)*np.exp(-(error/.5)**2)+f*np.exp(-(error/.08)**2)).mean(1)
        track=.02*8.*score*active;bias=.02*self.cfg.head_bias_cost*np.mean(abs(self._qh_bias),axis=1)/.15*active
        reward+=track-bias;self.head_active_frames+=int(active.sum())
        state.info.setdefault('log',{}).update({'head/quiet_active_fraction':float(active.mean()),'head/follow_reward':float(track.mean()),'head/bias_cost':float(bias.mean()),'head/nonquiet_violations':float(self.head_nonquiet_violations),'head/alignment_errors':float(self.head_alignment_errors)})
        return reward.astype(np.float32)

@registry.envcfg('XDuckQuietRecovery')
@dataclass
class QuietRecoveryCfg(RecoveryV2Cfg):
    head_training_enabled:bool=True
    head_range_fraction:float=.05
    head_fine_weight:float=0.
    head_bias_cost:float=.5

@registry.env('XDuckQuietRecovery',sim_backend='mjwarp')
class QuietRecoveryEnv(QuietHeadMixin,RecoveryV2Env):pass

@registry.envcfg('XDuckQuietSettle')
@dataclass
class QuietSettleCfg(SettleRepairCfg):
    head_training_enabled:bool=True
    head_range_fraction:float=1.
    head_fine_weight:float=.15
    head_bias_cost:float=1.5

@registry.env('XDuckQuietSettle',sim_backend='mjwarp')
class QuietSettleEnv(QuietHeadMixin,SettleRepairEnv):pass
