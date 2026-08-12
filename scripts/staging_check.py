#!/usr/bin/env python3
"""Bind what the storyboard STAGES to what the engine DRAWS, figure by figure.

WHY THIS EXISTS (2026-08-06, owner, on the shipped films): characters "don't really do
anything or contribute much to illustrating the story ... seems like it's impossible for
anyone to wanna have eyes on them for too long cause they're a bit boring".

The first version of this file assumed nobody had decided what the figures should do. That
was wrong, and the truth is more useful. The storyboard for that film had already written
real acting, beat by beat:

    t=48.3   "looks at the frame, then at the bar, and does not reach for anything yet"
    t=66.4   "signs the corner of the frame, slowly, once"
    t=91.4   "the slip is set down and NOT stamped, either way"
    t=97.0   "the slip moves between them and is slid back"

The engine then drew `pose="stand"` for five of its eight figures, holding for 10.3 to
14.3 seconds each. So the performance was designed and silently not built, and NOTHING IN
THE PIPELINE COMPARED THE TWO. That is the same defect shape that cost this repo a stale
filmstrip anchor set, a stale deliverable at the ship gate, an evidence pack that
photographed the wrong seconds, and a caption gate that graded a different file than the
one it emailed. A plan and an artifact, each fine on its own, and no one checking that the
artifact is the plan.

Telling a run "give the figures something to do" is not the fix, because the run already
did that, in the board, and then lost it. The fix is to quote the board's own words back
at the build and refuse the shot until they are on screen.

THE THREE RULES

  A. A gesture pose (point, raise, panic, carry) must be DRIVEN. `gesture` defaults to 1,
     which is fully-extended-on-frame-1, so an undriven gesture pose is a still photograph
     of an action. No figure in the 08-06 film actually tripped this, but the trap is real
     and one line of code away.

  B. If the storyboard stages a person performing an INTENTIONAL ACT during a shot, the
     figure in that shot must have a driven gesture. The failure quotes the board, so the
     fixer is told what to build rather than asked to invent something.

  C. A figure held past --stand-seconds in a shot whose beats never stage a person at all
     is unmotivated set dressing. Someone put a human in frame and gave them no reason to
     be there, and a person is the most attention-grabbing thing in any composition.

DELIBERATE STILLNESS IS ACTING AND IS NOT A VIOLATION. The 08-06 board has a beat reading
"the picture stops. Nothing advances. The person breathes and the stack sits." That is a
choice, it is the strongest beat in its shot, and a checker that could not tell it apart
from neglect would train runs to add pointless fidgeting. Rule B fires only on verbs that
denote an act.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FPS = 30.0
GESTURE_POSES = {"point", "raise", "panic", "carry"}

# A figure, as opposed to a hand, an object, or a room.
FIGURE = re.compile(r"\b(technician|official|attorney|attorneys|chief|person|people|figure|"
                    r"figures|clerk|resident|residents|worker|workers|member|members|crowd|"
                    r"staffer|analyst|officer|assembly)\b", re.I)
# Verbs that denote an ACT. Deliberate stillness is acting too and must not fire rule B.
ACT = re.compile(r"\b(looks?|glances?|turns?|signs?|sets? down|slides?|slid|reaches?|"
                 r"points?|hands?|stamps?|taps?|lifts?|pushes?|pulls?|opens?|closes?|"
                 r"writes?|types?|marks?|picks? up|puts?|passes?|leans?|steps?|walks?|"
                 r"raises?|drops?|gestures?)\b", re.I)
STILL = re.compile(r"\b(breathes?|waits?|sits?|stands? still|does not move|nothing advances|"
                   r"holds? still|motionless)\b", re.I)

# Things that are not people. A beat whose subject LEADS with one of these is about the
# object, even when a person is named later in the phrase.
OBJECT = re.compile(r"\b(plate|plates|screen|frame|frames|slip|stack|bar|box|boxes|wall|"
                    r"sign|chart|card|cards|desk|table|tile|tiles|room|console|spool|"
                    r"grid|map|counter|paper|folder|line|band|door)\b", re.I)

DRIVEN = re.compile(r"\b(interpolate|spring|useCurrentFrame)\b|\bf\b")


def stages_a_figure(subject):
    """Is this beat's subject a PERSON, or an object that merely mentions one?

    Two false positives on the 08-06 board taught this, and both are the same shape: a
    person's name living inside an object's description.

      "the frame on the technician's screen"                  -> the screen, not the person
      "a BrassPlate quote plate with an attribution line
       reading KEITH McCORMICK, ASSEMBLY MEMBER"              -> a text plate, not a person

    A bare keyword match calls both of those a staged figure and then demands the engine
    animate a person who was never the subject. A checker that invents defects gets
    switched off, and then the real ones ride along with it.

    The rule that separates them cleanly: whichever comes FIRST in the phrase is what the
    beat is about. Possessives are stripped first, so "the technician's screen" cannot
    win on position.
    """
    s = re.sub(r"\b[\w-]+'s\b", " ", str(subject))
    f = FIGURE.search(s)
    if not f:
        return False
    o = OBJECT.search(s)
    return o is None or f.start() < o.start()


def read_json(p):
    return json.load(open(p)) if os.path.exists(p) else None


def char_block(src, i):
    """The full <Character .../> text, brace-aware.

    A fixed-width slice was the first approach and it silently truncated the S9 crowd,
    whose gesture prop sits ~430 characters in. It reported a correctly-driven figure as
    frozen, which is a checker inventing a defect. Read to the matching '/>' at depth 0.
    """
    d = 0
    for j in range(i, min(len(src), i + 4000)):
        c = src[j]
        if c == "{":
            d += 1
        elif c == "}":
            d -= 1
        elif c == "/" and j + 1 < len(src) and src[j + 1] == ">" and d == 0:
            return src[i:j]
    return src[i:i + 1500]


def scan_engine(path):
    """Every <Character> with its scene number, poses, and whether its gesture is driven."""
    src = open(path).read()
    decls = [(int(m.group(2)), m.start())
             for m in re.finditer(r"^const (S(\d+)): React\.FC<SceneProps\b[^>]*>", src, re.M)]
    out = []
    for m in re.finditer(r"<Character\b", src):
        blk = char_block(src, m.start())
        scene = 0
        for num, pos in decls:
            if pos < m.start():
                scene = num
        poses = set(re.findall(r"'(\w+)'", blk)) | set(re.findall(r'pose="(\w+)"', blk))
        poses &= (GESTURE_POSES | {"stand", "arms-crossed"})
        g = re.search(r"gesture=\{", blk)
        driven = bool(g) and bool(DRIVEN.search(blk[g.start():g.start() + 300]))
        walking = "walking" in blk or "walkPhase" in blk
        out.append({"line": src[:m.start()].count("\n") + 1, "scene": scene,
                    "poses": poses, "has_gesture": bool(g), "driven": driven,
                    "walking": walking})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*")
    ap.add_argument("--props", default=os.path.join(REPO, "out", "dispatch", "episode_props.json"))
    ap.add_argument("--storyboard", default=os.path.join(REPO, "out", "dispatch", "storyboard.json"))
    ap.add_argument("--stand-seconds", type=float, default=4.0)
    a = ap.parse_args()

    targets = a.targets
    if not targets:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        from caption_band_check import default_targets
        targets = default_targets()

    props, sb = read_json(a.props), read_json(a.storyboard)
    scenes, staged = {}, {}
    if props:
        for i, sc in enumerate(props["scenes"]):
            scenes[i + 1] = (sc["from"] / FPS, (sc["from"] + sc["dur"]) / FPS)
    if sb:
        for b in sb.get("beats") or []:
            d = b.get("draw") or {}
            blob = f"{d.get('subject','')} {d.get('action','')}"
            if not stages_a_figure(d.get("subject", "")):
                continue
            t = float(b.get("t", -1))
            sc = next((n for n, (x, y) in scenes.items() if x <= t < y), None)
            if sc is None:
                continue
            act = bool(ACT.search(blob)) and not STILL.search(str(d.get("action", "")))
            staged.setdefault(sc, []).append(
                {"t": t, "act": act, "action": str(d.get("action", ""))[:110],
                 "subject": str(d.get("subject", ""))[:70]})

    problems, checked = [], 0
    for path in targets:
        rel = os.path.relpath(path, REPO)
        for ch in scan_engine(path):
            checked += 1
            sc, line = ch["scene"], ch["line"]
            secs = None
            if sc in scenes:
                secs = scenes[sc][1] - scenes[sc][0]
            beats = staged.get(sc, [])
            acts = [b for b in beats if b["act"]]

            # A. an undriven gesture pose is a photograph of an action
            if ch["poses"] & GESTURE_POSES and not ch["driven"]:
                problems.append(
                    f"{rel}:{line}  S{sc}  gesture pose {sorted(ch['poses'] & GESTURE_POSES)} "
                    f"with no driven `gesture`. It defaults to 1, fully extended on frame 1, "
                    f"so the figure holds the RESULT of the action and never performs it.")
                continue

            if ch["walking"] or ch["driven"]:
                continue

            # B. the board staged an act here and the engine did not build it
            if acts:
                b = acts[0]
                problems.append(
                    f"{rel}:{line}  S{sc}  the storyboard stages this figure ACTING at "
                    f"t={b['t']}s and the engine draws a static pose.\n"
                    f"      board subject: {b['subject']}\n"
                    f"      board action : {b['action']}\n"
                    f"      Build that. Drive `gesture` on the frame so the move plays across "
                    f"the beat. The performance was designed; it just was not rendered.")
            # C. a figure nobody wrote a reason for
            elif secs and secs > a.stand_seconds and not beats:
                problems.append(
                    f"{rel}:{line}  S{sc}  a figure stands for {secs:.1f}s and NO beat in this "
                    f"shot stages a person at all. Unmotivated set dressing. A person is the "
                    f"most attention-grabbing thing in a frame, so one with no reason to be "
                    f"there spends that attention on nothing. Give them a beat in the board "
                    f"first, then build it, or take them out of the shot.")

    if problems:
        for p in problems:
            print(f"FAIL {p}")
        print(f"\nstaging_check: {len(problems)} figure(s) of {checked} are not performing "
              f"what the board asked for.")
        print("Where the board already wrote the action, the fix is transcription, not")
        print("invention. Where it did not, the board is the thing to fix first.")
        return 1
    print(f"staging_check: {checked} figure(s), every one performing what the board staged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
