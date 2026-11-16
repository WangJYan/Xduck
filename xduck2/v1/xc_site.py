"""API-v2 v2.0.2 descent600 / original-B2500-rise candidate consumer.
Standalone NumPy consumer. Keep state across sit/rise commands.
Use current joint velocity feedback; no extra policy-frame velocity delay.
"""

import numpy as np
# Embedded deployment configuration; no external file required.
IO = {'model_filename': 'xduck_v202_descent600.onnx', 'input_name': 'obs', 'input_shape': [1, 61], 'output_name': 'actions', 'output_shape': [1, 14], 'actor_observation_normalization': False, 'control_dt_s': 0.02, 'simulation_dt_s': 0.001, 'policy_joint_names': ['left_hip_yaw_joint', 'left_hip_roll_joint', 'left_hip_pitch_joint', 'left_knee_pitch_joint', 'left_ankle_pitch_joint', 'neck_pitch_joint', 'head_pitch_joint', 'head_yaw_joint', 'head_roll_joint', 'right_hip_yaw_joint', 'right_hip_roll_joint', 'right_hip_pitch_joint', 'right_knee_pitch_joint', 'right_ankle_pitch_joint'], 'default_angles_rad': [0.0, 0.07999999821186066, 0.39399999380111694, -0.061000000685453415, -0.4550037682056427, -0.25999999046325684, -0.2774811387062073, 0.0, 0.0, 0.0, -0.07999999821186066, -0.39399999380111694, 0.061000000685453415, 0.4550037384033203], 'target_low_rad': [-1.19, -0.11000000178813935, -2.9900000061988834, -1.0900000006854536, -1.3900000103322057, -0.43999999046325683, -1.5274811387062073, -1.99, -0.44, -0.33999999999999997, -1.1899999982118605, -2.989999993801117, -0.7899999993145466, -1.2900000008345818], 'target_high_rad': [0.33999999999999997, 1.1899999982118605, 2.989999993801117, 0.7899999993145466, 1.2899999896677943, 1.2900000095367432, 0.8525188612937926, 1.99, 0.44, 1.19, 0.19000000178813936, 1.990000006198883, 1.0900000006854536, 1.3899999991654182], 'target_increment_rad': [0.015, 0.01, 0.08, 0.06, 0.075, 0.11, 0.025, 0.025, 0.01, 0.015, 0.01, 0.08, 0.06, 0.075], 'target_history_scale_rad': 0.12, 'reference_source': 'Unchanged v2.0.2 original_only deployment IO; new curriculum600 checkpoint', 'experiment': 'B2500_descent_repair_20261109/curriculum600', 'head_governor_enabled': False, 'flexible_joints_enabled': False, 'flexible_dr_enabled': False, 'actor_observation_layout': {'body_gyro_rad_s': [0, 3], 'body_gravity_down_unit': [3, 6], 'joint_position_minus_default_rad': [6, 20], 'joint_velocity_rad_s': [20, 34], '(previous_target-default)/history_scale': [34, 48], 'commands': [48, 61]}, 'command_layout': {'posture_0_stand_1_sit': [48, 49], 'other_twist_slots': [49, 51], 'neck_head_pitch_yaw_roll_offsets_rad': [51, 55], 'body_command_six_slots': [55, 61]}, 'target_mapping': 'clip(previous_target + increment * tanh(raw_actions), low, high)', 'hardware_to_policy_indices': [0, 1, 2, 3, 4, 10, 11, 12, 13, 5, 6, 7, 8, 9], 'policy_to_hardware_indices': [0, 1, 2, 3, 4, 9, 10, 11, 12, 13, 5, 6, 7, 8], 'hardware_order': 'left leg five, right leg five, neck/head four; mouth excluded', 'stand_height_m': 0.3228203087684791, 'sit_height_m': 0.22427459899559668, 'policy_reference_applies_to_both_joint_observations_and_target_history': True, 'base_updates': 2500, 'head_repair_updates': 200, 'head_repair_scope': 'Frozen seated head network; actual output can also include learned descent correction while settling or moving', 'extra_joint_velocity_delay_steps': 0, 'joint_velocity_feedback': 'Current received joint velocity, matching the existing API-v2 current_velocity deployment interface', 'kp': [90, 90, 75, 100, 90, 75, 90, 75, 90, 90, 90, 75, 100, 90], 'kd': [2.5, 2.5, 2.5, 3.0, 3.0, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 3.0, 3.0], 'initial_target': 'clip(measured joint positions, target_low, target_high); preserve target across sit/rise command switches; use previous commanded target on a continuous controller handoff', 'mouth_controlled': False, 'imu': {'network_frame': 'trunk/base_link', 'gyro_units': 'rad/s', 'gravity': 'Unit world-down projected into trunk coordinates; upright=[0,0,-1]; not raw acceleration', 'mjcf_imu_site': 'policy_aligned_imu', 'mjcf_R_trunk_from_site': [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], 'mjcf_imu_position_in_trunk_m': [0.0, 0.0, 0.0], 'raw_site_gyro_formula': 'gyro_trunk = R_trunk_from_site @ gyro_site', 'orientation_formula': 'If R_world_from_site is supplied in exactly the MJCF site frame: R_world_from_trunk = R_world_from_site @ R_trunk_from_site.T; gravity_trunk = R_world_from_trunk.T @ [0,0,-1]', 'driver_requirement': 'API frame imu.gyro and imu.gravity must already be in trunk coordinates; do not rotate twice; physical driver axes must match the chosen calibration'}, 'hardware_policy_joint_names': ['left_hip_yaw', 'left_hip_roll', 'left_hip_pitch', 'left_knee', 'left_ankle', 'neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'right_hip_yaw', 'right_hip_roll', 'right_hip_pitch', 'right_knee', 'right_ankle'], 'model_to_hardware_joint_name_aliases': {'left_hip_yaw_joint': 'left_hip_yaw', 'left_hip_roll_joint': 'left_hip_roll', 'left_hip_pitch_joint': 'left_hip_pitch', 'left_knee_pitch_joint': 'left_knee', 'left_ankle_pitch_joint': 'left_ankle', 'neck_pitch_joint': 'neck_pitch', 'head_pitch_joint': 'head_pitch', 'head_yaw_joint': 'head_yaw', 'head_roll_joint': 'head_roll', 'right_hip_yaw_joint': 'right_hip_yaw', 'right_hip_roll_joint': 'right_hip_roll', 'right_hip_pitch_joint': 'right_hip_pitch', 'right_knee_pitch_joint': 'right_knee', 'right_ankle_pitch_joint': 'right_ankle'}, 'hardware_mapping_note': 'Index permutations refer to logical name order, not CAN IDs. Retain the actual robot driver motor IDs, encoder-zero calibration and motor-direction mapping; those have not been inferred.', 'head_command': 'Offsets from new HOME, rad, order neck_pitch/head_pitch/head_yaw/head_roll; zero on rise/standing', 'policy_selection': 'obs[48]>0.5: repaired descent, fading back to frozen seated policy near settled SIT; otherwise frozen original B2500 rise with old HOME adapter internal', 'status': 'Candidate: nominal sit/rise passed, dynamic seated head contact remains', 'known_limitations': ['Dynamic seated head sine test: left shank shell contact in8/8, peak38.22N; head MAE[4.65,7.02,4.03,7.12]deg', 'Original rise transient body tilt up to19.67deg', 'Nominal deterministic8-trial protocol only; rapid reversals and delay stress from previous ONNX do not validate this checkpoint'], 'original_rise_updates': 2500, 'source_checkpoint_sha256': 'a2ee8daacbe48fa735769efccbda47f79e0ec601c6d8d49b14258db9ca680bae', 'onnx_sha256': '54f2feee7aac0e527f7bc23146e56c074aada6de8d331acdb3e7b04c8c41cf2b', 'descent_repair_updates_total': 900, 'descent_repair_final_phase_updates': 600}

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

# Deployment values extracted from the actual v2.0.2 inference environment.
DEFAULT_ANGLES=np.asarray(IO['default_angles_rad'],dtype=np.float32)
TARGET_LOW=np.asarray(IO['target_low_rad'],dtype=np.float32)
TARGET_HIGH=np.asarray(IO['target_high_rad'],dtype=np.float32)
INCREMENT=np.asarray(IO['target_increment_rad'],dtype=np.float32)
HISTORY_SCALE=IO['target_history_scale_rad']
KP=np.asarray(IO['kp'],dtype=np.float32)
KD=np.asarray(IO['kd'],dtype=np.float32)
CONTROL_DT=IO['control_dt_s']


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
        positions = np.asarray(first_frame["positions"], dtype=np.float32)
        velocities = np.asarray(first_frame["velocities"], dtype=np.float32)
        # The supplied reference_adapter.initialize_target also clips the
        # measured initial target to the policy bounds before integration.
        self.target = np.clip(positions[TRAINING_INDEX], TARGET_LOW, TARGET_HIGH)
        self.previous_velocity = velocities[TRAINING_INDEX].copy()
        if not np.isfinite(self.target).all() or not np.isfinite(self.previous_velocity).all():
            raise ValueError("Initial joint feedback must be finite")

    def preprocess(self, frame, feedback):
        if feedback is not None:
            targets = feedback.get("requested_targets", {})
            if "requested_targets" in feedback and not all(
                name in targets for name in TRAINING_JOINTS
            ):
                raise ValueError("Handoff feedback must contain all 14 requested targets")
            if all(name in targets for name in TRAINING_JOINTS):
                target = np.asarray(
                    [targets[name]["position"] for name in TRAINING_JOINTS], dtype=np.float32
                )
                if not np.isfinite(target).all():
                    raise ValueError("Previous commanded targets must be finite")
                self.target = np.clip(target, TARGET_LOW, TARGET_HIGH)
        mode = frame["policy_context"]["action"]
        if mode not in ("sit", "rise"):
            raise ValueError("Incremental SitStand requires sit or rise")
        q = np.asarray(frame["positions"], dtype=np.float32)[TRAINING_INDEX]
        qd = np.asarray(frame["velocities"], dtype=np.float32)[TRAINING_INDEX]
        commands = np.zeros(13, dtype=np.float32)
        commands[0] = 1.0 if mode == "sit" else 0.0
        # Head channels are desired offsets from DEFAULT_ANGLES, in radians.
        commands[3:7] = np.asarray(frame["command"]["head"], dtype=np.float32) if mode == "sit" else 0.0
        # Body and other velocity commands were zero in this training task.
        history = (self.target - DEFAULT_ANGLES) / HISTORY_SCALE
        obs = np.concatenate(
            (
                np.asarray(frame["imu"]["gyro"], dtype=np.float32),
                np.asarray(frame["imu"]["gravity"], dtype=np.float32),
                q - DEFAULT_ANGLES,
                qd,
                history,
                commands,
            )
        ).astype(np.float32)
        if not np.isfinite(obs).all():
            raise ValueError("Observation must be finite")
        self.previous_velocity = qd.copy()
        return {"obs": obs.reshape(1, 61)}

    def postprocess(self, outputs, frame):
        del frame
        # Tanh is evaluated in the network's float32 action dtype, matching
        # supplied reference_adapter decoding; target state is also float32.
        action = np.asarray(outputs["actions"], dtype=np.float32).reshape(14)
        if not np.isfinite(action).all():
            raise ValueError("Model output must be finite")
        self.target = np.clip(self.target + INCREMENT * np.tanh(action), TARGET_LOW, TARGET_HIGH)
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
