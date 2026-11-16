//! Keep IPC CPU bursts off the control/inference core on the K11C.
//! Affinity is a scheduling policy; hardware access is still restricted by the worker sandbox.
#[cfg(target_os = "linux")]
use std::sync::atomic::{AtomicBool, Ordering};

#[cfg(target_os = "linux")]
static ISOLATE_CPUS: AtomicBool = AtomicBool::new(false);

/// Opt in only in the board's service. CLI tools and development hosts keep their CPU set.
pub(crate) fn initialize() -> std::io::Result<()> {
    if std::env::var_os("ROBOT_CPU_ISOLATION").as_deref() != Some(std::ffi::OsStr::new("1")) {
        return Ok(());
    }
    #[cfg(target_os = "linux")]
    {
        let mut available: libc::cpu_set_t = unsafe { std::mem::zeroed() };
        if unsafe { libc::sched_getaffinity(0, std::mem::size_of_val(&available), &mut available) } != 0 {
            return Err(std::io::Error::last_os_error());
        }
        if !(0..4).all(|cpu| unsafe { libc::CPU_ISSET(cpu, &available) }) {
            return Err(std::io::Error::other("CPU isolation requires CPUs 0-3; check robotd.service cpuset/affinity"));
        }
        ISOLATE_CPUS.store(true, Ordering::Relaxed);
        // Background threads created before the control thread must also avoid CPU3.
        ipc_affinity()?;
    }
    Ok(())
}

#[cfg(target_os = "linux")]
fn bind(cpus: &[usize]) -> std::io::Result<()> {
    let mut mask: libc::cpu_set_t = unsafe { std::mem::zeroed() };
    for &cpu in cpus {
        unsafe { libc::CPU_SET(cpu, &mut mask); }
    }
    if unsafe { libc::sched_setaffinity(0, std::mem::size_of_val(&mask), &mask) } != 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok(())
}

pub(crate) fn ipc_affinity() -> std::io::Result<()> {
    #[cfg(target_os = "linux")]
    if ISOLATE_CPUS.load(Ordering::Relaxed) { bind(&[0, 1, 2])?; }
    Ok(())
}

