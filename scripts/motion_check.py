#!/usr/bin/env python3
"""Measure ARTICULATION, which is frame change with the camera taken out of it.

WHY THIS EXISTS (2026-08-06). "Nothing moves" was the single most repeated note across
all six panels this run. Every judge, in every round, on the same shots. It is the note
that kept the median under the bar, and the run failed to close it for one reason:

    I measured the wrong quantity, and the wrong quantity looked fine.

Asked to prove the figures were alive, I ran frame differences over the filmstrips and
reported 6.3% to 15.4% frame-to-frame change as evidence. Those numbers are real and
they are almost entirely CAMERA. Every shot in this engine rides

    translate(540+dx, 960+dy) scale(k) translate(-540,-960),  k = 1 + 0.062*push

so a 2% push repaints most of the frame while every figure in it is a statue. A judge is
not fooled by that for a second, because a judge is looking at the picture rather than at
a percentage. Three rounds were spent with me holding a measurement that agreed with me
and three humans-in-the-loop who did not.

WHAT IT DOES. For each sampled pair of frames it SOLVES for the camera, using exactly the
three-parameter model the engine actually applies (uniform scale about the frame centre,
plus translation), warps one frame back onto the other, and then measures what is left:

    gross      = change before registration  (what I wrongly quoted: mostly camera)
    registered = change after registration   (what a judge actually sees moving)
    block_max  = the most-changed 1/16th of the frame, after registration

`block_max` is the one that answers "is ANYTHING alive in this shot", because a breathing
chest or a turning head is a local event that a whole-frame mean averages into nothing.
A shot can have a healthy registered mean purely from a drifting background gradient.

The three numbers are printed SIDE BY SIDE, always, and that is deliberate. The failure
here was not that the gross number was unavailable, it was that the gross number was
quoted alone and sounded like an answer. Anything that reads this report sees the gap.

  gross 11.2%  registered 0.4%  ->  a camera move over a still frame
  gross 11.4%  registered 3.1%  ->  a camera move over a live one

ADVISORY BY DEFAULT, on the lesson written into preflight.py: a hard gate that has never
been observed passing is how a run dies at 3am for a reason nobody has seen. Run it, read
it, then set --floor and pass --strict once a shipped film has cleared it.

Usage:
  python3 scripts/motion_check.py                       # advisory report over every shot
  python3 scripts/motion_check.py --strict --floor 1.2  # blocking
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")
EV = os.path.join(REPO, "out", "evidence")
FPS = 30.0

# Registration works on a heavily downsampled luma. The camera is a global, low-frequency
# transform, so it solves fine at this size, and the search is O(candidates * pixels).
RW, RH = 64, 114


def grab(video, t, path):
    """One frame at t seconds. -ss BEFORE -i is the fast seek and it is accurate enough
    here because we only ever compare two frames grabbed the same way."""
    p = subprocess.run(
        ["ffmpeg", "-nostdin", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", video,
         "-frames:v", "1", "-y", path],
        capture_output=True, text=True)
    return p.returncode == 0 and os.path.exists(path)


def luma(path, w, h):
    im = Image.open(path).convert("L").resize((w, h), Image.BILINEAR)
    return np.asarray(im, dtype=np.float32) / 255.0


def warp(img, k, dx, dy):
    """Sample img under the engine's own camera model, bilinearly.

    The engine scales about the frame centre and then translates, so undoing it is the
    same operation with 1/k. Out-of-frame samples are clamped rather than zeroed: zeros
    would create a hard border that the search would then happily 'fix' by choosing k=1.
    """
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    sx = (xs - cx - dx) / k + cx
    sy = (ys - cy - dy) / k + cy
    sx = np.clip(sx, 0, w - 1.001)
    sy = np.clip(sy, 0, h - 1.001)
    x0, y0 = np.floor(sx).astype(np.int32), np.floor(sy).astype(np.int32)
    fx, fy = sx - x0, sy - y0
    x1, y1 = x0 + 1, y0 + 1
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy)
            + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)


def register(a, b):
    """Find the (k, dx, dy) that best explains b as a camera move over a.

    Coarse-to-fine, because the exhaustive grid at full registration resolution is the
    slow part and the camera is smooth. Returns (k, dx, dy, residual_map).
    """
    def best_over(cands, ia, ib):
        bk, err = None, None
        for k, dx, dy in cands:
            e = float(np.mean(np.abs(ia - warp(ib, k, dx, dy))))
            if err is None or e < err:
                err, bk = e, (k, dx, dy)
        return bk

    ha, wa = a.shape
    ca = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((wa // 2, ha // 2)),
                    dtype=np.float32) / 255.0
    cb = np.asarray(Image.fromarray((b * 255).astype(np.uint8)).resize((wa // 2, ha // 2)),
                    dtype=np.float32) / 255.0
    coarse = [(k, dx, dy)
              for k in np.arange(0.980, 1.0801, 0.010)
              for dx in range(-4, 5)
              for dy in range(-4, 5)]
    k0, dx0, dy0 = best_over(coarse, ca, cb)
    fine = [(k, dx, dy)
            for k in np.arange(k0 - 0.010, k0 + 0.0101, 0.0025)
            for dx in np.arange(dx0 * 2 - 2, dx0 * 2 + 2.1, 1.0)
            for dy in np.arange(dy0 * 2 - 2, dy0 * 2 + 2.1, 1.0)]
    k, dx, dy = best_over(fine, a, b)
    return k, dx, dy, np.abs(a - warp(b, k, dx, dy))


def block_max(resid, n=4):
    """The most-changed 1/16th of the frame. A local event survives this; a whole-frame
    mean does not, and 'one figure breathes' is always a local event."""
    h, w = resid.shape
    bh, bw = h // n, w // n
    return max(float(np.mean(resid[i * bh:(i + 1) * bh, j * bw:(j + 1) * bw]))
               for i in range(n) for j in range(n))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(OUT, "dispatch_master.mp4"))
    ap.add_argument("--props", default=os.path.join(OUT, "episode_props.json"))
    ap.add_argument("--pairs", type=int, default=3, help="sample pairs per shot")
    ap.add_argument("--gap", type=int, default=4, help="frames between the two samples")
    ap.add_argument("--floor", type=float, default=1.2,
                    help="%% registered block_max below which a shot has nothing alive in it")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 on a shot under the floor (default is advisory)")
    ap.add_argument("--out", default=os.path.join(EV, "motion_registered.json"))
    a = ap.parse_args()

    if not os.path.exists(a.video):
        print(f"motion_check: no video at {os.path.relpath(a.video, REPO)}")
        return 1
    scenes = json.load(open(a.props))["scenes"]
    dt = a.gap / FPS
    rows, tmp = [], tempfile.mkdtemp(prefix="motion_")

    for i, sc in enumerate(scenes):
        t0, t1 = sc["from"] / FPS, (sc["from"] + sc["dur"]) / FPS
        span = t1 - t0
        # Sample inside the shot, never on a boundary: a cut registers as a camera the
        # solver cannot explain, and the residual it leaves is not articulation.
        times = [t0 + span * frac for frac in
                 [(j + 1) / (a.pairs + 1) for j in range(a.pairs)]]
        got = []
        for j, t in enumerate(times):
            pa = os.path.join(tmp, f"s{i}_{j}_a.png")
            pb = os.path.join(tmp, f"s{i}_{j}_b.png")
            if not (grab(a.video, t, pa) and grab(a.video, t + dt, pb)):
                continue
            A, B = luma(pa, RW, RH), luma(pb, RW, RH)
            gross = float(np.mean(np.abs(A - B))) * 100.0
            k, dx, dy, resid = register(A, B)
            got.append({"t": round(t, 2), "gross_pct": round(gross, 2),
                        "registered_pct": round(float(np.mean(resid)) * 100.0, 2),
                        "block_max_pct": round(block_max(resid) * 100.0, 2),
                        "camera": {"k": round(float(k), 4),
                                   "dx": round(float(dx), 2), "dy": round(float(dy), 2)}})
        if not got:
            continue
        rows.append({
            "shot": f"S{i+1}", "from_s": round(t0, 2), "to_s": round(t1, 2),
            "gross_pct": round(max(g["gross_pct"] for g in got), 2),
            "registered_pct": round(max(g["registered_pct"] for g in got), 2),
            "block_max_pct": round(max(g["block_max_pct"] for g in got), 2),
            "samples": got,
        })

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump({"floor_pct": a.floor, "gap_frames": a.gap, "shots": rows},
              open(a.out, "w"), indent=1)

    print(f"{'shot':>5}  {'window':>14}  {'gross':>7}  {'registered':>11}  {'block_max':>10}")
    dead = []
    for r in rows:
        flag = ""
        if r["block_max_pct"] < a.floor:
            dead.append(r)
            flag = "   <- nothing articulates here"
        print(f"{r['shot']:>5}  {r['from_s']:>6.1f}-{r['to_s']:<7.1f}  "
              f"{r['gross_pct']:>6.2f}%  {r['registered_pct']:>10.2f}%  "
              f"{r['block_max_pct']:>9.2f}%{flag}")

    if rows:
        g = sum(r["gross_pct"] for r in rows) / len(rows)
        reg = sum(r["registered_pct"] for r in rows) / len(rows)
        print(f"\nfilm mean: gross {g:.2f}%, registered {reg:.2f}%. The gap between those "
              f"two numbers is camera,")
        print("and quoting the left one as proof the figures are alive is the mistake this "
              "file exists to stop.")

    if dead:
        print(f"\n{len(dead)} shot(s) below the {a.floor}% articulation floor: "
              + ", ".join(r["shot"] for r in dead))
        print("With the camera solved out, no sixteenth of these frames changes. That is")
        print("what every judge this run meant by 'static', and it is not a taste note,")
        print("it is a measurement. Give the held figures real amplitude, or give the")
        print("shot an event, before spending a panel on it.")
        if a.strict:
            return 1
    elif rows:
        print(f"\nmotion_check: every shot clears the {a.floor}% articulation floor")
    print(f"wrote {os.path.relpath(a.out, REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
