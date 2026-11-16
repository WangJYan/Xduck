"""API-v2: heading_start400 heading-start-phase61-v6 Walk; head-adjust pilot32 solver4 V1.1.4 Stand.
Stand uses exactly one policy-frame velocity buffer; normalization is in ONNX.
Walk retains the original v5 observation, scaling and velocity history.
"""

import numpy as np

JOINTS = [
    "left_hip_yaw",
    "left_hip_roll",
    "left_hip_pitch",
    "left_knee",
    "left_ankle",
    "right_hip_yaw",
    "right_hip_roll",
    "right_hip_pitch",
    "right_knee",
    "right_ankle",
    "neck_pitch",
    "head_pitch",
    "head_yaw",
    "head_roll",
    "mouth",
]
CONTROLLED = [name for name in JOINTS if name != "mouth"]
TRAINING_JOINTS = [
    "left_hip_yaw",
    "left_hip_roll",
    "left_hip_pitch",
    "left_knee",
    "left_ankle",
    "neck_pitch",
    "head_pitch",
    "head_yaw",
    "head_roll",
    "right_hip_yaw",
    "right_hip_roll",
    "right_hip_pitch",
    "right_knee",
    "right_ankle",
]
TRAINING_INDEX = [JOINTS.index(name) for name in TRAINING_JOINTS]

WALK_REFERENCE = np.asarray(
    [
        0.0,
        0.0,
        0.384,
        0.0,
        -0.384,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        -0.384,
        0.0,
        0.384,
    ],
    dtype=np.float32,
)
STAND_REFERENCE = np.asarray(
    [
        0.0,
        0.07999999821186066,
        0.39399999380111694,
        -0.061000000685453415,
        -0.45500001311302185,
        0.01899999938905239,
        0.05999999865889549,
        0.0,
        0.0,
        0.0,
        -0.07999999821186066,
        -0.39399999380111694,
        0.061000000685453415,
        0.45500001311302185,
    ],
    dtype=np.float64,
)
TARGET_LOW = np.asarray(
    [
        -1.19,
        -0.11,
        -2.99,
        -1.19,
        -1.49,
        -0.29,
        -1.19,
        -1.99,
        -0.49,
        -0.49,
        -1.19,
        -2.99,
        -1.49,
        -1.29,
    ],
    dtype=np.float32,
)
TARGET_HIGH = np.asarray(
    [
        0.49,
        1.49,
        2.99,
        1.39,
        1.29,
        1.29,
        1.19,
        1.99,
        0.49,
        1.19,
        0.19,
        1.99,
        1.29,
        1.49,
    ],
    dtype=np.float32,
)

# flex_adapt_50 action-to-radian mapping in training joint order.
WALK_ACTION_SCALE = np.asarray(
    [
        0.12,
        0.03666666666666667,
        0.12,
        0.12,
        0.12,
        0.09666666666666666,
        0.12,
        0.12,
        0.12,
        0.12,
        0.03666666666666667,
        0.12,
        0.12,
        0.12,
    ],
    dtype=np.float32,
)
# Stand stand2200_v114 uses target-history units of .12, not an output position scale.
STAND_HISTORY_SCALE = 0.12
STAND_INCREMENT = np.asarray(
    [0.015, 0.01, 0.08, 0.06, 0.075, 0.11, 0.025, 0.025, 0.01, 0.015, 0.01, 0.08, 0.06, 0.075],
    dtype=np.float64,
)
STAND_TARGET_LOW = np.asarray(
    [
        -1.19,
        -0.11000000178813935,
        -2.9900000061988834,
        -1.1900000006854534,
        -1.4900000131130215,
        -0.2900000006109476,
        -1.1900000013411045,
        -1.99,
        -0.49,
        -0.49,
        -1.1899999982118605,
        -2.989999993801117,
        -1.4899999993145465,
        -1.2899999868869783,
    ],
    dtype=np.float64,
)
STAND_TARGET_HIGH = np.asarray(
    [
        0.49,
        1.4899999982118606,
        2.989999993801117,
        1.3899999993145464,
        1.2899999868869783,
        1.2899999993890525,
        1.1899999986588954,
        1.99,
        0.49,
        1.19,
        0.19000000178813936,
        1.9900000061988834,
        1.2900000006854535,
        1.4900000131130215,
    ],
    dtype=np.float64,
)

KP = np.asarray(
    [90, 90, 75, 100, 90, 75, 90, 75, 90, 90, 90, 75, 100, 90],
    dtype=np.float32,
)
KD = np.asarray(
    [2.5, 2.5, 2.5, 3.0, 3.0, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 3.0, 3.0],
    dtype=np.float32,
)

