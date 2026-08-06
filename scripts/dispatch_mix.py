#!/usr/bin/env python3
"""Mix the Dispatch master audio: VO (dominant) + ducked music bed + SFX events,
with a real pre-button silence dip, normalized to -14 LUFS / TP <= -1.0 dBTP.

2026-07-21 SOUND-DESIGN OVERHAUL (owner: "ours is boring and reusing the same
sfx"). Every event is now PERFORMED, not placed:
  - VARIANT TAKES: sfx_bank.resolve(kind, episode_seed=DATE) shuffle-bags the
    6-take bank so no two plays of a kind reuse a take;
  - CLASS GAIN TIERS instead of flat volume=0.5 — hero hits peak ~-11 dBFS,
    standard accents ~-15, textures/sweeteners ~-19 (VO peaks -12..-6 stays
    the anchor);
  - DETERMINISTIC JITTER from crc32(DATE:idx): pitch (cents by family: UI ~40,
    impacts ~75, paper ~150, metal ~30 — metal variety lives in the modal
    variants), volume +/-1.5 dB, timing +/-15 ms (humanizes the grid);
  - PAN FROM THE PICTURE: each event carries the prop's storyboard x as a pan
    in [-1,1], scaled to max +/-0.35; hero payoff hits stay centered
    (mono-compatible for phone speakers);
  - FREQUENCY SLOTTING: the bed and all SUSTAINED sfx (whoosh/riser/paper/
    chain/creak) get a wide -2.5 dB dip at 3 kHz + a 100 Hz high-pass so they
    never fight VO intelligibility (2-5 kHz); short transients keep their
    energy — they read between syllables;
  - SCHEDULING ASSERT: no two consecutive events from the same sound FAMILY
    (spectral sameness is what reads "repetitive", not the count).

2026-07-22 "The checkpoint lever frozen at the midpoint" (Air Force EUL AI
data center dispatch). Episode-local: this file is rewritten per run with
EVENTS matched to THIS story's beats/storyboard; the doctrine above and the
machinery below CARRY OVER unchanged.
"""
import json, os, re, subprocess, sys, math, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(REPO, "out", "dispatch")
AUD = os.path.join(OUT, "audio")
FF = os.environ.get("FFMPEG_BIN", "ffmpeg")
SR = 44100
DATE = "2026-08-06"   # episode seed for the shuffle-bag + jitter


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr[-2000:])
        raise SystemExit(f"ffmpeg failed: {' '.join(cmd[:6])}...")
    return r


# --- sound families (spectral neighborhoods, for the repetition assert + jitter)
FAMILY = {
    "thud": "sub", "stamp": "sub", "boom": "sub", "paw": "sub",
    "clank": "metal", "chain": "metal", "klaxon": "metal",
    "ding": "bell", "chime": "bell",
    "tick": "click", "pop": "blip", "snap": "pluck",
    "whoosh": "air", "riser": "air",
    "paper": "texture", "creak": "texture",
    "caw": "bird",
}
SUSTAINED = {"whoosh", "riser", "paper", "chain", "creak"}   # get VO-slot EQ
PITCH_CENTS = {"sub": 75, "metal": 30, "bell": 25, "click": 40, "blip": 40,
               "pluck": 60, "air": 50, "texture": 150, "bird": 60}
# class -> target peak dBFS; bank takes peak at -6 dBFS, so gain = target+6 dB
CLASS_DB = {"hero": -11.0, "standard": -15.0, "texture": -19.0}


def jit(idx, salt, lo, hi):
    """Deterministic uniform in [lo,hi] from (DATE, event idx, salt)."""
    h = zlib.crc32(f"{DATE}:{idx}:{salt}".encode()) / 0xFFFFFFFF
    return lo + (hi - lo) * h


