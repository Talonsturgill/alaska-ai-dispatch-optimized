#!/usr/bin/env python3
"""Build and validate the exact run-scoped panel evidence pack.

Evidence is terminal only when this manifest was built from an empty directory,
every expected artifact is owned by a named producer, and all producer sources,
parameters, delivery bytes, schemas, and artifact hashes still match.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

from deliverable_contract import (
    DeliverableContractError,
    contract_digest,
    require_manifest,
    sha256_file,
)
from strict_json import StrictJSONError, canonical_bytes, load_path
from run_guard import stamp_digest

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_REL = "out/evidence"
MANIFEST_REL = "out/evidence/evidence_manifest.json"
SCHEMA_VERSION = 3
GENERATOR_VERSION = "dispatch-evidence-v3"
PRODUCER_SPECS = {
    "visual": ("scripts/build_evidence.py", GENERATOR_VERSION),
    "audio_report": ("scripts/audio_report.py", "dispatch-audio-report-v3"),
    "audio_card": ("scripts/audio_evidence.py", "dispatch-audio-evidence-v3"),
}
PRODUCER_INPUTS = {
    "visual": (
        "out/dispatch/dispatch_master_hosted.mp4",
        "out/dispatch/vo_lines.json",
        "out/dispatch/episode_props.json",
    ),
    "audio_report": (
        "out/dispatch/dispatch_square.mp4",
        "out/dispatch/dispatch_master_hosted.mp4",
        "out/dispatch/audio/words.json",
    ),
    "audio_card": (
        "out/dispatch/audio/master.wav",
        "out/dispatch/audio/vo.wav",
        "out/dispatch/sfx_events.json",
    ),
}
ALLOWED_EXTENSIONS = {".jpg", ".png", ".json"}


class EvidenceContractError(RuntimeError):
    pass


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


def _logical_directory(base: Path) -> Path:
    current = base
    for part in EVIDENCE_REL.split("/"):
        current = current / part
        if current.is_symlink():
            raise EvidenceContractError("evidence directory path may not contain symlinks")
    logical = base.joinpath(*EVIDENCE_REL.split("/"))
    try:
        logical.resolve(strict=False).relative_to(base)
    except (OSError, ValueError):
        raise EvidenceContractError("evidence directory escapes the repository") from None
    return logical


def recreate_evidence_directory(*, root: str | Path = ROOT) -> Path:
    """Remove only the validated evidence directory, then recreate it empty."""
    base = Path(root).resolve()
    directory = _logical_directory(base)
    if directory.exists():
        if not directory.is_dir():
            raise EvidenceContractError("evidence path exists but is not a directory")
        shutil.rmtree(directory)
    directory.mkdir(parents=True, exist_ok=False)
    return directory


def _evidence_directory(base: Path) -> Path:
    directory = _logical_directory(base)
    if not directory.is_dir():
        raise EvidenceContractError("evidence directory is missing or unsafe")
    return directory


def _canonical_relative(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.startswith(EVIDENCE_REL + "/")
        or "\\" in value
        or value.startswith("/")
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise EvidenceContractError(f"{label} must be a canonical evidence-relative POSIX path")
    if Path(value).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise EvidenceContractError(f"{label} has an unsupported evidence extension")
    return value


def _canonical_input(value: Any, *, label: str) -> str:
    if (
        not isinstance(value, str) or not value or not value.isascii()
        or "\\" in value or PurePosixPath(value).is_absolute()
        or any(part in {"", ".", ".."} for part in value.split("/"))
        or PurePosixPath(value).as_posix() != value
    ):
        raise EvidenceContractError(f"{label} must be a canonical repo-relative POSIX path")
    return value


def _input_facts(
    base: Path, relative: str, *, authority: dict[str, Any], label: str,
) -> dict[str, Any]:
    relative = _canonical_input(relative, label=label)
    logical = base.joinpath(*relative.split("/"))
    current = base
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise EvidenceContractError(f"{label} path may not contain symlinks")
    try:
        logical.resolve(strict=True).relative_to(base)
    except (OSError, ValueError) as exc:
        raise EvidenceContractError(f"{label} is missing or escapes the repository: {exc}") from None
    if not logical.is_file() or logical.is_symlink():
        raise EvidenceContractError(f"{label} is missing or unsafe")
    return {
        "path": relative,
        "bytes": logical.stat().st_size,
        "sha256": sha256_file(logical),
        "authority": authority,
    }


def _input_authority(
    relative: str, delivery: dict[str, Any], *, root: Path,
) -> dict[str, Any]:
    delivery_digest = contract_digest(delivery)
    for role, entry in delivery.get("artifacts", {}).items():
        if isinstance(entry, dict) and entry.get("path") == relative:
            return {"type": "delivery_manifest", "digest": delivery_digest, "role": role}
    mastering = delivery.get("mastering")
    if relative in {"out/dispatch/audio/master.wav", "out/dispatch/sfx_events.json"}:
        if not isinstance(mastering, dict):
            raise EvidenceContractError("delivery manifest has no mastering lineage")
        return {
            "type": "mastering_receipt",
            "path": mastering.get("path"),
            "sha256": mastering.get("sha256"),
        }
    return {"type": "run_stamp", "sha256": stamp_digest(root)}


def _evidence_files(base: Path) -> list[Path]:
    directory = _evidence_directory(base)
    files: list[Path] = []
    for candidate in directory.iterdir():
        if candidate.name == "evidence_manifest.json":
            continue
        if candidate.is_symlink():
            raise EvidenceContractError(f"evidence may not be a symlink: {candidate.name}")
        if candidate.is_dir():
            raise EvidenceContractError(f"evidence directory may not contain subdirectories: {candidate.name}")
        if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise EvidenceContractError(f"unexpected evidence file type: {candidate.name}")
        if candidate.stat().st_size <= 0:
            raise EvidenceContractError(f"evidence artifact is empty: {candidate.name}")
        files.append(candidate)
    if not files:
        raise EvidenceContractError("evidence directory contains no review artifacts")
    if not any(path.suffix.lower() in (".jpg", ".png") for path in files):
        raise EvidenceContractError("evidence pack contains no review image")
    return sorted(files, key=lambda path: path.name)


def _artifact_map(base: Path) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    for path in _evidence_files(base):
        relative = path.resolve().relative_to(base).as_posix()
        artifacts[relative] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    return artifacts


def _schema_problems(base: Path, artifacts: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for relative in artifacts:
        if not relative.endswith(".json"):
            continue
        try:
            value = load_path(base.joinpath(*relative.split("/")), label=relative)
        except StrictJSONError as exc:
            problems.append(str(exc))
            continue
        if not isinstance(value, dict):
            problems.append(f"{relative} must be a JSON object")
            continue
        if relative.endswith("/caption_cues.json"):
            if set(value) != {"note", "count", "cues"} or not isinstance(value.get("cues"), list):
                problems.append("caption_cues.json schema is not canonical")
            elif isinstance(value.get("count"), bool) or value.get("count") != len(value["cues"]):
                problems.append("caption_cues.json count does not match cues")
            else:
                for index, cue in enumerate(value["cues"]):
                    if not isinstance(cue, dict) or set(cue) != {"start", "end", "text"}:
                        problems.append(f"caption_cues.json cue {index} schema is not canonical")
                        break
        elif relative.endswith("/motion.json"):
            if set(value) != {"note", "strips"} or not isinstance(value.get("strips"), dict):
                problems.append("motion.json schema is not canonical")
        elif relative.endswith("/audio_report.json"):
            required = {
                "measured_on", "also_covers_master", "master_measured", "master_identity",
                "tool", "delivered_i", "delivered_tp", "delivered_lra", "targets", "pass",
                "vo_gaps_ge_0_35s", "vo_gaps_ge_0_50s", "vo_silence_in_gaps_s",
                "last_word_ends_s", "longest_gaps", "diagnosis",
            }
            if set(value) != required:
                problems.append("audio_report.json schema is not canonical")
    return problems


def _producer_map(
    base: Path, producers: dict[str, Any], artifacts: dict[str, Any],
    delivery: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    problems: list[str] = []
    if not isinstance(producers, dict) or set(producers) != set(PRODUCER_SPECS):
        return {}, ["evidence producers must exactly name visual, audio_report, and audio_card"]
    normalized: dict[str, Any] = {}
    owned: list[str] = []
    for name, (source_rel, version) in PRODUCER_SPECS.items():
        supplied = producers.get(name)
        if not isinstance(supplied, dict) or set(supplied) != {"parameters", "outputs"}:
            problems.append(f"evidence producer {name} fields are not canonical")
            continue
        parameters = supplied.get("parameters")
        outputs = supplied.get("outputs")
        try:
            canonical_bytes(parameters)
        except StrictJSONError as exc:
            problems.append(f"evidence producer {name} parameters are invalid: {exc}")
        if not isinstance(parameters, dict) or not parameters:
            problems.append(f"evidence producer {name} parameters must be a non-empty object")
        if not isinstance(outputs, list) or not outputs:
            problems.append(f"evidence producer {name} outputs must be a non-empty list")
            outputs = []
        clean_outputs: list[str] = []
        for output in outputs:
            try:
                clean = _canonical_relative(output, label=f"evidence producer {name} output")
            except EvidenceContractError as exc:
                problems.append(str(exc))
                continue
            clean_outputs.append(clean)
            owned.append(clean)
        source = base.joinpath(*source_rel.split("/"))
        if not source.is_file() or source.is_symlink():
            problems.append(f"evidence producer {name} source is missing or unsafe")
            source_hash = None
        else:
            source_hash = sha256_file(source)
        inputs: dict[str, Any] = {}
        for input_rel in PRODUCER_INPUTS[name]:
            try:
                inputs[input_rel] = _input_facts(
                    base,
                    input_rel,
                    authority=_input_authority(input_rel, delivery, root=base),
                    label=f"evidence producer {name} input",
                )
            except EvidenceContractError as exc:
                problems.append(str(exc))
        normalized[name] = {
            "path": source_rel,
            "version": version,
            "sha256": source_hash,
            "parameters": parameters,
            "inputs": inputs,
            "outputs": clean_outputs,
        }
    if len(owned) != len(set(owned)):
        problems.append("evidence artifacts may be owned by exactly one producer")
    if set(owned) != set(artifacts):
        problems.append("evidence producer outputs do not exactly cover the artifact set")
    return normalized, problems


def build_evidence_manifest(
    *, root: str | Path = ROOT, producers: dict[str, Any], expected_artifacts: list[str],
    delivery_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = Path(root).resolve()
    try:
        delivery = delivery_manifest or require_manifest(root=base)
        artifacts = _artifact_map(base)
    except (DeliverableContractError, EvidenceContractError) as exc:
        raise EvidenceContractError(str(exc)) from None
    try:
        expected = [_canonical_relative(value, label="expected evidence artifact") for value in expected_artifacts]
    except (TypeError, EvidenceContractError) as exc:
        raise EvidenceContractError(str(exc)) from None
    if expected != sorted(set(expected)):
        raise EvidenceContractError("expected evidence artifacts must be sorted and unique")
    if set(expected) != set(artifacts):
        raise EvidenceContractError("evidence directory does not exactly match the expected artifact set")
    problems = _schema_problems(base, artifacts)
    normalized_producers, producer_problems = _producer_map(base, producers, artifacts, delivery)
    problems.extend(producer_problems)
    if problems:
        raise EvidenceContractError("; ".join(problems))
    vertical = delivery["artifacts"]["vertical_hosted"]
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "run_id": delivery["identity"]["run_id"],
            "run_date": delivery["identity"]["date"],
            "composition": delivery["identity"]["composition"],
        },
        "delivery_manifest_digest": contract_digest(delivery),
        "vertical_hosted": {
            "path": vertical["path"], "bytes": vertical["bytes"], "sha256": vertical["sha256"],
        },
        "producers": normalized_producers,
        "expected_artifacts": expected,
        "artifacts": artifacts,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_json(base.joinpath(*MANIFEST_REL.split("/")), manifest)
    return manifest


def validate_evidence_manifest(
    *, root: str | Path = ROOT, delivery_manifest: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    base = Path(root).resolve()
    problems: list[str] = []
    try:
        delivery = delivery_manifest or require_manifest(root=base)
        raw = load_path(base.joinpath(*MANIFEST_REL.split("/")), label="evidence manifest")
    except (DeliverableContractError, StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(raw, dict):
        return None, ["evidence manifest must be a JSON object"]
    fields = {
        "schema_version", "identity", "delivery_manifest_digest", "vertical_hosted",
        "producers", "expected_artifacts", "artifacts", "generated_at",
    }
    if set(raw) != fields or raw.get("schema_version") != SCHEMA_VERSION:
        problems.append("evidence manifest fields/schema are not canonical")
    expected_identity = {
        "run_id": delivery["identity"]["run_id"],
        "run_date": delivery["identity"]["date"],
        "composition": delivery["identity"]["composition"],
    }
    if raw.get("identity") != expected_identity:
        problems.append("evidence manifest identity does not match the delivery manifest")
    if raw.get("delivery_manifest_digest") != contract_digest(delivery):
        problems.append("evidence manifest delivery digest does not match current deliverables")
    vertical = delivery["artifacts"]["vertical_hosted"]
    expected_vertical = {
        "path": vertical["path"], "bytes": vertical["bytes"], "sha256": vertical["sha256"],
    }
    if raw.get("vertical_hosted") != expected_vertical:
        problems.append("evidence manifest vertical_hosted facts do not match exact delivered bytes")
    try:
        current_artifacts = _artifact_map(base)
    except EvidenceContractError as exc:
        problems.append(str(exc))
        current_artifacts = {}
    artifacts = raw.get("artifacts")
    expected = raw.get("expected_artifacts")
    if not isinstance(artifacts, dict):
        problems.append("evidence manifest artifacts must be an object")
        artifacts = {}
    if not isinstance(expected, list) or expected != sorted(set(expected)):
        problems.append("evidence manifest expected_artifacts must be a sorted unique list")
        expected = []
    if set(expected) != set(artifacts) or artifacts != current_artifacts:
        problems.append("evidence artifact set/bytes/hashes changed after manifest creation")
    problems.extend(_schema_problems(base, current_artifacts))
    producers = raw.get("producers")
    if not isinstance(producers, dict) or set(producers) != set(PRODUCER_SPECS):
        problems.append("evidence manifest producers are not canonical")
    else:
        owned: list[str] = []
        for name, (path_rel, version) in PRODUCER_SPECS.items():
            entry = producers.get(name)
            fields = {"path", "version", "sha256", "parameters", "inputs", "outputs"}
            if not isinstance(entry, dict) or set(entry) != fields:
                problems.append(f"evidence producer {name} receipt fields are not canonical")
                continue
            source = base.joinpath(*path_rel.split("/"))
            if entry.get("path") != path_rel or entry.get("version") != version:
                problems.append(f"evidence producer {name} identity changed")
            if not source.is_file() or source.is_symlink() or entry.get("sha256") != sha256_file(source):
                problems.append(f"evidence producer {name} source hash changed")
            try:
                canonical_bytes(entry.get("parameters"))
            except StrictJSONError as exc:
                problems.append(f"evidence producer {name} parameters are invalid: {exc}")
            if not isinstance(entry.get("parameters"), dict) or not entry["parameters"]:
                problems.append(f"evidence producer {name} parameters are missing")
            outputs = entry.get("outputs")
            if not isinstance(outputs, list) or not outputs:
                problems.append(f"evidence producer {name} outputs are missing")
            else:
                owned.extend(outputs)
        if isinstance(producers, dict):
            supplied = {
                name: {
                    "parameters": producers.get(name, {}).get("parameters"),
                    "outputs": producers.get(name, {}).get("outputs"),
                }
                for name in PRODUCER_SPECS
            }
            current, current_problems = _producer_map(base, supplied, artifacts, delivery)
            problems.extend(current_problems)
            if current != producers:
                problems.append(
                    "evidence producer source/input bytes, hashes, authority, version, or parameters changed"
                )
        if len(owned) != len(set(owned)) or set(owned) != set(artifacts):
            problems.append("evidence producer outputs do not exactly own the artifact set")
    if not isinstance(raw.get("generated_at"), str) or not raw["generated_at"]:
        problems.append("evidence manifest generated_at is missing")
    return raw, problems


def require_evidence_manifest(
    *, root: str | Path = ROOT, delivery_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest, problems = validate_evidence_manifest(root=root, delivery_manifest=delivery_manifest)
    if manifest is None or problems:
        raise EvidenceContractError("; ".join(problems or ["evidence manifest is unavailable"]))
    return manifest


def evidence_manifest_sha(*, root: str | Path = ROOT) -> str:
    return sha256_file(Path(root).resolve().joinpath(*MANIFEST_REL.split("/")))
