from pathlib import Path
import mujoco
import mujoco.viewer
import numpy as np
import sys
import time
entry='scene_train.xml' if '--train-model' in sys.argv else 'scene.xml'
model=mujoco.MjModel.from_xml_path(str(Path(__file__).resolve().parent/entry))
data=mujoco.MjData(model)
if '--knee-adjust' in sys.argv:
    for side in ('left','right'):
        knee_joint=model.joint(side+'_knee_pitch_joint').id
        knee_actuator=model.actuator(side+'_knee_pitch').id
        model.jnt_range[knee_joint]=[-2.5,2.5]
        model.actuator_ctrlrange[knee_actuator]=[-2.5,2.5]
        print('Temporary '+side+'_knee_pitch range: [-2.5, 2.5] rad', flush=True)
if '--neck-adjust' in sys.argv:
    neck_joint=model.joint('neck_pitch_joint').id
    neck_actuator=model.actuator('neck_pitch').id
    model.jnt_range[neck_joint]=[-1.3,1.8]
    model.actuator_ctrlrange[neck_actuator]=[-1.3,1.8]
    print('Temporary neck_pitch range: [-1.3, 1.8] rad', flush=True)
if '--upper-cover' in sys.argv:
    for i in np.flatnonzero(model.geom_group == 2):
        if model.geom(i).name != 'new_Upper_Cover_Battery_Opening':
            model.geom_rgba[i,3] = .045
if '--highlight' in sys.argv:
    for name in ('new_CAD_Head_Pitch_Output','new_CAD_Head_Yaw_Output'):
        geom=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_GEOM,name)
        if geom >= 0: model.geom_rgba[geom]=[1,.04,.02,1]
key_name='ANKLE_ZERO_CHECK' if '--ankle-zero' in sys.argv else ('MECHANICAL_ZERO' if '--zero' in sys.argv else ('HOME' if '--home' in sys.argv else 'ASSEMBLY_INITIAL'))
home=mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_KEY,key_name)
mujoco.mj_resetDataKeyframe(model,data,home)
mujoco.mj_forward(model,data)
# For this visual inspection mode, the purple Control sliders set joint
# angles directly. This avoids running the provisional collision/inertia model.
joint_ids = model.actuator_trnid[:,0].copy()
assert all(model.actuator_trntype[i] == mujoco.mjtTrn.mjTRN_JOINT for i in range(model.nu))
assert all(model.jnt_type[j] == mujoco.mjtJoint.mjJNT_HINGE and model.jnt_limited[j] for j in joint_ids)
qpos_ids = model.jnt_qposadr[joint_ids]
model.actuator_ctrlrange[:,:] = model.jnt_range[joint_ids,:]
data.ctrl[:] = np.clip(data.qpos[qpos_ids],model.actuator_ctrlrange[:,0],model.actuator_ctrlrange[:,1])
collision_mode = any(a in sys.argv for a in ['--collision','--overlay','--self-collision','--train-model'])
if '--overlay' in sys.argv:
    model.geom_rgba[model.geom_group == 2,3] = .12
collision_ids = np.flatnonzero(np.isin(model.geom_group,[3,4]) & (model.geom_contype != 0))
if collision_mode:
    model.vis.scale.contactwidth = .006
    model.vis.scale.contactheight = .003
    for geom_id in collision_ids:
        body_name=model.body(model.geom_bodyid[geom_id]).name
        color=[.08,.72,1,.8]
        if body_name=='head_roll': color=[.35,.9,.46,.8]
        elif body_name in ('neck_pitch','head_pitch','head_yaw'): color=[1,.72,.22,.8]
        elif body_name in ('Battery','IMU','control-box','power-strip'): color=[.7,.4,1,.6]
        elif 'ankle' in body_name: color=[.95,.36,.14,.8]
        if model.geom_group[geom_id]==4: color=[.7,.25,.9,.35]
        if '--self-collision' in sys.argv and not (model.geom_contype[geom_id]&4): color[3]=0
        model.geom_rgba[geom_id]=color
collision_colors = model.geom_rgba[collision_ids].copy()
with mujoco.viewer.launch_passive(model,data) as viewer:
    viewer.cam.lookat[:]=[-.02,0,.30]
    viewer.cam.distance=1.0
    viewer.cam.azimuth=140
    viewer.cam.elevation=-14
    if '--upper-cover' in sys.argv:
        viewer.cam.lookat[:]=[-.095,0,.33]
        viewer.cam.distance=.43
        viewer.cam.azimuth=145
        viewer.cam.elevation=-36
    if '--ankle-zero' in sys.argv:
        viewer.cam.lookat[:]=[-.045,.125,.11]
        viewer.cam.distance=.37
        viewer.cam.azimuth=-90
        viewer.cam.elevation=-4
    if collision_mode:
        viewer.opt.geomgroup[2] = '--overlay' in sys.argv
        viewer.opt.geomgroup[3] = True
        viewer.opt.geomgroup[4] = '--self-collision' in sys.argv
        viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONVEXHULL] = True
        viewer.opt.flags[mujoco.mjtVisFlag.mjVIS_CONTACTPOINT] = False
    while viewer.is_running():
        viewer.sync()
        with viewer.lock():
            data.qpos[qpos_ids] = np.clip(data.ctrl,model.actuator_ctrlrange[:,0],model.actuator_ctrlrange[:,1])
            mujoco.mj_forward(model,data)
            if collision_mode:
                model.geom_rgba[collision_ids] = collision_colors
                for contact in data.contact:
                    if contact.dist < -.0001 and model.geom_bodyid[contact.geom1] and model.geom_bodyid[contact.geom2]:
                        model.geom_rgba[contact.geom1] = [1,.08,.12,.9]
                        model.geom_rgba[contact.geom2] = [1,.08,.12,.9]
        time.sleep(1/30)
