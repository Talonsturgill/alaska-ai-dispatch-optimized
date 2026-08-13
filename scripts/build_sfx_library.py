#!/usr/bin/env python3
"""BUILD THE SFX BANK — designed foley with VARIANTS, not one static take.

2026-07-21 owner note: "ours is boring and reusing the same sfx". The old bank
rendered ONE wav per kind, so a clank on July 18 was bit-identical to a clank on
July 21 (and to the other clank 30 seconds earlier). This rebuild encodes the
game-audio doctrine (Wwise/FMOD round-robin, School-of-Motion layering):

  VARIANTS   6 takes per kind (<kind>_v1..v6.wav), each sampled from a per-kind
             PARAM FAMILY (sfxr-style ranges), so takes are siblings, not clones.
             scripts/sfx_bank.py shuffle-bags them with no-repeat-last-2.
  LAYERING   every hit is Transient + Body + Tail (+ sweetener):
             - transient (1-15ms) = material; body (50-400ms) = weight;
             - TAIL: a small-room reverb (Schroeder comb+allpass) — the layer
               the old bank lacked entirely, which is why it read "synthesized";
             - sweeteners: paper grains after a stamp, mechanism rattle after a
               clank, air tick after a pop.
  PHYSICS    metal = modal stacks with stiff-bar inharmonicity
             f_n = n*f0*sqrt(1 + B*n^2), per-partial decay ~ f (highs die
             first), struck (noise-burst) onset; per-variant f0 +/-3% + B jitter
             = endless non-repeating clanks. paper = granular synthesis (15-60ms
             band-passed Hann grains, density-enveloped). snap = Karplus-Strong.
  DETERMINISM every variant is seeded from crc32(kind:vN) — same repo state
             reproduces the bank bit-identically; no salted hash(), no clock.

44.1k 16-bit stereo, peaks at -6 dBFS, gentle tanh saturation. The bank is
committed; every future run mixes from the same takes (variety comes from the
shuffle-bag + the per-event jitter in dispatch_mix.py).

UPGRADE PATH FOR REAL RECORDINGS: curated CC0/PD takes at
assets/sfx/real/<kind>*.wav (logged in assets/sfx/MANIFEST.md) win over the
synth bank in scripts/sfx_bank.py. Multiple real takes per kind join the
shuffle-bag alongside nothing else — real replaces synth per kind, wholesale.
"""
import json
import os
import zlib
import numpy as np
from scipy.signal import butter, sosfilt, lfilter

SR = 44100
VARIANTS = 6
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, ".."))
BANK = os.path.join(REPO, "assets", "sfx")


def seed_for(kind, v):
    return zlib.crc32(f"akai-sfx:{kind}:v{v}".encode()) % (2**32)


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def env_exp(n, decay):
    return np.exp(-decay * np.arange(n) / SR)


def env_ar(n, attack_s, release_s):
    a = int(max(1, attack_s * SR)); r = int(max(1, release_s * SR))
    e = np.ones(n)
    e[:a] = np.linspace(0, 1, a)
    if r < n:
        e[-r:] *= np.linspace(1, 0, r)
    return e


def bp(x, lo, hi, order=4):
    sos = butter(order, [max(20, lo), min(SR / 2 - 100, hi)], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x)


def lp(x, fc, order=4):
    sos = butter(order, min(SR / 2 - 100, fc), btype="low", fs=SR, output="sos")
    return sosfilt(sos, x)


def hp(x, fc, order=4):
    sos = butter(order, max(20, fc), btype="high", fs=SR, output="sos")
    return sosfilt(sos, x)


def pink(rng, n):
    # Voss-ish: sum of octave-spaced LP noise
    x = np.zeros(n)
    for oct_ in range(5):
        step = 2 ** oct_
        base = rng.standard_normal(n // step + 1)
        x += np.repeat(base, step)[:n]
    return x / 5


def sweep_sine(f0, f1, dur, curve=1.0):
    t = t_axis(dur)
    f = f0 + (f1 - f0) * (t / dur) ** curve
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph)


def click(rng, dur=0.006, fc=3000):
    n = int(SR * dur)
    return bp(rng.standard_normal(n), fc * 0.5, fc * 2) * env_exp(n, 600)


