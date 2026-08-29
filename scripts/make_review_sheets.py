#!/usr/bin/env python3
"""Build a NON-TERMINAL EARLY-LOOK pack for visual iteration.

This output is never the Gate-B panel pack and never authorizes a verdict. Terminal
judging requires scripts/build_evidence.py plus its validated evidence manifest.

Two kinds of evidence, because two kinds of judgment:
  1. CONTACT SHEETS (sheet_0..5.png): 36 stills sampling the whole timeline ~every 1.7s.
     Right for composition, typography, color, accuracy, legibility.
  2. MOTION FILMSTRIPS (strip_*.png): 8 CONSECUTIVE frames (default step 2 = 1/15s apart)
     at the key moves. Right for judging MOTION: easing, anticipation/overshoot/settle,
     motion blur, secondary follow-through. A panel judging animation from lone stills is
     structurally blind — it caps the Motion axis on "cannot verify" instead of evidence
     (which is exactly what happened on 2026-07-10; this script is the fix).

Strip positions come from --strips "name:frame[:step],..." or default to thirds of the
timeline. The orchestrator should pick the storyboard's biggest MOVES (a slam, a swim,
a settle, a transition) and pass them explicitly.

  python scripts/make_review_sheets.py --frames out/dispatch/frames_v3 \
      --out out/dispatch/review --strips "hook_slam:14,swim:300,settle:1420"

EARLY-LOOK MODE: the script works on a PARTIAL frame dir (a render in progress) — sheets sample
whatever exists and strip positions clamp into the available range. Run it ~120 frames into every
full render and give the pack to one critic pass: a defect caught at frame 120 costs 2 minutes,
the same defect at frame 1800 costs 3 hours. Look-dev should ALSO probe motion before any full
render: 8 CONSECUTIVE frames at the storyboard's riskiest move (fast subject, domain repetition,
rack) at scale=0.4 — still-probes cannot show ribboning/shear/jitter, strips can.
"""
import argparse, glob, os
from PIL import Image

def main():
    print("EARLY LOOK ONLY: not terminal panel evidence; run scripts/build_evidence.py before judges")
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="out/dispatch/frames_v3")
    ap.add_argument("--out", default="out/dispatch/review")
    ap.add_argument("--sheets", type=int, default=6)
    ap.add_argument("--per-sheet", type=int, default=6)
    ap.add_argument("--strips", default="", help="name:frame[:step[:x0,y0,x1,y1]],... (step default 2 = 1/15s; optional FULL-RES crop region — use it: downscaled whole frames hide sub-4px motion detail like shutter blur and tail swing)")
    ap.add_argument("--strip-len", type=int, default=8)
    a = ap.parse_args()
    fs = sorted(glob.glob(os.path.join(a.frames, "frame_*.png")))
    if not fs:
        raise SystemExit(f"no frames in {a.frames}")
    os.makedirs(a.out, exist_ok=True)
    n = len(fs)

    # contact sheets: stills across the whole timeline
    total = a.sheets * a.per_sheet
    picks = [int(i * (n - 1) / (total - 1)) for i in range(total)]
    for s in range(a.sheets):
        sheet = Image.new("RGB", (3 * 360, 2 * 640), (10, 10, 14))
        for j in range(a.per_sheet):
            im = Image.open(fs[picks[s * a.per_sheet + j]]).resize((360, 640))
            sheet.paste(im, ((j % 3) * 360, (j // 3) * 640))
        sheet.save(os.path.join(a.out, f"sheet_{s}.png"))

    # motion filmstrips: CONSECUTIVE frames at the key moves
    strips = []
    if a.strips:
        for part in a.strips.split(";"):
            bits = part.strip().split(":")
            name, f0 = bits[0], int(bits[1])
            st = int(bits[2]) if len(bits) > 2 and bits[2] else 2
            crop = tuple(int(v) for v in bits[3].split(",")) if len(bits) > 3 else None
            strips.append((name, f0, st, crop))
    else:
        for k, frac in (("early", 0.15), ("mid", 0.5), ("late", 0.85)):
            strips.append((k, int(n * frac), 2, None))
    for name, f0, st, crop in strips:
        f0 = max(0, min(n - 1 - a.strip_len * st, f0))
        # FULL-RES region crops: downscaled whole frames hide sub-4px motion (shutter smear, tail
        # swing) — crop the action region at native resolution so motion evidence survives
        if crop:
            cw, ch = crop[2] - crop[0], crop[3] - crop[1]
            sheet = Image.new("RGB", (a.strip_len * cw, ch), (0, 0, 0))
            for j in range(a.strip_len):
                sheet.paste(Image.open(fs[f0 + j * st]).crop(crop), (j * cw, 0))
        else:
            sheet = Image.new("RGB", (a.strip_len * 270, 480), (0, 0, 0))
            for j in range(a.strip_len):
                sheet.paste(Image.open(fs[f0 + j * st]).resize((270, 480)), (j * 270, 0))
        sheet.save(os.path.join(a.out, f"strip_{name}.png"))
    print(f"review pack: {a.sheets} sheets + {len(strips)} motion strips -> {a.out}")

if __name__ == "__main__":
    main()
