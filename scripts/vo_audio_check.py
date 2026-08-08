#!/usr/bin/env python3
"""Does the AUDIO WE ARE ACTUALLY SHIPPING obey the fact-check-safe set?

WHY THIS EXISTS (2026-08-08). scripts/vo_claims_check.py gates the SCRIPT before a second
of TTS is spent, which is the right place to catch a false line cheaply. It is not the last
place a false line can exist, because the script and the audio can diverge, and on this run
they did.

The caption scorer found that the narration claimed the X-ray machines went to "five rural
clinics that didn't have one", an imaging-absence inference claims.json bans outright. The
voice was already synthesized, so the fix was surgical: scripts/vo_patch_lines.py re-cut the
offending lines inside their existing slots. One line's replacement could not be fitted to
its slot and the tool correctly refused rather than ship a bad splice. So at that moment the
repo contained a CORRECTED SCRIPT and, for one line, UNCORRECTED AUDIO — and every gate the
pipeline had was reading the script.

A panel judge then charged the film with the banned claim, citing words.json. They were
wrong, but only by luck of timing: words.json was written at 06:08, the patched vo.wav at
06:25, so the transcript on disk described audio that no longer existed. Nobody in the loop
could tell the difference, because nothing had listened to the delivered mix.

Two failure modes, one gap. A patch that silently does not land, and a stale transcript that
misrepresents a mix in either direction. Both are answered the same way: transcribe the file
we are shipping and read what it actually says.

This is deliberately narrow. It cannot judge truth. It re-uses the BANNED list from
vo_claims_check verbatim, so the two gates can never disagree about what is forbidden, and
it applies it to ASR output rather than to authored text.

Usage:
    python3 scripts/vo_audio_check.py                       # gate the delivered master
    python3 scripts/vo_audio_check.py --video path.mp4
    python3 scripts/vo_audio_check.py --write-words         # also refresh words.json

Exit 0 clean, 1 on a banned phrase, 0 with a SKIP if no ASR backend is installed (this must
never be the thing that halts a run; it is a truth check, not an availability check).
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")
sys.path.insert(0, os.path.join(REPO, "scripts"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", default=os.path.join(OUT, "dispatch_master.mp4"))
    ap.add_argument("--model", default="base")
    ap.add_argument("--write-words", action="store_true")
    a = ap.parse_args()

    if not os.path.exists(a.video):
        print(f"vo_audio_check: SKIP, {os.path.relpath(a.video, REPO)} does not exist yet")
        return 0
    try:
        from faster_whisper import WhisperModel
    except Exception as e:
        print(f"vo_audio_check: SKIP, no ASR backend available ({e.__class__.__name__})")
        return 0

    from vo_claims_check import BANNED

    import subprocess
    wav = os.path.join(OUT, "audio", "_shipcheck.wav")
    os.makedirs(os.path.dirname(wav), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-i", a.video, "-ac", "1", "-ar", "16000", wav, "-v", "error"],
                   check=True)

    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segs, _ = model.transcribe(wav, word_timestamps=False)
    segs = [(s.start, s.end, s.text.strip()) for s in segs]
    full = " ".join(t for _, _, t in segs)

    if a.write_words:
        json.dump([{"s": round(s, 2), "e": round(e, 2), "text": t} for s, e, t in segs],
                  open(os.path.join(OUT, "audio", "shipped_transcript.json"), "w"), indent=1)

    hits = []
    for pat, why in BANNED:
        # the dash/punctuation bans are about WRITTEN copy; ASR output has no typography,
        # so applying them here would only produce noise. Phrase bans are what matter.
        if pat in (r"[—–]", r"[;:]"):
            continue
        for m in re.finditer(pat, full, re.I):
            where = next((s for s, e, t in segs if re.search(pat, t, re.I)), None)
            hits.append((why, m.group(0), where))

    print(f"vo_audio_check: transcribed {len(segs)} segments, {len(full.split())} words "
          f"from {os.path.basename(a.video)}")
    if not hits:
        print("PASS [vo_audio_check] the delivered mix contains no banned phrase.")
        return 0

    print("FAIL [vo_audio_check] the AUDIO WE ARE SHIPPING says something the claim set bans.")
    for why, got, where in hits:
        at = f"{where:.2f}s" if isinstance(where, float) else "?"
        print(f"  {at}  heard '{got}': {why}")
    print()
    print("  The script being correct is not enough. Re-cut the line with")
    print("  scripts/vo_patch_lines.py and re-run this against the new master.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
