#!/usr/bin/env python3
"""Hash-bind every panel evidence artifact to the delivered vertical bytes."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from deliverable_contract import (
    DeliverableContractError,
    contract_digest,
    require_manifest,
    sha256_file,
)
from strict_json import StrictJSONError, canonical_bytes, load_path

ROOT = Path(__file__).resolve().parent.parent
EVIDENCE_REL = "out/evidence"
MANIFEST_REL = "out/evidence/evidence_manifest.json"
SCHEMA_VERSION = 1
GENERATOR_VERSION = "dispatch-evidence-v1"


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


def _evidence_directory(base: Path) -> Path:
    logical = base.joinpath(*EVIDENCE_REL.split("/"))
    current = base
    for part in EVIDENCE_REL.split("/"):
        current = current / part
        if current.is_symlink():
            raise EvidenceContractError("evidence directory path may not contain symlinks")
    try:
        directory = logical.resolve(strict=True)
        directory.relative_to(base)
    except (OSError, ValueError):
        raise EvidenceContractError("evidence directory escapes the repository or is missing") from None
    if not directory.is_dir():
        raise EvidenceContractError("evidence directory is missing or unsafe")
    return directory


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
        if candidate.suffix.lower() not in (".jpg", ".png", ".json"):
            raise EvidenceContractError(f"unexpected evidence file type: {candidate.name}")
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


def build_evidence_manifest(
    *,
    root: str | Path = ROOT,
    parameters: dict[str, Any],
    delivery_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = Path(root).resolve()
    try:
        delivery = delivery_manifest or require_manifest(root=base)
    except DeliverableContractError as exc:
        raise EvidenceContractError(str(exc)) from None
    if not isinstance(parameters, dict) or not parameters:
        raise EvidenceContractError("evidence generator parameters must be a non-empty object")
    try:
        canonical_bytes(parameters)
    except StrictJSONError as exc:
        raise EvidenceContractError(f"evidence generator parameters are invalid: {exc}") from None
    vertical = delivery["artifacts"]["vertical_hosted"]
    generator_path = base / "scripts" / "build_evidence.py"
    if not generator_path.is_file() or generator_path.is_symlink():
        raise EvidenceContractError("evidence generator source is missing or unsafe")
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "run_id": delivery["identity"]["run_id"],
            "run_date": delivery["identity"]["date"],
            "composition": delivery["identity"]["composition"],
        },
        "delivery_manifest_digest": contract_digest(delivery),
        "vertical_hosted": {
            "path": vertical["path"],
            "bytes": vertical["bytes"],
            "sha256": vertical["sha256"],
        },
        "generator": {
            "path": "scripts/build_evidence.py",
            "version": GENERATOR_VERSION,
            "sha256": sha256_file(generator_path),
            "parameters": parameters,
        },
        "artifacts": _artifact_map(base),
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_json(base.joinpath(*MANIFEST_REL.split("/")), manifest)
    return manifest


def validate_evidence_manifest(
    *,
    root: str | Path = ROOT,
    delivery_manifest: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    base = Path(root).resolve()
    problems: list[str] = []
    try:
        delivery = delivery_manifest or require_manifest(root=base)
        raw = load_path(base.joinpath(*MANIFEST_REL.split("/")), label="evidence manifest")
    except (DeliverableContractError, EvidenceContractError, StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(raw, dict):
        return None, ["evidence manifest must be a JSON object"]
    expected_fields = {
        "schema_version", "identity", "delivery_manifest_digest", "vertical_hosted",
        "generator", "artifacts", "generated_at",
    }
    if set(raw) != expected_fields or raw.get("schema_version") != SCHEMA_VERSION:
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
        "path": vertical["path"], "bytes": vertical["bytes"], "sha256": vertical["sha256"]
    }
    if raw.get("vertical_hosted") != expected_vertical:
        problems.append("evidence manifest vertical_hosted facts do not match exact delivered bytes")
    generator = raw.get("generator")
    generator_path = base / "scripts" / "build_evidence.py"
    if not isinstance(generator, dict):
        problems.append("evidence manifest generator must be an object")
    else:
        if set(generator) != {"path", "version", "sha256", "parameters"}:
            problems.append("evidence manifest generator fields are not canonical")
        if generator.get("path") != "scripts/build_evidence.py":
            problems.append("evidence generator path is not canonical")
        if generator.get("version") != GENERATOR_VERSION:
            problems.append("evidence generator version changed")
        if not generator_path.is_file() or generator.get("sha256") != sha256_file(generator_path):
            problems.append("evidence generator source hash changed")
        if not isinstance(generator.get("parameters"), dict) or not generator["parameters"]:
            problems.append("evidence generator parameters are missing")
    try:
        current_artifacts = _artifact_map(base)
    except EvidenceContractError as exc:
        problems.append(str(exc))
        current_artifacts = {}
    if raw.get("artifacts") != current_artifacts:
        problems.append("evidence artifact set/bytes/hashes changed after manifest creation")
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
