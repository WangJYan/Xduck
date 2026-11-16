from pathlib import Path
import sys,json,shutil,hashlib
import numpy as np
import torch,onnx,onnxruntime as ort
R=Path('/home/xingchen/Xduck_branches/xduck_2_0_1_head_reference_repair_20261107')
P=Path('/home/xingchen/Xduck_branches/xduck_2_0_2_from0_20261107')
O=Path(__file__).resolve().parent
sys.path.insert(0,str(R))
from inference_policy import FrozenPolicy
old=json.loads((R/'model_contract.json').read_text());new=json.loads((P/'model_contract.json').read_text())
policy=FrozenPolicy(R/'feature_precise.pt',R/'model_contract.json',solver4=True).eval()
assert hashlib.sha256((R/'feature_precise.pt').read_bytes()).hexdigest()=='28efbd7d65457fb41cce6d63c4afbab54fc494801683577c4acfec5aef6f7dc6'
class Adapted(torch.nn.Module):
 def __init__(self,p):
  super().__init__();self.policy=p;self.register_buffer('delta',torch.tensor(np.array(new['home_ctrl'])-old['home_ctrl'],dtype=torch.float32))
 def forward(self,x):
  x=torch.cat([x[:,:6],x[:,6:20]+self.delta,x[:,20:34],x[:,34:48]+self.delta/.12,x[:,48:]],dim=1)
  return self.policy(x)
