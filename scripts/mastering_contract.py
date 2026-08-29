#!/usr/bin/env python3
"""Bind the canonical mute render and mastered audio to the five encoded outputs.

This receipt is deliberately written before the delivery manifest.  The delivery
manifest then embeds the receipt's bytes and SHA-256, closing the otherwise-open
gap where a different ``master.wav`` or SFX ledger could be substituted after
encoding while the video filenames stayed the same.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from render_contract import RenderContractError, probe_render, require_render
from run_guard import load_stamp, stamp_digest
from sfx_contract import AUDIO_REL, SFXContractError, sidecar_facts
from strict_json import StrictJSONError, load_path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_REL = "config/deliverables.json"
RECEIPT_REL = "out/dispatch/mastering_receipt.json"
SCHEMA_VERSION = 1
EXPECTED_ARTIFACTS = {
    "vertical_hosted": "out/dispatch/dispatch_master_hosted.mp4",
    "square": "out/dispatch/dispatch_square.mp4",
    "mobile": "out/dispatch/dispatch_master_720.mp4",
    "poster_square": "out/dispatch/poster.png",
    "poster_thumb_vertical": "out/dispatch/poster_thumb_vertical.jpg",
}


class MasteringContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
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
            raise MasteringContractError(
                f"mastering role {role} must use canonical path {expected_path}"
            )
    return value


def _file_facts(base: Path, relative: str, *, label: str) -> dict[str, Any]:
    path = _inside(base, relative, label=label)
    if not path.is_file() or path.is_symlink():
        raise MasteringContractError(f"{label} is missing or unsafe")
    return {"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def _current_payload(
    base: Path,
    *,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> dict[str, Any]:
    cfg = _config(base)
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
    audio = _file_facts(base, AUDIO_REL, label="audio master")
    if sfx.get("audio") != audio:
        raise MasteringContractError("canonical SFX ledger is not bound to the encoded audio master")
    render_receipt_path = _inside(
        base, "out/dispatch/render/render_receipt.json", label="render receipt"
    )
    artifacts: dict[str, Any] = {}
    roles = cfg["roles"]
    for role, spec in roles.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("path"), str):
            raise MasteringContractError(f"deliverable role {role} is invalid")
        artifacts[role] = _file_facts(base, spec["path"], label=f"deliverable {role}")
    return {
        "schema_version": SCHEMA_VERSION,
        "identity": {
            "run_id": stamp.get("run_id"),
            "run_date": stamp.get("date"),
            "composition": stamp.get("composition"),
            "stamp_sha256": stamp_digest(base),
        },
        "render": {
            "receipt_path": "out/dispatch/render/render_receipt.json",
            "receipt_sha256": sha256_file(render_receipt_path),
            "render_binding_sha256": render.get("render_binding_sha256"),
            "mute": render.get("artifact"),
        },
        "audio_master": audio,
        "sfx": {
            "path": sfx.get("path"),
            "sha256": sfx.get("sha256"),
            "audio": sfx.get("audio"),
        },
        "artifacts": artifacts,
    }


def record_mastering(
    *, root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> dict[str, Any]:
    base = Path(root).resolve()
    payload = _current_payload(base, render_probe=render_probe)
    payload["recorded_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _atomic_json(_inside(base, RECEIPT_REL, label="mastering receipt", must_exist=False), payload)
    return payload


def validate_mastering(
    *, root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> tuple[dict[str, Any] | None, list[str]]:
    base = Path(root).resolve()
    try:
        target = _inside(base, RECEIPT_REL, label="mastering receipt")
        receipt = load_path(target, label="mastering receipt")
    except (MasteringContractError, StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(receipt, dict):
        return None, ["mastering receipt must be a JSON object"]
    try:
        expected = _current_payload(base, render_probe=render_probe)
    except MasteringContractError as exc:
        return receipt, [str(exc)]
    problems: list[str] = []
    if set(receipt) != set(expected) | {"recorded_at"}:
        problems.append("mastering receipt fields are not canonical")
    for key, value in expected.items():
        if receipt.get(key) != value:
            problems.append(f"mastering receipt {key} changed after encoding")
    if not isinstance(receipt.get("recorded_at"), str) or not receipt["recorded_at"]:
        problems.append("mastering receipt recorded_at is missing")
    return receipt, problems


def require_mastering(
    *, root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> dict[str, Any]:
    receipt, problems = validate_mastering(root=root, render_probe=render_probe)
    if receipt is None or problems:
        raise MasteringContractError("; ".join(problems or ["mastering receipt is unavailable"]))
    return receipt


def mastering_binding(
    *, root: str | Path = ROOT,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> dict[str, Any]:
    base = Path(root).resolve()
    receipt = require_mastering(root=base, render_probe=render_probe)
    target = _inside(base, RECEIPT_REL, label="mastering receipt")
    return {
        "path": RECEIPT_REL,
        "bytes": target.stat().st_size,
        "sha256": sha256_file(target),
        "identity": receipt["identity"],
        "audio_master": receipt["audio_master"],
        "sfx": receipt["sfx"],
        "artifacts": receipt["artifacts"],
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("record", "check"))
    args = parser.parse_args()
    try:
        if args.command == "record":
            receipt = record_mastering()
            print(f"mastering_contract: recorded {receipt['audio_master']['sha256'][:16]}")
        else:
            receipt = require_mastering()
            print(f"mastering_contract: PASS {receipt['audio_master']['sha256'][:16]}")
        return 0
    except (MasteringContractError, StrictJSONError, OSError, ValueError) as exc:
        print(f"mastering_contract: FAIL: {exc}", file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
