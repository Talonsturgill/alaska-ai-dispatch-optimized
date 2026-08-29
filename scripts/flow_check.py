#!/usr/bin/env python3
"""flow_check.py, the VISUAL FLOW analyzer (never-rest cadence + say-it-show-it + sound-paired).

Scores a Dispatch's PLAN (out/dispatch/storyboard.json > beats[]) and, when present, its rendered
audio (out/dispatch/sfx_events.json + audio/words60.json/timing60.json) against
config/visual_flow.yaml. The legacy audio/sfx_events.json split ledger is a hard failure.
Doctrine: docs/craft/VISUAL_FLOW.md.

Two roles:
  1. BACK-TEST instrument: `python scripts/flow_check.py --report [--dir out/dispatch]` prints metrics
     for a run (handles the OLD string-beat format too, so past dispatches can be measured).
  2. GATE core: `python scripts/flow_check.py` exits non-zero if a HARD flow rule fails (wired into
     Gate 0A via storyboard_check.py once thresholds are calibrated).

Beat schema (new): each beat is an object {t:"9.0-13.5", vo, shows, sfx, means}. See VISUAL_FLOW.md §3.
numpy-free; stdlib + pyyaml only.
"""
import sys, os, json, argparse, re, math
from pathlib import Path
import yaml

from sfx_contract import LEGACY_SIDECAR_REL, sidecar_facts
from strict_json import StrictJSONError, load_path

ROOT = Path(__file__).resolve().parent.parent
CFG = yaml.safe_load((ROOT / "config" / "visual_flow.yaml").read_text())


def _parse_t(t):
    """'9.0-13.5' -> (9.0, 13.5). The '-' is a RANGE separator, not a minus (times are never negative).
    Tolerant of 'X to Y', a single number, or junk."""
    if isinstance(t, (int, float)):
        return float(t), None
    s = str(t or "").strip().lower().replace(" to ", "-")
    parts = [p for p in s.split("-") if p.strip()]

    def _num(x):
        m = re.search(r"\d+(?:\.\d+)?", x)
        return float(m.group()) if m else None
    a = _num(parts[0]) if parts else None
    b = _num(parts[1]) if len(parts) > 1 else None
    return a, b



def _t_num(v, default=0.0):
    """Beat/reveal timestamps are USUALLY floats but the documented schema also allows a
    range string like "0.0-3.5", and four archived boards use it. A bare float() on those
    raises ValueError and kills the whole gate with a traceback instead of reporting
    problems, which is strictly worse than the defect it was added to catch."""
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return default
    try:
        return float(s)
    except ValueError:
        head = s.split("-")[0].split("to")[0].strip()
        try:
            return float(head)
        except ValueError:
            return default

def piece_runtime(sb, beats=None):
    """THE PIECE'S RUNTIME, which is not the same thing as its last beat's start time.

    Every length-gated rule in this repo keys off "how long is this film", and both gates
    were answering that with the START timestamp of the final beat. That is short by
    however long the last beat runs plus the outro hold: on the shipped 2026-08-05 board
    the last beat starts at 84.6s and the film is 88.8s, a 4.2s gap.

    At 90s a 4-second error was invisible because no threshold sat near the end of the
    band. At 120s it silently disarms the entire two-minute format. A perfectly legal
    112.8s film whose last beat starts at 108.6s reads as a 108.6s piece, falls under the
    110s threshold, and skips the throughline gate, the reveal-per-third rule, the 60s
    loop span, the 85s payoff floor and the mandatory second open loop. Verified: only the
    rehook rule fires, because its windows are absolute rather than length-derived.

    So: trust the board's declared `total_seconds` first, since that is the runtime the
    film is actually cut to. Fall back to the last beat's END, then to its start.
    """
    for key in ("total_seconds", "total"):
        try:
            v = float(sb.get(key))
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    if beats is None:
        beats, _ = load_beats(sb)
    timed = [b for b in beats if b["t0"] is not None]
    if not timed:
        return 0.0
    return max((b["t1"] or b["t0"]) for b in timed)


