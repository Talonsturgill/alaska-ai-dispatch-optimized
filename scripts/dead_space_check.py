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

  python3 scripts/dead_space_check.py --frames out/dispatch/frames --every 30
  python3 scripts/dead_space_check.py --frames out/dispatch/frames --scenes out/dispatch/episode_props.json
"""
import argparse, glob, json, os
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
    ap.add_argument("--frames", default="out/dispatch/frames")
    ap.add_argument("--every", type=int, default=30)
    ap.add_argument("--scenes", default="out/dispatch/episode_props.json")
    ap.add_argument("--thresh", type=float, default=5.0)
    ap.add_argument("--budget", type=float, default=0.33,
                    help="per-shot ceiling; shots above it are named")
    a = ap.parse_args()

    fs = sorted(glob.glob(os.path.join(a.frames, "frame_*.png")))
    if not fs:
        raise SystemExit(f"no frames in {a.frames}")

    scenes = None
    if os.path.exists(a.scenes):
        try:
            scenes = json.load(open(a.scenes)).get("scenes")
        except Exception:
            scenes = None

    idx = list(range(0, len(fs), a.every))
    vals = [(i, low_info_fraction(fs[i], thresh=a.thresh)) for i in idx]
    overall = float(np.mean([v for _, v in vals]))

    print(f"frames sampled: {len(vals)} of {len(fs)}   (every {a.every})")
    print(f"MEAN LOW-INFORMATION AREA: {overall * 100:.1f}%")
    print()

    if scenes:
        print("per shot:")
        worst = []
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
        if worst:
            print()
            print("fix these first, worst first: " +
                  ", ".join(f"S{n} ({m * 100:.0f}%)" for m, n in sorted(worst, reverse=True)))
    else:
        for i, v in vals:
            print(f"  f{i:<5} {i / 30:6.1f}s  {v * 100:5.1f}%")


if __name__ == "__main__":
    main()