CONTROL_DT = 0.02
ACTION_FILTER_ALPHA = 1.0


def command_obs(frame):
    action = frame["policy_context"]["action"]
    if action == "stand":
        return np.zeros(13, dtype=np.float32)
    if action != "walk":
        raise ValueError("v6 locomotion policy requires walk or stand action")
    command = frame["command"]
    twist = [0.0, 0.0, 0.0] if frame["policy_context"]["body_active"] else command["twist"]
    return np.asarray(
        [
            *twist,
            *command["head"],
            0.0,
            0.0,
            *command["body"],
            0.0,
        ],
        dtype=np.float32,
    )


# API-v2 documents attitude_rpy (rad) and imu.quat [w,x,y,z].
def body_yaw(frame):
    rpy = frame.get("attitude_rpy")
    if rpy is not None:
        values = np.asarray(rpy, dtype=np.float64)
        if values.shape != (3,) or not np.isfinite(values).all():
            raise ValueError("attitude_rpy must contain three finite radians")
        return float(values[2])
    quat = frame["imu"].get("quat")
    if quat is None:
        raise ValueError("Walk requires API-v2 attitude_rpy or imu.quat [w,x,y,z]")
    values = np.asarray(quat, dtype=np.float64)
    if values.shape != (4,) or not np.isfinite(values).all():
        raise ValueError("imu.quat must contain four finite values [w,x,y,z]")
    norm = float(np.linalg.norm(values))
    if norm < 1e-8:
        raise ValueError("imu.quat must have nonzero norm")
    w, x, y, z = values / norm
    return float(np.arctan2(2.0 * (w*z + x*y), 1.0 - 2.0 * (y*y + z*z)))


def wrap_angle(value):
    return np.arctan2(np.sin(value), np.cos(value))

PHASE_MEAN = np.asarray([9.00035520317033e-05, -5.495280220202403e-06], dtype=np.float64)
PHASE_SCALE = np.asarray([0.038859352469444275, 0.03886078670620918], dtype=np.float64)


class HeadingAdapter:
 def __init__(self,n,kp=.8,rate_limit=.6):
  self.reference=np.zeros(n);self.kp=kp;self.rate_limit=rate_limit
 def reset(self,ids,body_yaw):self.reference[np.asarray(ids,dtype=int)]=body_yaw
 def step(self,body_yaw,user_yaw_rate,dt=.02,enabled=True):
  self.reference=wrap_angle(self.reference+np.asarray(user_yaw_rate)*dt)
  error=wrap_angle(np.asarray(body_yaw)-self.reference)
  effective=np.asarray(user_yaw_rate)-np.asarray(enabled)*self.kp*error
  return np.clip(effective,-self.rate_limit,self.rate_limit),error


class TaskAdapter:
 def __init__(self,n,mean,scale,goal=.15,variable=False):
  self.age=np.zeros(n);self.phase=np.zeros(n);self.mean=np.asarray(mean);self.scale=np.asarray(scale);self.goal=goal;self.variable=variable;self.heading=HeadingAdapter(n);self.side_age=np.zeros(n);self.was_side=np.zeros(n,bool);self.heading_error=np.zeros(n);self.last_requested=np.zeros((n,3));self.start_mean=-9.551364200888202e-06;self.start_scale=.012883138600736857;self.heading_mean=np.array([1.4711259836985846e-06,2.4759025109233335e-05]);self.heading_scale=np.array([.01288898404687643,.03884611673653126])
 def reset(self,ids,yaw,offset=0.):
  ids=np.asarray(ids,int);self.age[ids]=0;self.phase[ids]=offset;self.heading.reset(ids,yaw);self.side_age[ids]=0;self.was_side[ids]=False;self.heading_error[ids]=0;self.last_requested[ids]=0
 def encode(self):return self.mean+self.scale*np.c_[np.sin(2*np.pi*self.phase),np.cos(2*np.pi*self.phase)]
 def encode_task(self):return np.c_[self.start_mean+self.start_scale*np.clip(self.age/.5,0,1),self.heading_mean+self.heading_scale*np.c_[np.cos(self.heading_error),np.sin(self.heading_error)]]
 def advance(self,yaw,requested,dt=.02,feedback=False):
  requested=np.asarray(requested)
  old_key=np.where(np.abs(self.last_requested)>.05,np.sign(self.last_requested),0);new_key=np.where(np.abs(requested)>.05,np.sign(requested),0)
  active=np.any(new_key!=0,axis=1);was_active=np.any(old_key!=0,axis=1);start=active&np.any(old_key!=new_key,axis=1)
  self.age[start]=0;fresh=np.flatnonzero(active&(~was_active))
  if len(fresh):self.heading.reset(fresh,np.asarray(yaw)[fresh])
  self.last_requested[:]=requested
  interval=np.where(np.abs(requested[:,0])>.05,np.clip(self.goal/np.maximum(np.abs(requested[:,0]),.05),.35,.65),.5) if self.variable else .5
  self.age+=dt
  side=np.abs(requested[:,1])>.05;new=side&(~self.was_side);self.side_age[new]=0;self.phase[new]=np.where(requested[new,1]>0,.5,0.)
  self.side_age[side]+=dt;self.was_side=side
  moving=(np.linalg.norm(requested[:,:2],axis=1)>.05)|(np.abs(requested[:,2])>.05)
  self.phase=(self.phase+moving*dt/(2*interval))%1
  effective,error=self.heading.step(yaw,requested[:,2],dt,feedback);self.heading_error[:]=error;return effective,error
 def adapt_observation(self,obs,body_yaw,requested,dt=.02,heading_hold=False):
  if heading_hold:raise ValueError('Heading correction is inside this ONNX; use heading_hold=False')
  effective,error=self.advance(body_yaw,requested,dt,False);out=np.array(obs,copy=True);out[:,48:51]=requested;out[:,51:56]=0;out[:,56:59]=self.encode_task();out[:,50]=effective;out[:,59:61]=self.encode();return out

