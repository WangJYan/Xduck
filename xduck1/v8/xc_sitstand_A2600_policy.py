"""API-v2 A2600 rigid Sit/Rise consumer; persistent supplied SitGovernor.
Standalone: NumPy only, no external config or model loading.
20ms velocity history matches training. Reset only on takeover/physical reset.
"""

from types import SimpleNamespace

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

# Exact values supplied in policy_io.json, in training order.
DEFAULT_ANGLES = np.asarray(
    [
        0,
        0.07999999821186066,
        0.39399999380111694,
        -0.061000000685453415,
        -0.45500001311302185,
        0.01899999938905239,
        0.05999999865889549,
        0,
        0,
        0,
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
        -0.11000000178813935,
        -2.990000003198883,
        -1.1900000006854534,
        -1.4900000161130218,
        -0.2900000006109476,
        -1.1900000013411045,
        -1.99,
        -0.49,
        -0.49,
        -1.1899999982118608,
        -2.989999996801117,
        -1.4899999993145465,
        -1.2899999838869782,
    ],
    dtype=np.float64,
)
TARGET_HIGH = np.asarray(
    [
        0.49,
        1.4899999982118606,
        2.989999996801117,
        1.3899999993145467,
        1.2899999838869782,
        1.2899999993890523,
        1.1899999986588954,
        1.99,
        0.49,
        1.19,
        0.19000000178813936,
        1.9900000031988831,
        1.2900000006854535,
        1.4900000161130218,
    ],
    dtype=np.float64,
)
INCREMENT = np.asarray(
    [
        0.015,
        0.010,
        0.080,
        0.060,
        0.075,
        0.110,
        0.025,
        0.025,
        0.010,
        0.015,
        0.010,
        0.080,
        0.060,
        0.075,
    ],
    dtype=np.float64,
)
HISTORY_SCALE = 0.12
KP = np.asarray([90, 90, 75, 100, 90, 75, 90, 75, 90, 90, 90, 75, 100, 90], dtype=np.float64)
KD = np.asarray([2.5, 2.5, 2.5, 3, 3, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 3, 3], dtype=np.float64)
CONTROL_DT = 0.02


