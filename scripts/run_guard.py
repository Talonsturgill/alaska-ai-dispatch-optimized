#!/usr/bin/env python3
"""Run-freshness guard: make it physically impossible to ship a PREVIOUS run's scratch.

WHY THIS EXISTS
---------------
out/dispatch/ is gitignored scratch that survives across container sessions.
The pipeline reads and writes artifacts BY PATH, and a stale file at the right
path is byte-for-byte indistinguishable from a fresh one. Two runs have already
been bitten by this:
  - 2026-07-18 found a stale shots.json left over from the 07-17 episode.
  - 2026-07-19 found stale post.txt / sources.json / shots.json / vo_script.json
    left over from a run about an ENTIRELY DIFFERENT story (the Mat-Su AIDEA land
    conveyance). Delivery could have emailed the wrong caption and source list.

The root cause is not "someone forgot to clean up." It is that the pipeline
DRIFTS: newer runs stopped producing some of the old artifacts (they moved to
caption.txt, inline shots, etc.), so those old outputs are never overwritten and
just linger. Any fix that asks every PRODUCER to stamp or register its output
re-introduces exactly this drift problem the next time the pipeline changes.

THE INVARIANT (why this is a real fix and not another sticky note)
------------------------------------------------------------------
A run starts at a recorded instant T. Every artifact this run legitimately
produces is written at or after T. Therefore ANY scratch file with mtime < T is,
by definition, a leftover from an earlier run and must never be trusted.

Freshness is thus a property the filesystem already tracks (mtime), and mtime is
trustworthy here precisely because scratch files are gitignored -- git never
rewrites their timestamps the way it does for checked-out files. No producer has
to change; only:
  1. Phase 0 stamps the run ONCE, before any artifact is produced:
         python3 scripts/run_guard.py init --run-id 2026-07-19
  2. Consumers route their reads through fresh(), which refuses (loudly, with
     both timestamps) anything older than the stamp:
         from run_guard import fresh
         post = open(fresh("out/dispatch/post.txt")).read()

A missing stamp is also a hard failure: if the run was never stamped we cannot
PROVE a file is fresh, so we refuse rather than guess. The escape hatch for
deliberate manual/standalone use is an explicit opt-out on the consumer
(dispatch_email.py --no-freshness-check), never a silent fallback.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

STAMP_REL = "out/dispatch/.run_stamp.json"

# A file written up to GRACE_S seconds before the stamp is still accepted. Real
# leftovers are hours-to-days old, so this never lets a genuine stale file
# through; it only avoids a false positive on a file created moments before init
# in the same run's own setup.
GRACE_S = 5.0


class StaleArtifactError(RuntimeError):
    """Raised when a scratch artifact predates the current run (or the run was
    never stamped, so freshness cannot be proven)."""


def _stamp_path(root: str | None = None) -> Path:
    base = Path(root) if root else Path.cwd()
    return base / STAMP_REL


def _fmt(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


def init(run_id: str, root: str | None = None) -> dict:
    """Stamp the current run. Call ONCE, in Phase 0, before any artifact exists."""
    stamp = {"run_id": run_id, "started_at": time.time()}
    p = _stamp_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(stamp, indent=2))
    return stamp


def load_stamp(root: str | None = None) -> dict | None:
    p = _stamp_path(root)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def check_path(path: str, root: str | None = None) -> tuple[bool, str]:
    """Return (ok, reason). ok=False means the file is stale, missing, or the run
    was never stamped. Never raises -- for callers that want to branch."""
    stamp = load_stamp(root)
    if stamp is None:
        return False, (
            f"run not stamped (no {STAMP_REL}); cannot prove freshness. "
            f"Run `python3 scripts/run_guard.py init --run-id <date>` in Phase 0 first."
        )
    started = float(stamp["started_at"])
    fp = Path(path)
    if not fp.exists():
        return False, f"{path} does not exist"
    mtime = fp.stat().st_mtime
    if mtime < started - GRACE_S:
        return False, (
            f"STALE: {path} was last written {_fmt(mtime)}, but this run "
            f"(run_id={stamp.get('run_id')}) started {_fmt(started)}. "
            f"This file is a leftover from an earlier run -- regenerate it this run "
            f"or point at the artifact this run actually produced."
        )
    return True, "fresh"


def fresh(path: str, *, check: bool = True, root: str | None = None) -> str:
    """Assert `path` belongs to the current run and return it unchanged, so it
    drops into existing code:  open(fresh("out/dispatch/post.txt")).
    Set check=False to bypass (deliberate manual use only)."""
    if not check:
        return path
    ok, reason = check_path(path, root)
    if not ok:
        raise StaleArtifactError(reason)
    return path


def _main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="stamp the current run (Phase 0, once)")
    pi.add_argument("--run-id", required=True, help="e.g. the run date 2026-07-19")

    pc = sub.add_parser("check", help="check one path; exit 0 fresh, 1 stale/missing")
    pc.add_argument("path")

    a = ap.parse_args()
    if a.cmd == "init":
        s = init(a.run_id)
        print(f"run stamped: run_id={s['run_id']} started_at={_fmt(s['started_at'])} -> {STAMP_REL}")
        return 0
    if a.cmd == "check":
        ok, reason = check_path(a.path)
        print(("OK: " if ok else "FAIL: ") + reason, file=sys.stderr if not ok else sys.stdout)
        return 0 if ok else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
