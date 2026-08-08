#!/usr/bin/env bash
# ============================================================================
# PARALLEL RENDER — split the frame range across SEPARATE PROCESSES, then concat.
#
# MEASURED 2026-08-04 on the 4-core / 15GB routine box, 240 frames of Dispatch0803:
#     one process, --concurrency=2 ....... 149s
#     one process, --concurrency=4 ....... 155s   (NO GAIN)
#     four processes, 60 frames each ......  56s   (2.7x FASTER)
#
# AND THEN, on the full 2513-frame film, 4 equal chunks measured:
#     chunk 0 (S1-S3, characters + packet) .. ~14 min
#     chunks 1, 2, 3 ........................ ~4 min each, then idle
# i.e. ~26 min of work spread over 4 slots finished in 14 min of wall clock, because equal
# FRAME counts are not equal WORK. Hence the queue below: 12 chunks through 4 slots.
#
# So Remotion's in-process concurrency does not scale here: the tabs contend inside
# one Chrome and adding more just adds contention. Separate PROCESSES each get their
# own browser and do scale. That is why raising --concurrency looked like the obvious
# lever and did nothing, and it is why the owner remembered splitting the render.
#
# On the full 2513-frame film: ~30 minutes single-process, 14 with 4 equal chunks, and
# the queue below is what closes the rest of the gap toward the ~7 the work actually costs.
#
# Concat is STREAM COPY (-c copy), so the output is bit-identical to a single-process
# render; no re-encode, no generation loss. Chunk boundaries are exact frame ranges so
# no frame is rendered twice or skipped, and the script ASSERTS the final frame count
# against the expected total before it will hand back a file.
#
# Usage: scripts/render_parallel.sh <Comp> <out.mp4> [total_frames] [chunks]
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."
# NO DEFAULT COMPOSITION (2026-08-08). This read `${1:-Dispatch0803}`, so invoking the
# script with no arguments silently rendered a film that shipped on August 3rd. It cost
# 2.5 hours: the render succeeded, printed OK, produced a valid 3835-frame file with a
# plausible size, and every downstream step would have graded the wrong movie.
#
# A default target is only ever right for the run it was written in. Nothing about a
# per-run composition id belongs in a fallback, because the failure mode is not an error
# but a confident success on the wrong subject. Same family as the three gates this run
# that reported clean while reading a shipped July episode.
if [ $# -lt 1 ]; then
  echo "render_parallel.sh: refusing to guess which film to render." >&2
  echo "Usage: scripts/render_parallel.sh <Comp> <out.mp4> [total_frames] [chunks]" >&2
  echo "Compositions are declared in video-engine/src/Root.tsx." >&2
  exit 2
fi
COMP="$1"
OUT="${2:-out/dispatch/render_mute.mp4}"
PROPS="${PROPS:-out/dispatch/episode_props.json}"
# MORE CHUNKS THAN SLOTS, ON PURPOSE (2026-08-04). The first version cut the film into
# exactly one chunk per slot, which is only optimal when every frame costs the same. It
# does not: on the 2026-08-03 film, chunk 0 held S1 to S3, which carry the characters and
# the award packet, and it took about 14 minutes while chunks 1, 2 and 3 finished in about
# 4 and then sat idle. Wall clock was 14 minutes for roughly 26 minutes of work across 4
# slots, so three quarters of the machine was doing nothing for ten minutes.
#
# Smaller chunks fed through a work queue fix that without needing to predict which shots
# are expensive: when a slot frees, it takes the next chunk. The cost is one extra Chrome
# start per chunk (~10-15s), which is why this is 12 and not 60.
CHUNKS="${4:-12}"
SLOTS="${SLOTS:-4}"

# A CHUNK CAN HANG FOREVER AFTER BUNDLING (2026-08-04, observed twice in two renders).
# Remotion prints "Bundling 100%" and then never emits a single "Rendered" line. It does
# not crash, it does not exit, it just sits. Measured: a healthy 210-frame chunk finishes
# in 90 to 150 seconds; the hung ones sat past 330 and 700 seconds with zero frames. It
# hit chunk 0 on one render and chunk 3 on the next, so it is not a property of any shot.
#
# Left alone this stalls the WHOLE render behind one dead slot, and a run that is waiting
# on a process that will never finish looks exactly like a run that is making progress.
# That is how a routine burns its window and ships nothing. A hang is now a bounded
# failure: cap the attempt, then retry the chunk from scratch.
CHUNK_TIMEOUT="${CHUNK_TIMEOUT:-420}"
TRIES="${TRIES:-3}"

# total frames: from episode_props.json unless the caller states it
TOTAL="${3:-}"
if [ -z "$TOTAL" ]; then
  TOTAL="$(python3 -c "import json;print(json.load(open('$PROPS'))['total'])")"
fi

case "$OUT" in /*) ABS_OUT="$OUT";; *) ABS_OUT="$PWD/$OUT";; esac
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

echo "parallel render: $COMP  $TOTAL frames  $CHUNKS chunks, $SLOTS at a time"
# DELETE THE OLD FILM BEFORE RENDERING THE NEW ONE (2026-08-04). When a chunk dies the
# script exits 1, correctly, but it used to leave the PREVIOUS render sitting at $OUT
# with a plausible size and a valid frame count. Every downstream step then ran happily
# on yesterday's picture: encode, evidence, panel, all of it scoring a film that does
# not contain the fixes the run just made. It cost a full panel round to notice, by
# checking a timestamp by hand. A failed render must leave NO output, so that everything
# after it fails loudly instead of quietly succeeding on the wrong bytes.
rm -f "$ABS_OUT"

# Render one chunk, surviving the post-bundle hang described above. A chunk that produces
# no output file inside CHUNK_TIMEOUT is killed and retried from scratch. Success is
# judged on the FILE existing and being non-empty, not on the exit status, because the
# hang does not set one.
render_chunk() {
  local i="$1" A="$2" B="$3" attempt=1
  while [ "$attempt" -le "$TRIES" ]; do
    ( cd video-engine && timeout -k 15 "$CHUNK_TIMEOUT" \
        npx remotion render src/index.ts "$COMP" "$WORK/c$i.mp4" \
        --props="../$PROPS" --codec=h264 --muted --concurrency=1 --crf=19 \
        --frames="$A-$B" ) >"$WORK/c$i.attempt$attempt.log" 2>&1 || true
    if [ -s "$WORK/c$i.mp4" ]; then
      cp "$WORK/c$i.attempt$attempt.log" "$WORK/c$i.log"
      [ "$attempt" -gt 1 ] && echo "  chunk $i recovered on attempt $attempt" >&2
      return 0
    fi
    echo "  chunk $i attempt $attempt produced no file (hang or crash), retrying" >&2
    attempt=$(( attempt + 1 ))
  done
  cp "$WORK/c$i.attempt$(( attempt - 1 )).log" "$WORK/c$i.log" 2>/dev/null || true
  echo "  chunk $i FAILED after $TRIES attempts" >&2
  return 1
}

PER=$(( (TOTAL + CHUNKS - 1) / CHUNKS ))
LIST="$WORK/list.txt"; : > "$LIST"
FAIL=0; RUNNING=0

for i in $(seq 0 $((CHUNKS - 1))); do
  A=$(( i * PER ))
  B=$(( A + PER - 1 ))
  [ "$B" -ge "$TOTAL" ] && B=$(( TOTAL - 1 ))
  [ "$A" -gt "$B" ] && continue
  echo "  chunk $i: frames $A-$B"
  render_chunk "$i" "$A" "$B" &
  echo "file '$WORK/c$i.mp4'" >> "$LIST"
  RUNNING=$(( RUNNING + 1 ))
  # THE WORK QUEUE. Hold at most SLOTS renders in flight and start the next chunk the
  # moment any one of them finishes, so a slow chunk overlaps with fast ones instead of
  # holding the whole render open on its own.
  if [ "$RUNNING" -ge "$SLOTS" ]; then
    wait -n || FAIL=1
    RUNNING=$(( RUNNING - 1 ))
  fi
done

while [ "$RUNNING" -gt 0 ]; do
  wait -n || FAIL=1
  RUNNING=$(( RUNNING - 1 ))
done
if [ "$FAIL" -ne 0 ]; then
  echo "a chunk failed; logs in $WORK" >&2
  for l in "$WORK"/c*.log; do echo "--- $l"; tail -5 "$l"; done >&2
  exit 1
fi

ffmpeg -y -f concat -safe 0 -i "$LIST" -c copy "$ABS_OUT" -v error

GOT="$(ffprobe -v error -select_streams v:0 -count_frames \
        -show_entries stream=nb_read_frames -of default=nw=1:nk=1 "$ABS_OUT" | head -1)"
if [ "$GOT" != "$TOTAL" ]; then
  echo "FRAME COUNT ASSERT FAILED: concat produced $GOT frames, expected $TOTAL ($ABS_OUT)" >&2
  echo "  A short concat means a chunk boundary is wrong; do NOT ship this file." >&2
  exit 1
fi
echo "  OK  $ABS_OUT  $GOT frames  $(du -h "$ABS_OUT" | cut -f1)"