class SitGovernor:
    def __init__(self, count, dt, default_angles, sit_legs, cfg):
        self.cfg = cfg
        self.default_angles = np.asarray(default_angles)
        self.sit_legs = np.asarray(sit_legs)
        self.cooldown = np.zeros(count)
        self.recovering = np.zeros(count, dtype=bool)
        self.armed = np.zeros(count, dtype=bool)
        self.dt = dt
        self.age = np.zeros(count)
        self.strength = np.zeros(count)
        self.previous = np.zeros((count, 5))
        self.valid = np.zeros(count, dtype=bool)
        self.legs = np.array([0, 1, 2, 3, 4, 9, 10, 11, 12, 13])
        self.filtered_gyro = np.zeros((count, 3))
        self.filtered_leg = np.zeros((count, 10))
        self.filtered_gravity = np.zeros((count, 3))
        self.fast_gyro = np.zeros((count, 3))
        self.fast_leg = np.zeros((count, 10))
        self.filter_valid = np.zeros(count, dtype=bool)
        self.last_stable = np.zeros(count, dtype=bool)
        self.last_release = np.zeros(count, dtype=bool)
        self.last_hold = np.zeros(count, dtype=bool)

    def reset(self, ids):
        self.age[ids] = 0.0
        self.strength[ids] = 0.0
        self.valid[ids] = False
        self.cooldown[ids] = 0.0
        self.recovering[ids] = False
        self.armed[ids] = False
        self.filter_valid[ids] = False
        self.filtered_gyro[ids] = 0.0
        self.filtered_leg[ids] = 0.0
        self.filtered_gravity[ids] = 0.0
        self.fast_gyro[ids] = 0.0
        self.fast_leg[ids] = 0.0
        self.last_stable[ids] = False
        self.last_release[ids] = False
        self.last_hold[ids] = False

    def update(self, obs, alpha):
        gravity = obs[:, 3:6]
        tilt = np.rad2deg(
            np.arccos(
                np.clip(
                    -gravity[:, 2] / np.maximum(np.linalg.norm(gravity, axis=1), 1e-6), -1.0, 1.0
                )
            )
        )
        raw_gyro = obs[:, :3]
        raw_leg = obs[:, 20:34][:, self.legs]
        # Filter signed vectors before taking magnitudes: alternating exploration
        # is different from sustained motion. Keep an unfiltered emergency path.
        beta = self.dt / (0.12 + self.dt)
        fresh = ~self.filter_valid
        for filtered, raw in [
            (self.filtered_gyro, raw_gyro),
            (self.filtered_leg, raw_leg),
            (self.filtered_gravity, gravity),
        ]:
            filtered[:] += beta * (raw - filtered)
            filtered[fresh] = raw[fresh]
        fast_beta = self.dt / (0.04 + self.dt)
        for filtered, raw in [(self.fast_gyro, raw_gyro), (self.fast_leg, raw_leg)]:
            filtered[:] += fast_beta * (raw - filtered)
            filtered[fresh] = raw[fresh]
        self.filter_valid[:] = True
        gyro = np.linalg.norm(self.filtered_gyro, axis=1)
        leg = np.mean(abs(self.filtered_leg), axis=1)
        g = self.filtered_gravity
        filtered_tilt = np.rad2deg(
            np.arccos(np.clip(-g[:, 2] / np.maximum(np.linalg.norm(g, axis=1), 1e-6), -1.0, 1.0))
        )
        commands = obs[:, 48:61]
        head_and_posture = commands[:, [0, 3, 4, 5, 6]]
        changed = (~self.valid) | np.any(abs(head_and_posture - self.previous) > 1e-6, axis=1)
        self.previous[:] = head_and_posture
        self.valid[:] = True
        # Encoders and commanded angles only: no privileged height/contact inputs.
        angles = obs[:, 6:20] + self.default_angles[None, :]
        leg_error = np.sqrt(np.mean((angles[:, self.legs] - self.sit_legs[None, :]) ** 2, axis=1))
        goal = self.default_angles[None, 5:9] + commands[:, 3:7]
        self.goal = goal
        captured = leg_error < self.cfg.fast_leg_pose_rms_rad
        hold = (commands[:, 0] > 0.5) & (captured | self.recovering) & ~changed
        stable = hold & (filtered_tilt < 18.0) & (gyro < 0.35) & (leg < 0.65)
        emergency = (
            (tilt > 28.0)
            | (np.linalg.norm(raw_gyro, axis=1) > 2.0)
            | (np.mean(abs(raw_leg), axis=1) > 2.0)
        )
        disturbance = (
            emergency
            | (np.linalg.norm(self.fast_gyro, axis=1) > 0.7)
            | (np.mean(abs(self.fast_leg), axis=1) > 1.2)
        )
        sitting = commands[:, 0] > 0.5
        self.armed[~sitting] = False
        self.recovering[~sitting] = False
        self.cooldown[~sitting] = 0.0
        self.cooldown[:] = np.maximum(0.0, self.cooldown - self.dt)
        disturbed = sitting & self.armed & disturbance
        self.cooldown[disturbed] = self.cfg.recovery_cooldown_s
        self.recovering[disturbed] = True
        release = (~hold) | disturbance | (self.cooldown > 0.0)
        dwell = np.where(
            self.recovering, self.cfg.recovery_stable_dwell_s, self.cfg.fast_stable_dwell_s
        )
        tightening = np.where(
            self.recovering, self.cfg.recovery_tightening_s, self.cfg.fast_tightening_s
        )
        self.age[:] = np.where(
            release,
            0.0,
            np.minimum(np.maximum(self.age + self.dt * np.where(stable, 1.0, -0.5), 0.0), dwell),
        )
        self.strength[:] = np.where(
            release,
            0.0,
            np.where(
                self.age >= dwell - 1e-9,
                np.minimum(self.strength + self.dt / tightening, 1.0),
                np.where(
                    self.age < dwell * 0.5,
                    np.maximum(self.strength - self.dt / dwell, 0.0),
                    self.strength,
                ),
            ),
        )
        self.armed[:] |= self.strength > 0.5
        self.recovering[self.strength > 0.99] = False
        self.last_hold[:] = hold
        self.last_stable[:] = stable
        self.last_release[:] = release
        return self.strength

    def limit_raw(self, previous, raw, increments):
        rates = np.asarray(increments[5:9]) / self.dt
        cap = (
            (1 - self.strength[:, None]) * rates[None, :]
            + self.strength[:, None] * self.cfg.quiet_head_rate_rad_s
        ) * self.dt
        delta = raw[:, 5:9] - previous[:, 5:9]
        limited = np.clip(delta, -cap, cap)
        error = self.goal - previous[:, 5:9]
        # Retain useful return-to-target motion; never allow crossing the goal
        # through this extra allowance. Outward motion keeps the quiet cap.
        inward = (delta * error > 0) & (abs(error) > self.cfg.fast_head_deadband_rad)
        correction = np.sign(error) * np.minimum(
            np.minimum(abs(delta), abs(error)),
            np.minimum(rates[None, :], self.cfg.head_return_gain_s_inv * abs(error)) * self.dt,
        )
        return previous[:, 5:9] + np.where(
            inward, np.sign(error) * np.maximum(abs(limited), abs(correction)), limited
        )


