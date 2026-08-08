#!/usr/bin/env python3
"""Enforce the obligations a claim's note puts on the BUILD.

WHY THIS EXISTS (2026-08-06, after the panel found seven of these in one run).

claims.json is checked for what strings are ALLOWED on screen. It has never been checked
for what its notes REQUIRE. A note is prose sitting in a data file, so the build reads it,
agrees with it, and then quietly does something else — and nothing anywhere notices.

Every one of these shipped in a graded cut this run:

  c1   note: "SAY ROUGHLY."            -> the VO said "six hundred thousand dollars" flat,
                                          and later the card said "$600,000" bare.
  c6   note: "SCOPE. Plate readers ONLY. Never widen."
                                       -> shipped as "OBJECT RECOGNITION", scope dropped,
                                          and a VO line claimed Anchorage recognises faces.
  c7   note: "HIS CHARACTERIZATION, not a finding. Attribute on screen."
                                       -> the quote shipped bare, so a contested
                                          characterisation read as a finding about the code.
  c13  approved on_screen "NO VENDOR NAMED"
                                       -> the build shortened it to "NOT NAMED", which reads
                                          as a person being unnamed, not a procurement fact.
  c18  note: "Attribute to the chief."  -> stated as fact, on screen and in the VO.
  c19  the Fairbanks counter-point      -> never shipped at all, in any frame or line, while
                                          the other city's counter-cards were drawn.
  c20  note: "MUST SHIP WITH c21."      -> shipped, and its own speaker line rendered
                                          underneath another card, invisible.

Judges caught all seven. That is judge time spent re-deriving something the fact-checker had
already written down, which is the most expensive way possible to learn it.

HOW IT WORKS. Obligations live in a machine-readable `requires` block on the claim, so they
are data rather than prose:

    "requires": {
      "on_screen_verbatim": true,          # the approved string, exactly, no paraphrase
      "spoken_contains": ["roughly"],      # the VO line must carry this hedge
      "attribution_on_screen": "McCORMICK",# a distinctive token from `label` must be drawn
      "must_ship_with": ["c21"],           # if this is drawn, so is that
      "must_ship": true                    # this claim has to appear somewhere at all
    }

The prose note stays: it is what a human reads. The `requires` block is what the machine
reads. Whoever writes claims.json writes both, and they must agree.

Exit 1 on any unmet obligation.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def engine_text(path):
    return open(path).read()


def _norm(t):
    """Reduce text to comparable content: no punctuation, no case, single spaces.

    Parsing JS string literals with a regex was the first approach and it broke on the
    escaped apostrophe in `'"WE JUST DON\\'T HAVE'`, silently reporting a card that was on
    screen as missing. A checker that cries wolf gets switched off, so this compares CONTENT
    instead: strip the JSX attribute names, drop every character that is not a letter,
    a digit or a space, and collapse. A card split across two `lines` entries, or across
    StatCard's big= and sub=, then reads as the one string it renders as.
    """
    # COMMENTS ARE NOT ON SCREEN. Caught in this checker's own regression test: deleting
    # both MIKE SANDERS attribution plates still passed, because the source comments explain
    # at length why Sanders must be credited. A checker that reads its own documentation as
    # evidence will certify anything that is well described and not drawn.
    t = re.sub(r"/\*.*?\*/", " ", t, flags=re.S)
    t = re.sub(r"^\s*//.*$", " ", t, flags=re.M)
    t = re.sub(r"\b[\w-]+=", " ", t)              # JSX attribute names
    t = t.replace("&quot;", " ").replace("&apos;", " ").replace("\u2019", "'")
    t = re.sub(r"[^A-Za-z0-9 ]+", "", t.upper())
    return " ".join(t.split())


def drawn(engine, s, _cache={}):
    """Is this string's CONTENT drawn anywhere in the engine?"""
    if not s:
        return False
    key = id(engine)
    if key not in _cache:
        _cache[key] = _norm(engine)
    n = _norm(s)
    return bool(n) and n in _cache[key]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims", default=os.path.join(REPO, "out", "dispatch", "claims.json"))
    ap.add_argument("--vo", default=os.path.join(REPO, "out", "dispatch", "vo_script.txt"))
    ap.add_argument("--engine", default=None)
    a = ap.parse_args()

    eng_path = a.engine
    if eng_path is None:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        from caption_band_check import default_targets
        eng_path = default_targets()[0]

    doc = json.load(open(a.claims))
    claims = doc["claims"] if isinstance(doc, dict) and "claims" in doc else doc
    engine = engine_text(eng_path)
    vo = open(a.vo).read()
    by_id = {c["id"]: c for c in claims}

    problems, checked = [], 0
    for c in claims:
        # `requires` may be PROSE (a list written by the fact-checker for humans and for
        # vo_claims_check.py) or a machine contract (a dict). A list used to crash this
        # gate outright with AttributeError, which BLOCKED the panel on a shape mismatch
        # rather than on a defect. Machine assertions now live in `contract`; a prose-only
        # claim is skipped here and still checked by vo_claims_check.py.  (2026-08-08)
        req = c.get("contract") or c.get("requires") or {}
        if isinstance(req, list):
            req = {}
        if not req:
            continue
        cid = c["id"]
        on = c.get("on_screen") or ""
        is_drawn = drawn(engine, on)

        # COUNT THE EVALUATION, NOT THE FAILURE (2026-08-08). This increment sat inside the
        # failure branch, so a run where every must_ship obligation was SATISFIED reported
        # "0 obligation(s) met, none outstanding" — a passing gate and a gate that graded
        # nothing print the identical line. That distinction is the whole value of the
        # report. Twice already this run a checker announced clean while reading the wrong
        # file or returning early, and the only reason either was caught is that a number
        # somewhere looked wrong. A counter that cannot tell 8-and-all-fine from 0 takes
        # that last signal away.
        if req.get("must_ship"):
            checked += 1
            if not is_drawn and not drawn(engine, (c.get("spoken") or "")):
                problems.append(f"{cid}: requires must_ship, but its approved string "
                                f"{on!r} appears nowhere in {os.path.basename(eng_path)}.")

        if req.get("on_screen_verbatim") and on:
            checked += 1
            if not is_drawn:
                near = [ln.strip() for ln in engine.split("\n")
                        if on.split(":")[0][:16] and on.split(":")[0][:16] in ln][:1]
                hint = f" Closest line drawn: {near[0][:90]}" if near else ""
                problems.append(f"{cid}: requires on_screen_verbatim, so the card must read "
                                f"exactly {on!r}. It does not.{hint}")

        for tok in req.get("spoken_contains") or []:
            checked += 1
            if tok.lower() not in vo.lower():
                problems.append(f"{cid}: note requires the narration to carry {tok!r} "
                                f"(its `note` says so); vo_script.txt does not contain it.")

        att = req.get("attribution_on_screen")
        if att:
            checked += 1
            if is_drawn and not drawn(engine, att):
                problems.append(f"{cid}: its note requires an on-screen attribution and the "
                                f"quote IS drawn, but no card carries {att!r}. "
                                f"Speaker per claims.json: {c.get('label')!r}.")

        for other in req.get("must_ship_with") or []:
            checked += 1
            o = by_id.get(other)
            if is_drawn and o and not drawn(engine, o.get("on_screen") or ""):
                problems.append(f"{cid} requires must_ship_with {other}, and {cid} is drawn, "
                                f"but {other} ({o.get('on_screen')!r}) is not.")

    if problems:
        for p in problems:
            print(f"FAIL {p}")
        print(f"\nclaims_contract_check: {len(problems)} unmet obligation(s) "
              f"across {checked} check(s).")
        print("These are instructions the fact-checker wrote FOR the build, in the claim")
        print("record. A note the build can decline is not a safeguard, it is a suggestion.")
        return 1
    print(f"claims_contract_check: {checked} obligation(s) met, none outstanding")
    return 0


if __name__ == "__main__":
    sys.exit(main())
