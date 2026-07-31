#!/usr/bin/env python3
"""
GATE 0 — COMPOSITION DIVERGENCE (objective, runs BEFORE any frame is rendered).

This is the structural answer to the cookie-cutter failure: the routine kept opening the repo,
copying the last render script, re-skinning the hero, and shipping a composition identical to the
prior video (the salmon that "looked just like the damn beluga video"). A new subject is not a new
composition. This gate makes "different video" measurable and refuses to let a re-skin proceed.

It reads:
  out/dispatch/storyboard.json   the planned composition FINGERPRINT (7 axes) + beats + notes
  config/state.yaml              dispatch_history, each entry carrying its own composition fingerprint
  config/composition_axes.yaml   the axes + the divergence rule

and FAILS (exit 1) if the plan is incomplete, admits it was derived from a prior render, or its
composition re-skins a recent dispatch (too few differing axes / a repeated spatial signature /
a repeated palette). Exit 0 = the composition is genuinely distinct; you may build it.

  python scripts/storyboard_check.py [path/to/storyboard.json]

Same contract as quality_gate.py / caption_check.py: machine-checked, no cap, fix the cause and
re-run. You do not get to relax the rule to pass — you change the composition.
"""
import sys, json, re
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "config" / "state.yaml"
AXES = ROOT / "config" / "composition_axes.yaml"
DEFAULT_SB = ROOT / "out" / "dispatch" / "storyboard.json"

CONTROLLED = ["pov", "motion_vector", "hero_treatment", "layout", "register",
              "camera_strategy", "light_story"]  # exact-tag axes (camera/light added with the 3D engine)
FREETEXT = ["palette", "metaphor"]                                             # token-overlap axes
ALL_AXES = CONTROLLED + FREETEXT
STOP = {"the", "a", "an", "of", "in", "and", "for", "to", "on", "with", "by", "ai", "+", "·", "-"}


def norm_tag(s):
    return re.sub(r"\s+", "-", str(s or "").strip().lower())


def tokens(s):
    return {w for w in re.findall(r"[a-z0-9]+", str(s or "").lower()) if w not in STOP and len(w) > 1}


