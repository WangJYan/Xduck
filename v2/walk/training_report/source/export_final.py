import hashlib,json,shutil,zipfile
from runtime_helper import *
from torch import nn
from mirror_policy import MirrorMLP
import onnxruntime as ort
complete=json.loads((B/'COMPLETE.json').read_text());assert complete['new_updates']==100 and complete['parent_stage']=='P12' and complete['P13_excluded'];path=Path(complete['final_checkpoint']);ck=torch.load(path,map_location='cpu',weights_only=False);sd=ck['actor_state_dict'];torch.set_num_threads(2)
class Export(nn.Module):
 def __init__(self):
  super().__init__();self.register_buffer('mean',sd['obs_normalizer._mean'].clone());self.register_buffer('std',sd['obs_normalizer._std'].clone());base=nn.Sequential(nn.Linear(61,512),nn.ELU(),nn.Linear(512,256),nn.ELU(),nn.Linear(256,128),nn.ELU(),nn.Linear(128,14));self.net=MirrorMLP(base,self.mean,self.std,float(sd['mlp.blend']),heading_gain=float(sd['mlp.heading_gain']));self.net.load_state_dict({k[4:]:v for k,v in sd.items() if k.startswith('mlp.')},strict=True)
 def forward(self,obs):return self.net((obs-self.mean)/(self.std+.01))
model=Export().eval();dest=B/'exports';dest.mkdir(exist_ok=True);onnx=dest/'P12_flexDR100.onnx';torch.onnx.export(model,torch.zeros((1,61)),str(onnx),opset_version=17,input_names=['obs'],output_names=['actions'],dynamic_axes={'obs':{0:'batch'},'actions':{0:'batch'}});options=ort.SessionOptions();options.intra_op_num_threads=1;sess=ort.InferenceSession(str(onnx),sess_options=options,providers=['CPUExecutionProvider']);x=np.random.default_rng(111418).normal(0,.05,(64,61)).astype(np.float32)
with torch.inference_mode():expected=model(torch.from_numpy(x)).numpy()
error=float(abs(sess.run(None,{'obs':x})[0]-expected).max());assert error<3e-5,error
metadata=dict(status='COMPLETE_100_UPDATES_EXPORTED',parent_stage='P12',P13_excluded=True,checkpoint=str(path),checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),onnx_sha256=hashlib.sha256(onnx.read_bytes()).hexdigest(),physics_sha256=complete['physics_sha256'],new_updates=100,cumulative_updates=3142,normalization_embedded=True,external_normalization=False,obs_dim=61,action_dim=14,onnx_parity_max_error=error,consumer='Same P12 API contract and active14-axisHOME/scale; hardware correspondence still requires verification.')
atomic(dest/'EXPORT_METADATA.json',metadata);atomic(B/'STATUS.json',dict(status='COMPLETE',completed_updates=100,total_updates=100,cumulative_updates=3142,onnx=str(onnx),checkpoint=str(path)));print(json.dumps(metadata),flush=True)
io=json.loads((B/'inputs/parent_P12_IO_CONTRACT.json').read_text());io.update(training_revision='P12_flexDR100_20261114',parent_stage='P12',P13_excluded=True,new_PPO_updates=100,physics_sha256=complete['physics_sha256']);atomic(dest/'P12_IO_CONTRACT.json',io)
contract=json.loads((B/'inputs/parent_MODEL_CONTRACT.json').read_text());import mujoco
m=mujoco.MjModel.from_binary_path(str(B/'physics/effective_training.mjb'));j=np.flatnonzero(m.jnt_stiffness>0);contract.update(model_sha256=complete['physics_sha256'],home_qpos=m.key('HOME').qpos.tolist(),passive_dofs=48,passive_joint_names=[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_JOINT,int(i)) for i in j],passive_stiffness=m.jnt_stiffness[j].tolist(),passive_damping=m.dof_damping[m.jnt_dofadr[j]].tolist(),flexible_dr_fraction=.1,physics_microsteps=16,nominal_physical_model_version='2.0.2',simulation_variant='48 passive flexible hinges');atomic(dest/'MODEL_CONTRACT.json',contract)
for source,target in [(B/'runs/P12/TRAINING_CONFIG.yaml',dest/'TRAINING_CONFIG.yaml'),(B/'runs/P12/EFFECTIVE_CONFIG.yaml',dest/'EFFECTIVE_CONFIG.yaml'),(B/'inputs/parent_consumer.py',dest/'xc_walk_stand.py')]:shutil.copy2(source,target)
with zipfile.ZipFile(B/'P12_flexDR100_ONNX_and_configs.zip','w',zipfile.ZIP_DEFLATED) as z:
 for f in dest.iterdir():
  if f.is_file():z.write(f,f.name)
