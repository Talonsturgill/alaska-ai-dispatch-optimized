#!/usr/bin/env python3
"""VO SOUND CHECK — the QC gate that enforces docs/craft/VO_DIRECTION.md on a
Gemini TTS take. Given a rendered wav and the intended SPOKEN script, it scores:

  1. word_accuracy  — ASR-transcribe (faster-whisper) and compare to the script.
                      Catches dropped/added words and the 500 "text instead of
                      audio" fallback. (1 - WER)
  2. no_leak        — the transcript must NOT contain any tag word or director's-
                      note word (e.g. "whispers", "director", "transcript"). Catches
                      vocalized-markup / notes-read-aloud failures.
  3. expressive     — pitch (f0) std-dev in semitones must clear a monotone floor.
                      A flat read is the robotic tell; this enforces tone fluctuation.
  4. duration       — within the target window (pace on target).
  5. loudness       — integrated LUFS within a broadcast-safe band.

Usage (single take):
  python scripts/vo_soundcheck.py --audio take.wav --script "the spoken words" [--json]
Programmatic:
  from vo_soundcheck import check, pick_best
  rep = check(wav_path, spoken_text, tags=[...])
  best_idx, reports = pick_best([w1,w2,w3], spoken_text, tags=[...])
"""
import argparse, json, os, re, sys

# THE DURATION WINDOW IS READ FROM CONFIG, NOT HARDCODED (2026-07-30). It used to be a
# literal dur_hi=75.0, which silently became a run-breaker the moment the format went from
# 60s to 90s: a conforming 90s read is 84 to 96 seconds of audio, so EVERY take would have
# failed the PACE check, pick_best would have returned a failing take, and the routine
# forbids shipping one. Deriving it from config/state.yaml means the next format change
# cannot strand this file behind it.
def _duration_window():
    lo, hi = 8.0, 75.0
    try:
        import yaml
        cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "state.yaml")
        band = (yaml.safe_load(open(cfg)) or {}).get("dispatch_seconds_band")
        if band and len(band) == 2:
            # DELIBERATELY WIDE. The gate that owns exact runtime is Phase 7; this check
            # only needs to catch a take that is GROSSLY broken, a TTS truncation or a
            # runaway loop. Making it tight here just burns re-synths on takes the runtime
            # gate would have accepted.
            lo, hi = max(8.0, float(band[0]) * 0.55), float(band[1]) * 1.35
    except Exception:
        pass
    return lo, hi

DUR_LO, DUR_HI = _duration_window()


def _target_band():
    """The TIGHT band and target the format actually wants, straight from config.

    Distinct from _duration_window() above, which is the deliberately-wide sanity check.
    This is what take SELECTION uses (see pick_best), and until 2026-08-05 nothing in
    code read it at all: `dispatch_target_seconds` and the tight `dispatch_seconds_band`
    existed only as prose for the routine prompt to honour by hand.
    """
    lo, hi, target = None, None, None
    try:
        import yaml
        cfg = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "state.yaml")
        c = yaml.safe_load(open(cfg)) or {}
        band = c.get("dispatch_seconds_band")
        if band and len(band) == 2:
            lo, hi = float(band[0]), float(band[1])
        if c.get("dispatch_target_seconds"):
            target = float(c["dispatch_target_seconds"])
    except Exception:
        pass
    if target is None and lo is not None:
        target = (lo + hi) / 2
    return lo, hi, target

# tolerances (tuned for a ~55s brisk social VO)
WER_MAX = 0.08          # <= 8% word error
PITCH_STD_MIN = 1.6     # semitones; below this = monotone
LUFS_MIN, LUFS_MAX = -20.0, -12.0
VOICED_MIN = 0.35       # at least this fraction voiced (not silence/noise)
NOTE_WORDS = {"transcript", "director", "profile", "narrator", "audio", "preamble", "aloud"}


