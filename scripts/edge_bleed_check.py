#!/usr/bin/env python3
"""Find drawn content that the LEFT or RIGHT frame edge cuts, by looking at the render.

WHY THIS EXISTS (2026-08-13, found by three judges and by no gate).
-------------------------------------------------------------------
This run shipped a cut in which a filing cabinet's label read "ACCURATE GENERATOR MODE",
its index card read "usually unavaila", and the annotation beside it read "WIRED TOO C" for
about six seconds. All three were the same defect: an element authored at an x that looks
safe in source, pushed past x=1080 by the scene's composed camera scale.

`zoom_clip_check.py` was written for exactly this and it passed, correctly. It is a STATIC
reader: it walks the translate stack in the episode file and computes
`x_rendered = 540 + (x_authored - 540) * (1 + push) * zoom`. The drawer's label is not in
the episode file. It lives inside a library component, and its position is
`translate(open * 210)` where `open` is an animation value that exists only at runtime. No
static reader can resolve that, and pretending otherwise would just move the blind spot.

So this checker does not read code at all. It reads PIXELS, out of the encoded master, and
asks one question per sampled frame: is there structured content -- type, plate edges,
object outlines -- inside the outer safe margin? Background gradient and the corrugated
wall are flat there and score near zero. A label running off the edge is not.

WHAT IT DELIBERATELY DOES NOT DO
--------------------------------
It does not fail the run. Some elements are cut by the frame edge ON PURPOSE in this engine
(the breaker panel and the door shaft are staged half-out to open the room up), so a hard
fail would be wrong and would teach the next run to loosen the threshold until it means
nothing. It exits 2 for attention and never 1, the same contract as the gas watch page
check in the sibling repo: it hands the run a short LOOK HERE list with timestamps and a
side, which is precisely what was missing when this defect shipped.

The caption band is excluded by row. It is INK at 72 percent across the full width by
design, so it touches both margins in every frame and would otherwise be the only thing
this ever reported.

VALIDATED AGAINST THE DEFECT IT WAS WRITTEN FOR. Run against the master that shipped the
bug, it reports "right edge 62.0-65.0s", which is the drawer window all three judges cited,
and it does not report the many seconds where the breaker panel is merely staged half out.

  python3 scripts/edge_bleed_check.py [--video out/dispatch/dispatch_master.mp4]
                                      [--every 0.5] [--margin 54] [--json]
"""
import argparse, json, os, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))

CAPTION_TOP, CAPTION_H = 1336, 132     # matches Ep0813.tsx; excluded by row, see above
EDGE_DELTA = 28                        # a pixel differing this much from 3px away is an edge
MIN_STEMS = 3                          # transitions across the margin that say "glyphs"
MIN_ROWS = 11                          # ...held over this many rows, i.e. a line of type
MAX_ROWS = 64                          # ...but no taller than one: a 300-row block is an OBJECT


def _duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True).stdout
    return float(out.strip())


def _cut_type_rows(img, x0, x1):
    """Rows in the column band [x0,x1) that look like a line of TYPE running off the edge.

    A first version of this measured "how much structure is in the margin" and reported 30 of
    31 sampled seconds, on both sides, because this engine deliberately stages a breaker panel
    and a door light shaft half out of frame. A checker that fires on every frame is not a
    checker. What actually hurt the film was never a cut OBJECT, it was cut TYPE, and type has
    a signature an outline does not: many short vertical stems packed across a narrow band.

    So this counts horizontal edge TRANSITIONS per row. A cabinet edge or a light shaft gives
    one or two per row. A run of glyphs gives several, and holds them over the rows of a cap
    height. Both conditions have to be true before anything is reported."""
    import numpy as np
    a = np.asarray(img.convert("L"), dtype=np.int16)
    band = a[:, max(0, x0):min(a.shape[1], x1)]
    if band.shape[1] < 8:
        return []
    d = np.abs(band[:, 2:] - band[:, :-2]) > EDGE_DELTA
    stems = (d[:, 1:] & ~d[:, :-1]).sum(axis=1)          # rising edges only, so a stem counts once
    rows = np.where(stems >= MIN_STEMS)[0]
    rows = rows[(rows < CAPTION_TOP) | (rows >= CAPTION_TOP + CAPTION_H)]
    return rows.tolist()


