#!/usr/bin/env python3
"""Prove the evidence pack actually shows the film, before a judge grades it.

WHY THIS EXISTS (2026-08-06, and it cost this run at least four judge-rounds).

A panel can only grade what it is shown. Every time the pack failed to show something, a
judge reported that thing as absent — correctly, about the evidence, and wrongly about the
film — and the run spent a round chasing a defect that did not exist:

  - c11 "14 DAYS, THEN DELETED" is on screen 44.43s..46.90s. The nearest filmstrip sampled
    42.64s and the contact sheet sampled 39.5s and 48.3s. Three judges reported Anchorage's
    counter-case as thin or missing. It was drawn, and invisible to the pack.
  - The S11 thesis wall rides a fade. Every strip and every contact frame ever taken of it
    landed at 50% or 78% opacity, so three judges across three rounds reported no orange
    brackets and no grey box on the film's closing argument.
  - Two strips were centred on the soft tail of a hard ease-out and measured 1.6%, which
    reads as "frozen" and means "sampled forty frames after the event".

Each of those cost a full render-and-regrade cycle. That is the most expensive way in this
pipeline to discover a sampling error.

WHAT IT CHECKS
  1. every shot has at least one filmstrip
  2. every storyboard beat has a sample (strip centre or contact frame) within --beat-window
  3. no strip is centred where the picture is nearly static, which almost always means the
     anchor is on an ease-out tail rather than on the move

It reads out/evidence/motion.json and the contact frame times from the jpg filenames, so it
grades the pack that exists rather than the pack that was intended.
"""
import argparse
import glob
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
EV = os.path.join(REPO, "out", "evidence")
OUT = os.path.join(REPO, "out", "dispatch")
FPS = 30.0


def contact_times():
    ts = []
    for p in glob.glob(os.path.join(EV, "f*.jpg")):
        m = re.search(r"f(\d+\.\d)\.jpg$", os.path.basename(p))
        if m:
            ts.append(float(m.group(1)))
    return sorted(ts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beat-window", type=float, default=1.6,
                    help="a beat is covered if any sample lands within this many seconds")
    ap.add_argument("--static-floor", type=float, default=3.0,
                    help="a strip below this %% change is probably anchored on a tail")
    a = ap.parse_args()

    mj = os.path.join(EV, "motion.json")
    if not os.path.exists(mj):
        print("evidence_coverage_check: no motion.json; run build_evidence.py first")
        return 1
    strips = json.load(open(mj))["strips"]
    props = json.load(open(os.path.join(OUT, "episode_props.json")))
    scenes = props["scenes"]
    sb = json.load(open(os.path.join(OUT, "storyboard.json")))
    beats = sb.get("beats") or []

    # THE MANIFEST IS NOT THE PACK (2026-08-13). This check read motion.json and never
    # asked whether the strips it names are on disk, so it passed a pack whose strips had
    # been destroyed and a judge graded four of thirty-seven. The cause was mundane and will
    # recur: `build_evidence.py | head -6` sends SIGPIPE partway through, the build dies
    # after writing a few strips, and motion.json from the previous complete run is still
    # sitting there describing files that no longer exist. Same class as the stale filmstrip
    # anchors, a per-run artifact read by path that looked plausible and described something
    # else. A judge reporting motion absent from evidence that was never written is the most
    # expensive possible way to find this.
    # BOUND BEFORE FIRST USE (2026-08-13, round 6). The on-disk guard below was appending to
    # `problems` a dozen lines before `problems` was created, so the check written this morning
    # to catch a pack whose filmstrips were destroyed raised NameError instead of reporting one.
    # A guard that cannot fire is worse than no guard, because it reads as a passing check.
    # Found by a judge reading the source, which is not where this should have been caught.
    problems, notes = [], []
    missing_on_disk = [n for n in strips if not os.path.exists(os.path.join(EV, f"filmstrip_{n}.jpg"))]
    if missing_on_disk:
        problems.append(
            f"{len(missing_on_disk)} of {len(strips)} filmstrips named in motion.json are NOT ON DISK "
            f"({', '.join(sorted(missing_on_disk)[:6])}{' ...' if len(missing_on_disk) > 6 else ''}). "
            f"motion.json is describing a build whose files are gone, which usually means "
            f"build_evidence.py was interrupted (a `| head` on its output is enough). "
            f"Re-run scripts/build_evidence.py and re-check BEFORE convening a panel.")

    samples = sorted([s["centre_s"] for s in strips.values()] + contact_times())

    # 1. every shot sampled
    for i, sc in enumerate(scenes):
        t0, t1 = sc["from"] / FPS, (sc["from"] + sc["dur"]) / FPS
        if not any(t0 <= s < t1 for s in samples):
            problems.append(f"S{i+1} ({t0:.1f}-{t1:.1f}s) has no strip and no contact frame. "
                            f"A judge cannot grade a shot nobody photographed.")

    # 2. every beat covered
    uncovered = []
    for b in beats:
        t = b.get("t")
        if t is None:
            continue
        t = float(t)
        if not any(abs(t - s) <= a.beat_window for s in samples):
            uncovered.append((t, str(b.get("title") or b.get("draw") or "")[:56]))
    if uncovered:
        problems.append(f"{len(uncovered)} storyboard beat(s) have no sample within "
                        f"{a.beat_window}s. Each is something the film draws and the panel "
                        f"will never see:")
        for t, title in uncovered[:12]:
            problems.append(f"      t={t:>6.1f}s  {title}")

    # 3. strips anchored on a tail
    for name, s in sorted(strips.items(), key=lambda kv: kv[1]["changed_pct"]):
        if s["changed_pct"] < a.static_floor:
            notes.append(f"strip '{name}' at {s['centre_s']:.2f}s measures "
                         f"{s['changed_pct']:.1f}% change. Below {a.static_floor}% usually "
                         f"means the anchor sits on an ease-out tail rather than the move; "
                         f"re-anchor to peak velocity before blaming the film.")

    for n in notes:
        print(f"NOTE {n}")
    if problems:
        for p in problems:
            print(f"FAIL {p}" if not p.startswith("      ") else p)
        print(f"\nevidence_coverage_check: the pack does not show the film. Fix the anchors,")
        print("not the film. A judge reporting something absent from the evidence is the")
        print("most expensive possible way to discover a sampling error.")
        return 1
    print(f"evidence_coverage_check: {len(scenes)} shots and {len(beats)} beats all covered "
          f"by {len(samples)} samples"
          + (f"; {len(notes)} anchor(s) worth re-checking" if notes else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