# SFX events cut to the picture, derived from vo_lines.json (out/dispatch/vo_lines.json,
# idx 0-8, this run's 9 spoken lines) plus fixed offsets into the retimed scenes
# (out/dispatch/episode_props.json > scenes[], scripts/build_scenes.py). Each event:
# (time, kind, class, pan) — pan is the prop's approximate storyboard x mapped to
# [-1,1], scaled by 0.35 in the graph.
_lines = json.load(open(os.path.join(OUT, "vo_lines.json")))["lines"]
L = {x["idx"]: x["start"] for x in _lines}
_TAIL = 2.6   # matches scripts/build_scenes.py TAIL (hold after the last word)
VIDEO_SECS = max(x["end"] for x in _lines) + _TAIL   # derive from VO; never hardcode

EVENTS = [
    # 2026-08-06, RE-DERIVED against the shipped take after the VO was re-cut. Times come
    # from vo_lines.json, never typed. Families alternate so no two consecutive events
    # share one (check_schedule hard-asserts). ONE riser, on the convergence.
    (0.00, "tick", "standard", -0.35),   # the two objects exist before anything is claimed a
    (0.41, "clank", "standard", 0.02),   # the machine attends, instantly
    (2.65, "thud", "hero", 0.0),   # the ban is drawn before it is spoken
    (5.31, "paper", "texture", 0.06),   # the two cities enter as two lit rectangles
    (8.67, "snap", "hero", 0.0),   # THE PRIMARY LOOP IS PLANTED
    (12.65, "pop", "standard", 0.1),   # the pull-back begins
    (15.20, "creak", "texture", -0.23),   # REVEAL ONE, the HEADROOM the capture side is built
    (18.57, "stamp", "hero", 0.0),   # the price lands on the room
    (21.43, "chime", "standard", -0.19),   # the rule Anchorage actually wrote, drawn as the on
    (24.69, "clank", "standard", 0.18),   # THROUGHLINE STATE TWO, scoped honestly. Claim c6 l
    (27.34, "tick", "standard", -0.15),   # the code opens, and it is NOT empty. A surveillanc
    (29.59, "thud", "standard", 0.22),   # REHOOK ONE. Not a hole in the law, a MISMATCH: the
    (32.65, "tick", "standard", -0.11),   # the objection gets a name, a district and the APPR
    (34.28, "clank", "standard", 0.26),   # ANCHORAGE'S REAL CARDS, and v1 gave them none. c11
    (37.75, "thud", "hero", 0.0),   # THE FILM'S TITLE, PAID. The frame is the still poi
    (41.01, "paper", "texture", 0.3),   # the corridor, and the primary loop touched once in
    (44.79, "snap", "hero", 0.0),   # THROUGHLINE STATE THREE and THE SECOND LOOP PLANTE
    (49.28, "pop", "standard", 0.34),   # the honest report
    (52.54, "creak", "texture", 0.01),   # the tool's competence asserted by REPETITION AND S
    (56.73, "stamp", "hero", 0.0),   # the mechanism opens
    (59.79, "chime", "standard", 0.05),   # the half the machine took
    (64.07, "clank", "standard", -0.28),   # REVEAL TWO and REHOOK TWO, the film's mechanism
    (67.75, "tick", "standard", 0.09),   # who the judgment half actually is
    (70.91, "thud", "standard", -0.24),   # the load arrives
    (74.38, "tick", "standard", 0.13),   # the curve breaks
    (75.60, "clank", "standard", -0.2),   # THE DIP and THROUGHLINE STATE FOUR
    (80.50, "thud", "hero", 0.0),   # the other side speaks and it is not a straw man. T
    (84.68, "paper", "texture", -0.16),   # the law drawn as a KNOWN OBJECT WITH FIXED CAPACIT
    (89.68, "snap", "hero", 0.0),   # the throughline object is BACK, and the thing that
    (93.25, "pop", "standard", -0.12),   # the idea floated at the table, drawn as a slip tha
    (96.21, "creak", "texture", 0.25),   # THE CONCESSION, drawn on a THING. The problem is r
    (98.97, "stamp", "hero", 0.0),   # THE SECOND LOOP PAYS WITH AN EVENT AND A UNIT. v1 
    (103.56, "chime", "standard", 0.29),   # the film's sharpest line, drawn
    (107.13, "riser", "hero", 0.0),   # the film's argument in one line gets the two opera
    (110.90, "tick", "standard", 0.33),   # REVEAL THREE and THE PRIMARY LOOP PAYS
    (113.76, "thud", "standard", 0.0),   # the one thing a viewer is meant to act on, drawn a
    (115.80, "tick", "standard", -0.33),   # the pre-button dip
    (117.94, "clank", "standard", 0.04),   # THE SIGNATURE SHOT, and it now states the thesis a
    (121.41, "thud", "hero", 0.0),   # the button
]