/// Also called in pre_exec: use only stack data, atomics and libc, never locks/allocation.
pub(crate) fn policy_affinity() -> std::io::Result<()> {
    #[cfg(target_os = "linux")]
    if ISOLATE_CPUS.load(Ordering::Relaxed) { bind(&[3])?; }
    Ok(())
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use super::*;

    #[test]
    fn affinity_changes_only_the_calling_thread() {
        let mask = || {
            let mut mask: libc::cpu_set_t = unsafe { std::mem::zeroed() };
            assert_eq!(unsafe { libc::sched_getaffinity(0, std::mem::size_of_val(&mask), &mut mask) }, 0);
            (0..libc::CPU_SETSIZE as usize).filter(|&cpu| unsafe { libc::CPU_ISSET(cpu, &mask) }).collect::<Vec<_>>()
        };
        let original = mask();
        let cpu = original[0];
        std::thread::spawn(move || {
            bind(&[cpu]).unwrap();
            assert_eq!(mask(), vec![cpu]);
        }).join().unwrap();
        assert_eq!(mask(), original);
    }

    #[test]
    #[ignore = "K11C root only; explicit model paths, isolated inference and synthetic IPC, no RobotIo"]
    fn policy_meets_deadline_during_ipc_bursts() {
        use crate::custom_policy::{CustomPolicy, PolicyContext};
        use std::{path::PathBuf, sync::Arc, time::{Duration, Instant}};
        assert_eq!(std::env::var("ROBOT_CPU_ISOLATION").unwrap(), "1");
        initialize().unwrap();
        // Test-only reproduction of the old service-wide CPU3 arrangement.
        let shared_cpu = std::env::var_os("TEST_SHARED_CPU").is_some();
        if shared_cpu {
            ISOLATE_CPUS.store(false, Ordering::Relaxed);
            bind(&[3]).unwrap();
        }
        let runtime = tokio::runtime::Builder::new_multi_thread().worker_threads(2)
            .on_thread_start(|| crate::set_ipc_scheduling().unwrap())
            .build().unwrap();
        let stop = Arc::new(AtomicBool::new(false));
        struct Stop(Arc<AtomicBool>);
        impl Drop for Stop { fn drop(&mut self) { self.0.store(true, Ordering::Relaxed); } }
        let guard = Stop(Arc::clone(&stop));
        let path = |key| PathBuf::from(std::env::var_os(key).expect("explicit model/policy path required"));
        let mut policy = CustomPolicy::load_pair(&path("TEST_POLICY"), &path("TEST_WALK"), &path("TEST_STAND")).unwrap();
        let mut loads = Vec::new();
        for _ in 0..2 {
            let stop = Arc::clone(&stop);
            loads.push(runtime.spawn_blocking(move || {
                let mut mask: libc::cpu_set_t = unsafe { std::mem::zeroed() };
                assert_eq!(unsafe { libc::sched_getaffinity(0, std::mem::size_of_val(&mask), &mut mask) }, 0);
                assert_eq!(unsafe { libc::CPU_ISSET(3, &mask) }, shared_cpu, "unexpected IPC CPU mask");
                let value = serde_json::json!({"sessions":vec![vec![0.125f64; 128]; 8]});
                while !stop.load(Ordering::Relaxed) {
                    let burst = Instant::now();
                    while burst.elapsed() < Duration::from_millis(6) {
                        std::hint::black_box(serde_json::to_vec(&value).unwrap());
                    }
                    std::thread::sleep(Duration::from_millis(14));
                }
            }));
        }
        policy_affinity().unwrap();
        let mut sensors = duck_control::io::Sensors::default();
        sensors.imu.gravity = [0.0, 0.0, -1.0];
        sensors.imu.quat = [1.0, 0.0, 0.0, 0.0];
        sensors.positions = [0.0, 0.08, 0.394, -0.061, -0.455,
            0.0, -0.08, -0.394, 0.061, 0.455, 0.019, 0.060, 0.0, 0.0, 0.0];
        let mut command = duck_control::obs::Command::default();
        command.head = [0.1, 0.1, 0.1, 0.05];
        let samples: usize = std::env::var("TEST_SAMPLES").unwrap_or("1500".into()).parse().unwrap();
        let phase_frames: usize = std::env::var("TEST_PHASE_FRAMES").unwrap_or("25".into()).parse().unwrap();
        assert!(phase_frames > 0);
        let mut timings = Vec::with_capacity(samples);
        let mut worst_ms = 0.0f64;
        let mut error = None;
        let mut completed = 0;
        let mut deadline = Instant::now();
        for frame in 0..samples {
            let model = if (frame / phase_frames) % 2 == 0 { "walk" } else { "stand" };
            command.twist = if model == "walk" { [0.1, 0.0, 0.1] } else { [0.0; 3] };
            let started = Instant::now();
            let result = policy.step_model(&sensors, &command, PolicyContext::new(model, None, false), 0.02, model);
            let elapsed_ms = started.elapsed().as_secs_f64() * 1000.0;
            timings.push(elapsed_ms);
            worst_ms = worst_ms.max(elapsed_ms);
            if let Err(reason) = result { error = Some((frame, reason)); break; }
            completed += 1;
            deadline += Duration::from_millis(20);
            if let Some(wait) = deadline.checked_duration_since(Instant::now()) { std::thread::sleep(wait); }
        }
        drop(guard);
        runtime.block_on(async { for load in loads { load.await.unwrap(); } });
        runtime.shutdown_timeout(Duration::from_secs(2));
        timings.sort_by(f64::total_cmp);
        let percentile = |p: f64| timings.get(((timings.len().saturating_sub(1)) as f64 * p) as usize).copied().unwrap_or(0.0);
        println!("policy_cpu_test shared_cpu={shared_cpu} completed={completed} phase_frames={phase_frames} p50_ms={:.3} p99_ms={:.3} max_step_ms={worst_ms:.3} error={error:?}", percentile(0.5), percentile(0.99));
        assert!(error.is_none(), "strict 18 ms policy deadline failed: {error:?}");
    }
}
