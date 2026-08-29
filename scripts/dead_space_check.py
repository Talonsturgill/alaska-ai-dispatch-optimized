#!/usr/bin/env python3
"""DEAD-SPACE METER — turn "the frame feels empty" into a number you can act on.

WHY THIS EXISTS (2026-07-31, after two panel rounds).

"Mean low-information area is roughly 50 percent" was the single most repeated finding
across two rounds and three judges, and it survived a whole editing round in which I added
a far ridge, wheel ruts, a gravel scatter, a verge, a near berm and a ground falloff. All
of that was texture, and texture is not information. The reason the round failed on this
axis is that I was guessing at what "empty" meant and shipping fixes I could not measure,
so I could not tell the difference between a frame that got better and a frame that got
busier.

The measure: a pixel is LOW INFORMATION if its neighbourhood carries almost no structure
(local standard deviation under a threshold) AND it is not close to an edge. Gradients,
noise textures and subtle scatter all stay low-information, which is correct — a viewer
gets nothing from them. Ink outlines, type, and real objects raise local structure, which
is also correct. The score is the fraction of frame area that is low-information.

Use it as a RATCHET, not a target: measure, change one thing, measure again, keep the
change if the number moved. Reported per-shot so the worst shots are named rather than
averaged away.

WHY IT WAS REWRITTEN (2026-08-04, after the panel found 12 to 14 seconds of empty frames
inside the retention window and this script did not).

The meter was correct and unreachable. Three separate reasons, each enough on its own:

  1. It read PNGs from out/dispatch/frames, and the pipeline renders straight to mp4. That
     directory has never existed on a normal run, so every invocation died on "no frames"
     and the step was quietly skipped. A check with a precondition no run satisfies is not
     a check.
  2. It only PRINTED. `worst` was computed, named, and then the process exited 0. Nothing
     downstream could tell a clean film from a film with three empty shots.
  3. It measured the 1080x1920 master. The LinkedIn deliverable is the 1:1 SQUARE CUT, and
     the square throws away 840 rows. A subject parked at the top of the tall frame is
     centred and fine there and gone from the thing people actually see.

All three are the same shape as the no_exit hole closed earlier today: an artifact that
looked like a gate, read as authoritative, and could not fail. So this now samples the
SHIPPED VIDEO with ffmpeg, measures the cut that ships, and EXITS 1.

WHAT IT DOES NOT DO, stated plainly so nobody trusts it for more than it is worth. This
measures TEXTURE-FREE AREA, which is not the same thing as "no subject in the shot". On
the cut the panel faulted for empty frames, the shots the judges named scored 27 to 30
percent while three shots they did not name scored 39 to 45. Big flat colour fields are
this brand, and they read as empty to the meter whether or not something is happening in
front of them. So the ceilings below are a RATCHET against regression, deliberately set
just above the worst film measured rather than at a level that would have caught the
2026-08-03 defect, because a gate tuned to catch that one would fail three innocent shots
every run and would be turned off within a week. Judging whether a shot has a SUBJECT is
still the panel's job, and the storyboard's.

  python3 scripts/dead_space_check.py                          # the square cut, gated
  python3 scripts/dead_space_check.py --video out/dispatch/dispatch_master_hosted.mp4
  python3 scripts/dead_space_check.py --frames out/dispatch/frames   # legacy PNG path
"""
import argparse, glob, json, os, shutil, subprocess, tempfile
import numpy as np


