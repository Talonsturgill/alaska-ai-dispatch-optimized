#!/usr/bin/env bash
# ============================================================================
# LOOK AT THE EDIT BEFORE YOU SPEND A RENDER ON IT.
#
# WHY THIS EXISTS (2026-08-09, owner: "you introduce a lot of defects when editing").
# ----------------------------------------------------------------------------
# Every placement defect this routine shipped in one day came from the same move: an element
# was repositioned to fix one complaint and landed on something else, and nobody looked until
# a judge did, two renders later. The list is embarrassing and it is all one mistake:
#
#   - the location label moved off the miner's legs and onto the dashed polygon it labels
#   - the brand mark moved into the closing frame and landed across the hero tank
#   - the 4 PAPERS card moved off the tank's valve and back into the caption band
#   - the BIOLOGY chip was plated for contrast and overflowed its parent panel
#
# The geometry gates caught none of them, correctly: they model frame edges, plate-on-plate
# overlap and the caption band, and every one of these was an element landing on ART, which
# no gate in this repo models and none reasonably can.
#
# What catches it is looking. The reason nobody looked is that looking cost a 13-minute full
# render, so the temptation was always to batch the edit with the next one and find out later.
# Rendering eleven frames costs about a minute. That is the whole idea.
#
# Usage:
#   scripts/probe_frames.sh <Comp> <seconds[,seconds...]>   # e.g. 91.3,116.0,129.4
#   scripts/probe_frames.sh Dispatch0809 91.3,129.4
#
# Writes out/dispatch/probe/f<sec>.jpg and a single contact strip probe_strip.jpg.
# It renders MUTE and from the same props the real render uses, so what you see is what the
# full render will draw.
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -lt 2 ]; then
  echo "usage: probe_frames.sh <Comp> <seconds[,seconds...]>" >&2
  exit 2
fi
COMP="$1"
TIMES="$2"
PROPS="${PROPS:-out/dispatch/episode_props.json}"
OUTDIR="out/dispatch/probe"
FPS="${FPS:-30}"

# Parse fails a bundle dead, and finding that out per-frame is the slow way.
if [ -d video-engine/node_modules/esbuild ]; then
  for _f in video-engine/src/*.tsx video-engine/src/lib/*.tsx; do
    [ -e "$_f" ] || continue
    (cd video-engine && npx --no-install esbuild "${_f#video-engine/}" \
       --log-level=error --outfile=/dev/null) || { echo "probe: engine does not parse." >&2; exit 4; }
  done
fi

rm -rf "$OUTDIR"; mkdir -p "$OUTDIR"
IFS=',' read -ra SECS <<< "$TIMES"
SHOTS=()
for s in "${SECS[@]}"; do
  fr=$(python3 -c "print(int(round(float('$s')*$FPS)))")
  out="$OUTDIR/f${s}.mp4"
  ( cd video-engine && npx remotion render src/index.ts "$COMP" "../$out" \
      --props="../$PROPS" --codec=h264 --muted --concurrency=1 --crf=22 \
      --frames="$fr-$fr" ) >/dev/null 2>&1 || { echo "probe: render failed at ${s}s" >&2; exit 1; }
  ffmpeg -y -loglevel error -i "$out" -frames:v 1 -q:v 3 "$OUTDIR/f${s}.jpg"
  rm -f "$out"
  SHOTS+=("$OUTDIR/f${s}.jpg")
  echo "  probed ${s}s -> $OUTDIR/f${s}.jpg"
done

# one strip, so a placement edit is judged against its neighbours rather than in isolation
if [ "${#SHOTS[@]}" -gt 1 ]; then
  ffmpeg -y -loglevel error $(printf -- "-i %s " "${SHOTS[@]}") \
    -filter_complex "hstack=inputs=${#SHOTS[@]},scale=-1:900" "$OUTDIR/probe_strip.jpg"
  echo "  strip -> $OUTDIR/probe_strip.jpg"
fi
echo "probe_frames: ${#SHOTS[@]} frame(s). LOOK AT THEM before starting a full render."
