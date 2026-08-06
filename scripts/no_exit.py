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

# THE TWO CUTS A VIEWER COULD ACTUALLY RECEIVE.
#
# HARDENED 2026-08-03, and this was a REAL HOLE that let a run stop with a finished
# film on disk. The list used to read ["master_9x16.mp4", "master_4x5.mp4"] under
# out/dispatch/render/, and the pipeline has never written those paths: Phase 7 encodes
# out/dispatch/dispatch_master.mp4 and out/dispatch/dispatch_4x5.mp4. So this gate could
# never see a delivered film. It refused every stop identically whether the run had ten
# shots encoded or nothing at all, which is worse than not existing, because a gate that
# is always red teaches the run to stop reading it. On 2026-08-03 the run encoded both
# cuts, passed every audio and structure gate, and still wrote a PR body explaining what
# was unfinished plus a "did not ship" notification, without ever invoking this check.
#
# Each entry is a list of ACCEPTED PATHS, relative to out/dispatch/, newest naming first.
DELIVERABLES = [
    ("9:16 master", ["dispatch_master.mp4", "render/master_9x16.mp4"]),
    # dispatch_4x5.mp4 USED TO BE LISTED HERE AS AN ALIAS AND THAT WAS A HOLE (2026-08-04).
    # 4:5 is the aspect this routine deliberately moved AWAY from, because LinkedIn routes
    # anything taller than square into the swipe-only Video tab, so accepting a 1080x1350
    # file as proof of "the 1:1 square cut" let the gate be satisfied by the exact mistake
    # the encode script exists to prevent. Worse, a judge found a stale 4:5 from the PREVIOUS
    # DAY still sitting in out/dispatch carrying the old VO ("paid" where the record says
    # obligated), a PI name missing its middle initial, plates that no longer exist in the
    # film and text clipped at both frame edges. That file satisfied this gate.
    ("1:1 square LinkedIn cut", ["dispatch_square.mp4", "render/master_4x5.mp4"]),
]

# A FILM ON DISK IS NOT A DELIVERED FILM. The second half of the hole: even with the
# paths corrected this gate only ever asked whether BYTES existed, so a run could encode
# both cuts, look at them, and still stop without the draft that puts the film in front
# of the owner. Delivery is what the routine promises, so delivery is what this checks.
# scripts/dispatch_email.py writes this receipt after the Gmail connector accepts a draft.
DRAFT_RECEIPT = "gmail_draft_receipt.json"

# A deliverable OLDER than the mute render is a leftover from a previous cut, not this run's
# film. This is how a day-old 4:5 with the wrong voice track sat in the run directory for a
# whole session looking like a finished artifact.
FRESHNESS_REFERENCE = "render_mute.mp4"

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
    for label, candidates in DELIVERABLES:
        p = next((OUT / c for c in candidates if (OUT / c).exists()), None)
        if p is None:
            lines.append(f"  MISSING  {label} (looked for {', '.join(candidates)})")
            delivered = False
            continue
        name = f"{label} [{p.name}]"
        size = p.stat().st_size
        info = probe(p)
        if info is None:
            lines.append(f"  UNREADABLE  {name} ({size} bytes, ffprobe failed)")
            delivered = False
            continue
        secs, has_v, has_a = info
        problems = []
        # STALE-DELIVERABLE GUARD. A cut older than the render it is supposed to come from is
        # a leftover, and a leftover looks exactly like a finished artifact from the outside.
        ref = OUT / FRESHNESS_REFERENCE
        if ref.exists() and p.stat().st_mtime + 1 < ref.stat().st_mtime:
            problems.append(f"older than {FRESHNESS_REFERENCE}, so it is a previous cut")
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
    # ---- THE DELIVERY LEG. Bytes on disk are not a delivered film. -------------
    # This is the half of the hole that survived the path fix: with the paths correct
    # the gate said "this run may end" while no draft existed anywhere, which is exactly
    # the state the 2026-08-03 run stopped in. The routine promises the owner a draft in
    # their inbox, so the gate asks for the receipt, not for the encode.
    receipt = OUT / DRAFT_RECEIPT
    if not receipt.exists():
        lines.append(f"  MISSING  the Gmail draft. Both cuts encode, and nobody has been")
        lines.append(f"           handed the film. Run scripts/dispatch_email.py and hand")
        lines.append(f"           the payload to the Gmail connector, then write")
        lines.append(f"           out/dispatch/{DRAFT_RECEIPT}.")
        delivered = False
    else:
        try:
            r = json.loads(receipt.read_text())
            lines.append(f"  OK       Gmail draft {r.get('draft_id', '(no id)')} "
                         f"to {r.get('to', '?')} at {r.get('created_at', '?')}")
        except (OSError, ValueError) as e:
            lines.append(f"  UNREADABLE  {DRAFT_RECEIPT} ({e})")
            delivered = False

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