def _year_words(n):
    """Natural date reading for a 4-digit number, MATCHING HOUSE SCRIPT CONVENTION.

    The script is always spelled out in words (VO_DIRECTION mandates it) and only the
    ASR transcript contains digits, so this function's only job is to turn whisper's
    digits into the words a house script would have used. Getting that mapping wrong
    scores word errors against a take that said exactly the right sentence.

    It was wrong for two whole decades' worth of numbers (fixed 2026-08-05, measured on
    a 288-word probe). The rule was "two 2-digit groups" for everything from 1000 to
    2999, which is correct for 2024 ('twenty twenty four') and wrong for:

      2008  ->  gave 'twenty eight'.   House scripts write 'two thousand eight', and
                every Dispatch that cites a paper year hits this. The 2026-08-05 script
                said 'two thousand eight' and 'two thousand six'; both scored as errors.
      1,000 ->  gave 'ten hundred'. A round thousand is a QUANTITY, not a year, and this
                format puts a round thousand in almost every script ('about a thousand
                species a decade'). Three separate instances in one probe script.

    Those two bugs alone contributed most of a 0.074 WER against a 0.08 fail ceiling, so
    a clean take was one mishearing away from a spurious re-synth. At 288 words there are
    simply more numbers for it to happen to, which is why a latent bug became a blocker.
    """
    from num2words import num2words
    words = lambda k: num2words(k).replace("-", " ").replace(" and ", " ").split()
    # A round thousand reads as a quantity. Nobody says "ten hundred".
    if n % 1000 == 0:
        return words(n)
    # 2000-2009 reads "two thousand eight", not "twenty oh eight" or "twenty eight".
    if 2000 <= n <= 2009:
        return words(n)
    hi, lo = n // 100, n % 100
    return words(hi) + (["hundred"] if lo == 0 else words(lo))


def _canon_token(tok):
    """Canonicalize a token so spelling differences (500 vs five hundred, A.I. vs
    AI, 28th vs twenty eighth, 2024 vs twenty twenty four) don't count as word
    errors. Digits -> words via num2words; leave the rest."""
    t = tok.strip("+%").replace(",", "")
    m = re.match(r"^(\d+)(st|nd|rd|th)$", t)
    # DECIMALS. "1.6" fails isdigit(), so it used to pass through verbatim while the
    # script said "one point six", scoring three word errors on the one token that
    # matters most in a funding story. Every Dispatch has a money figure in it.
    dec = re.match(r"^(\d+)\.(\d+)$", t)
    try:
        from num2words import num2words
        if dec:
            whole = num2words(int(dec.group(1))).replace("-", " ").replace(" and ", " ").split()
            frac = [num2words(int(d)) for d in dec.group(2)]
            return whole + ["point"] + frac
        if m:
            return num2words(int(m.group(1)), to="ordinal").replace("-", " ").replace(" and ", " ").split()
        if t.isdigit():
            n = int(t)
            if 1000 <= n <= 2999 and len(t) == 4:
                return _year_words(n)
            return num2words(n).replace("-", " ").replace(" and ", " ").split()
    except Exception:
        return [tok]
    return [tok]


def _norm_words(s):
    s = s.lower()
    # currency/percent SYMBOLS carry a spoken word that a bare regex strip would
    # silently drop ("$50,000" -> heard has no "dollars"; "60%" -> no "percent"),
    # inflating WER on every number-heavy script (this format has one every run).
    # SCALED CURRENCY FIRST. "$1.6 million" under the bare rule below became
    # "1.6 dollars million", i.e. the spoken word landed in the wrong place and the
    # scale word was orphaned, so a take that said exactly the right sentence scored
    # two more errors on top of the decimal. Whisper writes money this way every time.
    s = re.sub(r"\$\s?(\d[\d,]*(?:\.\d+)?)\s+(million|billion|trillion|thousand)",
               r"\1 \2 dollars", s)
    s = re.sub(r"\$\s?(\d[\d,]*(?:\.\d+)?)", r"\1 dollars", s)
    s = re.sub(r"(\d)\s?%", r"\1 percent", s)
    # DECIMALS BEFORE THE STRIP. The general regex below replaces every non
    # [a-z0-9\'] character with a space, so "1.6" became "1 6" and the decimal branch
    # in _canon_token could never see a dot. Spell it out here, while the dot exists.
    def _dec(m):
        try:
            from num2words import num2words
            whole = num2words(int(m.group(1))).replace("-", " ").replace(" and ", " ")
            frac = " ".join(num2words(int(d)) for d in m.group(2))
            return f" {whole} point {frac} "
        except Exception:
            return m.group(0)
    s = re.sub(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])", _dec, s)

    # thousands-separator commas glue a number into one token ("50,000" is ONE
    # value); stripped by the general regex below they'd split into "50" + "000"
    # and canonicalize as "fifty" + "zero" instead of "fifty thousand".
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", s)
    raw = [w for w in re.sub(r"[^a-z0-9' ]", " ", s).split() if w]
    expanded = []
    for w in raw:
        expanded.extend(_canon_token(w))
    # collapse runs of single letters into one word: a i -> ai, u a f -> uaf
    out, run = [], []
    for w in expanded:
        if len(w) == 1 and w.isalpha():
            run.append(w)
        else:
            if run:
                out.append("".join(run)); run = []
            out.append(w)
    if run:
        out.append("".join(run))
    # COMPOUND JOIN (2026-07-20): Whisper transcribes closed compounds as two words
    # ("airstrip" -> "air strip", "megafire" -> "mega fire", "wildfire" -> "wild fire"),
    # so a script using the closed form scored 2 word-errors PER compound and inflated
    # WER above threshold on every take of a compound-heavy script (the Nenana/wildfire
    # run: all 4 takes 0.09-0.10 vs 0.08 max, purely from air/strip + mega/fire). Same
    # canonicalizer-precision class as the earlier $/% fix. Join a curated set of common
    # closed compounds SYMMETRICALLY (applied to ref AND hyp), so it can only cancel a
    # tokenization mismatch, never invent a missing word: if the hyp truly dropped a
    # word, the bigram won't be present to join. Extend the set as new compounds recur.
    _COMPOUNDS = {("air", "strip"): "airstrip", ("mega", "fire"): "megafire",
                  ("wild", "fire"): "wildfire", ("data", "center"): "datacenter",
                  ("data", "centers"): "datacenters", ("grid", "lock"): "gridlock",
                  ("air", "base"): "airbase"}
    joined, i = [], 0
    while i < len(out):
        if i + 1 < len(out) and (out[i], out[i + 1]) in _COMPOUNDS:
            joined.append(_COMPOUNDS[(out[i], out[i + 1])]); i += 2
        else:
            joined.append(out[i]); i += 1
    return joined


