#!/usr/bin/env python3
"""VO CLAIMS CHECK — does the NARRATION obey the fact-check-safe set?

WHY THIS EXISTS (2026-08-08).

On this run the caption scorer found a hard fail in the LinkedIn post: the copy said the
X-ray machines went to "five rural clinics that didn't have one". That is an inference.
The claim record (c4) supports only "portable X-ray machines for five rural clinics", and
claims.json explicitly bans any imaging-absence claim, because the only source for it is a
single first-person essay three years old. It was also the one invented detail attached to
an Alaska Native nonprofit, which is where the claim set is strictest.

The same sentence was in the NARRATION, and by the time the scorer found it the voice had
already been synthesized. It cost two rounds of surgical line patching to remove.

The gap is structural, not a lapse. The caption is gated by a scorer that reads claims.json.
The VO script is gated by Gate 0E, which asks whether a STRANGER CAN FOLLOW IT, and by the
soundcheck, which asks whether the ASR heard the right words. Nothing between the writers
room and the TTS ever compares the script to the EVIDENCE. So a false line can pass every
gate the pipeline has and reach synthesis.

This closes that. It is deliberately mechanical and deliberately narrow: it cannot judge
whether a sentence is true, so it checks the two things a machine CAN check.

  1. OBLIGATIONS. Every claims.json claim carries a `requires` block, written by the
     fact-checker, listing what the film must do to use it honestly. Where an obligation
     names a word the line must contain (STUDY, IN THIS ROUND, YEAR ONE, JUNE 2026...), a
     line citing that claim must contain it. Where an obligation BANS a form, the line must
     not contain it.
  2. UNSOURCED QUANTIFICATION. A line that states a number, a proportion or a superlative
     and cites NO claim id is an assertion the record has not been asked about. That is
     exactly the shape of the line that got through.

Usage:
    python3 scripts/vo_claims_check.py            # exit 1 on any violation
    python3 scripts/vo_claims_check.py --list     # print what it derived, exit 0

It reads the SCRIPT, so it runs BEFORE a second of TTS is spent, which is the whole point.
"""
import json, re, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(REPO, "out", "dispatch")

# An obligation phrased in the fact-checker's own words maps to a token the line must
# carry. Keys are matched case-insensitively inside the `requires` text.
MUST_CONTAIN = [
    ("must be on screen and in the vo", None),      # handled by the explicit pairs below
    ("the word study must be on screen", "study"),
    ("with study on screen", "study"),
    ("in this round", "this round"),
    ("label it year one", "year one"),
    ("is labelled year one", "year one"),
    ("must appear on screen with the quote, and the vo must place her in june", "june"),
    ("the vo must place her in june", "june"),
]

# Forms a line may never take, phrased as (regex, why). These come straight out of the
# claim set's own kill list and its `requires` prohibitions.
BANNED = [
    (r"\bcannot\b", "the word 'cannot' is banned; use can't"),
    (r"[—–]", "em or en dash"),
    (r"[;:]", "semicolon or colon"),
    (r"\btribal consortium\b", "Chugachmiut may not be called a tribal consortium (unverified)"),
    (r"didn'?t have one", "an imaging-absence claim; the record does not support it"),
    (r"\blacked\b.{0,24}\b(x[- ]?ray|imaging)\b", "an imaging-absence claim"),
    (r"\bAI scheduling\b", "the scheduling system carries no technology descriptor in the source"),
    (r"\b1\.65\s*%|\b1\.65 percent", "must stay 'under two percent'; the numerator is 'over $4.5M'"),
    (r"\$?4,500,000|four million five hundred thousand", "must stay 'over four and a half million'"),
]

# A line that quantifies. Bare years and ordinal dates are not quantification.
QUANT = re.compile(
    r"\b(hundred|thousand|million|billion|percent|per cent|twice|three times|four times|"
    r"half|most|fewest|largest|smallest|only one|not one|exactly once|every|all of)\b", re.I)
DATEISH = re.compile(r"\b(august|june|july|september|friday|monday|year one)\b", re.I)

# 3. UNSOURCED CADENCE (2026-08-13). QUANT catches numbers, proportions and superlatives, and a
# RATE is none of those, so "The aim is a new one any hour" passed this gate clean while
# asserting a refresh frequency no claim in the file carries. Two judges reported it, three
# rounds apart, and the run shipped the video anyway and told the owner it "needs a single-line
# re-synth" -- i.e. handed over a knowingly wrong narration and deferred the fix. The owner's
# answer: "why would u give me a video, and say it needs a resynth, who's gonna do that?"
#
# A cadence is a factual assertion about how often something happens. It is exactly as
# load-bearing as a number and it was the one shape of claim nothing here was reading.
CADENCE = re.compile(
    r"\b(any hour|every hour|each hour|hourly|per hour|a minute|per minute|every minute|"
    r"every day|each day|daily|per day|every second|per second|continuously|"
    r"in real time|round the clock|constantly|on demand|any time)\b", re.I)


