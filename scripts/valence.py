#!/usr/bin/env python3
"""THE COMMITTED VALENCE, read once, by everything that has to answer it.

WHY THIS IS ITS OWN MODULE (2026-08-13)
---------------------------------------
Phase 2 writes out/dispatch/angle.json with a valence the writers room argued for in prose.
For months nothing downstream read it. get_music.py took a --mood string typed by hand, so a
film that had reasoned its way to "genuinely hopeful" got scored with a cold ambient bed, and
the storyboard picked its palette independently and landed in the same grey. The owner saw the
result before anyone saw the cause: "all the last videos just feel like down, or intense or
kinds of like doomy".

Music was wired to the valence first. Putting the palette on a SECOND copy of this logic would
guarantee the two drift, and a run whose bed says hopeful while its world says slate is exactly
the incoherence being fixed. One definition, two callers.

THE TWO TRAPS, both hit live while building the music side, both encoded here so the next
caller inherits the fix instead of rediscovering it:

  1. NEGATION IS NOT ASSERTION. A good valence field argues by elimination. The 08-13 one reads
     "Not celebration, because the award is three days old ... Not caution, because no Alaska
     outage is in the record." A bare keyword match reads "caution" there and scores a hopeful
     film as a warning -- inverting the tone on exactly the runs that reasoned most carefully.

  2. INTENSE IS NOT WARM. "driving" spent four minutes in the warm set and immediately chose a
     track tagged (driving, urgent, tense, newsy) for a hopeful film, answering "doomy" with
     "intense", which is the other half of the same complaint. Warm means carrying NO harsh
     tag, not merely carrying one bright one.
"""
import json
import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_HERE, ".."))
ANGLE = os.path.join(REPO, "out", "dispatch", "angle.json")

# Vocabularies shared by the bed and the world, so "warm" means one thing in this repo.
DOWN = {"cold", "glacial", "somber", "dark", "ominous", "tense", "urgent", "vast",
        "reflective", "pondering", "deep", "ambient", "grim", "bleak", "murky",
        "overcast", "night", "slate", "grey", "gray", "desaturated", "monochrome",
        "institutional", "sterile", "washed"}
UP = {"warm", "upbeat", "hopeful", "friendly", "gentle", "celebratory", "uplifting",
      "playful", "bouncy", "light", "wonder", "inspired", "bright", "golden", "amber",
      "sunlit", "dawn", "verdant", "saturated", "clear"}
HARSH = {"tense", "urgent", "dark", "ominous", "somber", "cold", "glacial", "deep",
         "bleak", "grim"}

_WANTS_UP = ("hopeful", "celebrat", "warm", "upbeat", "optimis", "curious", "wonder",
             "playful", "encouraging", "promising")
_WANTS_DOWN = ("caution", "somber", "grim", "warning", "loss", "danger", "elegy", "bleak")


def raw() -> str:
    """The valence + stance prose, lowercased. Empty when there is no angle on disk."""
    try:
        a = json.load(open(ANGLE))
        return " ".join(str(a.get(k, "")) for k in ("valence", "stance")).lower()
    except (OSError, ValueError):
        return ""


def _denegated(text: str) -> str:
    """Strip 'not <word>' spans. See trap 1 in the module docstring."""
    return re.sub(r"\bnot\s+[a-z]+", " ", text)


def stance():
    """(wants_up, wants_down, had_angle). Neither flag implies the other's negation:
    a film can commit to something that is genuinely both, and this reports that honestly
    rather than forcing a side."""
    text = raw()
    if not text:
        return False, False, False
    clean = _denegated(text)
    return (any(w in clean for w in _WANTS_UP),
            any(w in clean for w in _WANTS_DOWN),
            True)


def wants_warm() -> bool:
    """True only when the room committed to an up-leaning stance and did NOT also commit to a
    cautionary one. A mixed stance is left alone deliberately: forcing brightness onto a story
    that earned its gravity is the same failure as forcing grey onto a hopeful one."""
    up, down, had = stance()
    return had and up and not down


def is_warm_tagset(tags) -> bool:
    """A tag set counts as warm only if it carries an UP tag and NO harsh tag. See trap 2."""
    t = {str(x).lower() for x in tags}
    return bool(UP & t) and not (HARSH & t)


def score_text(text: str):
    """(up_hits, down_hits) for free-text like a palette or light_story description."""
    words = set(re.findall(r"[a-z]+", _denegated(str(text or "").lower())))
    return len(UP & words), len(DOWN & words)
