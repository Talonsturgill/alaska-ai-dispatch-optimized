#!/usr/bin/env python3
"""THE ONE OUTCOME GATE: a run may not end without a delivered video.

WHY THIS EXISTS
---------------
The "no empty runs" rule has been written into prompts/dispatch_routine.md four times
and routed around four times, because each writing closed a SPECIFIC excuse and the next
run invented a new sentence:

  2026-07-29  "no story clears the bar"                  -> closed by story_gate.py
  2026-07-31  "remaining defects are cosmetic, ship it"  -> closed by ship_gate.py
  2026-07-31  "I can't reach the bar, failed run"        -> closed by prompt text only
  2026-08-01  "I ran out of session, banked the work"    -> closed by prompt text only

The two closed by code have not recurred. The two closed by prose have. That is the whole
argument for this file: a sentence a run writes to itself is negotiable, and an exit code
is not.

WHAT IT DOES, AND THE ONE THING IT MUST NEVER DO
------------------------------------------------
`check` asks one question: does a delivered video exist? Exit 0 means yes and the run may
end. Exit 1 means no and the run may not.

It is ASYMMETRIC BY DESIGN. It can only ever refuse a STOP. It can never refuse a SHIP.
Nothing in the delivery path calls it, so a bug here can delay an empty run and can not
block a good one. Any future edit that puts this script in front of upload, the Gmail
draft, the merge, or any render is a REGRESSION -- ship_gate.py is the gate that decides
whether bytes are good enough to leave, and this one only decides whether the absence of
bytes is an acceptable way to finish.

It deliberately does NOT judge quality. A run standing at a passing ship_gate has a video.
A run standing at a failing ship_gate has a video and an instruction to go improve it.
Neither is an empty run, and this script has no opinion about which one you are.

USAGE (from prompts/dispatch_routine.md, THE ONE OUTCOME LAW)
-------------------------------------------------------------
Before writing ANY stop-shaped artifact -- a queue file, a handoff note, a PR body that
explains what is unfinished, a notification containing the word partial -- and before
ending the run for any reason other than a hard blocker:

    python3 scripts/no_exit.py check          # exit 1 = keep building

    python3 scripts/no_exit.py status         # always exit 0; the honest state, for logs
    python3 scripts/no_exit.py check --blocker "remotion render segfaults, tried X, Y, Z"

A --blocker still exits 1. It exists so the refusal transcript records what you claimed,
in your own words, next to the evidence that no film exists. A hard blocker is a tool that
will not run, an API that is down, or an input no amount of work can produce. Time,
difficulty, quality and remaining scope are not blockers, and naming one here does not
make it one.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "dispatch"
RENDER = OUT / "render"
STAMP = OUT / ".run_stamp.json"
ROUGHCUT = OUT / "roughcut.mp4"

# Same list ship_gate.py binds its hashes to. A run has "a video" when the two cuts a
# viewer could actually receive exist and carry real streams.
DELIVERABLES = ["master_9x16.mp4", "master_4x5.mp4"]

MIN_BYTES = 200_000          # anything smaller is a stub, not a film
MIN_SECONDS = 30.0           # the format band is 84-96s; 30 is a generous floor for "a film"


def probe(path: Path):
    """Return (seconds, has_video, has_audio) or None if ffprobe can't read it."""
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            return None
        d = json.loads(r.stdout)
        secs = float(d.get("format", {}).get("duration", 0.0))
        kinds = {s.get("codec_type") for s in d.get("streams", [])}
        return secs, "video" in kinds, "audio" in kinds
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def video_state():
    """The honest state of this run's film. Returns (delivered: bool, lines: list[str])."""
    lines = []
    delivered = True
    for name in DELIVERABLES:
        p = RENDER / name
        if not p.exists():
            lines.append(f"  MISSING  {name}")
            delivered = False
            continue
        size = p.stat().st_size
        info = probe(p)
        if info is None:
            lines.append(f"  UNREADABLE  {name} ({size} bytes, ffprobe failed)")
            delivered = False
            continue
        secs, has_v, has_a = info
        problems = []
        if size < MIN_BYTES:
            problems.append(f"{size} bytes is a stub")
        if secs < MIN_SECONDS:
            problems.append(f"{secs:.1f}s is not a film")
        if not has_v:
            problems.append("no video stream")
        if not has_a:
            problems.append("no audio stream")
        if problems:
            lines.append(f"  BAD      {name} ({', '.join(problems)})")
            delivered = False
        else:
            lines.append(f"  OK       {name} ({secs:.1f}s, {size/1e6:.1f} MB, video+audio)")
    return delivered, lines


