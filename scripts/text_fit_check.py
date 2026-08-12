#!/usr/bin/env python3
"""Assert every plated monospace string fits inside the plate that carries it.

WHY THIS EXISTS (2026-08-04). Three separate on-screen strings shipped past every
existing gate in one cut:

  - "illustrative, the project hasn't run" overflowed its plate on BOTH ends and was
    held to the final frame of both deliverables. One judge scored it a hard blocker.
  - "the count doesn't exist yet" ran edge to edge in the SAFE DAYS card with ~5px of
    local margin, so the terminal 't' merged into the border stroke.
  - "UAF share of a two-award project" was struck through by the comma descenders of
    the $1,588,147 above it.

quality_gate.py passed all three, because nothing in the pipeline related a text run to
the geometry of the rect behind it. The failure mode is always the same and always
mine: the type gets resized to answer a legibility note and the plate does not get
re-measured. That is not a taste problem a judge should have to catch. It is arithmetic.

WHAT IT MEASURES. For a monospace face the advance width is exact, so no rendering is
required. The container resolves ${MONO} to DejaVu Sans Mono (JetBrains Mono is not
installed), whose advance is 1233/2048 em. Width is therefore

    len(text) * size * 0.602  +  letterSpacing * (len(text) - 1)

which is an identity, not an estimate. The check pairs each mono <text> with the
nearest preceding <rect> in the same JSX block and asserts the text's box sits inside
the rect's inner box (rect minus its stroke) with MIN_MARGIN to spare on each side.

HONEST LIMITS, stated because a gate that quietly checks nothing is worse than no gate:
  - It only understands literal sizes and literal strings. Interpolated text ({NAME})
    and computed sizes (fit(...)) are SKIPPED and counted in the skipped tally.
  - It only understands textAnchor="middle" and the default start anchor.
  - It cannot see transforms, so it compares text and rect in their shared local space.
    That is the space they are authored in, which is where the bug lives.
  - It says nothing about vertical collisions between two text runs.
The pass line prints checked/skipped counts. If checked ever drops to zero, the gate has
stopped working and the run should treat that as a failure, not a pass.
"""
import argparse
import math
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# DejaVu Sans Mono advance, 1233/2048 em. Exact for the face the container resolves.
MONO_ADV = 0.602
# Below this the glyph is close enough to the border stroke to read as touching it at
# phone size. Two judges independently called ~5px "zero margin" at 4x zoom.
MIN_MARGIN = 14.0

TEXT_RE = re.compile(
    r"<text\b(?P<attrs>[^>]*?)>\s*(?P<body>[^<>{}]*?)\s*</text>",
    re.S,
)
# x and width are frequently authored as small arithmetic expressions (x={540 - 358},
# x={-W / 2 + 34}). An earlier build of this gate demanded a bare number and therefore
# SILENTLY SKIPPED the closing disclaimer, which is the exact string a judge scored as a
# hard blocker. Accept an expression and evaluate it below.
NUMEXPR = r"[-+*/().\s\w]+?"
RECT_RE = re.compile(
    r"<rect\b[^>]*?\bx=\{(?P<x>" + NUMEXPR + r")\}[^>]*?\bwidth=\{(?P<w>" + NUMEXPR + r")\}"
    r"(?:[^>]*?\bstrokeWidth=\{(?P<sw>" + NUMEXPR + r")\})?",
    re.S,
)
FONT_RE = re.compile(r"font:\s*`\s*\d+\s+(?P<size>[\d.]+)px\s*\$\{MONO\}")
# ...AND THE OTHER WAY THE SAME THING IS WRITTEN (2026-08-08). FONT_RE above only matches
# the CSS shorthand form, `font: {`700 ${size}px ${MONO}`}`, which is how the July/August-03
# generation of episodes authored mono text. This generation uses plain SVG presentation
# attributes instead - fontFamily={MONO} fontSize={38} - and the gate matched none of them,
# so it measured ZERO strings on the film it was gating while happily measuring eleven in a
# shipped episode it had hardcoded as its default. Two spellings of one idea, and the
# checker knew one. Accept both, in either attribute order.
FONT_ATTR_RE = re.compile(
    r"fontFamily=\{MONO\}(?=(?:[^>]*?\bfontSize=\{(?P<size_a>[\d.]+)\}))"
    r"|fontSize=\{(?P<size_b>[\d.]+)\}(?=(?:[^>]*?\bfontFamily=\{MONO\}))")


