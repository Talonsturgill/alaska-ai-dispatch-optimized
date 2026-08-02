#!/usr/bin/env python3
"""Compute scene frame boundaries from the VO line timings so the timeline stays
in sync with the narration automatically. Scene i begins at the start of a mapped
VO line; S1 covers lines 0-1. Writes episode_props.json {captions, scenes, total}.
"""
import json, os

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "out", "dispatch")
FPS = 30
TAIL = 2.6  # hold after the last word

# scene -> index of the VO line that starts it. 2026-07-22 "the checkpoint lever frozen
# at the midpoint" has 7 scenes (S1..S7 in video-engine/src/Episode.tsx, SCENE_COMPONENTS)
# mapped onto 9 VO lines (vo_lines.json has exactly 9 lines this run, some scenes span 2
# lines of VO): S1 line0 (map/counter+offer), S2 line1 (parcels+NOT FOR SALE+"not a sale"
# is still S2's content but starts visually at the parcels line), S3 line3 (EUL
# mechanism), S4 line4 (MachineShadow/Moriarty), S5 line5 (Hollister), S6 line6 (lever
# return, covers "nobody picked"+"still open"), S7 line8 (closing question+hold+loop).
# (keep this list's length equal to SCENE_COMPONENTS.length every run -- an earlier list
# here silently mismatched it once and Episode fell back to hardcoded DEFAULT_BOUNDS.)
# 2026-07-23 "Counting Belugas From Orbit": 7 scenes (S1..S7) onto 11 VO lines.
# S1 L0 (silt/find-the-whale), S2 L1 (331+decline), S3 L2 (from space, SatelliteEye),
# S4 L3-L4 (GAIA+partners, the learning pipeline), S5 L5-L6 (cannot-count-yet, needs a
# clear look), S6 L7-L8 (June 2025 empty, sky booked), S7 L9-L10 (holding on, the question).
# 2026-07-25 "The One It Didn't Hear": 7 scenes (S1..S7) onto 12 VO lines. Shot boundaries
# are anchored to VO LINE STARTS so the picture can never drift from the words (the Gate 0B/0C
# finding that killed the first board: the collapse was spoken at 19.6s and drawn at 33.9s).
# S1 L0-L1 (Otto at work + the second job), S2 L2 (duration lanes + the gate latching),
# S3 L3-L4 (boundary + travel out + THE COLLAPSE), S4 L5 (signature shot + the dark lamp),
# S5 L6-L7 (still heard + by hand + the boulder), S6 L8 (crate + money),
# S7 L9-L11 (wireframe twin + calendar + button).
# 2026-07-26 "The Field That Stopped in 2019": NINE scenes (S1..S9 in Episode.tsx) onto
# 14 VO lines. Shot boundaries are anchored to VO LINE STARTS so the picture can never
# drift from the words. S1 L0 (the letter opens), S2 L1-L2 (the 200 baseline + McCabe's
# fair defense, VOICED not merely posted), S3 L3-L4 (the mouth cranks wide + the intake +
# the burst from the unchanged stem), S4 L5 (the plain letter + 3,048 into one finite
# tape), S5 L6 (three Alaskans reacting three different ways), S6 L7-L8 (the machine opens
# on the capped third pipe + the pawl + the two records), S7 L9-L10 (the arrow on the
# doorless wall + the door swinging free), S8 L11-L12 (NO ALGORITHM + the signature shot),
# S9 L13 (the button, back at the same table, staying interior).
# 2026-08-02 "The Copy In The Mud": TWELVE shots (S1..S12 in video-engine/src/Ep0802.tsx) onto
# 16 VO lines. Shot boundaries are anchored to VO LINE STARTS so the picture can never drift
# from the words. S1 L0 (the lamp arrives + the notches), S2 L1 (the stack + THE BLADE WIPE),
# S3 L2 (the bench lamp match-cut + the USGS AVO plate), S4 L3 (THE DROP through the waterline
# + the coring punch), S5 L4 (eight columns rise + the running count to 70), S6 L5 (the sort
# down to 37), S7 L6-L7 (THE CARD PRINTS WIDE + the shard's machined edge), S8 L8 (the grain
# runs the chain), S9 L9 (the three name plates + the strips stack + MAGENTA FUSES),
# S10 L10-L11 (out of register + THE SIGNATURE PULL-BACK + the set-down), S11 L12-L13 (the dark
# bench + the calipers + COULD and COULDN'T + the crumb lands), S12 L14-L15 (the button + the
# lamp withdrawing onto the unread stripe, which is frame 1 unlit).
SCENE_START_LINE = [0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 14]