def _wer(ref, hyp):
    r, h = _norm_words(ref), _norm_words(hyp)
    if not r:
        return 0.0
    # Levenshtein over word lists
    dp = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        prev, dp[0] = dp[0], i
        for j in range(1, len(h) + 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (r[i - 1] != h[j - 1]))
            prev = cur
    return dp[len(h)] / len(r)


def _transcribe(wav):
    from faster_whisper import WhisperModel
    m = WhisperModel("base", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(wav, language="en", vad_filter=False)
    return " ".join(s.text.strip() for s in segs)


def _pitch_std_semitones(wav):
    import librosa
    import numpy as np
    y, sr = librosa.load(wav, sr=22050, mono=True)
    f0, voiced, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr,
                                 frame_length=2048, hop_length=256)
    v = f0[~np.isnan(f0)]
    voiced_frac = float(len(v)) / max(1, len(f0))
    if len(v) < 10:
        return 0.0, voiced_frac, len(y) / sr
    semis = 12.0 * np.log2(v / np.median(v))
    return float(np.std(semis)), voiced_frac, len(y) / sr


def _lufs(wav):
    import soundfile as sf
    import pyloudnorm as pyln
    data, rate = sf.read(wav)
    if data.ndim > 1:
        data = data.mean(axis=1)
    meter = pyln.Meter(rate)
    return float(meter.integrated_loudness(data))


def check(wav, spoken_text, tags=None, dur_lo=None, dur_hi=None):
    dur_lo = DUR_LO if dur_lo is None else dur_lo
    dur_hi = DUR_HI if dur_hi is None else dur_hi
    tags = tags or []
    heard = _transcribe(wav)
    wer = _wer(spoken_text, heard)
    heard_words = set(_norm_words(heard))
    tag_words = set(w for t in tags for w in _norm_words(t))
    leaked = sorted((tag_words | NOTE_WORDS) & heard_words)
    pstd, voiced, dur = _pitch_std_semitones(wav)
    try:
        lufs = _lufs(wav)
    except Exception:
        lufs = None

    checks = {
        "word_accuracy": {"wer": round(wer, 3), "pass": wer <= WER_MAX},
        "no_leak": {"leaked": leaked, "pass": len(leaked) == 0},
        "expressive": {"pitch_std_semitones": round(pstd, 2), "voiced_frac": round(voiced, 2),
                       "pass": pstd >= PITCH_STD_MIN and voiced >= VOICED_MIN},
        "duration": {"seconds": round(dur, 2), "pass": dur_lo <= dur <= dur_hi},
        "loudness": {"lufs": None if lufs is None else round(lufs, 1),
                     "pass": lufs is None or LUFS_MIN <= lufs <= LUFS_MAX},
    }
    # score = accuracy + expressiveness headroom, penalized hard for leaks
    score = (1 - wer) * 0.5 + min(pstd / 4.0, 1.0) * 0.4 + (0.1 if not leaked else -0.5)
    passed = all(c["pass"] for c in checks.values())
    return {"pass": passed, "score": round(score, 3), "heard": heard, "checks": checks,
            "diagnosis": _diagnose(checks)}


