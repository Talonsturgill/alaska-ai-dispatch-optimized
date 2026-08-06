#!/usr/bin/env python3
"""Print what each shot's ART does against the VO lines that shot actually covers.

WHY THIS EXISTS (2026-08-06, cost a full render and most of a panel round).

`SSL` / `scene_start_line` decides which VO lines each shot covers. Scene components are
authored against a PARTICULAR mapping, and every timing inside them is a frame offset from
that shot's own start. Re-solve SSL, or insert one line into the script, and every shot
downstream is cutting to different words — and nothing says so. tsc is clean. build_scenes
runs. The render succeeds. The film is just about the wrong things.

What that looked like: a re-solve moved S4 from two lines to three. S4's art whipped to a
Fairbanks records room at 0.3s and the narration stayed on the Anchorage police chief for
ten more seconds. S2's tail lost its picture entirely — six seconds of a finished crane
holding on a price card while the VO described a city ordinance. Both were found by reading
geometry by hand, after the render.

The judgement "is this picture about this line" is not automatable. The MECHANICAL half is:
where the lines start, and where the scene's animation events fire. Those two columns side
by side make a mismatch obvious in one screen. A shot whose only events fire at 0.3s while
its second line starts at 5.4s has nothing happening for five seconds; a shot whose events
all sit in its first third has a dead tail. Both are visible here and neither is visible in
the source.

Events are parsed from `interpolate(f, [...])` in each scene component — the first and last
keyframe of each call, in seconds from the shot's own start. Reads only; changes nothing.
"""
import argparse
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FPS = 30.0


def scene_bodies(path):
    """{'S4': source text} for each `const S<n>: React.FC<SceneProps>` in the episode."""
    src = open(path).read()
    starts = [(m.group(1), m.start()) for m in
              re.finditer(r"^const (S\d+): React\.FC<SceneProps>", src, re.M)]
    out = {}
    for i, (name, a) in enumerate(starts):
        b = starts[i + 1][1] if i + 1 < len(starts) else len(src)
        out[name] = src[a:b]
    return out


def events(body):
    """(first_frame, last_frame, varname) for every interpolate() in the scene."""
    ev = []
    for m in re.finditer(r"const\s+(\w+)\s*=\s*interpolate\(\s*f\s*,\s*\[([^\]]*)\]", body):
        try:
            ks = [float(x) for x in m.group(2).replace("\n", " ").split(",") if x.strip()]
        except ValueError:
            continue
        if ks:
            ev.append((ks[0], ks[-1], m.group(1)))
    return sorted(ev)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode", default=None)
    ap.add_argument("--props", default=os.path.join(REPO, "out", "dispatch", "episode_props.json"))
    ap.add_argument("--lines", default=os.path.join(REPO, "out", "dispatch", "vo_lines.json"))
    a = ap.parse_args()

    ep = a.episode
    if ep is None:
        sys.path.insert(0, os.path.join(REPO, "scripts"))
        from caption_band_check import default_targets
        ep = default_targets()[0]

    props = json.load(open(a.props))
    scenes = props["scenes"]
    ld = json.load(open(a.lines))
    lines = ld["lines"] if isinstance(ld, dict) and "lines" in ld else ld
    bodies = scene_bodies(ep)

    print(f"{os.path.relpath(ep, REPO)}   {len(scenes)} shots   "
          f"{props['total']} frames ({props['total'] / FPS:.2f}s)\n")

    bad = 0
    for i, sc in enumerate(scenes):
        name = f"S{i + 1}"
        f0, dur = sc["from"], sc["dur"]
        t0, t1 = f0 / FPS, (f0 + dur) / FPS
        mine = [(j, l) for j, l in enumerate(lines)
                if l["start"] >= t0 - 0.02 and l["start"] < t1 - 0.02]
        ev = events(bodies.get(name, ""))
        print(f"{name}  f{f0}-{f0 + dur - 1}  {t0:6.2f}-{t1:6.2f}s  ({dur / FPS:.2f}s)")
        for j, l in mine:
            off = l["start"] - t0
            near = [e for e in ev if abs(e[0] / FPS - off) <= 1.2]
            mark = "  " if near else "??"
            print(f"   {mark} +{off:5.2f}s  L{j:<2} {l['text'][:62]}")
            if not near:
                bad += 1
        onsets = ", ".join(f"{v}@{s / FPS:.1f}s" for s, _, v in ev) or "(none)"
        print(f"      events: {onsets}")
        # a tail with no event at all is the S2 defect: the shot finishes early and holds
        last_ev = max((e[1] for e in ev), default=0.0) / FPS
        tail = (dur / FPS) - last_ev
        if tail > 3.0:
            print(f"      !! {tail:.1f}s of tail after the last event ends")
            bad += 1
        print()

    print(f"{bad} line(s)/tail(s) with no animation event within 1.2s.")
    print("?? marks a line whose shot starts no event near it. That is not automatically")
    print("wrong — a held beat is a choice — but every one should be a choice you made.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