def font_size_of(attrs):
    """The mono font size on this <text>, however the episode spells it, else None."""
    m = FONT_RE.search(attrs)
    if m:
        return float(m.group("size"))
    m = FONT_ATTR_RE.search(attrs)
    if m:
        s = m.group("size_a") or m.group("size_b")
        if s:
            return float(s)
    return None

# Same two-spellings problem as the font: `letterSpacing: 1.6` in the CSS form and
# `letterSpacing={1.6}` as an SVG attribute. Reading only the first silently measured
# every attribute-form string as if it had no tracking, which UNDER-estimates its width
# and is the direction that lets an overflow through.
LS_RE = re.compile(r"letterSpacing(?::\s*|=\{)(?P<ls>[\d.]+)")
X_RE = re.compile(r"\bx=\{(?P<x>" + NUMEXPR + r")\}")
ANCHOR_RE = re.compile(r'textAnchor="(?P<a>\w+)"')

# Identifiers the episode uses as plate dimensions. Resolved from the source so an
# expression like {-W / 2 + 34} is measurable rather than skipped.
CONST_RE = re.compile(r"^\s*const\s+(?P<names>[\w\s,=\d]+);\s*$", re.M)


def source_consts(src):
    """Pick up `const W = 780, H = 470;` style declarations for expression evaluation."""
    out = {}
    for m in re.finditer(r"\bconst\s+([A-Za-z_]\w*)\s*=\s*(-?[\d.]+)\s*[,;]", src):
        out.setdefault(m.group(1), float(m.group(2)))
    return out


def num(expr, consts):
    """Evaluate a literal arithmetic expression, or return None if it is not one."""
    expr = expr.strip()
    try:
        return float(eval(expr, {"__builtins__": {}}, dict(consts)))  # noqa: S307
    except Exception:
        return None


def mono_width(text, size, letter_spacing=0.0):
    n = len(text)
    if n == 0:
        return 0.0
    return n * size * MONO_ADV + letter_spacing * (n - 1)


def check_file(path, min_margin=MIN_MARGIN):
    src = open(path).read()
    consts = source_consts(src)
    failures, checked, skipped = [], 0, []

    for m in TEXT_RE.finditer(src):
        attrs, body = m.group("attrs"), m.group("body")
        line = src[:m.start()].count("\n") + 1
        size = font_size_of(attrs)
        if size is None:
            continue  # not a mono run, or a computed size
        if not body or "{" in body or "}" in body:
            skipped.append((line, (body or "")[:44], "interpolated text"))
            continue  # width is not knowable statically
        xm = X_RE.search(attrs)
        tx = num(xm.group("x"), consts) if xm else None
        if tx is None:
            skipped.append((line, body[:44], "unreadable x"))
            continue

        ls = LS_RE.search(attrs)
        ls = float(ls.group("ls")) if ls else 0.0
        anchor = ANCHOR_RE.search(attrs)
        anchor = anchor.group("a") if anchor else "start"

        w = mono_width(body, size, ls)
        if anchor == "middle":
            t0, t1 = tx - w / 2, tx + w / 2
        elif anchor == "end":
            t0, t1 = tx - w, tx
        else:
            t0, t1 = tx, tx + w

        # nearest preceding rect in the same block
        head = src[:m.start()]
        rects = list(RECT_RE.finditer(head))
        if not rects:
            skipped.append((line, body[:44], "no plate found"))
            continue
        r = rects[-1]
        # only trust a rect that is close by; anything further off is a different block
        if head[r.end():].count("\n") > 12:
            skipped.append((line, body[:44], "nearest plate too far off"))
            continue

        rx = num(r.group("x"), consts)
        rw = num(r.group("w"), consts)
        if rx is None or rw is None:
            skipped.append((line, body[:44], "unreadable plate geometry"))
            continue
        sw = num(r.group("sw") or "0", consts) or 0.0
        r0, r1 = rx + sw, rx + rw - sw

        # NOT EVERY RECT IS A PLATE. A 6px accent bar drawn beside a wordmark is the
        # nearest preceding rect to it, and pairing them reported a 150px overflow
        # against a rule that never applied. A plate that is less than half the width of
        # the string it supposedly carries is not that string's plate: the text is
        # free-standing on the frame. Say so rather than failing, because a gate that
        # cries wolf is a gate that gets ignored, which is how the real overflow shipped.
        if (r1 - r0) < w * 0.5:
            skipped.append((line, body[:44], "no plate (nearest rect is not one)"))
            continue

        checked += 1
        left, right = t0 - r0, r1 - t1
        if left < min_margin or right < min_margin:
            failures.append({
                "line": src[:m.start()].count("\n") + 1,
                "text": body,
                "size": size,
                "text_w": round(w, 1),
                "plate": [round(r0, 1), round(r1, 1)],
                "margin_l": round(left, 1),
                "margin_r": round(right, 1),
            })
    return failures, checked, skipped