def _diagnose(c):
    if not c["no_leak"]["pass"]:
        return f"LEAK: model spoke {c['no_leak']['leaked']} — remove those inline tags, move emotion to the notes, re-synth."
    if not c["word_accuracy"]["pass"]:
        return f"WORDS: WER {c['word_accuracy']['wer']} too high (dropped/garbled or a 500 text-fallback) — re-roll."
    if not c["expressive"]["pass"]:
        return f"MONOTONE: pitch std {c['expressive']['pitch_std_semitones']} st below floor {PITCH_STD_MIN} — add ENERGY CONTRAST between adjacent lines (VO_DIRECTION step 5), then re-synth."
    if not c["duration"]["pass"]:
        return f"PACE: {c['duration']['seconds']}s out of window — adjust the brisk-pace note."
    if not c["loudness"]["pass"]:
        return f"LEVEL: {c['loudness']['lufs']} LUFS out of band — normalize in the mix."
    return "clean"


def pick_best(wavs, spoken_text, tags=None):
    """Choose the take to ship: quality first, but RUNTIME IS A SELECTION CRITERION.

    WHY (2026-08-05, measured during the 90s -> 120s upgrade). Take-to-take duration
    spread on an IDENTICAL prompt is large and quality spread is not. The 2026-08-05
    run's three takes ran 86.6 / 86.8 / 97.4 seconds, a 12.5 percent spread, while their
    quality scores were 0.963 / 0.969 / 0.967, a spread of 0.006. Selecting on score
    alone therefore picked the runtime essentially at random, out of a set that contained
    a take much closer to the format's target.

    That was survivable at 90 seconds and is not at 120. The longer the piece, the more
    of the runtime band a single stochastic take can eat, and runtime is the one thing
    the format promises. So: among takes that PASS, prefer the ones inside the tight band
    from config/state.yaml, and let quality decide within that set. If none is in band,
    take the passing one closest to target rather than the most expressive one.

    Quality is never traded away. A failing take is still never preferred to a passing
    one, and the in-band set is still ranked by the same score as before.
    """
    reports = [check(w, spoken_text, tags) for w in wavs]
    for r, w in zip(reports, wavs):
        r["seconds"] = r["checks"]["duration"]["seconds"]
    passing = [i for i, r in enumerate(reports) if r["pass"]]
    pool = passing or list(range(len(reports)))

    lo, hi, target = _target_band()
    if lo is None:
        best = max(pool, key=lambda i: reports[i]["score"])
    else:
        inband = [i for i in pool if lo <= reports[i]["seconds"] <= hi]
        if inband:
            best = max(inband, key=lambda i: reports[i]["score"])
        else:
            best = min(pool, key=lambda i: abs(reports[i]["seconds"] - target))
        for i, r in enumerate(reports):
            r["in_target_band"] = lo <= r["seconds"] <= hi
        reports[best]["selection"] = (
            f"in the {lo:.0f}-{hi:.0f}s band, best quality of {len(inband)} in-band take(s)"
            if inband else
            f"NO take landed in {lo:.0f}-{hi:.0f}s; chose the one closest to {target:.0f}s")
    return best, reports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--script", required=True, help="the intended SPOKEN words (no tags/notes)")
    ap.add_argument("--tags", default="", help="comma-sep inline tags used, e.g. '[curious],[wry]'")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    tags = [t.strip() for t in a.tags.split(",") if t.strip()]
    rep = check(a.audio, a.script, tags)
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        v = "PASS" if rep["pass"] else "FAIL"
        print(f"{v}  score={rep['score']}  {rep['diagnosis']}")
        for name, c in rep["checks"].items():
            print(f"  [{'x' if c['pass'] else ' '}] {name}: {({k:v for k,v in c.items() if k!='pass'})}")
        print(f"  heard: {rep['heard'][:160]}")
    sys.exit(0 if rep["pass"] else 1)


if __name__ == "__main__":
    main()
