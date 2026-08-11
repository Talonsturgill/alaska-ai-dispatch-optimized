#!/usr/bin/env python3
"""Refuse a Dispatch whose credits are missing, hand-typed, or out of step with the record.

WHY THIS EXISTS (2026-08-09, owner's request, and a judge's hard blocker before it).
------------------------------------------------------------------------------------
The music is CC BY 4.0. The licence requires attribution wherever the work is distributed,
which is every surface the file reaches and not just the one comment box somebody remembers
to paste into. The sources are what make the film's claims checkable by anyone who did not
watch a routine build them. Both used to live only in a LinkedIn first comment, typed by
hand, run after run.

On 2026-08-09 a judge filed the missing credit as a HARD BLOCKER, correctly: the rubric names
"music inaudible/uncredited" as an automatic fail. Three judges had raised it across six
rounds before that and each time the answer was "the email carries it", which was an answer
about one surface to a question about all of them.

So the credits are now rendered into the film by lib/EndCredits.tsx from data that
build_scenes.py derives from music_credit.json and sources.json. This gate is the half that
makes that stick. It checks four things, and each one is a way the arrangement could rot:

  1. THE BLOCK EXISTS.        A run that loses it ships an unattributed CC BY work.
  2. IT MATCHES THE RECORD.   The rendered music string must equal music_credit.json's
                              `credit` VERBATIM, and the source labels must be derivable from
                              sources.json. Hand-editing either into episode_props.json is
                              exactly the drift this replaces.
  3. THE ENGINE RENDERS IT.   The block can be perfect and the episode can still not draw it.
                              A prop nothing reads is not a credit.
  4. IT FITS.                 A credit nobody can read is not attribution. Every line is
                              measured against the safe width at its rendered size.

Exit 1 on any failure. There is no flag to skip it; a run that cannot credit its music has
nothing to ship.

    python3 scripts/credits_check.py
"""
import glob
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")
FRAME_W = 1080
SAFE = 72                      # must match EndCredits.tsx
MAXW = FRAME_W - SAFE * 2


def mono_w(s, size, track=0.0):
    return len(s) * size * 0.602 + track * max(0, len(s) - 1)


def fit_size(s, maxw, ideal, floor=13.0):
    return max(floor, min(ideal, maxw / (len(s) * 0.602 + 0.001)))


def newest_episode():
    files = glob.glob(os.path.join(REPO, "video-engine", "src", "Ep*.tsx"))
    return max(files, key=os.path.getmtime) if files else None


def main() -> int:
    problems = []

    props_p = os.path.join(OUT, "episode_props.json")
    if not os.path.exists(props_p):
        print("credits_check: no episode_props.json. Run scripts/build_scenes.py first.")
        return 1
    props = json.load(open(props_p))
    cred = props.get("credits")

    # ---- 1. the block exists ---------------------------------------------------------
    if not cred:
        print("credits_check: FAIL, episode_props.json carries no `credits` block.")
        print("  The music is CC BY 4.0 and the licence needs attribution on the work itself.")
        print("  build_scenes.py builds this from music_credit.json + sources.json; if it")
        print("  refused, it said why on its own line above.")
        return 1

    # ---- 2. it matches the record ----------------------------------------------------
    mc_p = os.path.join(OUT, "music_credit.json")
    if not os.path.exists(mc_p):
        problems.append("out/dispatch/music_credit.json is missing, so nothing can verify "
                        "the licence string that is on screen.")
    else:
        want = (json.load(open(mc_p)).get("credit") or "").strip()
        got = (cred.get("music") or "").strip()
        if not want:
            problems.append("music_credit.json has no `credit` field.")
        elif got != want:
            problems.append("the on-screen music credit is NOT the one in music_credit.json.\n"
                            f"          record: {want!r}\n"
                            f"          screen: {got!r}\n"
                            "        A credit that drifts from its own record is the failure "
                            "this gate exists for.")
        for token in ("CC BY", "MacLeod" if "MacLeod" in want else ""):
            if token and token.lower() not in got.lower():
                problems.append(f"the on-screen credit is missing {token!r}, which the licence "
                                f"or the composer requires.")

    src_p = os.path.join(OUT, "sources.json")
    labels = cred.get("sources") or []
    if not labels:
        problems.append("the credits carry no source labels at all.")
    elif os.path.exists(src_p):
        raw = json.dumps(json.load(open(src_p)))
        # every id shown on screen must appear somewhere in sources.json. This catches a label
        # somebody typed by hand, which is the only way a wrong id can get here.
        for lab in labels:
            for ident in re.findall(r"\b\d{6,}\b", lab):
                if ident not in raw:
                    problems.append(f"source label {lab!r} names {ident}, which appears "
                                    f"nowhere in sources.json.")

    site = (cred.get("site") or "").strip()
    if "alaskaaihq.com" not in site.lower():
        problems.append(f"the credits point at {site!r} rather than alaskaaihq.com.")

    # ---- 3. the engine renders it ----------------------------------------------------
    ep = newest_episode()
    if not ep:
        problems.append("no Ep*.tsx found, so nothing can be drawing the credits.")
    else:
        src = open(ep).read()
        body = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)      # comments are not renders
        body = re.sub(r"^\s*//.*$", " ", body, flags=re.M)
        # a TAG, not a substring: the first version of this check passed on "XEndCredits",
        # which is exactly the kind of near-miss a rename would produce
        if not re.search(r"<\s*EndCredits[\s/>]", body):
            problems.append(f"{os.path.relpath(ep, REPO)} never renders <EndCredits>. The "
                            f"credits block exists and nothing draws it.")
        elif not re.search(r"<Sequence[^>]*name=\"CREDITS\"", body):
            problems.append("the credits are not in a Sequence named CREDITS, so their "
                            "placement cannot be verified from the timeline.")

    # ---- 4. it fits ------------------------------------------------------------------
    site_line = f"VISIT US AT {site.upper()}"
    checks = [(site_line, fit_size(site_line, MAXW, 40)),
              ((cred.get("music") or "").upper(), fit_size((cred.get("music") or "").upper(),
                                                           MAXW, 19))]
    src_size = min([fit_size(l.upper(), MAXW, 22) for l in labels] or [22])
    checks += [(l.upper(), src_size) for l in labels]
    for text, size in checks:
        w = mono_w(text, size)
        if w > MAXW + 0.5:
            problems.append(f"{text[:44]!r} renders {w:.0f}px wide at size {size:.1f}, over the "
                            f"{MAXW}px safe width.")
        if size < 13.5:
            problems.append(f"{text[:44]!r} has to shrink to {size:.1f}px to fit, which is not "
                            f"readable on a phone. Shorten the label.")

    total, frames = props.get("total"), cred.get("frames")
    if total and frames and frames >= total:
        problems.append(f"the credits ({frames}f) are as long as the whole film ({total}f).")

    if problems:
        for p in problems:
            print(f"FAIL credits_check: {p}")
        print(f"\ncredits_check: {len(problems)} problem(s). A Dispatch that cannot credit its "
              f"music or show its sources has nothing to ship.")
        return 1

    print(f"credits_check: clean. {len(labels)} source line(s), licence string matches "
          f"music_credit.json verbatim, {cred.get('seconds')}s sign-off rendered by the engine.")
    for l in labels:
        print(f"    {l}")
    print(f"    {site_line}")
    print(f"    {(cred.get('music') or '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
