from pathlib import Path
import time,hashlib
import numpy as np,mujoco
from runtime_helper import *
initialize();c=OmegaConf.load(B/'BANK_CONFIG.yaml');c.env.reference_weight_after300=0.;c.env.cadence_weight_after300=0.;e=env(c,128,False);fields=['geom_pos','geom_quat','jnt_stiffness','dof_damping','body_mass','body_inertia','body_ipos','geom_friction','dof_armature'];model=mujoco.MjModel.from_binary_path(str(B/'physics/effective_training.mjb'));start=time.time()
try:
 e.step_counter=900*24;e._apply_stage_schedule();e.init_state();e.set_autoreset(False);ids=np.arange(128,dtype=np.int32);home=model.key('HOME').qpos.copy();e._backend.set_state(ids,np.tile(home,(128,1)),np.zeros((128,model.nv)),None);e._motor.reset(ids);e._current_action_target[:]=e.default_angles;e._previous_action_target[:]=e.default_angles
 def hold(state):state.info['commands'][:]=0
 e._maybe_resample_commands=hold;snapshots=[];masks=[]
 for tick in range(250):
  result=e.step(np.zeros((128,14)));assert np.isfinite(result.reward).all();phi=e._backend.get_physics_state();q=phi[:,1:1+model.nq];v=phi[:,1+model.nq:1+model.nq+model.nv];assert np.isfinite(q).all()
  if tick in [149,199,249]:
   tilt=np.degrees(np.arccos(np.clip(1-2*(q[:,4]**2+q[:,5]**2),-1,1)));velocity=e.get_local_linvel();good=(tilt<6)&(np.linalg.norm(velocity[:,:2],axis=1)<.02)&(q[:,2]>.252878360748291);masks.append(good);saved={key:getattr(e._backend._device_model,key).numpy().copy() for key in fields};feet=np.stack([e._backend.get_sensor_data(s) for s in e.cfg.sensor.feet_pos],1);saved.update(qpos=q.copy(),qvel=v.copy(),target=e._current_action_target.copy(),initial_width=abs(feet[:,0,1]-feet[:,1,1]),linvel=velocity.copy())
   for key in ['encoder_bias','imu_rotation','sole_angles','sole_delta_quat']:saved[key]=getattr(e,'_'+key).copy()
   snapshots.append(saved);print('BANK',tick+1,'good',int(good.sum()),'elapsed',round(time.time()-start,1),flush=True)
 good=np.logical_and.reduce(masks);selected=np.flatnonzero(good)[:96];assert len(selected)>=32,('Not enough settled flexible states',len(selected));bank={key:np.concatenate([s[key][selected] for s in snapshots]) for key in snapshots[0]};path=B/'inputs/new_standing_bank.npz';np.savez_compressed(path,**bank);idsflex=np.flatnonzero(model.jnt_stiffness>0);ratio=bank['jnt_stiffness'][:,idsflex]/model.jnt_stiffness[idsflex];assert ratio.min()>=.9-1e-6 and ratio.max()<=1.1+1e-6
 atomic(B/'audit/FLEXIBLE_STANDING_BANK.json',dict(status='PASS',rows=len(bank['qpos']),independent_worlds=len(selected),nq=model.nq,nv=model.nv,held_HOME=True,physically_settled=True,passive_deflection_nonzero=bool(abs(bank['qpos'][:,model.jnt_qposadr[idsflex]]).max()>1e-6),stiffness_ratio=[float(ratio.min()),float(ratio.max())],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),elapsed_s=time.time()-start))
 print('BANK_READY',path,len(bank['qpos']),flush=True)
finally:e.close()
