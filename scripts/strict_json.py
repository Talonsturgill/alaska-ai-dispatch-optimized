#!/usr/bin/env python3
"""Small strict-JSON boundary shared by run and delivery gates."""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


class StrictJSONError(ValueError):
    pass


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise StrictJSONError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def loads(text: str, *, label: str = "JSON") -> Any:
    def reject_constant(token: str) -> None:
        raise StrictJSONError(f"{label} contains non-finite number {token}")

    def finite_float(token: str) -> float:
        try:
            value = float(token)
        except (ValueError, OverflowError):
            raise StrictJSONError(f"{label} contains invalid number {token!r}") from None
        if not math.isfinite(value):
            raise StrictJSONError(f"{label} contains non-finite number {token}")
        return value

    def strict_int(token: str) -> int:
        try:
            return int(token)
        except (ValueError, OverflowError):
            raise StrictJSONError(f"{label} contains invalid integer") from None

    try:
        return json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=reject_constant,
            parse_float=finite_float,
            parse_int=strict_int,
        )
    except StrictJSONError:
        raise
    except (json.JSONDecodeError, TypeError, ValueError, OverflowError, RecursionError, UnicodeError) as exc:
        detail = exc.msg if hasattr(exc, "msg") else str(exc)
        raise StrictJSONError(f"{label} is not valid JSON: {detail}") from None


def load_path(path: str | Path, *, label: str | None = None) -> Any:
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise StrictJSONError(f"{label or target.name} cannot be read: {exc}") from None
    return loads(text, label=label or target.name)


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError, UnicodeError) as exc:
        raise StrictJSONError(f"value cannot be represented as canonical JSON: {exc}") from None
