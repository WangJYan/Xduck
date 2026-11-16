"""API-v2 shared v2.0.2 P12 Walk + supplied Stand/recovery; canonical BASE IMU input.
Normalization, solver4 and HOME adaptation are embedded in the supplied ONNX.
"""
import numpy as np
JOINTS = ['left_hip_yaw', 'left_hip_roll', 'left_hip_pitch', 'left_knee', 'left_ankle', 'right_hip_yaw', 'right_hip_roll', 'right_hip_pitch', 'right_knee', 'right_ankle', 'neck_pitch', 'head_pitch', 'head_yaw', 'head_roll', 'mouth']
INDEX = [0, 1, 2, 3, 4, 10, 11, 12, 13, 5, 6, 7, 8, 9]
NAMES = [JOINTS[i] for i in INDEX]
HOME = np.asarray([0.0, 0.08, 0.394, -0.061, -0.455003757873437, -0.26, -0.27748112810894915, 0.0, 0.0, 0.0, -0.08, -0.394, 0.061, 0.4550037392379021], dtype=np.float32)
LOW = np.asarray([-1.19999, -0.11999, -2.99999, -1.09999, -1.3999899999999998, -0.26999, -1.537471128108949, -1.99999, -0.44999, -0.34998999999999997, -1.19999, -2.99999, -0.7999900000000001, -1.29999], dtype=np.float32)
HIGH = np.asarray([0.34998999999999997, 1.19999, 2.99999, 0.7999900000000001, 1.29999, 1.29999, 0.8625088718910509, 1.99999, 0.44999, 1.19999, 0.19999, 1.99999, 1.09999, 1.3999899999999998], dtype=np.float32)
INCREMENT = np.asarray([0.015, 0.01, 0.08, 0.06, 0.075, 0.11, 0.025, 0.025, 0.01, 0.015, 0.01, 0.08, 0.06, 0.075], dtype=np.float32)
KP = np.asarray([90, 90, 75, 100, 90, 75, 90, 75, 90, 90, 90, 75, 100, 90], dtype=np.float32)
KD = np.asarray([2.5, 2.5, 2.5, 3.0, 3.0, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 2.5, 3.0, 3.0], dtype=np.float32)
HEAD_LOW = np.asarray([0, -0.5, -1.0, -0.2], dtype=np.float64)
HEAD_HIGH = np.asarray([0.6, 0.28, 1.0, 0.2], dtype=np.float64)
HEAD_RATE = np.asarray([0.8, 1.0, 1.2, 0.45], dtype=np.float64)

WALK_HOME = np.asarray([0.0, 0.08, 0.394, -0.061, -0.455003757873437, -0.26, -0.27748112810894915, 0.0, 0.0, 0.0, -0.08, -0.394, 0.061, 0.4550037392379021], dtype=np.float32)
WALK_SCALE = np.asarray([0.12, 0.03666666666666667, 0.12, 0.12, 0.12, 0.09666666666666666, 0.12, 0.12, 0.12, 0.12, 0.03666666666666667, 0.12, 0.12, 0.12], dtype=np.float32)
WALK_LOW = np.asarray([-1.19999, -0.11999, -2.99999, -1.09999, -1.3999899999999998, -0.44999, -1.537471128108949, -1.99999, -0.44999, -0.34998999999999997, -1.19999, -2.99999, -0.7999900000000002, -1.29999], dtype=np.float32)
WALK_HIGH = np.asarray([0.34998999999999997, 1.19999, 2.99999, 0.7999900000000002, 1.29999, 1.29999, 0.862508871891051, 1.99999, 0.44999, 1.19999, 0.19999, 1.99999, 1.09999, 1.3999899999999998], dtype=np.float32)