# THE MIX HAS AN ARC NOW (2026-07-31, round 6 panel note: "the mix is flat -- LRA 3.10").
#
# Two separate things were making it flat, and only one of them was the bed.
#
# 1. The bed sat at a constant 0.30 for the whole 91 seconds. A documentary bed that never
#    moves is wallpaper: it tells the ear that nothing in the argument is more important
#    than anything else, which is exactly the opposite of what this script does. The arc
#    below is written against the SCRIPT, not against a clock -- it thins hard under the
#    two concession lines (43.4s "so he's right that there's a hole" and 46.1s "Alaska has
#    a patchwork, not a process"), because a concession delivered over a full bed sounds
#    like a rhetorical move rather than an honest one, and it swells into the closing
#    questions at 82.5s where the piece stops arguing and starts asking.
#
# 2. Single-pass dynamic loudnorm was undoing whatever arc existed anyway. In dynamic mode
#    loudnorm is a slow AGC: it walks the gain toward the target continuously, so a bed
#    that drops 6 dB gets quietly pushed back up over the next few seconds and the range
#    collapses. That is where an LRA of 3.10 comes from. main() now measures the premix and
#    applies a LINEAR (static-gain) correction, which hits the same -14 LUFS without
#    touching the dynamics.
#
# Multipliers are relative to the bed's base level, so the shape lives here and the level
# lives in one place in the graph.
BED_ARC = [
    # 2026-08-06, re-derived on the shipped take. Two real floors (the desk, the pre-button),
    # two peaks (the mechanism, the thesis). Depth set so LRA clears its 6.0-9.0 target.
    (0.00, 0.874),
    (10.36, 1.21),
    (24.76, 1.378),
    (36.04, 1.042),
    (46.90, 1.462),
    (56.26, 0.706),
    (65.32, 1.63),
    (78.90, 1.336),
    (93.20, 0.58),
    (104.66, 1.252),
    (115.14, 1.546),
    (118.84, 0.42),
    (124.04, 1.05),
    (125.84, 0.9),
]

# A WIND BED FOR THE COUNTRY THE FILM DRIVES INTO. The same panel note asked for ambience,
# and undifferentiated room tone under the whole piece would be another flat layer. This is
# geography instead: nothing but the bed on the Railbelt side, and wind from the moment the
# VO says "now go north, onto state land, where neither reaches" until the comment count
# lands. It is synthesised (brown noise, lowpassed, slowly gusting) rather than sampled, so
# it is deterministic and carries no attribution.
AMB_IN, AMB_OUT = 21.9, 42.6
AMB_LEVEL = 0.085


