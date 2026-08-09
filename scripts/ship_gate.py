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

OWNER RELEASE (added 2026-07-31, and it is NOT an override flag — read this before you
touch it). The owner, who set the 8.6 bar, can lower it for one specific run. The run
cannot. The difference is the whole point, so the mechanism is built to make it
impossible for a run to grant itself one:

  - It lives in config/owner_release.json, not in an argv flag. A flag is something a
    process types to itself; a file with the owner's own words in it is a decision.
  - It is bound to a single run date and refuses to apply on any other day, so it can
    never sit in the repo quietly authorising future runs.
  - It carries the verbatim instruction and the floor the owner accepted. Both are
    printed by the gate and both go into the dated email, so the release is always
    visible to the person who granted it, in the same place the score is.
  - It does not disable any other check. The bytes still have to be the graded bytes,
    the evidence still has to come from those bytes, and there still have to be three
    judges. A release lowers the bar for one run; it never lets an ungraded or stale
    cut through.

If you are a future run reading this and thinking about writing that file yourself:
don't. That is the exact thing the 2026-07-31 directive forbade.

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
# THE GATE WAS POINTING AT A DIRECTORY AND A NAMING SCHEME THE PIPELINE STOPPED USING
# (fixed 2026-08-05). It expected out/dispatch/render/{master_9x16,master_4x5,
# master_9x16_720}.mp4 while encode_deliverables.sh has been writing
# out/dispatch/{dispatch_master,dispatch_square,dispatch_master_720}.mp4. So the gate
# could never pass, on any cut, for any score: it failed on missing deliverables before
# it ever looked at a verdict, and the failure message said "go back into the loop",
# which reads as a quality problem and sent every run back to editing.
#
# Worse, one of the three files it demanded was master_4x5.mp4. This repo documents
# 1080x1350 as the WRONG LinkedIn cut in two places, because a taller-than-square video
# routes into the swipe-only Video tab instead of the main feed. The gate was requiring
# the one deliverable the routine forbids.
RENDER = OUT
# Same staleness as DELIVERABLES above: the evidence pack the panel actually reads is
# built by scripts/build_evidence.py into out/evidence (contact sheet, 14 stills, 5
# filmstrips, audio_report.json). The gate was looking in out/dispatch/review, which
# nothing has written to in this pipeline's lifetime.
REVIEW = ROOT / "out" / "evidence"
VERDICT = OUT / "panel_verdict.json"
ATTEMPTS = OUT / "gate_attempts.json"
RUBRIC = ROOT / "config" / "dispatch_rubric.yaml"

# every artifact a viewer could actually receive
DELIVERABLES = ["dispatch_master.mp4", "dispatch_square.mp4", "dispatch_master_720.mp4"]

# Everything whose contents can change what a frame looks like. If any of it is NEWER than
# the deliverables, the deliverables were rendered from code that no longer exists.
SOURCE_GLOBS = ["video-engine/src/**/*.tsx", "video-engine/src/**/*.ts",
                "scripts/dispatch_mix.py", "scripts/build_scenes.py"]


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


RELEASE = ROOT / "config" / "owner_release.json"


def owner_release(run_date: str):
    """The owner's decision to accept a lower bar for ONE run, or None.

    Requires, in config/owner_release.json: run_date matching this run, the verbatim
    instruction, and the floor being accepted. Anything missing means no release, because
    a release nobody can read afterwards is indistinguishable from a run helping itself.
    """
    if not RELEASE.exists():
        return None
    try:
        d = json.loads(RELEASE.read_text())
    except Exception as e:
        print(f"ship_gate: owner_release.json is unreadable ({e}); ignoring it.")
        return None
    for k in ("run_date", "instruction", "floor"):
        if not d.get(k):
            print(f"ship_gate: owner_release.json has no {k}; ignoring it.")
            return None
    if str(d["run_date"]) != run_date:
        print(f"ship_gate: owner release is for {d['run_date']}, this run is {run_date}; "
              f"it does not apply.")
        return None
    return d


