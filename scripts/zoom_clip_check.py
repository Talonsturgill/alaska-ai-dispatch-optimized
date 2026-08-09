#!/usr/bin/env python3
"""Refuse anything the scene's own composed camera scale pushes off the side of the frame.

WHY THIS EXISTS (2026-08-09, found by looking at the contact sheet, not by any gate).
------------------------------------------------------------------------------------
`text_fit_check.py` asks whether a string fits the plate drawn behind it. That is the right
question and it is not this one. A plate can fit its own box perfectly and still leave the
frame, because every scene in this engine composes a camera scale about x=540:

    x_rendered = 540 + (x_authored - 540) * SCALE

At SCALE 1.24 an element authored at x=760 with a 555px box renders from 469 to 1157, so 93
pixels of it are outside a 1080-wide frame. On the 2026-08-09 first cut that clipped five
elements, and the worst of them was the film's central quotation: NSF's own sentence lost a
word off each end and read on screen as "FORCEMENT-LEARNING CONTROLLERS ... GRATED WITH MICR".

Nothing caught it. text_fit_check passed, because each string fit its plate. caption_band_check
passed, because it models the VERTICAL crop and this is a horizontal one. plate_overlap_check
passed, because the boxes did not intersect each other. The defect only exists in the
relationship between an authored x and a scale declared somewhere else in the file, which is
exactly the "derive geometry, never hand-tune it" class from DISPATCH_STANDARD section 4.

WHAT THE FIRST VERSION OF THIS FILE STILL COULD NOT SEE (found the same day, by a judge, in the
SECOND cut, which is the part worth writing down).
------------------------------------------------------------------------------------------------
The first version modelled SCALE as `max(CONTENT_ZOOM, zoom={...})` over the whole file and only
measured `<Plate>` and `<BrassPlate>`. Both halves of that were wrong, and each one shipped a
clipped element into a graded cut:

  1. Stage composes TWO factors, not one:  scale = (1 + push) * zoom.  `push` is the dolly, it
     ramps across the shot, and it is a real multiplier. Shot 6 declares zoom 1.02 and looks
     safe; its push reaches 0.10, so its true worst case is 1.122. The three money cards were
     authored 300 wide at x=196 and x=884 and lost 7px off ALASKA's left and WYOMING's right.
  2. A file-wide MAXIMUM is the wrong statistic even when it is conservative, because it is
     conservative in the wrong direction for every OTHER scene: it would fail plates that are
     fine and, worse, it invites the next person to loosen it. Scale is a per-scene fact, so it
     is now computed per scene.
  3. Most of what leaves the frame is not a Plate. `PUMPS / TIMING / POWER` is a bare <text>
     inside a translated <g>, and at shot 9's true scale of 1.144 its left edge rendered at
     x=3. So this checker now walks the translate stack and measures plain mono <text> too.

WHAT IT STILL CANNOT SEE, stated so a pass is never mistaken for coverage: any element whose
position comes from a template literal, a variable, or a prop (the checker prints these as
"not measured" rather than assuming them safe), and any non-text geometry, which means a wide
<rect> or <path> can still bleed off the edge. Several do so deliberately, which is why raw
shapes are not graded here.

    python3 scripts/zoom_clip_check.py            # exit 1 on any clipped element
"""
import glob
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRAME_W = 1080
# 54px is 5% of the frame, the safe area every social platform assumes. 16 was the old value and
# it is arithmetically correct and practically wrong: the shot-6 bin row cleared it at 21px and
# three separate judge readings across two rounds called that row clipped or bleeding. A margin
# that passes geometry a viewer reads as cut is not measuring the thing that matters.
MARGIN = 54
CAPTION_TOP = 1336   # must match the episode's own constant
CAP_MARGIN = 26      # a plate that touches the caption box reads as occluded
DEFAULT_SIZE = {"Plate": 40, "BrassPlate": 34}
LS = 1.6
NUM = r"-?\d+(?:\.\d+)?"


def mono_w(s: str, size: float, track: float = LS) -> float:
    """Mono advance is exact, so a string's width is arithmetic and never judgement."""
    return len(s) * size * 0.602 + track * max(0, len(s) - 1)