def _assert_per_run_data_covers_the_film():
    """BED_ARC and EVENTS are PER-RUN DATA. Fail loudly when they belong to another film.

    This has already cost a panel round once. On 2026-08-04 the arc in this file still
    carried the previous episode's breakpoints, labelled "go north" and "the wellhead
    lease", with its last two nodes at 82.5s and 87.9s on a film that ended at 83.76s. The
    bed spent the whole run following someone else's story and its final move never played.
    Two judges measured the consequence from opposite directions, LRA 3.0 across the piece
    and "the arc is not in the dynamics, so the punch cannot punch", and neither could see
    the cause from the audio alone. It is the same class as the stale-frame and
    wrong-filmstrip-anchor bugs: an artifact read BY PATH that looked plausible and
    described a different film.

    The 120-second format makes it worse rather than better. An arc left over from a 90s
    run now stops two thirds of the way through and leaves the last forty seconds flat,
    which is exactly the stretch the two-minute format is fighting hardest to hold.

    A warning rather than a hard fail: a run may legitimately resolve its bed a little
    before the last frame, and blocking a mix on a judgement call is worse than a loud
    line in the log. The numbers make the diagnosis immediate either way.
    """
    warn = []
    # `for t, *_` not `for t, _`: BED_ARC is hand-rewritten every run, and a node written
    # with a trailing comment value or a third element would raise inside the guard that
    # exists to protect the mix, killing it at import. EVENTS is already tolerant.
    arc_end = max(t for t, *_ in BED_ARC) if BED_ARC else 0.0
    # 0.95, not 0.9. The arc is supposed to RESOLVE at the end rather than stop near it, and
    # the looser threshold missed a live case: the 2026-08-05 film ran 88.8s against an arc
    # ending at 83.7s, which is 94 percent and would have passed while leaving the last five
    # seconds, the button, with no bed move at all.
    if arc_end < VIDEO_SECS * 0.95:
        warn.append(f"BED_ARC ends at {arc_end:.1f}s but the film runs {VIDEO_SECS:.1f}s. The last "
                    f"{VIDEO_SECS - arc_end:.1f}s have no bed automation. Re-anchor BED_ARC to THIS "
                    f"film's beats from vo_lines.json.")
    if arc_end > VIDEO_SECS + 1.0:
        warn.append(f"BED_ARC runs to {arc_end:.1f}s past a {VIDEO_SECS:.1f}s film; its last moves "
                    f"never play. These are the previous episode's breakpoints.")
    ev_end = max((t for t, *_ in EVENTS), default=0.0)
    if ev_end < VIDEO_SECS * 0.85:
        warn.append(f"EVENTS stop at {ev_end:.1f}s on a {VIDEO_SECS:.1f}s film; the last "
                    f"{VIDEO_SECS - ev_end:.1f}s carry no motivated sound. Re-anchor EVENTS to "
                    f"THIS film's beats.")
    if ev_end > VIDEO_SECS + 1.0:
        warn.append(f"EVENTS run to {ev_end:.1f}s past a {VIDEO_SECS:.1f}s film; those sounds fire "
                    f"after the last frame.")
    for w in warn:
        print(f"  !! STALE PER-RUN DATA: {w}")
    return warn


_assert_per_run_data_covers_the_film()


def pw_expr(points, var="t"):
    """A piecewise-linear ffmpeg volume expression through (time, value) breakpoints.

    Held flat before the first point and after the last, linear in between. Single-quoted
    at the call site so the commas survive the filtergraph parser.

    FLAT SUM OF GATED SEGMENTS, NOT NESTED ifs (rewritten 2026-08-05, and it was a real
    outage rather than a tidy-up). This function used to wrap one `if(lt(t,..),..,..)`
    around the previous result per breakpoint, so the nesting depth equalled the number of
    breakpoints. ffmpeg's expression evaluator gives up somewhere above roughly a hundred
    levels, and it does not fail with "too deep", it fails with a bare "Invalid argument"
    on the whole filtergraph, which points at nothing.

    That threshold is a function of THE NARRATION, not of the code: the bed lifts into
    every inter-line gap of 0.5s or longer, at four breakpoints each. A VO with 25 such
    gaps, which is an ordinary 90-second read and exactly what this run produced, emits
    106 nested ifs and the entire mix dies. Any future run with a slightly breathier
    delivery would have hit it too.

    A sum of half-open interval gates has NO nesting at all, so the depth is constant no
    matter how many breakpoints there are. `gte(t,a)*lt(t,b)` is used rather than
    `between(t,a,b)` on purpose: between() is inclusive at both ends, so adjacent segments
    would both fire on their shared boundary and the sum would double there.
    """
    pts = sorted(points)
    terms = [f"lt({var}\\,{pts[0][0]:.3f})*{pts[0][1]:.4f}"]
    for (t0, v0), (t1, v1) in zip(pts, pts[1:]):
        span = t1 - t0
        if span <= 0:
            continue
        seg = f"({v0:.4f}+({v1 - v0:.4f})*({var}-{t0:.3f})/{span:.3f})"
        terms.append(f"gte({var}\\,{t0:.3f})*lt({var}\\,{t1:.3f})*{seg}")
    terms.append(f"gte({var}\\,{pts[-1][0]:.3f})*{pts[-1][1]:.4f}")
    return "(" + "+".join(terms) + ")"


