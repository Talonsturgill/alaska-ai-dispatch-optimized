#!/usr/bin/env python3
"""Refuse two text plates that occupy the same pixels.

WHY THIS EXISTS (2026-08-06, after it cost score in three separate panel rounds).

Three times in one run, a card was added to a band that already held one, and every time
the result was worse than the gap being closed:

  1. S8. Adding c19 stacked it onto the Sanders quote, clipping it to '"BASICALLY /
     YOUTUBERS F' and leaving a CHIEF RON DUPEE credit inside a quotation belonging to
     Chief of Staff Mike Sanders. Two judges hard-failed it: the film's most inflammatory
     line read as credited to a different named living police chief.
  2. S9. The c20 attribution I added to fix (1) rendered UNDERNEATH the concession card,
     completely occluded. A judge then reported c20 as the only quote in the film with no
     speaker — true on screen, false in the source.
  3. S7 earlier the same day: the spool's FULL tag landed on the word YOUTUBERS.

Every one was invisible to typecheck, to text_fit_check, and to caption_band_check, because
each element is individually fine. The defect is only in the RELATIONSHIP, and nothing was
looking at relationships.

WHAT IT DOES. Parses each scene component, reconstructs the box of every <Plate> from its
own layout arithmetic (the same monoW/height maths the component uses), and reports any two
boxes that intersect. Deliberate overlaps declare themselves with `plate-overlap-ok` on one
of the two lines.

WHAT IT DOES NOT DO, stated plainly. It is GEOMETRIC and opacity-blind: two plates that
overlap in space but never share a frame in time — because one retires before the other
lands — will be reported. That is the right failure direction. A false positive costs one
comment; a false negative costs a misattributed quotation on a named public official.
"""
import argparse
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OK = "plate-overlap-ok"
NUM = r"\{(-?\d+(?:\.\d+)?)\}"

CAPTION_TOP = 1310
CAP_GUARD = CAPTION_TOP - 34


def mono_w(s, size, track=0.5):
    return len(s) * size * 0.602 + track * max(0, len(s) - 1)


def scenes(src):
    starts = [(m.group(1), m.start()) for m in
              re.finditer(r"^const (S\d+): React\.FC<SceneProps>", src, re.M)]
    for i, (name, a) in enumerate(starts):
        b = starts[i + 1][1] if i + 1 < len(starts) else len(src)
        yield name, a, src[a:b]


def plates(body, base_line):
    """Every <Plate> in a scene, as (line, box, label)."""
    out = []
    for m in re.finditer(r"<Plate\b", body):
        blk = body[m.start():m.start() + 420]
        end = blk.find("/>")
        if end == -1:
            continue
        blk = blk[:end]
        xm, ym = re.search(r"\bx=" + NUM, blk), re.search(r"\by=" + NUM, blk)
        if not (xm and ym):
            continue
        x, y = float(xm.group(1)), float(ym.group(1))
        sm = re.search(r"\bsize=" + NUM, blk)
        size = float(sm.group(1)) if sm else 26.0
        rows = re.findall(r"'([^']*)'|`([^`]*)`|\"([^\"]*)\"", blk)
        texts = [a or b or c for a, b, c in rows if (a or b or c)]
        texts = [t for t in texts if not t.startswith("#")] or [""]
        n = len(texts) if "lines=" in blk else 1
        wide = max((mono_w(t, size) for t in texts), default=0) + 34
        h = size + 24 + (n - 1) * (size + 10)
        yy = min(y, CAP_GUARD - h / 2)
        line = base_line + body[:m.start()].count("\n")
        out.append((line, (x - wide / 2, yy - h / 2, x + wide / 2, yy + h / 2), texts[0][:34]))
    return out


def intersect(a, b, pad=2.0):
    return not (a[2] <= b[0] + pad or b[2] <= a[0] + pad
                or a[3] <= b[1] + pad or b[3] <= a[1] + pad)


def check(path):
    src = open(path).read()
    lines = src.split("\n")
    found = []
    for name, off, body in scenes(src):
        base = src[:off].count("\n")
        ps = plates(body, base)
        for i in range(len(ps)):
            for j in range(i + 1, len(ps)):
                (li, bi, ti), (lj, bj, tj) = ps[i], ps[j]
                if not intersect(bi, bj):
                    continue
                if OK in lines[li] or OK in lines[lj]:
                    continue
                ox = min(bi[2], bj[2]) - max(bi[0], bj[0])
                oy = min(bi[3], bj[3]) - max(bi[1], bj[1])
                found.append((path, li + 1, lj + 1, name, ti, tj, ox, oy))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*")
    a = ap.parse_args()
    targets = a.targets
    if not targets:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        from caption_band_check import default_targets
        targets = default_targets()

    # A CHECKER THAT PARSED NOTHING MUST NOT REPORT CLEAN (2026-08-08).
    #
    # `scenes()` matches `^const (S\d+): React.FC<SceneProps>`. Ep0808 declared its scenes
    # as bare `React.FC`, so the pattern matched zero scenes, `check()` returned no
    # findings, and this printed "clean across 1 file(s)" every time it ran for an entire
    # run — while a plate sat over a cycling hatch and two more overlapped at 22.8s.
    #
    # That is the FOURTH time this run that a gate has announced clean while grading
    # nothing: caption_band_check resolved a shipped July episode through a stamp field
    # nobody writes, then passed again by returning early on a missing constant, and
    # claims_contract_check printed "0 obligation(s) met" in the same breath as "none
    # outstanding". Every one was found by a human noticing a number looked wrong. That is
    # not a control, it is luck.
    #
    # So: emptiness is now a finding in its own right. If a file contains plates but the
    # parser yielded no scenes to put them in, the gate FAILS and says why, rather than
    # congratulating the run on a file it could not read. The fix for a real refactor is
    # one line here; the cost of the silent version is a whole run's worth of false green.
    found, blind = [], []
    for t in targets:
        src = open(t).read()
        if "<Plate" in src and not list(scenes(src)):
            blind.append(t)
        found += check(t)

    if blind:
        for t in blind:
            print(f"FAIL {os.path.relpath(t, REPO)}: contains <Plate> elements but the scene "
                  f"parser matched ZERO scenes, so nothing in this file was checked.")
        print("\nplate_overlap_check: parsed no scenes, so 'clean' would be a lie.")
        print("scenes() expects `const S<n>: React.FC<SceneProps>`. If the episode renamed")
        print("or retyped its scene components, update the pattern — do not ignore this.")
        return 1

    if not found:
        print(f"plate_overlap_check: clean across {len(targets)} file(s), "
              f"{sum(len(list(scenes(open(t).read()))) for t in targets)} scene(s) parsed")
        return 0
    for path, li, lj, scene, ti, tj, ox, oy in found:
        rel = os.path.relpath(path, REPO)
        print(f"{rel}:{li} and :{lj}  {scene}  OVERLAP {ox:.0f}x{oy:.0f}px")
        print(f"    '{ti}'  vs  '{tj}'")
    print(f"\nplate_overlap_check: {len(found)} overlapping pair(s).")
    print("Two plates in the same pixels means one of them is unreadable, and the one")
    print("underneath is usually an attribution. Separate them, sequence them so one")
    print("retires before the other lands, or mark a line `plate-overlap-ok` if the")
    print("overlap is deliberate and they never share a frame.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