def mix(*parts):
    n = max(p.size for p in parts)
    out = np.zeros(n)
    for p in parts:
        out[:p.size] += p
    return out


def at(base, part, t):
    """Overlay `part` onto `base` starting at time t (seconds), growing base."""
    s = int(t * SR)
    n = max(base.size, s + part.size)
    out = np.zeros(n)
    out[:base.size] += base
    out[s:s + part.size] += part
    return out


# --------------------------------------------------------------- room + physics
def reverb_tail(x, decay_s=0.25, wet=0.22, bright=4200):
    """Small-room Schroeder reverb (4 combs + 2 allpasses) — the TAIL layer.
    Grounds a synthesized hit in a space; the single biggest 'produced' cue."""
    if wet <= 0:
        return x
    y = np.zeros(x.size + int(SR * decay_s * 2.5))
    y[:x.size] = x
    combs = [(0.0297, 0.72), (0.0371, 0.68), (0.0411, 0.64), (0.0437, 0.60)]
    wetsig = np.zeros_like(y)
    for d, g0 in combs:
        D = int(d * SR)
        g = g0 * np.exp(-6.91 * d / max(0.05, decay_s))  # RT60-ish scaling
        a = np.zeros(D + 1); a[0] = 1; a[-1] = -g
        wetsig += lfilter([1.0], a, y) / len(combs)
    for d in (0.005, 0.0017):
        D = int(d * SR); g = 0.7
        b = np.zeros(D + 1); b[0] = -g; b[-1] = 1
        a = np.zeros(D + 1); a[0] = 1; a[-1] = -g
        wetsig = lfilter(b, a, wetsig)
    wetsig = lp(wetsig, bright)  # rooms darken tails
    return y * (1 - wet * 0.4) + wetsig * wet


def modal_metal(rng, f0, B, n_partials, decay_base, dur, strike_fc=2600):
    """Struck metal: stiff-bar modal stack f_n = n*f0*sqrt(1+B*n^2), per-partial
    decay proportional to frequency (highs die first), noise-burst onset."""
    t = t_axis(dur)
    x = np.zeros(t.size)
    for nn in range(1, n_partials + 1):
        fn = nn * f0 * np.sqrt(1 + B * nn * nn)
        if fn > SR / 2 - 200:
            break
        dec = decay_base * (fn / f0) ** 0.7
        amp = 1.0 / (nn ** 0.8)
        x += amp * np.sin(2 * np.pi * fn * t + rng.uniform(0, 6.28)) * env_exp(t.size, dec)
    x /= max(1, n_partials * 0.45)
    strike = click(rng, 0.003, strike_fc)
    return mix(strike * 0.9, x)


def grains(rng, n_grains, dur, lo=1500, hi=8000, glen=(0.015, 0.06),
           density_env=None, pitch_spread=0.0):
    """Granular noise texture: Hann-windowed band-passed bursts scattered over
    dur. THE paper engine — reads as moving paper, not a looped crackle."""
    n = int(SR * dur)
    out = np.zeros(n)
    for i in range(n_grains):
        u = rng.uniform()
        if density_env is not None:
            u = u ** density_env  # <1 biases early, >1 biases late
        s = int(u * (dur - glen[1]) * SR)
        gl = int(SR * rng.uniform(*glen))
        c = rng.uniform(-1, 1)
        f_lo, f_hi = lo * (2 ** (c * pitch_spread)), hi * (2 ** (c * pitch_spread))
        g = bp(rng.standard_normal(gl), f_lo, f_hi) * np.hanning(gl) * rng.uniform(0.25, 1.0)
        out[s:s + gl] += g[:max(0, n - s)]
    return out


def ks_pluck(rng, f0, dur, damp=0.996, blend=0.5):
    """Karplus-Strong pluck; damp<1 shortens, blend<0.5 dulls. The 'rubber-band
    boing' voice for snaps/levers."""
    D = int(SR / f0)
    buf = rng.uniform(-1, 1, D)
    n = int(SR * dur)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % D]
        nxt = damp * (blend * buf[i % D] + (1 - blend) * buf[(i + 1) % D])
        buf[i % D] = nxt
    return out


def u(rng, lo_hi):
    return rng.uniform(*lo_hi)


