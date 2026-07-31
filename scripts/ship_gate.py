#!/usr/bin/env python3
"""
SHIP GATE — the last thing that runs before anything leaves the building.

WHY THIS EXISTS (2026-07-31, owner directive after the run shipped a failing cut).

That run did three things wrong and every one of them was possible because nothing
in the pipeline checked:

  1. The 3-judge panel returned a 6.98 median against an 8.6 bar and the run shipped
     anyway, using a clause in the routine that let it "deliver with the full scorecard
     disclosed" when it judged the remaining complaints to be style-register. The run
     graded its own remaining defects as cosmetic. They were not: five boring stretches
     with timestamps and a 15.3 second static ending are concrete named defects. THAT
     CLAUSE IS DELETED and this gate is what replaces it.

  2. The panel graded ONE render. The run then fixed things and re-rendered TWICE more.
     THE CUT THAT SHIPPED WAS NEVER GRADED BY ANYONE. The reported 6.98 described a
     file that no longer existed. Nothing caught that, because the verdict was a number
     in a transcript rather than a claim bound to bytes.

  3. The evidence the panel looked at (contact sheets, motion filmstrips) was likewise
     generated from the FIRST render. Re-rendering silently invalidated every frame the
     judges had seen, and the pipeline had no idea.

So the invariant this gate enforces is one sentence:

    THE PANEL MUST HAVE GRADED THE EXACT BYTES THAT ARE ABOUT TO SHIP, USING EVIDENCE
    DERIVED FROM THOSE EXACT BYTES, AND IT MUST HAVE PASSED.

It is enforced by sha256, not by anyone remembering. Re-render anything and the hashes
stop matching, the gate fails, and the run has to re-cut the evidence and re-grade.

THERE IS NO OVERRIDE FLAG, AND ADDING ONE IS A REGRESSION. The whole failure mode was a
run granting itself permission. A gate with an escape hatch is a suggestion.

Usage
-----
  # after the FINAL render, rebuild evidence from it, then have the panel grade THAT
  python3 scripts/ship_gate.py record --median 8.7 --judges 8.5,8.7,8.9 \
      --notes "what the panel said"

  # before upload / email / merge. exit 0 = you may ship. exit 1 = you may not.
  python3 scripts/ship_gate.py check
"""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out" / "dispatch"
RENDER = OUT / "render"
REVIEW = OUT / "review"
VERDICT = OUT / "panel_verdict.json"
RUBRIC = ROOT / "config" / "dispatch_rubric.yaml"

# every artifact a viewer could actually receive
DELIVERABLES = ["master_9x16.mp4", "master_4x5.mp4", "master_9x16_720.mp4"]


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ship_threshold() -> float:
    """Read the bar from the rubric. Never hardcode it here, so raising the bar in the
    rubric raises it everywhere."""
    try:
        import yaml
        cfg = yaml.safe_load(RUBRIC.read_text())
        for key in ("ship_threshold", "threshold"):
            if key in cfg:
                return float(cfg[key])
            for v in cfg.values():
                if isinstance(v, dict) and key in v:
                    return float(v[key])
    except Exception:
        pass
    return 8.6


def artifact_state():
    """sha256 of every deliverable plus every piece of review evidence."""
    missing = [n for n in DELIVERABLES if not (RENDER / n).exists()]
    if missing:
        fail([f"deliverable(s) missing from {RENDER}: {', '.join(missing)}"])
    arts = {n: sha(RENDER / n) for n in DELIVERABLES}
    ev = {}
    if REVIEW.exists():
        for p in sorted(REVIEW.glob("*.png")):
            ev[p.name] = sha(p)
    return arts, ev


def fail(lines):
    print("=" * 72)
    print("SHIP GATE: BLOCKED. Nothing may be uploaded, emailed, or merged.")
    print("=" * 72)
    for l in lines:
        print(f"  FAIL  {l}")
    print()
    print("  There is no override flag. Fix the cause, re-render, rebuild the review")
    print("  evidence FROM the new render, have the panel grade THAT, then re-record.")
    sys.exit(1)


