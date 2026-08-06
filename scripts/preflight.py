#!/usr/bin/env python3
"""Run every mechanical gate BEFORE a panel is ever convened. Exit nonzero if any fail.

WHY THIS EXISTS (2026-08-05, owner: "I'm frustrated at ur pre-panel performance").

The mechanical gates in this repo are good and they were being run inconsistently, after
the fact, one at a time, by a run that remembered to. So cuts reached the panel carrying
defects that a script could have named in four seconds: a string wider than its plate, a
stale deliverable, an evidence pack describing a file that no longer existed. Three judges
then spent twenty minutes each rediscovering them, and a fix round went on something
arithmetic.

A checklist in a document is a suggestion. This is the checklist as a program. The routine
runs it before convening a panel, and a failure here means the panel does not get convened,
because a judge's attention is the most expensive thing in the loop and it should never be
spent on something a regex can find.

It deliberately does NOT judge quality. Everything here is a fact check: does the string
fit, do the bytes match, is the report measured rather than typed. Taste is the panel's
job and this file has no opinion about it.
"""
import os
import subprocess
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# (label, argv, required). A non-required check that fails is reported and does not block,
# because it is advisory rather than a fact about correctness.
CHECKS = [
    ("typecheck the engine",
     ["npx", "tsc", "--noEmit", "-p", "video-engine/tsconfig.json"], True),
    ("plated strings fit their plates",
     [sys.executable, "scripts/text_fit_check.py"], True),
    # Belt and braces. Its real home is Gate 0A', BEFORE the render, where catching a
    # collision costs nothing instead of seven minutes. It is repeated here because the
    # defect it catches is invisible at every other stage: the source reads fine, tsc is
    # clean, the render succeeds, and two annotations are stacked in the same pixels.
    ("nothing informational sits in the caption band",
     [sys.executable, "scripts/caption_band_check.py"], True),
    # Two elements in the same pixels cost score in three separate panel rounds on
    # 2026-08-06 and were invisible to every other check, because each element is
    # individually fine and the defect lives only in the relationship.
    ("no two text plates share pixels",
     [sys.executable, "scripts/plate_overlap_check.py"], True),
    # The fact-checker's instructions are obligations, not suggestions. Seven were
    # silently declined in one run and judges found all seven.
    ("every claim obligation the fact-checker wrote is honoured",
     [sys.executable, "scripts/claims_contract_check.py"], True),
    # ADVISORY ON PURPOSE, same reasoning as the block below: it has never gone green.
    # On the film that prompted it (2026-08-06) it fails 6 of 8 figures, which is the
    # honest state of the craft rather than a broken checker. Promote it to required once
    # a run has actually staged its cast instead of parking them.
    ("every figure on screen is doing something",
     [sys.executable, "scripts/staging_check.py"], False),
    # ADVISORY ON PURPOSE, FOR NOW. It is new and it has never been observed passing, and
    # arming a hard gate that has never gone green is how a run dies at 3am for a reason
    # nobody has seen (see the beat-delivery note in prompts/dispatch_routine.md). Promote
    # it to required once one run has read it and cleared it.
    ("the evidence pack actually shows the film",
     [sys.executable, "scripts/evidence_coverage_check.py"], False),
    ("the square crop cuts nothing built",
     [sys.executable, "scripts/crop_safety.py"], False),
    ("dead space within ceilings",
     [sys.executable, "scripts/dead_space_check.py", "--every", "30"], False),
]


def deliverables_are_fresh():
    """The cut on disk must be NEWER than everything that can change a frame.

    This is the check that catches the failure this repo has been burned by more than any
    other: a render that died, or an encode that did not rerun, leaving a plausible file
    with a valid frame count that every downstream step then treats as current.
    """
    import glob
    sources = []
    for pat in ("video-engine/src/**/*.tsx", "video-engine/src/**/*.ts",
                "out/dispatch/captions.json", "out/dispatch/episode_props.json",
                "out/dispatch/audio/master.wav"):
        sources += glob.glob(os.path.join(REPO, pat), recursive=True)
    if not sources:
        return None, "no source files found, which is itself wrong"
    newest = max(sources, key=os.path.getmtime)
    cut = os.path.join(REPO, "out", "dispatch", "dispatch_master.mp4")
    if not os.path.exists(cut):
        return False, "dispatch_master.mp4 does not exist"
    if os.path.getmtime(cut) < os.path.getmtime(newest):
        return False, (f"dispatch_master.mp4 is OLDER than {os.path.relpath(newest, REPO)}. "
                       f"Re-render and re-encode before grading anything.")
    return True, f"cut is newer than every source (newest: {os.path.relpath(newest, REPO)})"


def main():
    os.chdir(REPO)
    failures, advisories = [], []

    ok, msg = deliverables_are_fresh()
    if ok is False:
        failures.append(("deliverables are fresh", msg))
        print(f"  FAIL  deliverables are fresh: {msg}")
    else:
        print(f"  OK    deliverables are fresh: {msg}")

    for label, argv, required in CHECKS:
        p = subprocess.run(argv, capture_output=True, text=True)
        tail = (p.stdout or p.stderr).strip().splitlines()
        tail = tail[-1] if tail else "(no output)"
        if p.returncode == 0:
            print(f"  OK    {label}: {tail}")
        elif required:
            failures.append((label, tail))
            print(f"  FAIL  {label}: {tail}")
        else:
            advisories.append((label, tail))
            print(f"  NOTE  {label}: {tail}")

    print()
    if advisories:
        print(f"preflight: {len(advisories)} advisory check(s) reported something. They do "
              f"not block, but read them before spending a panel:")
        for label, tail in advisories:
            print(f"  - {label}: {tail}")
    if failures:
        print(f"preflight: BLOCKED on {len(failures)} check(s). Do NOT convene a panel.")
        print("  Every one of these is a fact a script found in seconds. A judge's "
              "attention is the most expensive thing in this loop and must not be spent "
              "on arithmetic.")
        return 1
    print("preflight: clear. The mechanical checks have nothing left to say; "
          "what remains is taste, which is what the panel is for.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
