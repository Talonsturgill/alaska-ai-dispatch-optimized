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
    # A phonetic respelling reaching the screen is a hard blocker every time a panel has
    # seen one, and the fix for it is a build-time TRANSFORM with no audit trail. This
    # asks the built artifact the question afterwards, which is the only way an ordering
    # change gets caught. 2026-08-08: "A I" on screen under a plate reading "AI".
    ("no phonetic respelling survived into the built props",
     [sys.executable, "scripts/caption_spelling_check.py"], True),
    # Two elements in the same pixels cost score in three separate panel rounds on
    # 2026-08-06 and were invisible to every other check, because each element is
    # individually fine and the defect lives only in the relationship.
    ("no two text plates share pixels",
     [sys.executable, "scripts/plate_overlap_check.py"], True),
    # A plate can fit its own box perfectly and still be cut in half by the frame edge,
    # because the scene's content zoom pushes everything off-centre outward. On 2026-08-09
    # that clipped five elements including the film's central NSF quotation, which read on
    # screen as "FORCEMENT-LEARNING CONTROLLERS ... GRATED WITH MICR". No existing check
    # could see it: text_fit measures string against plate, caption_band models the VERTICAL
    # crop, plate_overlap compares boxes to each other. This one projects each box through
    # the zoom and compares it to the frame.
    ("no plate leaves the frame under the content zoom",
     [sys.executable, "scripts/zoom_clip_check.py"], True),
    # The fact-checker's instructions are obligations, not suggestions. Seven were
    # silently declined in one run and judges found all seven.
    ("every claim obligation the fact-checker wrote is honoured",
     [sys.executable, "scripts/claims_contract_check.py"], True),
    # The credits ride in the picture (2026-08-09, owner's request). The music is CC BY 4.0
    # and the licence needs attribution on every surface the file reaches, not just the one
    # comment box somebody remembers. Blocking, because a run that cannot credit its music
    # has nothing to ship.
    ("the film credits its music and shows its sources",
     [sys.executable, "scripts/credits_check.py"], True),
    # THE NARRATION obeys the claim set too. Added 2026-08-08, after a false line
    # ("five rural clinics that didn't have one") passed Gate 0E and the soundcheck
    # and reached a synth, because Gate 0E asks whether a stranger can FOLLOW the
    # script and the soundcheck asks whether the ASR heard it, and nothing asked
    # whether it was TRUE. Verified in both directions on the real defect.
    ("the narration obeys the fact-check-safe set",
     [sys.executable, "scripts/vo_claims_check.py"], True),
    # ...AND SO DOES THE AUDIO WE ACTUALLY SHIP. The check above gates the SCRIPT before TTS
    # is spent, which is the cheap place to catch a false line. It is not the LAST place one
    # can exist. On 2026-08-08 a surgical re-cut left a corrected script beside audio that
    # had not all been re-cut, and a words.json written 17 minutes before the patched vo.wav
    # then misrepresented the mix to a panel judge in the OTHER direction. Both failures are
    # the same gap: nothing had listened to the delivered file. Now something does.
    # Advisory, because a missing ASR backend must never be the thing that halts a run.
    ("the delivered mix obeys the fact-check-safe set",
     [sys.executable, "scripts/vo_audio_check.py"], False),
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
    # THE STORY REGION, WITH THE FURNITURE TAKEN OUT. The whole-frame dead-window gate went
    # blind the moment a near-field foreground was added to fix the previous round's dead
    # lower third: the foreground bobs continuously, so every frame contains motion whatever
    # the story is doing. A judge then measured two windows over the gate's own 5s rule that
    # it could not see. Advisory: the timecodes are the point, not the exit code.
    ("the story region never stops moving",
     [sys.executable, "scripts/content_sag_check.py"], False),
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