torch.set_num_threads(2);torch.manual_seed(20261108)
reports={}
for name,model in [('policy_v201_original',policy),('policy_v202_adapter',Adapted(policy).eval())]:
 path=O/(name+'.onnx');dummy=torch.zeros(1,61);dummy[:,5]=-1
 torch.onnx.export(model,dummy,str(path),opset_version=17,input_names=['obs'],output_names=['raw_action'],dynamic_axes={'obs':{0:'batch'},'raw_action':{0:'batch'}},dynamo=False)
 onnx.checker.check_model(onnx.load(str(path)))
 opts=ort.SessionOptions();opts.intra_op_num_threads=2
 session=ort.InferenceSession(str(path),opts,providers=['CPUExecutionProvider'])
 rawmax=0.;targetmax=0.;total=0
 with torch.inference_mode():
  for batch in [1,32,128,1024]:
   x=torch.randn(batch,61)*.2;x[:,3:6]=torch.tensor([0.,0.,-1.]);x[:,48:51]=0.;x[:,55:]=0.
   x[:,51:55]=torch.rand(batch,4)*torch.tensor([.6,.78,2.,.4])+torch.tensor([0.,-.5,-1.,-.2]);x[:max(1,batch//4),51:55]=0.
   # Include targets near trained bounds, where raw inverse-tanh can be ill-conditioned.
   prev=policy.low+torch.rand(batch,14)*(policy.high-policy.low)
   home=torch.tensor(new['home_ctrl'] if 'adapter' in name else old['home_ctrl'])
   x[:,34:48]=(prev-home)/.12
   a=model(x).numpy();b=session.run(None,{'obs':x.numpy()})[0]
   assert np.isfinite(b).all()
   rawmax=max(rawmax,float(np.max(abs(a-b))))
   targetmax=max(targetmax,float(np.max(abs(np.tanh(a)-np.tanh(b))*policy.inc.numpy())))
   total+=batch
 assert targetmax<2e-6,(name,targetmax)
 reports[name]=dict(samples=total,max_raw_action_difference=rawmax,max_decoded_target_difference_rad=targetmax,onnx_checker='passed',sha256=hashlib.sha256(path.read_bytes()).hexdigest())
np.savez(O/'normalization_reference.npz',mean=policy.mean.numpy(),std=policy.std.numpy(),epsilon=np.float32(.01))
for src,dest in [(R/'feature_precise.pt','checkpoint.pt'),(R/'model_contract.json','original_policy_contract.json'),(P/'model_contract.json','v202_physical_model_contract.json'),(R/'inference_policy.py','inference_policy.py'),(R/'configs/PROTECTED.yaml','training_reference_PROTECTED.yaml')]:shutil.copy2(src,O/dest)
config=dict(primary_model='policy_v202_adapter.onnx',checkpoint_sha256=hashlib.sha256((O/'checkpoint.pt').read_bytes()).hexdigest(),model='Xduck_v2.0.2',source_policy='v2.0.1 feature_precise, protected old2700 body',input=dict(name='obs',dtype='float32',shape=['batch',61],normalization='embedded: (obs-mean)/(std+0.01); do not normalize externally',slices={'0:3':'base-frame angular velocity rad/s','3:6':'world down unit vector expressed in base frame; upright [0,0,-1]','6:20':'joint position minus v202 HOME rad','20:34':'joint velocity rad/s','34:48':'(previous position target - v202 HOME)/0.12','48:51':'body vx,vy m/s and yaw rate rad/s commands','51:55':'HOME-relative head commands rad: neck_pitch,head_pitch,head_yaw,head_roll','55:61':'remaining command fields: keep zero for validated standing/recovery protocol'}),output=dict(name='raw_action',shape=['batch',14],decoder='clip(previous_target + increment*tanh(raw_action), controller_target_low, controller_target_high)',state='previous_target must be the previously applied POSITION TARGET; initialize to HOME when initializing in HOME, otherwise measured joint positions within limits'),joint_names=new['policy_joint_names'],home_rad=new['home_ctrl'],legacy_home_rad=old['home_ctrl'],home_adapter='embedded: add HOME_v202-HOME_v201 to obs[6:20], and delta/0.12 to obs[34:48]; do not apply twice',target_increment_rad=new['target_increment_rad'],controller_target_low_rad=old['target_low_rad'],controller_target_high_rad=old['target_high_rad'],physical_target_low_rad=new['target_low_rad'],physical_target_high_rad=new['target_high_rad'],physics_dt_s=.001,control_dt_s=.02,joint_kp=[90,90,75,100,90,75,90,75,90,90,90,75,100,90],joint_kd=[2.5, 2.5, 2.5, 3.0, 3.0, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 3.0, 3.0],imu=dict(physical_position_in_base_m=new['imu_physical_position_in_base_m'],R_base_from_imu=new['imu_rotation_physical_to_policy'],gyro_conversion='gyro_base=R_base_from_imu @ gyro_imu',orientation_conversion='R_world_from_base=R_world_from_imu @ transpose(R_base_from_imu); gravity_base=transpose(R_world_from_base) @ [0,0,-1]',normal_input_frame='canonical base frame; IMU rotation is upstream, not embedded in ONNX',linear_acceleration='not an actor input'),head=dict(joint_indices=[5,6,7,8],command_low_rad=[0,-.5,-1.,-.2],command_high_rad=[.6,.28,1.,.2],slew_rad_s=[.8,1.,1.2,.45],command_scope='standing task only; non-standing/recovery command zero; no tilt/motion activation gate',reference_bound_rad=float(policy.head_reference_bound),expert_feature_scale=policy.head_expert_command_scale.tolist(),new_negative_neck_range='unsupported by this old trained controller; do not widen its internal target low',qualification='common single-axis accuracy 56/56, combined32/32; corner-box collision audit is not a full dynamic success guarantee'),goal_height_m=new['goal_height_m'],embedded_solver_substeps=4,limitations=['Head/body high-frequency jitter remains above proposed threshold','Rare standing head roll failure seen in earlier 27/28 migration test','Real hardware not yet validated; these are simulation and numerical parity results'],training_state='stopped by explicit user request; export performs no training')
(O/'deployment_config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
(O/'onnx_verification.json').write_text(json.dumps(dict(torch_version=torch.__version__,onnx_version=onnx.__version__,onnxruntime_version=ort.__version__,opset=17,provider='CPUExecutionProvider',verification='synthetic canonical observations, including zero/nonzero head commands and controller-bound target histories; numerical parity, not new physics qualification',results=reports),indent=2)+'\n')
print(json.dumps(reports,indent=2))
