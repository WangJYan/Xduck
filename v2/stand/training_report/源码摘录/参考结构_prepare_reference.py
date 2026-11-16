from pathlib import Path
import hashlib,json,shutil,torch

B=Path(__file__).resolve().parent
S=Path('/home/xingchen/Xduck_branches/xduck_2_0_1_standing_head_20261107')
assert not (B/'project').exists()
shutil.copytree(S/'project',B/'project',symlinks=True,ignore=shutil.ignore_patterns('.git','__pycache__'))
for name in ['physics','data']:(B/name).symlink_to(S/name,target_is_directory=True)
for name in ['runs','logs','evaluations','audit','configs']:(B/name).mkdir(exist_ok=True)
for name in ['PROTECTED.yaml','REPAIR.yaml']:
    (B/'configs'/name).write_text((S/'configs'/name).read_text().replace(str(S),str(B)))
(B/'model_contract.json').write_text((S/'model_contract.json').read_text().replace(str(S),str(B)))
(B/'source2700.pt').symlink_to(S/'source2700.pt')
source=S/'runs/standing512/final.pt'
state=torch.load(source,map_location='cpu',weights_only=True)
state['actor_state_dict']['head_reference_bound']=torch.tensor(.025)
torch.save(state,B/'source_reference.pt')
owner=B/'project/src/unilab/envs/locomotion/xduck_gf43x40'
for p in owner.glob('*.py'):
    text=p.read_text()
    if str(S) in text:p.write_text(text.replace(str(S),str(B)))
for name in ['quiet_head.py','standing_head_command.py']:shutil.copy2(B/name,owner/name)
shutil.copy2(B/'protected_actor.py',B/'project/src/unilab/algos/torch/protected_head.py')
info=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),head_reference_bound_rad=.025,head_reference_bound_deg=.025*180/3.141592653589793,weights_changed=False,optimizer_moments_preserved=True,policy_parameterization_changed=True,angle_gate=False,motion_gate=False)
(B/'audit/SOURCE.json').write_text(json.dumps(info,indent=2)+'\n');print(json.dumps(info),flush=True)
