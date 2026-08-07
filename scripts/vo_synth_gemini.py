#!/usr/bin/env python3
"""EXPRESSIVE VO SYNTH (Gemini native TTS) — the delivery upgrade.

Reads out/dispatch/vo_direction.json (produced by the vo-director agent following
docs/craft/VO_DIRECTION.md): the assembled expressive prompt + the per-line spoken
script + the inline tags used. Then:

  1. Renders N takes of the WHOLE passage in ONE call each (natural sentence-to-
     sentence flow), model gemini-3.1-flash-tts-preview, voice Sulafat. Retries on
     the random 500 "text-instead-of-audio" error; fails over to
     gemini-2.5-pro-preview-tts after repeated 500s.
  2. Runs scripts/vo_soundcheck.py on every take and keeps the BEST passing one
     (word accuracy, no spoken tags, pitch-variance/expressiveness, duration,
     loudness). Writes the QC report for the Gmail draft.
  3. Force-aligns the winning take against the script to emit vo_lines.json,
     words.json and captions.json (whole-file alignment; the API has no word
     timestamps), so build_scenes.py + the caption overlay work unchanged.

Config (env, with sane defaults):
  DISPATCH_GEMINI_VOICE   default Sulafat
  DISPATCH_GEMINI_MODEL   default gemini-3.1-flash-tts-preview
  DISPATCH_GEMINI_FALLBACK default gemini-2.5-pro-preview-tts
  VO_TAKES                default 3
Requires GEMINI_API_KEY (or GOOGLE_API_KEY).
"""
import os, sys, json, base64, urllib.request, urllib.error, ssl, time, re, difflib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vo_soundcheck as sc

REPO = os.path.abspath(os.path.join(HERE, ".."))
OUT = os.path.join(REPO, "out", "dispatch")
AUD = os.path.join(OUT, "audio")
SR = 44100
VOICE = os.environ.get("DISPATCH_GEMINI_VOICE", "Sulafat")
MODEL = os.environ.get("DISPATCH_GEMINI_MODEL", "gemini-3.1-flash-tts-preview")
FALLBACK = os.environ.get("DISPATCH_GEMINI_FALLBACK", "gemini-2.5-pro-preview-tts")
TAKES = int(os.environ.get("VO_TAKES", "3"))
CA = os.environ.get("SSL_CERT_FILE") or "/root/.ccr/ca-bundle.crt"
CTX = ssl.create_default_context(cafile=CA) if os.path.exists(CA) else ssl.create_default_context()


def _key():
    k = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not k:
        raise SystemExit("No GEMINI_API_KEY / GOOGLE_API_KEY in env.")
    return k


def _synth_once(prompt, model, voice):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": _key()})
    with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
        resp = json.loads(r.read().decode())
    b64 = resp["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    return np.frombuffer(base64.b64decode(b64), dtype="<i2")  # int16 @ 24k


def _synth_retry(prompt):
    """One good 24k int16 take, with 500-retry and pro fallback."""
    for model in (MODEL, FALLBACK):
        for d in (0, 4, 10, 20):
            if d:
                time.sleep(d)
            try:
                pcm = _synth_once(prompt, model, VOICE)
                if len(pcm) > 24000 * 2:  # at least ~2s of audio
                    return pcm, model
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 503):
                    continue
                raise
            except Exception:
                continue
        print(f"  {model} exhausted; failing over" if model == MODEL else f"  {FALLBACK} exhausted")
    raise RuntimeError("Gemini TTS failed on both models after retries.")


def _save_24k(pcm_i16, path):
    from scipy.io import wavfile
    wavfile.write(path, 24000, pcm_i16)


