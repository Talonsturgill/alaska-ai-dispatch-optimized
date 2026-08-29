#!/usr/bin/env python3
"""Bind the canonical operator preview to a fully validated ship verdict."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from deliverable_contract import contract_digest
from run_guard import load_stamp
from strict_json import StrictJSONError, canonical_bytes, load_path

ROOT = Path(__file__).resolve().parent.parent
PREVIEW_REL = "out/dispatch/dispatch-preview.html"
RECEIPT_REL = "out/dispatch/delivery_preview_receipt.json"
SCHEMA_VERSION = 1


class DeliveryPreviewError(RuntimeError):
    pass


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _paths(root: str | Path):
    base = Path(root).resolve()
    return (
        base,
        base.joinpath(*PREVIEW_REL.split("/")),
        base.joinpath(*RECEIPT_REL.split("/")),
    )


def record_delivery_preview(
    path: str | Path,
    *,
    ship_state: dict[str, Any],
    root: str | Path = ROOT,
) -> dict[str, Any]:
    base, canonical, receipt_path = _paths(root)
    supplied = Path(path).resolve()
    if supplied != canonical:
        raise DeliveryPreviewError(f"terminal preview must use canonical path {PREVIEW_REL}")
    if not canonical.is_file() or canonical.is_symlink():
        raise DeliveryPreviewError("terminal preview is missing or unsafe")
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        raise DeliveryPreviewError("run stamp is missing or unreadable")
    verdict_path = base / "out" / "dispatch" / "panel_verdict.json"
    if not verdict_path.is_file() or verdict_path.is_symlink():
        raise DeliveryPreviewError("ship verdict is missing or unsafe")
    manifest = ship_state["manifest"]
    publications = manifest.get("publications", {})
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "preview": {
            "path": PREVIEW_REL,
            "bytes": canonical.stat().st_size,
            "sha256": _sha(canonical),
        },
        "ship_verdict": {
            "path": "out/dispatch/panel_verdict.json",
            "bytes": verdict_path.stat().st_size,
            "sha256": _sha(verdict_path),
            "median": ship_state["median"],
            "threshold": ship_state["threshold"],
        },
        "manifest_digest": contract_digest(manifest),
        "publications_sha256": hashlib.sha256(canonical_bytes(publications)).hexdigest(),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_json(receipt_path, payload)
    return payload


def validate_delivery_preview(
    *,
    root: str | Path = ROOT,
    ship_state: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    base, canonical, receipt_path = _paths(root)
    if ship_state is None:
        try:
            from ship_gate import require_ship_verdict
            ship_state = require_ship_verdict(verify_blankness=True)
        except Exception as exc:
            return None, [f"ship verdict is not fully valid: {exc}"]
    try:
        raw = load_path(receipt_path, label="delivery preview receipt")
    except (StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(raw, dict):
        return None, ["delivery preview receipt must be a JSON object"]
    if not canonical.is_file() or canonical.is_symlink():
        return raw, ["canonical delivery preview is missing or unsafe"]
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        return raw, ["run stamp is missing or unreadable"]
    verdict_path = base / "out" / "dispatch" / "panel_verdict.json"
    if not verdict_path.is_file() or verdict_path.is_symlink():
        return raw, ["ship verdict is missing or unsafe"]
    manifest = ship_state["manifest"]
    expected = {
        "schema_version": SCHEMA_VERSION,
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "preview": {"path": PREVIEW_REL, "bytes": canonical.stat().st_size, "sha256": _sha(canonical)},
        "ship_verdict": {
            "path": "out/dispatch/panel_verdict.json",
            "bytes": verdict_path.stat().st_size,
            "sha256": _sha(verdict_path),
            "median": ship_state["median"],
            "threshold": ship_state["threshold"],
        },
        "manifest_digest": contract_digest(manifest),
        "publications_sha256": hashlib.sha256(canonical_bytes(manifest.get("publications", {}))).hexdigest(),
    }
    problems = [
        f"delivery preview receipt {key} does not match current ship state"
        for key, value in expected.items() if raw.get(key) != value
    ]
    if set(raw) != set(expected) | {"recorded_at"}:
        problems.append("delivery preview receipt fields are not canonical")
    return raw, problems


def require_delivery_preview(*, root: str | Path = ROOT, ship_state=None):
    receipt, problems = validate_delivery_preview(root=root, ship_state=ship_state)
    if receipt is None or problems:
        raise DeliveryPreviewError("; ".join(problems or ["delivery preview is unavailable"]))
    return receipt
