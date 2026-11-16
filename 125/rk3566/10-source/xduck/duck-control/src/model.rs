//! The robot, as data.
//!
//! Rider Mini's twelve motor joints in physical motor-ID order.

pub const NUM_JOINTS: usize = 12;

/// Array index plus one is the physical motor ID.
pub const JOINT_NUMBERS: [u8; NUM_JOINTS] = [
    1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
];

/// Joint names, from the protocol crate — the wire indexes `joints` and `targets`
/// positionally, so that order and this one cannot be allowed to drift apart. The
/// assertion below is what makes "cannot" true.
pub use duck_ipc_proto::JOINT_NAMES;

const _: () = assert!(JOINT_NAMES.len() == NUM_JOINTS);

/// Current standing pose from Rider Mini 186 deployment, in motor-ID order.
/// A future policy's training home frame must be checked against this table.
pub const DEFAULT_POSITION: [f64; NUM_JOINTS] = [
    0.308279, -0.308279,
    0.0, 0.0,
    0.0, 0.0,
    0.300000, -0.300000,
    0.207704, -0.207704,
    0.152691, -0.152691,
];

/// MIT software limits from Rider Mini 186 deployment, not mechanical hard stops.
pub const DEFAULT_MIT_LIMITS: [(f64, f64); NUM_JOINTS] = [
    (-1.80, 2.00), (-2.00, 1.80),
    (-0.50, 0.50), (-0.50, 0.50),
    (-3.80, 3.30), (-3.30, 3.80),
    (-1.10, 0.75), (-0.75, 1.10),
    (-0.80, 1.10), (-1.10, 0.80),
    (-1.00, 1.43), (-1.43, 1.00),
];

/// Legacy independent IMU ID, retained for persisted configuration compatibility.
/// DMUSB v4 takes its IMU sample from the STM32 USB state frame.
pub const IMU_DXL_ID: u8 = 200;

pub const BAUD_RATE: u32 = 1_000_000;

/// EEPROM registers asserted (and corrected) at startup.
///
/// `return_delay_time` is the load-bearing one: the XL330 ships at 250, which is 500 µs of
/// turnaround *per device*. Across 16 devices that is 8 ms per tick — 40% of a 20 ms budget
/// — spent waiting for servos to get around to answering. The rest are here because the
/// runtime found them worth pinning; `shutdown = 52` is the error mask that latches on
/// overload, overheating and input-voltage faults.
pub const EXPECTED_REGISTERS: &[(&str, u8)] = &[
    ("return_delay_time", 0),
    ("baud_rate", 3), // 3 = 1 Mbps, must agree with BAUD_RATE
    ("pwm_slope", 255),
    ("shutdown", 52),
];

/// Index of a joint by name.
pub fn joint_index(name: &str) -> Option<usize> {
    JOINT_NAMES.iter().position(|n| *n == name)
}

// ── battery ──────────────────────────────────────────────────────────────────
//
// Legacy 2S motor-bus mapping for backends that still report supply voltage.
// The current STM32 robot uses a 7S pack and forwards the external meter's own
// percentage separately; this mapping must never be applied to its meter voltage.

/// Off a full charge, under load. NP-F550, 2S Li-ion.
pub const BATTERY_FULL_V: f64 = 8.2;

/// The sag floor: below this the robot starts struggling, well before the pack's own
/// protection trips. Empty for our purposes, not empty for the cells'.
pub const BATTERY_EMPTY_V: f64 = 6.6;

/// Fraction of a pack, 0–100, for a bus voltage.
///
/// Linear, and the numbers come from `microduck_runtime`'s `check_battery`, where they were
/// arrived at by running a duck flat. It lives here rather than in `robotd` so there is one
/// mapping: the prototype had it in a CLI *and* re-derived in the app, which is how two
/// screens end up disagreeing about the same pack.
///
/// A non-finite or non-positive reading is 0 — those mean "no answer from the bus", and the
/// caller is expected to report that as unknown rather than to display this number.
pub fn battery_percent(volts: f64) -> f64 {
    if !volts.is_finite() || volts <= 0.0 {
        return 0.0;
    }
    ((volts - BATTERY_EMPTY_V) / (BATTERY_FULL_V - BATTERY_EMPTY_V)).clamp(0.0, 1.0) * 100.0
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The three tables are indexed by the same integer everywhere in the crate. If they
    /// ever diverge in length, every lookup silently reads the wrong joint.
    #[test]
    fn tables_agree_on_length() {
        assert_eq!(JOINT_NUMBERS.len(), NUM_JOINTS);
        assert_eq!(JOINT_NAMES.len(), NUM_JOINTS);
        assert_eq!(DEFAULT_POSITION.len(), NUM_JOINTS);
    }

    /// Operator-facing joint numbers match physical motor IDs.
    #[test]
    fn joint_numbers_are_unique_and_contiguous() {
        let mut seen = JOINT_NUMBERS;
        seen.sort_unstable();
        assert_eq!(seen, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]);
        assert_eq!(JOINT_NAMES[0], "right_hip_pitch");
        assert_eq!(JOINT_NAMES[11], "left_foot_pitch");
    }

    /// The ends of the span and the middle of it. Getting the direction wrong here would
    /// report a full pack as flat, which is the kind of thing nobody double-checks.
    #[test]
    fn battery_percent_spans_the_usable_range() {
        assert_eq!(battery_percent(BATTERY_FULL_V), 100.0);
        assert_eq!(battery_percent(BATTERY_EMPTY_V), 0.0);
        assert!((battery_percent(7.4) - 50.0).abs() < 0.001);
    }

    /// Voltages outside the span are ordinary — a fresh pack reads over 8.2 V off the
    /// charger, and a robot being run into the ground reads under 6.6 V. Neither may
    /// produce a percentage outside 0–100 for a caller to display.
    #[test]
    fn battery_percent_clamps_rather_than_extrapolating() {
        assert_eq!(battery_percent(9.5), 100.0);
        assert_eq!(battery_percent(5.0), 0.0);
    }

    /// A bus that did not answer arrives here as 0.0, and NaN is what a mean over an empty
    /// set produces. Both must be 0 rather than a wild number a caller might print.
    #[test]
    fn battery_percent_treats_no_reading_as_zero() {
        assert_eq!(battery_percent(0.0), 0.0);
        assert_eq!(battery_percent(f64::NAN), 0.0);
        assert_eq!(battery_percent(-1.0), 0.0);
    }

    /// The legs are mirrored: the corresponding poses are equal and opposite. A sign
    /// typo in the home pose is invisible by inspection and makes the robot stand crooked.
    #[test]
    fn home_pose_legs_are_mirrored() {
        for (left, right) in [
            ("left_hip_roll", "right_hip_roll"),
            ("left_hip_pitch", "right_hip_pitch"),
            ("left_knee_pitch", "right_knee_pitch"),
            ("left_shank_pitch", "right_shank_pitch"),
            ("left_foot_pitch", "right_foot_pitch"),
        ] {
            let l = DEFAULT_POSITION[joint_index(left).unwrap()];
            let r = DEFAULT_POSITION[joint_index(right).unwrap()];
            assert!(
                (l + r).abs() < 1e-9,
                "{left} ({l}) and {right} ({r}) should be equal and opposite"
            );
        }
    }

    #[test]
    fn standing_pose_is_inside_each_mit_limit() {
        for (home, (min, max)) in DEFAULT_POSITION.into_iter().zip(DEFAULT_MIT_LIMITS) {
            assert!(min <= home && home <= max);
        }
    }
}
