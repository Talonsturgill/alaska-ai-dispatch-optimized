#!/usr/bin/env bash
# Phase-6 self-healing loop driver: render -> objective gate -> encode (ONLY on PASS).
# The master agent runs this. On a non-zero exit (gate FAIL) the master delegates the named
# failure + quality_report.json to the `dispatch-fixer` subagent, then RE-INVOKES this script.
# The loop's only exit is PASS; it never encodes a render that fails the gate. No cap, no fallback.
#
#   bash scripts/dispatch_loop.sh              # render all frames, gate, encode on pass
#   bash scripts/dispatch_loop.sh --no-render  # gate the existing frames, encode on pass
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENG="$ROOT/.claude/skills/alaska-dispatch"        # committed engine = source of truth
WORK="${DISPATCH_WORK:-$ROOT/out/dispatch}"       # working scratch (frames, audio, master)
FRAMES_DIR="$WORK/frames_v3"
TOT="${DISPATCH_FRAMES:-1800}"
NORENDER=0; [ "${1:-}" = "--no-render" ] && NORENDER=1

mkdir -p "$WORK" "$FRAMES_DIR"; cd "$WORK"
# always run the committed engine, so the loop reflects what's actually shipped
for f in render_v3.py vo60.py audio_v3.py quality_gate.py craft.py easing.py; do
  [ -f "$ENG/$f" ] && cp -f "$ENG/$f" "$WORK/"; done

if [ "$NORENDER" = "0" ]; then
  echo "=== render $TOT frames (parallel across $(nproc) cores) ==="
  rm -f "$FRAMES_DIR"/*.png
  N=$(nproc); CH=$(( (TOT + N - 1) / N ))
  for ((i=0;i<N;i++)); do s=$((i*CH)); e=$((s+CH)); [ $e -gt $TOT ] && e=$TOT; [ $s -ge $TOT ] && break
    python render_v3.py $s $e >"$WORK/_rv_$i.log" 2>&1 & done
  wait
fi
echo "frames: $(ls "$FRAMES_DIR"/*.png 2>/dev/null | wc -l)/$TOT"

echo "=== GATE A: objective quality gate ==="
if ! python quality_gate.py --frames "$FRAMES_DIR" --words "$WORK/audio/words60.json" --fps 30 --max-gap 5.0; then
  echo ""
  echo ">>> GATE FAILED — the loop does NOT stop here."
  echo ">>> Master: hand the failing check(s) above + $WORK/quality_report.json to the dispatch-fixer"
  echo ">>> subagent (it patches the cause in its own context), then RE-INVOKE this script."
  echo ">>> Do not encode, do not deliver. The only exit is PASS."
  exit 1
fi

echo "=== GATE PASS — encoding BOTH masters (9:16 TikTok + 4:5 LinkedIn feed) ==="
# 9:16 1080x1920 — TikTok-native. On LinkedIn this ratio is pulled into the swipe-only Video tab.
ffmpeg -y -framerate 30 -i "$FRAMES_DIR/frame_%05d.png" -i "$WORK/audio/master60.wav" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -profile:v high \
  -c:a aac -b:a 320k -movflags +faststart -shortest "$WORK/dispatch_master.mp4" 2>"$WORK/_encode.log" \
  || { echo "9:16 ENCODE FAIL"; tail -8 "$WORK/_encode.log"; exit 2; }

# 4:5 1080x1350 — THE LINKEDIN FEED CUT. 4:5 stays in the MAIN HOME FEED next to the post
# copy; 9:16 does not. Center-crop of the 9:16 (composition keeps hero + captions inside the
# centered 4:5 safe box per the routine spec). Cropped from the LOSSLESS PNG frames, not
# re-encoded from the mp4, so no double compression. (1920-1350)/2 = 285 = centered;
# override DISPATCH_CROP45_Y only if a run placed its captions outside the safe box.
CROP_Y="${DISPATCH_CROP45_Y:-285}"
ffmpeg -y -framerate 30 -i "$FRAMES_DIR/frame_%05d.png" -i "$WORK/audio/master60.wav" \
  -vf "crop=1080:1350:0:$CROP_Y" \
  -c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p -profile:v high \
  -c:a aac -b:a 320k -movflags +faststart -shortest "$WORK/dispatch_master_4x5.mp4" 2>"$WORK/_encode45.log" \
  || { echo "4:5 ENCODE FAIL"; tail -8 "$WORK/_encode45.log"; exit 2; }

echo "=== MASTERS READY ==="
for m in dispatch_master.mp4 dispatch_master_4x5.mp4; do
  [ -f "$WORK/$m" ] && ls -la "$WORK/$m" | awk -v m="$m" '{print "  "m": "$5" bytes"}'; done
# Prove the pixel dimensions so a wrong-ratio cut can never silently ship (this is the whole bug).
python3 - "$WORK/dispatch_master.mp4" "$WORK/dispatch_master_4x5.mp4" <<'PY'
import subprocess, sys
want={"dispatch_master.mp4":"1080x1920","dispatch_master_4x5.mp4":"1080x1350"}
for p in sys.argv[1:]:
    name=p.split("/")[-1]
    try:
        wh=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0",
            "-show_entries","stream=width,height","-of","csv=s=x:p=0",p]).decode().strip()
        ok="OK" if wh==want.get(name) else f"MISMATCH (want {want.get(name)})"
        print(f"  {name}: {wh}  [{ok}]")
    except Exception as e:
        print(f"  {name}: probe failed {e}")
PY
echo ""
echo "Next: keep both cuts local or upload to the CANARY media branch, then build dispatch_email.py --local-only --out-html preview.html."
echo ">>> LinkedIn: post the 4:5 (dispatch_master_4x5.mp4) — it lands in the MAIN FEED. 9:16 = TikTok."
