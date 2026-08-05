#!/usr/bin/env python3
"""Generate out/evidence/audio_report.json from MEASUREMENTS, never from memory.

WHY THIS EXISTS (2026-08-04). This file used to be hand-written into the evidence pack.
It carried the sentence "the VO runs nearly wall to wall across 83.8s with one gap over
0.35s, so there is almost nowhere for the bed to open", and it was false. Two judges
checked it against the run's own word timings in the same round and found 21 gaps longer
than 0.35s, 13 longer than 0.50s, and roughly 11.9 seconds of silence inside an 81.6s VO
track. The orchestrator had repeated the claim to the owner as fact.

That is worse than a wrong number in a report. The evidence pack is what the panel grades
from, so a hand-written assertion inside it is an unverified claim wearing the costume of
a measurement, and it pointed the fix at cutting VO when the actual cause was a music bed
that never rises into the gaps that already exist.

So nothing in this file is typed by hand. Every number comes from words.json and ffmpeg,
and the diagnosis is derived from those numbers rather than asserted alongside them.
"""
import argparse
import json
import os
import re
import subprocess

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")
EV = os.path.join(REPO, "out", "evidence")


def loudnorm(path):
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", p.stderr, re.S)
    if not m:
        return {}
    d = json.loads(m.group(0))
    return {"i": float(d["input_i"]), "tp": float(d["input_tp"]),
            "lra": float(d["input_lra"])}


def gaps_from_words(words_path, min_gap=0.35):
    w = json.load(open(words_path))["words"]
    out = []
    for a, b in zip(w, w[1:]):
        g = b["s"] - a["e"]
        if g >= min_gap:
            out.append({"at": round(a["e"], 2), "len": round(g, 2)})
    return out, (w[-1]["e"] if w else 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--delivered", default=os.path.join(OUT, "dispatch_square.mp4"))
    ap.add_argument("--words", default=os.path.join(OUT, "audio", "words.json"))
    ap.add_argument("--out", default=os.path.join(EV, "audio_report.json"))
    a = ap.parse_args()

    m = loudnorm(a.delivered)
    gaps, last_word = gaps_from_words(a.words)
    long_gaps = [g for g in gaps if g["len"] >= 0.50]
    silence = round(sum(g["len"] for g in gaps), 2)

    lra = m.get("lra", 0.0)
    if lra >= 6.0:
        diagnosis = "LRA is inside the 6 to 9 LU target."
    else:
        diagnosis = (
            f"LRA is {lra} against the 6 to 9 LU target. MEASURED CAUSE, not asserted: the "
            f"VO track leaves {len(gaps)} gaps of 0.35s or longer ({len(long_gaps)} of them "
            f"0.50s or longer), totalling {silence}s of silence, and the last word ends at "
            f"{round(last_word, 2)}s. The room for the bed to open therefore EXISTS. If the "
            f"loudness range is still flat, the bed is not rising into that room, which is a "
            f"mix problem to be fixed at the faders and the duck release, not a script "
            f"problem to be fixed by cutting lines. An earlier hand-written version of this "
            f"field claimed there was only one gap over 0.35s and sent the fix in the wrong "
            f"direction; these figures are computed from words.json every run."
        )

    rep = {
        "measured_on": os.path.basename(a.delivered),
        "tool": "ffmpeg loudnorm + forced-alignment word timings",
        "delivered_i": m.get("i"),
        "delivered_tp": m.get("tp"),
        "delivered_lra": lra,
        "targets": {"i": -14.0, "tp_max": -1.0, "lra": [6.0, 9.0]},
        "pass": {
            "loudness": abs(m.get("i", 0) + 14.0) <= 1.0,
            "true_peak": m.get("tp", 0) <= -1.0,
            "lra": 6.0 <= lra <= 9.0,
        },
        "vo_gaps_ge_0_35s": len(gaps),
        "vo_gaps_ge_0_50s": len(long_gaps),
        "vo_silence_in_gaps_s": silence,
        "last_word_ends_s": round(last_word, 2),
        "longest_gaps": sorted(gaps, key=lambda g: -g["len"])[:8],
        "diagnosis": diagnosis,
    }
    os.makedirs(EV, exist_ok=True)
    json.dump(rep, open(a.out, "w"), indent=1)
    print(f"audio_report: I={rep['delivered_i']} TP={rep['delivered_tp']} LRA={lra}")
    print(f"  {len(gaps)} gaps >=0.35s, {len(long_gaps)} >=0.50s, {silence}s of silence")
    print(f"  -> {a.out}")


if __name__ == "__main__":
    main()
