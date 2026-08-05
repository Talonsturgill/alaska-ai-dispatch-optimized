#!/usr/bin/env python3
"""Rebuild captions.json from forced-aligned word timings AND the intended script.

WHY THIS EXISTS (2026-08-04). scripts/dispatch_captions.py does this job but assumes
vo_script.json["lines"] is a list of plain strings and that every line still has its own
vo_line_NN.wav on disk. This run's script is a list of {i, act, t} objects and the per
line wavs are gone after a patch pass, so that tool cannot run and the only other
alignment tool, align_captions.py, emits the WORDS file rather than the cue list. There
was no path from "the audio changed" back to "captions.json".

The rule this file exists to enforce: caption TEXT comes from the script, caption TIMING
comes from the audio. Whisper's transcript is used for nothing except placing the words
in time. Reading the text off the transcript is how "A prescribed burn" ships as
"prescribed burn" and "who pays when a burn escapes" ships as "a fire escapes": the ASR
drops and substitutes words, and a caption that disagrees with the voice is a hard
blocker in the rubric.

A cue never spans two VO lines, because build_scenes.py anchors every shot boundary to a
line start and the rebalancer refuses to merge across one.
"""
import argparse, difflib, json, os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")

MAX_WORDS = 7
MAX_CHARS = 62


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", default=os.path.join(OUT, "audio", "words.json"))
    ap.add_argument("--script", default=os.path.join(OUT, "vo_script.json"))
    ap.add_argument("--lines", default=os.path.join(OUT, "vo_lines.json"))
    ap.add_argument("--out", default=os.path.join(OUT, "captions.json"))
    a = ap.parse_args()

    heard = json.load(open(a.words))["words"]
    script = {l["i"]: l["t"] for l in json.load(open(a.script))["lines"]}
    lines = json.load(open(a.lines))["lines"]

    cues = []
    for L in lines:
        idx, s0, s1 = L["idx"], L["start"], L["end"]
        intended = script[idx].split()
        if not intended:
            continue
        hw = [w for w in heard if s0 - 0.02 <= w["s"] < s1 + 0.02]

        # map intended tokens onto heard timings; anything the ASR dropped or renamed
        # gets a time interpolated between its nearest matched neighbours, so the text
        # stays verbatim and the timing stays honest
        times = [None] * len(intended)
        if hw:
            sm = difflib.SequenceMatcher(
                None, [norm(t) for t in intended], [norm(w["w"]) for w in hw])
            for i, j, n in sm.get_matching_blocks():
                for k in range(n):
                    times[i + k] = (hw[j + k]["s"], hw[j + k]["e"])
        known = [i for i, t in enumerate(times) if t]
        if not known:
            step = (s1 - s0) / len(intended)
            times = [(s0 + i * step, s0 + (i + 1) * step) for i in range(len(intended))]
        else:
            for i in range(len(times)):
                if times[i]:
                    continue
                lo = max([k for k in known if k < i], default=None)
                hi = min([k for k in known if k > i], default=None)
                if lo is None:
                    times[i] = (s0, times[hi][0])
                elif hi is None:
                    times[i] = (times[lo][1], s1)
                else:
                    span = (times[hi][0] - times[lo][1]) / (hi - lo)
                    times[i] = (times[lo][1] + (i - lo - 1) * span,
                                times[lo][1] + (i - lo) * span)

        # chunk WITHIN the line, breaking after sentence punctuation
        cur = []
        for i, tok in enumerate(intended):
            cur.append(i)
            txt = " ".join(intended[c] for c in cur)
            ends_sentence = tok.endswith((".", "!", "?"))
            nxt = " ".join(intended[c] for c in cur + [i + 1]) if i + 1 < len(intended) else ""
            # never break between two capitalised words: "the National Science" /
            # "Foundation obligated" tears a proper noun across cards, and the eye
            # finishes the first card before the second arrives.
            nxt_tok = intended[i + 1] if i + 1 < len(intended) else ""
            in_proper_run = (tok[:1].isupper() and nxt_tok[:1].isupper()
                             and not ends_sentence and len(nxt) <= MAX_CHARS + 8)
            if (not in_proper_run
                    and (ends_sentence or len(cur) >= MAX_WORDS
                         or (nxt and len(nxt) > MAX_CHARS))) or i == len(intended) - 1:
                cues.append({"text": txt,
                             "start": round(times[cur[0]][0], 2),
                             "end": round(times[cur[-1]][1], 2),
                             "seg": idx})
                cur = []

    # a cue must not start before the previous one ends
    for i in range(1, len(cues)):
        if cues[i]["start"] < cues[i - 1]["end"]:
            cues[i]["start"] = cues[i - 1]["end"]
        if cues[i]["end"] <= cues[i]["start"]:
            cues[i]["end"] = cues[i]["start"] + 0.4
    # NO BLINK-OUTS. Each card holds until the next one starts, so the caption band
    # never empties between VO segments. A judge counted sixteen 0.2s to 0.7s blackouts
    # in 84 seconds, which reads as flicker on a muted phone play.
    for i in range(len(cues) - 1):
        cues[i]["end"] = round(cues[i + 1]["start"], 2)

    json.dump(cues, open(a.out, "w"), indent=1)
    print(f"wrote {len(cues)} cues -> {a.out}")
    for c in cues[:6]:
        print(f"  {c['start']:6.2f} seg{c['seg']:<3} {c['text']!r}")


if __name__ == "__main__":
    main()
