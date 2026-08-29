#!/usr/bin/env bash
# Encode the one non-shipped mastering source into exactly five manifested
# distribution artifacts. No 4:5 or historical output alias is accepted.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT=out/dispatch
# Transaction boundary comes first. It removes stale success controls and old
# outputs before any argument/source/retired-alias failure can return.
python3 scripts/mastering_contract.py prepare

MUTE="$OUT/render/video_mute.mp4"
if [ -n "${1:-}" ] && [ "${1}" != "$MUTE" ] && [ "${1}" != "$PWD/$MUTE" ]; then
  echo "encode_deliverables: mute input must be the canonical $MUTE" >&2
  exit 2
fi
WAV="$OUT/audio/master.wav"
if [ -n "${2:-}" ] && [ "${2}" != "$WAV" ] && [ "${2}" != "$PWD/$WAV" ]; then
  echo "encode_deliverables: audio input must be the canonical $WAV" >&2
  exit 2
fi
MASTERING="$OUT/dispatch_mastering_source.mp4"  # internal only; never upload/email/feed
HOSTED="$OUT/dispatch_master_hosted.mp4"        # canonical shipped 9:16 bytes
SQUARE="$OUT/dispatch_square.mp4"
MOBILE="$OUT/dispatch_master_720.mp4"
POSTER="$OUT/poster.png"
THUMB="$OUT/poster_thumb_vertical.jpg"

for retired in \
  "$OUT/dispatch_master.mp4" \
  "$OUT/dispatch_4x5.mp4" \
  "$OUT/poster_thumb.jpg" \
  "$OUT/render/master_9x16.mp4" \
  "$OUT/render/master_4x5.mp4"; do
  if [ -e "$retired" ]; then
    echo "encode_deliverables: REFUSING retired output alias: $retired" >&2
    echo "Remove this stale scratch artifact explicitly before encoding; it is not a deliverable." >&2
    exit 2
  fi
done

[ -f "$MUTE" ] || { echo "encode_deliverables: missing mute render $MUTE" >&2; exit 1; }
[ -f "$WAV" ] || { echo "encode_deliverables: missing audio master $WAV" >&2; exit 1; }
[ -f "$OUT/audio/vo.wav" ] || { echo "encode_deliverables: missing current VO $OUT/audio/vo.wav" >&2; exit 1; }

python3 scripts/run_guard.py require-composition --composition DispatchDaily
python3 scripts/render_contract.py check

if [ "$WAV" -ot "$OUT/audio/vo.wav" ]; then
  echo "encode_deliverables: STALE MIX: $WAV is older than the current VO" >&2
  exit 1
fi

bash scripts/mux_and_verify.sh "$MUTE" "$WAV" "$MASTERING"

# Resolution is fixed; bitrate may step down to fit GitHub's 99 MiB hard path.
HOST_MAX_BYTES="${HOST_MAX_BYTES:-99614720}"
hosted_ok=0
for crf in 20 22 24 26; do
  ffmpeg -y -i "$MASTERING" \
    -c:v libx264 -profile:v high -crf "$crf" -pix_fmt yuv420p -movflags +faststart \
    -c:a copy "$HOSTED" -v error
  bytes="$(stat -c%s "$HOSTED")"
  if [ "$bytes" -le "$HOST_MAX_BYTES" ]; then
    echo "encode_deliverables: hosted 1080x1920 CRF=$crf bytes=$bytes"
    hosted_ok=1
    break
  fi
done
if [ "$hosted_ok" != 1 ]; then
  echo "encode_deliverables: no full-resolution encode fits the host ceiling" >&2
  exit 1
fi

# Every derivative begins with the canonical hosted bytes, never the internal master.
ffmpeg -y -i "$HOSTED" -vf "crop=1080:1080:0:420" \
  -c:v libx264 -profile:v high -crf 20 -pix_fmt yuv420p -movflags +faststart \
  -c:a copy "$SQUARE" -v error

ffmpeg -y -i "$HOSTED" -vf scale=720:1280 \
  -c:v libx264 -profile:v main -crf 26 -maxrate 1400k -bufsize 2800k \
  -pix_fmt yuv420p -movflags +faststart -c:a copy "$MOBILE" -v error

POSTER_AT="${POSTER_AT:-9.2}"
ffmpeg -y -ss "$POSTER_AT" -i "$SQUARE" -frames:v 1 "$POSTER" -v error
ffmpeg -y -ss "$POSTER_AT" -i "$HOSTED" -frames:v 1 -vf scale=540:960 -q:v 5 "$THUMB" -v error

# Measure the actual delivered square after its encode. Its audio is stream-copied,
# but this hard gate keeps loudness/true-peak claims attached to delivered bytes.
audio_json="$(ffmpeg -i "$SQUARE" -af loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json -f null - 2>&1 | tail -20)"
audio_i="$(printf '%s' "$audio_json" | sed -n 's/.*"input_i"[^\"]*"\([^\"]*\)".*/\1/p' | head -1)"
audio_tp="$(printf '%s' "$audio_json" | sed -n 's/.*"input_tp"[^\"]*"\([^\"]*\)".*/\1/p' | head -1)"
if [ -z "$audio_i" ] || [ -z "$audio_tp" ]; then
  echo "encode_deliverables: could not measure delivered audio" >&2
  exit 1
fi
awk -v i="$audio_i" -v tp="$audio_tp" 'BEGIN {
  if (i < -15.0 || i > -13.0) {printf "encode_deliverables: loudness %.2f LUFS outside -15..-13\n", i > "/dev/stderr"; exit 1}
  if (tp > -1.0) {printf "encode_deliverables: true peak %.2f dBTP above -1.0\n", tp > "/dev/stderr"; exit 1}
}'

python3 scripts/mastering_contract.py finalize
python3 scripts/mastering_contract.py check
python3 scripts/deliverable_contract.py build
python3 scripts/deliverable_contract.py check
echo "encode_deliverables: PASS: one internal master + five exact manifested deliverables"
