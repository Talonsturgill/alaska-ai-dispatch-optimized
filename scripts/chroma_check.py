#!/usr/bin/env python3
"""DOES THE DELIVERED PICTURE ACTUALLY LOOK THE WAY THE STORY SAID IT WOULD?

WHY THIS EXISTS (2026-08-13)
----------------------------
Owner: "all the last videos just feel like down, or intense or kinds of like doomy". Two fixes
landed before this one. get_music.py now refuses a cold bed for a hopeful story, and
storyboard_check.py now refuses a board whose PALETTE PROSE reads cold against a hopeful stance.
Both are real and both share scripts/valence.py so they cannot drift.

Neither of them looks at a single pixel.

A board can write "warm amber light through the bay door" in its fingerprint, satisfy the prose
gate, and render a grey room, because the fingerprint is a promise and the render is the thing
the audience receives. Every other lesson today has the same shape: motion that was authored and
sub-pixel, an exhaust plume the same luminance as its wall, a sound design nobody could see. The
picture is what is graded, so the picture is what has to be measured.

WHAT IT MEASURES, on frames sampled from the DELIVERED cut:
  saturation  mean HSV S. A grey film is grey because nothing is saturated.
  warmth      share of reasonably-saturated pixels whose hue is red/orange/yellow rather than
              cyan/blue. This is the axis that reads as "cold" to a viewer.
  luma        mean V. Doomy is usually dark as well as desaturated, but not always, so this is
              reported and only counts as corroboration.

WHAT IT DOES NOT DO. It does not demand brightness of every film. A cautionary story is allowed
to be cold and a mixed stance is left alone entirely, exactly as valence.py decides for the bed
and the board. It only fires when the writers room COMMITTED to a hopeful stance and the pixels
argue the opposite.

CALIBRATION HONESTY. The thresholds below were set with the 2026-08-13 film measured and in
view, and that film FAILS them. They are not set where the current film passes; they are set
where a grey film fails and a film with any real colour in it does not. The numbers, and the
reasoning, are printed on every run so a future maintainer can argue with them from evidence.

  python3 scripts/chroma_check.py [video.mp4] [--frames 24] [--json]

Exit 0 pass or not-applicable, 1 on a genuine mismatch.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, ".."))
sys.path.insert(0, _HERE)

DEFAULT_VIDEO = os.path.join(REPO, "out", "dispatch", "dispatch_master.mp4")

# THRESHOLDS, CALIBRATED BY MEASUREMENT AND NOT BY GUESS.
#
# I first wrote 0.16/0.45 with GUESSED reference numbers in the comment (saturation 0.10,
# warmth 0.28). Then I measured, and both the guess and one threshold were wrong. The 08-13 cut
# reads saturation 0.136, warmth 0.171.
#
# The instrument was then validated differentially against the film's own two worlds, because a
# metric nobody has checked is the thing this repo has been burned by all day:
#     St Mary's dock, 90-96s   saturation 0.140   warmth 0.810
#     powerhouse,     30-80s   saturation 0.119   warmth 0.097
# Three panel judges independently called that dock beat the only chromatic relief in the film
# and the best-looking thing in it, so a +0.713 warmth delta is the instrument agreeing with
# human eyes about the one comparison those eyes made unprompted. WARMTH IS THE REAL AXIS.
#
# SATURATION IS A WEAK DISCRIMINATOR HERE and I nearly shipped it as a hard gate. The delta
# between the film's warmest and coldest worlds is +0.021, because the flat-vector house style
# is modestly saturated everywhere by design. A 0.16 floor would have failed the dock -- a frame
# the panel praised -- which is a gate punishing good work. It is now a floor for GENUINELY
# COLOURLESS only, set below the known-good dock rather than above it.
MIN_WARMTH = 0.45       # sits between the cold world (0.097) and the warm one (0.810)
MIN_SATURATION = 0.10   # below the known-good dock at 0.140; only catches an actually grey film
SAT_FLOOR_FOR_HUE = 0.12  # ignore near-grey pixels when asking "which way does the colour lean"


def sample_frames(video, n):
    """Evenly spaced JPEGs from the whole runtime, avoiding the first and last second."""
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
        capture_output=True, text=True, check=True).stdout.strip())
    out = []
    d = tempfile.mkdtemp(prefix="chroma")
    for i in range(n):
        t = 1.0 + (dur - 2.0) * (i / max(1, n - 1))
        p = os.path.join(d, f"f{i:03d}.jpg")
        subprocess.run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
                        "-vf", "scale=240:-1", "-q:v", "4", p, "-v", "error"], check=True)
        if os.path.exists(p):
            out.append((t, p))
    return out, dur


def measure(paths):
    from PIL import Image
    import numpy as np
    sats, warms, lumas = [], [], []
    for _, p in paths:
        hsv = np.asarray(Image.open(p).convert("HSV"), dtype=np.float64)
        h, s, v = hsv[..., 0] / 255.0, hsv[..., 1] / 255.0, hsv[..., 2] / 255.0
        sats.append(float(s.mean()))
        lumas.append(float(v.mean()))
        # hue in PIL HSV is 0..1 around the wheel; warm is red/orange/yellow plus the magenta
        # side, cold is the green/cyan/blue arc. Only ask of pixels with real colour in them.
        m = s >= SAT_FLOOR_FOR_HUE
        if m.sum() > 0:
            hh = h[m]
            warm = ((hh < 0.14) | (hh > 0.90)).sum()
            warms.append(float(warm) / float(m.sum()))
        else:
            warms.append(0.0)
    n = len(sats)
    return {"frames": n,
            "saturation": sum(sats) / n,
            "warmth": sum(warms) / n,
            "luma": sum(lumas) / n}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", default=DEFAULT_VIDEO)
    ap.add_argument("--frames", type=int, default=24)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        import valence as V
    except ImportError:
        print("chroma_check: cannot import scripts/valence.py; the check is unenforceable, "
              "which is a failure rather than a skip.")
        return 1

    up, down, had = V.stance()
    if not had:
        print("chroma_check: no out/dispatch/angle.json, so there is no committed stance to "
              "measure the picture against. Not applicable.")
        return 0
    if not V.wants_warm():
        print(f"chroma_check: the committed stance is not hopeful-leaning "
              f"(up={up} down={down}), so a cold world is a legitimate choice. Not applicable.")
        return 0
    if not os.path.exists(a.video):
        print(f"chroma_check: no video at {a.video}")
        return 1

    frames, dur = sample_frames(a.video, a.frames)
    m = measure(frames)
    if a.json:
        print(json.dumps(m, indent=1))

    print(f"chroma_check: {m['frames']} frames across {dur:.0f}s of {os.path.basename(a.video)}")
    print(f"  saturation {m['saturation']:.3f}  (floor {MIN_SATURATION}, weak axis in this style)")
    print(f"  warmth     {m['warmth']:.3f}  (floor {MIN_WARMTH})  share of coloured pixels on the warm arc")
    print(f"  luma       {m['luma']:.3f}  (reported, corroborating only)")

    bad = []
    if m["saturation"] < MIN_SATURATION:
        bad.append(f"saturation {m['saturation']:.3f} is under {MIN_SATURATION}: the delivered "
                   f"world is colourless, whatever the board's palette prose promised")
    if m["warmth"] < MIN_WARMTH:
        bad.append(f"warmth {m['warmth']:.3f} is under {MIN_WARMTH}: what colour there is sits on "
                   f"the cold side of the wheel")
    if bad:
        print("\nFAIL [chroma_check] the writers room committed to a hopeful stance and the "
              "PIXELS argue the opposite.")
        for b in bad:
            print(f"  {b}")
        print("\n  The board's fingerprint is a promise; this is the film. A palette gate that")
        print("  reads prose cannot catch a board that writes 'warm amber' and renders slate.")
        print("  Warm the actual render, or change the angle -- the angle decides this.")
        return 1
    print("\nPASS [chroma_check] the delivered picture matches the stance the story committed to.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
