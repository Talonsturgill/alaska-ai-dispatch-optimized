#!/usr/bin/env python3
"""Refuse a figure that stands on screen without doing anything.

WHY THIS EXISTS (2026-08-06, owner, on the shipped films): characters "don't really do
anything or contribute much to illustrating the story ... seems like it's impossible for
anyone to wanna have eyes on them for too long cause they're a bit boring".

Measured against the film that prompted it, the note is exactly right and the numbers are
blunt. Of the 8 figures in Ep0806, 5 were `pose="stand"` and only 2 of the remaining 3
were given a time-varying `gesture` drive. So six of eight people on screen either stood
there or held one frozen shape for the length of their shot.

The frozen-shape half is the more embarrassing one, because the engine already solved it
and then defaulted the solution off. Character's `gesture` prop is documented as
"0..1 drive ... so a scene can PLAY a point rather than hold one", was added on 2026-08-04
because "two judges measured the film's only character gesture as already-extended in the
first frame of its shot and unchanged for 6.6s, which is a pose wearing a gesture's
clothes" -- and then it defaults to 1, which is precisely already-extended. A default that
reproduces the defect it was built to fix is not a fix, it is a switch nobody flipped.

WHAT IT CHECKS, per <Character> in the episode:

  1. A gesture pose (point, raise, panic, carry) must be DRIVEN. Its `gesture` prop has to
     reference the frame, an interpolate, or a spring. A literal `gesture={1}` or an absent
     prop means the arm is welded in place, and this fails.
  2. A figure held for longer than --stand-seconds with no gesture and no walk is a
     mannequin. Idle life alone does not make a person INTERESTING, it only stops them
     reading as a sprite. Give them something to do, or let the shot be shorter, or do not
     put a person in it.

WHAT IT DOES NOT DO. It has no opinion about whether the action is any good, only that one
was authored. Taste stays with the panel; this is here so the panel never has to spend a
round saying "the person in shot four does nothing", which three of them did.

Exit 1 on any violation.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FPS = 30.0
GESTURE_POSES = {"point", "raise", "panic", "carry"}
# A driven prop mentions the frame, an interpolation, a spring, or a scene-local ramp.
DRIVEN = re.compile(r"\b(f|frame|interpolate|spring|Math\.|useCurrentFrame)\b")


def scene_durations(props_path):
    """Shot index -> seconds, from the run's own episode props."""
    if not os.path.exists(props_path):
        return {}
    scenes = json.load(open(props_path)).get("scenes") or []
    return {i + 1: sc["dur"] / FPS for i, sc in enumerate(scenes)}


def characters(src):
    """Every <Character .../> with its scene number and its raw prop block."""
    scene_at = []
    for m in re.finditer(r"^const (S(\d+)): React\.FC<SceneProps>", src, re.M):
        scene_at.append((int(m.group(2)), m.start()))
    out = []
    for m in re.finditer(r"<Character\b", src):
        blk = src[m.start():m.start() + 500]
        end = blk.find("/>")
        blk = blk[:end] if end > 0 else blk[:400]
        scene = 0
        for num, pos in scene_at:
            if pos < m.start():
                scene = num
        out.append((src[:m.start()].count("\n") + 1, scene, blk))
    return out


def prop(blk, name):
    m = re.search(name + r"=\{([^}]*)\}", blk) or re.search(name + r'="([^"]*)"', blk)
    return m.group(1).strip() if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*")
    ap.add_argument("--props", default=os.path.join(REPO, "out", "dispatch", "episode_props.json"))
    ap.add_argument("--stand-seconds", type=float, default=4.0,
                    help="a figure held longer than this with nothing to do is a mannequin")
    a = ap.parse_args()

    targets = a.targets
    if not targets:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        from caption_band_check import default_targets
        targets = default_targets()

    durs = scene_durations(a.props)
    problems, checked = [], 0

    for path in targets:
        src = open(path).read()
        rel = os.path.relpath(path, REPO)
        for line, scene, blk in characters(src):
            checked += 1
            pose = prop(blk, "pose") or "stand"
            gesture = prop(blk, "gesture")
            walking = prop(blk, "walking") or prop(blk, "walkPhase")
            secs = durs.get(scene)

            # a pose chosen by an expression (a crowd picking per-index) counts as the
            # expression's own business; we only judge the ones we can read.
            literal_pose = re.fullmatch(r"['\"]?(\w+)['\"]?", pose)
            pose_name = literal_pose.group(1) if literal_pose else None

            if pose_name in GESTURE_POSES:
                if gesture is None:
                    problems.append(
                        f"{rel}:{line}  S{scene}  pose={pose_name!r} with NO gesture drive. "
                        f"It defaults to 1, so the arm is fully extended on frame 1 and never "
                        f"moves. Pass a driven gesture (interpolate on the frame) so the "
                        f"figure PLAYS the action instead of holding its result.")
                elif not DRIVEN.search(gesture):
                    problems.append(
                        f"{rel}:{line}  S{scene}  gesture={{{gesture}}} is a constant, so the "
                        f"pose is welded. The prop exists to play the movement; give it a ramp.")
            elif walking is None and secs and secs > a.stand_seconds:
                problems.append(
                    f"{rel}:{line}  S{scene}  a figure stands for {secs:.1f}s "
                    f"(over {a.stand_seconds}s) with no gesture and no walk. Idle life stops "
                    f"them reading as a sprite; it does not make them worth watching. Give "
                    f"them an action tied to what the narration is saying, or cut the figure.")

    if problems:
        for p in problems:
            print(f"FAIL {p}")
        print(f"\nstaging_check: {len(problems)} figure(s) with nothing to do, of {checked}.")
        print("A person on screen is the most attention-grabbing thing in any frame, so a")
        print("person doing nothing spends that attention on nothing. This is the note the")
        print("owner gave on 2026-08-06 and that three judges gave before them.")
        return 1
    print(f"staging_check: {checked} figure(s), every one of them doing something")
    return 0


if __name__ == "__main__":
    sys.exit(main())