def load_beats(sb):
    """Return (beats_normalized, fmt) where fmt in {'object','string','mixed','none'}."""
    raw = sb.get("beats") or []
    if not raw:
        return [], "none"
    kinds = {"object" if isinstance(b, dict) else "string" for b in raw}
    fmt = "object" if kinds == {"object"} else "string" if kinds == {"string"} else "mixed"
    out = []
    for i, b in enumerate(raw):
        if isinstance(b, dict):
            a, e = _parse_t(b.get("t"))
            out.append({"i": i, "t0": a, "t1": e, "vo": b.get("vo", ""), "shows": b.get("shows", b.get("new", "")),
                        "sfx": b.get("sfx", ""), "means": b.get("means", ""), "choreo": b.get("choreo"),
                        "rehook": b.get("rehook", ""), "obj": True})
        else:
            out.append({"i": i, "t0": None, "t1": None, "vo": "", "shows": str(b), "sfx": "", "means": "", "obj": False})
    return out, fmt


def analyze(dirp):
    d = Path(dirp)
    sb = load_path(d / "storyboard.json", label="storyboard")
    if not isinstance(sb, dict):
        raise StrictJSONError("storyboard must be a JSON object")
    beats, fmt = load_beats(sb)
    bc = CFG["beats"]; cov = CFG["coverage"]; sc = CFG["sfx"]
    R = {"beat_format": fmt, "n_beats": len(beats), "problems": [], "warnings": [], "metrics": {}}

    # ---- timing / never-rest gap (only computable when beats declare t) ----
    timed = [b for b in beats if b["t0"] is not None]
    R["metrics"]["timed_beats"] = len(timed)

    # ---- beat count: DERIVED FROM THE PIECE'S OWN LENGTH, not a flat number -------
    # The floor was a constant that had to be hand-raised at every format change (12 at
    # 60s, 18 at 90s, 24 at 120s), and each of those numbers was really the same
    # arithmetic written out by hand: a piece cannot satisfy the never-rest ceiling with
    # fewer than piece_end / max_gap_s beats. Computing it means the floor tracks the
    # runtime automatically, and, more importantly, it means raising the format's target
    # does not retroactively fail a legal SHORTER board. An archived 86s film needs 18
    # beats and still needs 18 after the format moves to 120s. The configured `min` stays
    # as the fallback for boards whose beats carry no timestamps.
    need = bc["min"]
    _pe0 = piece_runtime(sb, beats) or None
    if _pe0:
        need = max(1, math.ceil(_pe0 / bc["max_gap_s"]))
        R["metrics"]["beats_required"] = need
    if len(beats) < need:
        R["problems"].append(
            f"beats_min: {len(beats)} beats < {need} required story-advancing beats"
            + (f" for a {_pe0:.0f}s piece at the {bc['max_gap_s']}s never-rest ceiling" if _pe0 else ""))
    # beats.max was config that nothing read. It is ADVISORY, not a hard fail: "more than
    # this is usually strobing, not storytelling" is a judgement about whether the cuts
    # carry story, which a count cannot settle. But config that no code consults is config
    # that quietly drifts out of true, so it surfaces as a warning the flow-critic can weigh.
    if bc.get("max") and len(beats) > bc["max"]:
        R["warnings"].append(f"beats_max: {len(beats)} beats > {bc['max']}; check this is density "
                             f"and not strobing (VISUAL_FLOW.md: each beat must ADVANCE the story)")
    if len(timed) >= 2:
        starts = sorted(b["t0"] for b in timed)
        gaps = [round(starts[i + 1] - starts[i], 2) for i in range(len(starts) - 1)]
        med = sorted(gaps)[len(gaps) // 2]
        over = [g for g in gaps if g > bc["max_gap_s"]]
        R["metrics"]["start_to_start_gaps"] = gaps
        R["metrics"]["median_gap_s"] = med
        R["metrics"]["max_gap_s"] = max(gaps)
        if over:
            R["problems"].append(f"max_gap: {len(over)} beat gap(s) exceed the {bc['max_gap_s']}s never-rest "
                                 f"ceiling (worst {max(gaps)}s), schedule a change in that window")
        lo, hi = bc["target_gap_s"]
        if not (lo <= med <= hi):
            R["warnings"].append(f"median_gap_in_target: median beat gap {med}s is outside the {lo} to {hi}s "
                                 f"sweet spot")
        if starts[0] > cov["head_start_s"]:
            R["warnings"].append(f"head_start: first beat at {starts[0]}s (> {cov['head_start_s']}s); open on the stake sooner")

        # ---- ENGAGEMENT block (docs/craft/ENGAGEMENT.md, upgrade #3) ----
        eng = CFG.get("engagement") or {}
        if eng:
            # FRONTLOAD: the first N seconds carry the piece's highest density
            fw, fmin = eng["frontload_window_s"], eng["frontload_min_beats"]
            early = sum(1 for s0 in starts if s0 < fw)
            R["metrics"]["frontload_beats"] = early
            if early < fmin:
                R["problems"].append(f"FRONTLOAD: only {early} beats start inside the first {fw}s "
                                     f"(< {fmin}); 50-60% of abandonment happens up front — front-load "
                                     f"the density (ENGAGEMENT.md §2.1)")
            # METRONOME: 3+ consecutive near-identical gaps habituate the eye
            tol, max_run = eng["metronome_tol_s"], eng["metronome_max_run"]
            run, worst_run, run_val = 1, 1, None
            for i in range(1, len(gaps)):
                if abs(gaps[i] - gaps[i - 1]) <= tol:
                    run += 1
                    if run > worst_run:
                        worst_run, run_val = run, gaps[i]
                else:
                    run = 1
            R["metrics"]["metronome_worst_run"] = worst_run
            if worst_run > max_run:
                R["problems"].append(f"METRONOME: {worst_run} consecutive beat gaps within ±{tol}s of "
                                     f"each other (~{run_val}s each); fixed cadence habituates — jitter "
                                     f"the intervals (ENGAGEMENT.md §2.3)")
            # REHOOK: a declared re-hook beat in EVERY drift window the piece is long enough
            # to reach. At 60s there was one window. The 90s format has two, because the
            # 25-38s cliff gets a sibling once a viewer has been watching a full minute with
            # no idea how much is left. A window the piece never reaches is exempt.
            piece_end = piece_runtime(sb, beats)
            windows = eng.get("rehook_windows_s") or [eng["rehook_window_s"]]
            found_total = 0
            for rlo, rhi in windows:
                if piece_end <= rhi:                  # piece never spans this window; exempt,
                    continue                          # same rule the single-window check used
                hits = [b for b in timed
                        if str(b.get("rehook", "")).strip() and rlo <= b["t0"] <= rhi]
                found_total += len(hits)
                if not hits:
                    R["problems"].append(f"REHOOK: no beat in the {rlo}-{rhi}s drift window declares "
                                         f"`rehook` (the escalation/promise turn that re-grabs a sagging "
                                         f"viewer — ENGAGEMENT.md §2.4). A {piece_end:.0f}s piece must "
                                         f"re-grab in EVERY window it runs through, not just the first.")
            R["metrics"]["rehook_beats_in_window"] = found_total
            R["metrics"]["rehook_windows_checked"] = [w for w in windows if piece_end > w[1]]

            # OPEN LOOP: a 90s film needs a promise planted early and paid late, or the
            # viewer has no reason to still be there at 70s except inertia. Declared on the
            # board as open_loop {plant_t, pay_t, what}.
            plant_by = eng.get("open_loop_plant_by_s")
            min_span = eng.get("open_loop_min_span_s")
            if plant_by and min_span and piece_end >= 75:      # only binding on long-format pieces
                ol = (sb.get("open_loop") or {}) if isinstance(sb, dict) else {}
                pt, yt = ol.get("plant_t"), ol.get("pay_t")
                if pt is None or yt is None or not str(ol.get("what", "")).strip():
                    R["problems"].append(
                        f"OPEN LOOP: a {piece_end:.0f}s piece declares no `open_loop` "
                        f"{{plant_t, pay_t, what}}. At this length a viewer needs an unanswered "
                        f"promise planted by {plant_by}s and paid at least {min_span}s later, or the "
                        f"back half runs on inertia (ENGAGEMENT.md §2.6).")
                else:
                    if _t_num(pt) > plant_by:
                        R["problems"].append(f"OPEN LOOP: planted at {pt}s, must be planted by {plant_by}s")
                    if _t_num(yt) - _t_num(pt) < min_span:
                        R["problems"].append(f"OPEN LOOP: plant {pt}s to pay {yt}s spans "
                                             f"{_t_num(yt)-_t_num(pt):.1f}s, needs >= {min_span}s to be a loop")
                    R["metrics"]["open_loop_span_s"] = round(_t_num(yt) - _t_num(pt), 2)

                    # ---- TWO-MINUTE RULES ------------------------------------------
                    # One loop cannot hold two minutes. The 2026-08-05 film planted at
                    # 7.5s and paid at 46s, which is correct at 90s and would leave
                    # SEVENTY SECONDS of inertia at 120s. Above the threshold the primary
                    # loop must reach into minute two, and a second, staggered loop has to
                    # carry the middle. Everything here is gated on piece length, so a 90s
                    # or 60s board is untouched by it.
                    long_from = eng.get("open_loop_long_from_s")
                    if long_from and piece_end >= long_from:
                        long_span = eng.get("open_loop_long_min_span_s")
                        pay_after = eng.get("open_loop_pay_after_s")
                        span = _t_num(yt) - _t_num(pt)
                        if long_span and span < long_span:
                            R["problems"].append(
                                f"OPEN LOOP: a {piece_end:.0f}s piece spans only {span:.1f}s "
                                f"({pt}s to {yt}s); needs >= {long_span}s. A loop that closes "
                                f"early leaves the back half running on inertia.")
                        if pay_after and _t_num(yt) < pay_after:
                            R["problems"].append(
                                f"OPEN LOOP: paid at {yt}s, must land no earlier than {pay_after}s "
                                f"in a {piece_end:.0f}s piece, or minute two owes the viewer nothing.")

                        # THE SECOND LOOP, deliberately staggered.
                        ol2 = (sb.get("open_loop_2") or {}) if isinstance(sb, dict) else {}
                        if not ol2 and isinstance(sb.get("open_loops"), list) and len(sb["open_loops"]) > 1:
                            ol2 = sb["open_loops"][1] or {}
                        w2 = eng.get("open_loop_2_plant_window_s")
                        span2_min = eng.get("open_loop_2_min_span_s")
                        sep_min = eng.get("open_loop_2_min_payoff_separation_s")
                        p2, y2 = ol2.get("plant_t"), ol2.get("pay_t")
                        if p2 is None or y2 is None or not str(ol2.get("what", "")).strip():
                            R["problems"].append(
                                f"OPEN LOOP 2: a {piece_end:.0f}s piece declares no `open_loop_2` "
                                f"{{plant_t, pay_t, what}}. One loop cannot hold two minutes; the "
                                f"middle needs its own unanswered promise (ENGAGEMENT.md §2.7).")
                        else:
                            if w2 and not (w2[0] <= _t_num(p2) <= w2[1]):
                                R["problems"].append(
                                    f"OPEN LOOP 2: planted at {p2}s, must be planted inside "
                                    f"{w2[0]}-{w2[1]}s. Earlier and it competes with the primary "
                                    f"plant; later and it cannot span far enough to matter.")
                            if span2_min and _t_num(y2) - _t_num(p2) < span2_min:
                                R["problems"].append(
                                    f"OPEN LOOP 2: plant {p2}s to pay {y2}s spans "
                                    f"{_t_num(y2)-_t_num(p2):.1f}s, needs >= {span2_min}s.")
                            if sep_min and abs(_t_num(y2) - _t_num(yt)) < sep_min:
                                R["problems"].append(
                                    f"OPEN LOOP 2: pays at {y2}s, {abs(_t_num(y2)-_t_num(yt)):.1f}s "
                                    f"from the primary payoff at {yt}s. Keep them >= {sep_min}s "
                                    f"apart; two payoffs landing together leave a vacuum behind them.")
                            R["metrics"]["open_loop_2_span_s"] = round(_t_num(y2) - _t_num(p2), 2)
    elif fmt != "object":
        R["problems"].append(f"beats are the OLD prose format ({fmt}); upgrade to timed objects "
                             f"{{t,vo,shows,sfx,means}} so cadence + coverage are checkable (VISUAL_FLOW.md §3)")
    else:
        R["warnings"].append("beats declare no timestamps; cannot check the never-rest gap")

    # ---- required fields (object beats) ----
    if fmt in ("object", "mixed"):
        ch_req = (CFG.get("choreo") or {}).get("required_beat_fields", [])
        if ch_req:
            bad_ch = [b["i"] for b in beats if b["obj"] and not (
                isinstance(b.get("choreo"), dict) and all(str(b["choreo"].get(k, "")).strip() for k in ch_req))]
            if bad_ch:
                R["problems"].append(f"beats {bad_ch} missing a complete `choreo` object "
                                     f"({{{', '.join(ch_req)}}}) — every beat declares its motion "
                                     f"choreography (docs/craft/CHOREOGRAPHY.md §9)")
        missing_sfx = [b["i"] for b in beats if b["obj"] and not str(b["sfx"]).strip()]
        missing_shows = [b["i"] for b in beats if b["obj"] and not str(b["shows"]).strip()]
        missing_vo = [b["i"] for b in beats if b["obj"] and not str(b["vo"]).strip()]
        if missing_shows:
            R["problems"].append(f"beats {missing_shows} have no `shows` (the new on-screen thing)")
        if missing_sfx:
            R["problems"].append(f"beats {missing_sfx} have no `sfx` (every beat names a motivated sound)")
        if missing_vo:
            R["warnings"].append(f"beats {missing_vo} have no `vo` (the phrase they illustrate), coverage unprovable")
        # sfx must be concrete, not "music"
        lazy = [b["i"] for b in beats if b["obj"] and str(b["sfx"]).strip().lower() in ("music", "sound", "sfx")]
        if lazy:
            R["problems"].append(f"beats {lazy} give a vague sfx ('music'/'sound'); name the actual event")

    # ---- VO coverage (say-it-show-it): no un-illustrated speech gap > max ----
    tim_p = d / "audio" / "timing60.json"
    speech_end = None
    if len(timed) >= 2 and tim_p.exists():
        try:
            timing = load_path(tim_p, label="audio timing")
            speech_end = timing.get("speech_end") if isinstance(timing, dict) else None
        except StrictJSONError:
            speech_end = None
        if speech_end:
            starts = sorted(b["t0"] for b in timed)
            covg = [round(starts[i + 1] - starts[i], 2) for i in range(len(starts) - 1)]
            tail = round(speech_end - starts[-1], 2)
            worst = max(covg + [tail]) if covg else tail
            R["metrics"]["speech_end_s"] = speech_end
            R["metrics"]["worst_uncovered_vo_gap_s"] = worst
            if worst > cov["max_uncovered_vo_gap_s"]:
                R["problems"].append(f"coverage: a {worst}s stretch of VO has no beat illustrating it "
                                     f"(> {cov['max_uncovered_vo_gap_s']}s), orphan narration")
        # WPM (ENGAGEMENT.md §6): pace band warning against the measured speech length
        wp = d / "audio" / "words60.json"
        eng = CFG.get("engagement") or {}
        if speech_end and eng.get("wpm_warn") and wp.exists():
            try:
                wdata = load_path(wp, label="aligned words")
                words = wdata.get("words", wdata) if isinstance(wdata, dict) else wdata
                n_words = len(words)
            except (StrictJSONError, TypeError):
                n_words = 0
            if n_words and speech_end > 10:
                wpm = round(n_words / (speech_end / 60.0))
                lo_w, hi_w = eng["wpm_warn"]
                R["metrics"]["vo_wpm"] = wpm
                if not (lo_w <= wpm <= hi_w):
                    R["warnings"].append(f"WPM: VO paces at {wpm} wpm (band {lo_w}-{hi_w}); "
                                         f"target 150-175 for this format (ENGAGEMENT.md §6)")

    # ---- SFX events (sound-paired-to-picture), if the mix emitted them ----
    legacy_p = d / Path(LEGACY_SIDECAR_REL).relative_to("out/dispatch")
    if legacy_p.exists():
        R["problems"].append(
            "legacy audio/sfx_events.json is forbidden; use the single canonical sfx_events.json"
        )
    ev_p = d / sc["events_json"]
    if ev_p.exists() and (ev_p.read_text().strip()):
        canonical_dir = (ROOT / "out" / "dispatch").resolve()
        if d.resolve() == canonical_dir:
            _facts, contract_problems = sidecar_facts(ev_p, root=ROOT)
            R["problems"].extend(contract_problems)
        try:
            ev = load_path(ev_p, label="canonical SFX ledger")
        except StrictJSONError as exc:
            R["problems"].append(str(exc))
            ev = None
        events = ev.get("events") if isinstance(ev, dict) else None
        if not isinstance(events, list):
            R["problems"].append("canonical SFX ledger must be an object with an events list")
            events = []
        R["metrics"]["sfx_events"] = len(events)
        if len(events) < sc["min_events_total"]:
            R["problems"].append(f"sfx_min_total: only {len(events)} sfx events (< {sc['min_events_total']}); "
                                 f"under-sonified")
        shots = sb.get("shots") or []
        if shots and events:
            per = []
            for s in shots:
                a, e = _parse_t(s.get("t"))
                if a is None:
                    continue
                e = e if e is not None else a + 10
                per.append(sum(1 for x in events if a <= _parse_t(x.get("t"))[0] < e))
            if per and min(per) < sc["min_events_per_shot"]:
                R["warnings"].append(f"sfx_per_shot: a shot has {min(per)} sfx events (< {sc['min_events_per_shot']})")
            R["metrics"]["sfx_per_shot"] = per
    else:
        R["metrics"]["sfx_events"] = None
        R["warnings"].append(f"no {sc['events_json']} (mix has not emitted its event list yet)")

    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="out/dispatch")
    ap.add_argument("--report", action="store_true", help="print metrics and never exit non-zero (back-test mode)")
    a = ap.parse_args()
    try:
        R = analyze(a.dir)
    except (StrictJSONError, OSError, TypeError, ValueError) as exc:
        raise SystemExit(f"flow_check: {exc}") from None
    print("=== VISUAL FLOW CHECK ===")
    print(f"beats: {R['n_beats']} ({R['beat_format']} format)   metrics: {json.dumps(R['metrics'])}")
    for p in R["problems"]:
        print(f"  [FAIL] {p}")
    for w in R["warnings"]:
        print(f"  [warn] {w}")
    ok = not R["problems"]
    print("RESULT:", "PASS ✓" if ok else "FAIL ✗")
    if a.report:
        sys.exit(0)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