def run_date() -> str:
    """The date this run is shipping under, from the run stamp, never from the clock."""
    stamp = OUT / ".run_stamp.json"
    if stamp.exists():
        try:
            d = json.loads(stamp.read_text())
            for k in ("run_id", "date", "run_date", "episode_date"):
                if d.get(k):
                    return str(d[k])
        except Exception:
            pass
    return time.strftime("%Y-%m-%d")


def newest_source():
    """(mtime, path) of the newest file that can change a rendered frame."""
    import glob
    newest = (0.0, None)
    for g in SOURCE_GLOBS:
        for f in glob.glob(str(ROOT / g), recursive=True):
            m = os.path.getmtime(f)
            if m > newest[0]:
                newest = (m, os.path.relpath(f, ROOT))
    return newest


def check_render_is_current():
    """THE GAP THIS CLOSES (2026-07-31, found the hard way on the fourth editing round).

    ship_gate binds the panel's verdict to the DELIVERABLE's bytes and the evidence to those
    same bytes. That is airtight against grading one cut and shipping another. It is
    completely blind to a third failure: a deliverable rendered from SOURCE THAT HAS SINCE
    CHANGED.

    That is exactly what happened. A render command silently did not run, I read the tail of
    a stale log as proof it had, and then muxed and graded a video that predated half an hour
    of fixes. Every hash matched perfectly, because the evidence really was cut from the
    deliverable -- the deliverable was just thirty minutes behind the code. A judge caught it
    by noticing that a shot the run described did not exist in the frames, which cost the
    panel a whole round.

    A timestamp check is cheap and it makes that mistake impossible to repeat."""
    mtime, path = newest_source()
    if path is None:
        return
    stale = []
    for n in DELIVERABLES:
        f = RENDER / n
        if f.exists() and f.stat().st_mtime < mtime - 1:
            stale.append(f"{n} ({time.strftime('%H:%M:%S', time.localtime(f.stat().st_mtime))})")
    if stale:
        fail([f"DELIVERABLE IS OLDER THAN THE SOURCE IT CLAIMS TO BE A RENDER OF.",
              f"  newest source: {path} at {time.strftime('%H:%M:%S', time.localtime(mtime))}",
              f"  stale output:  {', '.join(stale)}",
              "Every hash in this gate can match while the video is still a render of code "
              "that no longer exists. Re-render, re-cut the evidence from the new render, "
              "and re-grade. Do not trust a log tail as proof a render ran -- check the file."])


def artifact_state():
    """sha256 of every deliverable plus every piece of review evidence."""
    missing = [n for n in DELIVERABLES if not (RENDER / n).exists()]
    if missing:
        fail([f"deliverable(s) missing from {RENDER}: {', '.join(missing)}"])
    arts = {n: sha(RENDER / n) for n in DELIVERABLES}
    ev = {}
    if REVIEW.exists():
        # build_evidence.py writes the contact sheet, the stills and the filmstrips as
        # JPEG. Globbing only *.png found nothing, so the gate reported that the panel
        # "cannot have looked at anything" while a full evidence pack sat beside it.
        # Third instance of the same drift in this file: the gate was written against an
        # older pipeline and never re-pointed when the pipeline changed.
        for p in sorted(list(REVIEW.glob("*.png")) + list(REVIEW.glob("*.jpg"))):
            ev[p.name] = sha(p)
    return arts, ev


