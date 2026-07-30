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
import json, os, subprocess, sys, math, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(REPO, "out", "dispatch")
AUD = os.path.join(OUT, "audio")
FF = os.environ.get("FFMPEG_BIN", "ffmpeg")
SR = 44100
DATE = "2026-07-30"   # episode seed for the shuffle-bag + jitter


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
    # ---- 2026-07-30 "We know where the machine is". 7 shots, 14 VO lines.
    # SOUND IS THE SUBJECT of this film, so the foley carries argument rather than
    # decoration. Families deliberately alternate (the assert below enforces it) and
    # the single riser is spent on the pullback that reveals 34 empty years.
    # S1 (L0-L1): the signal cone dies flat on the ice, the machine's eye sweeps
    (L[0] + 0.20, "thud",   "hero",      0.0),    # the cone hits the lid and stops
    (L[0] + 1.60, "tick",   "texture",  -0.30),   # the failed lock
    (L[1] + 0.90, "creak",  "standard",  0.15),   # ice under load, the world is closed
    # S2 (L2-L3): six anchors plant, then the whole seafloor breathes light
    (L[2] + 0.40, "clank",  "standard", -0.25),   # first anchor lands
    (L[2] + 2.20, "paper",  "texture",   0.20),   # silt lifting
    (L[3] + 0.35, "ding",   "hero",      0.0),    # the 900 Hz field comes up
    # S3 (L4-L5): the range lines arrive and THE CLAMP lands. The signature shot.
    (L[4] + 0.30, "whoosh", "standard", -0.30),   # first range line sweeps in
    (L[4] + 1.55, "pop",    "standard",  0.25),   # second
    (L[4] + 2.70, "chime",  "hero",      0.0),    # THE SOLVE, centered for the payoff
    (L[5] + 0.25, "tick",   "texture",   0.10),   # the bare geometry drawing on
    # S4 (L6-L7): the ghost enters the sound field, the filing lands and stamps
    (L[6] + 0.50, "creak",  "standard", -0.20),   # the animal displacing water
    (L[7] + 0.45, "stamp",  "hero",      0.0),    # PROPOSED thuds down
    (L[7] + 2.30, "snap",   "texture",   0.20),   # the paper settling
    # S5 (L8): the finding, and the compliance tick given its own air
    (L[8] + 0.55, "clank",  "standard", -0.15),   # the finding card sets
    (L[8] + 2.60, "ding",   "standard",  0.15),   # the tick draws, unironic
    # S6 (L9-L11): THE TURN. one point lands, the pullback opens 34 empty years
    (L[9] + 0.35, "pop",    "hero",     -0.35),   # the 1992 point lands hard
    (L[9] + 1.90, "riser",  "hero",      0.0),    # THE ONE RISER, the scale pullback
    (L[10] + 0.40, "tick",  "texture",   0.30),   # the empty field, a hollow click
    (L[11] + 0.55, "boom",  "hero",      0.0),    # the thesis, the unreadable gauge
    # S7 (L12-L13): the date, then the button
    (L[12] + 0.40, "clank", "standard",  0.0),    # the date card sets square
    (L[13] + 0.35, "chime", "hero",      0.0),    # the button, one last lock tick
    (VIDEO_SECS - _TAIL + 1.0, "tick", "texture", 0.0),
]


# The breath before the PAYOFF. storyboard audio_arc.silence_at sits under the arrow's
# ANTICIPATION so the crumple at the turn lands into a hole (Gate 0C: the film's only
# reserved sub-60Hz spend and its silence cannot share a frame).
# The dip must land in the REAL VO GAP before the line, not on top of it. Placing it at
# L[9]'s start (pass 1) put it under the speech and measured as a 4.6 dB RISE. The 1.06s
# gap between L8 ending and L9 starting is the breath before "Neither record is wrong",
# the quietest and most important line in the film, so the bed drops out into real silence.
SILENCE_DIP_AT = round(L[11] - 0.85, 2)
DIP_LEN = 0.90


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

    # 2) assemble inputs: [0]=VO padded to VIDEO, [1]=music looped/trimmed, then SFX
    inputs = ["-i", os.path.join(AUD, "vo.wav"), "-i", os.path.join(OUT, "music_bed.wav")]
    for p in takes:
        inputs += ["-i", p]

    fc = []
    # VO: pad to full length, keep dominant; split (one copy to mix, one as sidechain key)
    fc.append(f"[0:a]aformat=sample_rates={SR}:channel_layouts=stereo,apad=whole_dur={VIDEO_SECS},volume=1.0,asplit=2[vo][vok]")
    # Music: loop, trim, base level, VO-slot EQ (wide -2.5dB dip at 3k so the bed
    # never fights intelligibility), scripted dip before the button, gentle lift
    # in the post-VO tail where there's no voice to serve
    dip0, dip1 = SILENCE_DIP_AT, SILENCE_DIP_AT + DIP_LEN
    vo_end = max(x["end"] for x in _lines)
    fc.append(
        f"[1:a]aformat=sample_rates={SR}:channel_layouts=stereo,aloop=loop=-1:size={int(SR*200)},"
        f"atrim=0:{VIDEO_SECS},equalizer=f=3000:t=q:w=1:g=-2.5,volume=0.30,"
        f"volume=enable='between(t,{dip0},{dip1})':volume=0.015,"
        f"volume=enable='gt(t,{vo_end + 0.4})':volume=1.3[bedraw]"
    )
    # sidechain duck the bed under the VO (uses the key copy)
    fc.append(f"[bedraw][vok]sidechaincompress=threshold=0.04:ratio=9:attack=6:release=320:makeup=1[bed]")

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

    # mix VO + bed + all sfx
    mix_in = "[vo][bed]" + "".join(sfx_labels)
    n = 2 + len(sfx_labels)
    fc.append(f"{mix_in}amix=inputs={n}:normalize=0:dropout_transition=0[premix]")
    # final loudness normalize + true-peak limit
    fc.append(f"[premix]loudnorm=I=-14:TP=-1.2:LRA=11,alimiter=limit=0.86:level=false[out]")

    filtergraph = ";".join(fc)
    master = os.path.join(AUD, "master.wav")
    run([FF, "-y", *inputs, "-filter_complex", filtergraph, "-map", "[out]",
         "-ar", str(SR), "-ac", "2", "-t", str(VIDEO_SECS), master])
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