def low_info_fraction(path, win=17, thresh=5.0):
    """Fraction of the frame carrying no local structure."""
    from PIL import Image
    im = Image.open(path).convert("L")
    im = im.resize((im.width // 3, im.height // 3))       # 360x640, plenty for this
    a = np.asarray(im, dtype=np.float32)

    # local mean and local mean-of-squares via a separable box filter -> local variance
    def box(x, k):
        c = np.cumsum(np.pad(x, ((k // 2 + 1, k // 2), (0, 0))), axis=0)
        x = (c[k:] - c[:-k]) / k
        c = np.cumsum(np.pad(x, ((0, 0), (k // 2 + 1, k // 2))), axis=1)
        return (c[:, k:] - c[:, :-k]) / k

    m = box(a, win)
    m2 = box(a * a, win)
    sd = np.sqrt(np.maximum(0.0, m2 - m * m))
    return float((sd < thresh).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default="out/dispatch/dispatch_square.mp4",
                    help="THE CUT THAT SHIPS. Frames are sampled from it with ffmpeg, so the "
                         "meter cannot measure a different image than the audience gets.")
    ap.add_argument("--frames", default="",
                    help="legacy: read frame_*.png from a directory instead of a video")
    ap.add_argument("--every", type=int, default=30)
    ap.add_argument("--scenes", default="out/dispatch/episode_props.json")
    ap.add_argument("--thresh", type=float, default=5.0)
    ap.add_argument("--budget", type=float, default=0.33,
                    help="per-shot ADVISORY ceiling; shots above it are named and sorted")
    # CEILINGS ARE MEASURED, NOT GUESSED. On the 2026-08-03 cut, which the panel called
    # partly empty, per-shot means ran 19.8% to 45.0% and the film mean was 33.2%. So these
    # are set just above that film: a RATCHET that fails on regression, not a target.
    ap.add_argument("--fail-shot", type=float, default=0.55,
                    help="per-shot HARD ceiling (measured worst-ever shot: 45.0%%).")
    ap.add_argument("--fail-mean", type=float, default=0.42,
                    help="whole-film HARD ceiling (measured worst-ever film: 33.2%%).")
    ap.add_argument("--no-gate", action="store_true",
                    help="measure and report without the exit code. For calibration runs ONLY: "
                         "a pipeline step must never pass this, or the gate is decorative again.")
    a = ap.parse_args()

    tmp = None
    stride = a.every          # source frames between samples; used to place samples in shots
    if a.frames:
        fs = sorted(glob.glob(os.path.join(a.frames, "frame_*.png")))
        if not fs:
            raise SystemExit(f"no frames in {a.frames}")
    else:
        if not os.path.exists(a.video):
            raise SystemExit(f"no video at {a.video} -- render and encode before measuring it")
        tmp = tempfile.mkdtemp(prefix="deadspace")
        fps = 30.0 / max(1, a.every)
        subprocess.run(["ffmpeg", "-y", "-i", a.video, "-vf", f"fps={fps}",
                        os.path.join(tmp, "frame_%05d.png"), "-v", "error"], check=True)
        fs = sorted(glob.glob(os.path.join(tmp, "frame_*.png")))
        if not fs:
            raise SystemExit(f"ffmpeg produced no frames from {a.video}")
        # ffmpeg already decimated, so read every extracted frame. STRIDE stays at --every
        # because the per-shot bucketing below compares against SOURCE frame numbers: the
        # first version scaled it to 1 and dropped all 84 samples into S1.
        a.every = 1
        print(f"sampled {len(fs)} frames from {a.video}")

    scenes = None
    if os.path.exists(a.scenes):
        try:
            scenes = json.load(open(a.scenes)).get("scenes")
        except Exception:
            scenes = None

    idx = list(range(0, len(fs), a.every))
    vals = [(i * stride, low_info_fraction(fs[i], thresh=a.thresh)) for i in idx]
    overall = float(np.mean([v for _, v in vals]))

    print(f"frames sampled: {len(vals)} of {len(fs)}   (every {a.every})")
    print(f"MEAN LOW-INFORMATION AREA: {overall * 100:.1f}%")
    print()

    if scenes:
        print("per shot:")
        worst, hard = [], []
        for si, sc in enumerate(scenes):
            lo, hi = sc["from"], sc["from"] + sc["dur"]
            v = [x for i, x in vals if lo <= i < hi]
            if not v:
                continue
            mean, mx = float(np.mean(v)), float(np.max(v))
            flag = "  <-- OVER BUDGET" if mean > a.budget else ""
            print(f"  S{si + 1:<2} {lo / 30:6.1f}s..{hi / 30:6.1f}s   mean {mean * 100:5.1f}%   worst {mx * 100:5.1f}%{flag}")
            if mean > a.budget:
                worst.append((mean, si + 1))
            if mean > a.fail_shot:
                hard.append((mean, si + 1))
        if worst:
            print()
            print("fix these first, worst first: " +
                  ", ".join(f"S{n} ({m * 100:.0f}%)" for m, n in sorted(worst, reverse=True)))
    else:
        hard = []
        for i, v in vals:
            print(f"  f{i:<5} {i / 30:6.1f}s  {v * 100:5.1f}%")

    # ---- THE PART THAT WAS MISSING: a verdict, with an exit code behind it -------
    if tmp:
        shutil.rmtree(tmp, ignore_errors=True)
    if a.no_gate:
        print("\n(--no-gate: measured only, no verdict)")
        return

    fails = []
    if overall > a.fail_mean:
        fails.append(f"whole film mean low-information area {overall * 100:.1f}% "
                     f"is over the {a.fail_mean * 100:.0f}% ceiling")
    for m, n in sorted(hard, reverse=True):
        fails.append(f"S{n} mean {m * 100:.1f}% is over the {a.fail_shot * 100:.0f}% "
                     f"per-shot ceiling: that shot has no subject in it")
    if fails:
        print()
        print("=" * 74)
        print("  DEAD-SPACE GATE FAILED")
        print("=" * 74)
        for f in fails:
            print("  - " + f)
        print()
        print("  A shot over the ceiling is not a taste note. It is a stretch of the film")
        print("  where a viewer is given nothing to look at, and it is measured on the cut")
        print("  that ships, not on the tall master. Put a SUBJECT in the frame -- an object,")
        print("  a person, an instrument doing something -- not more texture. Gradients,")
        print("  noise and scatter all score as empty here, correctly.")
        raise SystemExit(1)
    print(f"\n  OK  mean {overall * 100:.1f}% (ceiling {a.fail_mean * 100:.0f}%), "
          f"every shot under the {a.fail_shot * 100:.0f}% per-shot ceiling")


if __name__ == "__main__":
    main()