# THE BREATH BEFORE THE PAYOFF, NOW SELF-FITTING (hardened 2026-07-30 after code review).
#
# This used to be two hand-tuned constants, an offset from a chosen line and a fixed 0.90s
# length. That is fragile in exactly the way the 07-29 comment it replaced already warned
# about: on this run the chosen gap measured 0.84s while the dip was 0.90s, so the silence
# overlapped speech at BOTH ends and the "real pre-button silence" the audio gate checks for
# was landing on top of the two lines it was supposed to sit between.
#
# The fix is to stop guessing. Measure every real inter-line gap in the back half, take the
# widest one, and fit the dip inside it with a margin at each end. A dip can then never be
# wider than the hole it goes in, on this run or any future one, whatever the VO timing turns
# out to be.
_MARGIN = 0.10          # keep this much clear speech either side of the dip
_MIN_DIP = 0.35         # below this it is not an audible breath, so do not bother
_MAX_DIP = 0.90         # above this it reads as a dropout rather than a beat

def _fit_silence_dip(lines, after_frac=0.5):
    """Return (start_seconds, length_seconds) for the pre-button breath, fitted to a REAL gap."""
    if len(lines) < 3:
        return None, 0.0
    end = max(x["end"] for x in lines)
    cands = []
    for a, b in zip(lines, lines[1:]):
        gap = b["start"] - a["end"]
        # only the back half, and never the gap immediately before the final line, so the
        # button itself still lands into its own silence rather than sharing one
        if b["start"] >= end * after_frac and gap > 0:
            cands.append((gap, a["end"], b["start"]))
    if not cands:
        return None, 0.0
    gap, gstart, gend = max(cands)
    usable = gap - 2 * _MARGIN
    if usable < _MIN_DIP:
        return None, 0.0
    dip = min(_MAX_DIP, usable)
    start = gstart + _MARGIN + (usable - dip) / 2.0     # centre it in the hole
    return round(start, 3), round(dip, 3)


SILENCE_DIP_AT, DIP_LEN = _fit_silence_dip(_lines)
if SILENCE_DIP_AT is None:
    # No gap in the back half is wide enough to hold an audible breath. Say so loudly rather
    # than silently placing one on top of speech.
    print("dispatch_mix: WARNING no back-half VO gap wide enough for a silence dip; skipping it")
    SILENCE_DIP_AT, DIP_LEN = 0.0, 0.0
else:
    print(f"dispatch_mix: silence dip {DIP_LEN:.2f}s at {SILENCE_DIP_AT:.2f}s "
          f"(fitted inside a real VO gap, not hand-tuned)")


def check_schedule(events):
    """No two consecutive events share a sound family — spectral repetition is
    the 'boring sfx' failure mode. Also: at most one riser per episode."""
    seq = sorted(events, key=lambda e: e[0])
    for a, b in zip(seq, seq[1:]):
        fa, fb = FAMILY[a[1]], FAMILY[b[1]]
        if fa == fb:
            raise SystemExit(
                f"SFX SCHEDULE: consecutive '{fa}' family events at {a[0]:.2f}s "
                f"({a[1]}) and {b[0]:.2f}s ({b[1]}) — recast one to a different "
                f"family (spectral sameness reads as repetition).")
    risers = [e for e in events if e[1] == "riser"]
    if len(risers) > 1:
        raise SystemExit(f"SFX SCHEDULE: {len(risers)} risers — reserve the riser "
                         f"for exactly one moment per episode.")
    print(f"sfx schedule OK: {len(events)} events, no consecutive family repeats")


