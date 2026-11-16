from pathlib import Path
import json,xml.etree.ElementTree as ET
import mujoco,numpy as np
B=Path('/home/xingchen/Xduck_branches/xduck_2_0_2_P12_flexDR100_20261114/physics')
base=Path('/home/xingchen/Xduck_branches/xduck_2_0_2_v201route_step10_fromP07_20261109')
P=base/'physics';old=base/'workspace/xduck_flex_sole_dr_20260929/physics/scene.xml'
o=mujoco.MjModel.from_binary_path(str(P/'effective_training.mjb'));s=mujoco.MjSpec.from_file(str(P/'scene_train.xml'));s.compiler.discardvisual=False
added=[]
for body in ET.parse(old).findall('.//body'):
 for j in body.findall('joint'):
  if float(j.get('stiffness','0'))<=0:continue
  bodyname={'neck':'neck_pitch','neck_pitch':'head_pitch','yaw_roll_motion':'head_yaw','jaw_soft':'head_roll'}.get(body.get('name'),body.get('name'))
  target=s.body(bodyname);assert target is not None,bodyname
  target.add_joint(name=j.get('name'),type=mujoco.mjtJoint.mjJNT_HINGE,axis=[float(x) for x in j.get('axis').split()],pos=[float(x) for x in j.get('pos','0 0 0').split()],limited=False,stiffness=float(j.get('stiffness')),damping=float(j.get('damping')),armature=0,frictionloss=0,springref=0)
  added.append(dict(name=j.get('name'),body=bodyname,stiffness=float(j.get('stiffness')),damping=float(j.get('damping'))))
assert len(added)==48
for k in s.keys:
 q=np.zeros(o.nq+48);q[3]=1;k.qpos=q;k.qvel=np.zeros(o.nv+48)
for i in range(o.nkey):
 name=mujoco.mj_id2name(o,mujoco.mjtObj.mjOBJ_KEY,i);k=s.key(name)
 if k is None:k=s.add_key(name=name)
 q=np.zeros(o.nq+48);q[3]=1;k.qpos=q;k.qvel=np.zeros(o.nv+48)
m=s.compile()
for kind,n in [(mujoco.mjtObj.mjOBJ_BODY,o.nbody),(mujoco.mjtObj.mjOBJ_GEOM,o.ngeom),(mujoco.mjtObj.mjOBJ_MESH,o.nmesh)]:
 assert [mujoco.mj_id2name(o,kind,i) for i in range(n)]==[mujoco.mj_id2name(m,kind,i) for i in range(n)]
for field in ['body_pos','body_quat','body_mass','body_ipos','body_iquat','body_inertia','body_gravcomp']:
 getattr(m,field)[:]=getattr(o,field)
for field in dir(o):
 if not (field.startswith('geom_') or field.startswith('mesh_')):continue
 a=getattr(o,field);b=getattr(m,field)
 if isinstance(a,np.ndarray) and isinstance(b,np.ndarray) and a.shape==b.shape and b.flags.writeable:b[:]=a
for j in range(o.njnt):
 name=mujoco.mj_id2name(o,mujoco.mjtObj.mjOBJ_JOINT,j);k=m.joint(name).id
 nq=7 if o.jnt_type[j]==0 else 1;nv=6 if o.jnt_type[j]==0 else 1;a=int(o.jnt_qposadr[j]);b=int(m.jnt_qposadr[k]);u=int(o.jnt_dofadr[j]);v=int(m.jnt_dofadr[k])
 m.qpos0[b:b+nq]=o.qpos0[a:a+nq];m.qpos_spring[b:b+nq]=o.qpos_spring[a:a+nq]
 for key in range(o.nkey):
  mk=m.key(mujoco.mj_id2name(o,mujoco.mjtObj.mjOBJ_KEY,key)).id
  m.key_qpos[mk,b:b+nq]=o.key_qpos[key,a:a+nq];m.key_qvel[mk,v:v+nv]=o.key_qvel[key,u:u+nv]
 for field in ['dof_armature','dof_damping','dof_frictionloss']:getattr(m,field)[v:v+nv]=getattr(o,field)[u:u+nv]
 for field in ['jnt_range','jnt_limited','jnt_stiffness','jnt_pos','jnt_axis']:getattr(m,field)[k]=getattr(o,field)[j]
for field in ['actuator_gainprm','actuator_biasprm','actuator_dynprm','actuator_dyntype','actuator_gaintype','actuator_biastype','actuator_ctrlrange','actuator_forcerange','actuator_ctrllimited','actuator_forcelimited']:
 getattr(m,field)[:]=getattr(o,field)
for attr in dir(o.opt):
 if attr.startswith('_') or callable(getattr(o.opt,attr)):continue
 try:setattr(m.opt,attr,getattr(o.opt,attr))
 except (AttributeError,TypeError):pass
# Match legacy flexible solver: sixteen physics microsteps per 1ms motor update.
m.opt.timestep=.001/16
d0=mujoco.MjData(o);d1=mujoco.MjData(m);mujoco.mj_resetDataKeyframe(o,d0,o.key('HOME').id);mujoco.mj_resetDataKeyframe(m,d1,m.key('HOME').id);mujoco.mj_forward(o,d0);mujoco.mj_forward(m,d1)
validation=dict(added_joints=added,nq=m.nq,nv=m.nv,nu=m.nu,model_mass_kg=float(m.body_mass.sum()),mass_difference_kg=float(m.body_mass.sum()-o.body_mass.sum()),zero_flex_HOME_body_position_max_error_m=float(abs(d1.xpos-d0.xpos).max()),zero_flex_HOME_geom_position_max_error_m=float(abs(d1.geom_xpos-d0.geom_xpos).max()),zero_flex_HOME_geom_rotation_max_error=float(abs(d1.geom_xmat-d0.geom_xmat).max()),stiffness_DR=[.9,1.1],damping_DR=[.9,1.1],physics_microsteps=16,passive_state_initialization='zero deflection and zero velocity; true loaded structural deflection unobserved',scope='Original v2.0.2 masses, geometry and motor axes preserved; passive compliance recipe migrated from original flex model, not identified hardware stiffness.')
assert validation['zero_flex_HOME_geom_position_max_error_m']<1e-10
mujoco.mj_saveModel(m,str(B/'effective_training.mjb'));(B/'FLEX_MODEL_VALIDATION.json').write_text(json.dumps(validation,indent=2));print(json.dumps({k:v for k,v in validation.items() if k!='added_joints'},indent=2))

for i in range(o.nkey):
 name=mujoco.mj_id2name(o,mujoco.mjtObj.mjOBJ_KEY,i);mk=m.key(name).id;m.key_ctrl[mk]=o.key_ctrl[i]
for key in s.keys:
 key.qpos=m.key(key.name).qpos.copy();key.qvel=m.key(key.name).qvel.copy();key.ctrl=m.key(key.name).ctrl.copy()
for attr in dir(m.opt):
 if attr.startswith('_') or callable(getattr(m.opt,attr)):continue
 try:setattr(s.option,attr,getattr(m.opt,attr))
 except (AttributeError,TypeError):pass
s.compiler.meshdir='assets'
(B/'scene_flex.xml').write_text(s.to_xml())
mujoco.mj_saveModel(m,str(B/'effective_training.mjb'))
x=mujoco.MjModel.from_xml_path(str(B/'scene_flex.xml'));assert x.nq==69 and x.nv==68 and x.nu==14
assert np.allclose(x.body_mass,m.body_mass) and np.allclose(x.jnt_stiffness,m.jnt_stiffness)
print('XML and compiled flexible models saved and validated',x.nq,x.nv,x.nu)
