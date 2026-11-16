"""Standalone API-v2 Walk/Stand consumer from backward_stop_yaw_hold review.
Supplied network decoding and transition control are preserved. NumPy only.
Host must supply the outgoing controller target on cross-policy handoff.
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
# Stand actor61_1500 uses target-history units of .12, not an output position scale.
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


class _BasePolicy:
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
        self.last_mode = None
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
        if frame["policy_context"]["action"] == "stand" and feedback is not None:
            targets = feedback.get("requested_targets", {})
            if all(name in targets for name in TRAINING_JOINTS):
                commanded = np.asarray(
                    [targets[name]["position"] for name in TRAINING_JOINTS],
                    dtype=np.float64,
                )
                if not np.isfinite(commanded).all():
                    raise ValueError("Previous commanded targets must be finite")
                self.last_commanded_target = commanded
        positions = np.asarray(frame["positions"], dtype=np.float32)[TRAINING_INDEX]
        current_velocity = np.asarray(frame["velocities"], dtype=np.float32)[TRAINING_INDEX]
        delayed_velocity = self.previous_velocity
        self.previous_velocity = current_velocity.copy()
        if frame["policy_context"]["action"] == "stand":
            # The new deployment contract requires current sensors. Retain
            # previous_velocity above solely for the unchanged Walk path.
            q = np.asarray(frame["positions"], dtype=np.float64)[TRAINING_INDEX]
            qd = np.asarray(frame["velocities"], dtype=np.float64)[TRAINING_INDEX]
            obs = np.concatenate(
                [
                    np.asarray(frame["imu"]["gyro"], dtype=np.float64),
                    np.asarray(frame["imu"]["gravity"], dtype=np.float64),
                    q - STAND_REFERENCE,
                    qd,
                    (self.last_commanded_target - STAND_REFERENCE) / STAND_HISTORY_SCALE,
                    np.zeros(13, dtype=np.float64),
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
            last_action = np.zeros(14, dtype=np.float32)
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
        return {"obs": obs.reshape(1, 61)}

    def postprocess(self, outputs, frame):
        action = np.asarray(outputs["actions"], dtype=np.float32).reshape(14)
        mode = frame["policy_context"]["action"]
        if not np.isfinite(action).all():
            raise ValueError("Model output must be finite")
        if mode == "walk":
            absolute_target = WALK_REFERENCE + WALK_ACTION_SCALE * action
            target = np.clip(absolute_target, TARGET_LOW, TARGET_HIGH)
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


class Policy(_BasePolicy):
    def __init__(self, config=None):
        if config is None:
            config={'duration_s': 0.6, 'gyro_gain': 1.0, 'qd_gain': 1.0, 'roll_damping_s': 0.048, 'pitch_damping_s': 0.0, 'roll_axis_sign': [-1.0, -1.0], 'pitch_axis_sign': [-1.0, 1.0], 'backward': {'duration_s': 0.4, 'roll_damping_s': 0.048, 'yaw_damping_s': 0.048, 'yaw_hold_s': 0.6, 'yaw_end_s': 1.6, 'yaw_proportional': 0.16, 'yaw_offset_limit_rad': 0.16}, 'activation': 'Actual walk->stand only; last nonzero Walk vx<-.05 selects the backward profile. Temporary integrated heading feedback uses measured gyro and gravity. Initial/steady Stand and forward/turn profiles are unchanged.', 'walk_model_sha256': '944aeeb39c7fb568c80bd970c779776c4f3f8809183fd11910cfc1934ad67fc1', 'stand_model_sha256': '5cba99e9babc06a82d54cdee5fa4827c7c18788096fbb792f8a20dd2896ae2c3'}
        self.config=dict(config)
        self.last_moving_twist=np.zeros(3)
        self._apply_profile({})
        self.stop_age=None
        self.previous_offset=np.zeros(14)
        self.yaw_error=0.

    def _apply_profile(self,profile):
        config={**self.config,**profile}
        self.duration=float(config.get('duration_s',0.))
        self.gyro_gain=float(config.get('gyro_gain',1.))
        self.qd_gain=float(config.get('qd_gain',1.))
        self.damping=float(config.get('roll_damping_s',0.))
        self.pitch_damping=float(config.get('pitch_damping_s',0.))
        self.yaw_damping=float(config.get('yaw_damping_s',0.))
        self.yaw_proportional=float(config.get('yaw_proportional',0.))
        self.yaw_offset_limit=float(config.get('yaw_offset_limit_rad',float('inf')))
        self.pitch_hold=float(config.get('pitch_hold_s',0.))
        self.pitch_end=float(config.get('pitch_end_s',self.duration))
        self.yaw_hold=float(config.get('yaw_hold_s',0.))
        self.yaw_end=float(config.get('yaw_end_s',self.duration))
        self.roll_sign=np.asarray(config.get('roll_axis_sign',[-1.,-1.]),dtype=float)
        self.pitch_sign=np.asarray(config.get('pitch_axis_sign',[-1.,1.]),dtype=float)
        self.yaw_sign=np.asarray(config.get('yaw_axis_sign',[1.,1.]),dtype=float)

    def reset(self,robot_info,first_frame):
        super().reset(robot_info,first_frame)
        self.stop_age=None
        self.previous_offset.fill(0.)
        self.last_moving_twist.fill(0.)
        self.yaw_error=0.
        self._apply_profile({})

    def window(self):
        return self.axis_window(0.,self.duration)

    def axis_window(self,hold,end):
        if self.stop_age is None or end<=hold:return 0.
        u=float(np.clip((self.stop_age-hold)/(end-hold),0.,1.))
        return 1.-u**3*(10.+u*(-15.+6.*u))

    def preprocess(self,frame,feedback):
        mode=frame['policy_context']['action']
        if mode=='walk':
            self.yaw_error=0.
            self.stop_age=None
            self.previous_offset.fill(0.)
            twist=command_obs(frame)[:3]
            if np.linalg.norm(twist)>1e-3:self.last_moving_twist=twist.copy()
        elif mode=='stand' and self.last_mode=='walk':
            backward=self.last_moving_twist[0]<-.05
            self._apply_profile(self.config.get('backward',{}) if backward else {})
            self.stop_age=0.
            self.yaw_error=0.
            self.previous_offset.fill(0.)
        outputs=super().preprocess(frame,feedback)
        window=self.window()
        if mode=='stand' and window>0:
            obs=outputs['obs'].copy()
            obs[:,:3]*=1.+(self.gyro_gain-1.)*window
            obs[:,20:34]*=1.+(self.qd_gain-1.)*window
            outputs={'obs':obs}
        return outputs

    def postprocess(self,outputs,frame):
        mode=frame['policy_context']['action']
        if mode=='stand' and (self.damping!=0. or self.pitch_damping!=0. or self.yaw_damping!=0. or self.yaw_proportional!=0. or np.any(self.previous_offset)):
            action=np.asarray(outputs['actions'],dtype=np.float32).reshape(14)
            if not np.isfinite(action).all():raise ValueError('Model output must be finite')
            offset=np.zeros(14)
            offset[[1,10]]=self.damping*self.window()*float(frame['imu']['gyro'][0])*self.roll_sign
            offset[[2,11]]=self.pitch_damping*self.axis_window(self.pitch_hold,self.pitch_end)*float(frame['imu']['gyro'][1])*self.pitch_sign
            yaw_offset=np.clip(self.yaw_damping*float(frame['imu']['gyro'][2])+self.yaw_proportional*self.yaw_error,-self.yaw_offset_limit,self.yaw_offset_limit)
            offset[[0,9]]=yaw_offset*self.axis_window(self.yaw_hold,self.yaw_end)*self.yaw_sign
            target=np.clip(self.last_commanded_target+STAND_INCREMENT*np.tanh(action.astype(float))+offset-self.previous_offset,STAND_TARGET_LOW,STAND_TARGET_HIGH)
            self.previous_offset=offset
            self.last_raw_action=action.copy()
            self.last_commanded_target=target.copy()
            self.last_mode=mode
            by_name={name:dict(position=float(target[j]),velocity=0.,torque_ff=0.,kp=float(KP[j]),kd=float(KD[j])) for j,name in enumerate(TRAINING_JOINTS)}
            result={name:by_name[name] for name in CONTROLLED}
        else:
            result=super().postprocess(outputs,frame)
        if mode=='stand' and self.stop_age is not None:
            gravity=np.asarray(frame['imu']['gravity'],dtype=float)
            gyro=np.asarray(frame['imu']['gyro'],dtype=float)
            roll=np.arctan2(-gravity[1],-gravity[2])
            pitch=np.arctan2(gravity[0],np.hypot(gravity[1],gravity[2]))
            heading_rate=(gyro[1]*np.sin(roll)+gyro[2]*np.cos(roll))/max(float(np.cos(pitch)),.5)
            self.yaw_error+=float(heading_rate)*CONTROL_DT
            self.stop_age+=CONTROL_DT
            end=max(self.duration,self.pitch_end if self.pitch_damping else 0.,self.yaw_end if (self.yaw_damping or self.yaw_proportional) else 0.)
            if self.stop_age>=end+CONTROL_DT and not np.any(self.previous_offset):self.stop_age=None
        return result