# ---------------------------------------------------------------- the designs
# Each design takes rng and samples its own params from the family ranges, so
# every variant is a sibling take: same material, different performance.

def d_thud(rng):    # body-impact: sub sweep + knock + noise shell + debris
    dur = u(rng, (0.28, 0.36)); f_hi = u(rng, (118, 145)); f_lo = u(rng, (38, 48))
    body = sweep_sine(f_hi, f_lo, dur, 0.5) * env_exp(int(SR * dur), u(rng, (9, 13)))
    knock = lp(rng.standard_normal(int(SR * 0.05)), 900) * env_exp(int(SR * 0.05), 90) * 0.8
    shell = lp(rng.standard_normal(int(SR * 0.2)), 400) * env_exp(int(SR * 0.2), 22) * 0.35
    x = mix(body, knock, shell)
    x = at(x, grains(rng, 5, 0.09, 700, 3000) * 0.12, 0.03)   # sweetener: debris
    return reverb_tail(x, 0.16, 0.16)

def d_stamp(rng):   # deep sub + slap + PAPER-GRAIN sweetener + desk-room tail
    dur = u(rng, (0.36, 0.46))
    body = sweep_sine(u(rng, (92, 110)), u(rng, (30, 38)), dur, 0.5) * env_exp(int(SR * dur), u(rng, (7, 9.5))) * 1.1
    slap = bp(rng.standard_normal(int(SR * 0.04)), 700, 5000) * env_exp(int(SR * 0.04), 140) * 0.9
    x = mix(body, slap)
    # the paper being compressed, 25-80ms after the hit — makes it "stamp on
    # paper" instead of "kick drum"
    x = at(x, grains(rng, rng.integers(8, 13), 0.08, 1500, 7000) * 0.22, 0.025)
    return reverb_tail(x, 0.15, 0.2)

def d_boom(rng):    # scene-scale impact, longer bloom + room
    dur = u(rng, (0.8, 1.0))
    body = sweep_sine(u(rng, (82, 98)), u(rng, (26, 34)), dur, 0.4) * env_exp(int(SR * dur), u(rng, (3.8, 4.8))) * 1.1
    air = lp(pink(rng, int(SR * 0.7)), 500) * env_exp(int(SR * 0.7), 6) * 0.5
    x = mix(body, click(rng, 0.008, 1200) * 0.5, air)
    return reverb_tail(x, 0.5, 0.24, 2800)

def d_pop(rng):     # UI pop: pitch-drop blip + snap transient + tiny air tail
    f0 = u(rng, (820, 1050)); f1 = f0 * u(rng, (0.55, 0.7))
    chirp = sweep_sine(f0, f1, 0.05, 1.4) * env_exp(int(SR * 0.05), 55)
    snapl = click(rng, 0.003, u(rng, (2600, 4200))) * 1.15   # snap ~+2dB over body
    tail = lp(rng.standard_normal(int(SR * 0.08)), 8000) * env_exp(int(SR * 0.08), 60) * 0.12
    return mix(chirp, snapl, at(np.zeros(1), tail, 0.012))

def d_snap(rng):    # lever/rubber-band: Karplus-Strong pluck + crack + bump
    f0 = u(rng, (150, 240))
    pluck = ks_pluck(rng, f0, 0.28, damp=u(rng, (0.994, 0.9975)), blend=u(rng, (0.42, 0.55))) * 0.8
    crack = bp(rng.standard_normal(int(SR * 0.03)), 1500, 9000) * env_exp(int(SR * 0.03), 220)
    bump = sweep_sine(160, 80, 0.07, 1) * env_exp(int(SR * 0.07), 60) * 0.45
    return reverb_tail(mix(crack, pluck, bump), 0.12, 0.12)

def d_tick(rng):    # clock tick: tight resonant click, per-take color
    fc = u(rng, (1700, 2600))
    n = int(SR * 0.012)
    x = bp(rng.standard_normal(n), fc, fc * 2.9) * env_exp(n, u(rng, (360, 480)))
    return reverb_tail(x, 0.09, 0.1)

def d_ding(rng):    # small bright bell: modal stack, bell ratios, long ring
    f0 = 880 * u(rng, (0.97, 1.03))
    return modal_metal(rng, f0, u(rng, (0.0008, 0.004)), 7, u(rng, (2.8, 3.8)), 1.1, 5200) * 0.9