P12_IO = {'stage': 'P12', 'observation_dim': 61, 'action_dim': 14, 'normalization_inside_onnx': True, 'external_normalization': False, 'observation_mean': [0.0010675244266167283, -0.015530328266322613, 0.0025144636165350676, 0.009793272241950035, -0.0021797739900648594, -0.9916916489601135, 0.057532899081707, -0.08676166832447052, -0.051851868629455566, -0.042200010269880295, 0.05688776448369026, 0.05061676353216171, -0.006132994778454304, -0.0011833709431812167, -0.006067469250410795, -0.009593418799340725, 0.09646917134523392, 0.031164707615971565, 0.0098344087600708, -0.05892772600054741, -0.000826836156193167, -0.006456717383116484, -0.0049513899721205235, -0.004509254824370146, 0.0005840040394105017, -0.0013095519971102476, -0.00392984040081501, -0.003786493092775345, -0.0047240108251571655, -0.004026948474347591, 0.0006228840793482959, -0.0007016685558483005, -0.004009197000414133, -0.008727796375751495, 0.4761064946651459, -2.487050771713257, -0.4269041121006012, -0.32717493176460266, 0.47254619002342224, 0.5121245980262756, -0.04793557524681091, -0.009579016827046871, -0.0534275658428669, -0.07610996067523956, 2.7138302326202393, 0.25720828771591187, 0.05639722943305969, -0.4870971143245697, 0.08543180674314499, 0.0001934394967975095, 3.291155371698551e-05, 0.00023209220671560615, -0.00016105514077935368, 8.854168117977679e-05, 8.670232091390062e-06, -4.705146693595452e-06, 2.2093240659160074e-06, 6.172204507493007e-07, -8.137649274431169e-06, -4.350823701315676e-07, -7.059982453938574e-05], 'observation_scale': [0.6642211675643921, 0.696744441986084, 0.9775258898735046, 0.09995926916599274, 0.08712805062532425, 0.0625230222940445, 0.05673517286777496, 0.0687817856669426, 0.14660054445266724, 0.17837242782115936, 0.10215269029140472, 0.10963306576013565, 0.12785133719444275, 0.14387670159339905, 0.11354197561740875, 0.053598493337631226, 0.07646378129720688, 0.13369715213775635, 0.16859295964241028, 0.09882158041000366, 1.2174708843231201, 0.9181973934173584, 1.7573390007019043, 2.222588062286377, 1.5712976455688477, 1.2564624547958374, 1.941150188446045, 1.8470933437347412, 2.137403726577759, 1.179051160812378, 0.9373310804367065, 1.630232334136963, 2.0924642086029053, 1.4960356950759888, 0.4996322989463806, 1.8638395071029663, 1.214673638343811, 1.4835656881332397, 0.8738404512405396, 1.1598957777023315, 1.0458977222442627, 1.2053993940353394, 0.9544750452041626, 0.47840791940689087, 1.9667454957962036, 1.106886625289917, 1.40178382396698, 0.8410806059837341, 0.3060338497161865, 0.19810955226421356, 0.36106181144714355, 0.12623119354248047, 0.12630079686641693, 0.15579821169376373, 0.04262903332710266, 0.01288619264960289, 0.012887614779174328, 0.012887906283140182, 0.03888489305973053, 0.038845956325531006, 0.03881929814815521], 'policy_reference_qpos': [0.0, 0.08, 0.394, -0.061, -0.455003757873437, -0.26, -0.27748112810894915, 0.0, 0.0, 0.0, -0.08, -0.394, 0.061, 0.4550037392379021], 'motor_zero_qpos': [0.0, 0.0, 0.0, 0.0, -3.7578734369825284e-06, -0.26, -0.24, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.7392379020895206e-06], 'joint_limits_qpos_rad': [[-1.2, 0.35], [-0.12, 1.2], [-3.0, 3.0], [-1.1, 0.8], [-1.4, 1.3], [-0.45, 1.3], [-1.537481128108949, 0.8625188718910508], [-2.0, 2.0], [-0.45, 0.45], [-0.35, 1.2], [-1.2, 0.2], [-3.0, 2.0], [-0.8, 1.1], [-1.3, 1.4]], 'physical_action_scale_rad': [0.12, 0.03666666666666667, 0.12, 0.12, 0.12, 0.09666666666666666, 0.12, 0.12, 0.12, 0.12, 0.03666666666666667, 0.12, 0.12, 0.12], 'motor_position_feedback_to_qpos': 'motor_position_rad + motor_zero_qpos', 'action_to_qpos': 'clip(HOME + raw_action * physical_action_scale_rad, joint_limits)', 'qpos_to_motor_target': 'qpos - motor_zero_qpos', 'IMU_physical_to_body_rotation': [[-1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 1.0]], 'body_yaw_required': True, 'body_xy_or_body_velocity_required': False, 'heading_hold': False, 'phase_mean': [-4.350823701315676e-07, -7.059982453938574e-05], 'phase_scale': [0.038845956325531006, 0.03881929814815521], 'step_goal_m': 0.1, 'task_adapter_required': True, 'model_version': '2.0.2', 'measurement_revision': 'v201_route_contact_measurement_20261108', 'IMU_body_position_m': [-0.03, 0.006, -0.002626999999999935], 'IMU_physical_to_body_quaternion_wxyz': [0, 0, 0, 1]}

