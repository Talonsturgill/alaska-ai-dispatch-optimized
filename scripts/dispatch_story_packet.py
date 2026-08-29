#!/usr/bin/env python3
"""Build the bounded, source-hashed story packet used by the daily controller."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from strict_json import StrictJSONError, load_path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_REL = "config/daily_controller.json"
OUTPUT_REL = "out/dispatch/dispatch_story_packet.json"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PACKET_KEYS = {
    "schema_version", "run_date", "mode", "story", "claims", "sources",
    "research", "provenance", "measurement",
}
CLAIM_KEYS = {
    "id", "claim", "source_url", "source_outlet", "source_is_primary",
    "fetched", "date_of_source", "confidence", "notes",
}


class PacketError(RuntimeError):
    """A packet input or output violates the compact contract."""


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _render(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def estimate_tokens_bytes(data: bytes) -> int:
    """Deterministic, tokenizer-independent upper planning estimate."""
    return int(math.ceil(len(data) / 4.0))


def estimate_tokens_text(text: str) -> int:
    return estimate_tokens_bytes(text.encode("utf-8"))


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(_render(value))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def _date(value: str) -> str:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        raise PacketError("run date must be YYYY-MM-DD")
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError:
        raise PacketError("run date is not a real calendar date") from None
    if parsed.isoformat() != value:
        raise PacketError("run date is not canonical")
    return value


def _config(root: Path) -> dict[str, Any]:
    value = load_path(root / CONFIG_REL, label="daily controller config")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise PacketError("daily controller config must be a schema-v1 object")
    story = value.get("story_packet")
    if not isinstance(story, dict):
        raise PacketError("daily controller config is missing story_packet")
    return value


def _text(value: Any, *, label: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise PacketError(f"{label} must be a string")
    compact = re.sub(r"\s+", " ", value).strip()
    if not compact:
        raise PacketError(f"{label} must not be empty")
    if len(compact) > maximum:
        compact = compact[: maximum - 1].rstrip() + "…"
    return compact


def _url(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or value != value.strip():
        raise PacketError(f"{label} must be a canonical HTTPS URL")
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise PacketError(f"{label} must be a public HTTPS URL")
    return value


def _claim(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PacketError("each claim must be an object")
    required = {
        "id", "claim", "source_url", "source_outlet", "source_is_primary",
        "fetched", "date_of_source", "confidence",
    }
    missing = sorted(required - set(value))
    if missing:
        raise PacketError("claim is missing: " + ", ".join(missing))
    primary = value["source_is_primary"]
    confidence = value["confidence"]
    if not isinstance(primary, bool):
        raise PacketError("claim source_is_primary must be boolean")
    if value["fetched"] is not True:
        raise PacketError("claim fetched must be true; unfetched claims cannot enter the packet")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise PacketError("claim confidence must be numeric")
    confidence = float(confidence)
    if not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise PacketError("claim confidence must be finite and between zero and one")
    date_of_source = value["date_of_source"]
    if not isinstance(date_of_source, str):
        raise PacketError("claim date_of_source must be a string")
    return {
        "id": _text(value["id"], label="claim id", maximum=80),
        "claim": _text(value["claim"], label="claim text", maximum=560),
        "source_url": _url(value["source_url"], label="claim source_url"),
        "source_outlet": _text(value["source_outlet"], label="claim source_outlet", maximum=120),
        "source_is_primary": primary,
        "fetched": True,
        "date_of_source": date_of_source.strip(),
        "confidence": round(confidence, 4),
        "notes": _text(value.get("notes", "No additional note."), label="claim notes", maximum=260),
    }


def _section(markdown: str, title: str, maximum: int) -> str:
    pattern = re.compile(
        rf"(?ims)^##\s+{re.escape(title)}[^\n]*\n(?P<body>.*?)(?=^##\s+|\Z)"
    )
    match = pattern.search(markdown)
    if not match:
        return ""
    body = re.sub(r"[`*_>#]", "", match.group("body"))
    return re.sub(r"\s+", " ", body).strip()[:maximum].rstrip()


def _headline(selection: str) -> str:
    story = _section(selection, "THE STORY", 900)
    if not story:
        raise PacketError("selection.md is missing a THE STORY section")
    first = re.split(r"(?<=[.!?])\s+", story, maxsplit=1)[0]
    return _text(first, label="selected story", maximum=420)


def _fact_pack(run_dir: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    story_cfg = config["story_packet"]
    names = story_cfg["required_carousel_files"]
    if not isinstance(names, list) or any(not isinstance(item, str) for item in names):
        raise PacketError("required_carousel_files must be a string list")
    paths = {name: run_dir / name for name in names}
    if not all(path.is_file() for path in paths.values()):
        return None
    selection = paths["selection.md"].read_text(encoding="utf-8")
    scout = paths["scout_merge.md"].read_text(encoding="utf-8")
    raw_claims = load_path(paths["claims.json"], label="Carousel claims")
    run_state = load_path(paths["run_state.json"], label="Carousel run state")
    if not isinstance(raw_claims, dict) or not isinstance(raw_claims.get("claims"), list):
        raise PacketError("Carousel claims.json must contain a claims array")
    if raw_claims.get("run_date") != run_dir.name:
        raise PacketError("Carousel claims run_date does not match requested date")
    if not isinstance(run_state, dict) or run_state.get("run_date") != run_dir.name:
        raise PacketError("Carousel run_state run_date does not match requested date")
    if run_state.get("complete") is not True:
        raise PacketError("Carousel run_state is not complete")
    claims = [_claim(item) for item in raw_claims["claims"]]
    return {
        "mode": "carousel_fact_pack",
        "story": {
            "headline": _headline(selection),
            "angle": _text(
                _section(selection, "THE ANGLE", 1500) or _headline(selection),
                label="angle", maximum=1500,
            ),
            "why_it_matters": _text(
                _section(selection, "WHY THIS ONE, against the four criteria in order", 1100)
                or _section(selection, "WHY THIS ONE", 1100)
                or _headline(selection),
                label="why it matters", maximum=1100,
            ),
            "selection_excerpt": _text(
                _section(selection, "THE STORY", 1100), label="selection excerpt", maximum=1100
            ),
            "scout_excerpt": _text(
                _section(scout, "CANDIDATE 1 (SELECTED)", 1100)
                or _section(scout, "THE CONVERGENCE", 1100)
                or scout,
                label="scout excerpt", maximum=1100,
            ),
        },
        "claims": claims,
        "broad_searches_used": 0,
        "provenance_kind": "carousel_daily_fact_pack",
        "provenance": {name: _sha(path) for name, path in sorted(paths.items())},
    }


def _fallback(path: Path, run_date: str, config: dict[str, Any]) -> dict[str, Any]:
    if not path.is_file():
        raise PacketError("Carousel fact pack is incomplete and no fallback candidate file exists")
    value = load_path(path, label="bounded fallback candidates")
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "run_date", "broad_searches_used", "candidates"
    }:
        raise PacketError("fallback file has unknown or missing top-level fields")
    if value["schema_version"] != 1 or value["run_date"] != run_date:
        raise PacketError("fallback schema/date does not match this run")
    used = value["broad_searches_used"]
    fallback_cfg = config["story_packet"]["fallback"]
    if isinstance(used, bool) or not isinstance(used, int) or not 0 <= used <= fallback_cfg["maximum_broad_searches"]:
        raise PacketError("fallback broad_searches_used exceeds the committed cap")
    candidates = value["candidates"]
    if not isinstance(candidates, list) or not 1 <= len(candidates) <= fallback_cfg["maximum_candidates"]:
        raise PacketError("fallback candidates exceed the committed bound")
    selected = [item for item in candidates if isinstance(item, dict) and item.get("selected") is True]
    if len(selected) != 1:
        raise PacketError("fallback must mark exactly one candidate selected")
    candidate = selected[0]
    required = {"id", "selected", "headline", "angle", "why_it_matters", "claims"}
    if set(candidate) != required or not isinstance(candidate["claims"], list):
        raise PacketError("selected fallback candidate has unknown or missing fields")
    claims = [_claim(item) for item in candidate["claims"]]
    return {
        "mode": "bounded_fallback",
        "story": {
            "headline": _text(candidate["headline"], label="fallback headline", maximum=420),
            "angle": _text(candidate["angle"], label="fallback angle", maximum=1500),
            "why_it_matters": _text(candidate["why_it_matters"], label="fallback why", maximum=1100),
            "selection_excerpt": "",
            "scout_excerpt": "",
        },
        "claims": claims,
        "broad_searches_used": used,
        "provenance_kind": "bounded_fallback_candidates",
        "provenance": {path.name: _sha(path)},
    }


def _set_measurement(packet: dict[str, Any], maximum: int) -> None:
    measurement = {
        "token_estimator": "ceil(utf8_bytes/4)",
        "estimated_tokens": 0,
        "maximum_estimated_tokens": maximum,
        "utf8_bytes": 0,
    }
    packet["measurement"] = measurement
    for _ in range(8):
        data = _render(packet)
        new_bytes = len(data)
        new_tokens = estimate_tokens_bytes(data)
        if measurement["utf8_bytes"] == new_bytes and measurement["estimated_tokens"] == new_tokens:
            return
        measurement["utf8_bytes"] = new_bytes
        measurement["estimated_tokens"] = new_tokens
    raise PacketError("packet measurement did not converge")


def validate_packet(packet: Any, config: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(packet, dict) or set(packet) != PACKET_KEYS:
        raise PacketError("story packet has unknown or missing top-level fields")
    if packet["schema_version"] != 1 or packet["mode"] not in {
        "carousel_fact_pack", "bounded_fallback"
    }:
        raise PacketError("story packet schema or mode is invalid")
    _date(packet["run_date"])
    story = packet["story"]
    expected_story = {"headline", "angle", "why_it_matters", "selection_excerpt", "scout_excerpt"}
    if not isinstance(story, dict) or set(story) != expected_story:
        raise PacketError("story object has unknown or missing fields")
    for key in ("headline", "angle", "why_it_matters"):
        _text(story[key], label=f"story {key}", maximum=2000)
    claims = packet["claims"]
    cfg = config["story_packet"]
    if not isinstance(claims, list) or not cfg["minimum_claims"] <= len(claims) <= cfg["maximum_claims"]:
        raise PacketError("story packet claim count is outside the committed range")
    if any(not isinstance(item, dict) or set(item) != CLAIM_KEYS for item in claims):
        raise PacketError("story packet claims have unknown or missing fields")
    normalized = [_claim(item) for item in claims]
    ids = [item["id"] for item in normalized]
    if len(ids) != len(set(ids)):
        raise PacketError("story packet claim IDs must be unique")
    sources = packet["sources"]
    if not isinstance(sources, list) or len(sources) > cfg["maximum_sources"]:
        raise PacketError("story packet source count exceeds the committed cap")
    if sources != list(dict.fromkeys(sources)):
        raise PacketError("story packet sources must be unique and stable")
    for source in sources:
        _url(source, label="story packet source")
    research = packet["research"]
    if not isinstance(research, dict) or set(research) != {
        "broad_searches_used", "broad_search_cap", "fallback_used"
    }:
        raise PacketError("story packet research object is invalid")
    fallback_cfg = cfg["fallback"]
    expected_fallback = packet["mode"] == "bounded_fallback"
    if research["fallback_used"] is not expected_fallback:
        raise PacketError("story packet fallback flag disagrees with mode")
    searches = research["broad_searches_used"]
    if isinstance(searches, bool) or not isinstance(searches, int):
        raise PacketError("story packet broad search count must be an integer")
    allowed = fallback_cfg["maximum_broad_searches"] if expected_fallback else fallback_cfg["normal_broad_searches"]
    if not 0 <= searches <= allowed or research["broad_search_cap"] != fallback_cfg["maximum_broad_searches"]:
        raise PacketError("story packet broad search budget is invalid")
    provenance = packet["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != {"source_kind", "input_sha256"}:
        raise PacketError("story packet provenance object is invalid")
    hashes = provenance["input_sha256"]
    if not isinstance(hashes, dict) or not hashes:
        raise PacketError("story packet must bind at least one source input")
    if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes.values()):
        raise PacketError("story packet provenance contains an invalid SHA-256")
    measurement = packet["measurement"]
    if not isinstance(measurement, dict) or set(measurement) != {
        "token_estimator", "estimated_tokens", "maximum_estimated_tokens", "utf8_bytes"
    }:
        raise PacketError("story packet measurement object is invalid")
    data = _render(packet)
    if measurement != {
        "token_estimator": "ceil(utf8_bytes/4)",
        "estimated_tokens": estimate_tokens_bytes(data),
        "maximum_estimated_tokens": cfg["maximum_estimated_tokens"],
        "utf8_bytes": len(data),
    }:
        raise PacketError("story packet measurement does not match its exact emitted bytes")
    if measurement["estimated_tokens"] > cfg["maximum_estimated_tokens"]:
        raise PacketError("story packet exceeds its token cap")
    return packet


def build_packet(
    *, root: Path, run_date: str, carousel_root: Path, fallback_path: Path | None = None
) -> dict[str, Any]:
    run_date = _date(run_date)
    config = _config(root)
    source = _fact_pack(carousel_root.resolve() / "runs" / run_date, config)
    if source is None:
        if fallback_path is None:
            raise PacketError("Carousel fact pack is incomplete; provide a bounded fallback file")
        source = _fallback(fallback_path.resolve(), run_date, config)
    cfg = config["story_packet"]
    claims = source["claims"][: cfg["maximum_claims"]]
    if len(claims) < cfg["minimum_claims"]:
        raise PacketError("selected story does not have enough source-backed claims")
    packet: dict[str, Any] = {
        "schema_version": 1,
        "run_date": run_date,
        "mode": source["mode"],
        "story": source["story"],
        "claims": claims,
        "sources": [],
        "research": {
            "broad_searches_used": source["broad_searches_used"],
            "broad_search_cap": cfg["fallback"]["maximum_broad_searches"],
            "fallback_used": source["mode"] == "bounded_fallback",
        },
        "provenance": {
            "source_kind": source["provenance_kind"],
            "input_sha256": source["provenance"],
        },
    }
    maximum = cfg["maximum_estimated_tokens"]
    while True:
        packet["sources"] = list(dict.fromkeys(item["source_url"] for item in packet["claims"]))[: cfg["maximum_sources"]]
        _set_measurement(packet, maximum)
        if packet["measurement"]["estimated_tokens"] <= maximum:
            break
        if len(packet["claims"]) <= cfg["minimum_claims"]:
            raise PacketError("minimum source-backed packet cannot fit within the token cap")
        packet["claims"].pop()
    return validate_packet(packet, config)


def _inside_output(root: Path, value: str | None) -> Path:
    target = (root / (value or OUTPUT_REL)).resolve()
    allowed = (root / "out" / "dispatch").resolve()
    try:
        target.relative_to(allowed)
    except ValueError:
        raise PacketError("packet output must remain under out/dispatch") from None
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True)
    parser.add_argument("--carousel-root")
    parser.add_argument("--fallback-candidates")
    parser.add_argument("--output")
    args = parser.parse_args()
    carousel = Path(args.carousel_root).resolve() if args.carousel_root else ROOT.parent / "alaskaaicarousels"
    fallback = Path(args.fallback_candidates).resolve() if args.fallback_candidates else None
    try:
        packet = build_packet(root=ROOT, run_date=args.date, carousel_root=carousel, fallback_path=fallback)
        output = _inside_output(ROOT, args.output)
        _atomic_json(output, packet)
        print(json.dumps({
            "status": "ok",
            "output": output.relative_to(ROOT).as_posix(),
            "mode": packet["mode"],
            "claims": len(packet["claims"]),
            "estimated_tokens": packet["measurement"]["estimated_tokens"],
            "broad_searches_used": packet["research"]["broad_searches_used"],
        }, sort_keys=True))
        return 0
    except (PacketError, StrictJSONError, OSError, ValueError) as exc:
        print(f"dispatch_story_packet: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