GOVERNOR_CONFIG = {
    "fast_stable_dwell_s": 0.08,
    "fast_tightening_s": 0.12,
    "fast_leg_pose_rms_rad": 0.15,
    "fast_head_deadband_rad": 0.017453292519943295,
    "quiet_head_rate_rad_s": 0.005,
    "head_return_gain_s_inv": 8.0,
    "recovery_cooldown_s": 0.2,
    "recovery_stable_dwell_s": 0.3,
    "recovery_tightening_s": 0.3,
}
SIT_LEGS = np.asarray(
    [
        0.0,
        0.0,
        0.625,
        -1.1399999856948853,
        -0.3499999940395355,
        0.0,
        0.0,
        -0.625,
        1.1399999856948853,
        0.3499999940395355,
    ],
    dtype=np.float64,
)


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
            raise ValueError("Joint order does not match the API-v2 contract")
        # Training reset seeds the integrator from actual measured positions.
        positions = np.asarray(first_frame["positions"], dtype=np.float64)
        velocities = np.asarray(first_frame["velocities"], dtype=np.float64)
        # The supplied reference_adapter.initialize_target also clips the
        # measured initial target to the policy bounds before integration.
        self.target = np.clip(positions[TRAINING_INDEX], TARGET_LOW, TARGET_HIGH)
        self.previous_velocity = velocities[TRAINING_INDEX].copy()
        self.governor = SitGovernor(
            1,
            CONTROL_DT,
            DEFAULT_ANGLES.astype(np.float32),
            SIT_LEGS,
            SimpleNamespace(**GOVERNOR_CONFIG),
        )
        self.last_obs = None
        if not np.isfinite(self.target).all() or not np.isfinite(self.previous_velocity).all():
            raise ValueError("Initial joint feedback must be finite")

    def preprocess(self, frame, feedback):
        if feedback is not None:
            targets = feedback.get("requested_targets", {})
            if all(name in targets for name in TRAINING_JOINTS):
                target = np.asarray(
                    [targets[name]["position"] for name in TRAINING_JOINTS], dtype=np.float64
                )
                if not np.isfinite(target).all():
                    raise ValueError("Previous commanded targets must be finite")
                self.target = np.clip(target, TARGET_LOW, TARGET_HIGH)
        mode = frame["policy_context"]["action"]
        if mode not in ("sit", "rise"):
            raise ValueError("Incremental SitStand requires sit or rise")
        q = np.asarray(frame["positions"], dtype=np.float64)[TRAINING_INDEX]
        qd = np.asarray(frame["velocities"], dtype=np.float64)[TRAINING_INDEX]
        commands = np.zeros(13, dtype=np.float64)
        commands[0] = 1.0 if mode == "sit" else 0.0
        # Head channels are desired offsets from DEFAULT_ANGLES, in radians.
        commands[3:7] = np.asarray(frame["command"]["head"], dtype=np.float64)
        # Body and other velocity commands were zero in this training task.
        history = (self.target - DEFAULT_ANGLES) / HISTORY_SCALE
        obs = np.concatenate(
            (
                np.asarray(frame["imu"]["gyro"], dtype=np.float64),
                np.asarray(frame["imu"]["gravity"], dtype=np.float64),
                q - DEFAULT_ANGLES,
                self.previous_velocity,
                history,
                commands,
            )
        ).astype(np.float32)
        if not np.isfinite(obs).all():
            raise ValueError("Observation must be finite")
        self.last_obs = obs.reshape(1, 61).copy()
        self.previous_velocity = qd.copy()
        return {"obs": obs.reshape(1, 61)}

    def postprocess(self, outputs, frame):
        del frame
        # Tanh is evaluated in the network's float32 action dtype, matching
        # NumPy simulation decoding; target integration uses float64 state.
        action = np.asarray(outputs["actions"], dtype=np.float32).reshape(14)
        if not np.isfinite(action).all():
            raise ValueError("Model output must be finite")
        if self.last_obs is None:
            raise ValueError("Call preprocess before postprocess")
        # Match supplied Controller.step using the identical float32 observation.
        previous = self.last_obs[:, 34:48] * HISTORY_SCALE + DEFAULT_ANGLES.astype(np.float32)
        self.governor.update(self.last_obs, None)
        raw = previous + INCREMENT.astype(np.float32) * np.tanh(action[None, :])
        raw[:, 5:9] = self.governor.limit_raw(previous, raw, INCREMENT.astype(np.float32))
        self.target = np.clip(raw, TARGET_LOW.astype(np.float32), TARGET_HIGH.astype(np.float32))[0]
        self.last_obs = None
        # This is already the absolute target. No extra .12 scale, reference
        # addition, EMA or phase schedule may be applied by the caller.
        by_name = {
            name: {
                "position": float(self.target[i]),
                "velocity": 0.0,
                "torque_ff": 0.0,
                "kp": float(KP[i]),
                "kd": float(KD[i]),
            }
            for i, name in enumerate(TRAINING_JOINTS)
        }
        return {name: by_name[name] for name in CONTROLLED}