HEAD=np.array([5,6,7,8]);LEGS=np.array([0,1,2,3,4,9,10,11,12,13])
FINAL_LOW=np.array([-.25,-.6,-1.2,-.25]);FINAL_HIGH=np.array([.6,.6,1.2,.25]);RATE=np.array([.4,.5,.6,.25])
class HeadCommandState:
 def __init__(self,n):self.hold=np.zeros(n);self.normal=np.zeros(n,bool);self.effective=np.zeros((n,4));self.gyro_ema=np.zeros((n,3));self.velocity_ema=np.zeros((n,14));self.fresh=np.ones(n,bool)
 def reset(self,ids):self.hold[ids]=0.;self.normal[ids]=False;self.effective[ids]=0.;self.gyro_ema[ids]=0.;self.velocity_ema[ids]=0.;self.fresh[ids]=True
 def step(self,gravity,gyro,velocity,joint_rel,request,permission,dt=.02):
  self.gyro_ema[self.fresh]=gyro[self.fresh];self.velocity_ema[self.fresh]=velocity[self.fresh];self.fresh[:]=False
  self.gyro_ema+=(np.asarray(gyro)-self.gyro_ema)*(1-np.exp(-dt/.2));self.velocity_ema+=(np.asarray(velocity)-self.velocity_ema)*(1-np.exp(-dt/.15))
  g=np.asarray(gravity);norm=np.linalg.norm(g,axis=1);tilt=np.degrees(np.arccos(np.clip(-g[:,2]/np.maximum(norm,1e-8),-1,1)));omega=np.linalg.norm(self.gyro_ema,axis=1);leg=np.sqrt(np.mean(self.velocity_ema[:,LEGS]**2,axis=1));pose=np.sqrt(np.mean(joint_rel[:,LEGS]**2,axis=1))
  valid=permission&np.isfinite(g).all(1)&np.isfinite(gyro).all(1)&np.isfinite(velocity).all(1)&(norm>.8)&(norm<1.2)
  yaw_follow=np.abs(request[:,2])>.005
  raw_omega=np.linalg.norm(gyro,axis=1);raw_xy=np.linalg.norm(np.asarray(gyro)[:,:2],axis=1);ema_xy=np.linalg.norm(self.gyro_ema[:,:2],axis=1)
  safe_fast=np.where(yaw_follow,(raw_xy<.9)&(np.abs(np.asarray(gyro)[:,2])<1.8),raw_omega<.9)
  safe_average=np.where(yaw_follow,(ema_xy<.65)&(np.abs(self.gyro_ema[:,2])<.8),omega<.65)
  enter=valid&(tilt<8)&(omega<.4)&(leg<.6)&(pose<.3)&safe_fast;keep=valid&(tilt<12)&safe_fast&safe_average&(leg<.9)&(pose<.45)
  self.normal&=keep;self.hold=np.where(enter,self.hold+dt,0.);self.normal|=(self.hold>=.6-1e-9)&keep
  self.effective+=np.clip(request-self.effective,-RATE*dt,RATE*dt);self.effective[~self.normal]=0.
  return self.effective


