#!/usr/bin/env python3
"""Predict the VO runtime from the SCRIPT, before spending a synth on it.

WHY THIS EXISTS (2026-08-09, and it cost this run a full re-synth round).
-----------------------------------------------------------------------
config/state.yaml carries `dispatch_vo_words_band`, and the routine treats it as the length
control: write inside the band and the read lands inside `dispatch_seconds_band`. That works
for a script of ordinary sentence length and it silently does not work otherwise.

This run wrote 281 words, comfortably inside the 262 to 282 band, and the first synth came
back at 146.5 seconds against a 112 to 130 ceiling. Nothing was wrong with the prompt: the
Pace paragraph was verbatim, the model was the primary one, the take was clean. The script
simply had 35 SENTENCES in 281 words, because this film's voice is short and declarative, and
the required Pace paragraph instructs the reader to "take a real breath at every period". Every
period is therefore a cost, and a word band cannot see periods.

THE MODEL, and it is honestly a TWO-POINT FIT, not a study:

    seconds = 0.4345 * words + 0.6974 * sentences

Both points are real synths of this run, same voice, same model, same verbatim Pace paragraph:

    281 words / 35 sentences -> 146.5 s   (measured, take 0 of the first synth)
    257 words / 24 sentences -> 128.4 s   (measured, the delivered take)

Two points fix two coefficients exactly, so the fit reproduces its own inputs by construction
and that is not evidence. What it IS good for is the DIRECTION and the ROUGH SIZE of the
sentence cost, which is the thing the words band cannot express at all: about 0.7 seconds per
sentence, which is roughly a word and a half. A script of 270 words in 20 sentences and one of
270 words in 40 sentences differ by about 14 seconds, and that is most of the band.

TREAT THE OUTPUT AS A STEER, NOT A GATE. It exits 0 always, on purpose. It is here so a run
finds out before it pays for a synth, not so it can refuse one. Add a third and fourth measured
point to POINTS below whenever a run measures a take, and re-solve.

    python3 scripts/vo_length_estimate.py [path/to/vo_script.txt]
"""
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEFAULT = os.path.join(REPO, "out", "dispatch", "vo_script.txt")
STATE = os.path.join(REPO, "config", "state.yaml")

# (words, sentences, measured_seconds, note). Append every real measurement.
POINTS = [
    (281, 35, 146.5, "2026-08-09 take 0, first synth, over band"),
    (257, 24, 128.4, "2026-08-09 delivered take, in band"),
]
PER_WORD = 0.4345
PER_SENTENCE = 0.6974


def counts(text: str):
    words = len(text.split())
    # a sentence ends at . ! or ? — the units the Pace paragraph tells the reader to breathe at
    sentences = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
    return words, sentences


def band():
    """Read the bands out of state.yaml rather than restating them (the 2026-08-06 lesson:
    a number restated in a second place will be wrong in one of them)."""
    lo, hi = 112.0, 130.0
    wlo, whi = 262, 282
    try:
        import yaml
        d = yaml.safe_load(open(STATE)) or {}
        sb = d.get("dispatch_seconds_band") or [lo, hi]
        wb = d.get("dispatch_vo_words_band") or [wlo, whi]
        lo, hi = float(sb[0]), float(sb[1])
        wlo, whi = int(wb[0]), int(wb[1])
    except Exception:
        pass
    return lo, hi, wlo, whi


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.exists(path):
        print(f"vo_length_estimate: no script at {path}")
        return 0
    text = open(path).read()
    w, s = counts(text)
    lo, hi, wlo, whi = band()
    est = PER_WORD * w + PER_SENTENCE * s

    print(f"vo_length_estimate: {w} words, {s} sentences  ({w / max(1, s):.1f} words per sentence)")
    print(f"  words band {wlo}-{whi}: {'inside' if wlo <= w <= whi else 'OUTSIDE'}")
    print(f"  predicted runtime {est:.1f}s   seconds band {lo:.0f}-{hi:.0f}: "
          f"{'inside' if lo <= est <= hi else 'OUTSIDE'}")
    print(f"  model: {PER_WORD} s/word + {PER_SENTENCE} s/sentence, fitted on "
          f"{len(POINTS)} measured synths (a two-point fit, treat as a steer)")

    if est > hi:
        over = est - hi
        # a sentence costs about 1.6 words, so say which lever is cheaper for THIS script
        by_words = over / PER_WORD
        by_merge = over / PER_SENTENCE
        print(f"  OVER by {over:.1f}s. Either cut about {by_words:.0f} words, or merge about "
              f"{by_merge:.0f} sentence breaks into single clauses, or split the difference.")
        print("  MERGING IS USUALLY THE BETTER TRADE, because it costs no facts. Joining two "
              "short sentences with 'and', 'so' or 'because' also strengthens the causal chain "
              "Gate 0E grades, so it buys twice.")
    elif est < lo:
        print(f"  UNDER by {lo - est:.1f}s. There is room for a fact you were about to cut.")
    else:
        print("  Looks synthesisable as written. Synth it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
