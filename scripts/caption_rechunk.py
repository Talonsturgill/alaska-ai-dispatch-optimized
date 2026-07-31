#!/usr/bin/env python3
"""RE-BREAK CAPTION CUES ON PHRASES, IN PLACE, WITHOUT RE-ALIGNING ANYTHING.

WHY THIS EXISTS (2026-07-31, panel round 10).

Judge 3: "the caption chunker orphans nearly every sense unit -- 'Alaska has a patchwork,
not a', 'New York's covers only the biggest', 'His has no size limit and', 'comes from, not
on whether the'." Roughly two thirds of cues ended mid-phrase. The cause was in
dispatch_captions.py, which filled a cue to a character budget and then cut wherever the cut
landed, and that is fixed there for every future run.

This run cannot simply re-run that script: it force-aligns from per-line wavs that this
run's surgical VO patch consumed, and out/dispatch/audio/words.json predates the patch. Re-
deriving the alignment to fix a display-only defect would risk the thing that is currently
correct (sync) to improve the thing that is currently wrong (line breaks).

So this tool does the smallest correct thing. It never re-times a word and never changes a
single character of caption text. It only moves DANGLING TRAILING WORDS from the end of one
cue to the head of the next, within the same VO line, and moves the boundary timestamp with
them, allocating the moved time proportionally to the characters moved. A word is dangling
if it cannot end a phrase: an article, preposition, conjunction, auxiliary or possessive.

The guarantees, asserted at the end:
  - the concatenated text of all cues is byte-identical before and after
  - cue starts remain monotonic and no cue overlaps its neighbour
  - no cue is left shorter than MIN_DWELL

  python3 scripts/caption_rechunk.py [--in out/dispatch/captions.json]
"""
import argparse, json, os, re

# A word that cannot end a phrase. Round 12 came back with nine mid-unit breaks still
# burned in after the first pass, and every one of them was a class this set did not cover:
# a bare numeral before its unit ("a fifty | year lease", which splits a compound number), a
# superlative before its noun ("only the biggest | sites"), a determiner-like quantifier
# ("before writing any | statute"), and transitive verbs left without their object
# ("Anchorage requires | proof", "New York's covers only the biggest"). Judges counted these
# off delivered frames twice, so the set is written from what they actually found rather
# than from what felt likely.
DANGLING = {
    # determiners and function words
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "for", "from",
    "with", "by", "as", "that", "than", "if", "so", "since", "while", "not", "no",
    "is", "was", "are", "were", "it", "its", "his", "her", "their", "this", "these",
    "what", "when", "where", "who", "one", "up", "into", "onto", "about", "over",
    "any", "every", "each", "both", "more", "most", "fewer", "less", "own", "same",
    "there's", "here's", "it's", "he's", "she's", "they're", "we're",
    # numerals and number words, which must never be cut from their unit
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
    "twelve", "fifteen", "seventeen", "twenty", "thirty", "forty", "fifty", "hundred",
    "thousand", "million", "billion",
    # superlatives and comparatives that modify a following noun
    "biggest", "largest", "smallest", "only", "first", "last", "next", "other", "whole",
    # auxiliaries, which never end a clause
    "have", "has", "had", "be", "been", "being", "do", "does", "did", "will", "can",
    "could", "should", "would", "must", "may", "might",
    # negated auxiliaries, which are the same class wearing an apostrophe
    "doesn't", "don't", "didn't", "isn't", "aren't", "wasn't", "weren't", "won't",
    "can't", "couldn't", "shouldn't", "wouldn't", "hasn't", "haven't", "hadn't",
    # complementizers and adverbs that point forward at what has not arrived yet
    "whether", "instead", "because", "although", "unless", "until", "before", "after",
    "rather", "either", "neither", "such", "how", "why", "which",
}
# NOT transitive verbs. The obvious next move after judge 3 listed "Anchorage requires |
# proof" was to add requires/covers/says to the set. That was tried and made the film worse:
# pushing the verb forward strands its SUBJECT at the end of the previous cue, so
# "And since March, Anchorage requires" became "And since March, Anchorage", which is a
# worse break, not a better one. A cue ending on a verb still ends on a complete
# subject-plus-verb; a cue ending on a bare subject ends on nothing. Left out deliberately.
MIN_DWELL = 0.42          # a cue this short is a flash, not a caption
MIN_KEEP_WORDS = 2        # never strip a cue down past this


