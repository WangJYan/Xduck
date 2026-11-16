//! One startup verdict, independent of bus-open retries and the control thread.
use crate::{Params, RobotState, sound::Sound};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

const DEADLINE: Duration = Duration::from_secs(10);
const STABLE: Duration = Duration::from_secs(1);

pub struct AudioHandoff {
    pub done: AtomicBool,
    pub data_ok: AtomicBool,
    bad_samples: AtomicU64,
    voice: Mutex<Option<Sound>>,
}
impl Default for AudioHandoff {
    fn default() -> Self {
        Self {
            done: AtomicBool::new(true),
            data_ok: AtomicBool::new(false),
            bad_samples: AtomicU64::new(0),
            voice: Mutex::new(None),
        }
    }
}
impl AudioHandoff {
    pub fn observe(&self, ok: bool) {
        if !ok {
            self.bad_samples.fetch_add(1, Ordering::Release);
        }
        self.data_ok.store(ok, Ordering::Release);
    }

    pub fn take(&self) -> Option<Sound> {
        self.voice.lock().unwrap().take()
    }
}

#[derive(Default)]
struct Check {
    stable_since: Option<Duration>,
    last_bad_samples: u64,
}
impl Check {
    fn verdict(&mut self, elapsed: Duration, ok: bool, bad_samples: u64) -> Option<bool> {
        // Remember errors between worker polls as well as the latest frame.
        if bad_samples != self.last_bad_samples {
            self.stable_since = None;
            self.last_bad_samples = bad_samples;
        }
        if ok {
            let since = *self.stable_since.get_or_insert(elapsed);
            if elapsed.saturating_sub(since) >= STABLE {
                return Some(true);
            }
        } else {
            self.stable_since = None;
        }
        (elapsed >= DEADLINE).then_some(false)
    }
}

pub fn sample_ok(s: &duck_control::io::Sensors) -> bool {
    let finite = s
        .positions
        .iter()
        .chain(&s.velocities)
        .chain(&s.motor_torques_nm)
        .chain(&s.imu.gyro)
        .chain(&s.imu.gravity)
        .chain(&s.imu.quat)
        .all(|v| v.is_finite());
    finite
        && duck_control::bus::STM32_MOTOR_IDS
            .iter()
            .zip(duck_control::bus::STM32_TO_CONTROL_JOINT)
            .all(|(&id, j)| {
                // Only configured slots participate; the mouth has no DM motor.
                id == 0
                    || (s.motor_flags[j] & 0x0b == 3
                        && s.motor_feedback_age_ms[j] <= 500
                        && s.motor_temperatures_c[j].is_finite()
                        && (0.0..80.0).contains(&s.motor_temperatures_c[j]))
            })
}

fn problem(state: &RobotState) -> Option<String> {
    let health = state.health();
    if !health.healthy {
        return Some(health.reason.unwrap_or_else(|| "system not ready".into()));
    }
    if state.consecutive_errors.load(Ordering::Relaxed) != 0 {
        return Some("STM32 read errors".into());
    }
    if !state.imu_ready.load(Ordering::Relaxed) {
        return Some("IMU not ready".into());
    }
    if !state.startup_audio.data_ok.load(Ordering::Acquire) {
        return Some("STM32/IMU/motor feedback invalid or stale".into());
    }
    let battery = state.battery();
    if !battery.is_some_and(|b| b.volts.is_finite() && b.volts > 0.0 && b.alarm == Some(false)) {
        return Some("battery telemetry missing, stale or alarm active".into());
    }
    None
}

