#!/usr/bin/env python3
"""FORCED ALIGNMENT for dispatch captions — the fix for caption/voice desync.

The old pipeline APPROXIMATED word timings (evenly spreading each phrase's words
across its slot), then scaled them for a tempo change, then hand-shifted them for
the silence dip. Three stacked approximations produced visible desync on the
2026-07-14 dispatch. This script replaces all of that: it transcribes the FINAL
rendered VO with faster-whisper (word_timestamps=True) so every caption cue comes
from the actual audio (~±50-100ms), no guessing, no scaling, ever.

Usage:
  .venv-voice/bin/python scripts/align_captions.py \
      --audio out/dispatch/audio/vo60.wav \
      --script out/dispatch/vo_script.txt \
      --out out/dispatch/audio/words60.json [--total 60]

- --script is optional: when given, whisper gets it as an initial_prompt (better
  proper nouns) and the output words are validated against it (a mismatch count
  is reported so the caller can gate on transcription quality).
- Output schema matches what dispatch_core expects:
  {"words":[{"w","s","e","seg"}...], "speech_end", "total", "fps": 30}
  seg = sentence index (split on ./!/?), so phrase-level cues still work.
"""
import argparse, json, re, sys
from pathlib import Path


def norm_word(w):
    return re.sub(r"[^a-z0-9']", "", w.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--script", default="", help="intended VO text (optional, improves + validates)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--total", type=float, default=90.0)   # 90s format, 2026-07-30
    ap.add_argument("--model", default="base", help="faster-whisper model size (base is enough for alignment)")
    a = ap.parse_args()

    from faster_whisper import WhisperModel

    script_text = Path(a.script).read_text().strip() if a.script and Path(a.script).exists() else ""
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segments, info = model.transcribe(
        a.audio,
        word_timestamps=True,
        language="en",
        initial_prompt=script_text[:200] if script_text else None,
        vad_filter=False,          # the VO is clean studio speech; VAD can clip word onsets
        beam_size=5,
    )

    words = []
    seg_idx = 0
    for seg in segments:
        for w in seg.words or []:
            token = w.word.strip()
            if not token:
                continue
            words.append({"w": token, "s": round(w.start, 3), "e": round(w.end, 3), "seg": seg_idx})
            if token.endswith((".", "!", "?")):
                seg_idx += 1

    if not words:
        print("FAIL: no words aligned — is the audio silent or non-speech?", file=sys.stderr)
        sys.exit(1)

    speech_end = words[-1]["e"]

    # validation vs intended script (word-level, orders preserved via simple sequence ratio)
    mismatch_note = ""
    if script_text:
        import difflib
        got = [norm_word(w["w"]) for w in words]
        want = [norm_word(t) for t in script_text.split() if norm_word(t)]
        ratio = difflib.SequenceMatcher(None, got, want).ratio()
        mismatch_note = f"  transcript_match={ratio:.3f} (vs intended script)"
        if ratio < 0.85:
            print(f"WARN: aligned transcript matches only {ratio:.0%} of the intended script — "
                  f"check the VO audio for synthesis errors before shipping.", file=sys.stderr)

    out = {"words": words, "speech_end": round(speech_end, 3), "total": a.total, "fps": 30}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"aligned {len(words)} words, speech_end={speech_end:.2f}s -> {a.out}{mismatch_note}")


if __name__ == "__main__":
    main()
