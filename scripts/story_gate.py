#!/usr/bin/env python3
"""
STORY GATE — THE NO-EMPTY-RUN GUARD.

Why this exists (2026-07-29, owner directive after an empty run):
    The run found a thin first research round, called it a slow news week, and took the
    "if nothing clears the bar, stop" escape hatch. Every individual rejection was
    defensible in isolation and the conclusion was still wrong, because:

      1. The six-agent first round consumed the entire SESSION-WIDE WebSearch budget, so
         every later agent was blind. The run then cited its own blindness as evidence
         that there was no news. That is circular.
      2. It applied a fixed 10-day window although the automation had not shipped for
         three days, so the gap it actually owed the audience was WIDER, not narrower.
      3. It let a generic-token dedupe hit (alaska, digital, twin, uaf) kill a story whose
         actual subject, the electrical grid, had nothing to do with the prior dispatch's
         landslide seismology.
      4. WebFetch was never capped. Outlet front pages could have been swept at any moment
         for free, and were not.

    The root defect is not any single judgement. It is that STOPPING WAS AS CHEAP AS
    CONTINUING. There was one escape hatch and no ladder in front of it.

This gate makes stopping expensive and continuing the default. It refuses to authorise an
empty run until every rung of the escalation ladder has been ATTEMPTED and recorded with
evidence, and two of those rungs (primary-source mining and the pegged explainer) are
sources that essentially cannot come back empty. In practice that makes an empty run
impossible without a deliberate, documented, owner-visible override.

Usage:
    python3 scripts/story_gate.py window
        Print the window (in days) this run must cover, derived from the last shipped
        dispatch, so a skipped day widens the sweep instead of narrowing it.

    python3 scripts/story_gate.py check [path/to/candidates.json]
        Exit 0  -> a story is locked, proceed to the angle room.
        Exit 1  -> you may NOT stop. Prints the next rung to work and why.

Contract matches storyboard_check.py / caption_check.py: machine-checked, no cap, fix the
cause and re-run. You do not get to relax the rule to pass. You go find the story.
"""
import sys, json, datetime
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "config" / "state.yaml"
DEFAULT_CAND = ROOT / "out" / "dispatch" / "candidates.json"

# THE ESCALATION LADDER. Ordered cheapest-and-freshest first. A run may only report "no
# story" after EVERY rung is attempted, and the last two are designed to be inexhaustible.
LADDER = [
    ("in_window_sweep",
     "Beat fan-out across the window story_gate.py reports (NOT a fixed 10 days). Cap each "
     "researcher's WebSearch calls and reserve budget for round two."),
    ("outlet_index_sweep",
     "WebFetch the news indexes of the Alaska outlets directly and read the headlines. "
     "WebFetch is NOT capped by the session search budget. There is no excuse for skipping "
     "this rung, and a run that reports a slow week without it has not looked."),
    ("widened_window",
     "Re-sweep at 30 days. A story the audience has never been shown is NEW TO THEM. A "
     "still-developing pilot from three weeks ago is a legitimate Dispatch, especially when "
     "the channel has skipped days."),
    ("carried_leads",
     "Work the carried-forward leads from recent archive/*/story_pick.md files. Past runs "
     "logged them precisely so a thin week has somewhere to go."),
    ("primary_source_mining",
     "Mine primary databases directly, which is how the 07-25 and 07-29 scoops were both "
     "found: NSF api.nsf.gov, DOE science.osti.gov award lists, USAspending, grants.gov, "
     "SAM.gov, FERC eLibrary, the RCA filings portal, the Alaska Legislature bill tracker, "
     "agency dockets, university news feeds. These are uncapped WebFetch targets and they "
     "are never empty."),
    ("follow_up",
     "Revisit a previously covered story that has a genuinely NEW development, or answer "
     "the open question a prior Dispatch left hanging. 'What happened next' is real news."),
    ("pegged_explainer",
     "The floor, and it always exists: an evergreen Alaska-and-AI explainer pegged to a real "
     "current hook. Explain a mechanism, a number, or a decision the audience is living with. "
     "This rung cannot return empty, which is the entire point of the ladder."),
]
LADDER_KEYS = [k for k, _ in LADDER]
# Rungs that are effectively inexhaustible. A claim that BOTH produced zero candidates is
# not a slow news week, it is a research failure, and the gate says so in those words.
INEXHAUSTIBLE = {"primary_source_mining", "pegged_explainer"}

MIN_WINDOW_DAYS = 10
SKIP_BUFFER_DAYS = 4        # a skipped run widens the window rather than narrowing it


def _last_dispatch_date():
    try:
        state = yaml.safe_load(STATE.read_text()) or {}
    except Exception:
        return None
    hist = state.get("dispatch_history") or []
    dates = []
    for e in hist:
        d = str(e.get("date", "")).strip()
        try:
            dates.append(datetime.date.fromisoformat(d))
        except ValueError:
            continue
    return max(dates) if dates else None


