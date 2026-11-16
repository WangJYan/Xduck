"""Standing head reference with bounded learned correction and learned whole-body balance."""
import copy
import torch
from .joint_solver import JointSolverActor

class ProtectedHeadActor(JointSolverActor):
    def __init__(self,*args,head_expert_command_scale=None,head_reference_bound_rad=.025,**kwargs):
        super().__init__(*args,**kwargs)
        self.register_buffer("head_reference_bound",torch.tensor(head_reference_bound_rad))
        self.feature_scaling=head_expert_command_scale is not None
        if self.feature_scaling:self.register_buffer("head_expert_command_scale",torch.tensor(head_expert_command_scale,dtype=torch.float32))
        self.base_mlp=copy.deepcopy(self.mlp)
        self.base_mlp.requires_grad_(False)
        self.head_error_gain=torch.nn.Parameter(torch.zeros(14,4))
        self.head_command_gain=torch.nn.Parameter(torch.zeros(14,4))
    def update_normalization(self,obs):pass
    def forward(self,obs,masks=None,hidden_state=None,stochastic_output=False):
        if masks is not None:
            from rsl_rl.utils import unpad_trajectories
            obs=unpad_trajectories(obs,masks)
        x=torch.cat([obs[g] for g in self.obs_groups],dim=-1)
        previous=self.solver_default+.12*x[:,34:48];target=previous
        cmd=x[:,51:55];blend=torch.clamp(torch.amax(abs(cmd),dim=1,keepdim=True)/.02,max=1.)
        scale=x.new_tensor([.6,.6,1.2,.25]);error=(cmd-x[:,11:15])/scale
        for _ in range(4):
            inner=torch.cat([x[:,:34],(target-self.solver_default)/.12,x[:,48:]],dim=-1)
            normalized=self.obs_normalizer(inner)
            base=self.base_mlp(normalized)
            head_input=normalized
            if self.feature_scaling:head_input=torch.cat([normalized[:,:51],cmd/self.head_expert_command_scale,normalized[:,55:]],dim=-1)
            head=self.mlp(head_input)+error@self.head_error_gain.T+(cmd/scale)@self.head_command_gain.T
            raw=base+blend*(head-base)
            delta=.25*self.solver_inc*torch.tanh(raw)
            desired=self.solver_default[5:9]+cmd+self.head_reference_bound*torch.tanh(head[:,5:9])
            desired=torch.maximum(torch.minimum(desired,self.solver_high[5:9]),self.solver_low[5:9])
            reference_step=torch.clamp(desired-target[:,5:9],-.25*self.solver_inc[5:9],.25*self.solver_inc[5:9])
            base_step=.25*self.solver_inc[5:9]*torch.tanh(base[:,5:9])
            head_step=base_step+blend*(reference_step-base_step)
            delta=torch.cat([delta[:,:5],head_step,delta[:,9:]],dim=-1)
            target=torch.maximum(torch.minimum(target+delta,self.solver_high),self.solver_low)
        ratio=torch.clamp((target-previous)/self.solver_inc,-1+1e-6,1-1e-6)
        mean=.5*(torch.log1p(ratio)-torch.log1p(-ratio))
        if stochastic_output:self.distribution.update(mean);return self.distribution.sample()
        return self.distribution.deterministic_output(mean)
