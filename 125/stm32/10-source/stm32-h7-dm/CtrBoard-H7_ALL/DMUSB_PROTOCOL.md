# DM USB motor gateway

The H7 uses the binary USB CDC framing from `STM32_from_166`:

- magic `0x4D47`, version `4`, 18-byte little-endian header;
- CRC16-CCITT (`init=0xFFFF`, polynomial `0x1021`), with the CRC field zeroed;
- host command message `1`, STM32 state message `2`;
- admin enable/disable message `12` and result message `13`;
- no set/get-mode messages. Motor commands are always MIT (`mode=1`).

USB commands and states run at 50 Hz. `motor_task` and `imu_task` remain 1 ms tasks and
repeats the most recently accepted MIT command independently of USB timing.

## IMU observation

Version 4 uses a 64-byte state prefix. Bytes `16..64` contain:

| Offset | Type | Meaning |
| --- | --- | --- |
| 16..28 | `float32[3]` | `base_ang_vel`, body X/Y/Z angular rate in rad/s |
| 28..40 | `float32[3]` | `projected_gravity`, world `[0,0,-1]` in the body frame |
| 40..56 | `float32[4]` | body-to-world quaternion, scalar-first `[w,x,y,z]` |
| 56..60 | `uint32` | 1 kHz IMU sample sequence |
| 60 | `uint8` | flags: bit 0 sensor OK, bit 1 gyro calibrated, bit 2 magnetometer valid |
| 61..64 | bytes | reserved, zero |

Motor observations immediately follow at byte 64. The BMI088 task samples at 1 kHz,
applies a 30 Hz one-pole low-pass, and runs Mahony fusion. USB takes the latest atomic
snapshot every 20 ms without independently delaying angular velocity or projected
gravity relative to its quaternion. Same-tick catch-up iterations are skipped;
a task gap up to 50 ms uses its actual elapsed time for fusion. A longer gap
invalidates IMU readiness until 500 consecutive valid samples arrive.
Gyro bias calibration accepts only consecutive stationary samples, and the ready
flag waits for the equivalent of 25 valid 50 Hz observation periods. The onboard
BMI088 has no magnetometer, so the normal board configuration uses Mahony's 6DoF
gyro/accelerometer path. `IMU_SetMagnetometer` accepts a future calibrated external
magnetometer and selects the full 9DoF path without another wire-format change.

## Joint and FDCAN routing

The Rider Mini state array has 12 fixed route slots, ordered by motor number:

| Protocol slots | Group | FDCAN | Motor CAN IDs |
| --- | --- | --- | --- |
| 0, 2, 4, 6, 8, 10 | right joints | 1 | `0x01, 0x03, 0x05, 0x07, 0x09, 0x0B` |
| 1, 3, 5, 7, 9, 11 | left joints | 2 | `0x02, 0x04, 0x06, 0x08, 0x0A, 0x0C` |

FDCAN1 and FDCAN2 retain their existing bus timing and classic CAN motor protocol.
FDCAN3 has no Rider Mini motor route.

The command and per-motor records remain byte-compatible with the 166 format. The
state prefix is intentionally versioned. V4 carries the body-to-world quaternion directly
and removes the V3 RPY round trip.
