#!/usr/bin/env python3
"""Check the DERIVED square cut is safe, instead of convening a panel on it.

WHY THIS EXISTS (2026-08-04, owner's process call).

The run had been grading BOTH deliverables with the full 3-judge panel every round.
That is double the review surface for one film, and it actively hurt: judges spent
findings on the 9:16 padding and on square-crop collisions in the same cards, the two
sets of notes competed for the same fix budget, and the composition axis was being
marked down twice for what is one authoring decision. The owner's instruction: make ONE
version right, then reformat and make a couple of tweaks, and stop checking both every
single time.

So the panel grades the MASTER (1080x1920), which is the native canvas and the cut that
goes to the other social platforms. The LinkedIn square is DERIVED from it by
crop=1080:1080:0:420, and its correctness is a mechanical question, not a taste one:
does the crop slice anything that matters?

That is what this measures. For each sampled frame it looks at the two crop boundary
rows and asks whether structured content (plate edges, type, ink outlines) crosses them.
Background gradient crossing a crop line is fine and expected. A headline plate, a
caption band or a character's head crossing one is not, because in the square that
becomes a thing cut in half at the frame edge.

HONEST LIMITS, stated so a pass is not over-read:
  - It detects STRUCTURE crossing the boundary, not meaning. A decorative foreground
    bough crossing the bottom line will flag, and that is a false positive a human
    dismisses in one look at the named timecode.
  - It says nothing about whether the square composition is well-staged, only that it
    does not cut through something built.
  - It samples; it does not check every frame.
"""
import argparse
import os
import subprocess
import sys

import numpy as np
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

CROP_TOP = 420      # square is crop=1080:1080:0:420 off the 1080x1920 master
CROP_BOT = 420 + 1080
BAND = 4            # rows either side of the boundary to examine
# fraction of a boundary row that may carry strong local gradient before we call it
# "something built is being cut". Tuned so a sky or ground gradient passes and a plate
# edge or a run of type does not.
MAX_STRUCTURED = 0.06
GRAD_THRESH = 26    # per-channel step that counts as an edge


def frames(path, every):
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path],
        capture_output=True, text=True).stdout.strip())
    t = 0.5
    while t < dur:
        yield t
        t += every


def grab(path, t):
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", path, "-frames:v", "1",
         "-f", "image2pipe", "-vcodec", "png", "-"],
        capture_output=True)
    if not p.stdout:
        return None
    import io
    return np.asarray(Image.open(io.BytesIO(p.stdout)).convert("RGB"), dtype=np.int16)


def structured_fraction(img, y):
    """Fraction of the row at y whose vertical neighbourhood carries a real edge."""
    lo, hi = max(0, y - BAND), min(img.shape[0] - 1, y + BAND)
    strip = img[lo:hi + 1]
    # vertical gradient across the boundary, max over channels
    g = np.abs(np.diff(strip.astype(np.int16), axis=0)).max(axis=2).max(axis=0)
    return float((g > GRAD_THRESH).mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default=os.path.join(REPO, "out", "dispatch", "dispatch_master.mp4"))
    ap.add_argument("--every", type=float, default=2.0, help="seconds between samples")
    ap.add_argument("--max-structured", type=float, default=MAX_STRUCTURED)
    a = ap.parse_args()

    if not os.path.exists(a.master):
        print(f"crop-safety: MISSING {a.master}")
        return 2

    bad, checked = [], 0
    for t in frames(a.master, a.every):
        img = grab(a.master, t)
        if img is None or img.shape[0] < CROP_BOT:
            continue
        checked += 1
        for name, y in (("top", CROP_TOP), ("bottom", CROP_BOT)):
            f = structured_fraction(img, y)
            if f > a.max_structured:
                bad.append((round(t, 2), name, round(f, 3)))

    for t, name, f in bad:
        print(f"CUT  t={t:>6}s  {name} crop line  structured={f} "
              f"(limit {a.max_structured})")

    print(f"crop-safety: {checked} frames sampled at the square's crop lines "
          f"(y={CROP_TOP} and y={CROP_BOT}), {len(bad)} crossing")
    if checked == 0:
        print("crop-safety: GATE IS DEAD. It sampled nothing, which is not a pass.")
        return 2
    if bad:
        print("  Each line above names a moment where the square crop cuts through "
              "something built. Look at the timecode before dismissing it: a decorative "
              "foreground element crossing the line is fine, a plate or a head is not.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
