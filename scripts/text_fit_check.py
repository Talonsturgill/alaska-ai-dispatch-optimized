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
LS_RE = re.compile(r"letterSpacing:\s*(?P<ls>[\d.]+)")
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
        font = FONT_RE.search(attrs)
        if not font:
            continue  # not a mono run, or a computed size
        if not body or "{" in body or "}" in body:
            skipped.append((line, (body or "")[:44], "interpolated text"))
            continue  # width is not knowable statically
        xm = X_RE.search(attrs)
        tx = num(xm.group("x"), consts) if xm else None
        if tx is None:
            skipped.append((line, body[:44], "unreadable x"))
            continue

        size = float(font.group("size"))
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*",
                    default=[os.path.join(REPO, "video-engine", "src", "Ep0803.tsx")])
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