def _to_44k_int16(pcm_i16):
    a = pcm_i16.astype(np.float32) / 32768.0
    from math import gcd
    from scipy.signal import resample_poly
    g = gcd(24000, SR)
    a = resample_poly(a, SR // g, 24000 // g)
    return (np.clip(a, -1, 1) * 32767).astype(np.int16)


# ------------------------------------------------------------------ alignment
def _align_wholefile(wav24, lines):
    """Whisper word-timestamps on the whole take -> per-line spans + word list +
    caption cues. Mirrors dispatch_captions but over one file.

    NO initial_prompt: passing the script's own opening words as a prompt (as an
    earlier version did) makes Whisper treat that text as already-spoken context
    and HALLUCINATE-SKIP the real audio matching it -- reproduced 2026-07-19: a
    prompt built from this script's first ~220 chars caused the model to skip the
    first ~14.6s of a real 45s take (word timestamps jumped straight to sentence
    5), collapsing every earlier line's start/end to the same instant and wrecking
    caption/scene sync. Confirmed fix: omit initial_prompt entirely (unnecessary
    here anyway -- alignment is driven by the KNOWN intended text via difflib
    below, not by transcription accuracy, so no domain-hint prompt is needed)."""
    from faster_whisper import WhisperModel
    m = WhisperModel("small", device="cpu", compute_type="int8")
    segs, _ = m.transcribe(wav24, word_timestamps=True, language="en", vad_filter=False)
    heard = []
    for s in segs:
        for w in (s.words or []):
            heard.append({"w": w.word.strip(), "s": float(w.start), "e": float(w.end)})
    intended = []            # (line_idx, token)
    for i, ln in enumerate(lines):
        for tok in ln.split():
            intended.append((i, tok))
    # EXPAND every token to its FULL normalized word list (not just the first),
    # keeping an "owner" back-reference to the ORIGINAL token index. A single
    # token often canonicalizes to several words (num2words: "24"->"twenty four";
    # this run's $/% expansion: "$50"->"fifty dollars"; a hyphen split by the
    # regex: "non-attainment"->"non attainment") on BOTH sides independently, so
    # collapsing to word[0] (an earlier version of this function) silently drops
    # every word after the first -- reproduced 2026-07-19: it desynced `inn` and
    # `hn` by a growing offset (each multi-word token ate one array slot instead
    # of several), which cascaded into reversed/absurd time ranges (a total that
    # read 434s for a 51s take). Expanding both sides fully keeps `inn`/`hn` in
    # true 1:1 correspondence with what the matcher is actually comparing.
    inn, inn_owner = [], []
    for k, (_, t) in enumerate(intended):
        for w in sc._norm_words(t):
            inn.append(w); inn_owner.append(k)
    hn, hn_owner = [], []
    for j, x in enumerate(heard):
        for w in sc._norm_words(x["w"]):
            hn.append(w); hn_owner.append(j)
    sm = difflib.SequenceMatcher(a=inn, b=hn, autojunk=False)
    span = [None] * len(intended)   # [k] -> [start, end], accumulated across all its expanded words

    def _extend(k, s, e):
        if span[k] is None:
            span[k] = [s, e]
        else:
            span[k][0] = min(span[k][0], s); span[k][1] = max(span[k][1], e)

    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for off in range(i2 - i1):
                k = inn_owner[i1 + off]
                hs, he = heard[hn_owner[j1 + off]]["s"], heard[hn_owner[j1 + off]]["e"]
                _extend(k, hs, he)
        elif tag in ("replace", "delete"):
            hs = heard[hn_owner[j1]]["s"] if j1 < len(hn_owner) else (heard[-1]["e"] if heard else 0.0)
            he = heard[hn_owner[j2 - 1]]["e"] if 0 < j2 <= len(hn_owner) and j2 > j1 else hs
            ks = sorted(set(inn_owner[i1:i2])) or ([inn_owner[i1]] if i1 < len(inn_owner) else [])
            n = max(1, len(ks))
            for idx, k in enumerate(ks):
                _extend(k, hs + (he - hs) * idx / n, hs + (he - hs) * (idx + 1) / n)
    timed = [None if s is None else (s[0], s[1]) for s in span]
    # guard against any inverted/degenerate window (start > end) slipping through
    timed = [None if t is None else (t[0], max(t[0], t[1])) for t in timed]
    for k in range(len(timed)):
        if timed[k] is None:
            prev = next((timed[j] for j in range(k - 1, -1, -1) if timed[j]), None)
            nxt = next((timed[j] for j in range(k + 1, len(timed)) if timed[j]), None)
            timed[k] = (prev[1], nxt[0]) if prev and nxt else (prev or nxt or (0.0, 0.25))
    # enforce monotonic non-decreasing starts across the whole take (belt-and-
    # suspenders: expansion/accumulation above should already guarantee this, but
    # a forced-alignment output feeding captions/scene-cuts must never regress)
    for k in range(1, len(timed)):
        if timed[k][0] < timed[k - 1][0]:
            timed[k] = (timed[k - 1][0], max(timed[k - 1][0], timed[k][1]))
    words = [{"w": tok, "s": round(timed[n][0], 3), "e": round(max(timed[n][0] + 0.04, timed[n][1]), 3),
              "seg": li} for n, (li, tok) in enumerate(intended)]
    # per-line spans
    line_spans = []
    for i, ln in enumerate(lines):
        ws = [w for w in words if w["seg"] == i]
        if ws:
            line_spans.append({"idx": i, "text": ln, "start": ws[0]["s"], "end": ws[-1]["e"]})
    total = max(w["e"] for w in words)
    # caption cues (sentence/length break, anti-orphan)
    cues, cur = [], []
    for w in words:
        cur.append(w)
        j = " ".join(x["w"] for x in cur)
        if re.search(r"[.!?]$", w["w"]) or len(j) >= 30 or len(cur) >= 6 or cur[0]["seg"] != w["seg"]:
            cues.append({"text": " ".join(x["w"] for x in cur), "start": cur[0]["s"],
                         "end": cur[-1]["e"], "seg": cur[0]["seg"]}); cur = []
    if cur:
        cues.append({"text": " ".join(x["w"] for x in cur), "start": cur[0]["s"],
                     "end": cur[-1]["e"], "seg": cur[0]["seg"]})
    # enforce monotonic, non-overlapping, min-dwell cue timing for readable display
    MIN_CUE, GAP = 0.7, 0.03
    for i in range(len(cues)):
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else cues[i]["end"] + MIN_CUE + 1
        if i > 0:
            cues[i]["start"] = max(cues[i]["start"], cues[i - 1]["end"] + GAP)
        cues[i]["start"] = min(cues[i]["start"], max(0.0, nxt - 0.2))
        cues[i]["end"] = min(max(cues[i]["end"], cues[i]["start"] + MIN_CUE), max(cues[i]["start"] + 0.2, nxt - GAP))
    return words, line_spans, total, cues


def _strip_tags(s):
    """Remove [inline tags] — they're for the TTS prompt, never for captions/display."""
    return re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", s)).strip()


def _reconcile_plan_with_script(lines):
    """RECONCILE the plan against the script (added 2026-07-26 after this script silently
    narrated a stale draft; converted from a hard gate to a repair 2026-08-05).

    This script reads ONLY vo_direction.json. That file is written by the
    vo-director agent, so it is a SNAPSHOT of whatever the script said at the
    moment the agent ran. If the script is then revised (a creative gate demands
    a rewrite, a line is added, a clause is reordered), the plan silently goes
    stale UNDER the script and the run synthesizes, mixes, captions and ships the
    OLD narration. Nothing downstream can detect it: the audio is clean, the
    soundcheck passes, the alignment is monotonic, and the words are simply wrong.

    That is exactly what happened on 2026-07-26. Gate 0B required three new lines
    (the fair defense actually spoken, a 3,500-versus-3,048 split, and an explicit
    no-algorithm statement) plus one clause reorder. The plan predated all of it,
    so the first synth produced a 12 line read of a 14 line script and dropped the
    fairness line entirely. Caught only because the QC transcript was read by eye.

    Same failure CLASS as the 2026-07-19 stale-scratch incident, and it gets the
    same treatment: a code guard the pipeline runs, not a doctrine reminder. The
    run fails loudly here instead of shipping the wrong words.
    """
    sp = os.path.join(OUT, "vo_script.txt")
    if not os.path.exists(sp):
        return None, []   # nothing to compare against; the plan is the only source of truth
    want = [l.strip() for l in open(sp).read().strip().split("\n") if l.strip()]
    got = [l.strip() for l in lines]
    if want == got:
        return None, []
    msg = [
        "VO PLAN IS STALE. vo_direction.json does not match vo_script.txt.",
        f"  script lines: {len(want)}    plan lines: {len(got)}",
    ]
    for i in range(max(len(want), len(got))):
        w = want[i] if i < len(want) else "<missing from plan>"
        g = got[i] if i < len(got) else "<missing from plan>"
        if w != g:
            msg.append(f"  line {i}:\n    script: {w}\n    plan:   {g}")
    msg.append("REPAIRING: the SCRIPT is the source of truth (it is the locked copy the "
               "fact-check and the caption both key off), so the plan is rebuilt from it. "
               "Per-line direction is preserved for every line whose spoken text is "
               "unchanged; changed or new lines carry no inline tags, which is the safe "
               "default because an unvetted tag risks being read aloud.")
    return want, msg


def _num_words(n):
    """120 -> 'one hundred and twenty', for a pace line the model reads as prose."""
    try:
        from num2words import num2words
        return num2words(int(n))
    except Exception:
        return str(int(n))


def _pace_line(target):
    """THE REQUIRED PACE PARAGRAPH, built around the CURRENT target from config.

    docs/craft/VO_DIRECTION.md step 7 makes this required text, because it is the
    format's only reliable length control: the same 288-word script runs 105 seconds
    with a generic "BRISK and energetic" line and 120 with one that names the runtime.
    Generating it from config/state.yaml means the next format change moves it too,
    instead of leaving a sentence that names the old length.
    """
    mins = target / 60.0
    unit = (f"{_num_words(round(mins)).upper()} MINUTE PIECE" if abs(mins - round(mins)) < 0.05
            else f"{_num_words(round(target)).upper()} SECOND PIECE")
    return (f"Pace: MEASURED and unhurried. THIS IS A {unit}, about {_num_words(round(target))} "
            f"seconds, and the read must FILL it, so give every sentence room to land and take a "
            f"real breath at every period. Do not rush the numbers. Vary the tone line to line so "
            f"no two sentences sound the same.")


def _pace_names_runtime(head, target):
    """Does the Pace line actually NAME the target runtime, or is it generic?"""
    m = re.search(r"^Pace:.*$", head, re.M)
    if not m:
        return False
    line = m.group(0).lower()
    mins = target / 60.0
    ok = {str(int(target)), _num_words(round(target)).lower()}
    if abs(mins - round(mins)) < 0.05:
        ok |= {f"{_num_words(round(mins))} minute".lower(), f"{int(round(mins))} minute"}
    return any(tok in line for tok in ok)


def repair_prompt(prompt, plan):
    """REPAIR a damaged or generic prompt IN PLACE. Never stops the run.

    THE ONE OUTCOME LAW (scripts/no_exit.py): the only terminal state is a delivered
    video. An earlier version of this raised SystemExit on a damaged prompt, which put a
    brand new stop in the delivery path -- exactly the kind of thing that law exists to
    prevent. A damaged prompt is not a reason to have no video; it is a reason to rebuild
    the prompt, which is mechanical, because every part of it is recoverable from the plan
    plus the canonical template.

    WHAT IT GUARDS, and why each clause is a defect somebody already shipped:

      the `Transcript:` delimiter   Without it the model reads the director's notes aloud.
                                    On 2026-08-05 a hand-patch cut assembled_prompt at the
                                    FIRST occurrence of the substring `Transcript:`, which
                                    appears inside the preamble's own sentence, deleting
                                    the audio profile, the notes, the style and pace lines
                                    and the delimiter. The film shipped narrated with no
                                    direction at all and nothing noticed, because an
                                    undirected read is still fluent audio.
      the Pace line NAMING the      A generic pace line is worth ~15 percent of runtime.
      runtime                       At 288 words that is a 105-second film in a 112-130
                                    band, and it happens on three takes out of three, so
                                    it is the DEFAULT failure rather than an unlucky one.
                                    Catching it here fixes it before any TTS is spent.
      the transcript matching       Nothing downstream reads `lines`; the synth sends
      the plan                      `assembled_prompt` and only that. A plan whose lines
                                    are perfect and whose prompt is stale narrates the
                                    wrong thing at the right length.

    Returns (prompt, notes). notes is a list of human-readable repairs made, which the
    caller prints and records in vo_report.json so a silent rescue is still visible.
    """
    lo, hi, target = sc._target_band()
    target = target or 120.0
    plan_lines = plan.get("lines") or []
    notes = []
    delim = "\n" + "Transcript:" + "\n"
    head, body = (prompt.split(delim, 1) if delim in prompt else (None, None))

    if head is None:
        notes.append("NO 'Transcript:' delimiter on its own line: the whole notes block was "
                     "missing or the prompt had been split on the bare substring (which also "
                     "occurs inside the preamble sentence). Rebuilt from the plan.")
    else:
        if "Pace:" not in head:
            notes.append("no Pace line in the director's notes")
        elif not _pace_names_runtime(head, target):
            notes.append(f"the Pace line did not name the target runtime, which is the format's "
                         f"only reliable length control; replaced with the required "
                         f"{target:.0f}s paragraph")
        if "Style:" not in head:
            notes.append("no Style line")
        if "AUDIO PROFILE" not in head:
            notes.append("no '# AUDIO PROFILE:' block")
        tok = lambda x: re.findall(r"[a-z0-9]+", _strip_tags(x).lower())
        got, want = tok(body), tok(" ".join(l["text"] for l in plan_lines))
        if len(got) < 0.95 * len(want):
            notes.append(f"the prompt's transcript was shorter than the plan ({len(got)} words vs "
                         f"{len(want)}); the synth sends the PROMPT, so content was going missing")
        elif difflib.SequenceMatcher(a=want, b=got, autojunk=False).ratio() < 0.90:
            notes.append("the prompt's transcript did not match the plan's lines")

    if not notes:
        return prompt, []

    # Rebuild. Salvage whatever of the head is still good; force the Pace paragraph.
    def _salvage(pat, fallback):
        m = re.search(pat, head or "", re.M)
        return m.group(0).strip() if m else fallback
    profile = _salvage(r"^# AUDIO PROFILE:.*$",
                       "# AUDIO PROFILE: the house narrator: warm, grounded, quietly witty. "
                       "Neutral American accent, light and natural, not announcer-y.")
    style = _salvage(r"^Style:.*$", None) or (
        (plan.get("style_prompt") or "").split("\n")[0].strip()
        or "Style: warm, grounded and conversational; let the facts carry the weight.")
    if not style.startswith("Style:"):
        style = "Style: " + style.lstrip()
    emphasis = _salvage(r"^Emphasis:.*$",
                        "Emphasis: lean on the key word in each line; let numbers land.")
    rebuilt = "\n".join([
        'Read ONLY the transcript below aloud as speech. The lines above "Transcript:" '
        "are direction; never speak them.",
        profile,
        "### DIRECTOR'S NOTES",
        style,
        _pace_line(target),
        emphasis,
        "Transcript:",
        *[l["text"] for l in plan_lines],
    ])
    return rebuilt, notes


def main():
    os.makedirs(AUD, exist_ok=True)
    plan = json.load(open(os.path.join(OUT, "vo_direction.json")))
    prompt = plan["assembled_prompt"]
    lines = [_strip_tags(l["text"]) for l in plan["lines"]]  # SPOKEN words only (no tags)
    # THE SCRIPT WINS, AND A MISMATCH IS REPAIRED RATHER THAN FATAL (THE ONE OUTCOME LAW).
    # A stale plan used to stop the run. But vo_script.txt is the locked copy that the
    # fact-check and the caption both key off, so reconciling is mechanical: take the
    # script's lines, and carry each line's direction across wherever the spoken text is
    # unchanged. Only genuinely new or edited lines lose their per-line notes.
    _want, _fixes = _reconcile_plan_with_script(lines)
    if _want is not None:
        by_text = {_strip_tags(l["text"]).strip(): l for l in plan["lines"]}
        plan["lines"] = [
            dict(by_text[w], idx=i) if w in by_text
            else {"idx": i, "text": w, "intent": "", "emphasis": "", "energy": 3, "tags": []}
            for i, w in enumerate(_want)
        ]
        lines = [_strip_tags(l["text"]) for l in plan["lines"]]
    # PRONUNCIATION BELONGS IN THE NOTES, NEVER IN THE TRANSCRIPT (added 2026-08-07).
    # docs/craft/VO_DIRECTION.md asks the director to respell tricky proper nouns
    # phonetically. Until today that respelling was written INTO the transcript, where
    # _reconcile_plan_with_script correctly saw it as a divergence from the locked script
    # and reverted it, so the instruction could never once take effect. It also could not
    # be allowed to take effect there: the transcript must stay byte-identical to
    # vo_script.txt or the WER gate compares the ASR against the wrong words and the
    # captions burn text the voice did not say. So a respelling is now DATA in
    # plan["pronunciations"], injected as a direction line ABOVE the Transcript: delimiter,
    # where the model reads it as instruction and never speaks it.
    _pron = plan.get("pronunciations") or {}
    if _pron:
        _pl = "Pronunciation: " + "; ".join(f'say "{k}" as {v}' for k, v in _pron.items())
        _d = "\nTranscript:\n"
        if _d in prompt:
            prompt = prompt.replace(_d, "\n" + _pl + _d, 1)
            _fixes = list(_fixes) + [f"pronunciation guide injected into the notes ({len(_pron)} entries)"]
    prompt, _pfixes = repair_prompt(prompt, plan)
    _fixes = list(_fixes) + list(_pfixes)
    for _f in _fixes:
        print(f"  !! PROMPT REPAIRED: {_f}")
    spoken = " ".join(lines)
    tags = sorted({t for l in plan["lines"] for t in l.get("tags", [])})

    # REUSE (2026-07-23): a crashed run after synth (e.g. the librosa gap that killed the
    # soundcheck) should not re-spend TTS calls re-rendering identical takes. With
    # VO_REUSE_TAKES=1, reuse any vo_take_{n}.wav already on disk from THIS run instead of
    # re-synthesizing it. Opt-in only, so default behavior is unchanged; reuse is safe here
    # because run_guard already stamps the run and the takes are this run's own output.
    REUSE = os.environ.get("VO_REUSE_TAKES", "") == "1"
    takes = []
    for n in range(TAKES):
        p = os.path.join(AUD, f"vo_take_{n}.wav")
        if REUSE and os.path.exists(p):
            takes.append((p, MODEL))
            print(f"take {n}: reused {os.path.getsize(p)} bytes (VO_REUSE_TAKES=1)")
            continue
        pcm, used = _synth_retry(prompt)
        _save_24k(pcm, p)
        takes.append((p, used))
        print(f"take {n}: {len(pcm)/24000:.1f}s ({used})")

    best_i, reports = sc.pick_best([p for p, _ in takes], spoken, tags)

    # ---- RUNTIME: RE-ROLL, THEN ACCEPT. NEVER STOP. -------------------------------
    # The format's target runtime was enforced nowhere in code: the soundcheck's window
    # is deliberately wide (~62-176s) because its job is catching a grossly broken synth
    # rather than policing pace. So a 105-second take passed everything and the run would
    # have shipped it believing it had made a two-minute film.
    #
    # The first version of this fix raised SystemExit, which was wrong for a reason the
    # repo already had written down: THE ONE OUTCOME LAW (scripts/no_exit.py) says the
    # only terminal state is a delivered video, and I had put a brand new stop directly in
    # the delivery path. A wrong-length take is not a reason to have no video.
    #
    # So it re-rolls instead. repair_prompt has already forced the runtime-naming pace
    # paragraph, which is the lever that is actually worth 15 percent of pace, so the
    # common case is fixed before any of this runs. If takes still land outside the band,
    # spend one more round rather than none, then take the best available and CARRY THE
    # MISS FORWARD LOUDLY in vo_report.json, where the panel and the dated email both read
    # it. A visible miss on a delivered film beats a clean stop.
    lo, hi, target = sc._target_band()
    runtime_note = None
    if lo is not None:
        for extra in range(1):                       # one re-roll, then accept
            secs = reports[best_i]["checks"]["duration"]["seconds"]
            if lo <= secs <= hi:
                break
            n_words = len(spoken.split())
            rate = n_words / secs * 60 if secs else 0
            want = int(round(target * rate / 60))
            print(f"  !! RUNTIME {secs:.1f}s outside the {lo:.0f}-{hi:.0f}s band "
                  f"({rate:.1f} wpm over {n_words} words; {target:.0f}s wants about {want}). "
                  f"Re-rolling {TAKES} more take(s) on the repaired prompt.")
            for n in range(TAKES):
                q = os.path.join(AUD, f"vo_take_r{extra}{n}.wav")
                pcm, used = _synth_retry(prompt)
                _save_24k(pcm, q)
                takes.append((q, used))
                print(f"re-roll take {n}: {len(pcm)/24000:.1f}s ({used})")
            best_i, reports = sc.pick_best([p for p, _ in takes], spoken, tags)
        secs = reports[best_i]["checks"]["duration"]["seconds"]
        if not (lo <= secs <= hi):
            n_words = len(spoken.split())
            rate = n_words / secs * 60 if secs else 0
            want = int(round(target * rate / 60))
            delta = want - n_words
            runtime_note = (
                f"RUNTIME {secs:.1f}s is outside the {lo:.0f}-{hi:.0f}s band (target {target:.0f}s) "
                f"after a re-roll. Delivered {rate:.1f} wpm over {n_words} words; at that rate "
                f"{target:.0f}s wants about {want} words ({'add' if delta > 0 else 'cut'} roughly "
                f"{abs(delta)}). The pace paragraph was already repaired to name the runtime, so "
                f"the remaining gap is script length. SHIPPING THE BEST TAKE ANYWAY: a delivered "
                f"film with a stated miss beats a stopped run.")
            print(f"  !! {runtime_note}")
        else:
            print(f"  runtime {secs:.1f}s is inside the {lo:.0f}-{hi:.0f}s band")

    best_wav, best_model = takes[best_i]
    print(f"BEST take {best_i} ({best_model}): {reports[best_i]['diagnosis']}  score={reports[best_i]['score']}")

    # write the winning VO at 44.1k for the pipeline
    from scipy.io import wavfile
    _, pcm24 = wavfile.read(best_wav)
    wavfile.write(os.path.join(AUD, "vo.wav"), SR, _to_44k_int16(pcm24))

    # align the winning take -> timings for scenes + captions.
    # ALIGN THE 44.1k vo.wav, NOT the 24k take (2026-07-24 fix): faster-whisper on the raw
    # 24k take intermittently mis-timestamps a whole run of opening (or trailing) words,
    # collapsing several consecutive lines to a single instant and wrecking scene/caption
    # sync (reproduced this run: lines 0-3 all pinned to 20.16s though speech starts at 0.0).
    # Re-aligning the SAME content resampled to 44.1k yields a clean monotonic 0..total
    # alignment every time. The word text is identical; only the timestamps differ, so this
    # is purely a timing-stability fix.
    words, line_spans, total, cues = _align_wholefile(os.path.join(AUD, "vo.wav"), lines)
    json.dump({"words": words, "speech_end": round(total, 3), "total": 60.0, "fps": 30},
              open(os.path.join(AUD, "words.json"), "w"), indent=2)
    json.dump({"total": round(total, 3), "voice": VOICE, "model": best_model, "lines": line_spans},
              open(os.path.join(OUT, "vo_lines.json"), "w"), indent=2)
    json.dump(cues, open(os.path.join(OUT, "captions.json"), "w"), indent=2)
    json.dump({"backend": "gemini-tts", "model": best_model, "voice": VOICE, "take": best_i,
               "takes": TAKES, "soundcheck": reports[best_i],
               "prompt_repairs": _fixes, "runtime_warning": runtime_note,
               "all_reports": [{"pass": r["pass"], "score": r["score"], "diagnosis": r["diagnosis"]} for r in reports],
               "watermark": "SynthID (Google) embedded in all Gemini TTS audio",
               "license": "Google Gemini API preset voice (per-use billing)"},
              open(os.path.join(OUT, "vo_report.json"), "w"), indent=2)
    print(f"wrote vo.wav ({total:.1f}s), vo_lines.json ({len(line_spans)} lines), captions.json ({len(cues)} cues), vo_report.json")

    # acting data (mouth envelope + emphasis accents) always tracks the shipped take
    import vo_envelope
    vo_envelope.main()


if __name__ == "__main__":
    main()