# The legibility floor for auto-fitted plate type, in px at 1080x1920. Below this a string
# is technically inside its plate and unreadable on a phone, which the rubric calls out
# ("legible muted at phone size"). 22px is the smallest size that survived a thumb-sized
# read in the 2026-08-12 evidence pack.
MIN_PLATE_PX = 22.0

PLATE_CALL_RE = re.compile(r"<Plate\b(?P<attrs>[^>]*?)/>", re.S)
PLATE_TEXT_RE = re.compile(r'\btext="(?P<t>[^"]*)"')
PLATE_SIZE_RE = re.compile(r"\bsize=\{(?P<s>[\d.]+)\}")
PLATE_LS_RE = re.compile(r"\bls=\{(?P<ls>[\d.]+)\}")


def check_plate_call_sites(path, min_px=MIN_PLATE_PX):
    """Measure <Plate text="..."/> call sites, which the literal-<text> pass cannot see.

    WHY THIS EXISTS (2026-08-12). This gate reported "GATE IS DEAD, it measured nothing"
    on the episode whose plates were clipping the frame, and it was right to: Ep0812 does
    not inline its strings. It factors them through a Plate component that computes its own
    fontSize, so both of the gate's patterns miss by construction. TEXT_RE wants a literal
    body and finds the JSX expression {text}; FONT_ATTR_RE wants fontSize={38} and finds
    fontSize={fit}. Every string in the film was invisible to it.

    Factoring text through a component is better engineering, not a defect, and Plate
    already makes overflow arithmetically impossible by shrinking type until it fits. So the
    interesting question moves: not "does the string overflow" but "what did it cost to make
    it fit". Auto-fit converts an overflow into an illegibility, silently, and a 14px plate
    on a phone is as much a defect as one running off the edge.

    This mirrors Plate's own fit arithmetic (keep the two in step) and fails any call site
    whose type is driven below the legibility floor.
    """
    src = open(path).read()
    # Read the geometry out of the episode rather than hardcoding it, so a retuned zoom or
    # advance cannot leave this measuring against numbers the film stopped using.
    def const(name, default):
        m = re.search(r"^const\s+" + name + r"\s*=\s*([-\d.]+)", src, re.M)
        return float(m.group(1)) if m else default

    W = const("W", 1080.0)
    zoom = const("CONTENT_ZOOM", 1.22)
    adv = const("ADV", 0.62)
    usable = (W - 150) / (zoom * 1.10)
    pad_x = 26.0

    fails, checked = [], 0
    for m in PLATE_CALL_RE.finditer(src):
        attrs = m.group("attrs")
        tm = PLATE_TEXT_RE.search(attrs)
        if not tm:
            continue  # a computed string; zoom_clip_check reports these as not measured
        text = tm.group("t")
        sm = PLATE_SIZE_RE.search(attrs)
        size = float(sm.group("s")) if sm else 34.0
        lsm = PLATE_LS_RE.search(attrs)
        ls = float(lsm.group("ls")) if lsm else 2.0
        fit = min(size, math.floor((usable - pad_x * 2) / max(1, len(text) * adv + ls)))
        checked += 1
        if fit < min_px:
            fails.append({
                "line": src[:m.start()].count("\n") + 1,
                "text": text,
                "size": f"authored {size:.0f}px, auto-fitted to {fit:.0f}px",
                "text_w": round(len(text) * fit * adv + ls * max(0, len(text) - 1)),
                "plate": (0, round(usable)),
                "margin_l": 0,
                "margin_r": 0,
                "why": (f"Plate auto-fit drove this string to {fit:.0f}px to make it fit, below "
                        f"the {min_px:.0f}px legibility floor. It is inside its plate and "
                        f"unreadable on a phone. Shorten the string or split it across two "
                        f"plates; do not raise the floor."),
            })
    return fails, checked


