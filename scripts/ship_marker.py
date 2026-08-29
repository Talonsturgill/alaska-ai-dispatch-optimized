#!/usr/bin/env python3
"""Record/validate the current-run SHIP_NOW stop marker as a signed-by-hashes receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from deliverable_contract import contract_digest, sha256_file
from run_guard import load_stamp
from strict_json import StrictJSONError, canonical_bytes, load_path

ROOT = Path(__file__).resolve().parent.parent
MARKER_REL = "out/dispatch/SHIP_NOW"
VERDICT_REL = "out/dispatch/panel_verdict.json"
SCHEMA_VERSION = 1


class ShipMarkerError(RuntimeError):
    pass


def _path(root: str | Path, relative: str) -> Path:
    base = Path(root).resolve()
    current = base
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise ShipMarkerError(f"{relative} path may not contain symlinks")
    target = current
    try:
        target.resolve(strict=False).relative_to(base)
    except (OSError, ValueError):
        raise ShipMarkerError(f"{relative} escapes the repository") from None
    if target.is_symlink():
        raise ShipMarkerError(f"{relative} may not be a symlink")
    return target


def _atomic(path: Path, value: dict[str, Any]) -> None:
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


def _expected(ship_state: dict[str, Any], root: Path) -> dict[str, Any]:
    stamp = load_stamp(root)
    if not isinstance(stamp, dict):
        raise ShipMarkerError("run stamp is missing or unreadable")
    verdict_path = _path(root, VERDICT_REL)
    if not verdict_path.is_file():
        raise ShipMarkerError("current-run panel verdict is missing or unsafe")
    verdict = ship_state.get("verdict")
    manifest = ship_state.get("manifest")
    if not isinstance(verdict, dict) or not isinstance(manifest, dict):
        raise ShipMarkerError("fully validated ship state is incomplete")
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "verdict": {
            "path": VERDICT_REL,
            "bytes": verdict_path.stat().st_size,
            "sha256": sha256_file(verdict_path),
            "digest": hashlib.sha256(canonical_bytes(verdict)).hexdigest(),
        },
        "manifest_digest": contract_digest(manifest),
    }


def record_ship_marker(ship_state: dict[str, Any], *, root: str | Path = ROOT) -> dict[str, Any]:
    base = Path(root).resolve()
    value = _expected(ship_state, base)
    value["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _atomic(_path(base, MARKER_REL), value)
    return value


def validate_ship_marker(
    *, root: str | Path = ROOT, ship_state: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    base = Path(root).resolve()
    if ship_state is None:
        try:
            from ship_gate import GateInputError, require_ship_verdict
            ship_state = require_ship_verdict(verify_blankness=False)
        except GateInputError as exc:
            return None, [f"current ship verdict is invalid: {exc}"]
    marker = _path(base, MARKER_REL)
    try:
        raw = load_path(marker, label="SHIP_NOW marker")
    except StrictJSONError as exc:
        return None, [str(exc)]
    if not isinstance(raw, dict):
        return None, ["SHIP_NOW marker must be a JSON object"]
    try:
        expected = _expected(ship_state, base)
    except (ShipMarkerError, StrictJSONError) as exc:
        return raw, [str(exc)]
    problems = [
        f"SHIP_NOW marker {key} does not match the current run/verdict"
        for key, wanted in expected.items() if raw.get(key) != wanted
    ]
    if set(raw) != set(expected) | {"recorded_at"}:
        problems.append("SHIP_NOW marker fields are not canonical")
    return raw, problems


def require_ship_marker(*, root: str | Path = ROOT, ship_state=None) -> dict[str, Any]:
    marker, problems = validate_ship_marker(root=root, ship_state=ship_state)
    if marker is None or problems:
        raise ShipMarkerError("; ".join(problems or ["SHIP_NOW marker is unavailable"]))
    return marker


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check",))
    parser.parse_args()
    try:
        marker = require_ship_marker()
    except (ShipMarkerError, StrictJSONError, OSError, ValueError) as exc:
        print(f"ship_marker: stale/absent marker ignored: {exc}", file=sys.stderr)
        return 1
    print(
        f"ship_marker: current {marker['run_id']} verdict={marker['verdict']['sha256'][:16]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
