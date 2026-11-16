//! Yesense YIS USB stream, independent of STM32 DMUSB framing and pacing.
use std::{io::Read, sync::{Arc, Mutex, atomic::{AtomicBool, Ordering}}, time::{Duration, Instant}};
use crate::{imu::ImuData, io::{IoError, Result}};

const MAX_AGE: Duration = Duration::from_millis(100);

#[derive(Clone, Copy)]
struct Sample { imu: ImuData, sequence: u16 }

#[derive(Default)]
struct Parser { buffer: Vec<u8> }

impl Parser {
    fn feed(&mut self, bytes: &[u8]) -> Vec<Sample> {
        self.buffer.extend_from_slice(bytes);
        let mut samples = Vec::new();
        loop {
            let Some(start) = self.buffer.windows(2).position(|w| w == [0x59, 0x53]) else {
                let partial = self.buffer.last() == Some(&0x59);
                self.buffer.clear();
                if partial { self.buffer.push(0x59); }
                break;
            };
            self.buffer.drain(..start);
            if self.buffer.len() < 7 { break; }
            let len = 7 + self.buffer[4] as usize;
            if self.buffer.len() < len { break; }
            let frame = &self.buffer[..len];
            let (mut a, mut b) = (0u8, 0u8);
            for &value in &frame[2..len-2] { a = a.wrapping_add(value); b = b.wrapping_add(a); }
            if frame[len-2..] != [a, b] {
                self.buffer.drain(..1);
                continue;
            }
            if let Some(sample) = decode(frame) { samples.push(sample); }
            self.buffer.drain(..len);
        }
        samples
    }
}

fn decode(frame: &[u8]) -> Option<Sample> {
    let mut acceleration = None;
    let mut gyro = None;
    let mut quat = None;
    let payload = &frame[5..frame.len()-2];
    let mut offset = 0;
    while offset < payload.len() {
        let id = *payload.get(offset)?;
        let len = *payload.get(offset+1)? as usize;
        let data = payload.get(offset+2..offset+2+len)?;
        let values = || data.chunks_exact(4).map(|b| i32::from_le_bytes(b.try_into().unwrap()) as f64 * 1e-6).collect::<Vec<_>>();
        match id {
            0x10 | 0x20 => {
                if len != 12 { return None; }
                let v = values();
                let v = [v[0], v[1], v[2]];
                if id == 0x10 { acceleration = Some(v); }
                else { gyro = Some(v.map(f64::to_radians)); }
            }
            0x41 => {
                if len != 16 { return None; }
                let v = values();
                let norm = v.iter().map(|x| x*x).sum::<f64>().sqrt();
                if !(0.5..=1.5).contains(&norm) { return None; }
                quat = Some([v[0]/norm, v[1]/norm, v[2]/norm, v[3]/norm]);
            }
            _ => {},
        }
        offset += 2 + len;
    }
    let quat = quat?;
    let [w,x,y,z] = quat;
    // q is body->ENU world, so gravity in body is q^-1 * [0,0,-1] * q.
    let gravity = [2.0*(w*y-x*z), -2.0*(y*z+w*x), -(1.0-2.0*(x*x+y*y))];
    Some(Sample { sequence: u16::from_le_bytes([frame[2],frame[3]]),
        imu: ImuData { gyro: gyro?, acceleration: acceleration?, quat, gravity } })
}

#[derive(Default)]
struct Latest {
    sample: Option<(ImuData, Instant)>,
    sequence: Option<u16>,
    generation: u32,
    connection: u32,
}
impl Latest {
    fn observe(&mut self, sample: Sample, now: Instant) {
        // Duplicate packets must not refresh freshness; wraparound is normal.
        if self.sequence == Some(sample.sequence) { return; }
        self.sequence = Some(sample.sequence);
        self.generation = self.generation.wrapping_add(1);
        self.sample = Some((sample.imu, now));
    }
    fn get(&self, now: Instant) -> Option<(ImuData, u32, u32)> {
        self.sample.filter(|(_, at)| now.saturating_duration_since(*at) < MAX_AGE)
            .map(|(imu, _)| (imu, self.generation, self.connection))
    }
    fn disconnect(&mut self) {
        self.sample = None; self.sequence = None;
        self.connection = self.connection.wrapping_add(1);
    }
}

