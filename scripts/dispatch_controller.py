#!/usr/bin/env python3
"""Deterministic, budgeted controller for the token-optimized daily canary."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from daily_scope_guard import ScopeError, check_scope, create_snapshot
from dispatch_story_packet import PacketError, estimate_tokens_bytes, validate_packet
from strict_json import StrictJSONError, canonical_bytes, load_path, loads


ROOT = Path(__file__).resolve().parent.parent
CONFIG_REL = "config/daily_controller.json"
VERSION = "1.0.0"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
STATE_KEYS = {
    "schema_version", "controller_version", "run_id", "run_date", "phase",
    "repair_rounds", "story_packet_mode", "broad_searches_used",
    "cost_budget_usd", "history",
}
CONTEXT_KEYS = {
    "schema_version", "cache_strategy", "static_cache_key", "controller_prompt",
    "standing_context", "total_standing_tokens", "story_packet",
    "model_payload_contract",
}
EVENT_KEYS = {
    "schema_version", "sequence", "event", "recorded_at", "payload",
}
RESERVATION_KEYS = {
    "reservation_id", "phase", "role", "model_tier", "context_cache_key",
    "estimated_input_tokens", "maximum_output_tokens", "estimated_cost_usd",
}
COMPLETION_KEYS = {
    "reservation_id", "prompt_tokens", "input_tokens", "output_tokens",
    "cache_read_tokens", "cache_write_tokens", "cost_usd",
}
FROZEN_EVAL_SCENARIOS = {
    "2026-08-12": "normal",
    "2026-08-13": "normal",
    "2026-08-28": "worst_case",
}


class ControllerError(RuntimeError):
    """A controller transition, context, or budget contract failed."""


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


def _config(root: Path = ROOT) -> dict[str, Any]:
    value = load_path(root / CONFIG_REL, label="daily controller config")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ControllerError("daily controller config must be a schema-v1 object")
    for key in ("authoring_outputs", "story_packet", "context", "state_machine", "models", "budgets", "daily_scope"):
        if not isinstance(value.get(key), dict):
            raise ControllerError(f"daily controller config is missing {key}")
    _validate_plan(value)
    _validate_daily_contract(root, value)
    return value


def _validate_plan(config: dict[str, Any]) -> None:
    models = config["models"]
    budgets = config["budgets"]
    roles = models.get("roles")
    normal = models.get("normal_plan")
    worst = models.get("worst_case_plan")
    if not isinstance(roles, dict) or not isinstance(normal, list) or not isinstance(worst, list):
        raise ControllerError("model roles and plans must be configured")
    if len(normal) != budgets.get("normal_model_calls") or len(normal) > budgets.get("maximum_normal_model_calls", -1):
        raise ControllerError("normal model-call plan exceeds its committed budget")
    if len(worst) != budgets.get("worst_case_model_calls") or len(worst) > budgets.get("maximum_worst_case_model_calls", -1):
        raise ControllerError("worst-case model-call plan exceeds its committed budget")
    if len(worst) > budgets.get("hard_model_call_cap", -1):
        raise ControllerError("worst-case plan exceeds the hard model-call cap")
    for plan_name, plan in (("normal", normal), ("worst-case", worst)):
        counts = Counter(plan)
        unknown = sorted(set(counts) - set(roles))
        if unknown:
            raise ControllerError(f"{plan_name} plan names unknown roles: {', '.join(unknown)}")
        for role, count in counts.items():
            maximum = roles[role].get("maximum_calls")
            if isinstance(maximum, bool) or not isinstance(maximum, int) or count > maximum:
                raise ControllerError(f"{plan_name} plan exceeds {role} quota")
    if normal.count("showrunner") != 1 or worst.count("showrunner") != 1:
        raise ControllerError("each plan must use exactly one showrunner")
    tiers = models.get("telemetry_tiers")
    if tiers != {"high": "frontier", "mid": "balanced", "cheap": "fast"}:
        raise ControllerError("telemetry tier mapping is not canonical")


def _validate_daily_contract(root: Path, config: dict[str, Any]) -> None:
    if config.get("cadence") != "daily" or config.get("timezone") != "America/Anchorage":
        raise ControllerError("daily cadence must use America/Anchorage")
    if config.get("fps") != 30:
        raise ControllerError("daily video contract requires 30 fps")
    if config.get("runtime_seconds") != {"minimum": 112, "maximum": 130}:
        raise ControllerError("daily runtime contract must be exactly 112-130 seconds")
    if config.get("voiceover_words") != {"minimum": 262, "maximum": 282}:
        raise ControllerError("daily voiceover contract must be exactly 262-282 words")
    formats = config.get("video_formats")
    expected = {
        "master": ("vertical_hosted", 1080, 1920, "9:16"),
        "square": ("square", 1080, 1080, "1:1"),
        "mobile": ("mobile", 720, 1280, "9:16"),
    }
    if not isinstance(formats, dict) or set(formats) != set(expected):
        raise ControllerError("daily video formats must be exactly master, square, and mobile")
    for name, facts in expected.items():
        value = formats[name]
        if not isinstance(value, dict) or (
            value.get("role"), value.get("width"), value.get("height"), value.get("aspect_ratio")
        ) != facts:
            raise ControllerError(f"daily {name} format is not canonical")
    if config.get("forbidden_video_formats") != [
        {"width": 1080, "height": 1350, "aspect_ratio": "4:5"}
    ]:
        raise ControllerError("daily format contract must explicitly forbid 1080x1350/4:5")
    outputs = config["authoring_outputs"]
    if set(outputs) != {"voiceover_text", "storyboard", "episode_props"}:
        raise ControllerError("authoring output paths must be exact")
    for name, value in outputs.items():
        _safe_rel(value, label=f"authoring output {name}")
    deliverables_path = root / "config" / "deliverables.json"
    if deliverables_path.is_file():
        deliverables = load_path(deliverables_path, label="deliverables config")
        if not isinstance(deliverables, dict) or not isinstance(deliverables.get("roles"), dict):
            raise ControllerError("deliverables config is invalid")
        for _, (role, width, height, _) in expected.items():
            role_value = deliverables["roles"].get(role)
            if not isinstance(role_value, dict) or (
                role_value.get("width"), role_value.get("height")
            ) != (width, height):
                raise ControllerError(f"deliverables config disagrees with daily role {role}")
        forbidden = deliverables.get("forbidden_dimensions")
        if not isinstance(forbidden, list) or [1080, 1350] not in forbidden:
            raise ControllerError("deliverables config does not forbid 1080x1350")


def _date(value: str) -> str:
    if not isinstance(value, str) or not DATE_RE.fullmatch(value):
        raise ControllerError("run date must be YYYY-MM-DD")
    try:
        if dt.date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError:
        raise ControllerError("run date is not a real canonical calendar date") from None
    return value


def _safe_rel(value: str, *, label: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ControllerError(f"{label} must be a repository-relative POSIX path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise ControllerError(f"{label} must be a canonical repository-relative path")
    return value


def _inside(root: Path, value: str, *, label: str, must_exist: bool = True) -> Path:
    rel = _safe_rel(value, label=label)
    target = (root / rel).resolve(strict=False)
    try:
        target.relative_to(root.resolve())
    except ValueError:
        raise ControllerError(f"{label} escapes the repository") from None
    if must_exist and (not target.is_file() or target.is_symlink()):
        raise ControllerError(f"{label} must be a regular file: {rel}")
    return target


def _state_path(root: Path, config: dict[str, Any]) -> Path:
    return _inside(root, config["state_machine"]["state_path"], label="state path", must_exist=False)


def _telemetry_path(root: Path, config: dict[str, Any]) -> Path:
    return _inside(root, config["budgets"]["telemetry"], label="telemetry path", must_exist=False)


def load_state(root: Path = ROOT, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or _config(root)
    value = load_path(_state_path(root, config), label="controller state")
    if not isinstance(value, dict) or set(value) != STATE_KEYS:
        raise ControllerError("controller state has unknown or missing fields")
    if value["schema_version"] != 1 or value["controller_version"] != VERSION:
        raise ControllerError("controller state schema/version is invalid")
    _date(value["run_date"])
    machine = config["state_machine"]
    phases = set(machine["transitions"]) | set(machine["terminal"])
    if value["phase"] not in phases:
        raise ControllerError("controller state phase is unknown")
    repairs = value["repair_rounds"]
    if isinstance(repairs, bool) or not isinstance(repairs, int) or not 0 <= repairs <= machine["maximum_repairs"]:
        raise ControllerError("controller repair count is invalid")
    if value["story_packet_mode"] not in (None, "carousel_fact_pack", "bounded_fallback"):
        raise ControllerError("controller story packet mode is invalid")
    if not isinstance(value["history"], list):
        raise ControllerError("controller history must be a list")
    return value


def initialize(
    *, root: Path, run_id: str, run_date: str, cost_budget_usd: float | None = None
) -> dict[str, Any]:
    config = _config(root)
    run_date = _date(run_date)
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{2,79}", run_id):
        raise ControllerError("run ID must be 3-80 canonical ASCII characters")
    configured_cost = float(config["budgets"]["maximum_cost_usd"])
    cost = configured_cost if cost_budget_usd is None else float(cost_budget_usd)
    if not math.isfinite(cost) or cost <= 0 or cost > configured_cost:
        raise ControllerError("run cost budget must be positive and may only lower the committed maximum")
    state_path = _state_path(root, config)
    telemetry_path = _telemetry_path(root, config)
    if state_path.exists() or telemetry_path.exists():
        raise ControllerError("controller state/telemetry already exists; use a fresh out/dispatch run directory")
    create_snapshot(root)
    state = {
        "schema_version": 1,
        "controller_version": VERSION,
        "run_id": run_id,
        "run_date": run_date,
        "phase": config["state_machine"]["initial"],
        "repair_rounds": 0,
        "story_packet_mode": None,
        "broad_searches_used": 0,
        "cost_budget_usd": round(cost, 6),
        "history": [],
    }
    _atomic_json(state_path, state)
    return state


def build_context(
    *, root: Path = ROOT, story_packet_rel: str | None = None
) -> dict[str, Any]:
    config = _config(root)
    manifest = _compose_context(root, config, story_packet_rel)
    cfg = config["context"]
    _atomic_json(_inside(root, cfg["manifest"], label="context manifest", must_exist=False), manifest)
    return manifest


def _compose_context(
    root: Path, config: dict[str, Any], story_packet_rel: str | None = None
) -> dict[str, Any]:
    cfg = config["context"]
    packet_rel = story_packet_rel or config["story_packet"]["output"]
    packet_path = _inside(root, packet_rel, label="story packet")
    packet = validate_packet(load_path(packet_path, label="story packet"), config)
    prompt_path = _inside(root, cfg["controller_prompt"], label="controller prompt")
    context_path = _inside(root, cfg["standing_context"], label="standing context")
    prompt_bytes = prompt_path.read_bytes()
    context_bytes = context_path.read_bytes()
    prompt_tokens = estimate_tokens_bytes(prompt_bytes)
    context_tokens = estimate_tokens_bytes(context_bytes)
    total = prompt_tokens + context_tokens
    if prompt_tokens > cfg["maximum_controller_prompt_tokens"]:
        raise ControllerError("controller prompt exceeds its token cap")
    if context_tokens > cfg["maximum_standing_context_tokens"]:
        raise ControllerError("standing context exceeds its token cap")
    if total > cfg["maximum_total_standing_tokens"]:
        raise ControllerError("total standing prompt exceeds its token cap")
    cache_key = hashlib.sha256(prompt_bytes + b"\0" + context_bytes).hexdigest()
    manifest = {
        "schema_version": 1,
        "cache_strategy": "one_static_block_reused_by_hash",
        "static_cache_key": cache_key,
        "controller_prompt": {
            "path": cfg["controller_prompt"], "sha256": _sha(prompt_path),
            "utf8_bytes": len(prompt_bytes), "estimated_tokens": prompt_tokens,
        },
        "standing_context": {
            "path": cfg["standing_context"], "sha256": _sha(context_path),
            "utf8_bytes": len(context_bytes), "estimated_tokens": context_tokens,
        },
        "total_standing_tokens": total,
        "story_packet": {
            "path": packet_rel, "sha256": _sha(packet_path),
            "estimated_tokens": packet["measurement"]["estimated_tokens"],
        },
        "model_payload_contract": {
            "static_block_once": True,
            "reuse_cache_key": True,
            "repeat_static_injection": False,
            "broad_repository_injection": False,
        },
    }
    return manifest


def _validate_context(root: Path, config: dict[str, Any]) -> dict[str, Any]:
    cfg = config["context"]
    path = _inside(root, cfg["manifest"], label="context manifest")
    value = load_path(path, label="context manifest")
    if not isinstance(value, dict) or set(value) != CONTEXT_KEYS or value.get("schema_version") != 1:
        raise ControllerError("context manifest has unknown or missing fields")
    rebuilt = _compose_context(root, config, value["story_packet"]["path"])
    if value != rebuilt:
        raise ControllerError("context manifest is stale")
    return value


def _require_packet_binding(root: Path, state: dict[str, Any], config: dict[str, Any]) -> None:
    if state["story_packet_mode"] is None:
        return
    entries = [item for item in state["history"] if item.get("from") == "packet_context"]
    if len(entries) != 1 or not isinstance(entries[0].get("evidence"), list):
        raise ControllerError("controller state lacks one packet_context evidence binding")
    hashes = {
        item.get("path"): item.get("sha256")
        for item in entries[0]["evidence"]
        if isinstance(item, dict)
    }
    for rel in (config["story_packet"]["output"], config["context"]["manifest"]):
        expected = hashes.get(rel)
        if not isinstance(expected, str) or not SHA_RE.fullmatch(expected):
            raise ControllerError(f"packet_context did not hash-bind {rel}")
        if _sha(_inside(root, rel, label="packet/context binding")) != expected:
            raise ControllerError(f"packet_context evidence changed after validation: {rel}")


def _evidence(root: Path, paths: list[str], minimum: int) -> list[dict[str, Any]]:
    if len(paths) < minimum:
        raise ControllerError(f"phase requires at least {minimum} evidence file(s)")
    facts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in paths:
        rel = _safe_rel(value, label="evidence path")
        if rel in seen:
            raise ControllerError("phase evidence paths must be unique")
        seen.add(rel)
        path = _inside(root, rel, label="phase evidence")
        facts.append({"path": rel, "bytes": path.stat().st_size, "sha256": _sha(path)})
    return facts


def _validate_authored_outputs(root: Path, config: dict[str, Any], evidence: list[dict[str, Any]]) -> None:
    outputs = config["authoring_outputs"]
    expected = set(outputs.values())
    supplied = {item["path"] for item in evidence}
    if supplied != expected:
        raise ControllerError(
            "authoring phase requires exactly the canonical VO text, storyboard, and episode props"
        )
    vo_path = _inside(root, outputs["voiceover_text"], label="voiceover text")
    try:
        vo = vo_path.read_text(encoding="utf-8")
    except UnicodeError:
        raise ControllerError("voiceover text must be UTF-8") from None
    words = re.findall(r"[A-Za-z0-9]+(?:[’'-][A-Za-z0-9]+)*", vo)
    voice_cfg = config["voiceover_words"]
    if not voice_cfg["minimum"] <= len(words) <= voice_cfg["maximum"]:
        raise ControllerError(
            f"voiceover must contain {voice_cfg['minimum']}-{voice_cfg['maximum']} words; got {len(words)}"
        )
    storyboard = load_path(
        _inside(root, outputs["storyboard"], label="storyboard"), label="daily storyboard"
    )
    if not isinstance(storyboard, (dict, list)) or not storyboard:
        raise ControllerError("storyboard must be a nonempty strict-JSON object or array")
    props = load_path(
        _inside(root, outputs["episode_props"], label="episode props"), label="episode props"
    )
    if not isinstance(props, dict):
        raise ControllerError("episode props must be a strict-JSON object")
    total = props.get("total")
    fps = props.get("fps")
    if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
        raise ControllerError("episode props total must be a positive integer frame count")
    if fps != config["fps"]:
        raise ControllerError("episode props fps must equal the 30 fps daily contract")
    duration = total / fps
    runtime = config["runtime_seconds"]
    if not runtime["minimum"] <= duration <= runtime["maximum"]:
        raise ControllerError(
            f"episode duration must be {runtime['minimum']}-{runtime['maximum']} seconds; got {duration:.3f}"
        )


def _require_ship_gate(root: Path, evidence: list[dict[str, Any]]) -> None:
    required = {"out/dispatch/panel_verdict.json", "out/dispatch/SHIP_NOW"}
    supplied = {item["path"] for item in evidence}
    if len(evidence) != 5 or not required.issubset(supplied):
        raise ControllerError(
            "a passing judge round requires three cards plus canonical panel_verdict.json and SHIP_NOW"
        )
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "ship_gate.py"), "check"],
        cwd=root, capture_output=True, text=True, timeout=120, check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise ControllerError(
            "existing ship gate did not pass: " + (detail[-1] if detail else "unknown failure")
        )


def advance(
    *, root: Path = ROOT, outcome: str, evidence_paths: list[str]
) -> dict[str, Any]:
    config = _config(root)
    ok, reason = check_scope(root)
    if not ok:
        raise ControllerError(f"daily scope failed: {reason}")
    state = load_state(root, config)
    _require_packet_binding(root, state, config)
    phase = state["phase"]
    machine = config["state_machine"]
    if phase in machine["terminal"]:
        raise ControllerError(f"controller is already terminal at {phase}")
    transitions = machine["transitions"].get(phase, {})
    if outcome not in transitions:
        raise ControllerError(f"outcome {outcome!r} is not legal from {phase}")
    minimum = machine["evidence_minimums"][phase]
    evidence = _evidence(root, evidence_paths, minimum)
    if phase in ("judges_round_1", "judges_round_2"):
        if outcome == "fail" and len(evidence) != 3:
            raise ControllerError("a failing judge phase requires exactly three independent card files")
        if outcome == "pass":
            _require_ship_gate(root, evidence)
    if phase == "packet_context":
        packet_rel = config["story_packet"]["output"]
        context_rel = config["context"]["manifest"]
        supplied = {item["path"] for item in evidence}
        if not {packet_rel, context_rel}.issubset(supplied):
            raise ControllerError("packet_context requires the canonical packet and context manifest")
        packet = validate_packet(load_path(root / packet_rel, label="story packet"), config)
        _validate_context(root, config)
        state["story_packet_mode"] = packet["mode"]
        state["broad_searches_used"] = packet["research"]["broad_searches_used"]
    if phase == "vo_storyboard_episode_props":
        _validate_authored_outputs(root, config, evidence)
    next_phase = transitions[outcome]
    if next_phase == "repair":
        if state["repair_rounds"] >= machine["maximum_repairs"]:
            raise ControllerError("the single repair allowance is exhausted")
        state["repair_rounds"] += 1
    state["history"].append({
        "from": phase, "outcome": outcome, "to": next_phase, "evidence": evidence,
    })
    state["phase"] = next_phase
    _atomic_json(_state_path(root, config), state)
    return state


def _events(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    path = _telemetry_path(root, config)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ControllerError(f"telemetry cannot be read: {exc}") from None
    for index, line in enumerate(lines, 1):
        if not line:
            raise ControllerError(f"telemetry line {index} is blank")
        value = loads(line, label=f"telemetry line {index}")
        if not isinstance(value, dict) or set(value) != EVENT_KEYS:
            raise ControllerError(f"telemetry line {index} has unknown or missing fields")
        if value["schema_version"] != 1 or value["sequence"] != index:
            raise ControllerError(f"telemetry line {index} sequence/schema is invalid")
        if value["event"] not in ("call_reserved", "call_completed") or not isinstance(value["payload"], dict):
            raise ControllerError(f"telemetry line {index} event is invalid")
        payload = value["payload"]
        expected = RESERVATION_KEYS if value["event"] == "call_reserved" else COMPLETION_KEYS
        if set(payload) != expected:
            raise ControllerError(f"telemetry line {index} payload has unknown or missing fields")
        if not isinstance(value["recorded_at"], str) or not value["recorded_at"].endswith("Z"):
            raise ControllerError(f"telemetry line {index} recorded_at is invalid")
        reservation_id = payload["reservation_id"]
        if not isinstance(reservation_id, str) or not re.fullmatch(r"[0-9a-f]{24}", reservation_id):
            raise ControllerError(f"telemetry line {index} reservation_id is invalid")
        if value["event"] == "call_reserved":
            if payload["model_tier"] not in ("frontier", "balanced", "fast"):
                raise ControllerError(f"telemetry line {index} model tier is invalid")
            if not isinstance(payload["phase"], str) or not isinstance(payload["role"], str):
                raise ControllerError(f"telemetry line {index} phase/role is invalid")
            if not isinstance(payload["context_cache_key"], str) or not SHA_RE.fullmatch(payload["context_cache_key"]):
                raise ControllerError(f"telemetry line {index} cache key is invalid")
            for field in ("estimated_input_tokens", "maximum_output_tokens"):
                field_value = payload[field]
                if isinstance(field_value, bool) or not isinstance(field_value, int) or field_value <= 0:
                    raise ControllerError(f"telemetry line {index} {field} is invalid")
            estimated_cost = payload["estimated_cost_usd"]
            if isinstance(estimated_cost, bool) or not isinstance(estimated_cost, (int, float)) or not math.isfinite(float(estimated_cost)) or estimated_cost < 0:
                raise ControllerError(f"telemetry line {index} estimated cost is invalid")
        else:
            for field in ("prompt_tokens", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens"):
                field_value = payload[field]
                if isinstance(field_value, bool) or not isinstance(field_value, int) or field_value < 0:
                    raise ControllerError(f"telemetry line {index} {field} is invalid")
            if payload["cache_read_tokens"] + payload["cache_write_tokens"] > payload["prompt_tokens"] + payload["input_tokens"]:
                raise ControllerError(f"telemetry line {index} cache accounting is invalid")
            actual_cost = payload["cost_usd"]
            if isinstance(actual_cost, bool) or not isinstance(actual_cost, (int, float)) or not math.isfinite(float(actual_cost)) or actual_cost < 0:
                raise ControllerError(f"telemetry line {index} actual cost is invalid")
        events.append(value)
    return events


def _append_event(root: Path, config: dict[str, Any], event: str, payload: dict[str, Any]) -> None:
    events = _events(root, config)
    record = {
        "schema_version": 1,
        "sequence": len(events) + 1,
        "event": event,
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "payload": payload,
    }
    path = _telemetry_path(root, config)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def telemetry_summary(root: Path = ROOT, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or _config(root)
    events = _events(root, config)
    reservations: dict[str, dict[str, Any]] = {}
    completions: dict[str, dict[str, Any]] = {}
    for event in events:
        payload = event["payload"]
        reservation_id = payload.get("reservation_id")
        if not isinstance(reservation_id, str) or not reservation_id:
            raise ControllerError("telemetry event lacks reservation_id")
        if event["event"] == "call_reserved":
            if reservation_id in reservations:
                raise ControllerError("telemetry contains a duplicate reservation")
            reservations[reservation_id] = payload
        else:
            if reservation_id not in reservations or reservation_id in completions:
                raise ControllerError("telemetry completion is orphaned or duplicated")
            completions[reservation_id] = payload
    role_counts = Counter(item["role"] for item in reservations.values())
    phase_role_counts = Counter((item["phase"], item["role"]) for item in reservations.values())
    uncached_input = 0
    cache_read = 0
    output = 0
    cost = 0.0
    for reservation_id, reservation in reservations.items():
        completed = completions.get(reservation_id)
        if completed:
            uncached_input += completed["input_tokens"] + completed["cache_write_tokens"]
            cache_read += completed["cache_read_tokens"]
            output += completed["output_tokens"]
            cost += completed["cost_usd"]
        else:
            uncached_input += reservation["estimated_input_tokens"]
            output += reservation["maximum_output_tokens"]
            cost += reservation["estimated_cost_usd"]
    return {
        "calls": len(reservations),
        "completed_calls": len(completions),
        "open_calls": len(reservations) - len(completions),
        "uncached_input_tokens": uncached_input,
        "cache_read_tokens": cache_read,
        "output_tokens": output,
        "cost_usd": round(cost, 6),
        "role_counts": dict(role_counts),
        "phase_role_counts": {f"{phase}:{role}": count for (phase, role), count in phase_role_counts.items()},
        "reservations": reservations,
        "completions": completions,
    }


def budget_problems(summary: dict[str, Any], state: dict[str, Any], config: dict[str, Any]) -> list[str]:
    budget = config["budgets"]
    problems: list[str] = []
    checks = (
        ("calls", budget["hard_model_call_cap"], "model-call cap"),
        ("uncached_input_tokens", budget["maximum_uncached_input_tokens"], "uncached-input token cap"),
        ("cache_read_tokens", budget["maximum_cache_read_tokens"], "cache-read token cap"),
        ("output_tokens", budget["maximum_output_tokens"], "output token cap"),
    )
    for field, maximum, label in checks:
        if summary[field] > maximum:
            problems.append(f"{label} exceeded: {summary[field]} > {maximum}")
    if summary["cost_usd"] > state["cost_budget_usd"]:
        problems.append(f"cost cap exceeded: {summary['cost_usd']:.6f} > {state['cost_budget_usd']:.6f}")
    roles = config["models"]["roles"]
    for role, count in summary["role_counts"].items():
        if role not in roles or count > roles[role]["maximum_calls"]:
            problems.append(f"role call quota exceeded for {role}")
    for key, count in summary["phase_role_counts"].items():
        phase, role = key.split(":", 1)
        if role == "judge" and phase in ("judges_round_1", "judges_round_2") and count > 3:
            problems.append(f"judge round exceeds three calls: {phase}")
    return problems


def reserve_call(
    *, root: Path = ROOT, role: str, estimated_input_tokens: int,
    maximum_output_tokens: int, estimated_cost_usd: float,
) -> dict[str, Any]:
    config = _config(root)
    ok, reason = check_scope(root)
    if not ok:
        raise ControllerError(f"daily scope failed: {reason}")
    state = load_state(root, config)
    if state["phase"] in config["state_machine"]["terminal"]:
        raise ControllerError("no model call may be reserved after a terminal state")
    roles = config["models"]["roles"]
    if role not in roles:
        raise ControllerError(f"unknown model role {role!r}")
    role_cfg = roles[role]
    if state["phase"] not in role_cfg["allowed_phases"]:
        raise ControllerError(f"role {role} is not allowed in phase {state['phase']}")
    for value, label in (
        (estimated_input_tokens, "estimated input tokens"),
        (maximum_output_tokens, "maximum output tokens"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ControllerError(f"{label} must be a positive integer")
    if estimated_input_tokens > role_cfg["maximum_input_tokens_per_call"]:
        raise ControllerError("estimated input exceeds the role's per-call cap")
    if maximum_output_tokens > role_cfg["maximum_output_tokens_per_call"]:
        raise ControllerError("maximum output exceeds the role's per-call cap")
    cost = float(estimated_cost_usd)
    if not math.isfinite(cost) or cost < 0:
        raise ControllerError("estimated cost must be finite and nonnegative")
    context = _validate_context(root, config)
    _require_packet_binding(root, state, config)
    current = telemetry_summary(root, config)
    reservation_seed = {
        "run_id": state["run_id"], "sequence": current["calls"] + 1,
        "phase": state["phase"], "role": role, "cache": context["static_cache_key"],
    }
    reservation_id = hashlib.sha256(canonical_bytes(reservation_seed)).hexdigest()[:24]
    payload = {
        "reservation_id": reservation_id,
        "phase": state["phase"],
        "role": role,
        "model_tier": config["models"]["telemetry_tiers"][role_cfg["tier"]],
        "context_cache_key": context["static_cache_key"],
        "estimated_input_tokens": estimated_input_tokens,
        "maximum_output_tokens": maximum_output_tokens,
        "estimated_cost_usd": round(cost, 6),
    }
    projected = dict(current)
    projected["calls"] += 1
    projected["uncached_input_tokens"] += estimated_input_tokens
    projected["output_tokens"] += maximum_output_tokens
    projected["cost_usd"] = round(projected["cost_usd"] + cost, 6)
    projected["role_counts"] = dict(current["role_counts"])
    projected["role_counts"][role] = projected["role_counts"].get(role, 0) + 1
    projected["phase_role_counts"] = dict(current["phase_role_counts"])
    phase_role = f"{state['phase']}:{role}"
    projected["phase_role_counts"][phase_role] = projected["phase_role_counts"].get(phase_role, 0) + 1
    problems = budget_problems(projected, state, config)
    if problems:
        raise ControllerError("budget stop before call: " + "; ".join(problems))
    _append_event(root, config, "call_reserved", payload)
    return payload


def complete_call(
    *, root: Path = ROOT, reservation_id: str, prompt_tokens: int,
    input_tokens: int, output_tokens: int, cache_read_tokens: int,
    cache_write_tokens: int, cost_usd: float,
) -> dict[str, Any]:
    config = _config(root)
    state = load_state(root, config)
    summary = telemetry_summary(root, config)
    if reservation_id not in summary["reservations"]:
        raise ControllerError("call completion references an unknown reservation")
    if reservation_id in summary["completions"]:
        raise ControllerError("call reservation is already complete")
    values = {
        "prompt_tokens": prompt_tokens,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read_tokens,
        "cache_write_tokens": cache_write_tokens,
    }
    for label, value in values.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ControllerError(f"{label} must be a nonnegative integer")
    if cache_read_tokens + cache_write_tokens > prompt_tokens + input_tokens:
        raise ControllerError("cache read/write tokens cannot exceed prompt plus input tokens")
    cost = float(cost_usd)
    if not math.isfinite(cost) or cost < 0:
        raise ControllerError("actual cost must be finite and nonnegative")
    payload = {"reservation_id": reservation_id, **values, "cost_usd": round(cost, 6)}
    _append_event(root, config, "call_completed", payload)
    final = telemetry_summary(root, config)
    payload["budget_problems"] = budget_problems(final, state, config)
    return payload


def _gate(value: str) -> dict[str, str]:
    if "=" not in value:
        raise ControllerError("gate must be ID=pass or ID=fail")
    gate_id, result = value.split("=", 1)
    if not gate_id or result not in ("pass", "fail"):
        raise ControllerError("gate must be ID=pass or ID=fail")
    return {"id": gate_id, "result": result}


def export_eval(
    *, root: Path, scenario: str, source_kind: str, fetch_calls: int,
    other_tool_calls: int, editorial_revisions: int,
    preserved_outputs: list[str], gates: list[str], output_rel: str,
) -> dict[str, Any]:
    config = _config(root)
    state = load_state(root, config)
    summary = telemetry_summary(root, config)
    if summary["open_calls"]:
        raise ControllerError("evaluation telemetry requires every reservation to be completed")
    if scenario not in ("normal", "worst_case") or source_kind not in ("measured", "estimated", "synthetic"):
        raise ControllerError("evaluation scenario or source_kind is invalid")
    fixed_scenario = FROZEN_EVAL_SCENARIOS.get(state["run_date"])
    if fixed_scenario is not None and scenario != fixed_scenario:
        raise ControllerError(
            f"frozen fixture {state['run_date']} requires scenario {fixed_scenario}"
        )
    for value, label in (
        (fetch_calls, "fetch_calls"), (other_tool_calls, "other_tool_calls"),
        (editorial_revisions, "editorial_revisions"),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ControllerError(f"{label} must be a nonnegative integer")
    if not preserved_outputs or any(not isinstance(item, str) or not item for item in preserved_outputs):
        raise ControllerError("at least one nonempty preserved output ID is required")
    if len(preserved_outputs) != len(set(preserved_outputs)):
        raise ControllerError("preserved output IDs must be unique")
    gate_objects = [_gate(item) for item in gates]
    gate_ids = [item["id"] for item in gate_objects]
    if not gate_objects or len(gate_ids) != len(set(gate_ids)):
        raise ControllerError("gate IDs must be nonempty and unique")
    context = _validate_context(root, config)
    _require_packet_binding(root, state, config)
    calls: list[dict[str, Any]] = []
    for reservation_id, reservation in summary["reservations"].items():
        completed = summary["completions"][reservation_id]
        calls.append({
            "id": reservation_id,
            "model_tier": reservation["model_tier"],
            "purpose": reservation["role"],
            "prompt_tokens": completed["prompt_tokens"],
            "input_tokens": completed["input_tokens"],
            "output_tokens": completed["output_tokens"],
            "cache_read_tokens": completed["cache_read_tokens"],
            "cache_write_tokens": completed["cache_write_tokens"],
        })
    run = {
        "fixture_id": state["run_date"],
        "scenario": scenario,
        "standing_context_tokens": context["total_standing_tokens"],
        "calls": calls,
        "tools": {
            "search_calls": state["broad_searches_used"],
            "fetch_calls": fetch_calls,
            "other_tool_calls": other_tool_calls,
        },
        "revisions": {
            "editorial_revisions": editorial_revisions,
            "repair_passes": state["repair_rounds"],
        },
        "preserved_outputs": preserved_outputs,
        "gates": gate_objects,
    }
    seed = hashlib.sha256(canonical_bytes(run)).hexdigest()[:16]
    value = {
        "schema_version": 1,
        "telemetry_id": f"dispatch-controller-{state['run_date']}-{scenario}-{seed}",
        "source_kind": source_kind,
        "controller": {"name": "dispatch-token-controller", "version": VERSION},
        "runs": [run],
    }
    validate_eval_telemetry(value)
    output = _inside(root, output_rel, label="evaluation telemetry output", must_exist=False)
    _atomic_json(output, value)
    return value


def validate_eval_telemetry(value: Any) -> dict[str, Any]:
    top = {"schema_version", "telemetry_id", "source_kind", "controller", "runs"}
    if not isinstance(value, dict) or set(value) != top or value.get("schema_version") != 1:
        raise ControllerError("evaluation telemetry top-level shape is invalid")
    if not isinstance(value["telemetry_id"], str) or not value["telemetry_id"]:
        raise ControllerError("evaluation telemetry_id must be nonempty")
    if value["source_kind"] not in ("measured", "estimated", "synthetic"):
        raise ControllerError("evaluation source_kind is invalid")
    if not isinstance(value["controller"], dict) or set(value["controller"]) != {"name", "version"}:
        raise ControllerError("evaluation controller shape is invalid")
    if any(not isinstance(item, str) or not item for item in value["controller"].values()):
        raise ControllerError("evaluation controller name/version must be nonempty strings")
    if not isinstance(value["runs"], list) or len(value["runs"]) != 1:
        raise ControllerError("evaluation telemetry must contain exactly one run")
    run = value["runs"][0]
    run_keys = {
        "fixture_id", "scenario", "standing_context_tokens", "calls", "tools",
        "revisions", "preserved_outputs", "gates",
    }
    if not isinstance(run, dict) or set(run) != run_keys:
        raise ControllerError("evaluation run shape/fixture is invalid")
    _date(run.get("fixture_id"))
    if run["scenario"] not in ("normal", "worst_case"):
        raise ControllerError("evaluation scenario is invalid")
    fixed_scenario = FROZEN_EVAL_SCENARIOS.get(run["fixture_id"])
    if fixed_scenario is not None and run["scenario"] != fixed_scenario:
        raise ControllerError("evaluation frozen-fixture scenario is invalid")
    standing = run["standing_context_tokens"]
    if isinstance(standing, bool) or not isinstance(standing, int) or standing < 0:
        raise ControllerError("evaluation standing_context_tokens must be nonnegative")
    call_keys = {
        "id", "model_tier", "purpose", "prompt_tokens", "input_tokens",
        "output_tokens", "cache_read_tokens", "cache_write_tokens",
    }
    calls = run["calls"]
    if not isinstance(calls, list) or not calls:
        raise ControllerError("evaluation calls must be nonempty")
    scenario_cap = 9 if run["scenario"] == "normal" else 14
    if len(calls) > scenario_cap or len(calls) > 15:
        raise ControllerError("evaluation call count exceeds its scenario/hard cap")
    ids: list[str] = []
    for call in calls:
        if not isinstance(call, dict) or set(call) != call_keys:
            raise ControllerError("evaluation call shape is invalid")
        if call["model_tier"] not in ("frontier", "balanced", "fast"):
            raise ControllerError("evaluation model tier is invalid")
        if not isinstance(call["id"], str) or not call["id"] or not isinstance(call["purpose"], str) or not call["purpose"]:
            raise ControllerError("evaluation call ID/purpose must be nonempty")
        ids.append(call["id"])
        for key in call_keys - {"id", "model_tier", "purpose"}:
            if isinstance(call[key], bool) or not isinstance(call[key], int) or call[key] < 0:
                raise ControllerError("evaluation token counts must be nonnegative integers")
        if call["cache_read_tokens"] + call["cache_write_tokens"] > call["prompt_tokens"] + call["input_tokens"]:
            raise ControllerError("evaluation cache tokens exceed prompt plus input")
    if len(ids) != len(set(ids)):
        raise ControllerError("evaluation call IDs must be unique")
    for object_name, keys in (
        ("tools", {"search_calls", "fetch_calls", "other_tool_calls"}),
        ("revisions", {"editorial_revisions", "repair_passes"}),
    ):
        item = run[object_name]
        if not isinstance(item, dict) or set(item) != keys:
            raise ControllerError(f"evaluation {object_name} shape is invalid")
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in item.values()):
            raise ControllerError(f"evaluation {object_name} values must be nonnegative integers")
    if run["revisions"]["repair_passes"] > 1:
        raise ControllerError("evaluation repair passes exceed one")
    if run["scenario"] == "normal" and run["tools"]["search_calls"] != 0:
        raise ControllerError("normal evaluation scenario must use zero broad searches")
    if run["tools"]["search_calls"] > 10:
        raise ControllerError("evaluation broad search count exceeds ten")
    outputs = run["preserved_outputs"]
    if (
        not isinstance(outputs, list) or not outputs
        or any(not isinstance(item, str) or not item for item in outputs)
        or len(outputs) != len(set(outputs))
    ):
        raise ControllerError("evaluation preserved_outputs must be unique and nonempty")
    gates = run["gates"]
    if not isinstance(gates, list) or not gates:
        raise ControllerError("evaluation gates must be nonempty")
    gate_ids: list[str] = []
    for gate in gates:
        if not isinstance(gate, dict) or set(gate) != {"id", "result"} or gate.get("result") not in ("pass", "fail"):
            raise ControllerError("evaluation gate shape/result is invalid")
        if not isinstance(gate.get("id"), str) or not gate["id"]:
            raise ControllerError("evaluation gate ID must be nonempty")
        gate_ids.append(gate["id"])
    if len(gate_ids) != len(set(gate_ids)):
        raise ControllerError("evaluation gate IDs must be unique")
    return value


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--run-id", required=True)
    init.add_argument("--date", required=True)
    init.add_argument("--cost-budget-usd", type=float)
    context = sub.add_parser("build-context")
    context.add_argument("--story-packet")
    move = sub.add_parser("advance")
    move.add_argument("--outcome", choices=("pass", "fail"), required=True)
    move.add_argument("--evidence", action="append", default=[], required=True)
    reserve = sub.add_parser("reserve-call")
    reserve.add_argument("--role", required=True)
    reserve.add_argument("--estimated-input-tokens", type=int, required=True)
    reserve.add_argument("--maximum-output-tokens", type=int, required=True)
    reserve.add_argument("--estimated-cost-usd", type=float, required=True)
    complete = sub.add_parser("complete-call")
    complete.add_argument("--reservation-id", required=True)
    complete.add_argument("--prompt-tokens", type=int, required=True)
    complete.add_argument("--input-tokens", type=int, required=True)
    complete.add_argument("--output-tokens", type=int, required=True)
    complete.add_argument("--cache-read-tokens", type=int, required=True)
    complete.add_argument("--cache-write-tokens", type=int, required=True)
    complete.add_argument("--cost-usd", type=float, required=True)
    sub.add_parser("status")
    sub.add_parser("budget-check")
    export = sub.add_parser("export-eval")
    export.add_argument("--scenario", choices=("normal", "worst_case"), required=True)
    export.add_argument("--source-kind", choices=("measured", "estimated", "synthetic"), required=True)
    export.add_argument("--fetch-calls", type=int, default=0)
    export.add_argument("--other-tool-calls", type=int, default=0)
    export.add_argument("--editorial-revisions", type=int, default=0)
    export.add_argument("--preserved-output", action="append", default=[], required=True)
    export.add_argument("--gate", action="append", default=[], required=True)
    export.add_argument("--output", default="out/dispatch/eval_telemetry.json")
    args = parser.parse_args()
    try:
        if args.command == "init":
            _print(initialize(root=ROOT, run_id=args.run_id, run_date=args.date, cost_budget_usd=args.cost_budget_usd))
        elif args.command == "build-context":
            _print(build_context(root=ROOT, story_packet_rel=args.story_packet))
        elif args.command == "advance":
            _print(advance(root=ROOT, outcome=args.outcome, evidence_paths=args.evidence))
        elif args.command == "reserve-call":
            _print(reserve_call(
                root=ROOT, role=args.role, estimated_input_tokens=args.estimated_input_tokens,
                maximum_output_tokens=args.maximum_output_tokens,
                estimated_cost_usd=args.estimated_cost_usd,
            ))
        elif args.command == "complete-call":
            result = complete_call(
                root=ROOT, reservation_id=args.reservation_id,
                prompt_tokens=args.prompt_tokens, input_tokens=args.input_tokens,
                output_tokens=args.output_tokens, cache_read_tokens=args.cache_read_tokens,
                cache_write_tokens=args.cache_write_tokens, cost_usd=args.cost_usd,
            )
            _print(result)
            if result["budget_problems"]:
                return 1
        elif args.command in ("status", "budget-check"):
            config = _config(ROOT)
            state = load_state(ROOT, config)
            summary = telemetry_summary(ROOT, config)
            problems = budget_problems(summary, state, config)
            result = {"state": state, "telemetry": summary, "budget_problems": problems}
            _print(result)
            if args.command == "budget-check" and problems:
                return 1
        else:
            value = export_eval(
                root=ROOT, scenario=args.scenario, source_kind=args.source_kind,
                fetch_calls=args.fetch_calls, other_tool_calls=args.other_tool_calls,
                editorial_revisions=args.editorial_revisions,
                preserved_outputs=args.preserved_output, gates=args.gate,
                output_rel=args.output,
            )
            _print({"status": "ok", "telemetry_id": value["telemetry_id"], "output": args.output})
        return 0
    except (
        ControllerError, PacketError, ScopeError, StrictJSONError, OSError,
        ValueError, TypeError, OverflowError,
    ) as exc:
        print(f"dispatch_controller: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
