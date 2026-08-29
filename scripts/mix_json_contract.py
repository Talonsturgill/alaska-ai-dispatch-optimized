#!/usr/bin/env python3
"""Strict JSON boundaries for required dispatch_mix inputs."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from strict_json import StrictJSONError, load_path, loads


class MixInputError(RuntimeError):
    pass


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MixInputError(f"{label} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise MixInputError(f"{label} must be a finite number")
    return number


def load_vo_lines(path: str | Path) -> list[dict[str, Any]]:
    try:
        value = load_path(path, label="dispatch mix VO lines")
    except (StrictJSONError, OSError) as exc:
        raise MixInputError(str(exc)) from None
    if not isinstance(value, dict) or set(value) != {"lines"} or not isinstance(value["lines"], list):
        raise MixInputError("dispatch mix VO lines must be an object with only a lines list")
    for index, line in enumerate(value["lines"]):
        if not isinstance(line, dict) or not {"idx", "start", "end"}.issubset(line):
            raise MixInputError(f"dispatch mix VO line {index} is not canonical")
        if isinstance(line["idx"], bool) or not isinstance(line["idx"], int) or line["idx"] < 0:
            raise MixInputError(f"dispatch mix VO line {index}.idx must be nonnegative integer")
        start = _finite(line["start"], f"dispatch mix VO line {index}.start")
        end = _finite(line["end"], f"dispatch mix VO line {index}.end")
        if start < 0 or end < start:
            raise MixInputError(f"dispatch mix VO line {index} timing is invalid")
    return value["lines"]


def load_words(path: str | Path) -> list[dict[str, Any]]:
    try:
        value = load_path(path, label="dispatch mix aligned words")
    except (StrictJSONError, OSError) as exc:
        raise MixInputError(str(exc)) from None
    if not isinstance(value, dict) or set(value) != {"words"} or not isinstance(value["words"], list):
        raise MixInputError("dispatch mix aligned words must be an object with only a words list")
    for index, word in enumerate(value["words"]):
        if not isinstance(word, dict) or not {"s", "e"}.issubset(word):
            raise MixInputError(f"dispatch mix aligned word {index} is not canonical")
        start = _finite(word["s"], f"dispatch mix aligned word {index}.s")
        end = _finite(word["e"], f"dispatch mix aligned word {index}.e")
        if start < 0 or end < start:
            raise MixInputError(f"dispatch mix aligned word {index} timing is invalid")
    return value["words"]


def load_loudnorm(text: str) -> dict[str, Any]:
    try:
        value = loads(text, label="dispatch mix loudnorm analysis")
    except StrictJSONError as exc:
        raise MixInputError(str(exc)) from None
    required = {
        "input_i", "input_tp", "input_lra", "input_thresh", "target_offset",
    }
    if not isinstance(value, dict) or not required.issubset(value):
        raise MixInputError("dispatch mix loudnorm analysis is missing required fields")
    for field in required:
        try:
            number = float(value[field])
        except (TypeError, ValueError, OverflowError):
            raise MixInputError(f"dispatch mix loudnorm {field} is not finite") from None
        if not math.isfinite(number):
            raise MixInputError(f"dispatch mix loudnorm {field} is not finite")
    return value
