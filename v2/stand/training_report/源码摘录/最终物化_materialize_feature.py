from pathlib import Path
import json,shutil,torch
from omegaconf import OmegaConf

B=Path(__file__).resolve().parent
source=B/'runs/reference128/final.pt'
for name,bound in [('feature_normalized',.025),('feature_precise',.01)]:
    checkpoint=torch.load(source,map_location='cpu',weights_only=True)
    checkpoint['actor_state_dict']['head_expert_command_scale']=torch.tensor([.6,.6,1.2,.25])
    checkpoint['actor_state_dict']['head_reference_bound']=torch.tensor(bound)
    torch.save(checkpoint,B/f'{name}.pt')
c=OmegaConf.load(B/'configs/PROTECTED.yaml')
c.algo.actor.head_expert_command_scale=[.6,.6,1.2,.25]
c.algo.actor.head_reference_bound_rad=.01
OmegaConf.save(c,B/'configs/PROTECTED.yaml')
shutil.copy2(B/'protected_actor.py',B/'project/src/unilab/algos/torch/protected_head.py')
(B/'audit/FEATURE_FIX.json').write_text(json.dumps(dict(source=str(source),scale=[.6,.6,1.2,.25],frozen_base_normalization_unchanged=True,expert_command_feature='command / physical range',weights_changed=False,candidates=dict(feature_normalized=.025,feature_precise=.01)),indent=2)+'\n')
