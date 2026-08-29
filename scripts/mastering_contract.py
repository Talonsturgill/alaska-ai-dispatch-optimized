#!/usr/bin/env python3
"""Transactional mastering and decoded-audio lineage for Dispatch deliverables.

``prepare`` invalidates every stale success state and output before it validates
inputs, then writes an immutable intent. ``finalize`` accepts only unchanged
intent inputs and newly produced outputs, measures decoded audio lineage, and
writes the receipt consumed by the delivery manifest. There is deliberately no
standalone observational ``record`` path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import statistics
import struct
import subprocess
import sys
import tempfile
import time
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from render_contract import RenderContractError, probe_render, require_render
from run_guard import load_stamp, stamp_digest
from sfx_contract import AUDIO_REL, SFXContractError, sidecar_facts
from strict_json import StrictJSONError, load_path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_REL = "config/deliverables.json"
INTENT_REL = "out/dispatch/mastering_intent.json"
RECEIPT_REL = "out/dispatch/mastering_receipt.json"
SCHEMA_VERSION = 2
MASTERING_SOURCE_REL = "out/dispatch/dispatch_mastering_source.mp4"
EXPECTED_ARTIFACTS = {
    "vertical_hosted": "out/dispatch/dispatch_master_hosted.mp4",
    "square": "out/dispatch/dispatch_square.mp4",
    "mobile": "out/dispatch/dispatch_master_720.mp4",
    "poster_square": "out/dispatch/poster.png",
    "poster_thumb_vertical": "out/dispatch/poster_thumb_vertical.jpg",
}
AUDIO_ROLES = ("vertical_hosted", "square", "mobile")
MIX_INPUTS = {
    "audio_master": AUDIO_REL,
    "voice": "out/dispatch/audio/vo.wav",
    "aligned_words": "out/dispatch/audio/words.json",
    "music_bed": "out/dispatch/music_bed.wav",
}
SOURCE_TOOLS = (
    "scripts/dispatch_mix.py",
    "scripts/mix_json_contract.py",
    "scripts/sfx_contract.py",
    "scripts/encode_deliverables.sh",
    "scripts/mux_and_verify.sh",
    "scripts/mastering_contract.py",
    "scripts/deliverable_contract.py",
)
CONTROL_PATHS = (
    INTENT_REL,
    RECEIPT_REL,
    "out/dispatch/deliverables_manifest.json",
    "out/dispatch/preflight_receipt.json",
    "out/dispatch/panel_verdict.json",
    "out/dispatch/SHIP_NOW",
    "out/dispatch/SHIP_NOW.json",
    "out/dispatch/delivery_preview_receipt.json",
    "out/dispatch/dispatch-preview.html",
    "out/dispatch/quality_report.json",
    "out/evidence/evidence_manifest.json",
)
OUTPUT_PATHS = (MASTERING_SOURCE_REL, *EXPECTED_ARTIFACTS.values())
COMMAND_PLAN = (
    "mux canonical render/video_mute.mp4 + audio/master.wav -> dispatch_mastering_source.mp4",
    "encode vertical_hosted with libx264 CRF fallback 20,22,24,26 and copied AAC",
    "derive square by crop=1080:1080:0:420 from vertical_hosted with copied AAC",
    "derive mobile by scale=720:1280 from vertical_hosted with copied AAC",
    "extract 1080x1080 PNG poster from square and 540x960 MJPEG poster from vertical_hosted",
    "measure delivered square loudness/true peak, finalize mastering, build/check manifest",
)
AUDIO_SAMPLE_RATE = 16000
AUDIO_BLOCK_SAMPLES = 320
AUDIO_MAX_LAG_BLOCKS = 15
AUDIO_SPECTRAL_WINDOW = 512
AUDIO_SPECTRAL_BINS = 96
AUDIO_SPECTRAL_WINDOWS = 40
AUDIO_MIN_ENVELOPE_CORRELATION = 0.97
AUDIO_MAX_ENVELOPE_NORMALIZED_ERROR = 0.25
AUDIO_MIN_WAVEFORM_CORRELATION = 0.985
AUDIO_MAX_WAVEFORM_NORMALIZED_ERROR = 0.18
AUDIO_MIN_SPECTRAL_SIMILARITY = 0.985
AUDIO_MAX_CEPSTRAL_DISTANCE = 0.30
AUDIO_MAX_DURATION_DELTA_SECONDS = 0.30


class MasteringContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_json(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _inside(base: Path, relative: str, *, label: str, must_exist: bool = True) -> Path:
    if (
        not isinstance(relative, str) or not relative or not relative.isascii()
        or "\\" in relative or PurePosixPath(relative).is_absolute()
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise MasteringContractError(f"{label} must be a canonical repo-relative POSIX path")
    logical = base.joinpath(*relative.split("/"))
    current = base
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise MasteringContractError(f"{label} path may not contain symlinks")
    try:
        logical.resolve(strict=must_exist).relative_to(base)
    except (OSError, ValueError) as exc:
        raise MasteringContractError(f"{label} escapes or cannot be resolved: {exc}") from None
    return logical


def _config(base: Path) -> dict[str, Any]:
    try:
        value = load_path(_inside(base, CONFIG_REL, label="deliverable config"), label="deliverable config")
    except (StrictJSONError, OSError, MasteringContractError) as exc:
        raise MasteringContractError(str(exc)) from None
    if not isinstance(value, dict) or not isinstance(value.get("roles"), dict):
        raise MasteringContractError("deliverable config must contain a roles object")
    if value.get("mastering_receipt_path") != RECEIPT_REL:
        raise MasteringContractError(f"mastering receipt path must be {RECEIPT_REL}")
    if set(value["roles"]) != set(EXPECTED_ARTIFACTS):
        raise MasteringContractError("mastering contract requires exactly the five canonical roles")
    for role, expected_path in EXPECTED_ARTIFACTS.items():
        spec = value["roles"].get(role)
        if not isinstance(spec, dict) or spec.get("path") != expected_path:
            raise MasteringContractError(f"mastering role {role} must use {expected_path}")
    return value


def _file_facts(base: Path, relative: str, *, label: str) -> dict[str, Any]:
    path = _inside(base, relative, label=label)
    if not path.is_file() or path.is_symlink():
        raise MasteringContractError(f"{label} is missing or unsafe")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _external_tool_facts() -> dict[str, Any]:
    facts: dict[str, Any] = {}
    for name in ("ffmpeg", "ffprobe"):
        executable = shutil.which(name)
        if not executable:
            raise MasteringContractError(f"{name} is unavailable for mastering")
        try:
            result = subprocess.run(
                [executable, "-version"], capture_output=True, text=True, timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise MasteringContractError(f"{name} version probe failed: {exc}") from None
        if result.returncode != 0:
            raise MasteringContractError(f"{name} version probe exited {result.returncode}")
        line = (result.stdout or result.stderr).splitlines()
        if not line:
            raise MasteringContractError(f"{name} returned no version")
        facts[name] = {
            "path": str(Path(executable).resolve()),
            "version": line[0].strip(),
        }
    facts["python"] = {"path": str(Path(sys.executable).resolve()), "version": sys.version.split()[0]}
    return facts


def _source_state(
    base: Path,
    *,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> dict[str, Any]:
    _config(base)
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        raise MasteringContractError("run stamp is missing or unreadable")
    try:
        render = require_render(root=base, probe=render_probe)
        sfx, sfx_problems = sidecar_facts(root=base)
    except (RenderContractError, SFXContractError) as exc:
        raise MasteringContractError(str(exc)) from None
    if sfx is None or sfx_problems:
        raise MasteringContractError("canonical SFX ledger is invalid: " + "; ".join(sfx_problems))
    mix_inputs = {
        name: _file_facts(base, relative, label=f"mix input {name}")
        for name, relative in MIX_INPUTS.items()
    }
    if sfx.get("audio") != mix_inputs["audio_master"]:
        raise MasteringContractError("canonical SFX ledger is not bound to audio/master.wav")
    render_receipt = _file_facts(
        base, "out/dispatch/render/render_receipt.json", label="render receipt",
    )
    source_tools = {
        relative: _file_facts(base, relative, label=f"mastering tool {relative}")
        for relative in SOURCE_TOOLS
    }
    return {
        "identity": {
            "run_id": stamp.get("run_id"),
            "run_date": stamp.get("date"),
            "composition": stamp.get("composition"),
            "stamp_sha256": stamp_digest(base),
        },
        "render": {
            "receipt": render_receipt,
            "render_binding_sha256": render.get("render_binding_sha256"),
            "mute": render.get("artifact"),
        },
        "mix_inputs": mix_inputs,
        "sfx": {"path": sfx.get("path"), "sha256": sfx.get("sha256"), "audio": sfx.get("audio")},
        "config": _file_facts(base, CONFIG_REL, label="deliverable config"),
        "source_tools": source_tools,
    }


def _unlink_known(base: Path, relative: str) -> None:
    path = base.joinpath(*relative.split("/"))
    current = base
    for part in relative.split("/")[:-1]:
        current = current / part
        if current.is_symlink():
            raise MasteringContractError(f"refusing stale-path parent symlink at {relative}")
    try:
        if path.is_symlink():
            path.unlink()
            return
        if path.is_dir():
            raise MasteringContractError(f"refusing to clear directory at file path {relative}")
        path.unlink()
    except FileNotFoundError:
        pass


def _clear_stale_state(base: Path) -> None:
    """Clear every safe stale path, even when one malformed path must block prepare."""
    problems = []
    for relative in (*CONTROL_PATHS, *OUTPUT_PATHS):
        try:
            _unlink_known(base, relative)
        except MasteringContractError as exc:
            problems.append(str(exc))
    if problems:
        raise MasteringContractError("; ".join(problems))


def prepare_mastering(
    *,
    root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    tool_probe: Callable[[], dict[str, Any]] = _external_tool_facts,
) -> dict[str, Any]:
    """Invalidate stale success first, then write a closed encode intent."""
    base = Path(root).resolve()
    # This loop intentionally precedes every input check. A missing WAV, invalid
    # CLI argument, or failed mux can never leave yesterday's success controls live.
    _clear_stale_state(base)
    sources = _source_state(base, render_probe=render_probe)
    tools = tool_probe()
    if not isinstance(tools, dict) or set(tools) != {"ffmpeg", "ffprobe", "python"}:
        raise MasteringContractError("mastering external tool facts are not canonical")
    # The encoder cannot start until this function returns. Timestamp only after
    # every source/tool probe so all accepted outputs must follow the final intent.
    prepared_at_ns = time.time_ns()
    intent = {
        "schema_version": SCHEMA_VERSION,
        "phase": "prepared",
        "sources": sources,
        "external_tools": tools,
        "command_plan": list(COMMAND_PLAN),
        "command_plan_sha256": _sha256_json(list(COMMAND_PLAN)),
        "cleared_paths": list((*CONTROL_PATHS, *OUTPUT_PATHS)),
        "prepared_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "prepared_at_ns": prepared_at_ns,
    }
    _atomic_json(_inside(base, INTENT_REL, label="mastering intent", must_exist=False), intent)
    return intent


def _load_intent(base: Path) -> dict[str, Any]:
    try:
        value = load_path(_inside(base, INTENT_REL, label="mastering intent"), label="mastering intent")
    except (StrictJSONError, OSError, MasteringContractError) as exc:
        raise MasteringContractError(str(exc)) from None
    fields = {
        "schema_version", "phase", "sources", "external_tools", "command_plan",
        "command_plan_sha256", "cleared_paths", "prepared_at", "prepared_at_ns",
    }
    if not isinstance(value, dict) or set(value) != fields or value.get("schema_version") != SCHEMA_VERSION:
        raise MasteringContractError("mastering intent fields/schema are not canonical")
    if value.get("phase") != "prepared" or value.get("command_plan") != list(COMMAND_PLAN):
        raise MasteringContractError("mastering intent command plan is not canonical")
    if value.get("command_plan_sha256") != _sha256_json(list(COMMAND_PLAN)):
        raise MasteringContractError("mastering intent command plan digest is invalid")
    if value.get("cleared_paths") != list((*CONTROL_PATHS, *OUTPUT_PATHS)):
        raise MasteringContractError("mastering intent stale-path plan is not canonical")
    if isinstance(value.get("prepared_at_ns"), bool) or not isinstance(value.get("prepared_at_ns"), int):
        raise MasteringContractError("mastering intent prepared_at_ns is invalid")
    return value


@lru_cache(maxsize=1)
def _spectral_basis() -> tuple[tuple[tuple[float, float], ...], ...]:
    return tuple(
        tuple(
            (
                math.cos(2.0 * math.pi * bin_index * sample / AUDIO_SPECTRAL_WINDOW),
                math.sin(2.0 * math.pi * bin_index * sample / AUDIO_SPECTRAL_WINDOW),
            )
            for sample in range(AUDIO_SPECTRAL_WINDOW)
        )
        for bin_index in range(1, AUDIO_SPECTRAL_BINS + 1)
    )


@lru_cache(maxsize=1)
def _hann_window() -> tuple[float, ...]:
    return tuple(
        0.5 - 0.5 * math.cos(2.0 * math.pi * index / (AUDIO_SPECTRAL_WINDOW - 1))
        for index in range(AUDIO_SPECTRAL_WINDOW)
    )


def _spectral_features(samples: list[float]) -> tuple[list[float], list[float]]:
    available = len(samples) - AUDIO_SPECTRAL_WINDOW
    if available < 0:
        raise MasteringContractError("decoded audio is too short for spectral identity")
    if AUDIO_SPECTRAL_WINDOWS == 1:
        offsets = [available // 2]
    else:
        offsets = sorted({
            round(index * available / (AUDIO_SPECTRAL_WINDOWS - 1))
            for index in range(AUDIO_SPECTRAL_WINDOWS)
        })
    profile = [0.0] * AUDIO_SPECTRAL_BINS
    window = _hann_window()
    basis = _spectral_basis()
    for offset in offsets:
        frame = [samples[offset + index] * window[index] for index in range(AUDIO_SPECTRAL_WINDOW)]
        magnitudes = []
        for wave in basis:
            real = sum(value * pair[0] for value, pair in zip(frame, wave))
            imag = sum(value * pair[1] for value, pair in zip(frame, wave))
            magnitudes.append(math.hypot(real, imag))
        total = sum(magnitudes)
        if total <= 1e-12:
            continue
        for index, magnitude in enumerate(magnitudes):
            profile[index] += magnitude / total
    total = sum(profile)
    if total <= 1e-12:
        raise MasteringContractError("decoded audio has no measurable spectral program")
    profile = [value / total for value in profile]
    log_profile = [math.log(max(value, 1e-12)) for value in profile]
    log_mean = statistics.fmean(log_profile)
    centered = [value - log_mean for value in log_profile]
    cepstrum = [
        sum(
            value * math.cos(math.pi * order * (index + 0.5) / AUDIO_SPECTRAL_BINS)
            for index, value in enumerate(centered)
        ) / AUDIO_SPECTRAL_BINS
        for order in range(1, 17)
    ]
    return profile, cepstrum


def _decode_audio_features(path: Path) -> dict[str, Any]:
    before = path.stat()
    before_sha256 = sha256_file(path)
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
                "-ar", str(AUDIO_SAMPLE_RATE), "-f", "s16le", "-",
            ],
            capture_output=True, timeout=180,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise MasteringContractError(f"audio decode failed for {path.name}: {exc}") from None
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise MasteringContractError(
            f"audio decode failed for {path.name}: {detail[-1] if detail else 'no PCM'}"
        )
    pcm = result.stdout
    after = path.stat()
    after_sha256 = sha256_file(path)
    if (
        (before.st_size, before.st_mtime_ns, before_sha256)
        != (after.st_size, after.st_mtime_ns, after_sha256)
    ):
        raise MasteringContractError(f"audio input changed while decoding: {path.name}")
    if len(pcm) % 2:
        raise MasteringContractError(f"audio decode returned odd PCM byte count for {path.name}")
    samples = [item[0] / 32768.0 for item in struct.iter_unpack("<h", pcm)]
    if len(samples) < AUDIO_SAMPLE_RATE:
        raise MasteringContractError(f"decoded audio is under one second for {path.name}")
    envelope = []
    zero_crossing = []
    for offset in range(0, len(samples), AUDIO_BLOCK_SAMPLES):
        block = samples[offset:offset + AUDIO_BLOCK_SAMPLES]
        if len(block) < AUDIO_BLOCK_SAMPLES // 2:
            break
        envelope.append(math.sqrt(sum(value * value for value in block) / len(block)))
        zero_crossing.append(
            sum(1 for left, right in zip(block, block[1:]) if (left < 0) != (right < 0))
            / max(1, len(block) - 1)
        )
    if len(envelope) < 20 or max(envelope) < 1e-5:
        raise MasteringContractError(f"decoded audio has no measurable program for {path.name}")
    spectral_profile, cepstrum = _spectral_features(samples)
    feature_fingerprint = _sha256_json({
        "envelope": [round(value, 8) for value in envelope],
        "zero_crossing": [round(value, 8) for value in zero_crossing],
        "spectral_profile": [round(value, 10) for value in spectral_profile],
        "cepstrum": [round(value, 10) for value in cepstrum],
    })
    return {
        "sample_rate": AUDIO_SAMPLE_RATE,
        "sample_count": len(samples),
        "duration_seconds": round(len(samples) / AUDIO_SAMPLE_RATE, 6),
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
        "container_sha256": after_sha256,
        "feature_fingerprint_sha256": feature_fingerprint,
        "samples": samples,
        "envelope": envelope,
        "spectral_profile": spectral_profile,
        "cepstrum": cepstrum,
    }


def _aac_packet_sha256(path: Path) -> str:
    """Hash exact AAC packet payloads; derivatives use ``-c:a copy`` and must match."""
    before = path.stat()
    before_sha256 = sha256_file(path)
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0",
                "-c:a", "copy", "-f", "adts", "-",
            ],
            capture_output=True, timeout=180,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise MasteringContractError(f"AAC packet extraction failed for {path.name}: {exc}") from None
    if result.returncode != 0 or not result.stdout:
        detail = result.stderr.decode("utf-8", errors="replace").strip().splitlines()
        raise MasteringContractError(
            f"AAC packet extraction failed for {path.name}: "
            f"{detail[-1] if detail else 'no AAC packets'}"
        )
    after = path.stat()
    after_sha256 = sha256_file(path)
    if (
        (before.st_size, before.st_mtime_ns, before_sha256)
        != (after.st_size, after.st_mtime_ns, after_sha256)
    ):
        raise MasteringContractError(f"audio input changed while extracting packets: {path.name}")
    return hashlib.sha256(result.stdout).hexdigest()


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 8:
        return -1.0
    lm, rm = statistics.fmean(left), statistics.fmean(right)
    numerator = sum((a - lm) * (b - rm) for a, b in zip(left, right))
    ld = math.sqrt(sum((a - lm) ** 2 for a in left))
    rd = math.sqrt(sum((b - rm) ** 2 for b in right))
    return numerator / (ld * rd) if ld > 0 and rd > 0 else -1.0


def _normalized_error(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or len(left) < 8:
        return math.inf
    left_mean, right_mean = statistics.fmean(left), statistics.fmean(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    left_rms = math.sqrt(statistics.fmean(value * value for value in left_centered))
    right_rms = math.sqrt(statistics.fmean(value * value for value in right_centered))
    if left_rms <= 1e-10 or right_rms <= 1e-10:
        return math.inf
    return math.sqrt(statistics.fmean(
        (left_value / left_rms - right_value / right_rms) ** 2
        for left_value, right_value in zip(left_centered, right_centered)
    ))


def _aligned_waveforms(
    source: list[float], delivered: list[float], coarse_lag_samples: int,
) -> tuple[list[float], list[float], int]:
    """Refine codec-delay alignment, then return a bounded deterministic sample."""
    best = (-2.0, coarse_lag_samples)
    # Refine within two milliseconds around the envelope-derived coarse lag.
    for lag in range(coarse_lag_samples - 32, coarse_lag_samples + 33):
        source_start = max(0, -lag)
        delivered_start = max(0, lag)
        count = min(len(source) - source_start, len(delivered) - delivered_start, AUDIO_SAMPLE_RATE)
        if count < AUDIO_SAMPLE_RATE // 2:
            continue
        stride = 4
        left = source[source_start:source_start + count:stride]
        right = delivered[delivered_start:delivered_start + count:stride]
        score = _pearson(left, right)
        if score > best[0]:
            best = (score, lag)
    lag = best[1]
    source_start = max(0, -lag)
    delivered_start = max(0, lag)
    count = min(len(source) - source_start, len(delivered) - delivered_start)
    if count < AUDIO_SAMPLE_RATE:
        raise MasteringContractError("decoded audio overlap is under one second after alignment")
    # Bound work for full-length films while sampling the complete timeline.
    stride = max(1, count // 200_000)
    left = source[source_start:source_start + count:stride]
    right = delivered[delivered_start:delivered_start + count:stride]
    common = min(len(left), len(right))
    return left[:common], right[:common], lag


def _compare_audio(source: dict[str, Any], delivered: dict[str, Any]) -> dict[str, Any]:
    best = (-2.0, 0)
    a, b = source["envelope"], delivered["envelope"]
    for lag in range(-AUDIO_MAX_LAG_BLOCKS, AUDIO_MAX_LAG_BLOCKS + 1):
        if lag < 0:
            left, right = a[-lag:], b[:len(a) + lag]
        elif lag > 0:
            left, right = a[:len(a) - lag], b[lag:]
        else:
            left, right = a, b
        count = min(len(left), len(right))
        score = _pearson(left[:count], right[:count])
        if score > best[0]:
            best = (score, lag)
    lag_samples = best[1] * AUDIO_BLOCK_SAMPLES
    waveform_left, waveform_right, lag_samples = _aligned_waveforms(
        source["samples"], delivered["samples"], lag_samples,
    )
    waveform_correlation = _pearson(waveform_left, waveform_right)
    waveform_error = _normalized_error(waveform_left, waveform_right)
    envelope_count = min(len(a), len(b))
    if best[1] < 0:
        envelope_left, envelope_right = a[-best[1]:], b[:len(a) + best[1]]
    elif best[1] > 0:
        envelope_left, envelope_right = a[:len(a) - best[1]], b[best[1]:]
    else:
        envelope_left, envelope_right = a, b
    envelope_count = min(len(envelope_left), len(envelope_right))
    envelope_error = _normalized_error(
        envelope_left[:envelope_count], envelope_right[:envelope_count],
    )
    spectral_similarity = sum(
        math.sqrt(max(0.0, left) * max(0.0, right))
        for left, right in zip(source["spectral_profile"], delivered["spectral_profile"])
    )
    cepstral_numerator = math.sqrt(statistics.fmean(
        (left - right) ** 2
        for left, right in zip(source["cepstrum"], delivered["cepstrum"])
    ))
    cepstral_scale = max(
        1e-9,
        math.sqrt(statistics.fmean(value * value for value in source["cepstrum"])),
    )
    cepstral_distance = cepstral_numerator / cepstral_scale
    duration_delta = abs(source["duration_seconds"] - delivered["duration_seconds"])
    return {
        "envelope_correlation": round(best[0], 9),
        "envelope_normalized_error": round(envelope_error, 9),
        "waveform_correlation": round(waveform_correlation, 9),
        "waveform_normalized_error": round(waveform_error, 9),
        "spectral_similarity": round(spectral_similarity, 9),
        "cepstral_distance": round(cepstral_distance, 9),
        "lag_samples": lag_samples,
        "duration_delta_seconds": round(duration_delta, 6),
    }


def decoded_audio_lineage(base: Path, source_relative: str, roles: dict[str, str]) -> dict[str, Any]:
    source_path = _inside(base, source_relative, label="audio lineage source")
    source = _decode_audio_features(source_path)
    role_facts: dict[str, Any] = {}
    packet_digests: set[str] = set()
    for role, relative in roles.items():
        delivered_path = _inside(base, relative, label=f"audio lineage {role}")
        delivered = _decode_audio_features(delivered_path)
        packet_sha256 = _aac_packet_sha256(delivered_path)
        packet_digests.add(packet_sha256)
        comparison = _compare_audio(source, delivered)
        if comparison["envelope_correlation"] < AUDIO_MIN_ENVELOPE_CORRELATION:
            raise MasteringContractError(
                f"{role} decoded audio envelope correlation is below "
                f"{AUDIO_MIN_ENVELOPE_CORRELATION:.3f}; wrong audio may have been muxed"
            )
        if comparison["envelope_normalized_error"] > AUDIO_MAX_ENVELOPE_NORMALIZED_ERROR:
            raise MasteringContractError(
                f"{role} decoded audio envelope error exceeds "
                f"{AUDIO_MAX_ENVELOPE_NORMALIZED_ERROR:.3f}"
            )
        if (
            comparison["waveform_correlation"] < AUDIO_MIN_WAVEFORM_CORRELATION
            or comparison["waveform_normalized_error"] > AUDIO_MAX_WAVEFORM_NORMALIZED_ERROR
        ):
            raise MasteringContractError(
                f"{role} decoded waveform identity failed (correlation "
                f"{comparison['waveform_correlation']:.6f}, normalized error "
                f"{comparison['waveform_normalized_error']:.6f}); wrong audio may have been muxed"
            )
        if comparison["spectral_similarity"] < AUDIO_MIN_SPECTRAL_SIMILARITY:
            raise MasteringContractError(
                f"{role} decoded spectral identity {comparison['spectral_similarity']:.6f} is below "
                f"{AUDIO_MIN_SPECTRAL_SIMILARITY:.3f}; timbre substitution detected"
            )
        if comparison["cepstral_distance"] > AUDIO_MAX_CEPSTRAL_DISTANCE:
            raise MasteringContractError(
                f"{role} decoded cepstral distance {comparison['cepstral_distance']:.6f} exceeds "
                f"{AUDIO_MAX_CEPSTRAL_DISTANCE:.3f}; timbre substitution detected"
            )
        if comparison["duration_delta_seconds"] > AUDIO_MAX_DURATION_DELTA_SECONDS:
            raise MasteringContractError(
                f"{role} decoded audio duration differs from master by "
                f"{comparison['duration_delta_seconds']:.3f}s"
            )
        role_facts[role] = {
            "path": relative,
            "decoded_pcm_sha256": delivered["pcm_sha256"],
            "container_sha256": delivered["container_sha256"],
            "encoded_audio_packet_sha256": packet_sha256,
            "feature_fingerprint_sha256": delivered["feature_fingerprint_sha256"],
            "sample_count": delivered["sample_count"],
            "duration_seconds": delivered["duration_seconds"],
            **comparison,
        }
    if len(packet_digests) != 1:
        raise MasteringContractError(
            "hosted/square/mobile AAC packet bytes differ; derivatives did not preserve the exact mix"
        )
    return {
        "algorithm": "aligned-pcm-spectral-cepstral-v3",
        "sample_rate": AUDIO_SAMPLE_RATE,
        "block_samples": AUDIO_BLOCK_SAMPLES,
        "spectral": {
            "window_samples": AUDIO_SPECTRAL_WINDOW,
            "bins": AUDIO_SPECTRAL_BINS,
            "windows": AUDIO_SPECTRAL_WINDOWS,
        },
        "aac_packet_sha256": next(iter(packet_digests)),
        "tolerances": {
            "minimum_envelope_correlation": AUDIO_MIN_ENVELOPE_CORRELATION,
            "maximum_envelope_normalized_error": AUDIO_MAX_ENVELOPE_NORMALIZED_ERROR,
            "minimum_waveform_correlation": AUDIO_MIN_WAVEFORM_CORRELATION,
            "maximum_waveform_normalized_error": AUDIO_MAX_WAVEFORM_NORMALIZED_ERROR,
            "minimum_spectral_similarity": AUDIO_MIN_SPECTRAL_SIMILARITY,
            "maximum_cepstral_distance": AUDIO_MAX_CEPSTRAL_DISTANCE,
            "maximum_duration_delta_seconds": AUDIO_MAX_DURATION_DELTA_SECONDS,
            "maximum_lag_blocks": AUDIO_MAX_LAG_BLOCKS,
        },
        "source": {
            "path": source_relative,
            "container_sha256": source["container_sha256"],
            "decoded_pcm_sha256": source["pcm_sha256"],
            "feature_fingerprint_sha256": source["feature_fingerprint_sha256"],
            "sample_count": source["sample_count"],
            "duration_seconds": source["duration_seconds"],
        },
        "roles": role_facts,
    }


def _lineage_problems(value: Any) -> list[str]:
    if not isinstance(value, dict):
        return ["mastering audio lineage must be an object"]
    problems: list[str] = []
    if set(value) != {
        "algorithm", "sample_rate", "block_samples", "spectral", "aac_packet_sha256",
        "tolerances", "source", "roles",
    }:
        problems.append("mastering audio lineage fields are not canonical")
    if value.get("algorithm") != "aligned-pcm-spectral-cepstral-v3":
        problems.append("mastering audio lineage algorithm is not canonical")
    if value.get("sample_rate") != AUDIO_SAMPLE_RATE:
        problems.append("mastering audio lineage sample rate is not canonical")
    if value.get("block_samples") != AUDIO_BLOCK_SAMPLES:
        problems.append("mastering audio lineage block size is not canonical")
    if value.get("spectral") != {
        "window_samples": AUDIO_SPECTRAL_WINDOW,
        "bins": AUDIO_SPECTRAL_BINS,
        "windows": AUDIO_SPECTRAL_WINDOWS,
    }:
        problems.append("mastering audio lineage spectral configuration drifted")
    if value.get("tolerances") != {
        "minimum_envelope_correlation": AUDIO_MIN_ENVELOPE_CORRELATION,
        "maximum_envelope_normalized_error": AUDIO_MAX_ENVELOPE_NORMALIZED_ERROR,
        "minimum_waveform_correlation": AUDIO_MIN_WAVEFORM_CORRELATION,
        "maximum_waveform_normalized_error": AUDIO_MAX_WAVEFORM_NORMALIZED_ERROR,
        "minimum_spectral_similarity": AUDIO_MIN_SPECTRAL_SIMILARITY,
        "maximum_cepstral_distance": AUDIO_MAX_CEPSTRAL_DISTANCE,
        "maximum_duration_delta_seconds": AUDIO_MAX_DURATION_DELTA_SECONDS,
        "maximum_lag_blocks": AUDIO_MAX_LAG_BLOCKS,
    }:
        problems.append("mastering audio lineage tolerances drifted")
    def media_facts_problems(facts: Any, *, label: str, path: str) -> list[str]:
        issues = []
        core = {
            "path", "container_sha256", "decoded_pcm_sha256", "feature_fingerprint_sha256",
            "sample_count", "duration_seconds",
        }
        if not isinstance(facts, dict):
            return [f"{label} is invalid"]
        if not core.issubset(facts):
            issues.append(f"{label} fields are incomplete")
            return issues
        if facts.get("path") != path:
            issues.append(f"{label} path is not canonical")
        for digest_name in ("container_sha256", "decoded_pcm_sha256"):
            digest = facts.get(digest_name)
            if not isinstance(digest, str) or len(digest) != 64 or any(
                char not in "0123456789abcdef" for char in digest
            ):
                issues.append(f"{label} {digest_name} is invalid")
        fingerprint = facts.get("feature_fingerprint_sha256")
        if not isinstance(fingerprint, str) or len(fingerprint) != 64 or any(
            char not in "0123456789abcdef" for char in fingerprint
        ):
            issues.append(f"{label} feature fingerprint digest is invalid")
        samples = facts.get("sample_count")
        duration = facts.get("duration_seconds")
        if isinstance(samples, bool) or not isinstance(samples, int) or samples <= 0:
            issues.append(f"{label} sample count is invalid")
        if (
            isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(float(duration)) or float(duration) <= 0
        ):
            issues.append(f"{label} duration is invalid")
        elif isinstance(samples, int) and not isinstance(samples, bool) and abs(
            float(duration) - samples / AUDIO_SAMPLE_RATE
        ) > 1e-6:
            issues.append(f"{label} duration/sample count disagree")
        return issues

    source = value.get("source")
    if isinstance(source, dict) and set(source) != {
        "path", "container_sha256", "decoded_pcm_sha256", "feature_fingerprint_sha256",
        "sample_count", "duration_seconds",
    }:
        problems.append("mastering audio lineage source fields are not canonical")
    problems.extend(media_facts_problems(source, label="mastering audio lineage source", path=AUDIO_REL))
    roles = value.get("roles")
    if not isinstance(roles, dict) or set(roles) != set(AUDIO_ROLES):
        problems.append("mastering audio lineage must cover exactly the three audio-bearing roles")
    else:
        for role, facts in roles.items():
            expected_fields = {
                "path", "container_sha256", "decoded_pcm_sha256", "encoded_audio_packet_sha256",
                "feature_fingerprint_sha256", "sample_count",
                "duration_seconds", "envelope_correlation", "envelope_normalized_error",
                "waveform_correlation", "waveform_normalized_error", "spectral_similarity",
                "cepstral_distance", "lag_samples", "duration_delta_seconds",
            }
            if not isinstance(facts, dict) or set(facts) != expected_fields:
                problems.append(f"mastering audio lineage {role} fields are not canonical")
                continue
            problems.extend(media_facts_problems(
                facts, label=f"mastering audio lineage {role}", path=EXPECTED_ARTIFACTS[role],
            ))
            packet_digest = facts.get("encoded_audio_packet_sha256")
            if (
                not isinstance(packet_digest, str) or len(packet_digest) != 64
                or any(char not in "0123456789abcdef" for char in packet_digest)
                or packet_digest != value.get("aac_packet_sha256")
            ):
                problems.append(f"mastering audio lineage {role} AAC packet digest fails")
            envelope_correlation = facts.get("envelope_correlation")
            envelope_error = facts.get("envelope_normalized_error")
            waveform_correlation = facts.get("waveform_correlation")
            waveform_error = facts.get("waveform_normalized_error")
            spectral_similarity = facts.get("spectral_similarity")
            cepstral_distance = facts.get("cepstral_distance")
            delta = facts.get("duration_delta_seconds")
            lag = facts.get("lag_samples")
            if (
                isinstance(envelope_correlation, bool)
                or not isinstance(envelope_correlation, (int, float))
                or not math.isfinite(float(envelope_correlation))
                or not AUDIO_MIN_ENVELOPE_CORRELATION <= float(envelope_correlation) <= 1.0
            ):
                problems.append(f"mastering audio lineage {role} envelope correlation fails")
            if (
                isinstance(envelope_error, bool) or not isinstance(envelope_error, (int, float))
                or not math.isfinite(float(envelope_error))
                or not 0 <= float(envelope_error) <= AUDIO_MAX_ENVELOPE_NORMALIZED_ERROR
            ):
                problems.append(f"mastering audio lineage {role} envelope error fails")
            if (
                isinstance(waveform_correlation, bool)
                or not isinstance(waveform_correlation, (int, float))
                or not math.isfinite(float(waveform_correlation))
                or not AUDIO_MIN_WAVEFORM_CORRELATION <= float(waveform_correlation) <= 1.0
            ):
                problems.append(f"mastering audio lineage {role} waveform correlation fails")
            if (
                isinstance(waveform_error, bool) or not isinstance(waveform_error, (int, float))
                or not math.isfinite(float(waveform_error))
                or not 0 <= float(waveform_error) <= AUDIO_MAX_WAVEFORM_NORMALIZED_ERROR
            ):
                problems.append(f"mastering audio lineage {role} waveform error fails")
            if (
                isinstance(spectral_similarity, bool)
                or not isinstance(spectral_similarity, (int, float))
                or not math.isfinite(float(spectral_similarity))
                or not AUDIO_MIN_SPECTRAL_SIMILARITY <= float(spectral_similarity) <= 1.0 + 1e-9
            ):
                problems.append(f"mastering audio lineage {role} spectral similarity fails")
            if (
                isinstance(cepstral_distance, bool)
                or not isinstance(cepstral_distance, (int, float))
                or not math.isfinite(float(cepstral_distance))
                or not 0 <= float(cepstral_distance) <= AUDIO_MAX_CEPSTRAL_DISTANCE
            ):
                problems.append(f"mastering audio lineage {role} cepstral distance fails")
            if (
                isinstance(delta, bool) or not isinstance(delta, (int, float))
                or not math.isfinite(float(delta)) or not 0 <= float(delta) <= AUDIO_MAX_DURATION_DELTA_SECONDS
            ):
                problems.append(f"mastering audio lineage {role} duration fails")
            if (
                isinstance(lag, bool) or not isinstance(lag, int)
                or abs(lag) > AUDIO_MAX_LAG_BLOCKS * AUDIO_BLOCK_SAMPLES + 32
            ):
                problems.append(f"mastering audio lineage {role} lag fails")
            if (
                isinstance(source, dict) and isinstance(source.get("duration_seconds"), (int, float))
                and isinstance(facts.get("duration_seconds"), (int, float))
                and isinstance(delta, (int, float)) and not isinstance(delta, bool)
                and abs(
                    float(delta)
                    - abs(float(source["duration_seconds"]) - float(facts["duration_seconds"]))
                ) > 1e-6
            ):
                problems.append(f"mastering audio lineage {role} duration delta is inconsistent")
    common_packet = value.get("aac_packet_sha256")
    if (
        not isinstance(common_packet, str) or len(common_packet) != 64
        or any(char not in "0123456789abcdef" for char in common_packet)
    ):
        problems.append("mastering audio lineage common AAC packet digest is invalid")
    return problems


def finalize_mastering(
    *,
    root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    tool_probe: Callable[[], dict[str, Any]] = _external_tool_facts,
    audio_probe: Callable[[Path, str, dict[str, str]], dict[str, Any]] = decoded_audio_lineage,
) -> dict[str, Any]:
    base = Path(root).resolve()
    intent = _load_intent(base)
    current_sources = _source_state(base, render_probe=render_probe)
    if intent.get("sources") != current_sources:
        raise MasteringContractError("mastering inputs changed after prepare intent")
    current_tools = tool_probe()
    if intent.get("external_tools") != current_tools:
        raise MasteringContractError("mastering tool paths/versions changed after prepare intent")
    prepared_at_ns = intent["prepared_at_ns"]
    artifacts: dict[str, Any] = {}
    for role, relative in EXPECTED_ARTIFACTS.items():
        path = _inside(base, relative, label=f"deliverable {role}")
        if path.stat().st_mtime_ns <= prepared_at_ns:
            raise MasteringContractError(f"deliverable {role} does not postdate mastering prepare")
        artifacts[role] = _file_facts(base, relative, label=f"deliverable {role}")
    internal_path = _inside(base, MASTERING_SOURCE_REL, label="internal mastering source")
    if internal_path.stat().st_mtime_ns <= prepared_at_ns:
        raise MasteringContractError("internal mastering source does not postdate mastering prepare")
    internal = _file_facts(base, MASTERING_SOURCE_REL, label="internal mastering source")
    lineage = audio_probe(
        base, AUDIO_REL, {role: EXPECTED_ARTIFACTS[role] for role in AUDIO_ROLES},
    )
    problems = _lineage_problems(lineage)
    if problems:
        raise MasteringContractError("; ".join(problems))
    intent_path = _inside(base, INTENT_REL, label="mastering intent")
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "identity": current_sources["identity"],
        "intent": {
            "path": INTENT_REL,
            "bytes": intent_path.stat().st_size,
            "sha256": sha256_file(intent_path),
            "prepared_at_ns": prepared_at_ns,
            "command_plan_sha256": intent["command_plan_sha256"],
        },
        "sources": current_sources,
        "external_tools": current_tools,
        "internal_mastering_source": internal,
        "audio_lineage": lineage,
        "artifacts": artifacts,
        "finalized_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_json(_inside(base, RECEIPT_REL, label="mastering receipt", must_exist=False), receipt)
    return receipt


def validate_mastering(
    *,
    root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    audio_probe: Callable[[Path, str, dict[str, str]], dict[str, Any]] = decoded_audio_lineage,
) -> tuple[dict[str, Any] | None, list[str]]:
    base = Path(root).resolve()
    try:
        target = _inside(base, RECEIPT_REL, label="mastering receipt")
        receipt = load_path(target, label="mastering receipt")
        intent = _load_intent(base)
    except (MasteringContractError, StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(receipt, dict):
        return None, ["mastering receipt must be a JSON object"]
    fields = {
        "schema_version", "identity", "intent", "sources", "external_tools",
        "internal_mastering_source", "audio_lineage", "artifacts", "finalized_at",
    }
    problems: list[str] = []
    if set(receipt) != fields or receipt.get("schema_version") != SCHEMA_VERSION:
        problems.append("mastering receipt fields/schema are not canonical")
    try:
        current_sources = _source_state(base, render_probe=render_probe)
    except MasteringContractError as exc:
        return receipt, problems + [str(exc)]
    if intent.get("sources") != current_sources or receipt.get("sources") != current_sources:
        problems.append("mastering source inputs changed after prepare/finalize")
    intent_path = _inside(base, INTENT_REL, label="mastering intent")
    expected_intent = {
        "path": INTENT_REL,
        "bytes": intent_path.stat().st_size,
        "sha256": sha256_file(intent_path),
        "prepared_at_ns": intent["prepared_at_ns"],
        "command_plan_sha256": intent["command_plan_sha256"],
    }
    if receipt.get("intent") != expected_intent:
        problems.append("mastering receipt intent binding changed")
    if receipt.get("identity") != current_sources["identity"]:
        problems.append("mastering receipt identity changed")
    try:
        internal = _file_facts(base, MASTERING_SOURCE_REL, label="internal mastering source")
        artifacts = {
            role: _file_facts(base, relative, label=f"deliverable {role}")
            for role, relative in EXPECTED_ARTIFACTS.items()
        }
    except MasteringContractError as exc:
        return receipt, problems + [str(exc)]
    if receipt.get("internal_mastering_source") != internal:
        problems.append("internal mastering source changed after finalize")
    if receipt.get("artifacts") != artifacts:
        problems.append("mastering deliverable bytes changed after finalize")
    problems.extend(_lineage_problems(receipt.get("audio_lineage")))
    try:
        current_lineage = audio_probe(
            base, AUDIO_REL, {role: EXPECTED_ARTIFACTS[role] for role in AUDIO_ROLES},
        )
    except MasteringContractError as exc:
        problems.append(f"mastering decoded audio lineage cannot be revalidated: {exc}")
    else:
        current_lineage_problems = _lineage_problems(current_lineage)
        problems.extend(current_lineage_problems)
        if not current_lineage_problems and receipt.get("audio_lineage") != current_lineage:
            problems.append("mastering decoded audio/AAC packet lineage changed after finalize")
    if receipt.get("external_tools") != intent.get("external_tools"):
        problems.append("mastering receipt tool versions differ from prepare intent")
    if not isinstance(receipt.get("finalized_at"), str) or not receipt["finalized_at"]:
        problems.append("mastering receipt finalized_at is missing")
    return receipt, problems


def require_mastering(
    *,
    root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    audio_probe: Callable[[Path, str, dict[str, str]], dict[str, Any]] = decoded_audio_lineage,
) -> dict[str, Any]:
    receipt, problems = validate_mastering(
        root=root, render_probe=render_probe, audio_probe=audio_probe,
    )
    if receipt is None or problems:
        raise MasteringContractError("; ".join(problems or ["mastering receipt is unavailable"]))
    return receipt


def mastering_binding(
    *,
    root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    audio_probe: Callable[[Path, str, dict[str, str]], dict[str, Any]] = decoded_audio_lineage,
) -> dict[str, Any]:
    base = Path(root).resolve()
    receipt = require_mastering(root=base, render_probe=render_probe, audio_probe=audio_probe)
    target = _inside(base, RECEIPT_REL, label="mastering receipt")
    return {
        "path": RECEIPT_REL,
        "bytes": target.stat().st_size,
        "sha256": sha256_file(target),
        "identity": receipt["identity"],
        "intent": receipt["intent"],
        "audio_master": receipt["sources"]["mix_inputs"]["audio_master"],
        "mix_inputs": receipt["sources"]["mix_inputs"],
        "sfx": receipt["sources"]["sfx"],
        "audio_lineage": receipt["audio_lineage"],
        "artifacts": receipt["artifacts"],
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("prepare", "finalize", "check"))
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            intent = prepare_mastering()
            print(f"mastering_contract: prepared {intent['command_plan_sha256'][:16]}")
        elif args.command == "finalize":
            receipt = finalize_mastering()
            print(
                "mastering_contract: finalized decoded audio lineage "
                f"{receipt['intent']['sha256'][:16]}"
            )
        else:
            receipt = require_mastering()
            print(
                "mastering_contract: PASS "
                f"{receipt['sources']['mix_inputs']['audio_master']['sha256'][:16]}"
            )
        return 0
    except (MasteringContractError, StrictJSONError, OSError, ValueError, TypeError) as exc:
        print(f"mastering_contract: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