class Policy:
    def describe(self):
        return {
            "api_version": 2,
            "period_us": 20_000,
            "required_sources": ["joints", "imu", "command", "policy_context"],
            "inputs": {"obs": {"dtype": "float32", "shape": [1, 61]}},
            "outputs": {"actions": {"dtype": "float32", "shape": [1, 14]}},
            "controlled_joints": CONTROLLED,
        }

    def reset(self, robot_info, first_frame):
        if robot_info["joint_names"] != JOINTS:
            raise ValueError("joint order does not match the XDuck API-v2 contract")
        self.head_state = HeadCommandState(1)
        self.last_raw_action = np.zeros(14, dtype=np.float32)
        # Startup has no outgoing controller target. Use measured joint angles.
        # Normal Walk/Stand transitions keep this state and inherit the last
        # clipped commanded target; never snap to the standing reference.
        self.last_commanded_target = np.asarray(first_frame["positions"], dtype=np.float64)[
            TRAINING_INDEX
        ].copy()
        if first_frame["policy_context"]["action"] == "stand":
            self.last_commanded_target = np.clip(
                self.last_commanded_target, STAND_TARGET_LOW, STAND_TARGET_HIGH
            )
        if first_frame["policy_context"]["action"] == "walk":
            self.last_commanded_target = np.clip(self.last_commanded_target, TARGET_LOW, TARGET_HIGH)
        self.last_mode = None
        self.walk_adapter_active = False
        self.walk_adapter = TaskAdapter(1, PHASE_MEAN, PHASE_SCALE, goal=0.1, variable=True)
        velocity = np.asarray(first_frame["velocities"], dtype=np.float32)
        self.previous_velocity = velocity[TRAINING_INDEX].copy()

    @staticmethod
    def reference(frame):
        action = frame["policy_context"]["action"]
        if action == "walk":
            return WALK_REFERENCE
        if action == "stand":
            return STAND_REFERENCE
        raise ValueError("v6 locomotion policy requires walk or stand action")

    def preprocess(self, frame, feedback):
        # API feedback carries the outgoing controller's requested targets.
        # Prefer it on Stand frames when available, preserving any downstream
        # target adjustment exposed through this feedback contract.
        mode = frame["policy_context"]["action"]
        if mode != "walk":
            self.walk_adapter_active = False
        # On first Walk activation, prefer the incoming real PD target
        # over measured position. Regular Walk keeps its raw action history.
        if (mode == "stand" or self.last_mode is None) and feedback is not None:
            targets = feedback.get("requested_targets", {})
            if "requested_targets" in feedback and not all(
                name in targets for name in TRAINING_JOINTS
            ):
                raise ValueError("Handoff feedback must contain all 14 requested targets")
            if all(name in targets for name in TRAINING_JOINTS):
                commanded = np.asarray(
                    [targets[name]["position"] for name in TRAINING_JOINTS],
                    dtype=np.float64,
                )
                if not np.isfinite(commanded).all():
                    raise ValueError("Previous commanded targets must be finite")
                low, high = (STAND_TARGET_LOW, STAND_TARGET_HIGH) if mode == "stand" else (TARGET_LOW, TARGET_HIGH)
                self.last_commanded_target = np.clip(commanded, low, high)
        positions = np.asarray(frame["positions"], dtype=np.float32)[TRAINING_INDEX]
        current_velocity = np.asarray(frame["velocities"], dtype=np.float32)[TRAINING_INDEX]
        delayed_velocity = self.previous_velocity
        self.previous_velocity = current_velocity.copy()
        if frame["policy_context"]["action"] == "stand":
            # V1.1.4 stand2200 explicitly requires previous policy-frame qd.
            # Reuse delayed_velocity from the shared buffer, never add a second buffer.
            q = np.asarray(frame["positions"], dtype=np.float64)[TRAINING_INDEX]
            qd = delayed_velocity.astype(np.float64)
            if self.last_mode != "stand":
                self.head_state.reset(np.asarray([0]))
            request = np.asarray(frame["command"]["head"], dtype=np.float64)
            if request.shape != (4,) or not np.isfinite(request).all():
                raise ValueError("Head command must contain four finite radian offsets")
            request = np.clip(request, FINAL_LOW, FINAL_HIGH)
            command = frame["command"]
            permitted = (not frame["policy_context"]["body_active"]
                         and np.max(np.abs(command["twist"])) < 1e-6
                         and np.max(np.abs(command["body"])) < 1e-6)
            effective = self.head_state.step(
                np.asarray(frame["imu"]["gravity"], dtype=np.float64)[None],
                np.asarray(frame["imu"]["gyro"], dtype=np.float64)[None],
                np.asarray(frame["velocities"], dtype=np.float64)[TRAINING_INDEX][None],
                (q - STAND_REFERENCE)[None], request[None], np.asarray([permitted]),
            )
            stand_commands = np.zeros(13, dtype=np.float64)
            stand_commands[3:7] = effective[0]
            obs = np.concatenate(
                [
                    np.asarray(frame["imu"]["gyro"], dtype=np.float64),
                    np.asarray(frame["imu"]["gravity"], dtype=np.float64),
                    q - STAND_REFERENCE,
                    qd,
                    (self.last_commanded_target - STAND_REFERENCE) / STAND_HISTORY_SCALE,
                    stand_commands,
                ]
            ).astype(np.float32)
            if not np.isfinite(obs).all():
                raise ValueError("Stand observation must be finite")
            return {"obs": obs.reshape(1, 61)}
        reference = self.reference(frame)
        mode = frame["policy_context"]["action"]
        if mode == "stand":
            # Incremental Stand's observation contains executed target memory,
            # including saturation, and never the raw neural-network output.
            last_action = (self.last_commanded_target - reference) / STAND_HISTORY_SCALE
        elif self.last_mode is None:
            # Training starts with the actual standing PD target encoded
            # in Walk units; zero history would describe a different target.
            last_action = (self.last_commanded_target - reference) / WALK_ACTION_SCALE
        elif mode == self.last_mode:
            last_action = self.last_raw_action
        else:
            # Stand-to-Walk handoff expresses the preceding executed target
            # in Walk's reference and raw-action units.
            last_action = (self.last_commanded_target - reference) / WALK_ACTION_SCALE
        obs = np.concatenate(
            [
                np.asarray(frame["imu"]["gyro"], dtype=np.float32),
                np.asarray(frame["imu"]["gravity"], dtype=np.float32),
                positions - reference,
                delayed_velocity,
                last_action,
                command_obs(frame),
            ]
        ).astype(np.float32)
        yaw = body_yaw(frame)
        requested = np.asarray(obs[48:51], dtype=np.float64)
        if not self.walk_adapter_active:
            self.walk_adapter.reset([0], [yaw])
            self.walk_adapter_active = True
            dt = 0.0
        else:
            dt = float(frame.get("dt", CONTROL_DT))
            if not np.isfinite(dt) or dt <= 0.0:
                raise ValueError("frame.dt must be finite positive seconds")
        # ONNX owns heading correction. Pass raw user yaw rate through
        # the supplied adapter's feedback=False path (with its +/-0.6 clamp).
        obs = self.walk_adapter.adapt_observation(
            obs.reshape(1, 61), np.asarray([yaw]), requested.reshape(1, 3),
            dt=dt, heading_hold=False,
        )
        return {"obs": obs.reshape(1, 61)}

    def postprocess(self, outputs, frame):
        action = np.asarray(outputs["actions"], dtype=np.float32).reshape(14)
        mode = frame["policy_context"]["action"]
        if not np.isfinite(action).all():
            raise ValueError("Model output must be finite")
        if mode == "walk":
            absolute_target = WALK_REFERENCE + WALK_ACTION_SCALE * action
            target = np.clip(absolute_target, TARGET_LOW, TARGET_HIGH)
            target[5:9] = 0.0  # Package contract: four head joints fixed at zero.
        elif mode == "stand":
            absolute_target = self.last_commanded_target + STAND_INCREMENT * np.tanh(
                action.astype(np.float64)
            )
            target = np.clip(absolute_target, STAND_TARGET_LOW, STAND_TARGET_HIGH)
        else:
            raise ValueError("v6 locomotion policy requires walk or stand action")
        # Walk keeps raw action history within its own mode; Stand keeps the
        # actual commanded target used by the incremental integrator.
        self.last_raw_action = action.copy()
        self.last_commanded_target = target.copy()
        self.last_mode = mode
        by_name = {}
        for slot, name in enumerate(TRAINING_JOINTS):
            by_name[name] = {
                "position": float(target[slot]),
                "velocity": 0.0,
                "torque_ff": 0.0,
                "kp": float(KP[slot]),
                "kd": float(KD[slot]),
            }
        return {name: by_name[name] for name in CONTROLLED}