def wrap(x): return np.arctan2(np.sin(x), np.cos(x))
class HeadingAdapter:
 def __init__(self,n,kp=.8,rate_limit=.6):
  self.reference=np.zeros(n);self.kp=kp;self.rate_limit=rate_limit
 def reset(self,ids,body_yaw):self.reference[np.asarray(ids,dtype=int)]=body_yaw
 def step(self,body_yaw,user_yaw_rate,dt=.02,enabled=True):
  self.reference=wrap(self.reference+np.asarray(user_yaw_rate)*dt)
  error=wrap(np.asarray(body_yaw)-self.reference)
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


def new_walk_adapter():
    c = P12_IO
    a = TaskAdapter(1, c["phase_mean"], c["phase_scale"], goal=c["step_goal_m"], variable=True)
    mean = np.asarray(c["observation_mean"])
    scale = np.asarray(c["observation_scale"])
    a.start_mean = float(mean[56]); a.start_scale = float(scale[56])
    a.heading_mean = mean[57:59].copy(); a.heading_scale = scale[57:59].copy()
    return a

class Policy:
    def describe(self):
        return {"api_version": 2, "period_us": 20000,
                "required_sources": ["joints", "imu", "command", "policy_context"],
                "inputs": {"obs": {"dtype": "float32", "shape": [1, 61]}},
                "outputs": {"actions": {"dtype": "float32", "shape": [1, 14]}},
                "controlled_joints": [n for n in JOINTS if n != "mouth"]}

    @staticmethod
    def mode(frame):
        mode = frame["policy_context"]["action"]
        if mode not in ("walk", "stand"):
            raise ValueError("Shared P12/Stand policy requires walk or stand")
        return mode

    def reset(self, robot_info, first_frame):
        mode = self.mode(first_frame)
        if robot_info["joint_names"] != JOINTS:
            raise ValueError("API-v2 joint order mismatch")
        q = np.asarray(first_frame["positions"], dtype=np.float32)[INDEX]
        qd = np.asarray(first_frame["velocities"], dtype=np.float32)[INDEX]
        if not np.isfinite(q).all() or not np.isfinite(qd).all():
            raise ValueError("Initial joint feedback must be finite")
        self.target = np.clip(q, LOW if mode == "stand" else WALK_LOW,
                              HIGH if mode == "stand" else WALK_HIGH)
        self.previous_velocity = qd.copy()
        self.head = np.zeros(4, dtype=np.float64)
        self.last_mode = None
        self.raw_history = np.zeros(14, dtype=np.float32)
        self.walk_adapter = new_walk_adapter()

    def preprocess(self, frame, feedback):
        mode = self.mode(frame)
        low, high = (LOW, HIGH) if mode == "stand" else (WALK_LOW, WALK_HIGH)
        if feedback is not None and "requested_targets" in feedback:
            targets = feedback["requested_targets"]
            if not all(n in targets for n in NAMES):
                raise ValueError("Handoff feedback must contain all 14 requested targets")
            inherited = np.asarray([targets[n]["position"] for n in NAMES], dtype=np.float32)
            if not np.isfinite(inherited).all():
                raise ValueError("Inherited target must be finite")
            self.target = np.clip(inherited, low, high)
        else:
            self.target = np.clip(self.target, low, high)
        q = np.asarray(frame["positions"], dtype=np.float32)[INDEX]
        qd = np.asarray(frame["velocities"], dtype=np.float32)[INDEX]
        delayed = self.previous_velocity.copy()
        if not np.isfinite(qd).all():
            raise ValueError("Joint velocity must be finite")
        if mode == "stand":
            if self.last_mode != "stand":
                self.head[:] = 0.0
            request = np.asarray(frame["command"]["head"], dtype=np.float64)
            if request.shape != (4,) or not np.isfinite(request).all():
                raise ValueError("Head command must contain four finite HOME-relative radians")
            request = np.clip(request, HEAD_LOW, HEAD_HIGH)
            self.head += np.clip(request-self.head, -HEAD_RATE*.02, HEAD_RATE*.02)
            obs = np.concatenate([
                np.asarray(frame["imu"]["gyro"], dtype=np.float32),
                np.asarray(frame["imu"]["gravity"], dtype=np.float32),
                q-HOME, delayed, (self.target-HOME)/np.float32(.12),
                np.zeros(3), self.head, np.zeros(6),
            ]).astype(np.float32)
        else:
            entering = self.last_mode != "walk"
            history = ((self.target-WALK_HOME)/WALK_SCALE) if entering else self.raw_history
            requested = np.asarray([0., 0., 0.] if frame["policy_context"]["body_active"]
                                   else frame["command"]["twist"], dtype=np.float32)
            if requested.shape != (3,) or not np.isfinite(requested).all():
                raise ValueError("Walk twist must contain three finite values")
            obs = np.concatenate([
                np.asarray(frame["imu"]["gyro"], dtype=np.float32),
                np.asarray(frame["imu"]["gravity"], dtype=np.float32),
                q-WALK_HOME, delayed, history, np.zeros(13),
            ]).astype(np.float32)
            yaw = body_yaw(frame)
            if entering:
                self.walk_adapter.reset([0], np.asarray([yaw]))
            obs = self.walk_adapter.adapt_observation(
                obs.reshape(1, 61), np.asarray([yaw]), requested.reshape(1, 3),
                dt=0.0 if entering else .02, heading_hold=False,
            ).reshape(61)
        if obs.shape != (61,) or not np.isfinite(obs).all():
            raise ValueError("Expected finite 61D observation")
        self.previous_velocity = qd.copy()
        return {"obs": obs.reshape(1, 61)}

    def postprocess(self, outputs, frame):
        mode = self.mode(frame)
        raw = np.asarray(outputs["actions"], dtype=np.float32).reshape(14)
        if not np.isfinite(raw).all():
            raise ValueError("Model output must be finite")
        if mode == "stand":
            self.target = np.clip(self.target+INCREMENT*np.tanh(raw), LOW, HIGH)
        else:
            self.target = np.clip(WALK_HOME+WALK_SCALE*raw, WALK_LOW, WALK_HIGH)
            self.raw_history = raw.copy()
        self.last_mode = mode
        return {n: {"position": float(self.target[i]), "velocity": 0.0,
                    "torque_ff": 0.0, "kp": float(KP[i]), "kd": float(KD[i])}
                for i, n in enumerate(NAMES)}
