#!/usr/bin/env python3
"""Fail-closed Python boundary for schema-v2 DispatchDaily authoring output."""
from __future__ import annotations

import datetime as dt
import math
import re
from typing import Any
from urllib.parse import urlparse


class ParametricEpisodeError(RuntimeError):
    pass


ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$")
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
TOP_KEYS = {
    "schemaVersion", "episode", "fps", "total", "safeZones", "palette",
    "assets", "sources", "scenes", "captions", "wordTimings", "credits",
}
SAFE_ZONES = {
    "squareTop": 420, "squareBottom": 1500, "actionLeft": 72,
    "actionRight": 1008, "captionTop": 1328, "captionBottom": 1484,
}
PRIMITIVES = {
    "metric", "comparison", "timeline", "process", "document", "quote",
    "location", "closing",
}
GLYPHS = {"generator", "battery", "document", "pin", "people", "network", "clock", "spark"}


def _object(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ParametricEpisodeError(f"{label} has unknown or missing fields")
    return value


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise ParametricEpisodeError(f"{label} must be a lowercase canonical ID")
    return value


def _text(value: Any, minimum: int, maximum: int, label: str) -> str:
    if not isinstance(value, str) or value != value.strip() or not minimum <= len(value) <= maximum:
        raise ParametricEpisodeError(f"{label} must be a trimmed {minimum}-{maximum} character string")
    return value


def _integer(value: Any, minimum: int, maximum: int, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ParametricEpisodeError(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _number(value: Any, minimum: float, maximum: float, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ParametricEpisodeError(f"{label} must be a finite number")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ParametricEpisodeError(f"{label} must be from {minimum} through {maximum}")
    return number


def _ids(values: Any, maximum: int, label: str) -> list[str]:
    if not isinstance(values, list) or len(values) > maximum:
        raise ParametricEpisodeError(f"{label} must be a list with at most {maximum} IDs")
    result = [_id(value, f"{label}[{index}]") for index, value in enumerate(values)]
    if len(result) != len(set(result)):
        raise ParametricEpisodeError(f"{label} contains duplicate IDs")
    return result


def validate_parametric_episode(
    props: Any, storyboard: Any, *, expected_fps: int = 30,
    minimum_seconds: int = 112, maximum_seconds: int = 130,
) -> dict[str, Any]:
    value = _object(props, TOP_KEYS, "episode props")
    if value["schemaVersion"] != 2:
        raise ParametricEpisodeError("episode props schemaVersion must be exactly 2")
    if value["fps"] != expected_fps:
        raise ParametricEpisodeError("episode props fps must equal the 30 fps daily contract")
    total = _integer(value["total"], minimum_seconds * expected_fps,
                     maximum_seconds * expected_fps, "episode props total")
    if value["safeZones"] != SAFE_ZONES:
        raise ParametricEpisodeError("episode props safeZones must preserve the canonical square/mobile crop")

    episode = _object(value["episode"], {"id", "date", "title", "subtitle", "provenance", "motion"}, "episode")
    _id(episode["id"], "episode.id")
    _text(episode["date"], 10, 10, "episode.date")
    try:
        valid_date = dt.date.fromisoformat(episode["date"]).isoformat() == episode["date"]
    except ValueError:
        valid_date = False
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", episode["date"]) or not valid_date:
        raise ParametricEpisodeError("episode.date must be YYYY-MM-DD")
    _text(episode["title"], 6, 72, "episode.title")
    _text(episode["subtitle"], 8, 120, "episode.subtitle")
    provenance = _object(episode["provenance"], {"kind", "notice"}, "episode.provenance")
    if provenance["kind"] not in {"historical_reconstruction", "synthetic_canary"}:
        raise ParametricEpisodeError("episode provenance kind is invalid")
    _text(provenance["notice"], 12, 180, "episode.provenance.notice")
    if episode["motion"] not in {"full", "reduced"}:
        raise ParametricEpisodeError("episode.motion must be full or reduced")

    palette = _object(value["palette"], {"ink", "paper", "accent", "signal"}, "palette")
    if any(not isinstance(color, str) or not COLOR_RE.fullmatch(color) for color in palette.values()):
        raise ParametricEpisodeError("palette values must be six-digit hex colors")

    assets = value["assets"]
    if not isinstance(assets, list) or len(assets) > 16:
        raise ParametricEpisodeError("assets must contain at most 16 semantic symbols")
    asset_ids: set[str] = set()
    for index, raw in enumerate(assets):
        allowed = {"id", "kind", "glyph", "alt"} | ({"credit"} if isinstance(raw, dict) and "credit" in raw else set())
        asset = _object(raw, allowed, f"assets[{index}]")
        asset_id = _id(asset["id"], f"assets[{index}].id")
        if asset_id in asset_ids:
            raise ParametricEpisodeError("asset IDs must be unique")
        asset_ids.add(asset_id)
        if asset["kind"] != "symbol" or asset["glyph"] not in GLYPHS:
            raise ParametricEpisodeError(f"assets[{index}] must be a supported semantic symbol")
        _text(asset["alt"], 4, 120, f"assets[{index}].alt")
        if "credit" in asset:
            _text(asset["credit"], 2, 120, f"assets[{index}].credit")

    sources = value["sources"]
    if not isinstance(sources, list) or len(sources) > 12:
        raise ParametricEpisodeError("sources must contain at most 12 records")
    source_ids: set[str] = set()
    for index, raw in enumerate(sources):
        source = _object(raw, {"id", "label", "url", "claimIds"}, f"sources[{index}]")
        source_id = _id(source["id"], f"sources[{index}].id")
        if source_id in source_ids:
            raise ParametricEpisodeError("source IDs must be unique")
        source_ids.add(source_id)
        _text(source["label"], 4, 110, f"sources[{index}].label")
        parsed = urlparse(source["url"] if isinstance(source["url"], str) else "")
        if parsed.scheme != "https" or not parsed.netloc:
            raise ParametricEpisodeError(f"sources[{index}].url must be an HTTPS URL")
        _ids(source["claimIds"], 24, f"sources[{index}].claimIds")

    credits = _object(value["credits"], {"frames", "seconds", "music", "sources", "sourceIds", "site"}, "credits")
    credits_frames = _integer(credits["frames"], 360, 450, "credits.frames")
    credits_seconds = _number(credits["seconds"], 12, 15, "credits.seconds")
    if round(credits_seconds * expected_fps) != credits_frames:
        raise ParametricEpisodeError("credits seconds and frames disagree")
    _text(credits["music"], 4, 140, "credits.music")
    if not isinstance(credits["sources"], list) or not 1 <= len(credits["sources"]) <= 6:
        raise ParametricEpisodeError("credits.sources must contain 1-6 readable labels")
    for index, label in enumerate(credits["sources"]):
        _text(label, 4, 110, f"credits.sources[{index}]")
    credit_source_ids = _ids(credits["sourceIds"], 12, "credits.sourceIds")
    if not set(credit_source_ids).issubset(source_ids):
        raise ParametricEpisodeError("credits reference an unknown source")
    if credits["site"] != "alaskaaihq.com":
        raise ParametricEpisodeError("credits.site must be alaskaaihq.com")

    scenes = value["scenes"]
    if not isinstance(scenes, list) or not 6 <= len(scenes) <= 16:
        raise ParametricEpisodeError("scenes must contain 6-16 records")
    scene_ids: list[str] = []
    next_frame = 0
    for index, raw in enumerate(scenes):
        required = {"id", "from", "dur", "primitive", "eyebrow", "title", "body", "labels", "sourceIds"}
        optional = {name for name in ("primaryValue", "secondaryValue", "assetId", "accent") if isinstance(raw, dict) and name in raw}
        scene = _object(raw, required | optional, f"scenes[{index}]")
        scene_id = _id(scene["id"], f"scenes[{index}].id")
        if scene_id in scene_ids:
            raise ParametricEpisodeError("scene IDs must be unique")
        scene_ids.append(scene_id)
        start = _integer(scene["from"], 0, total, f"scenes[{index}].from")
        duration = _integer(scene["dur"], 1, total, f"scenes[{index}].dur")
        if start != next_frame:
            raise ParametricEpisodeError(f"scenes[{index}] must start at contiguous frame {next_frame}")
        next_frame = start + duration
        if scene["primitive"] not in PRIMITIVES:
            raise ParametricEpisodeError(f"scenes[{index}].primitive is unsupported")
        _text(scene["eyebrow"], 2, 34, f"scenes[{index}].eyebrow")
        _text(scene["title"], 4, 68, f"scenes[{index}].title")
        _text(scene["body"], 8, 118, f"scenes[{index}].body")
        if not isinstance(scene["labels"], list) or not 1 <= len(scene["labels"]) <= 4:
            raise ParametricEpisodeError(f"scenes[{index}].labels must contain 1-4 values")
        for label_index, label in enumerate(scene["labels"]):
            _text(label, 1, 36, f"scenes[{index}].labels[{label_index}]")
        refs = _ids(scene["sourceIds"], 8, f"scenes[{index}].sourceIds")
        if not set(refs).issubset(source_ids):
            raise ParametricEpisodeError(f"scenes[{index}] references an unknown source")
        if "assetId" in scene and _id(scene["assetId"], f"scenes[{index}].assetId") not in asset_ids:
            raise ParametricEpisodeError(f"scenes[{index}] references an unknown asset")
        if "accent" in scene and (not isinstance(scene["accent"], str) or not COLOR_RE.fullmatch(scene["accent"])):
            raise ParametricEpisodeError(f"scenes[{index}].accent must be a hex color")
        for field, maximum in (("primaryValue", 32), ("secondaryValue", 42)):
            if field in scene:
                _text(scene[field], 1, maximum, f"scenes[{index}].{field}")
    if next_frame + credits_frames != total:
        raise ParametricEpisodeError("scenes must end exactly where credits begin")

    if provenance["kind"] == "historical_reconstruction":
        if not sources or any(not scene["sourceIds"] for scene in scenes):
            raise ParametricEpisodeError("historical scenes require declared source bindings")
    elif sources or credit_source_ids or any(scene["sourceIds"] for scene in scenes):
        raise ParametricEpisodeError("synthetic canaries may not masquerade as sourced history")

    captions = value["captions"]
    if not isinstance(captions, list) or not 1 <= len(captions) <= 80:
        raise ParametricEpisodeError("captions must contain 1-80 cues")
    story_seconds = next_frame / expected_fps
    prior_end = 0.0
    for index, raw in enumerate(captions):
        caption = _object(raw, {"t", "d", "text"}, f"captions[{index}]")
        start = _number(caption["t"], 0, story_seconds, f"captions[{index}].t")
        duration = _number(caption["d"], 0.000001, 8, f"captions[{index}].d")
        text = _text(caption["text"], 1, 84, f"captions[{index}].text")
        if start < prior_end - 1e-6 or start + duration > story_seconds + 1e-6:
            raise ParametricEpisodeError("captions must be ordered, non-overlapping, and stay before credits")
        rows, row = [], ""
        for word in text.split():
            if len(word) > 26:
                raise ParametricEpisodeError("caption words must fit the phone-safe line width")
            candidate = f"{row} {word}".strip()
            if len(candidate) > 42 and row:
                rows.append(row)
                row = word
            else:
                row = candidate
        if row:
            rows.append(row)
        if len(rows) > 2:
            raise ParametricEpisodeError("captions must fit at most two phone-safe rows")
        prior_end = start + duration

    words = value["wordTimings"]
    if not isinstance(words, list) or not 1 <= len(words) <= 600:
        raise ParametricEpisodeError("wordTimings must contain 1-600 records")
    prior_end = 0.0
    for index, raw in enumerate(words):
        word = _object(raw, {"word", "start", "end", "lineId"}, f"wordTimings[{index}]")
        _text(word["word"], 1, 48, f"wordTimings[{index}].word")
        start = _number(word["start"], 0, story_seconds, f"wordTimings[{index}].start")
        end = _number(word["end"], 0.000001, story_seconds, f"wordTimings[{index}].end")
        _id(word["lineId"], f"wordTimings[{index}].lineId")
        if start < prior_end - 1e-6 or end <= start:
            raise ParametricEpisodeError("word timings must be ordered, non-overlapping, and positive")
        prior_end = end

    if not isinstance(storyboard, dict) or not isinstance(storyboard.get("shots"), list):
        raise ParametricEpisodeError("storyboard must be an object with a shots list")
    shot_ids = [shot.get("id") for shot in storyboard["shots"] if isinstance(shot, dict)]
    if shot_ids != scene_ids:
        raise ParametricEpisodeError("storyboard shot IDs must exactly match episode scene IDs in order")

    return {
        "schema_version": 2,
        "composition": "DispatchDaily",
        "total_frames": total,
        "story_frames": next_frame,
        "credits_frames": credits_frames,
        "scene_count": len(scenes),
        "source_count": len(sources),
    }
