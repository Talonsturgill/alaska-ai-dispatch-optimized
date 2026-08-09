#!/usr/bin/env python3
"""Refuse a plate that the scene's CONTENT ZOOM pushes off the side of the frame.

WHY THIS EXISTS (2026-08-09, found by looking at the contact sheet, not by any gate).
------------------------------------------------------------------------------------
`text_fit_check.py` asks whether a string fits the plate drawn behind it. That is the right
question and it is not this one. A plate can fit its own box perfectly and still leave the
frame, because every scene in this engine wraps its children in a CONTENT ZOOM about x=540:

    x_rendered = 540 + (x_authored - 540) * ZOOM

At ZOOM 1.24 an element authored at x=760 with a 555px box renders from 469 to 1157, so 93
pixels of it are outside a 1080-wide frame. On the 2026-08-09 first cut that clipped five
elements, and the worst of them was the film's central quotation: NSF's own sentence lost a
word off each end and read on screen as "FORCEMENT-LEARNING CONTROLLERS ... GRATED WITH MICR".

Nothing caught it. text_fit_check passed, because each string fit its plate. caption_band_check
passed, because it models the VERTICAL crop and this is a horizontal one. plate_overlap_check
passed, because the boxes did not intersect each other. The defect only exists in the
relationship between an authored x and a zoom declared somewhere else in the file, which is
exactly the "derive geometry, never hand-tune it" class from DISPATCH_STANDARD section 4.

WHAT IT DOES: reads the episode source, finds the largest CONTENT_ZOOM any Stage applies,
computes each plate's box from the exact mono advance (0.602em), projects it through the zoom,
and fails on anything crossing the frame edge. It reports the safe authored band so a fix is
arithmetic rather than a guess, and it prints what it could NOT measure so a pass is never
assumed over a string nobody checked.

    python3 scripts/zoom_clip_check.py            # exit 1 on any clipped element
"""
import glob
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRAME_W = 1080
MARGIN = 16          # a plate that touches the very edge reads as clipped even if it is not
DEFAULT_SIZE = {"Plate": 40, "BrassPlate": 34}
LS = 1.6


def mono_w(s: str, size: float, track: float = LS) -> float:
    """Mono advance is exact, so a string's width is arithmetic and never judgement."""
    return len(s) * size * 0.602 + track * max(0, len(s) - 1)


def episode_files():
    """The current run's episode, which is the newest Ep*.tsx. Past episodes are history and
    grading them would fail the run on a film that shipped weeks ago."""
    files = glob.glob(os.path.join(REPO, "video-engine", "src", "Ep*.tsx"))
    return [max(files, key=os.path.getmtime)] if files else []


def max_zoom(src: str) -> float:
    """The largest zoom any Stage in this file applies. Deliberately the MAXIMUM: a plate has
    to survive the worst zoom it can be rendered under, and a scene-by-scene attribution would
    need to resolve which Stage wraps which plate, which is not worth the fragility."""
    zooms = [float(m.group(1)) for m in re.finditer(r"\bCONTENT_ZOOM\s*=\s*([\d.]+)", src)]
    zooms += [float(m.group(1)) for m in re.finditer(r"\bzoom=\{([\d.]+)\}", src)]
    return max(zooms) if zooms else 1.0


def check(path: str):
    src = open(path).read()
    z = max_zoom(src)
    lo_safe = 540 - (540 - MARGIN) / z
    hi_safe = 540 + (FRAME_W - MARGIN - 540) / z
    bad, unmeasured, n = [], [], 0

    for m in re.finditer(r"<(Plate|BrassPlate)\b(.*?)/>", src, re.S):
        kind, blk = m.group(1), m.group(2)
        line = src[:m.start()].count("\n") + 1
        xm = re.search(r"\bx=\{(-?\d+(?:\.\d+)?)\}", blk)
        tm = re.search(r'text="([^"]*)"', blk)
        if not tm:
            unmeasured.append((line, kind, "text is not a plain literal"))
            continue
        if not xm:
            unmeasured.append((line, kind, f"x is not a plain number: {tm.group(1)[:28]}"))
            continue
        x = float(xm.group(1))
        # x=0 means the plate is positioned by a parent transform this checker cannot see
        if x == 0:
            unmeasured.append((line, kind, f"x=0, positioned by a parent transform: {tm.group(1)[:28]}"))
            continue
        sm = re.search(r"\bsize=\{(\d+(?:\.\d+)?)\}", blk)
        size = float(sm.group(1)) if sm else DEFAULT_SIZE[kind]
        w = mono_w(tm.group(1), size) + 56
        sub = re.search(r'sub="([^"]*)"', blk)
        if sub:
            w = max(w, mono_w(sub.group(1), size * 0.54, 1.2) + 56)
        n += 1
        rl = 540 + (x - w / 2 - 540) * z
        rr = 540 + (x + w / 2 - 540) * z
        if rl < MARGIN or rr > FRAME_W - MARGIN:
            bad.append((line, kind, tm.group(1)[:34], round(w), round(rl), round(rr), x))

    return z, lo_safe, hi_safe, bad, unmeasured, n


def main() -> int:
    targets = sys.argv[1:] or episode_files()
    if not targets:
        print("zoom_clip_check: no episode file found, which is itself wrong")
        return 1
    total_bad, total_n = 0, 0
    for path in targets:
        z, lo, hi, bad, unmeasured, n = check(path)
        rel = os.path.relpath(path, REPO)
        total_n += n
        print(f"zoom_clip_check: {rel}  content zoom {z}  "
              f"safe authored span {lo:.0f}..{hi:.0f}")
        for line, kind, text, w, rl, rr, x in bad:
            total_bad += 1
            # the fix, as arithmetic rather than as advice
            need_lo, need_hi = lo + w / 2, hi - w / 2
            print(f"  FAIL {rel}:{line}  {kind} '{text}'")
            print(f"       box {w}px authored at x={x:.0f} renders {rl}..{rr}, outside 0..{FRAME_W}")
            if need_lo > need_hi:
                print(f"       NO x can fit this string at this size. Shorten it or reduce the size.")
            else:
                print(f"       move x into {need_lo:.0f}..{need_hi:.0f}, or reduce the size")
        if unmeasured:
            print("  not measured (stated so coverage is never assumed):")
            for line, kind, why in unmeasured:
                print(f"    {rel}:{line}  {kind}: {why}")
    if total_n == 0:
        print("zoom_clip_check: measured NOTHING, which is a failure and not a pass")
        return 1
    if total_bad:
        print(f"\nzoom_clip_check: {total_bad} element(s) leave the frame under the content zoom.")
        print("A plate can fit its own box perfectly and still be cut in half by the frame edge.")
        return 1
    print(f"zoom_clip_check: clean, {total_n} plated element(s) measured against the frame edge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
