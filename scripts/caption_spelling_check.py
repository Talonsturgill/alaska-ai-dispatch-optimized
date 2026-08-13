#!/usr/bin/env python3
"""Hard gate: no phonetic respelling may survive into the BUILT episode props.

WHY THIS EXISTS (2026-08-08). The TTS script is phonetically respelled so the synth says
proper nouns correctly ("Ex Prize", "Nana" for Nenana, "A I" for AI). Captions are force
-aligned from Whisper's transcript OF THAT AUDIO, so the respelling is what lands on
screen unless something puts the real spelling back. build_scenes.py does exactly that,
from a `caption_fixups` map declared in vo_script.json.

That fix was correct and it still shipped the defect, because it is a TRANSFORM and not a
CHECK. On this run the map was declared at 06:44 and episode_props.json was built at 08:15
from a captions.json that a later line-patch had rewritten, and "A I" was on screen at
43.84s in a frame whose own plate read "AI" two inches above it. A panel judge called it a
hard blocker: wrong text on screen, contradicted by the same frame.

The transform runs at build time and leaves no trace anyone can audit. Nothing anywhere
asked the simple question afterwards: does the file we are about to RENDER still contain a
string we know is wrong? A pipeline that can only fix a defect at one instant, and cannot
detect it at any other, will ship it the first time the order of operations shifts.

So this reads the BUILT artifact, not the source, and it is deliberately dumb: every key of
caption_fixups is a string we have already declared must never appear on screen. If one is
in episode_props.json, the props are stale or the transform was bypassed. Either way the
answer is the same and it is cheap: re-run scripts/build_scenes.py.

Exit 0 clean, exit 1 with findings. Wire it BEFORE the render.
"""
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")


def main():
    sp = os.path.join(OUT, "vo_script.json")
    pp = os.path.join(OUT, "episode_props.json")
    for p in (sp, pp):
        if not os.path.exists(p):
            print(f"caption_spelling_check: SKIP, {os.path.relpath(p, REPO)} does not exist yet")
            return 0

    fixups = json.load(open(sp)).get("caption_fixups", {})
    if not fixups:
        print("caption_spelling_check: no caption_fixups declared, nothing to enforce")
        return 0

    caps = json.load(open(pp)).get("captions", [])
    findings = []
    for c in caps:
        t = c.get("text", "")
        for wrong, right in fixups.items():
            # same boundary rule build_scenes.py applies, so the check and the transform
            # can never disagree about what counts as a hit
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(wrong) + r"(?![A-Za-z0-9])", t, re.I):
                findings.append((c.get("start"), wrong, right, t))

    # ...AND ACROSS THE SEAM (2026-08-13). This checker read one cue at a time and therefore
    # agreed with a transform that also read one cue at a time, so when the chunker split
    # "N S F" into "...and N S" / "F says...", both of them saw a clean film and the phonetic
    # respelling shipped. Two tools sharing a blind spot is not two checks. Read the pair.
    for a, b in zip(caps, caps[1:]):
        seam = (a.get("text", "").rstrip() + " " + b.get("text", "").lstrip()).strip()
        for wrong, right in fixups.items():
            if len(wrong.split()) < 2:
                continue
            if re.search(r"(?<![A-Za-z0-9])" + re.escape(wrong) + r"(?![A-Za-z0-9])", seam, re.I) \
               and not re.search(r"(?<![A-Za-z0-9])" + re.escape(wrong) + r"(?![A-Za-z0-9])",
                                 a.get("text", ""), re.I):
                findings.append((a.get("start"), wrong, right,
                                 f"SPLIT ACROSS CUES: {a.get('text','')!r} + {b.get('text','')!r}"))

    if not findings:
        print(f"caption_spelling_check: clean, {len(caps)} cues carry none of the "
              f"{len(fixups)} declared respellings")
        return 0

    print("FAIL [caption_spelling_check] the built episode still carries a phonetic respelling.")
    for start, wrong, right, t in findings:
        at = f"{start:.2f}s" if isinstance(start, (int, float)) else "?"
        print(f"  {at}  '{wrong}' should read '{right}':  {t}")
    print()
    print("  episode_props.json is stale with respect to vo_script.json's caption_fixups.")
    print("  Re-run:  python3 scripts/build_scenes.py")
    return 1


if __name__ == "__main__":
    sys.exit(main())