def episode_files():
    """The current run's episode, which is the newest Ep*.tsx. Past episodes are history and
    grading them would fail the run on a film that shipped weeks ago."""
    files = glob.glob(os.path.join(REPO, "video-engine", "src", "Ep*.tsx"))
    return [max(files, key=os.path.getmtime)] if files else []


def content_zoom(src: str) -> float:
    m = re.search(r"\bCONTENT_ZOOM\s*=\s*([\d.]+)", src)
    return float(m.group(1)) if m else 1.0


def scenes(src: str, default_zoom: float):
    """Split the episode into its scene components and give each one its own camera scale.

    A scene is `const S<name>: React.FC<SceneProps> = (p) => {` up to the next such declaration.
    Anything before the first one is shared machinery (Plate, Stage, the vessels) whose geometry
    is relative to a caller, so it is deliberately not graded here.
    """
    starts = [(m.start(), m.group(1)) for m in
              re.finditer(r"^const (S[0-9A-Za-z]*)\s*:\s*React\.FC<SceneProps>\s*=\s*\(", src, re.M)]
    out = []
    for i, (pos, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(src)
        blk = src[pos:end]
        line0 = src[:pos].count("\n") + 1

        # zoom: the <Stage> tag's own literal, else the file default
        zm = re.search(r"<Stage\b[^>]*?\bzoom=\{([\d.]+)\}", blk, re.S)
        zoom = float(zm.group(1)) if zm else default_zoom
        cm = re.search(r"<Stage\b[^>]*?\bcamY=\{(" + NUM + r")\}", blk, re.S)
        camY = float(cm.group(1)) if cm else 0.0

        # push: whichever the <Stage> is actually handed. A literal is the whole story; a
        # variable means finding its interpolate and taking the largest value it can reach.
        push = 0.0
        pm = re.search(r"<Stage\b[^>]*?\bpush=\{([\d.]+)\}", blk, re.S)
        if pm:
            push = float(pm.group(1))
        else:
            im = re.search(r"const push\s*=\s*interpolate\([^,]+,\s*\[[^\]]*\]\s*,\s*\[([^\]]*)\]", blk)
            if im:
                vals = [float(v) for v in re.findall(NUM, im.group(1))]
                push = max(vals) if vals else 0.0
        out.append((name, line0, blk, zoom * (1.0 + push), zoom, push, camY))
    return out


def project_y(y, zoom, push, camY):
    """Where an AUTHORED y actually lands on the delivered frame.

    Stage composes two nested transforms and the vertical one has an offset the horizontal
    one does not:

        inner:  translate(540, 960 + camY*0.2) scale(zoom)  translate(-540, -960)
        outer:  translate(540, 960 + camY)     scale(1+push) translate(-540, -960)

    So y_rendered = 960 + camY + ((971' + (y - 971')*zoom) - 960) * (1 + push), where 971' is
    960 + camY*0.2. Ignoring camY and push is what let a card clamped to authored 1302 render
    at 1401, which is 65px INSIDE the burned-in caption band.
    """
    pivot = 960.0 + camY * 0.2
    y_inner = pivot + (y - pivot) * zoom
    return 960.0 + camY + (y_inner - 960.0) * (1.0 + push)


def translate_stack(blk: str):
    """Walk the block once and record, for every character offset, the accumulated x offset of
    the enclosing <g transform="translate(...)"> groups.

    A group whose transform is a template literal or an expression is UNKNOWABLE from source, so
    it pushes a sentinel and everything inside it is reported as not measured. That is the honest
    outcome: this checker would rather say it did not look than claim a string is safe.
    """
    events = []   # (offset, delta_or_None, +1 open / -1 close)
    for m in re.finditer(r"<g\b([^>]*)>|</g>", blk):
        if m.group(0) == "</g>":
            events.append((m.end(), None, -1))
            continue
        attrs = m.group(1)
        if attrs.rstrip().endswith("/"):
            continue                      # self-closing <g/>, opens no scope
        t = re.search(r'transform="translate\((' + NUM + r')\s*,\s*' + NUM + r'\)"\s*$', attrs.strip())
        if t:
            events.append((m.end(), float(t.group(1)), +1))
        elif "transform" in attrs:
            events.append((m.end(), None, +1))     # unknowable
        else:
            events.append((m.end(), 0.0, +1))
    events.sort()

    def offset_at(pos: int):
        stack, total, unknown = [], 0.0, False
        for off, delta, kind in events:
            if off > pos:
                break
            if kind > 0:
                stack.append(delta)
            elif stack:
                stack.pop()
        for d in stack:
            if d is None:
                unknown = True
            else:
                total += d
        return (None if unknown else total)

    return offset_at


def check(path: str):
    src = open(path).read()
    dz = content_zoom(src)
    bad, unmeasured, n = [], [], 0
    cap_bad = []
    per_scene = []

    for name, line0, blk, scale, zoom, push, camY in scenes(src, dz):
        lo_safe = 540 - (540 - MARGIN) / scale
        hi_safe = 540 + (FRAME_W - MARGIN - 540) / scale
        per_scene.append((name, scale, zoom, push, lo_safe, hi_safe))
        offset_at = translate_stack(blk)

        def record(pos, kind, text, x, w):
            nonlocal n
            n += 1
            rl = 540 + (x - w / 2 - 540) * scale
            rr = 540 + (x + w / 2 - 540) * scale
            if rl < MARGIN or rr > FRAME_W - MARGIN:
                line = line0 + blk[:pos].count("\n")
                bad.append((name, line, kind, text[:34], round(w), round(rl), round(rr),
                            x, lo_safe, hi_safe))

        def skip(pos, kind, why):
            unmeasured.append((name, line0 + blk[:pos].count("\n"), kind, why))

        def record_caption(pos, kind, text, y, h):
            """A plate's own CAP_GUARD clamp is applied in AUTHORED space, and the Stage then
            moves it. In shot 5 a card clamped to authored 1302 renders at 1401, which is 65px
            inside the burned-in caption band, so an open caption sat on top of the film's
            PubMed attribution for the 1.8s its cue was live."""
            bot = project_y(y + h / 2, zoom, push, camY)
            if bot > CAPTION_TOP - CAP_MARGIN:
                line = line0 + blk[:pos].count("\n")
                cap_bad.append((name, line, kind, text[:34], round(y), round(bot)))

        # ---- plated strings -------------------------------------------------------------
        for m in re.finditer(r"<(Plate|BrassPlate)\b(.*?)/>", blk, re.S):
            kind, a = m.group(1), m.group(2)
            xm = re.search(r"\bx=\{(" + NUM + r")\}", a)
            tm = re.search(r'text="([^"]*)"', a)
            if not tm:
                skip(m.start(), kind, "text is not a plain literal")
                continue
            if not xm:
                skip(m.start(), kind, f"x is not a plain number: {tm.group(1)[:28]}")
                continue
            off = offset_at(m.start())
            if off is None:
                skip(m.start(), kind, f"inside a computed transform: {tm.group(1)[:28]}")
                continue
            sm = re.search(r"\bsize=\{(\d+(?:\.\d+)?)\}", a)
            size = float(sm.group(1)) if sm else DEFAULT_SIZE[kind]
            w = mono_w(tm.group(1), size) + 56
            sub = re.search(r'sub="([^"]*)"', a)
            if sub:
                w = max(w, mono_w(sub.group(1), size * 0.54, 1.2) + 56)
            record(m.start(), kind, tm.group(1), float(xm.group(1)) + off, w)
            ym = re.search(r"\by=\{(" + NUM + r")\}", a)
            if ym:
                rows = max(1, (len(tm.group(1)) // 34) + 1)
                h = size * 1.16 * rows + (size * 0.54 * 1.5 if sub else 0) + 30
                y_auth = min(float(ym.group(1)), (CAPTION_TOP - 34) - h / 2)
                record_caption(m.start(), kind, tm.group(1), y_auth, h)

        # ---- bare centred mono strings --------------------------------------------------
        # This is the class the first version of this checker was blind to, and it is the class
        # the film actually uses most: a <text> in a translated group, positioned by the group.
        for m in re.finditer(r"<text\b([^>]*)>([^<{]*)</text>", blk, re.S):
            a, body = m.group(1), m.group(2).strip()
            if not body:
                continue
            if 'textAnchor="middle"' not in a:
                continue          # a left-anchored string's box is not centred on its x
            xm = re.search(r"\bx=\{(" + NUM + r")\}", a)
            fm = re.search(r"\bfontSize=\{(\d+(?:\.\d+)?)\}", a)
            if not xm or not fm:
                skip(m.start(), "text", f"x or fontSize is computed: {body[:28]}")
                continue
            off = offset_at(m.start())
            if off is None:
                skip(m.start(), "text", f"inside a computed transform: {body[:28]}")
                continue
            lsm = re.search(r"\bletterSpacing=\{(" + NUM + r")\}", a)
            track = float(lsm.group(1)) if lsm else 0.0
            record(m.start(), "text", body, float(xm.group(1)) + off,
                   mono_w(body, float(fm.group(1)), track))

        # ---- drawn objects ---------------------------------------------------------------
        # A <rect> POSITIONED BY AN ENCLOSING TRANSLATE is an object in the world (a card, a
        # panel, a slot) and being cut by the frame edge is always a defect. A <rect> authored
        # straight into scene coordinates is set dressing (a rail, a wall, a floor) and several
        # of those bleed off both edges on purpose, so they are left alone. That distinction is
        # not a convenience, it is how this file is written, and it is the line between the
        # money cards that had to move and the rail behind them that did not.
        for m in re.finditer(r"<rect\b([^>]*?)/>", blk, re.S):
            a = m.group(1)
            xm = re.search(r"\bx=\{(" + NUM + r")\}", a)
            wm = re.search(r"\bwidth=\{(" + NUM + r")\}", a)
            if not xm or not wm:
                continue          # computed geometry, and there is a great deal of it
            off = offset_at(m.start())
            if off in (None, 0.0):
                continue          # unknowable, or scene-coordinate set dressing
            x, w = float(xm.group(1)), float(wm.group(1))
            record(m.start(), "rect", f"{w:.0f}px box", x + w / 2 + off, w)

    return bad, unmeasured, n, per_scene, cap_bad


def main() -> int:
    targets = sys.argv[1:] or episode_files()
    if not targets:
        print("zoom_clip_check: no episode file found, which is itself wrong")
        return 1
    total_bad, total_n = 0, 0
    for path in targets:
        bad, unmeasured, n, per_scene, cap_bad = check(path)
        rel = os.path.relpath(path, REPO)
        total_n += n
        print(f"zoom_clip_check: {rel}")
        for name, scale, zoom, push, lo, hi in per_scene:
            print(f"  {name:<4} scale {scale:.3f}  (zoom {zoom} x push {1 + push:.2f})   "
                  f"safe authored span {lo:.0f}..{hi:.0f}")
        for name, line, kind, text, w, rl, rr, x, lo, hi in bad:
            total_bad += 1
            need_lo, need_hi = lo + w / 2, hi - w / 2      # the fix, as arithmetic not advice
            print(f"  FAIL {rel}:{line}  [{name}] {kind} '{text}'")
            print(f"       box {w}px at x={x:.0f} renders {rl}..{rr}, outside 0..{FRAME_W}")
            if need_lo > need_hi:
                print("       NO x can fit this string at this size. Shorten it or reduce the size.")
            else:
                print(f"       move x into {need_lo:.0f}..{need_hi:.0f}, or reduce the size")
        for nm, line, kind, text, y, bot in cap_bad:
            total_bad += 1
            print(f"  FAIL {rel}:{line}  [{nm}] {kind} '{text}'")
            print(f"       authored y={y} renders its bottom at {bot}, inside the caption band "
                  f"(top {CAPTION_TOP}). An open caption will sit on this string.")
        if unmeasured:
            print("  not measured (stated so coverage is never assumed):")
            for name, line, kind, why in unmeasured:
                print(f"    {rel}:{line}  [{name}] {kind}: {why}")
    if total_n == 0:
        print("zoom_clip_check: measured NOTHING, which is a failure and not a pass")
        return 1
    if total_bad:
        print(f"\nzoom_clip_check: {total_bad} element(s) leave the frame under the scene's camera scale.")
        print("An element can fit its own box perfectly and still be cut in half by the frame edge.")
        return 1
    print(f"zoom_clip_check: clean, {total_n} string(s) measured against the frame edge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