pub fn spawn(state: Arc<RobotState>, params: Params) -> Option<std::thread::JoinHandle<()>> {
    if !params.audio.enabled || !params.audio.greet {
        return None;
    }
    state.startup_audio.done.store(false, Ordering::Release);
    let shared = Arc::clone(&state);
    match std::thread::Builder::new().name("startup-audio".into()).spawn(move || {
        let mut voice = Sound::new(params.audio.bank, params.audio.device);
        let start = Instant::now();
        let mut check = Check::default();
        while !shared.shutdown.load(Ordering::Relaxed) {
            let reason = problem(&shared);
            if let Some(ok) = check.verdict(start.elapsed(), reason.is_none(), shared.startup_audio.bad_samples.load(Ordering::Acquire)) {
                if ok {
                    tracing::info!("startup checks passed: STM32, IMU, motors and battery; playing greeting");
                    voice.play("greet", true);
                } else {
                    tracing::error!(reason = ?reason, "startup checks timed out after 10s; playing 5s alarm");
                    voice.startup_alarm(&shared.shutdown);
                }
                break;
            }
            std::thread::sleep(Duration::from_millis(50));
        }
        *shared.startup_audio.voice.lock().unwrap() = Some(voice);
        shared.startup_audio.done.store(true, Ordering::Release);
    }) {
        Ok(handle) => Some(handle),
        Err(error) => {
            tracing::error!(%error, "cannot start startup audio checker");
            state.startup_audio.done.store(true, Ordering::Release);
            None
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn greeting_requires_uninterrupted_good_data() {
        let mut c = Check::default();
        assert_eq!(c.verdict(Duration::ZERO, true, 0), None);
        assert_eq!(c.verdict(Duration::from_millis(900), false, 0), None);
        assert_eq!(c.verdict(Duration::from_secs(1), true, 0), None);
        assert_eq!(c.verdict(Duration::from_millis(1999), true, 0), None);
        assert_eq!(c.verdict(Duration::from_secs(2), true, 0), Some(true));
    }
    #[test]
    fn missing_bus_and_late_recovery_alarm_at_ten_seconds() {
        let mut c = Check::default();
        assert_eq!(c.verdict(Duration::from_millis(9999), false, 0), None);
        assert_eq!(c.verdict(DEADLINE, false, 0), Some(false));
        let mut c = Check::default();
        assert_eq!(c.verdict(Duration::from_millis(9500), true, 0), None);
        assert_eq!(c.verdict(DEADLINE, true, 0), Some(false));
    }
    #[test]
    fn bad_frame_between_worker_polls_restarts_stability_timer() {
        let mut c = Check::default();
        assert_eq!(c.verdict(Duration::ZERO, true, 0), None);
        assert_eq!(c.verdict(STABLE, true, 1), None);
        assert_eq!(c.verdict(STABLE + STABLE, true, 1), Some(true));
    }
    #[test]
    fn complete_startup_verdict_includes_imu_motors_and_battery() {
        let state = RobotState::new(&Params::default(), false, false);
        assert!(problem(&state).is_some());
        state.ticks.store(10, Ordering::Relaxed);
        state.imu_ready.store(true, Ordering::Relaxed);
        state.startup_audio.data_ok.store(true, Ordering::Relaxed);
        state.meter_v.store(24.0_f64.to_bits(), Ordering::Relaxed);
        state.battery_percent.store(50, Ordering::Relaxed);
        state.battery_alarm.store(0, Ordering::Relaxed);
        assert!(problem(&state).is_none());
        state
            .motor_control_error
            .store(Some(Arc::new("limits not synchronized".into())));
        // Calibration/enable errors alone are not bad sensor data.
        assert!(problem(&state).is_none());
        state.startup_audio.observe(false);
        assert!(problem(&state).unwrap().contains("feedback"));
        state.startup_audio.observe(true);
        state.motor_control_error.store(None);
        state.battery_alarm.store(1, Ordering::Relaxed);
        assert!(problem(&state).unwrap().contains("battery"));
        state.battery_alarm.store(0, Ordering::Relaxed);
        state.imu_ready.store(false, Ordering::Relaxed);
        assert!(problem(&state).unwrap().contains("IMU"));
    }
    #[test]
    fn rejects_missing_stale_faulted_and_nonfinite_motor_data() {
        let mut s = duck_control::io::Sensors::default();
        assert!(!sample_ok(&s));
        for (&id, j) in duck_control::bus::STM32_MOTOR_IDS
            .iter()
            .zip(duck_control::bus::STM32_TO_CONTROL_JOINT)
        {
            if id != 0 {
                s.motor_flags[j] = 3;
                s.motor_temperatures_c[j] = 25.0;
            }
        }
        assert!(sample_ok(&s));
        s.motor_feedback_age_ms[0] = 501;
        assert!(!sample_ok(&s));
        s.motor_feedback_age_ms[0] = 0;
        s.motor_flags[0] |= 8;
        assert!(!sample_ok(&s));
        s.motor_flags[0] = 3;
        s.imu.gyro[0] = f64::NAN;
        assert!(!sample_ok(&s));
    }
}