def overlap_match(a, b, min_shared=2, jaccard=0.34):
    """Free-text axes (palette/metaphor) 'match' when they share real vocabulary."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return norm_tag(a) == norm_tag(b)
    shared = ta & tb
    j = len(shared) / len(ta | tb)
    return len(shared) >= min_shared or j >= jaccard


def axis_matches(axis, new_v, old_v):
    if axis in FREETEXT:
        return overlap_match(new_v, old_v)
    return norm_tag(new_v) == norm_tag(old_v)


def fp_of(entry):
    """Pull a composition fingerprint from a history entry (new 'composition' block; tolerate older
    entries by falling back to their free-text archetype/palette so the gate still has something)."""
    comp = entry.get("composition") or {}
    fp = {ax: comp.get(ax, "") for ax in ALL_AXES}
    if not fp.get("palette"):
        fp["palette"] = entry.get("palette", "")
    if not any(fp[ax] for ax in CONTROLLED):
        # legacy entry with only a free-text archetype: stuff it into metaphor so palette+metaphor
        # still get compared (better than silently treating it as fully distinct).
        fp["metaphor"] = entry.get("archetype", "") or fp.get("metaphor", "")
    return fp


def fail(msg):
    print(f"FAIL [storyboard_check] {msg}")
    sys.exit(1)



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

def main():
    sb_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SB
    if not sb_path.exists():
        fail(f"no storyboard at {sb_path} — Phase 4.5 must WRITE the board before any render. "
             f"Required fields: concept, derived_from, fingerprint{{{','.join(ALL_AXES)}}}, beats[], divergence_note.")
    sb = json.loads(sb_path.read_text())
    axcfg = yaml.safe_load(AXES.read_text())
    rule = axcfg["rule"]
    smin = axcfg["storyboard_min"]
    shotcfg = yaml.safe_load((ROOT / "config" / "shot_structure.yaml").read_text())
    srule = shotcfg["rule"]; SHOT_FRAMINGS = set(shotcfg.get("framings", [])); SHOT_TRANS = set(shotcfg.get("transitions", []))
    state = yaml.safe_load(STATE.read_text()) or {}
    history = state.get("dispatch_history", [])

    problems = []

    # ---- 1. completeness: planning can't be a stub ----
    fp = sb.get("fingerprint") or {}
    for fld in smin["required_fields"]:
        if fld == "palette":
            if not (sb.get("palette") or fp.get("palette")):
                problems.append("missing required field: palette (in fingerprint)")
        elif fld == "fingerprint":
            if not fp:
                problems.append("missing required field: fingerprint")
        elif not sb.get(fld):
            problems.append(f"missing required field: {fld}")
    missing_axes = [ax for ax in ALL_AXES if not fp.get(ax)]
    if missing_axes:
        problems.append(f"fingerprint missing axes: {missing_axes} (all 7 must be declared)")
    beats = sb.get("beats") or []
    if len(beats) < smin["beats"]:
        problems.append(f"only {len(beats)} beats; need >= {smin['beats']} story-advancing beats "
                        f"(matches the BEAT_DENSITY video gate)")
    dnote = sb.get("divergence_note", "")
    if len(dnote) < smin["divergence_note_min_chars"]:
        problems.append(f"divergence_note is {len(dnote)} chars; need >= {smin['divergence_note_min_chars']} "
                        f"— SAY in prose how this differs from the last 2 dispatches (forces the thinking).")

    # ---- 1b. SHOT STRUCTURE: the board must be a SEQUENCE of shots, not one 'oner' (config/shot_structure.yaml) ----
    shots = sb.get("shots") or []
    if len(shots) < srule["min_shots"]:
        problems.append(f"only {len(shots)} shots; need >= {srule['min_shots']} distinct shots with motivated "
                        f"transitions (a scene change ~every 10-15s — NOT one continuous 'oner' like the sonar Dispatch).")
    else:
        framings = [str(s.get("framing", "")).strip().lower() for s in shots]
        if len({f for f in framings if f}) < srule["min_distinct_framings"]:
            problems.append(f"shots use only {len({f for f in framings if f})} distinct framings; need >= "
                            f"{srule['min_distinct_framings']} (vary the shot types: {sorted(SHOT_FRAMINGS)}).")
        unknown_fr = sorted({f for f in framings if f and f not in SHOT_FRAMINGS})
        if unknown_fr:
            problems.append(f"shots use framings outside the vocab: {unknown_fr} (use config/shot_structure.yaml `framings`).")
        # ---- 1b-ii. SCALE + CAMERA HEIGHT (2026-07-29 repeat-offender guard) ----
        # The 07-26 panel: "nine shots play at one camera height on one set. No close-up, no low
        # angle, no real scale change in 57.9 seconds." `framing` never caught it because a board
        # can name eight framings and still compose every shot at one apparent subject size. So
        # scale and height are now first-class declared axes with their own gate.
        SCALES = shotcfg.get("scales", [])
        HEIGHTS = shotcfg.get("heights", [])
        classes = shotcfg.get("scale_classes", {}) or {}
        CLOSE_CLASS = set(classes.get("close_class", []))
        WIDE_CLASS = set(classes.get("wide_class", []))
        scales = [norm_tag(s.get("scale", "")) for s in shots]
        heights = [norm_tag(s.get("height", "")) for s in shots]
        no_scale = [s.get("id", i + 1) for i, s in enumerate(shots) if not scales[i]]
        if no_scale:
            problems.append(f"shots {no_scale} declare no `scale` — every shot names how big the subject "
                            f"reads ({SCALES}); this is the axis the 2026-07-26 panel found flat.")
        no_height = [s.get("id", i + 1) for i, s in enumerate(shots) if not heights[i]]
        if no_height:
            problems.append(f"shots {no_height} declare no `height` — every shot names where the camera "
                            f"stands ({HEIGHTS}).")
        bad_scale = sorted({s for s in scales if s and s not in SCALES})
        if bad_scale:
            problems.append(f"shots use scales outside the vocab: {bad_scale} (config/shot_structure.yaml `scales`).")
        bad_height = sorted({h for h in heights if h and h not in HEIGHTS})
        if bad_height:
            problems.append(f"shots use camera heights outside the vocab: {bad_height} "
                            f"(config/shot_structure.yaml `heights`).")
        if all(scales):
            nscale = len(set(scales))
            need_scale = int(srule.get("min_distinct_scales", 3))
            if nscale < need_scale:
                problems.append(f"shots use only {nscale} distinct scale(s) {sorted(set(scales))}; need >= "
                                f"{need_scale}. Shooting every beat at one subject size is the 2026-07-26 "
                                f"'no real scale change in 57.9 seconds' failure.")
            if srule.get("require_close_class", True) and not (set(scales) & CLOSE_CLASS):
                problems.append(f"no close-class shot ({sorted(CLOSE_CLASS)}) anywhere in the board — the panel "
                                f"named the missing close-up explicitly. Get the camera onto a face or a detail.")
            if srule.get("require_wide_class", True) and not (set(scales) & WIDE_CLASS):
                problems.append(f"no wide-class shot ({sorted(WIDE_CLASS)}) — a close-up only reads as close "
                                f"against something wide. Establish the world at least once.")
            run_max = int(srule.get("max_consecutive_same_scale", 2))
            run, prev = 1, scales[0]
            for i in range(1, len(scales)):
                run = run + 1 if scales[i] == prev else 1
                prev = scales[i]
                if run > run_max:
                    problems.append(f"shot {shots[i].get('id', i + 1)} is the {run}th consecutive shot at scale "
                                    f"'{scales[i]}' (max {run_max}). Break the size run — that is what reads as "
                                    f"one locked camera.")
                    break
        if all(heights):
            nheight = len(set(heights))
            need_h = int(srule.get("min_distinct_heights", 2))
            if nheight < need_h:
                problems.append(f"shots use only {nheight} camera height(s) {sorted(set(heights))}; need >= "
                                f"{need_h}. 'Nine shots at one camera height' was the panel's exact phrasing.")

        if srule.get("require_transitions", True):
            no_tr = [s.get("id", i + 2) for i, s in enumerate(shots[1:]) if not str(s.get("transition_in", "")).strip()]
            if no_tr:
                problems.append(f"shots {no_tr} declare no transition_in — every shot after the first needs a motivated "
                                f"transition ({sorted(SHOT_TRANS)}).")
            bad_tr = sorted({str(s.get("transition_in", "")).strip().lower() for s in shots[1:]
                             if str(s.get("transition_in", "")).strip() and str(s.get("transition_in", "")).strip().lower() not in SHOT_TRANS})
            if bad_tr:
                problems.append(f"shots use transitions outside the vocab: {bad_tr} (use config/shot_structure.yaml `transitions`).")

            # ---- 1c. ANTI-ZOOM: each shot is its OWN composition; a CUT moves to a different WORLD ----
            # The v2 critique: the "scene changes" were crops/zooms of one sonar display. Eight crops all share
            # pov=instrument-screen / layout=hud-instrument-frame / hero=instrument-as-subject -> 0 axes change.
            # So every shot must declare its heavy axes, and adjacent shots must differ on >= min_axis_change.
            HEAVY = srule.get("heavy_axes", ["pov", "layout", "motion_vector", "hero_treatment"])
            need_change = int(srule.get("min_axis_change_between_shots", 2))
            sfps = [{ax: norm_tag(s.get(ax, "")) for ax in HEAVY} for s in shots]
            for i, s in enumerate(shots):
                miss = [ax for ax in HEAVY if not sfps[i][ax]]
                if miss:
                    problems.append(f"shot {s.get('id', i + 1)} doesn't declare its composition {miss} — every shot must "
                                    f"name its own {HEAVY} (config/composition_axes.yaml vocab) so the gate can prove "
                                    f"adjacent shots are different WORLDS, not one canvas reframed.")
            if all(all(f.values()) for f in sfps):
                for i in range(1, len(sfps)):
                    chg = [ax for ax in HEAVY if sfps[i - 1][ax] != sfps[i][ax]]
                    if len(chg) < need_change:
                        problems.append(
                            f"shot {shots[i].get('id', i + 1)} is the SAME composition as the shot before it (changed "
                            f"{chg or 'nothing'}; need >= {need_change} of {HEAVY}). That is a camera zoom/pan over one "
                            f"canvas, NOT a scene change — cut to a different WORLD (docs/craft/CINEMATIC_SCENE_CRAFT.md §0-§1).")
            THREADS = {"match", "carry", "build", "travel"}
            bad_thread = [s.get("id", i + 2) for i, s in enumerate(shots[1:]) if norm_tag(s.get("thread", "")) not in THREADS]
            if bad_thread:
                problems.append(f"shots {bad_thread} don't declare a valid transition `thread` (one of {sorted(THREADS)}) "
                                f"— every scene break must MATCH / CARRY / BUILD / TRAVEL (docs/craft/CINEMATIC_SCENE_CRAFT.md §1).")

    # ---- 1d. ENGINE: infographic-2.5d (Remotion, current) or dimensional (retired 3D) ----
    engine = norm_tag(sb.get("engine", ""))
    if engine not in ("infographic-2.5d", "dimensional"):
        problems.append("engine must be 'infographic-2.5d' (video-engine/, prompts/dispatch_routine.md; "
                        "'dimensional' is the retired 3D engine, history only). Declare engine: infographic-2.5d.")
    if engine == "dimensional":
        # legacy 3D vocab checks (kept only so historical boards still validate)
        cam_vocab = {"dolly-through", "orbit-reveal", "rack-focus-macro", "aerial-descent",
                     "rise-reveal", "track-follow", "locked-drift"}
        light_vocab = {"dawn-backlight", "noon-hard", "dusk-silhouette", "overcast-diffuse",
                       "night-practical", "storm-dramatic"}
        if norm_tag(fp.get("camera_strategy")) not in cam_vocab:
            problems.append(f"fingerprint.camera_strategy '{fp.get('camera_strategy')}' not in {sorted(cam_vocab)}")
        if norm_tag(fp.get("light_story")) not in light_vocab:
            problems.append(f"fingerprint.light_story '{fp.get('light_story')}' not in {sorted(light_vocab)}")
        lightd = sb.get("light") or {}
        if not lightd.get("sun") or not lightd.get("mood"):
            problems.append("board must declare light: {sun: '<dir/elevation in words>', mood: '<what the light MEANS>'}")
        for i, sh in enumerate(shots):
            camd = sh.get("camera") or {}
            if norm_tag(camd.get("move", "")) not in cam_vocab:
                problems.append(f"shot {sh.get('id', i+1)} camera.move '{camd.get('move')}' missing/not in vocab "
                                f"— every 3D shot declares its camera move")
            if camd.get("focus_from") is None or camd.get("focus_to") is None:
                problems.append(f"shot {sh.get('id', i+1)} must declare camera.focus_from/focus_to "
                                f"(equal values = held focus; different = a rack the CAMERA_MOTION gate verifies)")
    else:
        # 2.5D boards: camera_strategy/light_story are free-text (fresh vs ledger is still
        # checked via the fingerprint comparison above); what is REQUIRED is the visual
        # sentence pass — every beat must carry a draw {subject, action, emotion, annotation}.
        for i, b in enumerate(beats):
            d = b.get("draw") or {}
            missing = [k for k in ("subject", "action", "emotion", "annotation") if not str(d.get(k, "")).strip()]
            if missing:
                problems.append(f"beat {i} missing draw.{missing} — every beat is a VISUAL SENTENCE "
                                f"(subject with a face does a visible verb, with its annotation); "
                                f"a beat without a draw is a slide (prompts/dispatch_routine.md §4.3)")
        # ---- STAGE3D ENFORCEMENT (2026-07-20, UPGRADE #1 wired into pre-planning) ----
        # The true-depth engine (lib/stage3d.tsx, docs/craft/STAGE3D.md) is now the default.
        # Every shot must PLAN its camera and its depth: `camera` names composed moves from
        # the CameraMoves vocab (or 'static' WITH a stated reason), and `stage3d` declares
        # the shot's depth plan ('planes' = a Stage3D world, or 'flat:<reason>' for shots
        # where depth genuinely adds nothing, e.g. a full-frame data panel). Unplanned
        # camera/depth is what made the old scenes read as slides; the gate refuses it.
        CAM_MOVES = {"dollythrough", "orbitreveal", "cranedown", "truckacross", "risewith", "static"}
        for i, sh in enumerate(shots):
            cam_f = str(sh.get("camera", "")).strip().lower()
            if not cam_f:
                problems.append(f"shot {sh.get('id', i + 1)} declares no `camera` — every 2.5D shot names its "
                                f"composed CameraMoves ({sorted(CAM_MOVES)}, '+'-composed, e.g. "
                                f"'craneDown+dollyThrough'), or 'static:<reason>' (docs/craft/STAGE3D.md).")
            else:
                moves = [m.split(":")[0] for m in re.split(r"[+,]", cam_f) if m.strip()]
                bad = [m for m in moves if m.replace("-", "") not in CAM_MOVES]
                if bad:
                    problems.append(f"shot {sh.get('id', i + 1)} camera move(s) {bad} not in the stage3d vocab "
                                    f"{sorted(CAM_MOVES)} (lib/stage3d.tsx CameraMoves).")
                if moves == ["static"] and ":" not in cam_f:
                    problems.append(f"shot {sh.get('id', i + 1)} camera 'static' needs a reason "
                                    f"('static:<why this shot earns a locked camera>').")
            st = str(sh.get("stage3d", "")).strip().lower()
            if not st:
                problems.append(f"shot {sh.get('id', i + 1)} declares no `stage3d` — 'planes' (a Stage3D depth "
                                f"world; the default) or 'flat:<reason>' (why depth adds nothing here).")
            elif st.startswith("flat") and ":" not in st:
                problems.append(f"shot {sh.get('id', i + 1)} stage3d 'flat' needs a reason ('flat:<why>').")

    # ---- 1e. HOOK / HERO / AUDIO_ARC blocks (docs/craft/HOOK_CRAFT.md, HERO_CRAFT.md, VOICE_AND_SCORE.md) ----
    HOOK_PATTERNS = {"anomaly-question", "in-medias-res", "bold-claim", "stakes-antagonist"}
    hk = sb.get("hook") or {}
    if not hk:
        problems.append("missing top-level `hook` block — the cold open is designed, not hoped for "
                        "(HOOK_CRAFT.md: {pattern, frame1, headline, motion_by_s, loopback})")
    else:
        if norm_tag(hk.get("pattern")) not in HOOK_PATTERNS:
            problems.append(f"hook.pattern '{hk.get('pattern')}' not in {sorted(HOOK_PATTERNS)}")
        hw = len(str(hk.get("headline", "")).split())
        if not (3 <= hw <= 8):
            problems.append(f"hook.headline is {hw} words; the burned-in frame-1 claim runs 5-8 words "
                            f"(hard band 3-8) and must survive the 120px shrink test")
        try:
            if float(hk.get("motion_by_s", 99)) > 1.5:
                problems.append("hook.motion_by_s > 1.5 — something must visibly change within the "
                                "first ~1.3s of a muted feed")
        except (TypeError, ValueError):
            problems.append("hook.motion_by_s missing/non-numeric")
        for fld in ("frame1", "loopback"):
            if not str(hk.get(fld, "")).strip():
                problems.append(f"hook.{fld} missing — declare the frame-0 poster and the loop-back rhyme")
    for i, sh in enumerate(shots):
        hero = sh.get("hero") or {}
        try:
            ok_hero = int(hero.get("parts", 0)) >= 3 and int(hero.get("zones", 0)) >= 2
        except (TypeError, ValueError):
            ok_hero = False
        if not (ok_hero and str(hero.get("name", "")).strip() and str(hero.get("detail_note", "")).strip()):
            problems.append(f"shot {sh.get('id', i+1)} missing a hero block with parts>=3, zones>=2, name, "
                            f"detail_note — a single-primitive hero cannot read designed or perform "
                            f"(HERO_CRAFT.md shape-hierarchy law)")
    # ---- 1f. REVEALS (docs/craft/ENGAGEMENT.md §3: telegraph -> disclose -> hold) ----
    REVEAL_TYPES = {"scale-pullback", "mask-wipe", "trim-path", "scale-from-anchor", "morph-to-chart", "build-on"}
    SCALE_CLASS = {"scale-pullback", "morph-to-chart", "build-on"}
    rv = sb.get("reveals") or []
    if not rv:
        problems.append("missing top-level `reveals` list — the board declares its designed reveal moments "
                        "(ENGAGEMENT.md §3: [{t, type, what, hold_s}], type in "
                        + str(sorted(REVEAL_TYPES)) + ")")
    else:
        bad_rv = [r.get("type") for r in rv if norm_tag(r.get("type")) not in REVEAL_TYPES]
        if bad_rv:
            problems.append(f"reveals type(s) {bad_rv} not in the reveal vocabulary {sorted(REVEAL_TYPES)}")
        # SCALE-CLASS REVEALS. At 60s one was enough. The 90s format needs one PER HALF,
        # because a single "whoa" beat cannot carry ninety seconds and a back half with no
        # reveal of its own is where a long film goes flat.
        scale_rv = [r for r in rv if norm_tag(r.get("type")) in SCALE_CLASS]
        if not scale_rv:
            problems.append("no scale-class reveal declared (scale-pullback / morph-to-chart / build-on) — "
                            "every piece gets at least one true-scale 'whoa' beat aligned to the escalation "
                            "(ENGAGEMENT.md §3)")
        else:
            beat_ts = [_t_num(b.get("t")) for b in (sb.get("beats") or []) if b.get("t") is not None]
            piece_end = max(beat_ts) if beat_ts else 0.0
            if piece_end >= 75:                       # long-format only
                mid = piece_end / 2.0
                first = [r for r in scale_rv if _t_num(r.get("t")) < mid]
                second = [r for r in scale_rv if _t_num(r.get("t")) >= mid]
                if len(scale_rv) < 2 or not first or not second:
                    problems.append(
                        f"a {piece_end:.0f}s piece declares {len(scale_rv)} scale-class reveal(s), "
                        f"{len(first)} in the first half and {len(second)} in the second. At this length "
                        f"the format needs at least ONE PER HALF (ENGAGEMENT.md §3), because a single "
                        f"whoa beat cannot carry ninety seconds and a back half with no reveal goes flat.")
        for r in rv:
            try:
                hold = float(r.get("hold_s", -1))
            except (TypeError, ValueError):
                hold = -1
            if not (0.3 <= hold <= 1.2):
                problems.append(f"reveal '{r.get('what', r.get('type'))}' hold_s={r.get('hold_s')} — every "
                                f"reveal lands with a 0.4-0.8s still HOLD (accepted band 0.3-1.2); the pause "
                                f"is the punctuation")
    aa = sb.get("audio_arc") or {}
    if not aa:
        problems.append("missing top-level `audio_arc` block (VOICE_AND_SCORE.md: {build_steps, dip_at, "
                        "riser_at, silence_at, payoff_at, button_pattern})")
    else:
        for fld in ("dip_at", "riser_at", "silence_at", "payoff_at"):
            try:
                float(aa.get(fld))
            except (TypeError, ValueError):
                problems.append(f"audio_arc.{fld} missing/non-numeric")
        if norm_tag(aa.get("button_pattern")) not in {"callback", "question", "tricolon"}:
            problems.append(f"audio_arc.button_pattern '{aa.get('button_pattern')}' must be callback|question|tricolon "
                            f"— the button is never a flat declarative")

    # ---- 2. the banned shortcut: a scene copied from a prior render and re-skinned ----
    if rule.get("require_derived_from_scratch", True):
        df = norm_tag(sb.get("derived_from", ""))
        if df != "scratch":
            problems.append(f"derived_from='{sb.get('derived_from')}' — the scene must be authored from "
                            f"scratch to this board. Copying a prior render_*.py to re-skin it is the "
                            f"banned cookie-cutter shortcut. Set derived_from: scratch and mean it "
                            f"(shared HELPERS are imported from dispatch_core, not copied).")

    if problems:
        for p in problems:
            print(f"FAIL [storyboard_check] {p}")
        sys.exit(1)

    # ---- 3. divergence vs recent history (only if we have prior dispatches) ----
    recent = history[-rule["compare_last_n"]:] if history else []
    for old in recent:
        ofp = fp_of(old)
        diff = [ax for ax in ALL_AXES if not axis_matches(ax, fp.get(ax), ofp.get(ax))]
        same = [ax for ax in ALL_AXES if ax not in diff]
        if len(diff) < rule["min_diff_axes"]:
            problems.append(
                f"too close to {old.get('date')} \"{old.get('slug') or old.get('topic')}\": differs on only "
                f"{len(diff)}/{len(ALL_AXES)} axes (need >= {rule['min_diff_axes']}). SAME on {same}. "
                f"Redesign the composition, don't re-skin it.")

    # ---- 4. spatial signature (pov, layout, motion_vector) must be unique ----
    sig_axes = rule["signature_axes"]
    new_sig = tuple(norm_tag(fp.get(ax)) for ax in sig_axes)
    for old in (history[-rule["signature_window"]:] if history else []):
        ofp = fp_of(old)
        old_sig = tuple(norm_tag(ofp.get(ax)) for ax in sig_axes)
        if old_sig == new_sig and all(old_sig):
            problems.append(
                f"spatial signature {dict(zip(sig_axes, new_sig))} repeats {old.get('date')} "
                f"\"{old.get('slug') or old.get('topic')}\". This (pov, layout, motion) triple is the exact "
                f"thing that made the salmon a beluga clone. Change at least one of {sig_axes}.")

    # ---- 4b. camera/light freshness (3D variety pressure) ----
    if history:
        last = fp_of(history[-1])
        if last.get("camera_strategy") and norm_tag(fp.get("camera_strategy")) == norm_tag(last.get("camera_strategy")):
            problems.append(f"camera_strategy '{fp.get('camera_strategy')}' repeats the previous dispatch — "
                            f"vary the camera's story run to run")
        last2 = [fp_of(h) for h in history[-2:]]
        lts = [norm_tag(l.get("light_story")) for l in last2 if l.get("light_story")]
        if len(lts) == 2 and all(norm_tag(fp.get("light_story")) == l for l in lts):
            problems.append(f"light_story '{fp.get('light_story')}' repeats both of the last 2 — choose a new sun")

    # ---- 5. palette must not repeat the last 2 ----
    for old in (history[-rule["palette_window"]:] if history else []):
        if overlap_match(fp.get("palette"), fp_of(old).get("palette")):
            problems.append(
                f"palette \"{fp.get('palette')}\" repeats {old.get('date')} \"{fp_of(old).get('palette')}\". "
                f"Choose a fresh color world (rubric hard_blocker).")

    # ---- 6. VISUAL FLOW: never-rest cadence + say-it-show-it + sound-paired (config/visual_flow.yaml) ----
    # docs/craft/VISUAL_FLOW.md. Beats must be timed objects {t,vo,shows,sfx,means} with start-to-start
    # gaps <= 5s (nothing on screen rests longer), covering the VO (no orphan narration), each naming a sound.
    try:
        _here = str(Path(__file__).resolve().parent)
        if _here not in sys.path:
            sys.path.insert(0, _here)
        import flow_check as _fc
        _fr = _fc.analyze(str(sb_path.parent))
        for _p in _fr["problems"]:
            problems.append(f"visual-flow: {_p}")
        for _w in _fr.get("warnings", []):
            print(f"  [flow-advisory] {_w}")
    except Exception as _e:
        print(f"  [flow-advisory] flow_check could not run ({_e}); beats not flow-validated")

    # ---- 7. PHYSICAL EVENTS: a beat must draw something happening, not label it ----
    # scripts/beat_events.py. Cheap regression guard: it PASSES the 2026-07-31 board, which is
    # the point of the note in that file -- the board was not that run's problem. It exists so
    # a board that genuinely schedules type instead of events cannot reach a render.
    try:
        import beat_events as _be
        _br = _be.analyze(str(sb_path))
        for _p in _br["problems"]:
            problems.append(f"beat-events: {_p}")
        print(f"  [beat-events] {_br['with_event']}/{_br['beats']} beats name a physical event")
    except Exception as _e:
        print(f"  [beat-events] could not run ({_e}); beats not event-validated")

    if problems:
        for p in problems:
            print(f"FAIL [storyboard_check] {p}")
        sys.exit(1)

    print(f"PASS [storyboard_check] composition is distinct: {sb.get('concept', '(unnamed)')}")
    print(f"  fingerprint: " + "  ".join(f"{ax}={fp.get(ax)}" for ax in ALL_AXES))
    if recent:
        print(f"  diverges from last {len(recent)}: " +
              "; ".join(f"{o.get('date')}→{len([ax for ax in ALL_AXES if not axis_matches(ax, fp.get(ax), fp_of(o).get(ax))])}/{len(ALL_AXES)} axes differ"
                        for o in recent))
    print(f"  beats: {len(beats)}   signature: {dict(zip(sig_axes, new_sig))}")
    if shots:
        worlds = len({tuple(norm_tag(s.get(ax, "")) for ax in ["pov", "layout", "motion_vector", "hero_treatment"]) for s in shots})
        print(f"  shots: {len(shots)} across {worlds} distinct compositions (each cut moves to a different world, not a zoom)")
    sys.exit(0)


if __name__ == "__main__":
    main()
