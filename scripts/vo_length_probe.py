#!/usr/bin/env python3
"""VO LENGTH PROBE — measure, do not reason, before changing the format's runtime.

WHY THIS EXISTS (2026-08-05, the 90s -> 120s upgrade). Every runtime change in this
repo rests on one unverified assumption: that Gemini native TTS will render a script
of the new length in ONE call without truncating, and that whole-file forced alignment
still produces monotonic timings over the longer take. The whole pipeline is a single
synth call and a single alignment pass, so a truncation at 120 seconds does not fail
loudly. It ships a short film with captions and scene cuts pointing at words that were
never spoken.

That risk cannot be retired by argument, only by a take. So this script renders the
probe script below at the proposed length, runs the real soundcheck on it, runs the
REAL alignment function out of vo_synth_gemini, and prints the four numbers that
decide whether the format change is safe:

  duration          does the read land in the proposed band
  WER               did anything get dropped or truncated
  alignment span    does the alignment cover the whole take, monotonically
  cue count         does the caption cutter still produce sane cues

It also prints words-per-minute, which is the number every word band is derived from
and which this repo has twice recorded wrong.

It writes to out/probe/ and NEVER touches out/dispatch/, so it is safe to run during a
live run.

USAGE
  python3 scripts/vo_length_probe.py                 # 2 takes at the default script
  python3 scripts/vo_length_probe.py --takes 3
  python3 scripts/vo_length_probe.py --script my.txt # one spoken line per line

THE PROMPT IS ASSEMBLED PER docs/craft/VO_DIRECTION.md STEP 7, IN FULL. Probing with a
prompt that differs from the one a run uses measures nothing about a run. The 2026-08-05
take was synthesized from a prompt whose preamble, director's notes and Pace line had
been destroyed by a bad string patch, and it read 161.5 wpm against a house rate of
~139, which is a 16 percent error in the direction that overruns the runtime ceiling.
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(REPO, "out", "probe")

# The probe script. REAL PROSE FROM A SHIPPED FILM, not invented filler: the 2026-08-05
# narration (232 spoken words) extended with the fair-objection material that ran in that
# run's verified post copy. Real numbers, real proper nouns, real sentence lengths, so the
# phonetics and the pacing are representative of what a run actually asks for. Filler
# would measure the wrong thing.
PROBE_LINES = [
    "[curious] Alaska might hold thirty thousand kinds of insect.",
    "It has names for about nine thousand.",
    "The strange part isn't the gap. [short pause] Somebody already built a machine to close it.",
    "Derek Sikes runs the insect collection at Alaska's Museum of the North.",
    "Since two thousand six its catalog went from one thousand entries to four hundred thousand.",
    "Those entries cover about two million pinned insects, each logged the day it arrives.",
    "Sequence one, and if it matches nothing in the world's databases, you might be holding something new.",
    "The Anchorage Daily News profiled him this week. [wry] This part wasn't in it.",
    "In two thousand eight, a study taught a neural network to name species from a gene.",
    "Ninety seven point five percent, on eighty unknown ground beetles.",
    "That's the machine. [short pause] One of its four authors was Derek Sikes.",
    "Eighteen years on, Alaska's list grows about a thousand species a decade.",
    "Twenty one thousand unnamed, at a thousand a decade. Two hundred ten years.",
    "So the model was never what was holding this up.",
    "A classifier needs a D N A sequence. A sequence needs a specimen.",
    "And a specimen needs somebody in a field with a net.",
    "Every one of those steps is a person, a season, and a budget line.",
    "Now push back on me here, because there is a fair objection.",
    "A two thousand eight network, tested on two well studied groups, is not a twenty twenty six model.",
    "[short pause] Nobody has run a modern one at this problem, and I'm not going to pretend otherwise.",
    "It still points somewhere useful.",
    "Those two million insects are what any future method has to read first.",
    "So what should Alaska buy. A smarter model, or another summer in the field?",
]

PREAMBLE = ('Read ONLY the transcript below aloud as speech. The lines above "Transcript:" '
            "are direction; never speak them.")
PROFILE = ("# AUDIO PROFILE: Nora, an Alaska public-radio host: warm, grounded, quietly witty. "
           "Neutral American accent, light and natural, not announcer-y.")
STYLE = ("Style: warm, grounded and genuinely curious, like a smart friend showing you the part of a "
         "newspaper profile that wasn't in it. Let the facts carry the irony instead of announcing it. "
         "Never cynical, never a gotcha.")
EMPHASIS = "Emphasis: lean on the key word in each line; let numbers land."

# THE PACE LINE IS THE VARIABLE UNDER TEST. `brisk` is the house default, used verbatim by
# every archived run. `anchored` adds an explicit runtime target, the technique 2026-08-03
# used, to test whether naming a duration actually slows the read or is merely decorative.
PACE_MODES = {
    "brisk": ("Pace: BRISK and energetic, keep it moving like a sharp modern explainer. Short "
              "natural breaths only, no long pauses, do not drag. Vary the tone line to line so "
              "no two sentences sound the same."),
    "anchored": ("Pace: MEASURED and unhurried. THIS IS A TWO MINUTE PIECE, about one hundred and "
                 "twenty seconds, and the read must FILL it, so give every sentence room to land "
                 "and take a real breath at every period. Do not rush the numbers. Vary the tone "
                 "line to line so no two sentences sound the same."),
}


def assemble(lines, pace_mode="brisk"):
    notes = "\n".join(["### DIRECTOR'S NOTES", STYLE, PACE_MODES[pace_mode], EMPHASIS])
    return "\n".join([PREAMBLE, PROFILE, notes, "Transcript:", *lines])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--takes", type=int, default=2)
    ap.add_argument("--script", help="file with one spoken line per line; defaults to PROBE_LINES")
    ap.add_argument("--band", default="112,130", help="proposed runtime band, lo,hi")
    ap.add_argument("--pace", default="brisk", choices=sorted(PACE_MODES),
                    help="which Pace line to put in the director's notes")
    ap.add_argument("--tag", default="", help="suffix for the take/report filenames")
    a = ap.parse_args()

    lo, hi = [float(x) for x in a.band.split(",")]
    raw = [l.strip() for l in open(a.script).read().strip().split("\n") if l.strip()] \
        if a.script else list(PROBE_LINES)

    import vo_soundcheck as sc
    import vo_synth_gemini as vs

    spoken = [re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", l)).strip() for l in raw]
    nwords = sum(len(s.split()) for s in spoken)
    prompt = assemble(raw, a.pace)
    tags = sorted(set(re.findall(r"\[[^\]]*\]", " ".join(raw))))

    os.makedirs(OUT, exist_ok=True)
    print(f"PROBE: {len(raw)} lines, {nwords} spoken words, proposed band {lo:.0f}-{hi:.0f}s, "
          f"pace mode {a.pace!r}")
    print(f"       prompt {len(prompt)} chars, delimiter present: {chr(10)+'Transcript:'+chr(10) in prompt}")
    print(f"       implied rate to land at 120.0s: {nwords / 120.0 * 60:.1f} wpm\n")

    results = []
    for n in range(a.takes):
        wav = os.path.join(OUT, f"probe{a.tag}_take_{n}.wav")
        if os.path.exists(wav) and os.environ.get("PROBE_REUSE") == "1":
            print(f"take {n}: reused")
        else:
            pcm, used = vs._synth_retry(prompt)
            vs._save_24k(pcm, wav)
            print(f"take {n}: {len(pcm)/24000:.1f}s raw audio ({used})")
        # generous window so the probe REPORTS the duration instead of failing on it
        rep = sc.check(wav, " ".join(spoken), tags, dur_lo=20.0, dur_hi=300.0)
        c = rep["checks"]
        dur = c["duration"]["seconds"]
        results.append({
            "take": n, "seconds": dur, "wpm": round(nwords / dur * 60, 1),
            "wer": c["word_accuracy"]["wer"], "words_ok": c["word_accuracy"]["pass"],
            "leaked": c["no_leak"]["leaked"], "lufs": c["loudness"]["lufs"],
            "pitch_std": c["expressive"]["pitch_std_semitones"], "in_band": lo <= dur <= hi,
            # THE TRANSCRIPT IS EVIDENCE, NOT A DETAIL. A raw WER number cannot tell a real
            # TTS defect from an ASR/normalization artifact, and on 2026-08-05 the whole
            # question of whether 288 words was safe turned on that distinction: two takes
            # tripped the WER ceiling entirely on year-normalization artifacts, and one
            # "leaked tag" was whisper mishearing "profiled him" as "profile tim". Saving
            # what was actually heard makes the next diagnosis a diff instead of a re-run.
            "heard": rep["heard"],
        })
        print(f"  -> {dur:.1f}s  {nwords/dur*60:.1f} wpm  WER {c['word_accuracy']['wer']}  "
              f"leaks {c['no_leak']['leaked']}  "
              f"{'IN BAND' if lo <= dur <= hi else 'OUT OF BAND'}")

    # ---- alignment, on the take closest to the band's midpoint ----
    mid = (lo + hi) / 2
    best = min(results, key=lambda r: abs(r["seconds"] - mid))
    src = os.path.join(OUT, f"probe{a.tag}_take_{best['take']}.wav")
    print(f"\nALIGNMENT on take {best['take']} ({best['seconds']:.1f}s), the closest to {mid:.0f}s")
    from scipy.io import wavfile
    _, pcm24 = wavfile.read(src)
    wav44 = os.path.join(OUT, f"probe{a.tag}_44k.wav")
    wavfile.write(wav44, vs.SR, vs._to_44k_int16(pcm24))
    words, spans, total, cues = vs._align_wholefile(wav44, spoken)

    starts = [w["s"] for w in words]
    monotonic = all(starts[i] <= starts[i + 1] for i in range(len(starts) - 1))
    covered = [s for s in spans]
    gaps = [round(covered[i + 1]["start"] - covered[i]["end"], 2) for i in range(len(covered) - 1)]
    align = {
        "aligned_words": len(words), "script_words": nwords,
        "lines_timed": len(spans), "lines_total": len(spoken),
        "speech_end": round(total, 2), "first_word_at": round(starts[0], 2),
        "monotonic": monotonic, "cues": len(cues),
        "max_line_gap_s": max(gaps) if gaps else 0.0,
        "cue_min_dwell_s": round(min(c["end"] - c["start"] for c in cues), 2),
        "degenerate_cues": sum(1 for c in cues if c["end"] <= c["start"]),
    }
    for k, v in align.items():
        print(f"  {k}: {v}")

    verdict = []
    if not all(r["words_ok"] for r in results):
        verdict.append("FAIL: a take dropped or garbled words (possible truncation).")
    if align["lines_timed"] != align["lines_total"]:
        verdict.append("FAIL: alignment did not time every line.")
    if not monotonic:
        verdict.append("FAIL: alignment is not monotonic at this length.")
    if align["degenerate_cues"]:
        verdict.append("FAIL: degenerate caption cues.")
    if align["speech_end"] < min(r["seconds"] for r in results) * 0.9:
        verdict.append("FAIL: alignment covers less than 90 percent of the take (truncation "
                       "or a whisper drop-out).")
    if not any(r["in_band"] for r in results):
        verdict.append(f"WARN: no take landed in {lo:.0f}-{hi:.0f}s; re-derive the word band.")

    print("\nVERDICT: " + ("\n         ".join(verdict) if verdict
                           else f"PASS. {nwords} words synthesizes in one call, aligns cleanly, "
                                f"and reads at {sum(r['wpm'] for r in results)/len(results):.1f} wpm mean."))
    json.dump({"words": nwords, "lines": len(raw), "band": [lo, hi], "pace_mode": a.pace,
               "takes": results,
               "alignment": align, "verdict": verdict or ["PASS"]},
              open(os.path.join(OUT, f"probe{a.tag}_report.json"), "w"), indent=2)
    print(f"\nwrote {os.path.join(OUT, 'probe_report.json')}")


if __name__ == "__main__":
    main()