def elapsed_note():
    if not STAMP.exists():
        return "run not stamped (run_guard.py init was never called)"
    try:
        started = float(json.loads(STAMP.read_text())["started_at"])
    except (ValueError, KeyError, OSError):
        return "run stamp unreadable"
    mins = (time.time() - started) / 60.0
    return f"{mins:.0f} min since the run was stamped"


REFUSAL = """
================================================================================
  NO. THIS RUN HAS NOT DELIVERED A VIDEO, SO THIS RUN IS NOT OVER.
================================================================================

There is exactly ONE terminal state for a Dispatch run and it is a delivered video.
Not a failed run, not a partial run, not a handoff, not a banked run, not a clean
stop, not a resumable state.

Whatever sentence you were about to write, apply the owner's test to it:

    if the owner read this, would their next words be "so where is the video?"

If yes, it is an exit hatch. Delete it and go build the film.

Out of session, out of runway, out of context, out of time, "several more hours
remain", "the responsible thing is to stop cleanly", "I banked the expensive work
for tomorrow", "I queued the story so nothing is wasted", "substantial progress
was made" -- every one of those has been used, none of them is a hard blocker,
and none of them is available.

IF YOU ARE REASONING ABOUT REMAINING EFFORT, YOU OWE A MEASUREMENT. Build one
scene end to end, render it, time it. An estimate you did not measure is a
feeling. And a real measurement never authorizes stopping, it only tells you
which version of the film you are making.

WHERE THE PRESSURE IS ALLOWED TO GO (scope the film down, never the delivery):
  1. one bespoke hero illustration instead of two
  2. compose entirely from the shelf, make the craft advance a small one
  3. fewer shots, toward the floor in config/shot_structure.yaml
  4. short end of the words band and the seconds band
  5. simpler staging: fewer depth planes, one camera move class

Not on that ladder, ever: the fact-check, the gates, the ship_gate median,
looking at frames before shipping, or the film itself.

NEXT ACTION: open video-engine/src/ and author the next scene. If no rough cut
exists yet, build the WHOLE film crude first (Phase 5 step 3a) -- every shot
present, real VO, zero polish -- so the film's absence stops being invisible.

  full law: prompts/dispatch_routine.md > THE ONE OUTCOME LAW
================================================================================
""".rstrip()


def cmd_status() -> int:
    delivered, lines = video_state()
    print(f"ONE OUTCOME GATE -- {elapsed_note()}")
    print(f"rough cut: {'present' if ROUGHCUT.exists() else 'NOT BUILT (Phase 5 step 3a)'}")
    print("deliverables:")
    for ln in lines:
        print(ln)
    print(f"verdict: {'A VIDEO EXISTS. This run may end.' if delivered else 'NO VIDEO. This run may not end.'}")
    return 0


def cmd_check(blocker: str) -> int:
    delivered, lines = video_state()
    if delivered:
        print("ONE OUTCOME GATE: a delivered video exists. This run may end.")
        for ln in lines:
            print(ln)
        return 0
    print(REFUSAL, file=sys.stderr)
    print("\nstate at refusal:", file=sys.stderr)
    print(f"  {elapsed_note()}", file=sys.stderr)
    print(f"  rough cut: {'present' if ROUGHCUT.exists() else 'NOT BUILT'}", file=sys.stderr)
    for ln in lines:
        print(ln, file=sys.stderr)
    if blocker:
        print(f"\n  you claimed a hard blocker: {blocker}", file=sys.stderr)
        print("  a hard blocker is a tool that will not run, an API that is down, or an input",
              file=sys.stderr)
        print("  no amount of work can produce. If yours is genuinely one of those, notify the",
              file=sys.stderr)
        print("  owner with the exact command, the exact error, and what you tried. If it is not,",
              file=sys.stderr)
        print("  it is a hatch with better manners, and the answer is another round.", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    pc = sub.add_parser("check", help="exit 0 if a video was delivered, 1 if not")
    pc.add_argument("--blocker", default="", help="the hard blocker you are claiming (still exits 1)")
    sub.add_parser("status", help="print the honest state; always exit 0")
    a = ap.parse_args()
    if a.cmd == "status":
        return cmd_status()
    return cmd_check(a.blocker)


if __name__ == "__main__":
    raise SystemExit(main())
