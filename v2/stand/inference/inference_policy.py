"""Deterministic inference with embedded normalization and optional solver4."""
import json
from pathlib import Path
import torch

class FrozenPolicy(torch.nn.Module):
    def __init__(self,checkpoint,contract,solver4=False):
        super().__init__();s=torch.load(checkpoint,map_location='cpu',weights_only=True)['actor_state_dict']
        self.register_buffer('mean',s['obs_normalizer._mean']);self.register_buffer('std',s['obs_normalizer._std'])
        self.net=torch.nn.Sequential(torch.nn.Linear(61,512),torch.nn.ELU(),torch.nn.Linear(512,256),torch.nn.ELU(),torch.nn.Linear(256,128),torch.nn.ELU(),torch.nn.Linear(128,14))
        self.net.load_state_dict({k[4:]:v for k,v in s.items() if k.startswith('mlp.')})
        self.feature_scaling='head_expert_command_scale' in s
        if self.feature_scaling:self.register_buffer('head_expert_command_scale',s['head_expert_command_scale'])
        self.reference='head_reference_bound' in s
        if self.reference:self.register_buffer('head_reference_bound',s['head_reference_bound'])
        self.protected='head_error_gain' in s
        if self.protected:
            import copy
            self.base_net=copy.deepcopy(self.net);self.base_net.load_state_dict({k[9:]:v for k,v in s.items() if k.startswith('base_mlp.')})
            self.register_buffer('error_gain',s['head_error_gain']);self.register_buffer('command_gain',s['head_command_gain'])
        c=json.loads(Path(contract).read_text());self.solver4=solver4
        for name,key in [('default','home_ctrl'),('low','target_low_rad'),('high','target_high_rad')]:self.register_buffer(name,torch.tensor(c[key],dtype=torch.float32))
        self.register_buffer('inc',torch.tensor([.015,.01,.08,.06,.075,.11,.025,.025,.01,.015,.01,.08,.06,.075]))
        self.eval();self.requires_grad_(False)
    def forward(self,x):
        if not self.solver4:return self.net((x-self.mean)/(self.std+.01))
        previous=self.default+.12*x[:,34:48];target=previous
        for _ in range(4):
            inner=torch.cat([x[:,:34],(target-self.default)/.12,x[:,48:]],dim=-1)
            normalized=(inner-self.mean)/(self.std+.01)
            head_input=normalized
            if self.feature_scaling:head_input=torch.cat([normalized[:,:51],x[:,51:55]/self.head_expert_command_scale,normalized[:,55:]],dim=-1)
            raw=self.net(head_input)
            if self.protected:
                cmd=x[:,51:55];scale=x.new_tensor([.6,.6,1.2,.25]);error=(cmd-x[:,11:15])/scale
                head=raw+error@self.error_gain.T+(cmd/scale)@self.command_gain.T
                base=self.base_net(normalized)
                blend=torch.clamp(torch.amax(abs(cmd),dim=1,keepdim=True)/.02,max=1.)
                raw=base+blend*(head-base)
            delta=.25*self.inc*torch.tanh(raw)
            if self.reference:
                desired=self.default[5:9]+cmd+self.head_reference_bound*torch.tanh(head[:,5:9])
                desired=torch.maximum(torch.minimum(desired,self.high[5:9]),self.low[5:9])
                reference_step=torch.clamp(desired-target[:,5:9],-.25*self.inc[5:9],.25*self.inc[5:9])
                base_step=.25*self.inc[5:9]*torch.tanh(base[:,5:9])
                head_step=base_step+blend*(reference_step-base_step)
                delta=torch.cat([delta[:,:5],head_step,delta[:,9:]],dim=-1)
            target=torch.maximum(torch.minimum(target+delta,self.high),self.low)
        ratio=torch.clamp((target-previous)/self.inc,-1+1e-6,1-1e-6)
        return .5*(torch.log1p(ratio)-torch.log1p(-ratio))
