//! One-shot spoken notices; missing telemetry never means an empty battery.
#[derive(Default)]
pub struct Notices {
    seen20: bool,
    seen10: bool,
    pending20: bool,
    pending10: bool,
    init_armed: bool,
    init_pending: bool,
}
impl Notices {
    pub fn battery(&mut self, percent: f64) {
        if !percent.is_finite() || !(0.0..=100.0).contains(&percent) {
            return;
        }
        // Two percentage points of recharge prevent repeated speech around a threshold.
        if percent >= 22.0 {
            self.seen20 = false;
        }
        if percent >= 12.0 {
            self.seen10 = false;
        }
        if percent >= 20.0 {
            self.pending20 = false;
        }
        if percent >= 10.0 {
            self.pending10 = false;
        }
        if percent < 10.0 && !self.seen10 {
            self.seen10 = true;
            self.seen20 = true;
            self.pending10 = true;
            self.pending20 = false;
        } else if percent < 20.0 && !self.seen20 {
            self.seen20 = true;
            self.pending20 = true;
        }
    }
    pub fn begin_init(&mut self) {
        self.init_armed = true;
        self.init_pending = false;
    }
    pub fn cancel_init(&mut self) {
        self.init_armed = false;
        self.init_pending = false;
    }
    pub fn confirm_init(&mut self, ready: bool) {
        if ready && self.init_armed {
            self.init_armed = false;
            self.init_pending = true;
        }
    }
    pub fn take(&mut self) -> Option<&'static str> {
        if std::mem::take(&mut self.pending10) {
            Some("notice-battery10")
        } else if std::mem::take(&mut self.init_pending) {
            Some("notice-init-success")
        } else if std::mem::take(&mut self.pending20) {
            Some("notice-battery20")
        } else {
            None
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn battery_warns_once_below_each_threshold() {
        let mut n = Notices::default();
        n.battery(20.0);
        assert_eq!(n.take(), None);
        n.battery(19.0);
        assert_eq!(n.take(), Some("notice-battery20"));
        n.battery(15.0);
        assert_eq!(n.take(), None);
        n.battery(10.0);
        assert_eq!(n.take(), None);
        n.battery(9.0);
        assert_eq!(n.take(), Some("notice-battery10"));
        n.battery(8.0);
        assert_eq!(n.take(), None);
    }
    #[test]
    fn startup_below_ten_only_plays_critical_notice() {
        let mut n = Notices::default();
        n.battery(8.0);
        assert_eq!(n.take(), Some("notice-battery10"));
        assert_eq!(n.take(), None);
        n.battery(f64::NAN);
        n.battery(-1.0);
        assert_eq!(n.take(), None);
    }
    #[test]
    fn recharge_rearms_but_small_fluctuations_do_not() {
        let mut n = Notices::default();
        n.battery(19.0);
        n.take();
        n.battery(20.0);
        n.battery(19.0);
        assert_eq!(n.take(), None);
        n.battery(22.0);
        n.battery(19.0);
        assert_eq!(n.take(), Some("notice-battery20"));
    }
    #[test]
    fn init_speech_requires_a_request_and_confirmed_completion() {
        let mut n = Notices::default();
        n.confirm_init(true);
        assert_eq!(n.take(), None);
        n.begin_init();
        n.confirm_init(false);
        assert_eq!(n.take(), None);
        n.confirm_init(true);
        assert_eq!(n.take(), Some("notice-init-success"));
        n.confirm_init(true);
        assert_eq!(n.take(), None);
        n.begin_init();
        n.cancel_init();
        n.confirm_init(true);
        assert_eq!(n.take(), None);
    }
}