pub(crate) struct UsbImu { latest: Arc<Mutex<Latest>>, stop: Arc<AtomicBool> }
impl UsbImu {
    pub(crate) fn start(path: &str) -> Result<Self> {
        if path.is_empty() { return Err(IoError::Bus("Yesense USB IMU port is required".into())); }
        let latest = Arc::new(Mutex::new(Latest::default()));
        let stop = Arc::new(AtomicBool::new(false));
        let (slot, cancelled, path) = (latest.clone(), stop.clone(), path.to_owned());
        std::thread::Builder::new().name("yesense-usb".into()).spawn(move || {
            while !cancelled.load(Ordering::Relaxed) {
                if let Ok(mut port) = serialport::new(&path, 460_800)
                    .data_bits(serialport::DataBits::Eight).parity(serialport::Parity::None)
                    .stop_bits(serialport::StopBits::One).timeout(Duration::from_millis(20)).open() {
                    let mut parser = Parser::default();
                    let mut bytes = [0u8; 1024];
                    while !cancelled.load(Ordering::Relaxed) {
                        match port.read(&mut bytes) {
                            Ok(0) => std::thread::sleep(Duration::from_millis(1)),
                            Ok(n) => {
                                let samples = parser.feed(&bytes[..n]);
                                let mut latest = slot.lock().unwrap();
                                for sample in samples { latest.observe(sample, Instant::now()); }
                            }
                            Err(e) if matches!(e.kind(), std::io::ErrorKind::TimedOut | std::io::ErrorKind::Interrupted) => {},
                            Err(_) => break,
                        }
                    }
                }
                slot.lock().unwrap().disconnect();
                // Reopen after hotplug, without spinning or blocking the control loop.
                for _ in 0..100 {
                    if cancelled.load(Ordering::Relaxed) { return; }
                    std::thread::sleep(Duration::from_millis(10));
                }
            }
        }).map_err(|e| IoError::Bus(format!("cannot start USB IMU reader: {e}")))?;
        Ok(Self { latest, stop })
    }
    #[cfg(test)]
    pub(crate) fn fixture(imu: Option<ImuData>) -> Self {
        Self::fixture_with_connection(imu, 0)
    }
    #[cfg(test)]
    pub(crate) fn fixture_with_connection(imu: Option<ImuData>, connection: u32) -> Self {
        let mut latest = Latest { connection, ..Latest::default() };
        if let Some(imu) = imu { latest.observe(Sample { imu, sequence: 1 }, Instant::now()); }
        Self { latest: Arc::new(Mutex::new(latest)), stop: Arc::new(AtomicBool::new(false)) }
    }
    pub(crate) fn latest(&self) -> Option<(ImuData,u32,u32)> {
        self.latest.lock().unwrap().get(Instant::now())
    }
}
impl Drop for UsbImu {
    fn drop(&mut self) {
        // Never join a possibly stuck USB driver from the safety/control thread.
        self.stop.store(true, Ordering::Relaxed);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn frame(sequence: u16, q: [i32;4], omit_gyro: bool) -> Vec<u8> {
        let mut payload = Vec::new();
        let mut add = |id, v: &[i32]| {
            payload.extend([id, (v.len()*4) as u8]);
            for x in v { payload.extend(x.to_le_bytes()); }
        };
        add(0x10, &[1_000_000,2_000_000,9_810_000]);
        if !omit_gyro { add(0x20, &[180_000_000,0,-90_000_000]); }
        add(0x41, &q);
        let mut f = vec![0x59,0x53]; f.extend(sequence.to_le_bytes()); f.push(payload.len() as u8); f.extend(payload);
        let (mut a,mut b)=(0u8,0u8);
        for &v in &f[2..] { a=a.wrapping_add(v); b=b.wrapping_add(a); }
        f.extend([a,b]); f
    }
    #[test]
    fn units_orientation_and_fragmented_stream() {
        let f=frame(65535,[1_000_000,0,0,0],false);
        let mut p=Parser::default();
        assert!(p.feed(&[0,1,0x59]).is_empty());
        assert!(p.feed(&f[..6]).is_empty());
        let sample=p.feed(&f[6..]).remove(0);
        for (actual, expected) in sample.imu.acceleration.iter().zip([1.0,2.0,9.81]) {
            assert!((actual-expected).abs()<1e-12);
        }
        assert!((sample.imu.gyro[0]-std::f64::consts::PI).abs()<1e-12);
        assert_eq!(sample.imu.quat,[1.0,0.0,0.0,0.0]);
        assert_eq!(sample.imu.gravity,[0.0,-0.0,-1.0]);
        let pitch=p.feed(&frame(0,[707107,0,707107,0],false)).remove(0);
        assert!((pitch.imu.gravity[0]-1.0).abs()<1e-9);
        assert!(pitch.imu.gravity[2].abs()<1e-9);
    }
    #[test]
    fn corruption_missing_fields_and_zero_quaternion_do_not_publish() {
        let mut p=Parser::default();
        let mut bad=frame(1,[1_000_000,0,0,0],false); bad[10]^=1;
        let mut bytes=bad; bytes.extend(frame(2,[0;4],false)); bytes.extend(frame(3,[1_000_000,0,0,0],true));
        bytes.extend(frame(4,[1_000_000,0,0,0],false));
        let samples=p.feed(&bytes); assert_eq!(samples.len(),1); assert_eq!(samples[0].sequence,4);
    }
    #[test]
    fn duplicates_expiry_disconnect_and_sequence_wrap() {
        let now=Instant::now(); let mut l=Latest::default();
        let s=decode(&frame(65535,[1_000_000,0,0,0],false)).unwrap();
        l.observe(s,now); l.observe(s,now+Duration::from_millis(90));
        assert!(l.get(now+MAX_AGE).is_none());
        l.observe(decode(&frame(0,[1_000_000,0,0,0],false)).unwrap(),now+MAX_AGE);
        assert_eq!(l.get(now+MAX_AGE).unwrap().1,2);
        l.disconnect(); assert!(l.get(now+MAX_AGE).is_none());
        l.observe(s,now+MAX_AGE); assert!(l.get(now+MAX_AGE).is_some());
        assert_eq!(l.get(now+MAX_AGE).unwrap().2,1, "reconnect epoch survives fresh samples");
    }
    #[cfg(unix)]
    #[test]
    fn serial_reader_accepts_stream_and_expires_after_disconnect() {
        use serialport::SerialPort;
        use std::io::Write;
        let (mut device, host) = serialport::TTYPort::pair().unwrap();
        let reader = UsbImu::start(&host.name().unwrap()).unwrap();
        let deadline = Instant::now() + Duration::from_secs(2);
        let mut sequence = 0;
        while reader.latest().is_none() && Instant::now() < deadline {
            device.write_all(&frame(sequence,[1_000_000,0,0,0],false)).unwrap();
            sequence += 1;
            std::thread::sleep(Duration::from_millis(10));
        }
        assert!(reader.latest().is_some(), "reader must ingest serial bytes");
        drop(device);
        std::thread::sleep(MAX_AGE + Duration::from_millis(30));
        assert!(reader.latest().is_none(), "disconnect must not retain ready data");
    }

    #[test]
    fn actual_jetson186_capture_decodes() {
        let hex="595313cc3c100c958cf9ffff49010074689500200c5e61000078b50200066c0400400ca25c2700d0e20700e06f80f94110ceda0800d1510000b42400000394f3ff10d9";
        let bytes=(0..hex.len()).step_by(2).map(|i| u8::from_str_radix(&hex[i..i+2],16).unwrap()).collect::<Vec<_>>();
        let samples=Parser::default().feed(&bytes); assert_eq!(samples.len(),1);
        assert!((samples[0].imu.acceleration[2]-9.791604).abs()<1e-6);
        assert_eq!(samples[0].sequence,52243);
        assert!((samples[0].imu.gravity.iter().map(|x| x*x).sum::<f64>()-1.0).abs()<1e-9);
    }
}
