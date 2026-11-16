//! Own a temporary devfreq floor without touching motor IO.
use std::{fs::{self, File, OpenOptions}, io, os::fd::AsRawFd, path::{Path, PathBuf}};
use serde::{Deserialize, Serialize};

const MIN: &str = "/sys/class/devfreq/dmc/min_freq";
const RECORD: &str = "/run/robotd-ddr.json";
const LOCK: &str = "/run/robotd-ddr.lock";

#[derive(Serialize, Deserialize)]
struct Saved { original: u64, applied: u64 }

fn read_number(path: &Path) -> io::Result<u64> {
    fs::read_to_string(path)?.trim().parse().map_err(io::Error::other)
}
fn lock(path: &Path) -> io::Result<File> {
    let file = OpenOptions::new().read(true).write(true).create(true).truncate(false).open(path)?;
    if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(file)
}
fn restore_locked(min: &Path, record: &Path) -> io::Result<()> {
    let bytes = match fs::read(record) {
        Ok(bytes) => bytes,
        Err(e) if e.kind() == io::ErrorKind::NotFound => return Ok(()),
        Err(e) => return Err(e),
    };
    let saved: Saved = serde_json::from_slice(&bytes).map_err(io::Error::other)?;
    let current = read_number(min)?;
    if current == saved.applied {
        fs::write(min, saved.original.to_string())?;
        tracing::info!(minimum_hz=saved.original, "DDR floor restored");
    } else {
        tracing::warn!(current_hz=current, owned_hz=saved.applied, "DDR floor changed externally; leaving external value untouched");
    }
    fs::remove_file(record)
}

pub fn restore() -> io::Result<()> {
    let _lock = lock(Path::new(LOCK))?;
    restore_locked(Path::new(MIN), Path::new(RECORD))
}

pub struct Floor {
    target: Option<u64>,
    min: PathBuf,
    record: PathBuf,
    lock_path: PathBuf,
    owned: Option<File>,
    requested: bool,
}
impl Floor {
    pub fn configured(real_hardware: bool) -> Self {
        let target = real_hardware.then(|| std::env::var("ROBOT_DDR_MIN_HZ").ok())
            .flatten().and_then(|v| v.parse::<u64>().ok()).filter(|v| *v > 0);
        Self { target, min: MIN.into(), record: RECORD.into(), lock_path: LOCK.into(), owned: None, requested: false }
    }
    fn acquire(&mut self) -> io::Result<()> {
        let Some(target) = self.target else { return Ok(()); };
        let file = lock(&self.lock_path)?;
        restore_locked(&self.min, &self.record)?;
        let directory = self.min.parent().unwrap();
        let available = fs::read_to_string(directory.join("available_frequencies"))?;
        if !available.split_whitespace().any(|v| v.parse::<u64>() == Ok(target)) {
            return Err(io::Error::other("requested DDR floor is not an available frequency"));
        }
        let original = read_number(&self.min)?;
        let applied = original.max(target);
        if read_number(&directory.join("max_freq"))? < applied {
            return Err(io::Error::other("DDR maximum is below requested floor"));
        }
        let temporary = self.record.with_extension("tmp");
        fs::write(&temporary, serde_json::to_vec(&Saved { original, applied }).map_err(io::Error::other)?)?;
        fs::rename(temporary, &self.record)?;
        self.owned = Some(file);
        fs::write(&self.min, applied.to_string())?;
        tracing::info!(minimum_hz=applied, previous_hz=original, "DDR policy floor acquired");
        Ok(())
    }
    fn release(&mut self) -> io::Result<()> {
        if self.owned.is_some() {
            restore_locked(&self.min, &self.record)?;
            self.owned = None;
        }
        Ok(())
    }
    pub fn set_active(&mut self, active: bool) {
        if self.target.is_none() || self.requested == active { return; }
        self.requested = active;
        let result = if active { self.acquire() } else { self.release() };
        if let Err(error) = result {
            tracing::error!(%error, active, "DDR performance request failed; runtime deadline unchanged");
        }
    }
}
impl Drop for Floor {
    fn drop(&mut self) {
        if let Err(error) = self.release() { tracing::error!(%error, "DDR cleanup failed; service exit hook will retry"); }
    }
}

pub fn check() -> io::Result<()> {
    let mut floor = Floor::configured(true);
    if floor.target.is_none() { return Err(io::Error::other("ROBOT_DDR_MIN_HZ is required")); }
    floor.acquire()?;
    let target = floor.target.unwrap();
    if read_number(Path::new(MIN))? < target { return Err(io::Error::other("DDR floor readback failed")); }
    floor.release()
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fixture() -> (tempfile::TempDir, Floor) {
        let dir=tempfile::tempdir().unwrap();let p=dir.path();
        fs::write(p.join("min_freq"),"324000000").unwrap();
        fs::write(p.join("max_freq"),"1056000000").unwrap();
        fs::write(p.join("available_frequencies"),"324000000 528000000 780000000 1056000000").unwrap();
        let floor=Floor{target:Some(780000000),min:p.join("min_freq"),record:p.join("lease.json"),lock_path:p.join("lease.lock"),owned:None,requested:false};
        (dir,floor)
    }
    #[test]
    fn acquire_release_and_drop_restore_original() {
        let (dir,mut floor)=fixture();floor.set_active(true);
        assert_eq!(read_number(&floor.min).unwrap(),780000000);
        floor.set_active(true);floor.set_active(false);
        assert_eq!(read_number(&floor.min).unwrap(),324000000);
        floor.set_active(true);drop(floor);
        assert_eq!(read_number(&dir.path().join("min_freq")).unwrap(),324000000);
    }
    #[test]
    fn existing_higher_floor_and_external_change_are_preserved() {
        let (_dir,mut floor)=fixture();fs::write(&floor.min,"1056000000").unwrap();
        floor.acquire().unwrap();floor.release().unwrap();assert_eq!(read_number(&floor.min).unwrap(),1056000000);
        fs::write(&floor.min,"324000000").unwrap();floor.acquire().unwrap();
        fs::write(&floor.min,"1056000000").unwrap();floor.release().unwrap();
        assert_eq!(read_number(&floor.min).unwrap(),1056000000);
    }
    #[test]
    fn orphaned_record_recovers_but_live_owner_is_exclusive() {
        let (_dir,mut floor)=fixture();floor.acquire().unwrap();assert!(lock(&floor.lock_path).is_err());
        drop(floor.owned.take()); // Simulate process death releasing flock, without normal cleanup.
        let _lock=lock(&floor.lock_path).unwrap();restore_locked(&floor.min,&floor.record).unwrap();
        assert_eq!(read_number(&floor.min).unwrap(),324000000);
    }
    #[test]
    fn unsupported_floor_is_rejected_without_changing_frequency() {
        let (_dir,mut floor)=fixture();floor.target=Some(999);assert!(floor.acquire().is_err());
        assert_eq!(read_number(&floor.min).unwrap(),324000000);assert!(!floor.record.exists());
    }
    #[test]
    fn fake_hardware_never_acquires_a_floor() {
        let mut floor=Floor::configured(false);floor.set_active(true);assert!(floor.owned.is_none());
    }
}