def compute_window(today=None):
    """The window this run OWES the audience. Skipped days widen it."""
    today = today or datetime.date.today()
    last = _last_dispatch_date()
    if not last:
        return MIN_WINDOW_DAYS, None, 0
    gap = (today - last).days
    # cover everything since the last ship, plus a buffer, never less than the floor
    return max(MIN_WINDOW_DAYS, gap + SKIP_BUFFER_DAYS), last, gap


def cmd_window():
    days, last, gap = compute_window()
    print(f"WINDOW {days}")
    if last:
        print(f"  last shipped dispatch: {last} ({gap} days ago)")
        if gap > 1:
            print(f"  NOTE: the automation has not shipped for {gap} days. The audience has seen "
                  f"NOTHING in that time, so stories from the skipped days are unspent, not stale. "
                  f"Widen, do not narrow.")
    else:
        print("  no dispatch history found; using the floor")
    return 0


def fail(msg_lines):
    print("FAIL [story_gate] YOU MAY NOT END THIS RUN WITHOUT A STORY.")
    for m in msg_lines:
        print(f"  {m}")
    print()
    print("  There is always news. This gate exists because a prior run rationalised an empty")
    print("  run from a thin first pass. Work the next rung and re-run this gate.")
    sys.exit(1)


def cmd_check(path):
    if not path.exists():
        fail([f"no candidate ledger at {path}.",
              "Phase 3 must WRITE out/dispatch/candidates.json recording every rung attempted",
              "and every candidate evaluated. Start with rung 1:",
              f"    {LADDER[0][0]} — {LADDER[0][1]}"])
    try:
        c = json.loads(path.read_text())
    except Exception as e:
        fail([f"candidate ledger at {path} is not valid JSON ({e})."])

    locked = c.get("locked_story")
    if locked and str(locked.get("headline", "")).strip():
        print(f"PASS [story_gate] story locked: {locked.get('headline')}")
        print(f"  rung: {locked.get('found_at_rung', '(unrecorded)')}")
        cands = c.get("candidates") or []
        print(f"  {len(cands)} candidate(s) evaluated this run")
        return 0

    # No story locked. Now the ladder must account for itself.
    rungs = {str(r.get("rung", "")): r for r in (c.get("rungs") or [])}
    problems = []

    not_attempted = [k for k in LADDER_KEYS if not (rungs.get(k) or {}).get("attempted")]
    if not_attempted:
        nxt = not_attempted[0]
        desc = dict(LADDER)[nxt]
        lines = [f"{len(not_attempted)} of {len(LADDER_KEYS)} escalation rungs have not been attempted.",
                 "",
                 f"NEXT RUNG TO WORK: {nxt}",
                 f"    {desc}",
                 "",
                 "Remaining after that: " + (", ".join(not_attempted[1:]) or "(none)")]
        fail(lines)

    # Every rung attempted. The inexhaustible ones may not report zero without saying why.
    for k in INEXHAUSTIBLE:
        r = rungs.get(k) or {}
        found = int(r.get("candidates_found", 0) or 0)
        if found == 0:
            problems.append(
                f"rung '{k}' reports ZERO candidates. That rung is inexhaustible by design "
                f"(federal award databases, agency dockets and a pegged explainer are never "
                f"empty), so a zero here is a RESEARCH FAILURE, not a slow news week. Re-work "
                f"it before claiming there is nothing to cover.")

    # A blind round may never be reported as scarcity.
    if c.get("search_budget_exhausted") and not c.get("uncapped_sweep_done"):
        problems.append(
            "the session search budget was exhausted AND no uncapped WebFetch outlet sweep was "
            "recorded (uncapped_sweep_done). A blind run cannot conclude there is no news. "
            "Sweep the outlet indexes with WebFetch, which is not capped, then re-run.")

    evaluated = len(c.get("candidates") or [])
    if evaluated < 8:
        problems.append(f"only {evaluated} candidate(s) evaluated. A genuine no-story finding "
                        f"requires having looked at real breadth (>= 8) across the ladder.")

    if problems:
        fail(problems)

    # Everything attempted, everything justified. Still require a deliberate override so an
    # empty run can never be a quiet default.
    auth = c.get("stop_authorization") or {}
    if not auth.get("override_reason") or len(str(auth.get("override_reason"))) < 200:
        fail(["every rung is attempted, but an empty run still requires an explicit, detailed",
              "stop_authorization.override_reason (>= 200 chars) naming what was searched, what",
              "was found, and why a pegged explainer was ALSO impossible.",
              "",
              "Before writing it, reconsider: the explainer rung has no external dependency. If",
              "you can explain one true thing about Alaska and AI, this run has a Dispatch."])

    print("PASS [story_gate] empty run authorised under explicit override.")
    print(f"  reason: {auth.get('override_reason')[:160]}...")
    print("  This is a LAST RESORT and will be surfaced to the owner.")
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "window":
        sys.exit(cmd_window())
    if cmd == "check":
        p = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_CAND
        sys.exit(cmd_check(p))
    print(__doc__)
    sys.exit(2)


if __name__ == "__main__":
    main()
