#!/usr/bin/env python3
"""Canonical objective pre-panel gate for the B1 Dispatch replay fixture.

This gate intentionally does not inspect historical ``frames_v3`` folders or
unscoped review sheets. It verifies the exact delivery manifest, evidence-v3
pack, sole SFX-v3 ledger, and mastering receipt that terminal consumers use.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from deliverable_contract import (  # noqa: E402
    DeliverableContractError,
    EXPECTED_ROLES,
    MANIFEST_SCHEMA_VERSION,
    contract_digest,
    require_manifest,
)
from evidence_contract import (  # noqa: E402
    EvidenceContractError,
    MANIFEST_REL as EVIDENCE_MANIFEST_REL,
    SCHEMA_VERSION as EVIDENCE_SCHEMA_VERSION,
    evidence_manifest_sha,
    require_evidence_manifest,
)
from mastering_contract import (  # noqa: E402
    MasteringContractError,
    mastering_binding,
)
from sfx_contract import (  # noqa: E402
    SCHEMA_VERSION as SFX_SCHEMA_VERSION,
    SFXContractError,
    sidecar_facts,
)
from strict_json import StrictJSONError, load_path  # noqa: E402

REPORT_REL = "out/dispatch/quality_report.json"
REPORT_SCHEMA_VERSION = 3
AUDIO_REPORT_REL = "out/evidence/audio_report.json"


class QualityGateError(RuntimeError):
    pass


def audio_report_facts(*, root: str | Path, evidence: dict[str, Any]) -> dict[str, Any]:
    base = Path(root).resolve()
    artifact = evidence.get("artifacts", {}).get(AUDIO_REPORT_REL)
    if not isinstance(artifact, dict):
        raise QualityGateError("evidence manifest does not declare mandatory audio_report.json")
    path = base.joinpath(*AUDIO_REPORT_REL.split("/"))
    if not path.is_file() or path.is_symlink():
        raise QualityGateError("audio report is missing or unsafe")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if artifact.get("bytes") != path.stat().st_size or artifact.get("sha256") != digest:
        raise QualityGateError("audio report bytes do not match the evidence manifest")
    try:
        value = load_path(path, label="audio report")
    except (StrictJSONError, OSError) as exc:
        raise QualityGateError(str(exc)) from None
    if not isinstance(value, dict):
        raise QualityGateError("audio report must be a JSON object")
    passed = value.get("pass")
    if not isinstance(passed, dict) or set(passed) != {"loudness", "true_peak", "lra"}:
        raise QualityGateError("audio report pass fields are not canonical")
    if any(passed[key] is not True for key in ("loudness", "true_peak", "lra")):
        raise QualityGateError("audio report has a failed loudness/true-peak/LRA field")
    if value.get("measured_on") != "dispatch_square.mp4" or value.get("also_covers_master") is not True:
        raise QualityGateError("audio report is not measured on square and cross-checked on hosted master")
    metrics = {}
    for key in ("delivered_i", "delivered_tp", "delivered_lra"):
        raw = value.get(key)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(float(raw)):
            raise QualityGateError(f"audio report {key} must be finite")
        metrics[key] = float(raw)
    if not -15.0 <= metrics["delivered_i"] <= -13.0:
        raise QualityGateError("delivered audio loudness is outside -15..-13 LUFS")
    if metrics["delivered_tp"] > -1.0:
        raise QualityGateError("delivered audio true peak exceeds -1.0 dBTP")
    if not 6.0 <= metrics["delivered_lra"] <= 9.0:
        raise QualityGateError("delivered audio LRA is outside 6..9 LU")
    master = value.get("master_measured")
    if not isinstance(master, dict) or set(master) != {"i", "tp", "lra"}:
        raise QualityGateError("audio report has no canonical hosted-master measurements")
    master_metrics = {}
    for key in ("i", "tp", "lra"):
        raw = master.get(key)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(float(raw)):
            raise QualityGateError(f"audio report master_measured.{key} must be finite")
        master_metrics[key] = float(raw)
    if (
        abs(master_metrics["i"] - metrics["delivered_i"]) > 0.5
        or abs(master_metrics["lra"] - metrics["delivered_lra"]) > 0.5
    ):
        raise QualityGateError("square and hosted-master audio measurements do not agree")
    if (
        not -15.0 <= master_metrics["i"] <= -13.0
        or master_metrics["tp"] > -1.0
        or not 6.0 <= master_metrics["lra"] <= 9.0
    ):
        raise QualityGateError("hosted-master loudness/true-peak/LRA measurement fails")
    return {
        "path": AUDIO_REPORT_REL,
        "bytes": artifact.get("bytes"),
        "sha256": artifact.get("sha256"),
        **metrics,
        "master_measured": master_metrics,
        "pass": passed,
    }


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


def evaluate(
    *,
    root: str | Path = ROOT,
    manifest_loader: Callable[..., dict[str, Any]] = require_manifest,
    evidence_loader: Callable[..., dict[str, Any]] = require_evidence_manifest,
    mastering_loader: Callable[..., dict[str, Any]] = mastering_binding,
    sfx_loader: Callable[..., tuple[dict[str, Any] | None, list[str]]] = sidecar_facts,
    audio_report_loader: Callable[..., dict[str, Any]] = audio_report_facts,
) -> dict[str, Any]:
    """Return the canonical objective report or raise one concise gate error."""
    base = Path(root).resolve()
    try:
        delivery = manifest_loader(root=base)
        evidence = evidence_loader(root=base, delivery_manifest=delivery)
        mastering = mastering_loader(root=base)
        sfx, sfx_problems = sfx_loader(root=base)
        audio_report = audio_report_loader(root=base, evidence=evidence)
    except (DeliverableContractError, EvidenceContractError, MasteringContractError, SFXContractError) as exc:
        raise QualityGateError(str(exc)) from None
    if sfx is None or sfx_problems:
        raise QualityGateError("canonical SFX ledger failed: " + "; ".join(sfx_problems))
    if delivery.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise QualityGateError("delivery manifest schema is not canonical")
    if evidence.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
        raise QualityGateError("evidence manifest schema is not canonical")
    if set(delivery.get("artifacts", {})) != set(EXPECTED_ROLES):
        raise QualityGateError("delivery manifest does not contain the exact five roles")
    if sfx.get("audio") != mastering.get("audio_master"):
        raise QualityGateError("SFX ledger audio does not match the mastered audio used for encode")
    if delivery.get("mastering") != mastering:
        raise QualityGateError("delivery manifest does not bind the current mastering receipt")
    evidence_path = base.joinpath(*EVIDENCE_MANIFEST_REL.split("/"))
    checks = [
        {"id": "delivery_manifest_v4", "exit_code": 0, "result": "pass"},
        {"id": "mastering_audio_lineage_v3", "exit_code": 0, "result": "pass"},
        {"id": "evidence_manifest_v3", "exit_code": 0, "result": "pass"},
        {"id": "sole_sfx_ledger_v3", "exit_code": 0, "result": "pass"},
        {"id": "delivered_audio_report_v1", "exit_code": 0, "result": "pass"},
    ]
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "status": "pass",
        "identity": evidence["identity"],
        "delivery": {
            "path": "out/dispatch/deliverables_manifest.json",
            "digest": contract_digest(delivery),
            "schema_version": delivery["schema_version"],
        },
        "mastering": mastering,
        "evidence": {
            "path": EVIDENCE_MANIFEST_REL,
            "bytes": evidence_path.stat().st_size,
            "sha256": evidence_manifest_sha(root=base),
            "schema_version": evidence["schema_version"],
            "artifact_count": len(evidence["artifacts"]),
        },
        "sfx": {
            "path": sfx["path"],
            "sha256": sfx["sha256"],
            "schema_version": SFX_SCHEMA_VERSION,
            "audio": sfx["audio"],
        },
        "audio_report": audio_report,
        "checks": checks,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def main() -> int:
    try:
        report = evaluate()
        _atomic_json(ROOT.joinpath(*REPORT_REL.split("/")), report)
        print(
            "quality_gate: PASS canonical delivery/evidence/mastering/SFX lineage "
            f"{report['delivery']['digest'][:16]}"
        )
        return 0
    except (QualityGateError, OSError, TypeError, ValueError, KeyError) as exc:
        print(f"quality_gate: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
