#!/usr/bin/env python3
"""Find windows where the STORY REGION stops changing, with the near field excluded.

WHY THIS EXISTS (2026-08-08). The previous round's panel charged the film with a dead lower
third, so a near-field foreground was added and raised into the shipped 1:1 crop. It worked.
It also broke the gate that watches for dead windows, because that gate measures the WHOLE
frame, and the foreground bobs continuously. Every frame now contains motion, so no window
can ever look dead, whatever the story region is doing.

A judge measured what the gate could no longer see: two stretches longer than the gate's own
5-second rule where the content region barely changed at all, one of them six full seconds
under the ALLOWABLE USES panel. The film had two of the exact defect the gate exists to
prevent, and the gate reported nothing, because the fix for the previous finding had blinded
it.

That is the most dangerous shape a defect can take here. It is not a checker pointed at the
wrong file or parsing zero scenes; it is a checker whose subject moved out from under it
while it kept returning true. Nothing about it looks wrong from the outside.

So this measures the region that actually carries the story: the square deliverable with the
near-field band and the caption card excluded. Everything below CONTENT_BOTTOM is furniture
or subtitle, and neither is an argument for the frame being alive.

Exit 0 clean, exit 1 with findings. Advisory by default in preflight; the numbers are the
point, not the exit code.
"""
import argparse
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# The 1:1 crop is master rows 420..1500. Inside that square, the near-field foreground starts
# at master y=1384 (square row 964) and the caption card spans master 1336..1468 (square
# 916..1048). Both are excluded: what remains is the story region.
CONTENT_BOTTOM = 840
FPS = 2.0            # sample rate
LOOKAHEAD_S = 1.0    # compare each frame against the frame one second later
DIFF_THRESH = 12     # per-pixel 8-bit delta that counts as "changed"
MIN_DEAD_S = 5.0     # the gate's own dead-window rule
DEFAULT_PCT = 12.0   # below this share of changed pixels, the region is not doing anything


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(REPO, "out", "dispatch", "dispatch_square.mp4"))
    ap.add_argument("--pct", type=float, default=DEFAULT_PCT)
    ap.add_argument("--min-dead", type=float, default=MIN_DEAD_S)
    a = ap.parse_args()

    if not os.path.exists(a.video):
        print(f"content_sag_check: SKIP, {os.path.relpath(a.video, REPO)} not present")
        return 0
    try:
        import numpy as np
    except Exception:
        print("content_sag_check: SKIP, numpy unavailable")
        return 0

    w, h = 270, 270
    keep = int(h * CONTENT_BOTTOM / 1080)
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"fps={FPS},scale={w}:{h},format=gray",
         "-f", "rawvideo", "-"], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        print("content_sag_check: SKIP, could not decode")
        return 0

    buf = np.frombuffer(p.stdout, dtype=np.uint8)
    n = len(buf) // (w * h)
    frames = buf[:n * w * h].reshape(n, h, w)[:, :keep, :].astype(np.int16)

    step = max(1, int(round(LOOKAHEAD_S * FPS)))
    pcts = []
    for i in range(n - step):
        d = np.abs(frames[i + step] - frames[i])
        pcts.append(100.0 * float((d > DIFF_THRESH).mean()))

    # contiguous runs under the threshold
    runs, start = [], None
    for i, v in enumerate(pcts):
        if v < a.pct:
            start = i if start is None else start
        else:
            if start is not None and (i - start) / FPS >= a.min_dead:
                runs.append((start / FPS, i / FPS, min(pcts[start:i])))
            start = None
    if start is not None and (len(pcts) - start) / FPS >= a.min_dead:
        runs.append((start / FPS, len(pcts) / FPS, min(pcts[start:])))

    med = float(np.median(pcts)) if pcts else 0.0
    print(f"content_sag_check: {n} frames at {FPS}fps, story region = square rows "
          f"0..{CONTENT_BOTTOM} (near field and caption card excluded); "
          f"median 1s novelty {med:.1f}%")
    if not runs:
        print(f"PASS [content_sag_check] no window of {a.min_dead:.0f}s or longer sits under "
              f"{a.pct:.0f}% changed.")
        return 0

    print(f"FAIL [content_sag_check] {len(runs)} window(s) where the story region stops moving:")
    for t0, t1, lo in runs:
        print(f"  {t0:6.2f}s .. {t1:6.2f}s  ({t1 - t0:.2f}s continuous, floor {lo:.1f}%)")
    print()
    print("  The whole-frame dead-window gate cannot see these: the near-field foreground")
    print("  bobs continuously, so every frame contains motion whatever the story is doing.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