def d_chime(rng):   # softer warm bell (win/positive accent)
    f0 = 660 * u(rng, (0.97, 1.03))
    x = modal_metal(rng, f0, u(rng, (0.0006, 0.003)), 6, u(rng, (2.2, 3.0)), 1.3, 3800) * 0.85
    return reverb_tail(x, 0.35, 0.14)

def d_clank(rng):   # struck machine metal: inharmonic modal + mechanism rattle
    f0 = 310 * u(rng, (0.97, 1.03)); B = u(rng, (0.05, 0.22))
    x = modal_metal(rng, f0, B, 9, u(rng, (8, 12)), 0.6)
    # sweetener: the linkage settling — 2-3 quiet pitch-varied micro-clinks
    for dt in (0.025, 0.06, 0.11)[:rng.integers(2, 4)]:
        c = modal_metal(rng, f0 * u(rng, (1.3, 2.1)), B, 4, 26, 0.12) * 0.3
        x = at(x, c, dt)
    return reverb_tail(x, 0.3, 0.18)

def d_chain(rng):   # a handful of clank-lets, irregular
    out = np.zeros(int(SR * 0.55))
    tpos = 0.0
    for i in range(int(rng.integers(5, 8))):
        c = modal_metal(rng, u(rng, (430, 730)), u(rng, (0.08, 0.25)), 5,
                        u(rng, (16, 26)), 0.16) * u(rng, (0.4, 1.0))
        out = at(out, c, tpos)
        tpos += u(rng, (0.03, 0.085))
    return reverb_tail(out, 0.2, 0.15)