def main():
    ap = argparse.ArgumentParser()
    # THE DEFAULT WAS A HARDCODED PATH TO A SHIPPED FILM (fixed 2026-08-08).
    #
    # It read Ep0803.tsx, an episode published on August 3rd. Preflight has been printing
    # "OK plated strings fit their plates: 11 measured, 0 failing" on every run since,
    # and every one of those measurements was of somebody else's movie. Pointed at the
    # episode actually being rendered it measures ZERO strings, so it has never once
    # checked the film it was gating.
    #
    # That is the FIFTH gate this run found reporting a pass while grading nothing or
    # grading the wrong file: caption_band_check resolved a July episode through a stamp
    # field nobody writes, then passed again by returning early on a missing constant;
    # plate_overlap_check parsed zero scenes; claims_contract_check counted only failures;
    # and render_parallel.sh defaulted to rendering Ep0803 as well. The shape is always the
    # same - a per-run target frozen into a default, which is correct for exactly one run
    # and silently wrong for every run after it.
    #
    # Resolved through the same helper caption_band_check uses, so there is one definition
    # of "this run's episode" and not five.
    def _this_runs_episode():
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        from caption_band_check import default_targets
        return default_targets()

    ap.add_argument("files", nargs="*", default=_this_runs_episode())
    ap.add_argument("--min-margin", type=float, default=MIN_MARGIN)
    a = ap.parse_args()

    total_checked, all_skipped, bad = 0, [], []
    for path in a.files:
        f, c, s = check_file(path, a.min_margin)
        total_checked += c
        all_skipped += [(os.path.basename(path),) + x for x in s]
        for x in f:
            x["file"] = path
        bad += f
        pf, pc = check_plate_call_sites(path)
        total_checked += pc
        for x in pf:
            x["file"] = path
        bad += pf

    # Coverage is printed, always. The whole reason this file exists is that a gate
    # reported a pass while quietly measuring none of the string that was broken.
    if all_skipped:
        print("text-fit: not measured (stated so coverage is never assumed):")
        for fn, ln, txt, why in all_skipped:
            print(f"  {fn}:{ln}  {why}: {txt!r}")

    for x in bad:
        print(f"FAIL {os.path.basename(x['file'])}:{x['line']}  {x['text']!r}")
        print(f"     {x['size']}px -> {x['text_w']}px of text in plate "
              f"[{x['plate'][0]}, {x['plate'][1]}]")
        print(f"     margin left {x['margin_l']}px, right {x['margin_r']}px "
              f"(need {a.min_margin}px)")

    print(f"text-fit: {total_checked} plated mono strings measured, "
          f"{len(all_skipped)} not measured, {len(bad)} failing")

    if total_checked == 0:
        print("text-fit: GATE IS DEAD. It measured nothing, which is not a pass.")
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
