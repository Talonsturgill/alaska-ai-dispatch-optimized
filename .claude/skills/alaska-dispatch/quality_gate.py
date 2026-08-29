#!/usr/bin/env python3
"""Canonical objective pre-panel gate for the B1 Dispatch replay fixture.

This gate intentionally does not inspect historical ``frames_v3`` folders or
unscoped review sheets. It verifies the exact delivery manifest, evidence-v3
pack, sole SFX-v3 ledger, and mastering receipt that terminal consumers use.
"""
from __future__ import annotations

import json
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

REPORT_REL = "out/dispatch/quality_report.json"
REPORT_SCHEMA_VERSION = 2


class QualityGateError(RuntimeError):
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


def evaluate(
    *,
    root: str | Path = ROOT,
    manifest_loader: Callable[..., dict[str, Any]] = require_manifest,
    evidence_loader: Callable[..., dict[str, Any]] = require_evidence_manifest,
    mastering_loader: Callable[..., dict[str, Any]] = mastering_binding,
    sfx_loader: Callable[..., tuple[dict[str, Any] | None, list[str]]] = sidecar_facts,
) -> dict[str, Any]:
    """Return the canonical objective report or raise one concise gate error."""
    base = Path(root).resolve()
    try:
        delivery = manifest_loader(root=base)
        evidence = evidence_loader(root=base, delivery_manifest=delivery)
        mastering = mastering_loader(root=base)
        sfx, sfx_problems = sfx_loader(root=base)
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
        {"id": "mastering_audio_lineage_v1", "exit_code": 0, "result": "pass"},
        {"id": "evidence_manifest_v3", "exit_code": 0, "result": "pass"},
        {"id": "sole_sfx_ledger_v3", "exit_code": 0, "result": "pass"},
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
