#!/usr/bin/env python3
"""THE PHYSICAL-EVENT GATE — every beat must DRAW something happening, not label it.

WHY THIS EXISTS (2026-07-31, after a seventeen-round run that could not reach its bar).

The panel's numbers were measured axis by axis at the end of that run. Weighted points lost:

    Hook & retention        0.44   (16%)
    Motion & animation      0.38   (14%)
    Illustration craft      0.37   (14%)
    Composition & staging   0.29   (11%)
    -------------------------------------
    those four                       55% of the entire deficit

Four axes, one cause, and all three judges described it in different words: the film STATES
its beats on cards over wide shots instead of DRAWING them.

  - the concession beat, the film's integrity move: "carried by a caption over ~85 percent
    empty bands", where the board itself had promised "the bare ground opens as a gap where
    there was never a gate". No gap was ever drawn.
  - the turn, the beat the whole film is built to deliver: "8 consecutive frames... the only
    change in frame is the burned caption swapping", where the board promised a slot cut on
    screen with daylight coming through it.
  - "'ONE LETS A SIZE THROUGH' is asserted in type, never demonstrated."

Seventeen rounds of patching could not touch that, because it is not a defect in a shot. It
is a decision made at Gate 0, before a single frame is rendered: the storyboard scheduled TYPE
where it should have scheduled EVENTS. A card appearing is not an event. The panel scores
picture events, and roughly half this film's beats resolved to a card appearing.

So this runs at Gate 0, costs no render time, and refuses a board whose beats do not move.

WHAT COUNTS
-----------
A beat passes when, after every clause about a CARD is removed, what remains still names a
physical event: something that moves, opens, breaks, lands, enters, fills, tips, cuts, or
otherwise CHANGES STATE on screen. "The gate arm swings down" passes. "The NO SIZE LIMIT card
seats above it" does not, on its own. "The candidate holds the sheet up while the card seats
beside it" passes, because a person is physically holding something.

WHAT THIS IS NOT
----------------
It is not a ban on cards. This film's cards are its sourcing and they are the best thing about
it. It is a requirement that a card be the ANNOTATION ON an event rather than a substitute for
one. Nor is it a stylistic opinion: the rubric's own descriptors for Motion and Hook are about
things happening, so a board with no events is failing a published standard, early, where it
is cheap to fix.

  python3 scripts/beat_events.py [--storyboard out/dispatch/storyboard.json] [--json]
"""
import argparse, json, re, sys
from pathlib import Path

# Verbs that name a change of state a viewer can SEE. Deliberately concrete; a verb that
# needs a caption to be understood does not belong here.
#
# BASE FORMS ONLY. The first version of this file listed third-person singular ("rises",
# "stamps") and storyboards are written in the base form ("two gates rise", "two questions
# stamp down"), so it produced five false failures on its first run, including the clock
# sweep, which is one of the few genuinely animated beats in that film. A gate that cries
# wolf gets switched off, so matching goes through _base() below.
EVENT_VERBS = {
    # arrival and departure
    "arrive", "enter", "land", "drop", "fall", "descend", "rise", "lift", "climb", "lower",
    "leave", "exit", "retreat", "withdraw", "roll", "drive", "walk", "run", "skid",
    "slide", "glide", "cross", "pass", "travel", "approach", "advance", "recede", "wake",
    # opening and closing
    "open", "close", "shut", "seal", "unfold", "fold", "swing", "slam", "snap",
    "click", "latch", "unlatch", "part", "split", "widen", "narrow", "gape",
    # making and breaking
    "cut", "carve", "break", "crack", "shatter", "tear", "rip", "punch", "bore",
    "stamp", "print", "burn", "melt", "freeze", "build", "assemble", "collapse",
    "crumble", "topple", "tip", "buckle", "bend", "warp",
    # filling and emptying
    "fill", "flood", "pour", "spill", "drain", "empty", "leak", "overflow",
    "pile", "stack", "bury", "scatter", "spray", "burst", "bloom",
    # turning and pointing
    "turn", "spin", "rotate", "sweep", "pivot", "swivel", "tilt", "lean", "point",
    "aim", "track", "follow", "recoil", "bounce", "settle", "shake", "tremble",
    "stutter", "flicker", "pulse", "throb", "rack",
    # scale and transformation
    "grow", "shrink", "expand", "contract", "stretch", "swell", "deflate",
    "brighten", "darken", "dim", "ignite", "extinguish",
    # contact
    "hit", "strike", "press", "push", "pull", "drag", "carry",
    "hold", "grip", "release", "catch", "block", "stop", "halt", "jam",
}

# Words that mark a clause as being ABOUT A PIECE OF TYPE rather than about the world.
CARD_NOUNS = {
    "card", "cards", "chip", "chips", "label", "labels", "caption", "captions", "annotation",
    "annotations", "title", "titles", "headline", "headlines", "nameplate", "nameplates",
    "subline", "sublines", "sub-line", "text", "type", "wordmark", "legend", "callout",
    "lower-third", "banner", "stat", "counter", "readout", "tag", "tags",
}