# ---------------------------------------------------------------------------
# THE SECOND HOLE, closed 2026-08-06 after a run walked straight through it.
#
# This gate was written to refuse a stop when NO BYTES EXIST. It did that job: the
# 08-06 run could not stop before the rough cut. Then the bytes appeared, the gate
# printed "A VIDEO EXISTS. This run may end.", went quiet, and the run abandoned a
# cut its own panel had graded 5.12 against a 9.0 bar, with the sentence:
#
#     "the rest needs more rounds than the run had"
#
# That is verbatim the class THE ONE OUTCOME LAW forecloses ("out of runway, out of
# budget, out of time"), it cited no measurement, and the gate had nothing to say
# about it because it only ever counted files.
#
# A BELOW-BAR CUT THAT GETS ABANDONED IS AN EMPTY RUN WITH BYTES IN IT. The audience
# gets the same nothing. So the gate now also refuses a stop when a panel verdict
# exists and is under the bar.
#
# THIS IS STILL ASYMMETRIC AND STILL ONLY REFUSES A STOP. It has no opinion about
# whether anything may SHIP -- ship_gate.py owns that and this file must never be
# added to the delivery path. All this does is make "I graded it, it failed, and I
# stopped" cost exactly as much as "I never built it".
def _bar_from_rubric(default=7.5):
    """THE BAR IS READ, NEVER TYPED. This file used to say BAR_DEFAULT = 9.0, copied out of
    a stale line in the routine prompt while config/dispatch_rubric.yaml had said 7.5 since
    2026-07-31. A guard that refuses stops using the wrong bar refuses the wrong stops."""
    try:
        import yaml
        cfg = yaml.safe_load((ROOT / "config" / "dispatch_rubric.yaml").read_text())
        for key in ("ship_threshold", "threshold"):
            if key in cfg:
                return float(cfg[key])
            for v in cfg.values():
                if isinstance(v, dict) and key in v:
                    return float(v[key])
    except Exception:
        pass
    return default


BAR_DEFAULT = _bar_from_rubric()
PANEL_VERDICT = OUT / "panel_verdict.json"


def panel_state():
    """(has_verdict, passing, median, bar, note). Never raises."""
    if not PANEL_VERDICT.exists():
        return False, None, None, None, "no panel verdict recorded yet"
    try:
        v = json.loads(PANEL_VERDICT.read_text())
    except Exception as e:
        return True, False, None, None, f"panel_verdict.json exists but does not parse ({e})"
    med = v.get("median")
    bar = v.get("bar", BAR_DEFAULT)
    if not isinstance(med, (int, float)):
        js = [j.get("overall") for j in (v.get("judges") or [])
              if isinstance(j.get("overall"), (int, float))]
        med = sorted(js)[len(js) // 2] if js else None
    if med is None:
        return True, False, None, bar, "a panel verdict exists but records no median"
    return True, med >= bar, med, bar, f"median {med} against a {bar} bar"

def cmd_status() -> int:
    delivered, lines = video_state()
    print(f"ONE OUTCOME GATE -- {elapsed_note()}")
    print(f"rough cut: {'present' if ROUGHCUT.exists() else 'NOT BUILT (Phase 5 step 3a)'}")
    print("deliverables:")
    for ln in lines:
        print(ln)
    has_v, passing, med, bar, note = panel_state()
    print(f"panel: {note}")
    if delivered and has_v and not passing:
        print("verdict: BYTES EXIST BUT THE PANEL FAILED THEM. This run may not end.")
    else:
        print(f"verdict: {'A VIDEO EXISTS. This run may end.' if delivered else 'NO VIDEO. This run may not end.'}")
    return 0


def cmd_check(blocker: str) -> int:
    delivered, lines = video_state()
    has_v, passing, med, bar, note = panel_state()
    if delivered and has_v and not passing:
        print("ONE OUTCOME GATE: BYTES EXIST AND THE PANEL FAILED THEM.", file=sys.stderr)
        print("", file=sys.stderr)
        print(f"  {note}", file=sys.stderr)
        print("  A below-bar cut that gets abandoned is an empty run with bytes in it.", file=sys.stderr)
        print("  The audience gets the same nothing either way.", file=sys.stderr)
        print("", file=sys.stderr)
        print("  A failing panel is an INSTRUCTION TO RE-ENTER THE LOOP, not an outcome.", file=sys.stderr)
        print("  Take the panel's named defects, fix them, re-render, REBUILD THE EVIDENCE", file=sys.stderr)
        print("  FROM THE NEW RENDER, re-grade, re-record, and run ship_gate again.", file=sys.stderr)
        print("", file=sys.stderr)
        print("  Renders are minutes. Measure one before you reason about how many are left,", file=sys.stderr)
        print("  and never assert a number you did not measure. 'More rounds than the run", file=sys.stderr)
        print("  had' is not a measurement, it is the out-of-runway hatch in new clothes.", file=sys.stderr)
        if blocker:
            print(f"\n  you claimed a hard blocker: {blocker}", file=sys.stderr)
            print("  quality is never a blocker and time is never a blocker.", file=sys.stderr)
        return 1
    if delivered:
        print("ONE OUTCOME GATE: a delivered video exists. This run may end.")
        print(f"  panel: {note}")
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