def _span_ids(lines, cid):
    """The line indices citing this claim, plus one line either side, as a string."""
    hits = [l["idx"] for l in lines if cid in (l.get("claims") or [])]
    if not hits:
        return "-"
    lo, hi = max(0, min(hits) - 1), min(len(lines) - 1, max(hits) + 1)
    return f"{lo}..{hi}"


def _claim_span(lines, cid):
    """Lowercased text of every line citing this claim, plus its immediate neighbours."""
    hits = [l["idx"] for l in lines if cid in (l.get("claims") or [])]
    if not hits:
        return ""
    lo, hi = max(0, min(hits) - 1), min(len(lines) - 1, max(hits) + 1)
    return " ".join(l["text"].lower() for l in lines if lo <= l["idx"] <= hi)


def main():
    show = "--list" in sys.argv
    script = json.load(open(os.path.join(OUT, "vo_script.json")))
    claims_doc = json.load(open(os.path.join(OUT, "claims.json")))
    claims = {c["id"]: c for c in claims_doc["claims"]}

    problems, notes = [], []
    for line in script["lines"]:
        idx, text = line["idx"], line["text"]
        cited = [c for c in line.get("claims", []) if c in claims]
        low = text.lower()

        for pat, why in BANNED:
            if re.search(pat, text, re.I):
                problems.append(f"L{idx}: {why}\n      {text}")

        # Obligations are satisfied across the CLAIM'S SPAN, not line by line. The
        # first build of this gate checked each line alone and fired on "Mina read the
        # pressure right" for not containing "June", although the line that introduces
        # her says "In June" two lines earlier. A guard that fires on a correct script
        # gets disabled, so the clause is loosened rather than the guard removed.
        for cid in cited:
            span = _claim_span(script["lines"], cid)
            for req in claims[cid].get("requires", []):
                rl = req.lower()
                for needle, token in MUST_CONTAIN:
                    if token and needle in rl and token not in span:
                        problems.append(
                            f"{cid} obligation not met ANYWHERE in the lines that cite it:\n"
                            f"        {req}\n"
                            f"      no line in the claim's span contains '{token}'. "
                            f"Span is L{_span_ids(script['lines'], cid)}.")

        # A CITED LINE IS NOT A SOURCED CADENCE. "The aim is a new one any hour" carries a claim
        # id and that claim says nothing about hours, so a `not cited` test passes it. For a rate
        # the citation has to actually CONTAIN the rate: the cadence words, or an equivalent, must
        # appear in the claim's own verbatim_source. Anything else is the film borrowing a claim's
        # credibility for an assertion the claim never made.
        m = CADENCE.search(text)
        if m:
            word = m.group(0).lower()
            backing = " ".join(
                str(claims[c].get("verbatim_source") or "") + " " + str(claims[c].get("spoken") or "")
                for c in cited).lower()
            if not cited:
                problems.append(
                    f"line {idx}: asserts a CADENCE ({word!r}) with no claim id. A rate is a factual "
                    f"claim about how often something happens and is as load-bearing as a number.\n"
                    f"      {text[:150]}")
            elif word not in backing:
                problems.append(
                    f"line {idx}: asserts a CADENCE ({word!r}) and cites {','.join(cited)}, but none of "
                    f"those claims' verbatim source says it. A citation is not a licence for a rate "
                    f"the record never states. Say what the record says, or drop the cadence.\n"
                    f"      {text[:150]}")
        if QUANT.search(text) and not cited and not DATEISH.search(text):
            problems.append(
                f"L{idx} states a quantity and cites NO claim id. Every number in the "
                f"narration must trace to the fact-check-safe set.\n      {text}")

        if show:
            notes.append(f"  L{idx:<3} claims={','.join(cited) or '-':<12} {text[:64]}")

    if show:
        print("\n".join(notes))
        print(f"\nvo_claims_check: {len(script['lines'])} lines, "
              f"{sum(1 for l in script['lines'] if l.get('claims'))} carry a claim id")

    problems = list(dict.fromkeys(problems))
    if problems:
        print("FAIL [vo_claims_check] the narration violates the fact-check-safe set.")
        for p in problems:
            print(f"  {p}")
        print()
        print("  Fix the SCRIPT, not the audio. This gate runs before any TTS is spent")
        print("  precisely so a false line never reaches a synth.")
        sys.exit(1)

    print(f"PASS [vo_claims_check] {len(script['lines'])} narration lines checked against "
          f"{len(claims)} claims; no obligation violated, no unsourced quantity and no unsourced cadence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
