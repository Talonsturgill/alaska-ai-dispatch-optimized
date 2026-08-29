#!/usr/bin/env python3
"""Strict, hash-bound episode timing shared by render, mix, and delivery.

The delivered duration is never inferred from VO length or a media file. It is
`episode_props.json.total / episode_props.json.fps`, and `total` must include the
credits frames after the final story scene. The props bytes must be the bytes
bound into the current run stamp.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from run_guard import ACTIVE_COMPOSITION, check_identity, load_stamp
from strict_json import StrictJSONError, load_path


class EpisodeContractError(RuntimeError):
    pass


def _positive_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EpisodeContractError(f"{label} must be a positive integer")
    return value


def episode_facts(*, root: str | Path) -> dict[str, Any]:
    """Return canonical timing facts from the exact hash-bound props bytes."""
    base = Path(root).resolve()
    ok, reason = check_identity(
        root=base, expected_composition=ACTIVE_COMPOSITION, require_props=True
    )
    if not ok:
        raise EpisodeContractError(f"run identity is invalid: {reason}")
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        raise EpisodeContractError("run stamp is missing or unreadable")
    props_rel = stamp.get("props_path")
    if not isinstance(props_rel, str):
        raise EpisodeContractError("run stamp props_path is invalid")
    props_path = base.joinpath(*props_rel.split("/"))
    try:
        props = load_path(props_path, label="episode props")
    except StrictJSONError as exc:
        raise EpisodeContractError(str(exc)) from None
    if not isinstance(props, dict):
        raise EpisodeContractError("episode props must be a JSON object")

    total = _positive_int(props.get("total"), label="episode props total")
    fps = _positive_int(props.get("fps"), label="episode props fps")
    if fps != 30:
        raise EpisodeContractError("episode props fps must be exactly 30")

    scenes = props.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise EpisodeContractError("episode props scenes must be a non-empty list")
    ends: list[int] = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            raise EpisodeContractError(f"episode scene {index} must be an object")
        start = scene.get("from")
        duration = scene.get("dur")
        if isinstance(start, bool) or not isinstance(start, int) or start < 0:
            raise EpisodeContractError(f"episode scene {index}.from must be a nonnegative integer")
        duration_i = _positive_int(duration, label=f"episode scene {index}.dur")
        ends.append(start + duration_i)
    story_frames = max(ends)

    credits = props.get("credits")
    if not isinstance(credits, dict):
        raise EpisodeContractError("episode props credits must be an object")
    credits_frames = _positive_int(credits.get("frames"), label="episode credits frames")
    credits_seconds = credits.get("seconds")
    if (
        isinstance(credits_seconds, bool)
        or not isinstance(credits_seconds, (int, float))
        or not math.isfinite(float(credits_seconds))
        or float(credits_seconds) <= 0
    ):
        raise EpisodeContractError("episode credits seconds must be a finite positive number")
    if round(float(credits_seconds) * fps) != credits_frames:
        raise EpisodeContractError("episode credits frames do not match credits seconds and fps")
    if total != story_frames + credits_frames:
        raise EpisodeContractError(
            "episode total must equal story frames plus credits frames "
            f"({story_frames}+{credits_frames}, got {total})"
        )

    return {
        "props_path": props_rel,
        "props_sha256": stamp.get("props_sha256"),
        "total_frames": total,
        "story_frames": story_frames,
        "credits_frames": credits_frames,
        "fps": fps,
        "duration_seconds": total / fps,
    }