def main():
    sys.path.insert(0, HERE)
    from sfx_bank import resolve

    check_schedule(EVENTS)
    os.makedirs(os.path.join(AUD, "sfx"), exist_ok=True)

    # 1) deal a variant take per EVENT (shuffle-bag, episode-seeded) — events of
    #    the same kind get different takes, in deterministic order
    takes = []
    for i, (t, kind, cls, pan) in enumerate(EVENTS):
        takes.append(resolve(kind, episode_seed=DATE))

    # 2) assemble inputs: [0]=VO padded to VIDEO, [1]=music looped/trimmed, then SFX,
    #    then [last]=synthesised wind for the north block
    inputs = ["-i", os.path.join(AUD, "vo.wav"), "-i", os.path.join(OUT, "music_bed.wav")]
    for p in takes:
        inputs += ["-i", p]
    amb_idx = 2 + len(takes)
    inputs += ["-f", "lavfi", "-i",
               f"anoisesrc=color=brown:sample_rate={SR}:amplitude=0.9:duration={VIDEO_SECS:.3f}"]

    fc = []
    # VO: pad to full length, keep dominant; split (one copy to mix, one as sidechain key)
    # THE NARRATOR LEANS IN AND BACKS OFF, which is the only thing that can actually move
    # LRA on this piece (round 13, 14 and 15, judge 2, three times, and the number went the
    # wrong way in between). The bed arc was real and inaudible in the statistic for a simple
    # reason: LRA is computed from SHORT-TERM loudness, the VO dominates short-term loudness
    # by about 13 dB, and a bed automation 13 dB down cannot move a measure the voice owns.
    # So the same script-shaped curve is applied to the VOICE, at a third of the depth: a
    # documentary narrator does drop under a concession and does lift into a closing
    # question, and unlike the bed it is the thing the meter is listening to.
    vo_arc = pw_expr([(t, 1.0 + (m - 1.0) * 0.78) for t, m in BED_ARC])
    fc.append(f"[0:a]aformat=sample_rates={SR}:channel_layouts=stereo,apad=whole_dur={VIDEO_SECS},"
              f"volume=volume={vo_arc}:eval=frame,asplit=2[vo][vok]")
    # Music: loop, trim, base level, VO-slot EQ (wide -2.5dB dip at 3k so the bed
    # never fights intelligibility), scripted dip before the button, gentle lift
    # in the post-VO tail where there's no voice to serve
    dip0, dip1 = SILENCE_DIP_AT, SILENCE_DIP_AT + DIP_LEN
    vo_end = max(x["end"] for x in _lines)
    # AND THE TAIL LIFT WAS APPENDED OUT OF ORDER. BED_ARC already ends with points at
    # 81.2, 82.4 and 83.7; appending (vo_end + 0.4, 1.60) put a t=81.5 point AFTER the
    # t=83.7 one, so the piecewise envelope was non-monotonic in time and the lift the
    # comment above promises never happened. A judge measured the 2.6s tail, the one
    # stretch in the film with no voice at all, sitting at -30.5 dBFS and fading rather
    # than opening. Sort by time, and hold the lift long enough to be heard before the
    # credit fade takes it.
    arc = pw_expr(sorted(BED_ARC + [(vo_end + 0.4, 1.62), (vo_end + 1.4, 1.55)]))

    # OPEN THE BED INTO THE GAPS THAT ACTUALLY EXIST (2026-08-05).
    #
    # Three judges measured the same thing from three directions: the bed sits 9 to 15 dB
    # under the VO and stays there THROUGH the gaps, so the mix never breathes and LRA
    # sticks at about 4.1 against a 6 to 9 target. The longest gap in the film measured
    # within 1 dB of the average gap, which is the signature of a bed that is not
    # responding to the voice at all in the direction that matters.
    #
    # Chasing this through the sidechain compressor did not work: shortening the release
    # from 320ms to 150ms changed the delivered LRA by nothing measurable. So this stops
    # asking the compressor to infer the gaps and states them. The gaps are KNOWN, to the
    # word, in the same forced-alignment data the captions are built from. Each one over
    # half a second gets an explicit lift, ramped in and out so it swells rather than
    # steps, applied downstream of the duck where it is a clean level move.
    gap_lift = [(0.0, 1.0)]
    try:
        _w = json.load(open(os.path.join(AUD, "words.json")))["words"]
        _gaps = [(a["e"], b["s"]) for a, b in zip(_w, _w[1:]) if b["s"] - a["e"] >= 0.5]
        for a, b in _gaps:
            gap_lift += [(a + 0.05, 1.0), (a + 0.22, 2.05), (b - 0.22, 2.05), (b - 0.05, 1.0)]
        print(f"bed opens into {len(_gaps)} gaps of 0.5s or longer "
              f"({sum(b - a for a, b in _gaps):.1f}s of room)")
    except Exception as e:
        print(f"bed gap-lift SKIPPED ({e}); the mix will be flatter than it should be")
    gap_expr = pw_expr(sorted(gap_lift))
    fc.append(
        f"[1:a]aformat=sample_rates={SR}:channel_layouts=stereo,aloop=loop=-1:size={int(SR*200)},"
        f"atrim=0:{VIDEO_SECS},equalizer=f=3000:t=q:w=1:g=-2.5,volume=0.30[bedraw]"
    )
    # sidechain duck the bed under the VO (uses the key copy)
    # THE BED NEVER OPENED INTO GAPS THAT ALREADY EXISTED (2026-08-04). Two judges
    # measured this independently in the same round: the VO leaves 21 gaps of 0.35s or
    # longer, 13 of them over 0.50s, about 11.9s of silence in total, and the bed sat
    # flat through all of them. The run's own evidence pack had been claiming there was
    # only one such gap and that the flat loudness range was structural, so the fix kept
    # being aimed at cutting VO instead of at this line.
    #
    # release=320ms was the cause. After a line ends the gain recovers on a 320ms time
    # constant, so a 0.5s gap closes again before the bed has come up meaningfully and a
    # 0.7s gap only gets part way. At 150ms the bed is substantially back inside every
    # gap over about 0.4s, which is 13 of them. Ratio eases 9 -> 6 so the duck is a lean
    # rather than a clamp, and the threshold rises slightly so quiet consonants stop
    # holding the bed down through the tail of a line.
    fc.append(f"[bedraw][vok]sidechaincompress=threshold=0.055:ratio=6:attack=8:release=150:makeup=1[bedduck]")
    # THE ARC GOES AFTER THE DUCK, NOT BEFORE IT. Placed upstream, the arc feeds a ratio-9
    # compressor: a quieter bed sits closer to the threshold, gets less gain reduction, and
    # comes out the far side pushed back toward where it started. The compressor was undoing
    # the shape. Downstream it is a clean level move on an already-ducked bed, so the written
    # arc is the arc you hear.
    fc.append(f"[bedduck]volume=volume={gap_expr}:eval=frame,"
              f"volume=volume={arc}:eval=frame,"
              f"volume=enable='between(t,{dip0},{dip1})':volume=0.015[bed]")

    # SFX: per-event performance — pitch/volume/timing jitter, class gain, pan
    sfx_labels = []
    for i, (t, kind, cls, pan) in enumerate(EVENTS):
        idx = 2 + i
        fam = FAMILY[kind]
        cents = jit(i, "pitch", -PITCH_CENTS[fam], PITCH_CENTS[fam])
        rate = 2 ** (cents / 1200)
        gain_db = CLASS_DB[cls] + 6.0 + jit(i, "vol", -1.5, 1.5)   # bank peaks -6
        t_actual = max(0.0, t + jit(i, "time", -0.015, 0.015))
        ms = int(t_actual * 1000)
        p = max(-1.0, min(1.0, pan)) * 0.35
        gl, gr = math.cos((p + 1) * math.pi / 4), math.sin((p + 1) * math.pi / 4)
        chain = [f"[{idx}:a]aformat=sample_rates={SR}:channel_layouts=stereo",
                 f"asetrate={int(SR * rate)}", f"aresample={SR}"]
        if kind in SUSTAINED:
            chain += ["highpass=f=100", "equalizer=f=3000:t=q:w=1:g=-2.5"]
        chain += [f"volume={10 ** (gain_db / 20):.4f}",
                  f"pan=stereo|c0={gl:.3f}*c0|c1={gr:.3f}*c1",
                  f"adelay={ms}|{ms}"]
        lbl = f"s{i}"
        fc.append(",".join(chain) + f"[{lbl}]")
        sfx_labels.append(f"[{lbl}]")

    # WIND for the north block: brown noise, lowpassed to a distant hiss, gusting on a
    # 9.5s cycle that is deliberately prime to nothing else in the mix so it never lines up
    # with the sfx grid, opened and closed by fades so it exists only where the film is
    # standing on state land.
    gust = "0.62+0.38*sin(2*PI*t/9.5)+0.12*sin(2*PI*t/3.7)"
    fc.append(
        f"[{amb_idx}:a]aformat=sample_rates={SR}:channel_layouts=stereo,"
        f"highpass=f=70,lowpass=f=560,equalizer=f=3000:t=q:w=1:g=-2.5,"
        f"volume=volume={gust.replace(',', chr(92) + ',')}:eval=frame,"
        f"volume={AMB_LEVEL},"
        f"afade=t=in:st={AMB_IN}:d=1.8,afade=t=out:st={AMB_OUT}:d=2.6[amb]"
    )

    # mix VO + bed + wind + all sfx
    mix_in = "[vo][bed][amb]" + "".join(sfx_labels)
    n = 3 + len(sfx_labels)
    fc.append(f"{mix_in}amix=inputs={n}:normalize=0:dropout_transition=0[premix]")

    filtergraph = ";".join(fc)
    master = os.path.join(AUD, "master.wav")
    premix = os.path.join(AUD, "premix.wav")

    # TWO PASSES, AND THE SECOND ONE IS LINEAR. See the BED_ARC note: single-pass loudnorm
    # is a slow AGC and it eats the arc it is handed. Measure the premix, then apply a
    # static gain that hits the same -14 LUFS while leaving the dynamics exactly as mixed.
    run([FF, "-y", *inputs, "-filter_complex", filtergraph, "-map", "[premix]",
         "-ar", str(SR), "-ac", "2", "-t", str(VIDEO_SECS), premix])

    p = subprocess.run([FF, "-i", premix, "-af",
                        "loudnorm=I=-14:TP=-2.0:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", p.stderr, re.S)
    if not m:
        raise SystemExit("dispatch_mix: loudnorm analysis pass produced no JSON")
    a = json.loads(m.group(0))
    print(f"premix measured: {a['input_i']} LUFS  TP {a['input_tp']}  LRA {a['input_lra']}")
    ln = (f"loudnorm=I=-14:TP=-2.0:LRA=11:linear=true"
          f":measured_I={a['input_i']}:measured_TP={a['input_tp']}"
          f":measured_LRA={a['input_lra']}:measured_thresh={a['input_thresh']}"
          f":offset={a['target_offset']}:print_format=summary")
    run([FF, "-y", "-i", premix, "-af", f"{ln},alimiter=limit=0.89:level=false",
         "-ar", str(SR), "-ac", "2", master])
    os.remove(premix)
    print("wrote", master)

    # write sfx_events.json for the gate (schema: t/kind as before, + performance)
    json.dump({"events": [
                   {"t": t, "kind": k, "class": c, "pan": p,
                    "take": os.path.basename(takes[i]), "family": FAMILY[k]}
                   for i, (t, k, c, p) in enumerate(EVENTS)],
               "silence_dip_at": SILENCE_DIP_AT, "count": len(EVENTS)},
              open(os.path.join(AUD, "sfx_events.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
