#!/usr/bin/env bash
# ============================================================================
# MUX + VERIFY — attach the mixed master audio to the silent render, and FAIL
# loudly if the result is silent.
#
# Why this exists: the 2026-07-17 dispatch shipped SILENT. The mix (master.wav)
# was fine (-16.8 dB), but the final `ffmpeg -i video -i audio` had no `-map`,
# so ffmpeg's default stream selection took the RENDER's empty audio track
# instead of the master. The quality gate checked master60.wav (not the mp4),
# so nothing caught it. This wrapper makes BOTH mistakes impossible:
#   1. explicit `-map 0:v:0 -map 1:a:0` (never guess the audio stream)
#   2. probe the OUTPUT mp4's mean_volume and exit non-zero if it is silent
#      (< -60 dB), so a silent mux fails the run instead of shipping.
#
# Usage: scripts/mux_and_verify.sh <silent_video.mp4> <master.wav> <out.mp4>
# ============================================================================
set -euo pipefail
FF="${FFMPEG_BIN:-ffmpeg}"
SILENCE_FLOOR_DB=-60

if [ "$#" -ne 3 ]; then
  echo "usage: mux_and_verify.sh <silent_video.mp4> <master.wav> <out.mp4>" >&2
  exit 2
fi
VIDEO="$1"; AUDIO="$2"; OUT="$3"

# PAD THE AUDIO TO THE PICTURE; NEVER CUT THE PICTURE TO THE AUDIO (2026-08-12).
# `-shortest` alone truncates whichever stream ends first, and the audio master always
# ends first because it is mixed against the VO while the render carries an end-credits
# tail after the last spoken word. On 2026-08-12 that silently cut 5.4s off a 119.6s film
# and took the whole credits card with it, which is where the music is attributed. The bed
# is CC BY 4.0, so attribution is a LICENCE CONDITION and not a courtesy, and a panel judge
# had already reported being unable to find the credit on any viewer-facing surface. The
# mux was eating it.
#
# apad extends the audio with silence; -shortest then trims that padding back to the exact
# video duration instead of trimming the video. Keep both: apad without -shortest would run
# forever, and -shortest without apad is the bug above.
"$FF" -y -i "$VIDEO" -i "$AUDIO" \
  -map 0:v:0 -map 1:a:0 -af apad \
  -c:v copy -c:a aac -b:a 192k -ar 48000 -movflags +faststart -shortest "$OUT" >/dev/null 2>&1

# verify the OUTPUT actually carries audio
mean=$("$FF" -i "$OUT" -af volumedetect -f null - 2>&1 | grep -oE "mean_volume: -?[0-9.]+ dB" | grep -oE "\-?[0-9.]+" | head -1)
if [ -z "$mean" ]; then
  echo "MUX VERIFY FAIL: $OUT has no audio stream at all" >&2
  exit 1
fi
# bash can't do float compare; use awk
if awk -v m="$mean" -v f="$SILENCE_FLOOR_DB" 'BEGIN{exit !(m < f)}'; then
  echo "MUX VERIFY FAIL: $OUT mean_volume ${mean} dB is below the silence floor ${SILENCE_FLOOR_DB} dB (the mux grabbed a silent track)" >&2
  exit 1
fi
echo "MUX OK: $OUT  mean_volume ${mean} dB (audio present)"
