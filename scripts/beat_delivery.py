#!/usr/bin/env python3
"""BEAT DELIVERY — did the BUILD draw the event the BOARD promised?

WHY THIS EXISTS (2026-07-31, and it exists because the first attempt at this was aimed at the
wrong stage).

That run's film lost 55% of its weighted points across four axes (Hook 0.44, Motion 0.38,
Illustration 0.37, Composition 0.29) and all three judges described one cause: beats that are
stated on cards instead of drawn. The obvious inference was that the STORYBOARD was scheduling
type where it should schedule events, so a Gate 0 checker was written to refuse such a board.

Run against the actual board, it passed every beat. The board was not the problem. Every beat
named a physical event; the BUILD did not draw them:

  - board t=43.02: "the bare ground opens as a gap where there was never a gate".
    Judge 1, on the delivered frames: "no hole, gap or ground event is drawn".
  - board t=55.04, the film's declared reveal: a slot cut on screen with daylight through it.
    Judge 2: "that image only appears at 80.64 on a different beat".

So the failure is BOARD-TO-BUILD DRIFT, and no amount of storyboard discipline catches it,
because the board was already right. It has to be measured on the rendered frames.

WHAT THIS MEASURES
------------------
For each beat, sample the render across the beat's own window and compute how much of the
picture actually CHANGES, ignoring the caption band (burned captions swap constantly and would
mask a frozen frame -- which is exactly how these beats survived seventeen review rounds) and
ignoring the global grade. A beat whose board promises an event and whose frames barely move
is a beat the film asserts rather than shows.

It is deliberately a LOW bar. It does not judge whether the motion is good, eased, or
motivated; the panel does that. It answers one question no reviewer could reliably answer by
eye at contact-sheet scale: did anything happen here at all.

  python3 scripts/beat_delivery.py
  python3 scripts/beat_delivery.py --frames out/dispatch/frames --storyboard out/dispatch/storyboard.json
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np

FPS = 30
CAPTION_TOP = 1420          # burned captions live below this; they are not beat events
MIN_CHANGED = 0.012         # fraction of non-caption pixels that must move within a beat
SAMPLE_STEP = 3             # frames between samples inside a beat window
MAX_SAMPLES = 10

# THE VIDEO PATH (added 2026-08-13, closing the known-dead gate documented in
# prompts/dispatch_routine.md "KNOWN DEAD GATE").
#
# This module's only entry point read a directory of frame_*.png that the pipeline has
# NEVER produced -- the engine renders straight to mp4 -- so ship_gate's caller returned
# silently on every run since 2026-07-31 and this check has never once looked at a frame.
# That is the same defect dead_space_check.py fixed for itself in August ("a check with a
# precondition no run satisfies is not a check"), and the remedy is the same one: sample
# the DELIVERED BYTES with ffmpeg instead of reading a directory nobody writes.
#
# Sampling at 10 fps rather than 30 is deliberate and lossless for this measurement: the
# frames-dir path compares samples SAMPLE_STEP=3 apart at 30 fps, which is 0.1s, and 10 fps
# with step 1 is the same 0.1s spacing at a third of the disk and a third of the decode.
SAMPLE_FPS = 10

# The MASTER is what gets sampled, not the square. The routine's note suggested the square
# because dead_space_check samples it, but CAPTION_TOP is authored in MASTER coordinates and
# the master is the cut the panel grades. Sampling the square would need the crop offset
# applied to the caption row, which is one more place for the 1420-vs-1336 class of error to
# live. Same reasoning as DISPATCH_STANDARD section 4: derive geometry, never restate it.
DEFAULT_CUT = "out/dispatch/dispatch_master.mp4"


def _load(path, scale=3):
    from PIL import Image
    im = Image.open(path).convert("L")
    im = im.resize((im.width // scale, im.height // scale))
    return np.asarray(im, dtype=np.int16)


def _changed_fraction(a, b, cap_row):
    """Fraction of ABOVE-CAPTION pixels that differ enough to be visible."""
    d = np.abs(a[:cap_row] - b[:cap_row])
    return float((d > 6).mean())


def episode_caption_top(default: int = CAPTION_TOP) -> int:
    """Read the CAPTION_TOP the RUN'S OWN episode declares, never this file's constant.

    The hardcoded 1420 is wrong for every recent film: 2026-08-12 uses 1336, and the 84-row
    difference means burned captions get counted as beat motion, which makes this check too
    LENIENT rather than too strict. The episode component declares it as a top-level const
    precisely so caption_band_check.py can read it, so read it here from the same place.
    """
    root = Path(__file__).resolve().parent.parent
    stamp = root / "out" / "dispatch" / ".run_stamp.json"
    comp = ""
    if stamp.exists():
        try:
            comp = (json.loads(stamp.read_text()) or {}).get("composition", "") or ""
        except Exception:
            comp = ""
    if not comp:
        return default
    src = root / "video-engine" / "src" / f"{comp}.tsx"
    if not src.exists():
        return default
    m = re.search(r"\bCAPTION_TOP\s*=\s*(\d+)", src.read_text())
    return int(m.group(1)) if m else default


def sample_cut(video: str, out_dir: str, fps: int = SAMPLE_FPS) -> str:
    """Decode the delivered cut into out_dir/frame_%05d.png at `fps`. Returns out_dir."""
    if not Path(video).exists():
        raise SystemExit(f"no delivered cut at {video} -- this gate runs AFTER the encode")
    os.makedirs(out_dir, exist_ok=True)
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", video,
           "-vf", f"fps={fps},scale=360:-2", os.path.join(out_dir, "frame_%05d.png")]
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"ffmpeg could not sample {video}: {p.stderr.strip()[:300]}")
    n = len(glob.glob(os.path.join(out_dir, "frame_*.png")))
    if n == 0:
        raise SystemExit(f"sampled ZERO frames from {video} -- a gate that measures nothing "
                         f"is a failure, not a pass")
    return out_dir


def analyze_cut(video: str, storyboard_path: str, min_changed: float = MIN_CHANGED,
                caption_top: int = None):
    """analyze(), but against the DELIVERED BYTES. This is the live path."""
    tmp = tempfile.mkdtemp(prefix="beatdel_")
    try:
        sample_cut(video, tmp)
        r = analyze(tmp, storyboard_path, min_changed,
                    caption_top=caption_top if caption_top is not None else episode_caption_top(),
                    fps=SAMPLE_FPS, step=1)
        r["sampled_from"] = video
        return r
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def analyze(frames_dir: str, storyboard_path: str,
            min_changed: float = MIN_CHANGED,
            caption_top: int = CAPTION_TOP,
            fps: int = FPS, step: int = SAMPLE_STEP):
    fs = sorted(glob.glob(str(Path(frames_dir) / "frame_*.png")))
    if not fs:
        raise SystemExit(f"no frames in {frames_dir} -- this gate runs AFTER the render")
    sb = json.loads(Path(storyboard_path).read_text())
    beats = sb.get("beats") or []
    if not beats:
        raise SystemExit("storyboard has no beats")

    probe = _load(fs[0])
    cap_row = int(caption_top / 1920 * probe.shape[0])

    bounds = []
    for i, b in enumerate(beats):
        t0 = float(b.get("t", 0))
        t1 = float(beats[i + 1]["t"]) if i + 1 < len(beats) else t0 + 3.0
        bounds.append((t0, t1))

    rows, problems = [], []
    for i, (b, (t0, t1)) in enumerate(zip(beats, bounds)):
        f0, f1 = int(t0 * fps), min(int(t1 * fps), len(fs) - 1)
        idxs = list(range(f0, max(f0 + 1, f1), step))[:MAX_SAMPLES]
        if len(idxs) < 2:
            idxs = [f0, min(f0 + 2, len(fs) - 1)]
        imgs = [_load(fs[k]) for k in idxs if 0 <= k < len(fs)]
        if len(imgs) < 2:
            continue
        peak = max(_changed_fraction(imgs[j], imgs[j + 1], cap_row)
                   for j in range(len(imgs) - 1))
        # also compare the beat's first and last sample, so a slow continuous move that is
        # small frame-to-frame still registers as an event
        span = _changed_fraction(imgs[0], imgs[-1], cap_row)
        score = max(peak, span)
        ok = score >= min_changed
        rows.append({"i": i, "t": t0, "title": b.get("title", ""),
                     "changed": round(score, 4), "ok": ok,
                     "promised": ((b.get("draw") or {}).get("action") or "")[:90]})
        if not ok:
            problems.append(
                f"beat {i} at t={t0} \"{b.get('title','')}\" is DELIVERED STATIC: only "
                f"{score*100:.2f}% of the picture above the caption band changes across its "
                f"whole window (floor {min_changed*100:.1f}%). The board promised: "
                f"\"{rows[-1]['promised']}\". Build the event or re-board the beat.")

    delivered = sum(1 for r in rows if r["ok"])
    share = delivered / max(1, len(rows))
    if rows and share < 0.90:
        problems.append(
            f"only {share*100:.0f}% of beats are delivered with visible change (floor 90%). "
            f"This is the 2026-07-31 failure: a correct board, a build that drew type where "
            f"the board wrote events, and a panel that scored the picture.")
    return {"beats": len(rows), "delivered": delivered, "share": share,
            "rows": rows, "problems": problems}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="out/dispatch/frames")
    ap.add_argument("--video", default=None,
                    help=f"sample the DELIVERED cut instead of a frames dir "
                         f"(default cut: {DEFAULT_CUT}). This is the live path; --frames "
                         f"reads a directory the pipeline does not produce.")
    ap.add_argument("--storyboard", default="out/dispatch/storyboard.json")
    ap.add_argument("--min-changed", type=float, default=MIN_CHANGED)
    ap.add_argument("--caption-top", type=int, default=None,
                    help="override the episode's own CAPTION_TOP (read from the run's "
                         "composition source by default)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if a.video is not None or not glob.glob(str(Path(a.frames) / "frame_*.png")):
        cut = a.video or DEFAULT_CUT
        r = analyze_cut(cut, a.storyboard, a.min_changed, a.caption_top)
        print(f"sampled {r['sampled_from']} at {SAMPLE_FPS} fps, "
              f"caption band from y={a.caption_top or episode_caption_top()}")
    else:
        r = analyze(a.frames, a.storyboard, a.min_changed,
                    caption_top=a.caption_top if a.caption_top is not None
                    else episode_caption_top())
    if a.json:
        print(json.dumps(r, indent=2))
        sys.exit(1 if r["problems"] else 0)
    print(f"beats: {r['beats']}   delivered with visible change: {r['delivered']} "
          f"({r['share']*100:.0f}%)")
    for row in r["rows"]:
        mark = "  ok " if row["ok"] else "  NO "
        print(f"{mark} t={row['t']:<7} {row['changed']*100:6.2f}%  {row['title'][:46]}")
    if r["problems"]:
        print()
        for p in r["problems"]:
            print(f"FAIL [beat_delivery] {p}")
        sys.exit(1)
    print("PASS [beat_delivery] every beat draws the event its board promised")
    sys.exit(0)


if __name__ == "__main__":
    main()