# Verbs a card does, which are NOT events even though they are motion words.
CARD_VERBS = {
    "seat", "appear", "fade", "read", "state", "say", "label", "name", "show",
    "display", "sit", "remain", "stay", "persist", "note",
}

def _base(tok: str) -> str:
    """Crude de-inflection, sufficient for storyboard prose: rises/rising/rose -> rise."""
    t = tok.lower()
    for suf, repl in (("ies", "y"), ("ing", ""), ("es", ""), ("ed", ""), ("s", "")):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            stem = t[: len(t) - len(suf)] + repl
            if stem in EVENT_VERBS or stem in CARD_VERBS:
                return stem
            if suf in ("ing", "ed") and (stem + "e") in (EVENT_VERBS | CARD_VERBS):
                return stem + "e"          # settling -> settle, closed -> close
    return t


_SPLIT = re.compile(r"[;,]| while | as | and then | then | with | beside | above | below |"
                    r" over | under | plus | alongside ")


def _clause_is_about_a_card(clause: str) -> bool:
    """True when the clause's subject is a piece of type."""
    raw = re.findall(r"[a-z][a-z\-']*", clause.lower())
    w = {_base(t) for t in raw} | set(raw)
    if not (w & CARD_NOUNS):
        return False
    # A clause naming a card AND a non-card event verb is a card doing something physical
    # (rare but real: "the card is knocked off the post"). Keep those.
    return not (w & (EVENT_VERBS - CARD_VERBS))


def beat_events(beat: dict):
    """(has_event, evidence, scanned_text) for one beat."""
    draw = beat.get("draw") or {}
    choreo = beat.get("choreo") or {}
    parts = [draw.get("action", ""), choreo.get("primary", ""),
             choreo.get("reaction", ""), choreo.get("ambient", "")]
    scanned = " ; ".join(p for p in parts if p)

    kept, found = [], []
    for chunk in parts:
        if not chunk:
            continue
        for clause in _SPLIT.split(chunk):
            clause = clause.strip()
            if not clause or _clause_is_about_a_card(clause):
                continue
            kept.append(clause)
            raw = re.findall(r"[a-z][a-z\-']*", clause.lower())
            nouns = {_base(t) for t in raw} | set(raw)
            for tok in raw:
                v = _base(tok)
                if v not in EVENT_VERBS or v in CARD_VERBS:
                    continue
                # hold/carry are events only when what is held is not a piece of type
                if v in ("hold", "carry") and (nouns & CARD_NOUNS):
                    continue
                found.append(v)
    return bool(found), sorted(set(found)), scanned


def analyze(storyboard_path: str):
    sb = json.loads(Path(storyboard_path).read_text())
    beats = sb.get("beats") or []
    rows, dead = [], []
    for i, b in enumerate(beats):
        ok, verbs, scanned = beat_events(b)
        rows.append({"i": i, "t": b.get("t"), "title": b.get("title", ""),
                     "has_event": ok, "verbs": verbs, "scanned": scanned})
        if not ok:
            dead.append(rows[-1])
    problems = []
    for d in dead:
        problems.append(
            f"beat {d['i']} at t={d['t']} \"{d['title']}\" names no physical event. Everything "
            f"in its draw.action and choreo is a card doing card things. Give it something that "
            f"moves, opens, breaks, lands or enters, and let the card annotate THAT. "
            f"(scanned: {d['scanned'][:160]})")
    # A board can technically satisfy the per-beat rule and still be mostly static, so hold a
    # floor on the SHARE of beats that carry an event.
    share = (len(beats) - len(dead)) / max(1, len(beats))
    if beats and share < 0.85:
        problems.append(
            f"only {share*100:.0f}% of beats name a physical event (floor is 85%). This is the "
            f"2026-07-31 failure mode: a board that schedules type where it should schedule "
            f"events, which no amount of per-shot polish can fix later.")
    return {"beats": len(beats), "with_event": len(beats) - len(dead),
            "share": share, "problems": problems, "rows": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--storyboard", default="out/dispatch/storyboard.json")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = analyze(a.storyboard)
    if a.json:
        print(json.dumps(r, indent=2))
        sys.exit(1 if r["problems"] else 0)
    print(f"beats: {r['beats']}   naming a physical event: {r['with_event']} "
          f"({r['share']*100:.0f}%)")
    for row in r["rows"]:
        mark = "  ok " if row["has_event"] else "  NO "
        print(f"{mark} t={row['t']:<7} {row['title'][:44]:44s} {','.join(row['verbs'][:4])}")
    if r["problems"]:
        print()
        for p in r["problems"]:
            print(f"FAIL [beat_events] {p}")
        sys.exit(1)
    print("PASS [beat_events] every beat draws something happening")
    sys.exit(0)


if __name__ == "__main__":
    main()
