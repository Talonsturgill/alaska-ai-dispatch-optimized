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
  2026-08-13  "below bar, zero blockers, low on context,
               so I'll hand off and notify the status"   -> closed HERE, in code

The two closed by code have not recurred. The two closed by prose have. That is the whole
argument for this file: a sentence a run writes to itself is negotiable, and an exit code
is not.

2026-08-13 proved it again and cost the owner an intervention. The run had a graded cut at
a 6.77 median with ZERO hard blockers on all three cards, ran low on context, and wrote
itself a defensible-sounding ending: worklog, PR update, push notification, "not shipped,
correct for a run under the bar." Every sentence in it was true. It was still an empty run,
and the owner had to say "ship it" for a video to exist. The specific mechanism of the
failure is worth naming, because it is not laziness and it will recur in this shape: the
run reported STATUS when it owed a DECISION. A status report asks for nothing, so nothing
happens. The fix is below, in the refusal text, and it is the owner_release path.

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

It does not invent a second quality policy. It reuses ship_gate's fully validated current-run
decision and also requires the verdict-bound terminal preview. A failing or stale ship verdict
is not a completed delivery, even if plausible media files exist on disk.

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
import sys
import time
from pathlib import Path

from delivery_preview import DeliveryPreviewError, require_delivery_preview
from ship_gate import GateInputError, require_ship_verdict
from strict_json import StrictJSONError, load_path

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
RETIRED_ALIASES = (
    "dispatch_master.mp4",
    "dispatch_4x5.mp4",
    "poster_thumb.jpg",
    "render/master_9x16.mp4",
    "render/master_4x5.mp4",
)

# A FILM ON DISK IS NOT A DELIVERED CANARY RESULT. The preview is local by policy, but it
# must still exist and be post-stamp so a run cannot stop after encoding without handing the
# owner the review surface the canary promises.
LOCAL_PREVIEW = "dispatch-preview.html"


def video_state():
    """The honest state of this run's film. Returns (delivered: bool, lines: list[str])."""
    lines = []
    delivered = True
    for alias in RETIRED_ALIASES:
        if (OUT / alias).exists():
            lines.append(f"  BAD      retired output alias exists: {alias}")
            delivered = False
    try:
        ship_state = require_ship_verdict(verify_blankness=True)
        manifest = ship_state["manifest"]
        lines.append(
            f"  OK       current ship verdict median {ship_state['median']} >= {ship_state['threshold']}"
        )
    except GateInputError as exc:
        lines.append(f"  BAD      current ship verdict: {exc}")
        manifest = None
        ship_state = None
        delivered = False
    if manifest is not None:
        for role, entry in manifest["artifacts"].items():
            duration = entry.get("duration_seconds")
            detail = f"{duration:.1f}s, " if isinstance(duration, (int, float)) else ""
            lines.append(
                f"  OK       {role} [{entry['path']}] ({detail}{entry['bytes']/1e6:.1f} MB, "
                f"sha256={entry['sha256'][:12]})"
            )
    try:
        require_delivery_preview(root=ROOT, ship_state=ship_state)
        lines.append(f"  OK       terminal canary preview [{LOCAL_PREVIEW}] is verdict-bound")
    except DeliveryPreviewError as exc:
        lines.append(f"  MISSING  terminal canary preview ({exc})")
        delivered = False

    return delivered, lines

def elapsed_note():
    if not STAMP.exists():
        return "run not stamped (run_guard.py init was never called)"
    try:
        value = load_path(STAMP, label="run stamp")
        started = float(value["started_at"])
    except (StrictJSONError, TypeError, ValueError, KeyError, OSError):
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
PANEL_VERDICT = OUT / "panel_verdict.json"


def panel_state():
    """(has_verdict, passing, median, bar, note). Never raises."""
    try:
        state = require_ship_verdict(verify_blankness=True)
        return True, True, state["median"], state["threshold"], (
            f"fully validated current-run median {state['median']} against {state['threshold']}"
        )
    except GateInputError as exc:
        return PANEL_VERDICT.exists(), False, None, None, str(exc)

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
        print("", file=sys.stderr)
        # 2026-08-13: the excuse of the day was "median below bar, zero hard blockers, and I am
        # low on context, so I will write a WORKLOG, update the PR and notify the owner of the
        # status." Every clause true, and the sum of it is still an empty run. The owner had to
        # come back and say ship it. What made it possible is that the run never told them a
        # DECISION was available -- it sent a status report, which asks for nothing, instead of
        # the one question only the owner can answer. There is a designed path for this and the
        # run did not offer it, so the hatch is named here and the path is printed.
        print("  IF YOU GENUINELY CANNOT CONTINUE (context or wall-clock, never quality),", file=sys.stderr)
        print("  YOU STILL MAY NOT DECLARE THE RUN OVER. A handoff is not an outcome and a", file=sys.stderr)
        print("  status notification is not a decision. Ask the owner the only question they", file=sys.stderr)
        print("  can answer -- SHIP AT THIS MEDIAN, OR KEEP GOING -- and say what the cut is:", file=sys.stderr)
        print("  its median, its hard-blocker count, and what is measurably fixed.", file=sys.stderr)
        print("  If they release it, config/owner_release.json carries {run_date, floor,", file=sys.stderr)
        print("  instruction verbatim} for that ONE run and ship_gate honours it without", file=sys.stderr)
        print("  waiving any other check. That file is the exit. A worklog is not.", file=sys.stderr)
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
