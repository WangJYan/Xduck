"""P12 continuation owner: existing objective, fresh passive-joint DR after bank restore."""
from dataclasses import dataclass
import numpy as np
from unilab.base import registry
from .balanced_env import BalancedPhaseEnv,BalancedPhaseCfg,BalancedPhaseReset
@registry.envcfg('XDuckP12FlexContinue')
@dataclass
class P12FlexContinueCfg(BalancedPhaseCfg):pass
class FlexibleBankReset(BalancedPhaseReset):
 def _finalize_reset_pose(self,env,plan):
  # The rigid finalizer clears all passive positions. Preserve the settled
  # flexible bank state while retaining active-angle bounds and root offset.
  q=env._policy_qpos_indices;plan.qpos[:,q]=np.clip(plan.qpos[:,q],env._reset_joint_limits[:,0]+.01,env._reset_joint_limits[:,1]-.01);plan.qpos[:,2]+=env.cfg.reset_root_z_offset_m;return plan
 def build_reset_plan(self,env,ids):
  plan=super().build_reset_plan(env,ids);n=len(ids);spread=env.cfg.flexible_dr_fraction;k=np.broadcast_to(env._nominal_flex_stiffness,(n,len(env._nominal_flex_stiffness))).copy();d=np.broadcast_to(env._nominal_flex_damping,(n,len(env._nominal_flex_damping))).copy();k[:,env._flex_joint_ids]*=env._flex_rng.uniform(1-spread,1+spread,(n,len(env._flex_joint_ids)));d[:,env._flex_dof_ids]*=env._flex_rng.uniform(1-spread,1+spread,(n,len(env._flex_dof_ids)));plan.randomization.jnt_stiffness=k;plan.randomization.dof_damping=d;return plan
@registry.env('XDuckP12FlexContinue',sim_backend='mjwarp')
class P12FlexContinueEnv(BalancedPhaseEnv):
 def _make_dr_provider(self):return FlexibleBankReset()
