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
DATE = "2026-08-03"   # episode seed for the shuffle-bag + jitter


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
    # ---- 2026-08-03 "The Days You Are Allowed To Burn". 10 shots, 17 VO lines, 30 beats.
    # Times are DERIVED from the shipped take's vo_lines.json, not typed, so a re-synth moves
    # the sound with the picture. Every event is motivated by a visible mechanical action in its
    # own beat. The single riser is spent on the drain, where the prohibition map tears loose.
    (0.00, "tick", "standard", -0.11),   # THE WASH FLOODS OUT
    (2.73, "clank", "texture", -0.28),   # THE COUNTER RUNS AWAY
    (5.00, "pop", "standard", 0.28),   # THE SECOND COUNTER IS DEAD
    (8.58, "thud", "hero", 0.00),   # NSF SETS DOWN
    (11.50, "clank", "standard", -0.17),   # UAF SLIDES IN AND LOCKS
    (14.74, "stamp", "hero", 0.00),   # THE FIGURE STAMPS
    (17.95, "pop", "standard", 0.00),   # THE TORCH TILTS
    (20.65, "creak", "texture", 0.08),   # THE LINE CRAWLS
    (24.21, "tick", "standard", -0.24),   # ONE TREATED PATCH
    (27.64, "snap", "hero", 0.00),   # THE CRADLE IS EMPTY
    (31.37, "clank", "standard", 0.11),   # THE ENGINE ASSEMBLES
    (33.51, "tick", "standard", -0.08),   # THE INTAKE IS RE-CUT
    (36.06, "thud", "standard", -0.16),   # THE REJECT CHUTE
    (38.12, "clank", "hero", 0.00),   # THE PUNCH
    (39.89, "tick", "standard", 0.18),   # PULL BACK ALONG THE RIBBON
    (42.45, "paper", "standard", 0.01),   # THE SHEET IS PUSHED ACROSS
    (44.11, "tick", "texture", 0.16),   # THE PLANNER STAYS BEHIND
    (45.83, "clank", "hero", 0.00),   # FOUR FIELDS COLLIDE
    (48.35, "thud", "texture", -0.07),   # THE GROUND UNDER ALL FOUR
    (50.85, "paper", "texture", 0.17),   # FOUR HANDS ARRIVE
    (54.21, "clank", "standard", -0.21),   # THE PLATES TURN TO FACE
    (58.30, "tick", "hero", 0.00),   # THE RULE SNAPS IN
    (60.39, "boom", "standard", 0.07),   # FOUR SEASONS BURN PAST
    (63.17, "snap", "hero", 0.00),   # THREE ARROWS STRIKE
    (65.14, "creak", "texture", -0.14),   # THE ARROW DISASSEMBLES
    (67.96, "clank", "standard", -0.18),   # THE TORCH SWINGS DOWN
    (70.96, "paper", "texture", 0.19),   # THE BLANK SHEET LOWERS
    (74.01, "riser", "hero", 0.00),   # THE WASH DRAINS OFF
    (77.77, "chime", "hero", 0.00),   # THE WINDOWS OPEN
    (80.75, "tick", "standard", -0.11),   # THE PULASKI FLIPS
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
    # REWRITTEN 2026-08-04. The arc that was here belonged to a different episode: its
    # breakpoints were labelled "go north", "the wellhead lease" and "New York comparison",
    # and its last two nodes sat at 82.5s and 87.9s on a film that ends at 83.76s. So the
    # bed was following someone else's story and the last move never played. Two judges
    # measured the consequence from opposite directions, LRA 3.0 across the whole piece and
    # "the arc is not in the dynamics, so the punch cannot punch". These nodes are this
    # film's beats, taken from vo_lines.json, and the range is deliberately wider.
    (0.0,  0.96),   # cold open: decades of days you must not burn
    (5.0,  1.18),   # "Nobody has mapped the days you can" -- the inversion, lift
    (8.1,  1.30),   # the award lands
    (17.8, 1.02),   # what a prescribed burn is, explanatory, step back
    (23.9, 0.90),   # "It works, and Alaska barely uses it"
    (27.2, 0.82),   # NSF says the state lacks the tools -- the problem, quietest so far
    (31.1, 1.10),   # the machine reads decades of weather -- build
    (38.1, 1.34),   # "That isn't a forecast. It's a count of safe days." -- the turn
    (45.7, 1.06),   # four entities over one piece of ground
    (54.5, 0.92),   # the grant pays to get them talking
    (58.0, 0.62),   # THE HONEST TURN: "But it isn't finished."
    (63.1, 0.56),   # who pays when a burn escapes -- the floor of the film
    (67.3, 0.98),   # "But nothing moves without that count" -- rebuild
    (73.9, 1.26),   # the wash drains
    (77.7, 1.55),   # the windows open. The payoff, and the loudest the bed gets.
    (81.2, 1.20),   # tail under the credit
    # RESOLVE, DON'T CUT. A judge measured the bed still at about -25 dBFS a tenth of a
    # second from the last frame, ramping off in roughly 60ms, so the film's final audible
    # moment was a splice rather than an ending. Fade it under the credit card instead.
    (82.9, 0.94),
    (83.7, 0.00),
]

# A WIND BED FOR THE COUNTRY THE FILM DRIVES INTO. The same panel note asked for ambience,
# and undifferentiated room tone under the whole piece would be another flat layer. This is
# geography instead: nothing but the bed on the Railbelt side, and wind from the moment the
# VO says "now go north, onto state land, where neither reaches" until the comment count
# lands. It is synthesised (brown noise, lowpassed, slowly gusting) rather than sampled, so
# it is deterministic and carries no attribution.
AMB_IN, AMB_OUT = 21.9, 42.6
AMB_LEVEL = 0.085


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
    vo_arc = pw_expr([(t, 1.0 + (m - 1.0) * 0.52) for t, m in BED_ARC])
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
                        "loudnorm=I=-14:TP=-1.8:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"\{[^{}]*input_i[^{}]*\}", p.stderr, re.S)
    if not m:
        raise SystemExit("dispatch_mix: loudnorm analysis pass produced no JSON")
    a = json.loads(m.group(0))
    print(f"premix measured: {a['input_i']} LUFS  TP {a['input_tp']}  LRA {a['input_lra']}")
    ln = (f"loudnorm=I=-14:TP=-1.8:LRA=11:linear=true"
          f":measured_I={a['input_i']}:measured_TP={a['input_tp']}"
          f":measured_LRA={a['input_lra']}:measured_thresh={a['input_thresh']}"
          f":offset={a['target_offset']}:print_format=summary")
    run([FF, "-y", "-i", premix, "-af", f"{ln},alimiter=limit=0.86:level=false",
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
