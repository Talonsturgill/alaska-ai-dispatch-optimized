#!/usr/bin/env python3
"""Static gate: nothing informational may be authored into the open-caption band.

WHY THIS EXISTS (2026-08-06). Round 1's panel put "typography and captions" in the
weakest column for two of three judges, and the specific complaint was plated
annotations bisected by, buried under, or pushed below the open-caption card. The fix
that round was a HARD CLAMP inside the Plate component: a plate can never enter the
band, whatever a call site asks for.

The clamp was right and it was not enough, because it is SILENT. In S10 a call site
asked for y=1520 — visually sensible, below the caption card — and the clamp correctly
hauled it back up to ~1251, which is precisely where a different plate was already
sitting. Two plates rendered into the same pixels. The clamp turned one defect into
another one, and nothing anywhere said so: the source read fine, the types checked, the
render succeeded. It took reading the geometry by hand to find.

Two lessons, and this file is both of them.

  1. A clamp that silently overrides an author is a lie the source tells about itself.
     If the y in the code is not the y on screen, that must be an ERROR at build time,
     not a quiet correction at render time.
  2. The clamp only protects <Plate>. Raw <rect> and <text> go straight to the SVG, and
     three of them were sitting in the band: S1's SAME PIPE label at y=1424, S5's vendor
     card at 1300..1354, S10's calendar at 1330..1458. The component-level guard could
     never have seen any of them.

So this checks the SOURCE, where the mistake is actually made. Elements that genuinely
belong in the band — room floors, background fills, the caption card itself — declare it
with a `data-band="ok"` attribute (or a `caption-band-ok` comment on the same line or the
line above, where an attribute will not fit). That is a rule an author can satisfy on
purpose and cannot satisfy by accident. The attribute form is preferred because it rides
on the element itself: a refactor that moves the rect carries the exemption with it,
where a comment on a neighbouring line silently stops applying.

Exit 0 clean, exit 1 with findings. Wire it BEFORE the render, never after: this is a
gate on the source, and its whole value is refusing to spend seven minutes of render on
a frame that was already wrong.
"""
import argparse
import glob
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Read the band out of the episode itself rather than hardcoding it here, so an episode
# that moves its caption card cannot silently fall out of the gate's coverage.
CAPTION_H = 132
OK = "caption-band-ok"

# The shipped LinkedIn cut is crop=1080:1080:0:420 off the 1080x1920 master, so scene rows
# above 420 are not in the deliverable most of the audience sees.
SQUARE_TOP = 420

# ...BUT AN AUTHORED y IS NOT A RENDERED y, and this is the part that fooled the first
# version of this check. Every scene sits inside World, which applies a continuous push:
#
#     translate(540+dx, 960+dy) scale(k) translate(-540,-960),  k = 1 + 0.062*push
#
# so a point at scene y maps to 960 + (y - 960)*k + dy. Above the centre line that scale
# drives things UP, and by the end of a shot it is worth about 32px at y=450. That is
# exactly how c18 "FREE UNDER 5 STAFF HOURS A MONTH", authored at y=452 with a span of
# 428..476 that looks safely clear of 420 on paper, ended up sliced in half by the crop
# line on the delivered square. Naive arithmetic said it was fine and the render disagreed.
#
# Worst case is the largest push (1.0) at the end of a shot, with the drift at its most
# negative. Modelled conservatively for every scene rather than parsing each World's push,
# so the bound is never too loose.
K_MAX = 1.062
DY_MAX = 14.0


def world_top(scene_y):
    """Where a scene-space y can render at worst, once World's push is applied."""
    return 960.0 + (scene_y - 960.0) * K_MAX - DY_MAX


# the lowest authored TOP edge that still clears the crop line at full push
SAFE_Y_MIN = 960.0 - (960.0 - SQUARE_TOP - DY_MAX) / K_MAX

NUM = r"\{(-?\d+(?:\.\d+)?)\}"


def band_of(src, path):
    m = re.search(r"^const CAPTION_TOP = (\d+);", src, re.M)
    if not m:
        return None
    top = int(m.group(1))
    return top, top + CAPTION_H


def guard_of(src):
    """The y a Plate is clamped to: CAP_GUARD = CAPTION_TOP - 34, minus half its height."""
    m = re.search(r"CAP_GUARD = CAPTION_TOP - (\d+)", src)
    top = int(re.search(r"^const CAPTION_TOP = (\d+);", src, re.M).group(1))
    return top - int(m.group(1)) if m else top


def exempt(lines, i):
    if OK in lines[i] or 'data-band="ok"' in lines[i]:
        return True
    return i > 0 and OK in lines[i - 1]


