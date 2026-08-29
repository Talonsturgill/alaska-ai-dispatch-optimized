#!/usr/bin/env python3
"""Write and verify SFX evidence against exact episode and audio bytes."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
import time
from pathlib import Path
from typing import Any, Iterable

from episode_contract import EpisodeContractError, episode_facts
from run_guard import load_stamp
from strict_json import StrictJSONError, load_path

SCHEMA_VERSION = 3
SIDECAR_REL = "out/dispatch/sfx_events.json"
LEGACY_SIDECAR_REL = "out/dispatch/audio/sfx_events.json"
AUDIO_REL = "out/dispatch/audio/master.wav"
KIND_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EVENT_FIELDS = {
    "t", "planned_t", "kind", "class", "pan", "take", "take_sha256",
    "family", "pitch_cents", "gain_db",
}


class SFXContractError(RuntimeError):
    pass


def _canonical_path(base: Path, relative: str, *, label: str) -> Path:
    logical = base.joinpath(*relative.split("/"))
    current = base
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise SFXContractError(f"{label} path may not contain symlinks")
    resolved = logical.resolve(strict=False)
    try:
        resolved.relative_to(base)
    except ValueError:
        raise SFXContractError(f"{label} path escapes the repository") from None
    return logical


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


def _number(
    event: dict[str, Any], field: str, index: int, problems: list[str],
    *, minimum: float, maximum: float, description: str,
) -> float | None:
    value = event.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        problems.append(f"sfx event {index}.{field} must be {description}")
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        problems.append(f"sfx event {index}.{field} must be {description}")
        return None
    if not math.isfinite(result) or not minimum <= result <= maximum:
        problems.append(f"sfx event {index}.{field} must be {description}")
        return None
    return result


def _take_path(base: Path, relative: Any, *, index: int) -> tuple[Path | None, str | None]:
    label = f"sfx event {index}.take"
    if (
        not isinstance(relative, str)
        or not relative
        or not relative.isascii()
        or "\\" in relative
        or relative.startswith("/")
        or re.match(r"^[A-Za-z]:", relative)
        or any(part in {"", ".", ".."} for part in relative.split("/"))
        or not relative.startswith("assets/sfx/")
    ):
        return None, f"{label} must be a canonical repo-relative POSIX assets/sfx path"
    try:
        path = _canonical_path(base, relative, label=label)
    except SFXContractError as exc:
        return None, str(exc)
    if not path.is_file() or path.is_symlink():
        return None, f"{label} is missing or unsafe"
    return path, None


def _normalize_events(
    events: Iterable[Any], duration: float, *, base: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    normalized: list[dict[str, Any]] = []
    problems: list[str] = []
    for index, raw in enumerate(events):
        if not isinstance(raw, dict):
            problems.append(f"sfx event {index} must be an enriched event object")
            continue
        event = dict(raw)
        unknown = set(event) - EVENT_FIELDS
        missing = EVENT_FIELDS - set(event)
        if unknown or missing:
            problems.append(
                f"sfx event {index} fields are not canonical"
                + (f"; unknown={sorted(unknown)}" if unknown else "")
                + (f"; missing={sorted(missing)}" if missing else "")
            )
        when = event.get("t")
        kind = event.get("kind")
        numeric_when = _number(
            event, "t", index, problems, minimum=0.0,
            maximum=math.nextafter(duration, -math.inf),
            description="finite and within the delivered duration",
        )
        planned_when = _number(
            event, "planned_t", index, problems, minimum=0.0,
            maximum=math.nextafter(duration, -math.inf),
            description="finite and within the delivered duration",
        )
        if not isinstance(kind, str) or not kind.isascii() or not KIND_RE.fullmatch(kind):
            problems.append(f"sfx event {index}.kind must be a lowercase ASCII identifier")
        event_class = event.get("class")
        if (
            not isinstance(event_class, str)
            or event_class not in {"hero", "standard", "texture"}
        ):
            problems.append(f"sfx event {index}.class is not canonical")
        numeric_pan = _number(
            event, "pan", index, problems, minimum=-1.0, maximum=1.0,
            description="finite in -1..1",
        )
        pitch_cents = _number(
            event, "pitch_cents", index, problems, minimum=-1200.0, maximum=1200.0,
            description="finite in -1200..1200",
        )
        gain_db = _number(
            event, "gain_db", index, problems, minimum=-96.0, maximum=24.0,
            description="finite in -96..24",
        )
        family = event.get("family")
        if not isinstance(family, str) or not family.isascii() or not KIND_RE.fullmatch(family):
            problems.append(f"sfx event {index}.family must be a lowercase ASCII identifier")
        take, take_problem = _take_path(base, event.get("take"), index=index)
        if take_problem:
            problems.append(take_problem)
        take_sha = event.get("take_sha256")
        if not isinstance(take_sha, str) or not SHA256_RE.fullmatch(take_sha):
            problems.append(f"sfx event {index}.take_sha256 must be a lowercase SHA-256")
        elif take is not None and sha256_file(take) != take_sha:
            problems.append(f"sfx event {index}.take_sha256 does not match the resolved take")
        clean = {
            "t": numeric_when if numeric_when is not None else when,
            "planned_t": planned_when if planned_when is not None else event.get("planned_t"),
            "kind": kind,
            "class": event_class,
            "pan": numeric_pan if numeric_pan is not None else event.get("pan"),
            "take": event.get("take"),
            "take_sha256": take_sha,
            "family": family,
            "pitch_cents": pitch_cents if pitch_cents is not None else event.get("pitch_cents"),
            "gain_db": gain_db if gain_db is not None else event.get("gain_db"),
        }
        normalized.append(clean)
    return normalized, problems


def write_sidecar(
    master: str | Path,
    events: Iterable[Any],
    *,
    root: str | Path,
) -> dict[str, Any]:
    base = Path(root).resolve()
    legacy = _canonical_path(base, LEGACY_SIDECAR_REL, label="legacy sfx sidecar")
    if legacy.exists():
        if legacy.is_symlink() or not legacy.is_file():
            raise SFXContractError(f"legacy {LEGACY_SIDECAR_REL} is unsafe; remove it")
        legacy.unlink()
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        raise SFXContractError("run stamp is missing or unreadable")
    try:
        episode = episode_facts(root=base)
    except EpisodeContractError as exc:
        raise SFXContractError(str(exc)) from None
    canonical_audio = _canonical_path(base, AUDIO_REL, label="audio master")
    audio = Path(master)
    audio = (base / audio) if not audio.is_absolute() else audio
    if audio.resolve(strict=False) != canonical_audio.resolve(strict=False):
        raise SFXContractError(f"audio master must use canonical path {AUDIO_REL}")
    audio = canonical_audio
    if not audio.is_file() or audio.is_symlink():
        raise SFXContractError("audio master is missing or unsafe")
    if audio.stat().st_mtime <= float(stamp["started_at"]):
        raise SFXContractError("audio master does not postdate the run stamp")
    normalized, problems = _normalize_events(events, episode["duration_seconds"], base=base)
    if len(normalized) < 6:
        problems.append(f"sfx schedule carries {len(normalized)} event(s); at least 6 are required")
    if problems:
        raise SFXContractError("; ".join(problems))
    payload = {
        "schema_version": SCHEMA_VERSION,
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "episode": episode,
        "video_seconds": episode["duration_seconds"],
        "count": len(normalized),
        "kinds": sorted({event["kind"] for event in normalized}),
        "audio": {
            "path": AUDIO_REL,
            "bytes": audio.stat().st_size,
            "sha256": sha256_file(audio),
        },
        "events": normalized,
    }
    target = _canonical_path(base, SIDECAR_REL, label="sfx sidecar")
    _atomic_json(target, payload)
    audio_ns = audio.stat().st_mtime_ns
    # Filesystems exposed through Windows/OneDrive can round nanosecond utime
    # values.  Give the sidecar a full-second ordering margin so the producer
    # never writes a receipt that its own stale-sidecar validator rejects.
    sidecar_ns = max(time.time_ns(), audio_ns) + 1_000_000_000
    os.utime(target, ns=(sidecar_ns, sidecar_ns))
    return payload


def sidecar_facts(
    path: str | Path | None = None,
    *,
    root: str | Path,
) -> tuple[dict[str, Any] | None, list[str]]:
    base = Path(root).resolve()
    try:
        canonical = _canonical_path(base, SIDECAR_REL, label="sfx sidecar")
    except SFXContractError as exc:
        return None, [str(exc)]
    if path is not None:
        supplied = Path(path)
        supplied = (base / supplied) if not supplied.is_absolute() else supplied
        try:
            if supplied.resolve(strict=False) != canonical.resolve(strict=False):
                return None, ["sfx_events.json path must use the canonical current-run location"]
        except OSError as exc:
            return None, [f"sfx_events.json path cannot be resolved: {exc}"]
    target = canonical
    problems: list[str] = []
    try:
        legacy = _canonical_path(base, LEGACY_SIDECAR_REL, label="legacy sfx sidecar")
    except SFXContractError as exc:
        return None, [str(exc)]
    if legacy.exists():
        problems.append(
            f"legacy {LEGACY_SIDECAR_REL} is forbidden; only {SIDECAR_REL} is canonical"
        )
    try:
        target.relative_to(base)
    except ValueError:
        return None, ["sfx_events.json path escapes the repository"]
    if target.is_symlink():
        return None, ["sfx_events.json may not be a symlink"]
    if not target.is_file():
        return None, ["no out/dispatch/sfx_events.json"]
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        return None, ["run stamp is missing or unreadable"]
    if target.stat().st_mtime <= float(stamp.get("started_at", float("inf"))):
        problems.append("sfx_events.json does not postdate the current run stamp")
    try:
        episode = episode_facts(root=base)
        raw = load_path(target, label="sfx_events.json")
    except (EpisodeContractError, StrictJSONError, OSError) as exc:
        return None, problems + [str(exc)]
    if not isinstance(raw, dict):
        return None, problems + ["sfx_events.json must be an object with an events list"]
    expected_fields = {
        "schema_version", "run_id", "run_date", "composition", "episode",
        "video_seconds", "count", "kinds", "audio", "events",
    }
    if set(raw) != expected_fields:
        problems.append("sfx_events.json fields are not canonical")
    for key, wanted in (
        ("schema_version", SCHEMA_VERSION),
        ("run_id", stamp.get("run_id")),
        ("run_date", stamp.get("date")),
        ("composition", stamp.get("composition")),
        ("episode", episode),
        ("video_seconds", episode["duration_seconds"]),
    ):
        if raw.get(key) != wanted:
            problems.append(f"sfx_events.json {key} does not match the current run")
    events = raw.get("events")
    if not isinstance(events, list):
        return None, problems + ["sfx_events.json.events must be a list"]
    normalized, event_problems = _normalize_events(
        events, episode["duration_seconds"], base=base,
    )
    problems.extend(event_problems)
    if len(events) < 6:
        problems.append(f"sfx_events.json carries {len(events)} event(s); at least 6 are required")
    if isinstance(raw.get("count"), bool) or raw.get("count") != len(events):
        problems.append("sfx_events.json count does not match events")
    kinds = sorted({event.get("kind") for event in normalized if isinstance(event.get("kind"), str)})
    if raw.get("kinds") != kinds:
        problems.append("sfx_events.json kinds must exactly match the sorted event kinds")

    try:
        audio = _canonical_path(base, AUDIO_REL, label="audio master")
    except SFXContractError as exc:
        audio = base.joinpath(*AUDIO_REL.split("/"))
        problems.append(str(exc))
    if not audio.is_file() or audio.is_symlink():
        current_audio = None
        problems.append("current audio master is missing or unsafe")
    else:
        current_audio = {
            "path": AUDIO_REL,
            "bytes": audio.stat().st_size,
            "sha256": sha256_file(audio),
        }
        if audio.stat().st_mtime <= float(stamp["started_at"]):
            problems.append("audio master does not postdate the current run stamp")
        if target.stat().st_mtime <= audio.stat().st_mtime:
            problems.append("sfx_events.json does not postdate the audio master it describes")
    if raw.get("audio") != current_audio:
        problems.append("sfx_events.json audio facts do not match the current audio master")
    facts = {
        "path": SIDECAR_REL,
        "sha256": sha256_file(target),
        "run_id": stamp["run_id"],
        "run_date": stamp["date"],
        "composition": stamp["composition"],
        "episode": episode,
        "count": len(events),
        "kinds": kinds,
        "first_seconds": min(
            (event["t"] for event in normalized if isinstance(event.get("t"), float)),
            default=None,
        ),
        "last_seconds": max(
            (event["t"] for event in normalized if isinstance(event.get("t"), float)),
            default=None,
        ),
        "audio": current_audio,
    }
    return facts, problems
