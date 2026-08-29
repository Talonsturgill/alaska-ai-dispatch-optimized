#!/usr/bin/env bash
# Alaska.Ai Dispatch routine — environment setup (idempotent, cached by the routine env).
# Point the routine's Environment > "Setup script" at:   bash scripts/setup_env.sh
# Installs everything the engine needs. Fonts are committed in the repo (no download).
set -uo pipefail

# ffmpeg
command -v ffmpeg >/dev/null 2>&1 || { apt-get update -qq && apt-get install -y -qq ffmpeg; }

# python deps (only install if missing)
python3 -c "import PIL,numpy,scipy,edge_tts,soundfile,yaml" >/dev/null 2>&1 \
  || pip install --break-system-packages -q pillow numpy scipy edge-tts soundfile pyyaml
# librosa + faster_whisper: the Gemini VO pipeline's soundcheck (scripts/vo_soundcheck.py
# pitch-variance gate) imports librosa, and scripts/vo_synth_gemini.py's whole-file forced
# alignment imports faster_whisper, both under the SYSTEM python3 (not the voice venv). They
# were silently missing from this env, so vo_synth_gemini crashed at the soundcheck stage on
# 2026-07-20 AFTER paying for 4 Gemini takes. Same silent-missing-dep class as the 07-18
# faster_whisper/resemblyzer gap. Idempotent top-up so it never recurs:
python3 -c "import librosa, faster_whisper" >/dev/null 2>&1 \
  || pip install --break-system-packages -q librosa faster_whisper \
  || echo "setup_env: WARN librosa/faster_whisper install failed (Gemini VO soundcheck/align will break)"
# num2words: vo_soundcheck.py's WER canonicalizer converts digit tokens (heard: "4,700",
# "50") to their spelled-out word form (reference script: "four thousand seven hundred",
# "fifty") so a correct read doesn't get penalized for spelling numbers differently than
# it says them. THIRD instance of the silent-missing-dep class (07-18 faster_whisper/
# resemblyzer, 07-20 librosa/faster_whisper, now this): with num2words absent,
# _canon_token's ImportError is swallowed by a bare except and every digit token is left
# unconverted, silently inflating WER on every number-heavy script (2026-07-22: 3 straight
# real takes scored 0.081-0.144, just over/near the 0.08 ceiling, purely from this, not
# from an actual bad read). Standard pip install builds a docopt wheel that fails under
# this env's patched setuptools (same class of failure as the voice-venv chatterbox
# install below); --no-deps skips it since num2words' core `num2words()` function does
# not need docopt at import or call time (only its bundled CLI script does).
python3 -c "import num2words" >/dev/null 2>&1 \
  || pip install --break-system-packages -q --no-deps num2words \
  || echo "setup_env: WARN num2words install failed (WER canonicalizer will under-count digit tokens, inflating WER on number-heavy scripts)"
# DIMENSIONAL ENGINE (3D): taichi is the primary renderer (CPU JIT, ~0.45s/frame @1080x1920)
python3 -c "import taichi" >/dev/null 2>&1 \
  || pip install --break-system-packages -q taichi
# bpy = Blender-as-module for Workbench mesh renders + Cycles hero bakes (large wheel, best-effort)
python3 -c "import bpy" >/dev/null 2>&1 \
  || pip install --break-system-packages -q bpy || true
# software-GL for bpy Workbench headless (llvmpipe); best-effort
ldconfig -p 2>/dev/null | grep -q libEGL.so.1 \
  || { apt-get update -qq && apt-get install -y -qq libegl1 libgl1 libgles2 libgl1-mesa-dri; } || true
# kokoro (preset-voice fallback, Apache-2.0) — larger; install if missing
python3 -c "import kokoro" >/dev/null 2>&1 \
  || pip install --break-system-packages -q kokoro || true

# ---- OWNER-VOICE CLONE STACK (publish primary; see config/voices.yaml) ----
# Chatterbox (MIT, the engine Voicebox bundles) in a DEDICATED VENV because the
# Debian-patched system setuptools breaks the antlr4 sdist build (install_layout
# AttributeError) under the system python. Run VO builds with $VOICE_PY.
# Proven on this env 2026-07-14: torch 2.6.0+cpu, weights pull from HF fine.
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_DIR/.venv-voice"
VOICE_PY="$VENV_DIR/bin/python"
if [ ! -x "$VOICE_PY" ] || ! "$VOICE_PY" -c "import chatterbox" >/dev/null 2>&1; then
  python3 -m venv "$VENV_DIR" \
    && "$VENV_DIR/bin/pip" install -q -U pip wheel \
    && "$VENV_DIR/bin/pip" install -q "setuptools<81" \
    && "$VENV_DIR/bin/pip" install -q chatterbox-tts edge-tts soundfile scipy numpy \
         faster_whisper resemblyzer \
         --extra-index-url https://download.pytorch.org/whl/cpu \
    || echo "setup_env: WARN voice venv install failed (kokoro/edge fallback will be used)"
fi
# faster_whisper (vo_qc.py's WER gate) and resemblyzer (its speaker-similarity gate)
# are separate packages from chatterbox-tts and were silently missing from this
# install line until 2026-07-18 (the venv "existed" per the chatterbox import check,
# so subsequent runs never re-installed them). Idempotent top-up on every run:
"$VOICE_PY" -c "import faster_whisper, resemblyzer" >/dev/null 2>&1 \
  || "$VENV_DIR/bin/pip" install -q faster_whisper resemblyzer \
  || echo "setup_env: WARN faster_whisper/resemblyzer install failed (vo_qc.py QC gates will break)"
# setuptools<81 matters: resemble-perth (chatterbox's watermarker) imports
# pkg_resources, removed in newer setuptools -> PerthImplicitWatermarker=None crash.
"$VOICE_PY" -c "import setuptools,pkg_resources" >/dev/null 2>&1 \
  || "$VENV_DIR/bin/pip" install -q "setuptools<81" || true

# edge-tts TLS: append the system + agent-proxy CA bundles to certifi (idempotent)
# — for BOTH pythons (system + voice venv); aiohttp/hf_hub read certifi, not SSL_CERT_FILE.
for PYBIN in python3 "$VOICE_PY"; do
  [ -x "$(command -v "$PYBIN" 2>/dev/null || echo "$PYBIN")" ] || continue
  "$PYBIN" - <<'PY' || true
import certifi, os
for src in ("/etc/ssl/certs/ca-certificates.crt", "/root/.ccr/ca-bundle.crt"):
    if os.path.exists(src):
        cur=open(certifi.where(),"rb").read(); add=open(src,"rb").read()
        if add[:160] not in cur: open(certifi.where(),"ab").write(b"\n"+add)
print("certifi CA ok:", certifi.where())
PY
done
echo "setup_env: ready"

# Canary commits are pushed deliberately after the guard and test suite passes.
# Do not install post-commit hooks or automatic push behavior in this lab.

# NODE / REMOTION deps for the video engine. The fresh clone has no node_modules; without this
# the render step fails with "remotion: not found" on every fresh container. Idempotent.
if [ -f video-engine/package.json ]; then
  if [ ! -x video-engine/node_modules/.bin/remotion ]; then
    ( cd video-engine && npm install --no-audit --no-fund ) \
      && echo "setup_env: video-engine node deps installed" \
      || echo "setup_env: WARN npm install failed (render will break)"
  fi
fi
