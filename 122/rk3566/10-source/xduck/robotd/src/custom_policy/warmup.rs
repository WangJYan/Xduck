//! Bounded preparation only; runtime policy calls retain their strict deadline.
use std::time::{Duration, Instant};

const FRAME_TIMEOUT: Duration = Duration::from_millis(200);
const TOTAL_BUDGET: Duration = Duration::from_secs(2);
const MAX_ROUNDS: usize = 20;
const STABLE_ROUNDS: usize = 3;

pub(crate) fn frame_timeout(deadline: Instant) -> Result<Duration, String> {
    deadline.checked_duration_since(Instant::now())
        .filter(|remaining| !remaining.is_zero())
        .map(|remaining| remaining.min(FRAME_TIMEOUT))
        .ok_or_else(|| "策略预热超过 2 秒总时限".into())
}

/// A round covers every model/context in a worker, returning its slowest frame.
/// Cold frames may be slow, but only consecutive rounds meeting the runtime
/// budget admit the worker. Persistent slowness and worker errors remain failures.
pub(crate) fn run(
    runtime_limit: Duration,
    mut round: impl FnMut(Instant) -> Result<Duration, String>,
) -> Result<usize, String> {
    let deadline = Instant::now() + TOTAL_BUDGET;
    let mut stable = 0;
    for attempt in 1..=MAX_ROUNDS {
        frame_timeout(deadline)?;
        let slowest = round(deadline)?;
        frame_timeout(deadline)?;
        stable = if slowest <= runtime_limit { stable + 1 } else { 0 };
        if stable == STABLE_ROUNDS { return Ok(attempt); }
    }
    Err(format!("策略预热未稳定：20 轮内未连续 3 轮满足 {} ms 运行时限", runtime_limit.as_millis()))
}

#[cfg(test)]
mod tests {
    use super::*;
    const LIMIT: Duration = Duration::from_millis(18);

    #[test]
    fn cold_frame_and_later_jitter_require_three_new_stable_rounds() {
        let mut samples = [90, 10, 12, 25, 8, 9, 11].into_iter();
        let rounds = run(LIMIT, |_| Ok(Duration::from_millis(samples.next().unwrap()))).unwrap();
        assert_eq!(rounds, 7);
        assert_eq!(samples.next(), None);
    }

    #[test]
    fn consistently_slow_worker_is_rejected_after_bounded_attempts() {
        let mut calls = 0;
        let error = run(LIMIT, |_| { calls += 1; Ok(Duration::from_millis(19)) }).unwrap_err();
        assert_eq!(calls, MAX_ROUNDS);
        assert!(error.contains("18 ms"));
    }

    #[test]
    fn worker_failure_is_not_retried_or_hidden() {
        let mut calls = 0;
        assert_eq!(run(LIMIT, |_| { calls += 1; Err("worker exited".into()) }), Err("worker exited".into()));
        assert_eq!(calls, 1);
    }

    #[test]
    fn frame_wait_is_capped_by_both_remaining_budget_and_cold_frame_limit() {
        assert!(frame_timeout(Instant::now() - Duration::from_millis(1)).is_err());
        assert_eq!(frame_timeout(Instant::now() + TOTAL_BUDGET).unwrap(), FRAME_TIMEOUT);
        let remaining = frame_timeout(Instant::now() + Duration::from_millis(20)).unwrap();
        assert!(remaining <= Duration::from_millis(20));
        assert!(!remaining.is_zero());
    }
}