def d_whoosh(rng):  # air pass: swept band-pass pink noise, asymmetric arc,
    dur = u(rng, (0.5, 0.62))          # volume env decoupled from filter env
    n = int(SR * dur)
    x = pink(rng, n)
    peak_at = u(rng, (0.35, 0.5))      # fast-in slow-out arc
    lo0, hi0 = u(rng, (180, 260)), u(rng, (800, 1100))
    loP, hiP = u(rng, (450, 650)), u(rng, (2200, 3200))
    seg_n = 8
    segs = []
    for i in range(seg_n):
        p = i / (seg_n - 1)
        m = (p / peak_at) if p < peak_at else 1 - (p - peak_at) / (1 - peak_at)
        m = m ** 0.8
        segs.append(bp(x[i * n // seg_n:(i + 1) * n // seg_n],
                       lo0 + (loP - lo0) * m, hi0 + (hiP - hi0) * m))
    y = np.concatenate(segs)
    vol = env_ar(y.size, dur * peak_at * 0.7, dur * (1 - peak_at) * 0.9)
    return reverb_tail(y * vol, 0.14, 0.1)

def d_riser(rng):   # build: detuned tone pair + noise, exp sweep, crescendo
    dur = u(rng, (0.9, 1.05)); n = int(SR * dur)
    nz = hp(pink(rng, n), 300) * np.linspace(0.15, 1.0, n) ** 1.5
    f_end = u(rng, (560, 700)); f_start = f_end / 2 ** (u(rng, (10, 12)) / 12)
    det = 2 ** (u(rng, (0.010, 0.015)) / 12)   # 10-15 cent detune spread
    tone = (sweep_sine(f_start, f_end, dur, 1.6) +
            sweep_sine(f_start * det, f_end * det, dur, 1.6)) * 0.5
    tone *= np.linspace(0.1, 0.8, n) ** 1.4 * 0.6
    y = mix(bp(nz, 400, 5200), tone)
    return y * env_ar(y.size, dur * 0.55, 0.06)

def d_creak(rng):   # stick-slip pulse train + wood-modal body underneath
    n = int(SR * 0.5)
    out = np.zeros(n)
    tpos = 0.0; gap = u(rng, (0.03, 0.042))
    res = u(rng, (750, 1100))
    while tpos < 0.42:
        c = click(rng, 0.005, res) * rng.uniform(0.5, 1.0)
        s = int(tpos * SR)
        out[s:s + c.size] += c[:max(0, n - s)]
        gap *= 0.86  # accelerates = the creak "gives"
        tpos += max(0.006, gap + rng.uniform(-0.004, 0.004))
    x = bp(out, 300, 2200) * env_ar(n, 0.02, 0.15)
    wood = modal_metal(rng, u(rng, (140, 190)), 0.0, 4, 30, 0.3) * 0.25  # B~0 = wood
    return reverb_tail(mix(x, wood), 0.13, 0.12)

def d_paper(rng):   # rustle/crumple: GRANULAR — density-enveloped noise grains
    dur = u(rng, (0.65, 0.8))
    x = grains(rng, int(rng.integers(45, 75)), dur, 1500, 8000,
               glen=(0.015, 0.06), density_env=u(rng, (0.7, 1.4)), pitch_spread=0.33)
    return x * env_ar(int(x.size), 0.05, 0.25) * 0.85

def d_paw(rng):     # soft muffled footfall
    body = sweep_sine(u(rng, (175, 205)), u(rng, (88, 102)), 0.09, 0.8) * env_exp(int(SR * 0.09), 45) * 0.7
    pad = lp(rng.standard_normal(int(SR * 0.06)), 600) * env_exp(int(SR * 0.06), 70) * 0.5
    return reverb_tail(mix(body, pad), 0.1, 0.1)

def d_caw(rng):     # raven call: two rasping downward caws, per-take pitch
    base = u(rng, (880, 1020))
    def one_caw(scale):
        n = int(SR * u(rng, (0.12, 0.16)))
        dur = n / SR
        tone = sweep_sine(base * scale, base * scale * 0.44, dur, 1.3) * env_ar(n, 0.01, 0.09) * 0.55
        rasp = bp(rng.standard_normal(n), 700, 3200) * env_ar(n, 0.008, 0.1) * 0.7
        return mix(tone, rasp)
    c1 = one_caw(1.0)
    x = at(c1, one_caw(u(rng, (0.9, 1.0))) * 0.8, c1.size / SR + u(rng, (0.07, 0.11)))
    return reverb_tail(x, 0.3, 0.12, 3000)   # outdoors = a longer, darker tail

def d_klaxon(rng):  # two-tone alert, band-limited square-ish
    fa, fb = 392 * u(rng, (0.97, 1.03)), 311 * u(rng, (0.97, 1.03))
    t = t_axis(0.5)
    f = np.where((t * u(rng, (3.6, 4.4))).astype(int) % 2 == 0, fa, fb)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.tanh(1.8 * np.sin(ph)) * 0.8
    return lp(y, 2400) * env_ar(t.size, 0.02, 0.1)


DESIGNS = {
    "thud": d_thud, "stamp": d_stamp, "boom": d_boom, "pop": d_pop, "snap": d_snap,
    "tick": d_tick, "ding": d_ding, "chime": d_chime, "clank": d_clank, "chain": d_chain,
    "whoosh": d_whoosh, "riser": d_riser, "creak": d_creak, "paper": d_paper,
    "paw": d_paw, "klaxon": d_klaxon, "caw": d_caw,
}


def finish(x):
    """Character saturation, DC removal, normalize to -6 dBFS, edge fades, stereo."""
    x = np.tanh(1.25 * x / max(1e-9, np.max(np.abs(x))))
    x = hp(x, 28, order=2)                       # rumble cleanup
    x = x / max(1e-9, np.max(np.abs(x))) * 0.5   # -6 dBFS
    fade = int(SR * 0.004)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    # subtle stereo: tiny decorrelated delay on the right channel
    d = int(SR * 0.0008)
    right = np.concatenate([np.zeros(d), x[:-d]]) if d else x
    return np.stack([x, 0.92 * right + 0.08 * x], axis=1)


def main():
    os.makedirs(BANK, exist_ok=True)
    from scipy.io import wavfile
    rows = []
    for kind, fn in DESIGNS.items():
        durs = []
        for v in range(1, VARIANTS + 1):
            rng = np.random.default_rng(seed_for(kind, v))
            y = finish(fn(rng))
            path = os.path.join(BANK, f"{kind}_v{v}.wav")
            wavfile.write(path, SR, (y * 32767).astype(np.int16))
            durs.append(y.shape[0] / SR)
            if v == 1:
                # back-compat alias: plain <kind>.wav = v1 (old episode-local
                # mixes and the self-heal path in sfx_bank keep working)
                wavfile.write(os.path.join(BANK, f"{kind}.wav"), SR, (y * 32767).astype(np.int16))
        rows.append((kind, durs))
        print(f"  {kind:8} {VARIANTS} takes  {min(durs):4.2f}-{max(durs):4.2f}s")
    man = os.path.join(BANK, "MANIFEST.md")

    # THE REAL-RECORDINGS SECTION IS REGENERATED, NEVER PRESERVED BY LUCK (2026-08-13).
    # This function opens MANIFEST.md with "w", and its template only ever described the
    # SYNTH bank. assets/sfx/real/ holds 30 committed CC0 recordings whose licence and
    # provenance were documented in a hand-written section of this same file, so every run
    # that rebuilt the bank silently DELETED the attribution trail for material that stays
    # on disk. The files kept working and the licence record disappeared, which is the worst
    # shape a documentation bug can take. Rather than ask a future run to remember to
    # restore it, the section is now DERIVED from assets/sfx/real/manifest.json, which
    # carries author, licence, pack, source URL and sha256 per file. Regenerated output
    # cannot drift from the files it describes, and a rebuild can no longer lose it.
    def _real_section():
        rp = os.path.join(BANK, "real", "manifest.json")
        if not os.path.exists(rp):
            return ""
        try:
            recs = json.load(open(rp)).get("files", [])
        except Exception:
            return ""
        if not recs:
            return ""
        by = {}
        for r in recs:
            key = (r.get("kind", "?"), r.get("pack", "?"), r.get("author", "?"), r.get("license", "?"))
            by.setdefault(key, []).append(r.get("filename", ""))
        lic = sorted({r.get("license", "?") for r in recs})
        auth = sorted({r.get("author", "?") for r in recs})
        out = ["\n## Real recordings (assets/sfx/real/ — win over synth, per kind)\n\n"]
        out.append(f"{len(recs)} file(s), regenerated from real/manifest.json, which carries the\n"
                   f"source URL, pack, sha256 and retrieval date for each one.\n\n")
        out.append(f"Licence: {', '.join(lic)}. Author: {', '.join(auth)}.\n")
        out.append("CC0 requires no attribution; credit is given anyway. Committing CC0 material\n"
                   "here is clean.\n\n")
        for (kind, pack, _a, _l), files in sorted(by.items()):
            out.append(f"- `{kind}_*` — {len(files)} take(s) — {pack}\n")
        out.append("\nDo NOT add Sonniss/Pixabay/Mixkit files here (commercial use OK, but\n"
                   "redistribution, which is what committing is, is prohibited). BBC RemArc is\n"
                   "non-commercial: never use it. CC0-only in this directory.\n")
        return "".join(out)

    with open(man, "w") as f:
        f.write("# SFX bank — designed foley with variants (scripts/build_sfx_library.py)\n\n")
        f.write("Deterministic numpy sound design (crc32-seeded), 44.1k/16-bit stereo, -6 dBFS\n")
        f.write("peaks. Each kind ships SIX sibling takes (`<kind>_v1..v6.wav`) sampled from a\n")
        f.write("param family — scripts/sfx_bank.py shuffle-bags them (no-repeat-last-2) so no\n")
        f.write("two plays of a kind in an episode (or across weeks) are the same take.\n")
        f.write("Layering: transient + body + Schroeder room tail (+ sweetener). Metal is modal\n")
        f.write("(f_n = n*f0*sqrt(1+B*n^2)); paper is granular; snap is Karplus-Strong.\n")
        f.write("License: original synthesis, no third-party material.\n\n")
        f.write("To UPGRADE any kind with real recordings: put curated CC0/public-domain takes\n")
        f.write("at `assets/sfx/real/<kind>*.wav` (e.g. clank_a.wav, clank_b.wav) and log source\n")
        f.write("+ license here. sfx_bank.py then shuffle-bags the real takes for that kind\n")
        f.write("instead of the synth ones, automatically.\n\n")
        for kind, durs in rows:
            f.write(f"- `{kind}_v1..v{VARIANTS}.wav` — {min(durs):.2f}-{max(durs):.2f}s — designed synth — no attribution needed\n")
        f.write(_real_section())
    print(f"bank: {len(rows)} kinds x {VARIANTS} takes -> {BANK}")


if __name__ == "__main__":
    main()
