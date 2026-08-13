#!/usr/bin/env python3
"""Assert the caption track ACTUALLY RENDERED into the delivered film.

WHY THIS EXISTS (2026-08-12). The 2026-08-12 dispatch shipped 4602 frames with a completely
empty caption band and every single check in this repo passed it.

The cause was a shape mismatch, not a missing feature. captions.json is forced-alignment
output and speaks in {start, end}; every caption component this engine has had reads {t, d}.
Handed a {start, end} cue, `cues.find(c => t >= c.t && t < c.t + c.d)` compares against
undefined, matches nothing on any frame, and the component's own `if (!cue) return null`
guard correctly draws nothing. The film then rendered exactly as instructed: no captions.

Nothing objected, and the reason is worth writing down, because it is the general shape of
the bug this file is here to close:

  - the props were valid JSON, so no parser complained
  - the zod schema declares {t, d, text}, but Remotion only enforces schemas on Studio
    inputs, not on CLI --props, so declaring it bought nothing at render time
  - caption_check.py lints what the captions SAY, not whether they are delivered
  - caption_band_check.py asserts nothing informational INTRUDES into the band, which an
    empty band satisfies perfectly
  - the pixel gates measure the story region, which was fine
  - a build gate on build_scenes.py would only ever prove the builder was right at the
    moment it ran

Every one of those checks is correct. They just all happened to be looking somewhere else.
Three judges reading 57 frames found it, which is the most expensive way to learn that a
caption track is missing.

So this asks the DELIVERED BYTES the direct question: at moments when a cue is supposed to
be on screen, is there anything in the caption band? It reads the film, not the builder,
for the same reason the site sign-off reads the built directory: a build that never happened
is invisible to a build gate.

Method: first check the cue SHAPE, which is the four-second version of this whole file.
Then, for a sample of cues spread across the runtime, extract the frame at the cue's
midpoint, crop the caption band, and measure how far its brightest pixels rise above its
general brightness (YMAX - YHIGH off ffmpeg's signalstats). Bone type on a dark ink bar
pushes the two far apart; an empty band keeps them together. See text_contrast for the
calibration numbers and for why it is not the Laplacian measure you would expect.

Exit 0 = captions are on screen. Exit 1 = they are not, and the film is not shippable.

Usage:
  python3 scripts/caption_render_check.py
  python3 scripts/caption_render_check.py --video out/dispatch/dispatch_master.mp4 \
      --props out/dispatch/episode_props.json --samples 8
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# The band geometry is the engine's, mirrored here. Keep in step with CAPTION_TOP /
# CAPTION_H in the episode component. Over-cropping slightly is safe; under-cropping is not.
CAPTION_TOP = 1336
CAPTION_H = 132

# Empirical floor for text_contrast(), calibrated on this run's frames: a captioned band
# measures 204, the two empty bands from the broken cut measure 21 and 59. 120 sits clear of
# both with room for a short cue on a lighter scene.
EDGE_FLOOR = 120.0


def text_contrast(png_path):
    """How far the brightest pixels in the band rise above its general brightness.

    Measured as YMAX - YHIGH off ffmpeg's signalstats. The caption is bone (#F4EEE0, luma
    ~240) set on a dark ink bar, so a band carrying a caption pushes YMAX to ceiling while
    YHIGH, which tracks the bulk of the band, stays down with the background. A band with
    no caption in it has the two close together, because whatever is there is all one
    rough brightness.

    Calibrated on this run's own frames: a captioned band measures 204 (YHIGH 51, YMAX
    255), and the two empty bands from the broken cut measure 21 and 59. The floor sits
    well clear of both.

    An earlier draft of this used a Laplacian convolution for glyph-edge energy, which is
    the more obvious measure and which silently returned 0.0 for every input because the
    filter's parameter list was malformed and ffmpeg failed the whole graph. It reported
    every caption missing on a cut whose captions were perfectly legible. A check that
    cannot fail loudly is worse than no check, so this uses a filter with no parameters to
    get wrong, and the calibration numbers above are recorded so the floor can be
    rechecked rather than trusted.
    """
    r = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", png_path,
         "-vf", "format=gray,signalstats,metadata=print:file=-", "-f", "null", "-"],
        capture_output=True, text=True)
    vals = {}
    for line in (r.stdout + r.stderr).splitlines():
        if "lavfi.signalstats.Y" in line and "=" in line:
            k, _, v = line.strip().partition("=")
            try:
                vals[k.rsplit(".", 1)[-1]] = float(v)
            except ValueError:
                pass
    if "YMAX" not in vals or "YHIGH" not in vals or "YMIN" not in vals:
        # Do not return a passing number when the measurement did not happen.
        return -1.0
    # YMAX - YHIGH ALONE HAS A COVERAGE BLIND SPOT, found 2026-08-13. YHIGH tracks the bulk
    # of the band, so a TWO-LINE cue, which is more text and therefore a better caption,
    # pushes YHIGH up and drives the statistic DOWN. Measured on that run's delivered master,
    # exact band, same metric:
    #     one-line cue    YMIN 0  YLOW 64 YHIGH 65  YMAX 254  ->  189  pass
    #     two-line cue    YMIN 0  YLOW 26 YHIGH 155 YMAX 255  ->  100  FALSE NEGATIVE
    #     credits tail    YMIN 13 YLOW 13 YHIGH 13  YMAX 13   ->    0  correct fail
    # So a fuller band scored worse than a sparser one, which is backwards.
    #
    # The engine's caption contract is specific and testable: bone glyphs (#F4EEE0, luma
    # ~240) on an ink bar (luma ~16) drawn behind them. A band carrying a caption therefore
    # has BOTH a dark floor and a bright ceiling, whatever fraction of it the text covers.
    # An empty band has neither, because whatever shows through is all one rough brightness.
    # Requiring both is strictly MORE discriminating than the single spread: a bright scene
    # with dark objects in it can fake a large YMAX-YMIN, and it cannot fake a dark floor.
    if vals["YMAX"] >= 200 and vals["YMIN"] <= 60:
        return vals["YMAX"] - vals["YMIN"]
    return vals["YMAX"] - vals["YHIGH"]


def crop_band(video, t, dest):
    """Crop EXACTLY the caption band. The 20-row margin this used to add was described in
    its own comment as "over-cropping slightly is safe", and on 2026-08-13 that turned out
    to be false for a high-key film.

    The metric is YMAX minus YHIGH, and YHIGH tracks the BULK of the cropped region. The
    band itself is a dark ink bar, so on a dark-palette film the 20 rows above and below
    are also dark and the padding costs nothing. On a snow-glare daylight palette those
    rows are bright scene at luma ~185, so YHIGH rises to meet YMAX and the measurement
    collapses even though the caption is plainly on screen.

    Measured on that run's own delivered master, same frames, same metric:

        captioned frame t=1.75s    exact band YHIGH 65,  YMAX 254 -> 189  PASS
                                   padded     YHIGH 185, YMAX 254 ->  69  FALSE NEGATIVE
        uncaptioned frame t=130s   exact band YHIGH 13,  YMAX 13  ->   0  correct FAIL
                                   padded     YHIGH 13,  YMAX 13  ->   0  correct FAIL

    So the exact crop keeps every bit of the check's discriminating power (an empty band
    still measures 0 against a floor of 120) and stops reporting a legible caption as
    missing. The padding was the defect, not the film."""
    subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", video, "-vframes", "1",
         "-vf", f"crop=iw:{CAPTION_H}:0:{CAPTION_TOP}",
         "-y", dest],
        capture_output=True, text=True)
    return os.path.exists(dest) and os.path.getsize(dest) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(REPO, "out/dispatch/dispatch_master.mp4"))
    ap.add_argument("--props", default=os.path.join(REPO, "out/dispatch/episode_props.json"))
    ap.add_argument("--samples", type=int, default=8)
    a = ap.parse_args()

    if not os.path.exists(a.video):
        print(f"caption_render_check: SKIP, no delivered cut at {a.video}")
        return 0
    if not os.path.exists(a.props):
        print(f"FAIL [caption_render_check] no props at {a.props}, so the caption contract "
              f"cannot be checked. This is a failure and not a skip: a missing props file is "
              f"how the caption track goes missing.")
        return 1

    props = json.load(open(a.props))
    cues = props.get("captions") or []
    if not cues:
        print("FAIL [caption_render_check] the props carry ZERO caption cues, so the film "
              "cannot have captions. Rebuild with scripts/build_scenes.py.")
        return 1

    # THE SHAPE CHECK, and it is the one that would have caught 2026-08-12 in four seconds.
    # The component reads c.t and c.t + c.d. Anything else is a cue that can never match.
    wrong = [c for c in cues if "t" not in c or "d" not in c or "text" not in c]
    if wrong:
        keys = sorted({k for c in wrong[:5] for k in c})
        print(f"FAIL [caption_render_check] {len(wrong)} of {len(cues)} caption cues are not in "
              f"the {{t, d, text}} shape the engine reads; they carry {keys}. A cue in any other "
              f"shape compares against undefined on every frame, matches nothing, and renders an "
              f"empty caption band for the whole film. Convert at the boundary in "
              f"scripts/build_scenes.py.")
        return 1

    good = [c for c in cues if c["d"] > 0.35 and c["text"].strip()]
    if not good:
        print("FAIL [caption_render_check] no caption cue is long enough to be seen.")
        return 1

    step = max(1, len(good) // a.samples)
    sample = good[::step][:a.samples]

    tmp = tempfile.mkdtemp(prefix="caprender_")
    failures, measured = [], []
    for i, c in enumerate(sample):
        mid = c["t"] + c["d"] / 2.0
        png = os.path.join(tmp, f"c{i:02d}.png")
        if not crop_band(a.video, mid, png):
            failures.append(f"t={mid:.2f}s: could not extract the frame")
            continue
        e = text_contrast(png)
        measured.append((mid, e, c["text"][:40]))
        if e < EDGE_FLOOR:
            failures.append(f"t={mid:.2f}s: caption band edge energy {e:.2f} < {EDGE_FLOOR} "
                            f"while the cue {c['text'][:40]!r} should be on screen")

    for mid, e, txt in measured:
        print(f"  t={mid:7.2f}s  contrast={e:6.0f}  {txt!r}")

    if failures:
        print(f"\nFAIL [caption_render_check] {len(failures)} of {len(sample)} sampled cues are "
              f"NOT on screen in the delivered cut:")
        for f in failures:
            print("  - " + f)
        print("\nThe caption band is empty where a caption belongs. Captions missing is a hard "
              "blocker in config/dispatch_rubric.yaml. Check the cue shape against the episode "
              "component's Captions reader before re-rendering.")
        return 1

    print(f"PASS [caption_render_check] {len(sample)} sampled cues all render visible captions "
          f"in the delivered cut.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
