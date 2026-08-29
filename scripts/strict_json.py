#!/usr/bin/env python3
"""Small strict-JSON boundary shared by run and delivery gates."""
from __future__ import annotations

import json
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

    try:
        return json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=reject_constant,
        )
    except StrictJSONError:
        raise
    except (json.JSONDecodeError, TypeError) as exc:
        detail = exc.msg if hasattr(exc, "msg") else str(exc)
        raise StrictJSONError(f"{label} is not valid JSON: {detail}") from None


def load_path(path: str | Path, *, label: str | None = None) -> Any:
    target = Path(path)
    try:
        text = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise StrictJSONError(f"{label or target.name} cannot be read: {exc}") from None
    return loads(text, label=label or target.name)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
