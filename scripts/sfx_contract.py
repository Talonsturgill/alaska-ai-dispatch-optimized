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

SCHEMA_VERSION = 2
SIDECAR_REL = "out/dispatch/sfx_events.json"
AUDIO_REL = "out/dispatch/audio/master.wav"
KIND_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
EVENT_FIELDS = {"t", "kind", "class", "pan", "take", "family"}


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


def _normalize_events(events: Iterable[Any], duration: float) -> tuple[list[dict[str, Any]], list[str]]:
    normalized: list[dict[str, Any]] = []
    problems: list[str] = []
    for index, raw in enumerate(events):
        if isinstance(raw, dict):
            event = dict(raw)
        elif isinstance(raw, (tuple, list)) and 2 <= len(raw) <= 4:
            event = {"t": raw[0], "kind": raw[1]}
            if len(raw) > 2:
                event["class"] = raw[2]
            if len(raw) > 3:
                event["pan"] = raw[3]
        else:
            problems.append(f"sfx event {index} must be an object or a 2-to-4-field event tuple")
            continue
        unknown = set(event) - EVENT_FIELDS
        missing = {"t", "kind"} - set(event)
        if unknown or missing:
            problems.append(
                f"sfx event {index} fields are not canonical"
                + (f"; unknown={sorted(unknown)}" if unknown else "")
                + (f"; missing={sorted(missing)}" if missing else "")
            )
        when = event.get("t")
        kind = event.get("kind")
        numeric_when: float | None = None
        if isinstance(when, bool) or not isinstance(when, (int, float)):
            problems.append(f"sfx event {index}.t must be a finite number")
        else:
            try:
                numeric_when = float(when)
            except (TypeError, ValueError, OverflowError):
                problems.append(f"sfx event {index}.t must be a finite number")
            else:
                if not math.isfinite(numeric_when):
                    problems.append(f"sfx event {index}.t must be a finite number")
                elif numeric_when < 0 or numeric_when >= duration:
                    problems.append(f"sfx event {index}.t must be within the delivered duration")
        if not isinstance(kind, str) or not kind.isascii() or not KIND_RE.fullmatch(kind):
            problems.append(f"sfx event {index}.kind must be a lowercase ASCII identifier")
        event_class = event.get("class")
        if event_class is not None and (
            not isinstance(event_class, str)
            or event_class not in {"hero", "standard", "texture"}
        ):
            problems.append(f"sfx event {index}.class is not canonical")
        pan = event.get("pan")
        if pan is not None:
            try:
                numeric_pan = float(pan)
            except (TypeError, ValueError, OverflowError):
                numeric_pan = float("nan")
            if (
                isinstance(pan, bool) or not isinstance(pan, (int, float))
                or not math.isfinite(numeric_pan) or not -1 <= numeric_pan <= 1
            ):
                problems.append(f"sfx event {index}.pan must be finite in -1..1")
        for field in ("take", "family"):
            value = event.get(field)
            if value is not None and (
                not isinstance(value, str) or not value or not value.isascii()
                or any(ord(char) < 0x20 or ord(char) == 0x7F for char in value)
            ):
                problems.append(f"sfx event {index}.{field} must be non-empty printable ASCII")
        clean = {"t": numeric_when if numeric_when is not None else when, "kind": kind}
        for optional in ("class", "pan", "take", "family"):
            if optional in event:
                clean[optional] = event[optional]
        normalized.append(clean)
    return normalized, problems


def write_sidecar(
    master: str | Path,
    events: Iterable[Any],
    *,
    root: str | Path,
) -> dict[str, Any]:
    base = Path(root).resolve()
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
    normalized, problems = _normalize_events(events, episode["duration_seconds"])
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
    normalized, event_problems = _normalize_events(events, episode["duration_seconds"])
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
        "first_seconds": min((event["t"] for event in normalized if isinstance(event.get("t"), float)), default=None),
        "last_seconds": max((event["t"] for event in normalized if isinstance(event.get("t"), float)), default=None),
        "audio": current_audio,
    }
    return facts, problems
