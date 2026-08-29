---
name: alaska-dispatch
description: Archived historical engine reference only. Never use it as an operational route; the optimization canary is governed exclusively by CANARY_SAFETY.md and prompts/dispatch_routine.md.
---

# ARCHIVED ENGINE REFERENCE — NOT AN OPERATIONAL ROUTE

This skill documents a retired engine generation. In the optimization canary,
the only operational contract is `prompts/dispatch_routine.md` plus
`CANARY_SAFETY.md`. Do not use the delivery or dependency instructions below to
publish, call Gmail, install rclone, or reach a production repository.

# Alaska.Ai Dispatch — historical production engine

Hand-coded illustration video (PIL + numpy + ffmpeg). No AI-generated imagery — that
is the brand signature. Pairs with `docs/VIDEO_PRODUCTION_STANDARD.md` (craft bible) and
`docs/ROUTINE_SPEC.md` (the routine). Fonts live in `../alaska-ai-brief/fonts/` (committed).

## Files
- `easing.py` — Penner/easings.net curves + closed-form spring (vectorized). Import as `E`.
- `post_grade.py` — standalone cinematic finishing pass (ACES, split-tone, bloom, grain,
  vignette, CA, dither) over a frame; also integrated inline in the renderer.
- `render_v2.py` — the reference renderer: 4:5 scene (glacial water + aurora + hero + parallax
  drift + push-in), finishing, crisp UI, open captions. `test`/range CLI. Currently authored
  at 30s/900 frames for the beluga Dispatch — **adapt per run** (see below).
- `audio_build.py` — edge-tts VO assembly (5 segments → timed vo.wav). New session CA setup
  required before edge-tts (append /etc/ssl/certs/ca-certificates.crt to certifi; export
  SSL_CERT_FILE+SSL_CERT_DIR=/etc/ssl/certs; install edge-tts with pip --break-system-packages).
- `audio_v2.py` — sound design + mix: synth underwater bed + distant whale + sonar, EQ-carved
  + sidechain-ducked VO, two-pass loudnorm to -14 LUFS/-1.5 dBTP, plus the **measurement gate**.
- `render_v3.py` — the CURRENT renderer: 9:16 1080x1920, 1800f/60s. Heroes get craft swim +
  180° motion blur + DoF; continuous life (marine snow + a distant pod + a scrubbing playhead +
  sonar every ~3s) so something moves every <5s; **HUD + captions composited AFTER the grade so
  they stay razor-sharp**; voice-synced kinetic captions; unsharp acuity pass.
- `craft.py` — illustration craft layer: `swim_deform`, `motion_blur`, `depth_blur`, `add_texture`.
- `vo60.py` — 60s edge-tts VO that ALSO captures per-phrase word-timings → `audio/words60.json`
  (captions are built from these, so they always match the voice). Emits `timing60.json`.
- `audio_v3.py` — the 60s mix + single-pass loudnorm + the audio gate (prints PASS).
- `quality_gate.py` — the current B1 objective pre-panel gate. It consumes only
  the schema-v4 delivery manifest, schema-v3 evidence manifest, mastering
  receipt, and sole SFX-v3 ledger; it writes `out/dispatch/quality_report.json`
  and is a required preflight check. Historical frame-folder metrics below are
  archived craft context, not an alternate gate.

## How to use (per run — VARY THE CONCEPT)
1. This engine is a REFERENCE, not a stamp. Each Dispatch must use a different visual
   archetype (see ROUTINE_SPEC Phase 3) and its own scene code. Copy the relevant pieces,
   re-derive the scene/hero for the new story, keep the finishing + audio + caption + gate
   machinery (those are the reusable quality layer).
2. For ~60s: set the frame count to 1800 (NF) and re-time the VO segments, caption windows,
   beat frames, and the music window to 60s. ~130–150 VO words.
3. Render in the BACKGROUND, in parallel chunks (e.g. 3×600), never blocking the run.
4. Historical sequence only. The active B1 order is canonical render -> mix ->
   encode/mastering receipt -> delivery manifest -> `build_evidence.py` ->
   `preflight.py`; judges receive only evidence-manifest-declared artifacts.
5. Historical delivery guidance is retired. In this canary, test media may go
   only to its own media branch and email output is a local HTML preview.

## Dependencies (install in the routine environment setup script; cached)
- ffmpeg, Python 3.11+, `pip install --break-system-packages pillow numpy scipy edge-tts kokoro soundfile`
  (Kokoro = Apache-2.0 publish voice, ~327MB cached; edge-tts = drafts. Voice roster: config/voices.yaml)
- No external upload client is installed or permitted by the canary.
- Fonts are committed under `../alaska-ai-brief/fonts/` — no download needed.

## Locked brand tokens
Deep flag-blue #081838, Pantone gold #FFC72C, aurora cyan-green #1AE5A4 + violet #7B5BFF,
glacier/teal/spruce/slate/snow/coral; Fraunces Black display (opsz 144 wght 900), JetBrains
Mono telemetry; vivid aurora signature; eyebrow "ALASKA.AI / FIELD SIGNAL"; signoff "alaska.ai".

## On-screen copy punctuation (hard rule)
NEVER use an em dash or en dash in ANY on-screen text, label, kinetic caption, or HUD string, ever.
Zero exceptions. Use a middot "·", a comma, a period, parentheses, or a colon as the separator/pause,
and write ranges as "X to Y". (Same rule the LinkedIn caption gate `scripts/caption_check.py` enforces
on the post copy, and `config/brand.yaml` on the voice.)

## THE DIMENSIONAL ENGINE (default for new Dispatches, added 2026-07-10)

`dimensional.py` is the 3D cinematic raymarcher (Taichi CPU JIT, ~0.45-0.7s/frame at FULL
1080x1920 with soft shadows, AO, specular, fog, depth-DOF). Author each shot as a scene file
(SDF `_scene` + `_mat` hooks + a `cam_at(f)` camera move) — see `demo_dimensional.py` (the
'Bristol Bay, Dawn' proof piece) and docs/craft/DIMENSIONAL_CRAFT.md for the doctrine and the
ten look levers. bpy is available for Workbench mesh renders (~2.1s/f, needs libEGL) and Cycles
hero bakes (~28s/f, bake-only). The 2D PIL path remains for HUD/caption/brand composites via
dispatch_core, layered OVER the dimensional render.