def _has_cut_type(img, x0, x1):
    """True when the qualifying rows form a contiguous block as tall as a line of type."""
    rows = _cut_type_rows(img, x0, x1)
    if len(rows) < MIN_ROWS:
        return 0.0
    run = best = 1
    for prev, cur in zip(rows, rows[1:]):
        run = run + 1 if cur - prev <= 2 else 1
        best = max(best, run)
    # An upper bound matters as much as the lower one. Without it this reported 290-row
    # blocks, which is a textured wall or a cabinet standing in the margin, not a caption.
    # A line of type in this engine is roughly 20 to 50 rows tall.
    return float(best) if MIN_ROWS <= best <= MAX_ROWS else 0.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(REPO, "out", "dispatch", "dispatch_master.mp4"))
    ap.add_argument("--every", type=float, default=0.5)
    ap.add_argument("--margin", type=int, default=54)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.video):
        print(f"edge_bleed_check: no video at {a.video}", file=sys.stderr)
        return 2
    from PIL import Image

    dur = _duration(a.video)
    times = [round(t * a.every, 2) for t in range(int(dur / a.every))]
    hits = []
    with tempfile.TemporaryDirectory() as td:
        for t in times:
            p = os.path.join(td, "f.png")
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", a.video,
                            "-frames:v", "1", p], check=False)
            if not os.path.exists(p):
                continue
            im = Image.open(p)
            W = im.size[0]
            left = _has_cut_type(im, 0, a.margin)
            right = _has_cut_type(im, W - a.margin, W)
            for side, v in (("left", left), ("right", right)):
                if v:
                    hits.append({"t": t, "side": side, "rows": int(v)})

    # collapse runs on the same side into one entry, so six seconds of one clipped label is
    # one line to go look at and not twelve
    runs = []
    for h in hits:
        if runs and runs[-1]["side"] == h["side"] and h["t"] - runs[-1]["t_end"] <= a.every * 2.5:
            runs[-1]["t_end"] = h["t"]
            runs[-1]["peak"] = max(runs[-1]["peak"], h["rows"])
        else:
            runs.append({"side": h["side"], "t_start": h["t"], "t_end": h["t"], "peak": h["rows"]})

    report = {"video": os.path.relpath(a.video, REPO), "sampled": len(times),
              "margin_px": a.margin, "min_stems": MIN_STEMS, "min_rows": MIN_ROWS, "runs": runs}
    if a.json:
        print(json.dumps(report, indent=1))
    else:
        if not runs:
            print(f"edge_bleed_check: clean. {len(times)} frames, no cut type inside the "
                  f"outer {a.margin}px on either side.")
        else:
            print(f"edge_bleed_check: ATTENTION. {len(runs)} window(s) with type running into "
                  f"the outer {a.margin}px:")
            for r in runs:
                span = f"{r['t_start']:.1f}s" if r["t_start"] == r["t_end"] else \
                       f"{r['t_start']:.1f}-{r['t_end']:.1f}s"
                print(f"  {r['side']:>5} edge  {span:>16}  {r['peak']:.0f} rows")
            print("  REMEDY: open each window as a frame and read it. If a string or a prop is "
                  "cut, move the element inboard; remember the authored x is scaled about "
                  "x=540 by (1+push)*zoom, so the safe authored band is narrower than 0..1080.")
            print("  Some elements here are staged half-out on purpose (breaker panel, door "
                  "shaft). This never fails a run; it only tells you where to look.")
    return 2 if runs else 0


if __name__ == "__main__":
    sys.exit(main())
