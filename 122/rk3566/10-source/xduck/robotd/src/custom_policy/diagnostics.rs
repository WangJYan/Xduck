//! Failure-only work. Never scan procfs, signal Python, wait for late replies or
//! export traces on the motor control thread.
use std::{collections::BTreeMap, path::Path, process::Child, sync::{Arc, Mutex, mpsc}, time::Duration};
use serde::Serialize;
use serde_json::{Value, json};

pub(super) type Lines = mpsc::Receiver<(Result<String, String>, u64)>;

#[derive(Clone, Debug, Serialize)]
pub(super) struct Identity {
    pub pid: u32,
    pub start_ticks: u64,
}

#[derive(Default, Serialize)]
pub(super) struct Request {
    pub action: String,
    pub model: String,
    pub sequence: u64,
    pub request_started_ns: u64,
    pub host_written_ns: u64,
    pub control_tid: u32,
}

#[derive(Serialize)]
pub(super) struct Incident {
    pub request: Request,
    pub parent_pid: u32,
    pub worker: Option<Identity>,
    pub timeout_ns: u64,
    pub deadline_ms: u64,
    #[serde(skip)]
    pub lines: Lines,
    // Keep the creator of --die-with-parent alive through the diagnostic grace.
    #[serde(skip)]
    pub keepalive: Option<mpsc::Sender<()>>,
}

pub(super) fn monitor(child: Arc<Mutex<Child>>) -> std::io::Result<mpsc::SyncSender<Incident>> {
    let (send, receive) = mpsc::sync_channel::<Incident>(1);
    std::thread::Builder::new().name("policy-diag".into()).spawn(move || {
        if let Err(error) = crate::scheduling::ipc_affinity() {
            tracing::error!(%error, "cannot move policy diagnostics off the control CPU");
            return;
        }
        #[cfg(target_os = "linux")]
        if unsafe { libc::setpriority(libc::PRIO_PROCESS, 0, 10) } != 0 {
            tracing::warn!("cannot lower policy diagnostic thread priority");
        }
        // A worker fails once. This thread also exits when a healthy worker is dropped.
        if let Ok(incident) = receive.recv() {
            tracing::error!("policy-timeout-event {}", serde_json::to_string(&incident).unwrap());
            let stack_signal_sent = incident.worker.as_ref().is_some_and(signal_stack);
            tracing::warn!(parent_pid = incident.parent_pid, stack_signal_sent,
                "policy timeout stack request result");
            let late = incident.lines.recv_timeout(Duration::from_millis(100));
            match late {
                Ok((Ok(line), reader_received_ns)) => {
                    let reply = serde_json::from_str::<Value>(&line);
                    let details = match reply {
                        Ok(reply) => json!({"request": incident.request,
                            "timeout_ns": incident.timeout_ns,
                            "reader_received_ns": reader_received_ns,
                            "ok": reply.get("ok"), "error": reply.get("error"),
                            "timing": reply.get("timing")}),
                        Err(error) => json!({"timeout_ns":incident.timeout_ns,
                            "parse_error":error.to_string()}),
                    };
                    tracing::warn!("policy-timeout-late-reply {}", details);
                }
                other => tracing::warn!(timeout_ns = incident.timeout_ns,
                    result = ?other.err(), "policy timeout had no late reply"),
            }
            if let Ok(mut child) = child.lock() {
                let _ = child.kill();
                let status = child.wait();
                tracing::warn!(timeout_ns = incident.timeout_ns, ?status,
                    "timed-out policy worker reaped; late targets were discarded");
            }
            drop(incident.keepalive);
        }
    })?;
    Ok(send)
}

pub(super) fn control_tid() -> u32 {
    #[cfg(target_os = "linux")]
    { unsafe { libc::syscall(libc::SYS_gettid) as u32 } }
    #[cfg(not(target_os = "linux"))]
    { std::process::id() }
}

fn stat(text: &str) -> Option<(u32, String, u32, u64)> {
    let (pid, tail) = text.split_once(" (")?;
    let (comm, fields) = tail.rsplit_once(") ")?;
    let fields: Vec<_> = fields.split_whitespace().collect();
    Some((pid.parse().ok()?, comm.into(), fields.get(1)?.parse().ok()?,
        fields.get(19)?.parse().ok()?))
}

