from pathlib import Path
import shutil
from omegaconf import OmegaConf
B=Path(__file__).resolve().parent
shutil.copy2(B/'protected_actor.py',B/'project/src/unilab/algos/torch/protected_head.py')
c=OmegaConf.load(B/'configs/REPAIR.yaml')
c.algo.actor.class_name='unilab.algos.torch.protected_head.ProtectedHeadActor'
c.env.head_track_rate=16.;c.env.head_bias_cost=3.;c.env.head_fine_weight=.5
c.env.head_body_posture_scale=.15
OmegaConf.save(c,B/'configs/PROTECTED.yaml')
print('Protected branch config prepared',flush=True)
