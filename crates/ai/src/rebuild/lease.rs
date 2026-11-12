//! A cross-process lease saying a project is being worked. RunSet keeps builders unique inside
//! one Craft; this keeps them unique across processes, and across one restarted mid-turn.
//! (2026-11-10: the builder's stub died but its turn kept working inside the agent's own
//! gateway, and the person's "continue" started a second builder over the first's files.)

use std::fs;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

/// A working run says so at least this often.
pub const HEARTBEAT: Duration = Duration::from_secs(30);
/// A holder silent past this is presumed dead, and its lease is taken over.
pub const STALE: Duration = Duration::from_secs(120);

pub struct Lease {
    path: PathBuf,
    touched: Instant,
}

fn now_ms() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_millis() as u64).unwrap_or(0)
}

impl Lease {
    fn file(root: &Path) -> PathBuf {
        root.join("craft-lease.json")
    }

    /// Take the project's lease. Err names who holds it and how long they've been silent;
    /// a lease older than STALE is taken over (and the holder is presumed dead). A RunSet
    /// replaces its own finished lease by defusing it first — never by a same-pid pass,
    /// because another RunSet (a tool server beside the app) holding a live lease is exactly
    /// who this must stop. A folder we cannot write keeps no lock: this guards builders from
    /// each other, not disk faults.
    pub fn acquire(root: &Path) -> Result<Lease, (String, String)> {
        let path = Self::file(root);
        if let Ok(body) = fs::read_to_string(&path) {
            if let Ok(v) = serde_json::from_str::<serde_json::Value>(&body) {
                let at = v.get("at_ms").and_then(|x| x.as_u64()).unwrap_or(0);
                let pid = v.get("pid").and_then(|x| x.as_u64()).unwrap_or(0);
                let silent = now_ms().saturating_sub(at);
                if silent < STALE.as_millis() as u64 {
                    return Err((
                        format!("Another builder holds this project: process {pid}, last seen {} seconds ago.", silent / 1000),
                        "Stop that build first, or wait until its lease lapses.".to_string(),
                    ));
                }
            }
        }
        let lease = Lease { path, touched: Instant::now() };
        lease.publish();
        Ok(lease)
    }

    fn publish(&self) {
        if self.path.as_os_str().is_empty() {
            return;
        }
        let body = format!("{{\"pid\":{},\"at_ms\":{}}}", std::process::id(), now_ms());
        let _ = fs::write(&self.path, body);
    }

    /// "Still here", rewritten only when the last word got old; the poll tick calls it freely.
    pub fn heartbeat(&mut self) {
        if self.touched.elapsed() >= HEARTBEAT {
            self.publish();
            self.touched = Instant::now();
        }
    }

    /// Let a deliberately replaced lease go: take back our own file first (only if it is still
    /// ours), then forget the path, so the replacement can acquire and our Drop harms nothing.
    pub fn defuse(&mut self) {
        if !self.path.as_os_str().is_empty() {
            if let Ok(body) = fs::read_to_string(&self.path) {
                if body.contains(&format!("\"pid\":{}", std::process::id())) {
                    let _ = fs::remove_file(&self.path);
                }
            }
        }
        self.path = PathBuf::new();
    }
}

impl Drop for Lease {
    fn drop(&mut self) {
        if self.path.as_os_str().is_empty() {
            return;
        }
        // Only take away a lease that is still ours (a newer holder took the floor while ours
        // lapsed); a replacement from this same process is defused before it gets here.
        if let Ok(body) = fs::read_to_string(&self.path) {
            if body.contains(&format!("\"pid\":{}", std::process::id())) {
                let _ = fs::remove_file(&self.path);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tmp(name: &str) -> PathBuf {
        let p = std::env::temp_dir().join(format!("ca-lease-{name}-{}", std::process::id()));
        let _ = fs::remove_dir_all(&p);
        fs::create_dir_all(&p).unwrap();
        p
    }

    #[test]
    fn a_live_lease_stops_a_second_builder_and_releases_on_drop() {
        let dir = tmp("live");
        let a = Lease::acquire(&dir).unwrap();
        assert!(Lease::acquire(&dir).is_err(), "a fresh holder stops the next one");
        drop(a);
        assert!(Lease::acquire(&dir).is_ok(), "and letting go lets the next through");
        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn a_silent_holder_is_taken_over() {
        let dir = tmp("stale");
        fs::write(Lease::file(&dir), format!("{{\"pid\":999998,\"at_ms\":{}}}", now_ms() - STALE.as_millis() as u64 - 5000)).unwrap();
        assert!(Lease::acquire(&dir).is_ok(), "a holder silent past the lapse loses the floor");
        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn a_live_lease_blocks_even_its_own_process_until_lapsing() {
        let dir = tmp("self");
        // A same-pid live lease (another RunSet, or one nobody polled yet) still holds:
        // the owner lets go by defusing or dropping, never by sharing a pid.
        fs::write(Lease::file(&dir), format!("{{\"pid\":{},\"at_ms\":{}}}", std::process::id(), now_ms())).unwrap();
        assert!(Lease::acquire(&dir).is_err(), "a live holder keeps the floor whatever its pid");
        fs::write(Lease::file(&dir), format!("{{\"pid\":{},\"at_ms\":{}}}", std::process::id(), now_ms() - STALE.as_millis() as u64 - 1000)).unwrap();
        assert!(Lease::acquire(&dir).is_ok(), "and past the lapse anyone may take it");
        let _ = fs::remove_dir_all(dir);
    }

    #[test]
    fn a_replaced_lease_leaves_the_new_file_alone() {
        let dir = tmp("defuse");
        // The RunSet order, exactly: our kept lease defuses first, the new one then takes.
        let mut first = Lease::acquire(&dir).unwrap();
        first.defuse();
        let second = Lease::acquire(&dir).unwrap();
        drop(first);
        assert!(Lease::file(&dir).exists(), "defusing a replaced lease must not delete its replacement's file");
        drop(second);
        let _ = fs::remove_dir_all(dir);
    }
}