// The children file is empty at the bwrap namespace boundary on the K11C kernel.
// Resolve all host-side PPids once, at load time, not on an expired control tick.
pub(super) fn python_identity(proc: &Path, parent: u32) -> Option<Identity> {
    let mut children = BTreeMap::<u32, Vec<(u32, String, u64)>>::new();
    for entry in std::fs::read_dir(proc).ok()?.flatten() {
        if !entry.file_name().to_string_lossy().bytes().all(|c| c.is_ascii_digit()) { continue; }
        let Ok(text) = std::fs::read_to_string(entry.path().join("stat")) else { continue; };
        if let Some((pid, name, ppid, start)) = stat(&text) {
            children.entry(ppid).or_default().push((pid, name, start));
        }
    }
    let mut pending = vec![parent];
    for _ in 0..32 {
        let next = pending.pop()?;
        for (pid, name, start_ticks) in children.get(&next).into_iter().flatten() {
            if name.starts_with("python") && *pid > 1 {
                return Some(Identity { pid: *pid, start_ticks: *start_ticks });
            }
            pending.push(*pid);
        }
    }
    None
}

fn same_process(proc: &Path, identity: &Identity) -> bool {
    if identity.pid <= 1 { return false; }
    std::fs::read_to_string(proc.join(identity.pid.to_string()).join("stat"))
        .ok().and_then(|s| stat(&s)).is_some_and(|(pid, name, _, start)|
            pid == identity.pid && name.starts_with("python") && start == identity.start_ticks)
}

fn signal_stack(identity: &Identity) -> bool {
    // pidfd pins the process identity across validation and signaling. Never fall
    // back to kill(pid) when pidfd is unavailable: that would reintroduce PID reuse.
    #[cfg(target_os = "linux")]
    unsafe {
        let fd = libc::syscall(libc::SYS_pidfd_open, identity.pid, 0) as libc::c_int;
        if fd < 0 { return false; }
        let valid = same_process(Path::new("/proc"), identity);
        let sent = valid && libc::syscall(libc::SYS_pidfd_send_signal, fd,
            libc::SIGUSR1, std::ptr::null::<libc::siginfo_t>(), 0) == 0;
        libc::close(fd);
        sent
    }
    #[cfg(not(target_os = "linux"))]
    { let _ = identity; false }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn fake_stat(pid: u32, name: &str, parent: u32, start: u64) -> String {
        let mut fields = vec!["0".to_owned(); 20];
        fields[0] = "S".into(); fields[1] = parent.to_string(); fields[19] = start.to_string();
        format!("{pid} ({name}) {}", fields.join(" "))
    }
    #[test]
    fn host_ppid_map_crosses_namespace_boundary_and_searches_siblings() {
        let root = tempfile::tempdir().unwrap();
        for (pid, name, parent) in [(10,"bwrap",1),(11,"helper",10),(12,"bwrap",10),(13,"python (worker)",12)] {
            let dir = root.path().join(pid.to_string()); std::fs::create_dir(&dir).unwrap();
            std::fs::write(dir.join("stat"), fake_stat(pid,name,parent,100)).unwrap();
        }
        let identity = python_identity(root.path(),10).unwrap();
        assert_eq!(identity.pid,13);
        assert!(same_process(root.path(),&identity));
        std::fs::write(root.path().join("13/stat"),fake_stat(13,"python",12,101)).unwrap();
        assert!(!same_process(root.path(),&identity));
        assert!(python_identity(root.path(),99).is_none());
    }

    #[cfg(target_os = "linux")]
    #[test]
    #[ignore = "root/bwrap PID namespace test; Python only, no model, robot socket or hardware IO"]
    fn namespace_pidfd_stack_dump_reaches_python() {
        use std::io::{BufRead, BufReader, Read};
        use std::process::{Command, Stdio};
        let mut child = Command::new("/usr/bin/bwrap")
            .args(["--die-with-parent", "--unshare-pid", "--unshare-net",
                "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
                "--tmpfs", "/run", "--", "/usr/bin/python3", "-u", "-c",
                "import faulthandler,signal,time; faulthandler.register(signal.SIGUSR1); print('ready',flush=True); time.sleep(1)"])
            .stdout(Stdio::piped()).stderr(Stdio::piped()).spawn().unwrap();
        let mut line = String::new();
        BufReader::new(child.stdout.take().unwrap()).read_line(&mut line).unwrap();
        assert_eq!(line.trim(), "ready");
        let identity = python_identity(Path::new("/proc"), child.id()).unwrap();
        assert_ne!(identity.pid, child.id());
        assert!(signal_stack(&identity), "pidfd must signal the host Python PID");
        assert!(child.wait().unwrap().success());
        let mut stack = String::new();
        child.stderr.take().unwrap().read_to_string(&mut stack).unwrap();
        assert!(stack.contains("<module>"), "{stack}");
    }
}