def dangling(word: str) -> bool:
    w = re.sub(r"^[\"'(\[]+|[\"')\]]+$", "", word).lower()
    if re.search(r"[.!?,;:]$", w):     # punctuation ends a phrase, so it is never dangling
        return False
    if re.fullmatch(r"[\d.,]+", w):    # a bare figure always belongs with its unit
        return True
    return w in DANGLING


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="out/dispatch/captions.json")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    raw = json.load(open(a.src))
    cues = raw["cues"] if isinstance(raw, dict) and "cues" in raw else raw
    before_text = " ".join(c["text"] for c in cues)

    moved = 0
    for i in range(len(cues) - 1):
        cur, nxt = cues[i], cues[i + 1]
        if cur.get("seg") != nxt.get("seg"):
            continue                       # never move a word across a spoken line
        words = cur["text"].split()
        tail = []
        while len(words) > MIN_KEEP_WORDS and dangling(words[-1]):
            tail.insert(0, words.pop())
        if not tail:
            continue

        span = cur["end"] - cur["start"]
        if span <= 0:
            continue
        # allocate the boundary by characters, which is the best proxy available without
        # per-word timings, and refuse the move if it would starve either cue
        kept_chars = len(" ".join(words))
        total_chars = kept_chars + 1 + len(" ".join(tail))
        new_end = cur["start"] + span * (kept_chars / total_chars)
        if new_end - cur["start"] < MIN_DWELL or nxt["end"] - new_end < MIN_DWELL:
            continue

        cur["text"] = " ".join(words)
        cur["end"] = round(new_end, 3)
        nxt["text"] = " ".join(tail + nxt["text"].split())
        nxt["start"] = round(new_end, 3)
        moved += len(tail)

    # A REPAIR PASS, BECAUSE MOVING A WORD FORWARD CAN STRAND WHAT IS LEFT BEHIND.
    #
    # Moving "requires" off the end of "And since March, Anchorage requires" leaves "And
    # since March, Anchorage", which ends on a bare subject and is a worse break than the one
    # it replaced. The same happens whenever the words before the moved one do not form a
    # clause on their own. So after the moves, any cue that is short, ends without
    # punctuation, and would still fit inside the reading budget when joined to its
    # neighbour is merged back into it. That is strictly better than either break: no split
    # at all.
    MERGE_MAX_CHARS, MERGE_MAX_WORDS = 46, 8
    out = []
    for c in cues:
        if (out and out[-1].get("seg") == c.get("seg")
                and not re.search(r"[.!?]$", out[-1]["text"])
                and len(out[-1]["text"].split()) <= 4
                and len(out[-1]["text"]) + 1 + len(c["text"]) <= MERGE_MAX_CHARS
                and len(out[-1]["text"].split()) + len(c["text"].split()) <= MERGE_MAX_WORDS):
            out[-1]["text"] += " " + c["text"]
            out[-1]["end"] = c["end"]
            continue
        out.append(c)
    # When a merge does not fit, pull ONE word back instead. A short cue stranded on a bare
    # subject is better served by taking its verb than by taking nothing, which is exactly the
    # state the move pass took it out of. This is the inverse operation and it is bounded to a
    # single word, so the two passes cannot ping-pong.
    pulled = 0
    for i in range(len(out) - 1):
        cur, nxt = out[i], out[i + 1]
        if (cur.get("seg") != nxt.get("seg")
                or re.search(r"[.!?]$", cur["text"])
                or len(cur["text"].split()) > 4):
            continue
        nw = nxt["text"].split()
        if len(nw) < 3 or dangling(nw[0]):
            continue
        span = nxt["end"] - nxt["start"]
        take_chars = len(nw[0]) + 1
        shift = span * (take_chars / max(1, len(nxt["text"])))
        if span - shift < MIN_DWELL:
            continue
        cur["text"] += " " + nw[0]
        cur["end"] = round(cur["end"] + shift, 3)
        nxt["text"] = " ".join(nw[1:])
        nxt["start"] = cur["end"]
        pulled += 1

    merged_back = len(cues) - len(out)
    cues[:] = out
    if isinstance(raw, dict) and "cues" in raw:
        raw["cues"] = out
    else:
        raw = out

    after_text = " ".join(c["text"] for c in cues)
    assert after_text == before_text, "caption TEXT changed; this tool may only re-break it"
    for x, y in zip(cues, cues[1:]):
        assert y["start"] >= x["end"] - 1e-6, f"cue overlap at {x['text']!r}"
        assert x["end"] - x["start"] >= MIN_DWELL - 1e-6, f"cue too short: {x['text']!r}"

    print(f"re-broke {moved} dangling word(s); merged {merged_back} and repaired {pulled} stranded cue(s); {len(cues)} cues")
    for c in cues[:12]:
        print(f"  {c['start']:6.2f} {c['text']}")
    if a.dry_run:
        print("(dry run, nothing written)")
        return
    json.dump(raw, open(a.src, "w"), indent=1)
    print(f"wrote {a.src}")


if __name__ == "__main__":
    main()