def check(path):
    src = open(path).read()
    band = band_of(src, path)
    if band is None:
        return []
    lo, hi = band
    guard = guard_of(src)
    lines = src.split("\n")
    out = []

    for i, ln in enumerate(lines):
        if exempt(lines, i):
            continue

        # --- raw geometry authored into the band -----------------------------
        for tag in ("rect", "text", "ellipse", "circle", "image"):
            if f"<{tag}" not in ln:
                continue
            ym = re.search(r"\by=" + NUM, ln)
            if not ym:
                continue
            y = float(ym.group(1))
            hm = re.search(r"\bheight=" + NUM, ln)
            y1 = y + (float(hm.group(1)) if hm else 0.0)
            if y1 >= lo and y <= hi:
                out.append((path, i + 1, "RAW",
                            f"<{tag}> spans y {y:g}..{y1:g}, inside the caption band {lo}..{hi}"))
            break

        # --- a Plate whose authored y is not the y it renders at -------------
        if "<Plate" in ln:
            blk = "\n".join(lines[i:i + 3])
            ym = re.search(r"\by=" + NUM, blk)
            if not ym:
                continue
            y = float(ym.group(1))
            sm = re.search(r"\bsize=" + NUM, blk)
            size = float(sm.group(1)) if sm else 26.0
            half = (size + 24) / 2.0
            eff = min(y, guard - half)
            if abs(eff - y) > 0.5:
                out.append((path, i + 1, "CLAMPED",
                            f"<Plate y={y:g} size={size:g}> renders at y={eff:g}, "
                            f"{y - eff:g}px above where the call site puts it"))

            # --- and the OTHER edge, which cost this run two claim cards -----
            # The shipped LinkedIn deliverable is the 1:1 square, crop=1080:1080:0:420, so
            # scene y < 420 does not exist for most of the audience. On 2026-08-06 two cards
            # were authored above it: c18 "FREE UNDER 5 STAFF HOURS A MONTH" at y=452 was
            # sliced exactly in half, and c20 "YOU'LL GET IT WHEN YOU GET IT" at y=392 was
            # cut ENTIRELY — the square viewer never saw that claim at all.
            #
            # crop_safety.py does catch this, but only by sampling a finished render, which
            # means the cost of the mistake is a full render plus an encode plus somebody
            # reading an advisory carefully enough not to wave it through as decorative.
            # It is arithmetic on a literal, so it belongs here, before the render.
            top = world_top(y - half)
            if top < SQUARE_TOP:
                how = ("wholly above it, invisible in the shipped 1:1 cut"
                       if world_top(y + half) <= SQUARE_TOP else "cut by it")
                out.append((path, i + 1, "CROPPED",
                            f"<Plate y={y:g} size={size:g}> authored top {y - half:g} "
                            f"RENDERS at {top:.0f} under the World push, crossing the square "
                            f"crop line at y={SQUARE_TOP} - {how}. Lowest safe y is "
                            f"{SAFE_Y_MIN + half:.0f}."))
    return out


def default_targets():
    """This run's episode only.

    Deliberately NOT every Ep*.tsx. The older episodes are shipped and published, and
    they fail this gate — that is what a new standard looks like on the day it is
    written. Retrofitting them would mean re-rendering and re-publishing films that are
    already out, which is rewriting history to make a checker happy. The gate binds what
    this run is about to render; pass explicit paths to audit anything else.
    """
    stamp = os.path.join(REPO, "out", "dispatch", ".run_stamp.json")
    src = os.path.join(REPO, "video-engine", "src")
    if os.path.exists(stamp):
        import json
        comp = json.load(open(stamp)).get("composition") or ""
        # the composition id is not the filename (id="Dispatch0806", file Ep0806.tsx), so
        # resolve it through Root.tsx the way Remotion does rather than guessing a path
        root = os.path.join(src, "Root.tsx")
        if comp and os.path.exists(root):
            r = open(root).read()
            m = re.search(r'id="' + re.escape(comp) + r'"\s*\n\s*component=\{(\w+)\}', r)
            if m:
                mi = re.search(r"import\s*\{[^}]*\b" + m.group(1) + r"\b[^}]*\}\s*from\s*'\./(\w+)'", r)
                if mi and os.path.exists(os.path.join(src, mi.group(1) + ".tsx")):
                    return [os.path.join(src, mi.group(1) + ".tsx")]
    return sorted(glob.glob(os.path.join(src, "Ep*.tsx")))[-1:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", default=default_targets())
    a = ap.parse_args()

    findings = []
    for t in a.targets:
        findings += check(t)

    if not findings:
        print(f"caption_band_check: clean across {len(a.targets)} file(s)")
        return 0

    for path, line, kind, msg in findings:
        print(f"{os.path.relpath(path, REPO)}:{line}  {kind}  {msg}")
    print(f"\ncaption_band_check: {len(findings)} finding(s).")
    print("Move the element clear of the band, or mark the line `caption-band-ok` if it")
    print("is background that genuinely belongs under the caption card.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
