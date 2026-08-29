#!/usr/bin/env python3
"""Record and verify the one canonical, mute DispatchDaily render."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from episode_contract import EpisodeContractError, episode_facts
from run_guard import (
    ACTIVE_COMPOSITION,
    check_identity,
    composition_record,
    load_stamp,
    stamp_digest,
)
from strict_json import StrictJSONError, load_path, loads

ROOT = Path(__file__).resolve().parent.parent
RENDER_SCHEMA_VERSION = 1
CANONICAL_RENDER_REL = "out/dispatch/render/video_mute.mp4"
RECEIPT_REL = "out/dispatch/render/render_receipt.json"
RETIRED_RENDER_PATHS = (
    "out/dispatch/render_mute.mp4",
    "out/dispatch/video_mute.mp4",
    "out/dispatch/render/final.mp4",
    "out/dispatch/render/master_mute.mp4",
)


class RenderContractError(RuntimeError):
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


def render_path(root: str | Path = ROOT) -> Path:
    return Path(root).resolve().joinpath(*CANONICAL_RENDER_REL.split("/"))


def receipt_path(root: str | Path = ROOT) -> Path:
    return Path(root).resolve().joinpath(*RECEIPT_REL.split("/"))


def reject_alternate_renders(root: str | Path = ROOT) -> None:
    base = Path(root).resolve()
    stale = [relative for relative in RETIRED_RENDER_PATHS if base.joinpath(*relative.split("/")).exists()]
    if stale:
        raise RenderContractError("retired/alternate mute render exists: " + ", ".join(stale))


def probe_render(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-count_frames", "-print_format", "json",
                "-show_entries",
                "stream=codec_type,width,height,nb_read_frames,nb_frames:format=duration",
                str(target),
            ],
            capture_output=True, text=True, timeout=180,
        )
    except FileNotFoundError:
        raise RenderContractError("ffprobe is not installed") from None
    except subprocess.TimeoutExpired:
        raise RenderContractError("ffprobe timed out while checking the mute render") from None
    except OSError as exc:
        raise RenderContractError(f"ffprobe could not start: {exc}") from None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise RenderContractError(
            f"ffprobe rejected the mute render: {detail[-1] if detail else 'unreadable media'}"
        )
    try:
        raw = loads(result.stdout, label="ffprobe render output")
    except StrictJSONError as exc:
        raise RenderContractError(str(exc)) from None
    if not isinstance(raw, dict) or not isinstance(raw.get("streams"), list):
        raise RenderContractError("ffprobe render output has no stream list")
    video = [item for item in raw["streams"] if isinstance(item, dict) and item.get("codec_type") == "video"]
    audio = [item for item in raw["streams"] if isinstance(item, dict) and item.get("codec_type") == "audio"]
    if len(video) != 1:
        raise RenderContractError(f"mute render must have exactly one video stream, got {len(video)}")
    first = video[0]
    try:
        width = int(first.get("width"))
        height = int(first.get("height"))
        frames = int(first.get("nb_read_frames") or first.get("nb_frames"))
        duration = float((raw.get("format") or {}).get("duration"))
    except (TypeError, ValueError, OverflowError):
        raise RenderContractError("ffprobe returned invalid render dimensions, frames, or duration") from None
    if not math.isfinite(duration) or duration <= 0 or frames <= 0:
        raise RenderContractError("ffprobe returned non-finite or non-positive render facts")
    return {
        "width": width,
        "height": height,
        "frames": frames,
        "duration_seconds": duration,
        "streams": {"video": len(video), "audio": len(audio)},
    }


def _expected(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    ok, reason = check_identity(
        root=root, expected_composition=ACTIVE_COMPOSITION, require_props=True
    )
    if not ok:
        raise RenderContractError(f"run identity is invalid: {reason}")
    stamp = load_stamp(root)
    if not isinstance(stamp, dict):
        raise RenderContractError("run stamp is missing or unreadable")
    record = composition_record(ACTIVE_COMPOSITION, root)
    if record.get("mute_render_path") != CANONICAL_RENDER_REL:
        raise RenderContractError("composition registry mute_render_path is not canonical")
    if record.get("render_receipt_path") != RECEIPT_REL:
        raise RenderContractError("composition registry render_receipt_path is not canonical")
    try:
        episode = episode_facts(root=root)
    except EpisodeContractError as exc:
        raise RenderContractError(str(exc)) from None
    return stamp, episode


def _artifact_facts(path: Path, media: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": CANONICAL_RENDER_REL,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "media": media,
    }


def _media_problems(media: dict[str, Any], episode: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if (media.get("width"), media.get("height")) != (1080, 1920):
        problems.append("mute render must be exactly 1080x1920")
    if media.get("streams") != {"video": 1, "audio": 0}:
        problems.append("mute render must contain one video stream and zero audio streams")
    if media.get("frames") != episode["total_frames"]:
        problems.append(
            f"mute render has {media.get('frames')} frames, expected {episode['total_frames']}"
        )
    duration = media.get("duration_seconds")
    tolerance = 1.0 / episode["fps"] + 0.01
    if (
        isinstance(duration, bool)
        or not isinstance(duration, (int, float))
        or not math.isfinite(float(duration))
        or abs(float(duration) - episode["duration_seconds"]) > tolerance
    ):
        problems.append(
            "mute render duration does not match hash-bound episode total/fps including credits"
        )
    return problems


def prepare_render(*, root: str | Path = ROOT) -> None:
    """Validate identity, reject alternates, then remove only canonical stale outputs.

    Every final-render entry point calls this before Remotion.  A failed render
    therefore cannot leave an older valid receipt/output available to encode.
    """
    base = Path(root).resolve()
    reject_alternate_renders(base)
    _expected(base)
    for target in (receipt_path(base), render_path(base)):
        try:
            target.unlink()
        except FileNotFoundError:
            pass


def record_render(
    *, root: str | Path = ROOT,
    probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> dict[str, Any]:
    base = Path(root).resolve()
    reject_alternate_renders(base)
    stamp, episode = _expected(base)
    target = render_path(base)
    if not target.is_file() or target.is_symlink():
        raise RenderContractError(f"canonical mute render is missing or unsafe: {CANONICAL_RENDER_REL}")
    if target.stat().st_mtime <= float(stamp["started_at"]):
        raise RenderContractError("canonical mute render does not postdate the run stamp")
    media = probe(target)
    problems = _media_problems(media, episode)
    if problems:
        raise RenderContractError("; ".join(problems))
    receipt = {
        "schema_version": RENDER_SCHEMA_VERSION,
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "stamp_sha256": stamp_digest(base),
        "stamped_git_head": stamp["git_head"],
        "props_path": stamp["props_path"],
        "props_sha256": stamp["props_sha256"],
        "episode": episode,
        "artifact": _artifact_facts(target, media),
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_json(receipt_path(base), receipt)
    return receipt


def validate_render(
    *, root: str | Path = ROOT,
    probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> tuple[dict[str, Any] | None, list[str]]:
    base = Path(root).resolve()
    problems: list[str] = []
    try:
        reject_alternate_renders(base)
        stamp, episode = _expected(base)
        receipt = load_path(receipt_path(base), label="render receipt")
    except (RenderContractError, StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(receipt, dict):
        return None, ["render receipt must be a JSON object"]
    target = render_path(base)
    if not target.is_file() or target.is_symlink():
        return receipt, ["canonical mute render is missing or unsafe"]
    try:
        media = probe(target)
    except RenderContractError as exc:
        return receipt, [str(exc)]
    problems.extend(_media_problems(media, episode))
    expected = {
        "schema_version": RENDER_SCHEMA_VERSION,
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "stamp_sha256": stamp_digest(base),
        "stamped_git_head": stamp["git_head"],
        "props_path": stamp["props_path"],
        "props_sha256": stamp["props_sha256"],
        "episode": episode,
        "artifact": _artifact_facts(target, media),
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            problems.append(f"render receipt {key} does not match the current run/render")
    if set(receipt) != set(expected) | {"recorded_at"}:
        problems.append("render receipt fields are not canonical")
    if not isinstance(receipt.get("recorded_at"), str) or not receipt["recorded_at"]:
        problems.append("render receipt recorded_at is missing")
    return receipt, problems


def require_render(
    *, root: str | Path = ROOT,
    probe: Callable[[str | Path], dict[str, Any]] = probe_render,
) -> dict[str, Any]:
    receipt, problems = validate_render(root=root, probe=probe)
    if receipt is None or problems:
        raise RenderContractError("; ".join(problems or ["render receipt is unavailable"]))
    return receipt


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("prepare")
    sub.add_parser("record")
    sub.add_parser("check")
    facts = sub.add_parser("episode")
    facts.add_argument("field", choices=("total_frames", "fps", "duration_seconds"))
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare_render()
            print(f"render_contract: prepared {CANONICAL_RENDER_REL}")
        elif args.command == "record":
            receipt = record_render()
            print(
                "render_contract: recorded "
                f"{receipt['artifact']['sha256'][:16]} {receipt['episode']['total_frames']} frames"
            )
        elif args.command == "check":
            receipt = require_render()
            print(f"render_contract: PASS {receipt['artifact']['sha256'][:16]}")
        else:
            print(episode_facts(root=ROOT)[args.field])
        return 0
    except (RenderContractError, EpisodeContractError, StrictJSONError, OSError, ValueError) as exc:
        print(f"render_contract: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