def log_attempt(reasons, median=None):
    """Every blocked attempt is appended, so the editing loop is auditable and a run
    cannot quietly stall in it. This is a LEDGER, not a budget: there is no attempt
    count at which stopping becomes allowed."""
    hist = []
    if ATTEMPTS.exists():
        try:
            hist = json.loads(ATTEMPTS.read_text())
        except Exception:
            hist = []
    hist.append({"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "attempt": len(hist) + 1, "median": median, "reasons": reasons})
    ATTEMPTS.write_text(json.dumps(hist, indent=2))
    return len(hist)


def fail(lines, median=None):
    n = log_attempt(lines, median)
    print("=" * 72)
    print(f"SHIP GATE: BLOCKED  (editing round {n})")
    print("=" * 72)
    for l in lines:
        print(f"  FAIL  {l}")
    print()
    print("  THIS IS NOT AN OUTCOME. IT IS AN INSTRUCTION TO GO BACK INTO THE LOOP.")
    print("  Return to Phase 6. Take the panel's named defects, fix them, re-render,")
    print("  rebuild the evidence FROM the new render, re-grade, re-record, run this again.")
    print()
    print("  There is no override flag and there is no round count at which stopping")
    print("  becomes acceptable. A below-bar film is unfinished, not failed. The only")
    print("  exit from this loop is a passing median. Quality is never a blocker;")
    print("  the only thing that legitimately halts a run is a tool that will not run.")
    sys.exit(1)


BLANK_LOW_INFO = 0.85   # a frame this featureless is not a shot, it is an absence


def check_not_blank(n=28):
    """Is there actually a FILM in the file?

    Added 2026-07-31 after this run rendered the wrong Remotion composition. Root.tsx keeps
    every past episode registered under its own id, and the generic id "Dispatch" still
    pointed at the July 26 film, so the render produced 93.3 seconds of the WRONG episode:
    correct length, correct dimensions, correct captions burned over the top, and thirty
    seconds of blank grey at the end where that episode had simply run out of scenes.

    Every existing check passed. The hashes matched because the bytes were consistent. The
    freshness check passed because the file was new. The mux verified because there was
    audio. ffprobe passed because the frame size was right. They all answer "is this
    deliverable current and well-formed", and not one of them answers "is this a movie".

    So: sample frames across the whole duration and measure local structure. A frame that is
    almost entirely flat is not a composition choice, it is a missing scene. Named by
    timestamp so the failure points at where to look rather than just asserting badness.
    """
    import glob, shutil, subprocess as sp, tempfile
    import numpy as np
    from PIL import Image

    vid = RENDER / "dispatch_master.mp4"
    if not vid.exists():
        return
    tmp = tempfile.mkdtemp(prefix="shipgate_blank_")
    try:
        dur = float(sp.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(vid)], capture_output=True, text=True
                           ).stdout.strip() or 0)
        if dur <= 0:
            return
        for i in range(n):
            t = dur * (i + 0.5) / n
            sp.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(vid),
                    "-frames:v", "1", "-vf", "scale=360:-1", f"{tmp}/f{i:03d}.png"],
                   capture_output=True)
        blank = []
        for i, p in enumerate(sorted(glob.glob(f"{tmp}/*.png"))):
            a = np.asarray(Image.open(p).convert("L"), dtype=np.float32)
            k = 17
            def box(x, ax):
                c = np.cumsum(np.pad(x, [(k // 2 + 1, k // 2) if d == ax else (0, 0)
                                         for d in (0, 1)]), axis=ax)
                return (np.take(c, range(k, c.shape[ax]), axis=ax)
                        - np.take(c, range(0, c.shape[ax] - k), axis=ax)) / k
            m = box(box(a, 0), 1)
            m2 = box(box(a * a, 0), 1)
            sd = np.sqrt(np.maximum(0.0, m2 - m * m))
            frac = float((sd < 5.0).mean())
            if frac > BLANK_LOW_INFO:
                blank.append((i * dur / n, frac))
        if blank:
            fail([f"{len(blank)} of {n} sampled frames are effectively BLANK "
                  f"(over {BLANK_LOW_INFO * 100:.0f}% of the frame carries no structure).",
                  "First few: " + ", ".join(f"{t:.1f}s ({f * 100:.0f}%)" for t, f in blank[:6]),
                  "A deliverable of the right length and the right dimensions is not the same "
                  "thing as the right film. Check that render.sh was given THIS run's "
                  "composition id (out/dispatch/.run_stamp.json > composition) and that every "
                  "scene in episode_props.json has a component behind it."])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def cmd_record(a):
    check_render_is_current()
    check_not_blank()
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


def check_beats_delivered():
    """Did the build draw the events the board wrote? (scripts/beat_delivery.py)

    Added 2026-07-31. Advisory-to-hard: it PASSES the run it was written for, at 100%, which
    is itself the finding -- that run's beats all moved, and the panel still scored the picture
    as static, so this is not the explanation for that score. It is here as a regression guard
    against a build that quietly stops drawing what the board promised, which is a failure that
    contact sheets hide and that cost a full review cycle to even suspect.
    """
    import glob as _g
    if not _g.glob(str(OUT / "frames" / "frame_*.png")):
        return
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import beat_delivery as _bd
        r = _bd.analyze(str(OUT / "frames"), str(OUT / "storyboard.json"))
        print(f"  beat delivery: {r['delivered']}/{r['beats']} beats draw a visible event")
        if r["problems"]:
            fail(r["problems"])
    except SystemExit:
        raise
    except Exception as e:
        print(f"  beat delivery: could not run ({e}); beats not delivery-checked")


def cmd_check(a):
    check_render_is_current()
    check_not_blank()
    check_beats_delivered()
    problems = []
    if not VERDICT.exists():
        fail([f"no {VERDICT.name}. The 3-judge panel has not graded this cut. "
              f"A Dispatch may not ship ungraded."])

    v = json.loads(VERDICT.read_text())
    arts, ev = artifact_state()
    thr = ship_threshold()

    # ---- 1. DID IT PASS? No self-granted exceptions, no 'style-register' carve-out. ----
    median = float(v.get("median", 0))
    rel = owner_release(run_date())
    effective = thr
    if rel and float(rel["floor"]) < thr:
        effective = float(rel["floor"])
    if median < effective:
        problems.append(
            f"PANEL MEDIAN {median} IS BELOW THE {effective} SHIP BAR. This is a hard stop. "
            f"The routine's old 'deliver with the scorecard disclosed' clause was DELETED "
            f"on 2026-07-31 because a run used it to ship a 6.98. Disclosure is not a "
            f"substitute for fixing. Fix the defects, re-render, re-grade.")
    elif effective < thr:
        print("=" * 72)
        print(f"SHIPPING UNDER AN OWNER RELEASE — the rubric bar is {thr}, this cut scored "
              f"{median}.")
        print(f"  released to: {effective}   on: {rel['run_date']}")
        print(f"  owner said: {rel['instruction']}")
        print("  Every other check below still applies and none of them were waived.")
        print("=" * 72)
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
        fail(problems, median=median)

    # A PASS IS A STOP ORDER, NOT A CHECKPOINT (2026-08-09, owner's instruction after this
    # routine passed at 7.61, kept editing, and never cleared the bar again in five further
    # rounds costing nine hours). The run that day had a shippable cut, found a real defect,
    # fixed it, and destroyed the passing verdict to do so, because any source edit forces a
    # re-render and a re-grade. The defect was genuine; fixing it THEN was the error.
    #
    # So the pass now leaves a lock on disk and render_parallel.sh refuses to start while it
    # exists. Continuing to polish after a pass is no longer a judgement call a run gets to
    # make on its own: it has to delete a file whose name says what it is doing.
    SHIP_NOW = RENDER / "SHIP_NOW"
    SHIP_NOW.write_text(
        f"median {median} cleared {effective} at {time.strftime('%H:%M:%S')}.\n"
        "SHIP THESE BYTES. Do not edit, do not re-render, do not improve.\n"
        "Every further fix is next run's work. Delete this file only if you are deliberately\n"
        "abandoning a passing cut, and say so out loud when you do.\n")
    print("=" * 72)
    print("SHIP GATE: PASS  ->  SHIP NOW, DO NOT KEEP EDITING")
    print("=" * 72)
    # print the EFFECTIVE bar, not the rubric one. The first version of this line printed
    # "7.2 >= 7.5" under a release, which is a false statement in the pass banner of the gate
    # whose entire job is to not let false statements through.
    print(f"  panel median {median} >= {effective} (rubric bar {thr})   judges={judges}"
          if effective != thr else
          f"  panel median {median} >= {thr}   judges={judges}")
    print(f"  {len(arts)} deliverables hash-match the graded cut")
    print(f"  {len(graded_ev)} pieces of review evidence hash-match")
    if ATTEMPTS.exists():
        try:
            n = len(json.loads(ATTEMPTS.read_text()))
            print(f"  cleared after {n} blocked round(s) in the editing loop")
        except Exception:
            pass
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