def cmd_record(a):
    arts, ev = artifact_state()
    if not ev:
        fail([f"no review evidence in {REVIEW} — the panel cannot have looked at anything. "
              f"Run scripts/make_review_sheets.py on frames extracted from THIS render."])

    judges = [float(x) for x in a.judges.split(",") if x.strip()] if a.judges else []
    if len(judges) < 3:
        fail([f"a 3-judge panel means THREE judges. Got {len(judges)}: {judges}. "
              f"The panel was skipped on 2026-07-29 and 2026-07-30 and that is exactly "
              f"how a failing cut reaches the owner."])

    median = a.median
    if median is None:
        s = sorted(judges)
        median = s[len(s) // 2] if len(s) % 2 else (s[len(s) // 2 - 1] + s[len(s) // 2]) / 2

    # The frames the judges saw must be NEWER than the render they claim to describe.
    # If a sheet predates the video, it was made from a different cut.
    vid_mtime = max((RENDER / n).stat().st_mtime for n in DELIVERABLES)
    stale = [n for n in ev if (REVIEW / n).stat().st_mtime < vid_mtime - 1]
    if stale:
        fail([f"review evidence is OLDER than the render it is supposed to describe: "
              f"{', '.join(sorted(stale)[:6])}{' ...' if len(stale) > 6 else ''}",
              "This is the 2026-07-31 failure exactly: the panel graded render #1 and the "
              "run shipped render #3. Rebuild the sheets from the current render."])

    VERDICT.write_text(json.dumps({
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "median": median,
        "judges": judges,
        "threshold": ship_threshold(),
        "notes": a.notes or "",
        "artifacts": arts,
        "evidence": ev,
    }, indent=2))
    print(f"ship_gate: verdict recorded. median={median} judges={judges} "
          f"threshold={ship_threshold()}")
    print(f"  bound to {len(arts)} deliverables and {len(ev)} pieces of review evidence")
    print(f"  -> {VERDICT}")


def cmd_check(a):
    problems = []
    if not VERDICT.exists():
        fail([f"no {VERDICT.name}. The 3-judge panel has not graded this cut. "
              f"A Dispatch may not ship ungraded."])

    v = json.loads(VERDICT.read_text())
    arts, ev = artifact_state()
    thr = ship_threshold()

    # ---- 1. DID IT PASS? No self-granted exceptions, no 'style-register' carve-out. ----
    median = float(v.get("median", 0))
    if median < thr:
        problems.append(
            f"PANEL MEDIAN {median} IS BELOW THE {thr} SHIP BAR. This is a hard stop. "
            f"The routine's old 'deliver with the scorecard disclosed' clause was DELETED "
            f"on 2026-07-31 because a run used it to ship a 6.98. Disclosure is not a "
            f"substitute for fixing. Fix the defects, re-render, re-grade.")
    judges = v.get("judges") or []
    if len(judges) < 3:
        problems.append(f"verdict records {len(judges)} judges, not 3.")

    # ---- 2. DID THEY GRADE WHAT IS ABOUT TO SHIP? ----
    for name, want in (v.get("artifacts") or {}).items():
        got = arts.get(name)
        if got is None:
            problems.append(f"{name} was graded but is no longer present.")
        elif got != want:
            problems.append(
                f"{name} HAS CHANGED SINCE IT WAS GRADED.\n"
                f"          graded: {want[:16]}...\n"
                f"          on disk: {got[:16]}...\n"
                f"        The panel's verdict describes a file that is not the file you are "
                f"about to ship. Re-cut the evidence, re-grade, re-record.")
    for name in arts:
        if name not in (v.get("artifacts") or {}):
            problems.append(f"{name} is a deliverable but was never graded.")

    # ---- 3. WAS THE EVIDENCE DERIVED FROM THOSE BYTES? ----
    graded_ev = v.get("evidence") or {}
    if not graded_ev:
        problems.append("the verdict records no review evidence — nobody looked at a frame.")
    for name, want in graded_ev.items():
        got = ev.get(name)
        if got is None:
            problems.append(f"review evidence {name} is gone.")
        elif got != want:
            problems.append(f"review evidence {name} changed after grading.")

    if problems:
        fail(problems)

    print("=" * 72)
    print("SHIP GATE: PASS")
    print("=" * 72)
    print(f"  panel median {median} >= {thr}   judges={judges}")
    print(f"  {len(arts)} deliverables hash-match the graded cut")
    print(f"  {len(graded_ev)} pieces of review evidence hash-match")
    print("  you may upload, email and merge.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="bind a passing panel verdict to the current bytes")
    r.add_argument("--median", type=float, default=None)
    r.add_argument("--judges", type=str, default="", help="comma-separated, need 3")
    r.add_argument("--notes", type=str, default="")
    r.set_defaults(fn=cmd_record)
    c = sub.add_parser("check", help="the hard gate. run before upload/email/merge")
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
