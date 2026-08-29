#!/usr/bin/env bash
# Render wrapper — makes the taste loop CHEAP and the final SHIP-GRADE.
#
#   scripts/render.sh draft  [comp] [out.mp4]   half-res, fast-encode preview (~3-4x faster)
#   scripts/render.sh final  [comp] [out.mp4]   full 1080x1920, ship quality
#   scripts/render.sh still  <frame> [comp] [out.png] [--draft]
#
# THE RULE (docs: taste loop / Phase 5): iterate on DRAFT renders and draft
# stills — look, fix, re-render 3-5x at low cost. Only the FINAL gate and the
# judge panel see a full-res render. Draft stills are half-res; critics grading
# COMPOSITION/story can use them, but legibility checks (caption px heights)
# must run on a final-res render.
set -euo pipefail
# CALLER_PWD: captured BEFORE the cd below. A relative OUT path the caller types (e.g.
# "out/dispatch/render/video_mute.mp4" from the repo root) is resolved against THIS
# directory, not video-engine/ -- the 2026-07-22 gotcha that cost a long debugging loop:
# every explicit OUT argument was silently written to video-engine/out/... instead of the
# repo-root out/... the caller expected, so a mux+gate cycle kept re-testing a stale file
# and made real engine fixes look like no-ops. Only the DEFAULT out paths below (relative
# to video-engine, "../out/...") are exempt, since those already resolve correctly as-is.
CALLER_PWD="$PWD"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/pw-browsers}"
PROPS="$REPO_ROOT/out/dispatch/episode_props.json"

resolve_out() {   # abs path -> unchanged; relative path -> resolved against the CALLER's cwd
  local p="$1"
  case "$p" in
    /*) printf '%s' "$p" ;;
    *)  printf '%s' "$CALLER_PWD/$p" ;;
  esac
}

# THE COMPOSITION LOCK (added 2026-07-31, after rendering the wrong film).
#
# Root.tsx keeps past episodes under explicit legacy IDs. Before B1, the generic id
# "Dispatch" was wired to a previous run's component. Rendering it succeeded, exited 0,
# writes an mp4 of the right length, and produces the wrong film. It did: this run rendered
# 93.3 seconds of the July 26 episode, whose scenes run out around 60 seconds, so the last
# third came out as blank grey with this run's captions burned over it. Nothing in the
# pipeline objected. Every hash matched, the mux verified, the encodes passed their ffprobe
# assertions, and the freshness check was satisfied, because all of those check that the
# deliverable is CURRENT and none of them check that it is the right MOVIE.
#
# So the run's composition id is now recorded in out/dispatch/.run_stamp.json and this
# wrapper refuses to render anything else. A stale id from an old command line, an old doc,
# or a habit stops here instead of at the panel.
python3 scripts/run_guard.py bind-inputs
python3 scripts/run_guard.py require-composition --composition DispatchDaily
RUN_COMP="$(python3 -c 'import sys;sys.path.insert(0,"scripts");from run_guard import load_stamp;print(load_stamp()["composition"])')"
assert_comp() {
  local want="$1"
  if [[ "$want" != "$RUN_COMP" ]]; then
    echo "render.sh: REFUSING to render composition '$want'." >&2
    echo "  This run's film is '$RUN_COMP' (out/dispatch/.run_stamp.json)." >&2
    echo "  Root.tsx still has every past episode registered, so a wrong id renders a" >&2
    echo "  PREVIOUS run's film at this run's length and exits 0. That is how the" >&2
    echo "  2026-07-31 run produced 30 seconds of blank frames and did not notice." >&2
    echo "  If the film really did change, create a new explicit run stamp." >&2
    exit 3
  fi
}

MODE="${1:?usage: render.sh draft|final|still ...}"
case "$MODE" in
  draft)
    COMP="${2:-$RUN_COMP}"; assert_comp "$COMP"; OUT="$REPO_ROOT/out/dispatch/render/draft.mp4"; [[ -n "${3:-}" ]] && OUT="$(resolve_out "$3")"
    cd "$REPO_ROOT/video-engine"
    exec npx remotion render src/index.ts "$COMP" "$OUT" \
      --props="$PROPS" --codec=h264 --muted --concurrency=4 \
      --scale=0.5 --crf=30 --every-nth-frame=1
    ;;
  final)
    COMP="${2:-$RUN_COMP}"; assert_comp "$COMP"; OUT="$REPO_ROOT/out/dispatch/render/video_mute.mp4"; [[ -n "${3:-}" ]] && OUT="$(resolve_out "$3")"
    cd "$REPO_ROOT/video-engine"
    exec npx remotion render src/index.ts "$COMP" "$OUT" \
      --props="$PROPS" --codec=h264 --muted --concurrency=4 --crf=19
    ;;
  still)
    FRAME="${2:?frame number}"; COMP="${3:-$RUN_COMP}"; assert_comp "$COMP"
    OUT="$REPO_ROOT/out/dispatch/probe/still_$FRAME.png"; [[ -n "${4:-}" && "${4:-}" != "--draft" ]] && OUT="$(resolve_out "$4")"
    SCALE=1
    if [[ "${5:-}" == "--draft" || "${4:-}" == "--draft" ]]; then SCALE=0.5; fi
    cd "$REPO_ROOT/video-engine"
    exec npx remotion still src/index.ts "$COMP" "$OUT" --frame="$FRAME" --props="$PROPS" --scale="$SCALE"
    ;;
  *)
    echo "unknown mode: $MODE (draft|final|still)"; exit 2
    ;;
esac
