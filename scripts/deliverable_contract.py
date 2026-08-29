#!/usr/bin/env python3
"""Build and verify the five hash-bound Alaska AI Dispatch deliverables.

The manifest is an attestation, not a filename list. Every check re-probes the
files and recomputes bytes and SHA-256, so a same-size or mtime-preserving edit
still fails. Paths are exact repo-relative POSIX paths and the five roles are
closed: no 4:5 alias or sixth distribution master is accepted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from run_guard import ACTIVE_COMPOSITION, check_identity, load_stamp, stamp_digest
from episode_contract import EpisodeContractError, episode_facts
from mastering_contract import MasteringContractError, mastering_binding
from render_contract import RenderContractError, probe_render, require_render
from strict_json import StrictJSONError, canonical_bytes, load_path, loads

ROOT = Path(__file__).resolve().parent.parent
CONFIG_REL = "config/deliverables.json"
EXPECTED_ROLES = (
    "vertical_hosted",
    "square",
    "mobile",
    "poster_square",
    "poster_thumb_vertical",
)
EXPECTED_SPECS = {
    "vertical_hosted": ("out/dispatch/dispatch_master_hosted.mp4", "video", 1080, 1920, 1, 1),
    "square": ("out/dispatch/dispatch_square.mp4", "video", 1080, 1080, 1, 1),
    "mobile": ("out/dispatch/dispatch_master_720.mp4", "video", 720, 1280, 1, 1),
    "poster_square": ("out/dispatch/poster.png", "image", 1080, 1080, 1, 0),
    "poster_thumb_vertical": (
        "out/dispatch/poster_thumb_vertical.jpg", "image", 540, 960, 1, 0,
    ),
}
EXPECTED_CODECS = {
    "vertical_hosted": (["h264"], ["aac"]),
    "square": (["h264"], ["aac"]),
    "mobile": (["h264"], ["aac"]),
    "poster_square": (["png"], []),
    "poster_thumb_vertical": (["mjpeg"], []),
}
EXPECTED_MANIFEST_PATH = "out/dispatch/deliverables_manifest.json"
EXPECTED_MASTERING_RECEIPT_PATH = "out/dispatch/mastering_receipt.json"
MANIFEST_SCHEMA_VERSION = 4
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_OID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


class DeliverableContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def safe_relative(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise DeliverableContractError(f"{label} must be a non-empty ASCII repo-relative path")
    if "\\" in value or not SAFE_PATH_RE.fullmatch(value) or re.match(r"^[A-Za-z]:", value):
        raise DeliverableContractError(f"{label} must use canonical POSIX path characters")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute() or ".." in pure.parts or any(part in ("", ".") for part in pure.parts)
        or pure.as_posix() != value
    ):
        raise DeliverableContractError(f"{label} must stay inside the repository")
    return pure.as_posix()


def resolve_inside(
    root: Path, relative: str, *, label: str, must_exist: bool = True,
) -> Path:
    rel = safe_relative(relative, label=label)
    candidate = root.joinpath(*PurePosixPath(rel).parts)
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as exc:
        raise DeliverableContractError(f"{label} cannot be resolved: {exc}") from None
    try:
        resolved.relative_to(root)
    except ValueError:
        raise DeliverableContractError(f"{label} escapes the repository") from None
    if candidate.is_symlink():
        raise DeliverableContractError(f"{label} may not be a symlink")
    return resolved


def load_config(
    *, root: str | Path = ROOT, config_path: str | Path | None = None,
) -> dict[str, Any]:
    base = Path(root).resolve()
    if config_path:
        path = Path(config_path).resolve()
        try:
            path.relative_to(base)
        except ValueError:
            raise DeliverableContractError("deliverable config is outside the repository") from None
        if Path(config_path).is_symlink():
            raise DeliverableContractError("deliverable config may not be a symlink")
    else:
        path = resolve_inside(base, CONFIG_REL, label="deliverable config")
    value = load_path(path, label="deliverable config")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise DeliverableContractError("deliverable config must be a schema_version 1 object")
    roles = value.get("roles")
    if not isinstance(roles, dict) or set(roles) != set(EXPECTED_ROLES) or len(roles) != 5:
        raise DeliverableContractError(
            "deliverable config must define exactly: " + ", ".join(EXPECTED_ROLES)
        )
    paths: set[str] = set()
    for role in EXPECTED_ROLES:
        spec = roles[role]
        if not isinstance(spec, dict):
            raise DeliverableContractError(f"role {role} must be an object")
        rel = safe_relative(spec.get("path"), label=f"path for {role}")
        if rel in paths:
            raise DeliverableContractError(f"deliverable path collision at {rel}")
        paths.add(rel)
        if spec.get("media_type") not in ("video", "image"):
            raise DeliverableContractError(f"role {role} has invalid media_type")
        for key in ("width", "height", "video_streams", "audio_streams", "minimum_bytes", "maximum_bytes"):
            if not isinstance(spec.get(key), int) or spec[key] < 0:
                raise DeliverableContractError(f"role {role}.{key} must be a nonnegative integer")
        if spec["minimum_bytes"] > spec["maximum_bytes"]:
            raise DeliverableContractError(f"role {role} has an inverted byte range")
        expected = EXPECTED_SPECS[role]
        actual = (
            rel, spec["media_type"], spec["width"], spec["height"],
            spec["video_streams"], spec["audio_streams"],
        )
        if actual != expected:
            raise DeliverableContractError(
                f"role {role} must be {expected[0]} {expected[2]}x{expected[3]} "
                f"with video={expected[4]} audio={expected[5]}"
            )
        expected_video, expected_audio = EXPECTED_CODECS[role]
        if spec.get("allowed_video_codecs") != expected_video:
            raise DeliverableContractError(
                f"role {role}.allowed_video_codecs must be exactly {expected_video}"
            )
        if spec.get("allowed_audio_codecs") != expected_audio:
            raise DeliverableContractError(
                f"role {role}.allowed_audio_codecs must be exactly {expected_audio}"
            )
    manifest_rel = safe_relative(value.get("manifest_path"), label="manifest path")
    if manifest_rel != EXPECTED_MANIFEST_PATH:
        raise DeliverableContractError(f"manifest path must be {EXPECTED_MANIFEST_PATH}")
    if manifest_rel in paths:
        raise DeliverableContractError("manifest path collides with a deliverable")
    mastering_rel = safe_relative(value.get("mastering_receipt_path"), label="mastering receipt path")
    if mastering_rel != EXPECTED_MASTERING_RECEIPT_PATH:
        raise DeliverableContractError(
            f"mastering receipt path must be {EXPECTED_MASTERING_RECEIPT_PATH}"
        )
    if mastering_rel in paths or mastering_rel == manifest_rel:
        raise DeliverableContractError("mastering receipt path collides with an artifact or manifest")
    forbidden = value.get("forbidden_dimensions")
    if not isinstance(forbidden, list) or [1080, 1350] not in forbidden:
        raise DeliverableContractError("deliverable config must explicitly forbid 1080x1350")
    duration = value.get("duration_seconds")
    if not isinstance(duration, dict):
        raise DeliverableContractError("duration_seconds must be an object")
    for key in ("minimum", "maximum", "match_tolerance"):
        if not isinstance(duration.get(key), (int, float)) or not math.isfinite(float(duration[key])):
            raise DeliverableContractError(f"duration_seconds.{key} must be finite")
    if float(duration["minimum"]) <= 0 or float(duration["maximum"]) < float(duration["minimum"]):
        raise DeliverableContractError("duration_seconds range is invalid")
    if (
        duration.get("derived_from") != "out/dispatch/episode_props.json#total/fps"
        or duration.get("includes_credits") is not True
        or duration.get("maximum_frame_error") != 1
    ):
        raise DeliverableContractError(
            "duration_seconds must derive from episode_props total/fps including credits with one-frame tolerance"
        )
    if value.get("video_fps") != 30:
        raise DeliverableContractError("deliverable config video_fps must be exactly 30")
    preview_roles = value.get("terminal_preview_required_roles")
    if (
        not isinstance(preview_roles, list)
        or len(preview_roles) != len(set(preview_roles))
        or not {"vertical_hosted", "square"}.issubset(preview_roles)
        or any(role not in EXPECTED_ROLES for role in preview_roles)
    ):
        raise DeliverableContractError(
            "terminal preview roles must be unique known roles including vertical_hosted and square"
        )
    return value


def terminal_preview_roles(*, root: str | Path = ROOT) -> tuple[str, ...]:
    return tuple(load_config(root=root)["terminal_preview_required_roles"])


def manifest_path(*, root: str | Path = ROOT, config: dict[str, Any] | None = None) -> Path:
    base = Path(root).resolve()
    cfg = config or load_config(root=base)
    return resolve_inside(base, cfg["manifest_path"], label="manifest", must_exist=False)


def probe_media(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error", "-print_format", "json",
                "-count_frames", "-show_format", "-show_streams", str(target),
            ],
            capture_output=True,
            text=True,
            timeout=90,
        )
    except FileNotFoundError:
        raise DeliverableContractError("ffprobe is not installed") from None
    except subprocess.TimeoutExpired:
        raise DeliverableContractError(f"ffprobe timed out for {target.name}") from None
    except OSError as exc:
        raise DeliverableContractError(f"ffprobe could not start for {target.name}: {exc}") from None
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise DeliverableContractError(
            f"ffprobe rejected {target.name}: {detail[-1] if detail else 'unreadable media'}"
        )
    try:
        raw = loads(result.stdout, label=f"ffprobe output for {target.name}")
    except StrictJSONError as exc:
        raise DeliverableContractError(str(exc)) from None
    if not isinstance(raw, dict) or not isinstance(raw.get("streams"), list):
        raise DeliverableContractError(f"ffprobe returned no stream list for {target.name}")
    streams = raw["streams"]
    video = [item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"]
    audio = [item for item in streams if isinstance(item, dict) and item.get("codec_type") == "audio"]
    first_video = video[0] if video else {}
    duration_raw = (raw.get("format") or {}).get("duration") if isinstance(raw.get("format"), dict) else None
    if duration_raw in (None, "N/A") and video:
        duration_raw = first_video.get("duration")
    duration: float | None = None
    if duration_raw not in (None, "N/A"):
        try:
            duration = float(duration_raw)
        except (TypeError, ValueError):
            raise DeliverableContractError(f"ffprobe returned invalid duration for {target.name}") from None
        if not math.isfinite(duration) or duration < 0:
            raise DeliverableContractError(f"ffprobe returned invalid duration for {target.name}")
    try:
        width = int(first_video.get("width", 0))
        height = int(first_video.get("height", 0))
    except (TypeError, ValueError):
        raise DeliverableContractError(f"ffprobe returned invalid dimensions for {target.name}") from None
    def parse_rate(value: Any) -> float | None:
        if value in (None, "", "N/A", "0/0"):
            return None
        try:
            numerator, denominator = str(value).split("/", 1)
            rate = float(numerator) / float(denominator)
        except (TypeError, ValueError, ZeroDivisionError, OverflowError):
            raise DeliverableContractError(f"ffprobe returned invalid fps for {target.name}") from None
        if not math.isfinite(rate) or rate <= 0:
            raise DeliverableContractError(f"ffprobe returned invalid fps for {target.name}")
        return round(rate, 9)

    fps = parse_rate(first_video.get("avg_frame_rate"))
    if fps is None:
        fps = parse_rate(first_video.get("r_frame_rate"))
    count_raw = first_video.get("nb_read_frames")
    if count_raw in (None, "", "N/A"):
        count_raw = first_video.get("nb_frames")
    frame_count: int | None = None
    if count_raw not in (None, "", "N/A"):
        try:
            frame_count = int(count_raw)
        except (TypeError, ValueError, OverflowError):
            raise DeliverableContractError(f"ffprobe returned invalid frame count for {target.name}") from None
        if frame_count <= 0:
            raise DeliverableContractError(f"ffprobe returned invalid frame count for {target.name}")
    return {
        "width": width,
        "height": height,
        "duration_seconds": round(duration, 6) if duration is not None else None,
        "streams": {"video": len(video), "audio": len(audio)},
        "video_codecs": [str(item.get("codec_name", "")) for item in video],
        "audio_codecs": [str(item.get("codec_name", "")) for item in audio],
        "fps": fps,
        "frame_count": frame_count,
    }


def _identity(root: Path) -> dict[str, Any]:
    ok, reason = check_identity(root=root, expected_composition=ACTIVE_COMPOSITION, require_props=True)
    if not ok:
        raise DeliverableContractError(f"run identity is invalid: {reason}")
    stamp = load_stamp(root)
    if stamp is None:
        raise DeliverableContractError("run stamp is missing or unreadable")
    fields = (
        "run_id", "date", "composition", "mode", "repository", "origin", "worktree_root",
        "branch", "git_head", "props_path", "props_sha256", "source_path", "source_sha256",
        "source_dependencies", "registry_sha256", "root_source_sha256",
    )
    identity = {key: stamp.get(key) for key in fields}
    identity["stamp_sha256"] = stamp_digest(root)
    return identity


def _entry_problems(
    role: str,
    spec: dict[str, Any],
    entry: dict[str, Any],
    facts: dict[str, Any],
    path: Path,
    *,
    started_at: float,
    forbidden: set[tuple[int, int]],
    duration: dict[str, Any],
    episode: dict[str, Any],
) -> list[str]:
    problems: list[str] = []
    expected_static = {
        "path": spec["path"],
        "media_type": spec["media_type"],
        "width": spec["width"],
        "height": spec["height"],
        "streams": {"video": spec["video_streams"], "audio": spec["audio_streams"]},
    }
    for key, wanted in expected_static.items():
        if entry.get(key) != wanted:
            problems.append(f"{role}.{key} does not match the canonical contract")
    expected_fields = {
        "path", "media_type", "width", "height", "duration_seconds", "streams",
        "video_codecs", "audio_codecs", "fps", "frame_count", "bytes", "sha256",
    }
    if set(entry) != expected_fields:
        problems.append(f"{role} manifest fields are not canonical")
    dimensions = (facts["width"], facts["height"])
    if dimensions in forbidden:
        problems.append(f"{role} uses forbidden dimensions {dimensions[0]}x{dimensions[1]}")
    if dimensions != (spec["width"], spec["height"]):
        problems.append(
            f"{role} is {dimensions[0]}x{dimensions[1]}, expected {spec['width']}x{spec['height']}"
        )
    if facts["streams"] != expected_static["streams"]:
        problems.append(
            f"{role} streams are video={facts['streams']['video']} audio={facts['streams']['audio']}, "
            f"expected video={spec['video_streams']} audio={spec['audio_streams']}"
        )
    expected_video_codecs = spec["allowed_video_codecs"]
    expected_audio_codecs = spec["allowed_audio_codecs"]
    if facts.get("video_codecs") != expected_video_codecs:
        problems.append(
            f"{role} video codecs {facts.get('video_codecs')} are not canonical {expected_video_codecs}"
        )
    if facts.get("audio_codecs") != expected_audio_codecs:
        problems.append(
            f"{role} audio codecs {facts.get('audio_codecs')} are not canonical {expected_audio_codecs}"
        )
    if entry.get("video_codecs") != facts.get("video_codecs"):
        problems.append(f"{role} video codecs changed after manifest creation")
    if entry.get("audio_codecs") != facts.get("audio_codecs"):
        problems.append(f"{role} audio codecs changed after manifest creation")
    size = path.stat().st_size
    if not spec["minimum_bytes"] <= size <= spec["maximum_bytes"]:
        problems.append(f"{role} byte size {size} is outside its allowed range")
    if entry.get("bytes") != size:
        problems.append(f"{role} byte size changed after manifest creation")
    current_sha = sha256_file(path)
    if entry.get("sha256") != current_sha:
        problems.append(f"{role} SHA-256 changed after manifest creation")
    if path.stat().st_mtime <= started_at:
        problems.append(f"{role} does not postdate the current run stamp")
    if spec["media_type"] == "video":
        fps = facts.get("fps")
        if not isinstance(fps, (int, float)) or isinstance(fps, bool) or not math.isfinite(float(fps)):
            problems.append(f"{role} has no measurable fps")
        elif abs(float(fps) - 30.0) > 0.001:
            problems.append(f"{role} fps {float(fps):.6f} is not the required 30 fps")
        if entry.get("fps") != fps:
            problems.append(f"{role} fps changed after manifest creation")
        frame_count = facts.get("frame_count")
        if isinstance(frame_count, bool) or not isinstance(frame_count, int):
            problems.append(f"{role} has no measurable frame count")
        elif abs(frame_count - int(episode["total_frames"])) > int(duration["maximum_frame_error"]):
            problems.append(
                f"{role} frame count {frame_count} does not match hash-bound episode total "
                f"{episode['total_frames']}"
            )
        if entry.get("frame_count") != frame_count:
            problems.append(f"{role} frame count changed after manifest creation")
        seconds = facts.get("duration_seconds")
        if not isinstance(seconds, (int, float)):
            problems.append(f"{role} has no measurable duration")
        else:
            low, high = float(duration["minimum"]), float(duration["maximum"])
            if not low <= float(seconds) <= high:
                problems.append(f"{role} duration {seconds:.3f}s is outside {low:.1f}..{high:.1f}s")
            exact_tolerance = 1.0 / int(episode["fps"]) + 0.01
            if abs(float(seconds) - float(episode["duration_seconds"])) > exact_tolerance:
                problems.append(
                    f"{role} duration {seconds:.3f}s does not match hash-bound episode "
                    f"duration {episode['duration_seconds']:.3f}s including credits"
                )
            recorded = entry.get("duration_seconds")
            if not isinstance(recorded, (int, float)) or abs(float(recorded) - float(seconds)) > 0.01:
                problems.append(f"{role} duration changed after manifest creation")
    else:
        if entry.get("duration_seconds") is not None:
            problems.append(f"{role} image duration must be null")
        if entry.get("fps") != facts.get("fps"):
            problems.append(f"{role} image fps changed after manifest creation")
        if entry.get("frame_count") != facts.get("frame_count"):
            problems.append(f"{role} image frame count changed after manifest creation")
    return problems


def build_manifest(
    *,
    root: str | Path = ROOT,
    probe: Callable[[str | Path], dict[str, Any]] = probe_media,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    mastering_audio_probe: Callable[..., dict[str, Any]] | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    base = Path(root).resolve()
    cfg = load_config(root=base, config_path=config_path)
    identity = _identity(base)
    try:
        episode = episode_facts(root=base)
        render = require_render(root=base, probe=render_probe)
        mastering_kwargs = {"root": base, "render_probe": render_probe}
        if mastering_audio_probe is not None:
            mastering_kwargs["audio_probe"] = mastering_audio_probe
        mastering = mastering_binding(**mastering_kwargs)
    except (EpisodeContractError, RenderContractError, MasteringContractError) as exc:
        raise DeliverableContractError(str(exc)) from None
    stamp = load_stamp(base)
    assert stamp is not None
    artifacts: dict[str, Any] = {}
    forbidden = {tuple(int(x) for x in pair) for pair in cfg["forbidden_dimensions"]}
    all_problems: list[str] = []
    durations: list[float] = []
    for role in EXPECTED_ROLES:
        spec = cfg["roles"][role]
        path = resolve_inside(base, spec["path"], label=f"artifact {role}")
        if not path.is_file():
            all_problems.append(f"{role} is missing")
            continue
        try:
            facts = probe(path)
        except DeliverableContractError as exc:
            all_problems.append(f"{role}: {exc}")
            continue
        entry = {
            "path": spec["path"],
            "media_type": spec["media_type"],
            "width": spec["width"],
            "height": spec["height"],
            "duration_seconds": facts.get("duration_seconds") if spec["media_type"] == "video" else None,
            "streams": {"video": spec["video_streams"], "audio": spec["audio_streams"]},
            "video_codecs": facts.get("video_codecs", []),
            "audio_codecs": facts.get("audio_codecs", []),
            "fps": facts.get("fps"),
            "frame_count": facts.get("frame_count"),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        all_problems.extend(
            _entry_problems(
                role, spec, entry, facts, path, started_at=float(stamp["started_at"]),
                forbidden=forbidden, duration=cfg["duration_seconds"],
                episode=episode,
            )
        )
        if spec["media_type"] == "video" and isinstance(facts.get("duration_seconds"), (int, float)):
            durations.append(float(facts["duration_seconds"]))
        artifacts[role] = entry
    tolerance = float(cfg["duration_seconds"]["match_tolerance"])
    if durations and max(durations) - min(durations) > tolerance:
        all_problems.append("video deliverable durations do not match")
    if all_problems:
        raise DeliverableContractError("; ".join(all_problems))
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "identity": identity,
        "episode": episode,
        "render": render,
        "mastering": mastering,
        "artifacts": artifacts,
        "publications": {},
    }
    _atomic_json(manifest_path(root=base, config=cfg), manifest)
    return manifest


def contract_digest(manifest: dict[str, Any]) -> str:
    immutable = {
        "schema_version": manifest.get("schema_version"),
        "identity": manifest.get("identity"),
        "episode": manifest.get("episode"),
        "render": manifest.get("render"),
        "mastering": manifest.get("mastering"),
        "artifacts": manifest.get("artifacts"),
    }
    return hashlib.sha256(canonical_bytes(immutable)).hexdigest()


def publication_name(manifest: dict[str, Any], role: str) -> str:
    if role not in EXPECTED_ROLES:
        raise DeliverableContractError(f"unknown publication role {role}")
    run_id = manifest.get("identity", {}).get("run_id")
    if (
        not isinstance(run_id, str) or not run_id.isascii()
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", run_id)
    ):
        raise DeliverableContractError("run_id is not safe for an immutable media name")
    entry = manifest["artifacts"][role]
    suffix = Path(entry["path"]).suffix.lower()
    # Keep the complete artifact digest in the object name.  A shortened digest
    # is convenient, but it is not an unambiguous identity for immutable media.
    name = f"dispatch-{run_id}-{role}-{entry['sha256']}{suffix}"
    if len(name) > 255:
        raise DeliverableContractError("immutable media name exceeds 255 characters")
    return name


def validate_manifest(
    *,
    root: str | Path = ROOT,
    path: str | Path | None = None,
    probe: Callable[[str | Path], dict[str, Any]] | None = None,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    mastering_audio_probe: Callable[..., dict[str, Any]] | None = None,
    require_publications: Iterable[str] = (),
    config_path: str | Path | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    base = Path(root).resolve()
    media_probe = probe or probe_media
    try:
        cfg = load_config(root=base, config_path=config_path)
        if path:
            supplied = Path(path)
            target = supplied.resolve()
            try:
                target.relative_to(base)
            except ValueError:
                raise DeliverableContractError("deliverables manifest is outside the repository") from None
            if supplied.is_symlink():
                raise DeliverableContractError("deliverables manifest may not be a symlink")
        else:
            target = manifest_path(root=base, config=cfg)
        raw = load_path(target, label="deliverables manifest")
    except (DeliverableContractError, StrictJSONError, OSError) as exc:
        return None, [str(exc)]
    if not isinstance(raw, dict):
        return None, ["deliverables manifest must be a JSON object"]
    problems: list[str] = []
    if raw.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        problems.append(f"manifest schema_version must be {MANIFEST_SCHEMA_VERSION}")
    try:
        expected_identity = _identity(base)
        if raw.get("identity") != expected_identity:
            problems.append("manifest run identity does not match the current stamp")
    except DeliverableContractError as exc:
        problems.append(str(exc))
    try:
        expected_episode = episode_facts(root=base)
        expected_render = require_render(root=base, probe=render_probe)
        if raw.get("episode") != expected_episode:
            problems.append("manifest episode timing does not match hash-bound props")
        if raw.get("render") != expected_render:
            problems.append("manifest render receipt does not match the canonical mute render")
    except (EpisodeContractError, RenderContractError) as exc:
        problems.append(str(exc))
        expected_episode = {"fps": 30, "duration_seconds": float("nan"), "total_frames": 0}
    try:
        mastering_kwargs = {"root": base, "render_probe": render_probe}
        if mastering_audio_probe is not None:
            mastering_kwargs["audio_probe"] = mastering_audio_probe
        expected_mastering = mastering_binding(**mastering_kwargs)
        if raw.get("mastering") != expected_mastering:
            problems.append("manifest mastering receipt does not match encoded audio/artifact lineage")
    except MasteringContractError as exc:
        problems.append(str(exc))
    expected_manifest_fields = {
        "schema_version", "identity", "episode", "render", "mastering",
        "artifacts", "publications",
    }
    if set(raw) != expected_manifest_fields:
        problems.append("manifest fields are not canonical")
    artifacts = raw.get("artifacts")
    if not isinstance(artifacts, dict) or set(artifacts) != set(EXPECTED_ROLES) or len(artifacts) != 5:
        problems.append("manifest must contain exactly the five canonical artifact roles")
        artifacts = artifacts if isinstance(artifacts, dict) else {}
    stamp = load_stamp(base)
    if stamp is None:
        problems.append("run stamp is missing or unreadable")
        started_at = float("inf")
    else:
        started_at = float(stamp.get("started_at", float("inf")))
    forbidden = {tuple(int(x) for x in pair) for pair in cfg["forbidden_dimensions"]}
    seen_paths: set[str] = set()
    durations: list[float] = []
    for role in EXPECTED_ROLES:
        entry = artifacts.get(role)
        if not isinstance(entry, dict):
            problems.append(f"manifest artifact {role} must be an object")
            continue
        rel = entry.get("path")
        try:
            canonical_rel = safe_relative(rel, label=f"manifest path for {role}")
            if canonical_rel in seen_paths:
                problems.append(f"manifest artifact paths collide at {canonical_rel}")
            seen_paths.add(canonical_rel)
            path_obj = resolve_inside(base, canonical_rel, label=f"artifact {role}")
        except DeliverableContractError as exc:
            problems.append(str(exc))
            continue
        if not path_obj.is_file():
            problems.append(f"{role} is missing")
            continue
        try:
            facts = media_probe(path_obj)
        except DeliverableContractError as exc:
            problems.append(f"{role}: {exc}")
            continue
        problems.extend(
            _entry_problems(
                role, cfg["roles"][role], entry, facts, path_obj, started_at=started_at,
                forbidden=forbidden, duration=cfg["duration_seconds"],
                episode=expected_episode,
            )
        )
        if cfg["roles"][role]["media_type"] == "video" and isinstance(facts.get("duration_seconds"), (int, float)):
            durations.append(float(facts["duration_seconds"]))
    tolerance = float(cfg["duration_seconds"]["match_tolerance"])
    if durations and max(durations) - min(durations) > tolerance:
        problems.append("video deliverable durations do not match")
    publications = raw.get("publications", {})
    if not isinstance(publications, dict):
        problems.append("manifest publications must be an object")
        publications = {}
    unknown_publications = set(publications) - set(EXPECTED_ROLES)
    if unknown_publications:
        problems.append("manifest has unknown publication roles: " + ", ".join(sorted(unknown_publications)))
    seen_names: dict[str, str] = {}
    seen_urls: dict[str, str] = {}
    for role, receipt in publications.items():
        if role not in EXPECTED_ROLES:
            continue
        entry = artifacts.get(role, {})
        if not isinstance(receipt, dict):
            problems.append(f"publication receipt for {role} must be an object")
            continue
        try:
            expected_name = publication_name(raw, role)
        except DeliverableContractError as exc:
            problems.append(str(exc))
            expected_name = None
        commit = receipt.get("media_commit_sha")
        repository = raw.get("identity", {}).get("repository")
        expected_url = (
            f"https://raw.githubusercontent.com/{repository}/{commit}/media/{expected_name}"
            if expected_name and isinstance(commit, str) and isinstance(repository, str) else None
        )
        expected_receipt = {
            "schema_version": 1,
            "role": role,
            "run_id": raw.get("identity", {}).get("run_id"),
            "composition": raw.get("identity", {}).get("composition"),
            "manifest_digest": contract_digest(raw),
            "artifact": {
                "path": entry.get("path"), "bytes": entry.get("bytes"), "sha256": entry.get("sha256")
            },
            "media_name": expected_name,
            "media_commit_sha": commit,
            "url": expected_url,
            "verified_bytes": entry.get("bytes"),
            "verified_sha256": entry.get("sha256"),
        }
        for key, wanted in expected_receipt.items():
            if receipt.get(key) != wanted:
                problems.append(f"publication receipt for {role}.{key} is not immutable/current")
        if set(receipt) != set(expected_receipt) | {"verified_at"}:
            problems.append(f"publication receipt fields for {role} are not canonical")
        if not isinstance(commit, str) or not GIT_OID_RE.fullmatch(commit):
            problems.append(f"publication receipt for {role} has invalid media commit SHA")
        name = receipt.get("media_name")
        url = receipt.get("url")
        if isinstance(name, str):
            if name in seen_names and seen_names[name] != role:
                problems.append(f"publication media name collides across {seen_names[name]} and {role}")
            seen_names[name] = role
        if isinstance(url, str):
            if url in seen_urls and seen_urls[url] != role:
                problems.append(f"publication URL collides across {seen_urls[url]} and {role}")
            seen_urls[url] = role
    for role in require_publications:
        if role not in EXPECTED_ROLES:
            problems.append(f"unknown required publication role {role}")
            continue
        receipt = publications.get(role)
        if not isinstance(receipt, dict):
            problems.append(f"publication receipt for {role} is missing")
    return raw, problems


def require_manifest(
    *, root: str | Path = ROOT, require_publications: Iterable[str] = (),
    probe: Callable[[str | Path], dict[str, Any]] | None = None,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    mastering_audio_probe: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    manifest, problems = validate_manifest(
        root=root,
        require_publications=require_publications,
        probe=probe,
        render_probe=render_probe,
        mastering_audio_probe=mastering_audio_probe,
    )
    if problems or manifest is None:
        raise DeliverableContractError("; ".join(problems or ["manifest is unavailable"]))
    return manifest


def role_for_path(path: str | Path, *, root: str | Path = ROOT) -> str:
    base = Path(root).resolve()
    cfg = load_config(root=base)
    target = Path(path)
    target = (base / target).resolve() if not target.is_absolute() else target.resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise DeliverableContractError("upload path is outside the repository") from None
    matches = [
        role for role in EXPECTED_ROLES
        if resolve_inside(base, cfg["roles"][role]["path"], label=f"artifact {role}") == target
    ]
    if len(matches) != 1:
        raise DeliverableContractError("upload path is not one canonical deliverable")
    return matches[0]


def validate_upload(
    path: str | Path, *, role: str | None = None, root: str | Path = ROOT,
) -> tuple[dict[str, Any], str, dict[str, Any]]:
    manifest = require_manifest(root=root)
    actual_role = role_for_path(path, root=root)
    if role is not None and role != actual_role:
        raise DeliverableContractError(f"upload role {role!r} does not match canonical role {actual_role!r}")
    return manifest, actual_role, manifest["artifacts"][actual_role]


def record_publication(
    role: str,
    url: str,
    *,
    remote_bytes: int,
    remote_sha256: str,
    media_name: str,
    media_commit_sha: str,
    root: str | Path = ROOT,
    probe: Callable[[str | Path], dict[str, Any]] | None = None,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    mastering_audio_probe: Callable[..., dict[str, Any]] | None = None,
) -> None:
    base = Path(root).resolve()
    manifest = require_manifest(
        root=base, probe=probe, render_probe=render_probe,
        mastering_audio_probe=mastering_audio_probe,
    )
    if role not in EXPECTED_ROLES:
        raise DeliverableContractError(f"unknown publication role {role}")
    entry = manifest["artifacts"][role]
    if remote_bytes != entry["bytes"] or remote_sha256 != entry["sha256"]:
        raise DeliverableContractError(f"published bytes for {role} do not match the local manifest")
    if not isinstance(url, str) or not url.startswith("https://"):
        raise DeliverableContractError("published URL must use HTTPS")
    expected_name = publication_name(manifest, role)
    if media_name != expected_name:
        raise DeliverableContractError(f"publication name must be immutable canonical name {expected_name}")
    if not isinstance(media_commit_sha, str) or not GIT_OID_RE.fullmatch(media_commit_sha):
        raise DeliverableContractError("media commit SHA must be a full lowercase Git object ID")
    repository = manifest["identity"]["repository"]
    expected_url = (
        f"https://raw.githubusercontent.com/{repository}/{media_commit_sha}/media/{expected_name}"
    )
    if url != expected_url:
        raise DeliverableContractError("published URL must use the immutable media commit SHA")
    publications = manifest.setdefault("publications", {})
    for other_role, receipt in publications.items():
        if other_role != role and isinstance(receipt, dict) and (
            receipt.get("media_name") == media_name or receipt.get("url") == url
        ):
            raise DeliverableContractError(
                f"publication name/URL collision between roles {other_role} and {role}"
            )
    new_receipt = {
        "schema_version": 1,
        "role": role,
        "run_id": manifest["identity"]["run_id"],
        "composition": manifest["identity"]["composition"],
        "manifest_digest": contract_digest(manifest),
        "artifact": {"path": entry["path"], "bytes": entry["bytes"], "sha256": entry["sha256"]},
        "media_name": media_name,
        "media_commit_sha": media_commit_sha,
        "url": url,
        "verified_bytes": remote_bytes,
        "verified_sha256": remote_sha256,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    existing = publications.get(role)
    if isinstance(existing, dict):
        existing_immutable = {key: value for key, value in existing.items() if key != "verified_at"}
        new_immutable = {key: value for key, value in new_receipt.items() if key != "verified_at"}
        if existing_immutable != new_immutable:
            raise DeliverableContractError(
                f"publication receipt for {role} is immutable and already names different media"
            )
        return
    publications[role] = new_receipt
    _atomic_json(manifest_path(root=base), manifest)


def require_publication_url(
    role: str, url: str, *, root: str | Path = ROOT,
    probe: Callable[[str | Path], dict[str, Any]] | None = None,
    render_probe: Callable[[str | Path], dict[str, Any]] = probe_render,
    mastering_audio_probe: Callable[..., dict[str, Any]] | None = None,
    verify_remote: bool = True,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    manifest = require_manifest(
        root=root, require_publications=[role], probe=probe, render_probe=render_probe,
        mastering_audio_probe=mastering_audio_probe,
    )
    receipt = manifest["publications"][role]
    if receipt.get("url") != url:
        raise DeliverableContractError(f"URL for {role} is not the exact verified publication")
    if verify_remote:
        verify_publication_bytes(role, url, root=root, manifest=manifest, opener=opener)
    return receipt


def verify_publication_bytes(
    role: str,
    url: str,
    *,
    root: str | Path = ROOT,
    manifest: dict[str, Any] | None = None,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    """Re-fetch and hash the complete immutable object before any preview consumes it."""
    current = manifest or require_manifest(root=root, require_publications=[role])
    if role not in EXPECTED_ROLES:
        raise DeliverableContractError(f"unknown publication role {role}")
    receipt = current.get("publications", {}).get(role)
    if not isinstance(receipt, dict) or receipt.get("url") != url:
        raise DeliverableContractError(f"publication receipt for {role} is missing or URL-mismatched")
    entry = current["artifacts"][role]
    digest = hashlib.sha256()
    total = 0
    try:
        request = Request(url, headers={"User-Agent": "Alaska-AI-Dispatch-canary-verifier/2"})
        with opener(request, timeout=180) as response:
            status = getattr(response, "status", 200)
            if status != 200:
                raise DeliverableContractError(f"published {role} returned HTTP {status}")
            content_type = response.headers.get("Content-Type", "")
            if content_type.lower().startswith("text/html"):
                raise DeliverableContractError(f"published {role} was served as text/html")
            for chunk in iter(lambda: response.read(1024 * 1024), b""):
                total += len(chunk)
                digest.update(chunk)
    except DeliverableContractError:
        raise
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise DeliverableContractError(f"published {role} full-byte verification failed: {exc}") from None
    remote_sha = digest.hexdigest()
    if total != entry["bytes"] or remote_sha != entry["sha256"]:
        raise DeliverableContractError(
            f"published {role} bytes/hash do not match the manifest artifact"
        )
    return {"bytes": total, "sha256": remote_sha}


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="probe five files and write the immutable manifest")
    check = sub.add_parser("check", help="re-probe and verify the current manifest")
    check.add_argument("--require-published", action="append", default=[])
    facts = sub.add_parser("facts", help="print one file's ffprobe facts")
    facts.add_argument("path")
    args = parser.parse_args()
    try:
        if args.command == "build":
            manifest = build_manifest()
            print(
                f"deliverable_contract: built 5 roles for run_id={manifest['identity']['run_id']} "
                f"digest={contract_digest(manifest)[:16]}"
            )
            return 0
        if args.command == "facts":
            print(json.dumps(probe_media(args.path), indent=2, sort_keys=True))
            return 0
        manifest, problems = validate_manifest(require_publications=args.require_published)
        if problems or manifest is None:
            for problem in problems or ["manifest is unavailable"]:
                print(f"deliverable_contract: FAIL: {problem}", file=sys.stderr)
            return 1
        print(f"deliverable_contract: PASS: five exact artifacts digest={contract_digest(manifest)[:16]}")
        return 0
    except (DeliverableContractError, StrictJSONError, OSError, ValueError) as exc:
        print(f"deliverable_contract: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