def _apply_caption_fixups(caps):
    """On-screen captions are force-aligned from Whisper's transcript of the
    PHONETICALLY-respelled audio, so proper-noun respellings ('Ex Prize', 'DRY-ad',
    'Nana' for Nenana) leak onto screen as typos (the 2026-07-20 panel caught all three
    as hard blockers). vo_script.json declares a `caption_fixups` {phonetic: display}
    map; apply it to every cue text (case-insensitive, word-boundary) so the REAL
    spelling always shows. Permanent pipeline fix so no future run leaks a respelling."""
    import re as _re
    sp = os.path.join(OUT, "vo_script.json")
    fixups = json.load(open(sp)).get("caption_fixups", {}) if os.path.exists(sp) else {}
    if not fixups:
        return caps
    # Use alnum lookarounds, NOT \b: \b fails on tokens whose edge char is punctuation
    # (e.g. "A.I." ends in '.', so \b after it never matches and the fixup silently no-ops —
    # the 2026-07-21c panel caught "A.I." leaking on screen while NOAA/GAIA normalized fine).
    # Longest keys first so a key that is a prefix of another can't pre-empt it.
    for c in caps:
        t = c.get("text", "")
        for wrong, right in sorted(fixups.items(), key=lambda kv: -len(kv[0])):
            t = _re.sub(r"(?<![A-Za-z0-9])" + _re.escape(wrong) + r"(?![A-Za-z0-9])", right, t, flags=_re.IGNORECASE)
        c["text"] = t
    return caps


def _rebalance_cues(caps):
    """Never break a caption between a number and its unit, or inside a proper noun.

    ADDED 2026-08-02 after a panel judge caught both failure modes in one film. Forced
    alignment chunks cues by width, which is correct for timing and blind to sense, so it
    produced "70 ash layers out of 8" / "tubes, a record they call virtually" (a number torn
    off its unit) and "It's confident about Katmai, Fisher" / "Caldera and Emmons Lake,
    because" (a two-word proper noun split across cards). Both read as errors to a viewer,
    because the eye finishes the line before the next one arrives.

    The fix is a MERGE, never a re-time: when a cue ends on a dangling token, it absorbs the
    next cue and takes its end time. Timing stays exactly as aligned, so caption sync is
    untouched; only the grouping changes. Merging is capped so a cue can't grow past what
    fits on two lines at phone size.
    """
    DANGLING = ("of", "out of", "the", "a", "an", "to", "in", "on", "and", "or", "for",
                "at", "by", "with", "from", "into", "than", "as", "is", "was", "which")
    MAXLEN = 62
    out = []
    i = 0
    while i < len(caps):
        cur = dict(caps[i])
        while i + 1 < len(caps):
            t = cur["text"].rstrip()
            last = t.split()[-1] if t.split() else ""
            nxt = caps[i + 1]["text"].strip()
            first = nxt.split()[0] if nxt.split() else ""
            bad = (
                last.lower().strip(",.") in DANGLING            # dangling function word
                or last.rstrip(",.").isdigit()                  # a number torn from its unit
                # a proper noun split across cards: "... Fisher" / "Caldera ..."
                or (last.rstrip(",").istitle() and first.istitle() and not last.endswith("."))
            )
            if not bad or len(t) + 1 + len(nxt) > MAXLEN:
                break
            cur["text"] = t + " " + nxt
            cur["end"] = caps[i + 1]["end"]
            i += 1
        out.append(cur)
        i += 1
    return out


def main():
    lines = json.load(open(os.path.join(OUT, "vo_lines.json")))["lines"]
    caps = _rebalance_cues(_apply_caption_fixups(json.load(open(os.path.join(OUT, "captions.json")))))
    start = {L["idx"]: L["start"] for L in lines}
    last_end = max(L["end"] for L in lines)
    total_s = last_end + TAIL
    total_f = round(total_s * FPS)

    bounds = [round(start[si] * FPS) for si in SCENE_START_LINE]
    scenes = []
    for i, b in enumerate(bounds):
        end = bounds[i + 1] if i + 1 < len(bounds) else total_f
        scenes.append({"from": b, "dur": end - b})

    # THE VO LINE START TABLE, and it is not a convenience (2026-08-02).
    # Scenes used to hardcode beat times as ABSOLUTE seconds copied off the storyboard. That
    # silently rots the moment the VO is re-synthesized, because a new take shifts every line
    # start by a different amount (this run: up to 1.8s of drift between the archived board and
    # the re-synth). The picture then plays against words it was not cut to, and no gate catches
    # it because the scene BOUNDARIES are still correct. Shipping the line table lets a scene
    # anchor each beat to the VO LINE IT BELONGS TO, so the film re-times itself with the voice.
    props = {"captions": caps, "scenes": scenes, "total": total_f,
             "lines": [round(L["start"], 3) for L in sorted(lines, key=lambda x: x["idx"])]}
    # voice-acting data (scripts/vo_envelope.py): per-frame mouth envelope + the
    # vo-director's emphasis accents, for lib/voice.tsx. Optional, additive.
    mt = os.path.join(OUT, "mouth_track.json")
    ac = os.path.join(OUT, "accents.json")
    if os.path.exists(mt):
        props["mouth"] = json.load(open(mt))["values"]
    if os.path.exists(ac):
        props["accents"] = json.load(open(ac))
    json.dump(props, open(os.path.join(OUT, "episode_props.json"), "w"))
    print(f"total={total_f}f ({total_s:.2f}s)  mouth={'y' if 'mouth' in props else 'n'} accents={len(props.get('accents', []))}")
    for i, s in enumerate(scenes):
        print(f"  S{i+1}: from={s['from']} dur={s['dur']} ({s['dur']/FPS:.2f}s)")


if __name__ == "__main__":
    main()
