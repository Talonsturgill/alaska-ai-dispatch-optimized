#!/usr/bin/env python3
"""Deterministic offline cost/quality evaluator for frozen Dispatch replays.

This module never calls a model, network service, renderer, publisher, or media
tool.  It compares controller telemetry with frozen contracts and reconstructs
the estimated legacy baseline from Git blobs at one pinned commit.
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
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from strict_json import StrictJSONError, canonical_bytes, load_path


ROOT = Path(__file__).resolve().parents[1]
EVAL_ROOT = ROOT / "eval" / "replay"
EXPECTED_FIXTURES = ("2026-08-12", "2026-08-13", "2026-08-28")
MAX_JSON_BYTES = 2_000_000
MAX_BLOB_BYTES = 2_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._:-]{0,95}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MODEL_TIER_WEIGHTS = {"fast": 1.0, "balanced": 2.0, "frontier": 4.0}
TOKEN_WEIGHTS = {
    "uncached_input": 1.0,
    "cache_write": 1.25,
    "cache_read": 0.10,
    "output": 3.0,
}
TARGETS = {
    "standing_context_reduction_percent_min": 70.0,
    "normal_call_max": 9,
    "worst_case_call_max": 14,
    "hard_call_max": 15,
    "repair_passes_max": 1,
}


class ReplayEvalError(ValueError):
    """Invalid evaluator input or an unavailable frozen Git object."""


def _exact_keys(value: Any, expected: set[str], *, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReplayEvalError(f"{label} must be an object")
    actual = set(value)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ReplayEvalError(f"{label} fields drifted; missing={missing}, extra={extra}")
    return value


def _nonempty_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ReplayEvalError(f"{label} must be a trimmed non-empty string")
    return value


def _identifier(value: Any, *, label: str) -> str:
    result = _nonempty_string(value, label=label)
    if not ID_RE.fullmatch(result):
        raise ReplayEvalError(f"{label} is not a canonical identifier")
    return result


def _nonnegative_int(value: Any, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReplayEvalError(f"{label} must be a nonnegative integer")
    return value


def _positive_int(value: Any, *, label: str) -> int:
    result = _nonnegative_int(value, label=label)
    if result == 0:
        raise ReplayEvalError(f"{label} must be positive")
    return result


def _sha256(value: Any, *, label: str) -> str:
    result = _nonempty_string(value, label=label)
    if not SHA256_RE.fullmatch(result):
        raise ReplayEvalError(f"{label} must be lowercase SHA-256")
    return result


def _commit(value: Any, *, label: str) -> str:
    result = _nonempty_string(value, label=label)
    if not COMMIT_RE.fullmatch(result):
        raise ReplayEvalError(f"{label} must be a lowercase 40-character Git SHA")
    return result


def _relative_path(value: Any, *, label: str) -> str:
    result = _nonempty_string(value, label=label)
    if "\\" in result or ":" in result or result.startswith("/"):
        raise ReplayEvalError(f"{label} must be a repository-relative POSIX path")
    parsed = PurePosixPath(result)
    if any(part in {"", ".", ".."} for part in parsed.parts):
        raise ReplayEvalError(f"{label} contains an unsafe path segment")
    return result


def _unique_strings(value: Any, *, label: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ReplayEvalError(f"{label} must be {'a' if not allow_empty else 'an'} list"
                              f"{' with at least one item' if not allow_empty else ''}")
    result = [_identifier(item, label=f"{label}[{index}]") for index, item in enumerate(value)]
    if len(result) != len(set(result)):
        raise ReplayEvalError(f"{label} contains duplicates")
    return result


def _load_json(path: Path, *, label: str) -> Any:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise ReplayEvalError(f"{label} cannot be inspected: {exc}") from None
    if path.is_symlink() or not path.is_file():
        raise ReplayEvalError(f"{label} must be a regular file")
    if size > MAX_JSON_BYTES:
        raise ReplayEvalError(f"{label} exceeds {MAX_JSON_BYTES} bytes")
    try:
        return load_path(path, label=label)
    except StrictJSONError as exc:
        raise ReplayEvalError(str(exc)) from None


def _git_blob(root: Path, commit: str, relative: str) -> bytes:
    """Read an exact committed blob without consulting the network or worktree."""
    spec = f"{commit}:{relative}"
    try:
        kind = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-t", spec],
            capture_output=True,
            timeout=30,
            check=False,
        )
        if kind.returncode != 0 or kind.stdout.strip() != b"blob":
            raise ReplayEvalError(f"frozen source is not a Git blob: {spec}")
        size_result = subprocess.run(
            ["git", "-C", str(root), "cat-file", "-s", spec],
            capture_output=True,
            timeout=30,
            check=False,
        )
        try:
            blob_size = int(size_result.stdout.strip())
        except (TypeError, ValueError, OverflowError):
            raise ReplayEvalError(f"cannot determine frozen Git blob size: {spec}") from None
        if size_result.returncode != 0 or blob_size < 0 or blob_size > MAX_BLOB_BYTES:
            raise ReplayEvalError(
                f"frozen Git blob size is outside 0..{MAX_BLOB_BYTES} bytes: {spec}"
            )
        result = subprocess.run(
            ["git", "-C", str(root), "show", spec],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired) as exc:
        raise ReplayEvalError(f"cannot read frozen Git blob {spec}: {exc}") from None
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReplayEvalError(f"cannot read frozen Git blob {spec}: {detail}")
    if len(result.stdout) != blob_size:
        raise ReplayEvalError(f"frozen Git blob changed while it was read: {spec}")
    return result.stdout


def _blob_facts(root: Path, commit: str, relative: str) -> tuple[int, str, int]:
    blob = _git_blob(root, commit, relative)
    return len(blob), hashlib.sha256(blob).hexdigest(), math.ceil(len(blob) / 4)


def _validate_context_entry(
    entry: Any, *, root: Path, commit: str, label: str
) -> dict[str, Any]:
    item = _exact_keys(
        entry,
        {"path", "bytes", "sha256", "estimated_tokens"},
        label=label,
    )
    relative = _relative_path(item["path"], label=f"{label}.path")
    expected_bytes = _positive_int(item["bytes"], label=f"{label}.bytes")
    expected_sha = _sha256(item["sha256"], label=f"{label}.sha256")
    expected_tokens = _positive_int(item["estimated_tokens"], label=f"{label}.estimated_tokens")
    actual_bytes, actual_sha, actual_tokens = _blob_facts(root, commit, relative)
    if (expected_bytes, expected_sha, expected_tokens) != (
        actual_bytes, actual_sha, actual_tokens
    ):
        raise ReplayEvalError(f"{label} no longer matches its frozen Git blob")
    return {
        "path": relative,
        "bytes": expected_bytes,
        "sha256": expected_sha,
        "estimated_tokens": expected_tokens,
    }


def _validate_call_group(value: Any, *, label: str) -> dict[str, Any]:
    item = _exact_keys(
        value,
        {
            "id", "count", "model_tier", "prompt_tokens", "input_tokens",
            "output_tokens", "cache_read_tokens", "cache_write_tokens",
        },
        label=label,
    )
    tier = _nonempty_string(item["model_tier"], label=f"{label}.model_tier")
    if tier not in MODEL_TIER_WEIGHTS:
        raise ReplayEvalError(f"{label}.model_tier is unsupported")
    result = {
        "id": _identifier(item["id"], label=f"{label}.id"),
        "count": _positive_int(item["count"], label=f"{label}.count"),
        "model_tier": tier,
    }
    for field in (
        "prompt_tokens", "input_tokens", "output_tokens", "cache_read_tokens",
        "cache_write_tokens",
    ):
        result[field] = _nonnegative_int(item[field], label=f"{label}.{field}")
    available = result["prompt_tokens"] + result["input_tokens"]
    if result["cache_read_tokens"] + result["cache_write_tokens"] > available:
        raise ReplayEvalError(f"{label} cache tokens exceed prompt plus input tokens")
    if available + result["output_tokens"] == 0:
        raise ReplayEvalError(f"{label} cannot describe a zero-token model call")
    return result


def _validate_tools(value: Any, *, label: str) -> dict[str, int]:
    item = _exact_keys(
        value, {"search_calls", "fetch_calls", "other_tool_calls"}, label=label
    )
    return {
        key: _nonnegative_int(item[key], label=f"{label}.{key}")
        for key in ("search_calls", "fetch_calls", "other_tool_calls")
    }


def _validate_revisions(value: Any, *, label: str) -> dict[str, int]:
    item = _exact_keys(value, {"editorial_revisions", "repair_passes"}, label=label)
    return {
        key: _nonnegative_int(item[key], label=f"{label}.{key}")
        for key in ("editorial_revisions", "repair_passes")
    }


def load_baseline(path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    raw = _exact_keys(
        _load_json(path, label="baseline context"),
        {
            "schema_version", "baseline_id", "source_commit", "estimator",
            "standing_context", "referenced_context", "call_estimate_basis", "scenarios",
        },
        label="baseline context",
    )
    if raw["schema_version"] != 1:
        raise ReplayEvalError("baseline context schema_version must be 1")
    commit = _commit(raw["source_commit"], label="baseline.source_commit")
    estimator = _exact_keys(raw["estimator"], {"id", "description"}, label="baseline.estimator")
    if estimator["id"] != "utf8_bytes_div_4_ceiling_v1":
        raise ReplayEvalError("baseline estimator is unsupported")
    _nonempty_string(estimator["description"], label="baseline.estimator.description")

    standing_raw = raw["standing_context"]
    referenced_raw = raw["referenced_context"]
    if not isinstance(standing_raw, list) or not standing_raw:
        raise ReplayEvalError("baseline.standing_context must be non-empty")
    if not isinstance(referenced_raw, list) or not referenced_raw:
        raise ReplayEvalError("baseline.referenced_context must be non-empty")
    standing = [
        _validate_context_entry(item, root=root, commit=commit, label=f"standing_context[{i}]")
        for i, item in enumerate(standing_raw)
    ]
    referenced = [
        _validate_context_entry(item, root=root, commit=commit, label=f"referenced_context[{i}]")
        for i, item in enumerate(referenced_raw)
    ]
    paths = [item["path"] for item in standing + referenced]
    if len(paths) != len(set(paths)):
        raise ReplayEvalError("baseline context paths must be unique")

    basis = raw["call_estimate_basis"]
    if not isinstance(basis, list) or not basis:
        raise ReplayEvalError("baseline.call_estimate_basis must be non-empty")
    for index, entry in enumerate(basis):
        item = _exact_keys(entry, {"path", "line_ranges", "note"}, label=f"basis[{index}]")
        relative = _relative_path(item["path"], label=f"basis[{index}].path")
        if relative not in paths:
            raise ReplayEvalError(f"basis[{index}].path is not in the frozen context inventory")
        _nonempty_string(item["line_ranges"], label=f"basis[{index}].line_ranges")
        _nonempty_string(item["note"], label=f"basis[{index}].note")

    scenarios_raw = raw["scenarios"]
    _exact_keys(scenarios_raw, {"normal", "worst_case"}, label="baseline.scenarios")
    scenarios: dict[str, Any] = {}
    for scenario in ("normal", "worst_case"):
        item = _exact_keys(
            scenarios_raw[scenario], {"call_groups", "tools", "revisions"},
            label=f"baseline.scenarios.{scenario}",
        )
        groups_raw = item["call_groups"]
        if not isinstance(groups_raw, list) or not groups_raw:
            raise ReplayEvalError(f"baseline.scenarios.{scenario}.call_groups must be non-empty")
        groups = [
            _validate_call_group(group, label=f"baseline.{scenario}.call_groups[{i}]")
            for i, group in enumerate(groups_raw)
        ]
        group_ids = [group["id"] for group in groups]
        if len(group_ids) != len(set(group_ids)):
            raise ReplayEvalError(f"baseline {scenario} call-group ids are duplicated")
        scenarios[scenario] = {
            "call_groups": groups,
            "tools": _validate_tools(item["tools"], label=f"baseline.{scenario}.tools"),
            "revisions": _validate_revisions(
                item["revisions"], label=f"baseline.{scenario}.revisions"
            ),
        }
    return {
        "schema_version": 1,
        "baseline_id": _identifier(raw["baseline_id"], label="baseline.baseline_id"),
        "source_commit": commit,
        "standing_context": standing,
        "referenced_context": referenced,
        "scenarios": scenarios,
    }


def load_fixture(path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    raw = _exact_keys(
        _load_json(path, label=f"fixture {path.name}"),
        {
            "schema_version", "fixture_id", "fixture_kind", "expected_scenario",
            "provenance", "artifacts", "required_outputs", "required_gates",
        },
        label=f"fixture {path.name}",
    )
    if raw["schema_version"] != 1:
        raise ReplayEvalError(f"fixture {path.name} schema_version must be 1")
    fixture_id = _nonempty_string(raw["fixture_id"], label=f"fixture {path.name}.fixture_id")
    if not DATE_RE.fullmatch(fixture_id):
        raise ReplayEvalError(f"fixture {path.name}.fixture_id must be YYYY-MM-DD")
    kind = _nonempty_string(raw["fixture_kind"], label=f"fixture {path.name}.fixture_kind")
    if kind not in {"archived_exact", "derived_source", "synthetic_contract"}:
        raise ReplayEvalError(f"fixture {fixture_id} has unsupported fixture_kind")
    expected_scenario = _nonempty_string(
        raw["expected_scenario"], label=f"fixture {fixture_id}.expected_scenario"
    )
    if expected_scenario not in {"normal", "worst_case"}:
        raise ReplayEvalError(f"fixture {fixture_id}.expected_scenario is unsupported")
    provenance = _exact_keys(
        raw["provenance"], {"source_commit", "label", "exact_artifacts", "note"},
        label=f"fixture {fixture_id}.provenance",
    )
    commit = _commit(provenance["source_commit"], label=f"fixture {fixture_id}.source_commit")
    if not isinstance(provenance["exact_artifacts"], bool):
        raise ReplayEvalError(f"fixture {fixture_id}.exact_artifacts must be boolean")
    _nonempty_string(provenance["label"], label=f"fixture {fixture_id}.label")
    _nonempty_string(provenance["note"], label=f"fixture {fixture_id}.note")

    artifact_raw = raw["artifacts"]
    if not isinstance(artifact_raw, list):
        raise ReplayEvalError(f"fixture {fixture_id}.artifacts must be a list")
    if kind != "synthetic_contract" and not artifact_raw:
        raise ReplayEvalError(f"fixture {fixture_id} must bind at least one exact artifact")
    if kind == "synthetic_contract" and (artifact_raw or provenance["exact_artifacts"]):
        raise ReplayEvalError(f"synthetic fixture {fixture_id} cannot claim exact artifacts")
    artifacts = []
    for index, artifact in enumerate(artifact_raw):
        label = f"fixture {fixture_id}.artifacts[{index}]"
        item = _exact_keys(artifact, {"path", "bytes", "sha256"}, label=label)
        relative = _relative_path(item["path"], label=f"{label}.path")
        expected_bytes = _positive_int(item["bytes"], label=f"{label}.bytes")
        expected_sha = _sha256(item["sha256"], label=f"{label}.sha256")
        actual_bytes, actual_sha, _tokens = _blob_facts(root, commit, relative)
        if (expected_bytes, expected_sha) != (actual_bytes, actual_sha):
            raise ReplayEvalError(f"{label} does not match its frozen Git blob")
        artifacts.append({"path": relative, "bytes": expected_bytes, "sha256": expected_sha})
    artifact_paths = [item["path"] for item in artifacts]
    if len(artifact_paths) != len(set(artifact_paths)):
        raise ReplayEvalError(f"fixture {fixture_id} artifact paths are duplicated")

    return {
        "schema_version": 1,
        "fixture_id": fixture_id,
        "fixture_kind": kind,
        "expected_scenario": expected_scenario,
        "source_commit": commit,
        "source_label": provenance["label"],
        "source_note": provenance["note"],
        "exact_artifacts": provenance["exact_artifacts"],
        "artifacts": artifacts,
        "required_outputs": _unique_strings(
            raw["required_outputs"], label=f"fixture {fixture_id}.required_outputs"
        ),
        "required_gates": _unique_strings(
            raw["required_gates"], label=f"fixture {fixture_id}.required_gates"
        ),
    }


def load_fixtures(directory: Path, *, root: Path = ROOT) -> dict[str, dict[str, Any]]:
    if directory.is_symlink() or not directory.is_dir():
        raise ReplayEvalError("fixture directory must be a regular directory")
    fixtures: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        fixture = load_fixture(path, root=root)
        fixture_id = fixture["fixture_id"]
        if fixture_id in fixtures:
            raise ReplayEvalError(f"duplicate fixture id {fixture_id}")
        fixtures[fixture_id] = fixture
    if tuple(sorted(fixtures)) != EXPECTED_FIXTURES:
        raise ReplayEvalError(
            f"fixture coverage drifted; expected={list(EXPECTED_FIXTURES)}, "
            f"actual={sorted(fixtures)}"
        )
    output_contracts = {tuple(item["required_outputs"]) for item in fixtures.values()}
    gate_contracts = {tuple(item["required_gates"]) for item in fixtures.values()}
    if len(output_contracts) != 1 or len(gate_contracts) != 1:
        raise ReplayEvalError("frozen fixtures disagree on required outputs or gates")
    return fixtures


def _validate_call(value: Any, *, label: str) -> dict[str, Any]:
    item = _exact_keys(
        value,
        {
            "id", "model_tier", "purpose", "prompt_tokens", "input_tokens",
            "output_tokens", "cache_read_tokens", "cache_write_tokens",
        },
        label=label,
    )
    tier = _nonempty_string(item["model_tier"], label=f"{label}.model_tier")
    if tier not in MODEL_TIER_WEIGHTS:
        raise ReplayEvalError(f"{label}.model_tier is unsupported")
    result = {
        "id": _identifier(item["id"], label=f"{label}.id"),
        "model_tier": tier,
        "purpose": _nonempty_string(item["purpose"], label=f"{label}.purpose"),
    }
    for field in (
        "prompt_tokens", "input_tokens", "output_tokens", "cache_read_tokens",
        "cache_write_tokens",
    ):
        result[field] = _nonnegative_int(item[field], label=f"{label}.{field}")
    available = result["prompt_tokens"] + result["input_tokens"]
    if result["cache_read_tokens"] + result["cache_write_tokens"] > available:
        raise ReplayEvalError(f"{label} cache tokens exceed prompt plus input tokens")
    if available + result["output_tokens"] == 0:
        raise ReplayEvalError(f"{label} cannot describe a zero-token model call")
    return result


def load_telemetry(path: Path) -> dict[str, Any]:
    raw = _exact_keys(
        _load_json(path, label=f"telemetry {path.name}"),
        {"schema_version", "telemetry_id", "source_kind", "controller", "runs"},
        label=f"telemetry {path.name}",
    )
    if raw["schema_version"] != 1:
        raise ReplayEvalError(f"telemetry {path.name} schema_version must be 1")
    source_kind = _nonempty_string(raw["source_kind"], label="telemetry.source_kind")
    if source_kind not in {"measured", "estimated", "synthetic"}:
        raise ReplayEvalError(f"telemetry {path.name} source_kind is unsupported")
    controller = _exact_keys(raw["controller"], {"name", "version"}, label="controller")
    controller_value = {
        "name": _identifier(controller["name"], label="controller.name"),
        "version": _nonempty_string(controller["version"], label="controller.version"),
    }
    runs_raw = raw["runs"]
    if not isinstance(runs_raw, list) or not runs_raw:
        raise ReplayEvalError(f"telemetry {path.name}.runs must be non-empty")
    runs = []
    for run_index, run in enumerate(runs_raw):
        label = f"telemetry {path.name}.runs[{run_index}]"
        item = _exact_keys(
            run,
            {
                "fixture_id", "scenario", "standing_context_tokens", "calls", "tools",
                "revisions", "preserved_outputs", "gates",
            },
            label=label,
        )
        fixture_id = _nonempty_string(item["fixture_id"], label=f"{label}.fixture_id")
        if not DATE_RE.fullmatch(fixture_id):
            raise ReplayEvalError(f"{label}.fixture_id must be YYYY-MM-DD")
        scenario = _nonempty_string(item["scenario"], label=f"{label}.scenario")
        if scenario not in {"normal", "worst_case"}:
            raise ReplayEvalError(f"{label}.scenario is unsupported")
        calls_raw = item["calls"]
        if not isinstance(calls_raw, list) or not calls_raw:
            raise ReplayEvalError(f"{label}.calls must be non-empty")
        calls = [_validate_call(call, label=f"{label}.calls[{i}]") for i, call in enumerate(calls_raw)]
        call_ids = [call["id"] for call in calls]
        if len(call_ids) != len(set(call_ids)):
            raise ReplayEvalError(f"{label}.calls contains duplicate ids")
        gates_raw = item["gates"]
        if not isinstance(gates_raw, list) or not gates_raw:
            raise ReplayEvalError(f"{label}.gates must be non-empty")
        gates = []
        for gate_index, gate in enumerate(gates_raw):
            gate_label = f"{label}.gates[{gate_index}]"
            gate_item = _exact_keys(gate, {"id", "result"}, label=gate_label)
            result = _nonempty_string(gate_item["result"], label=f"{gate_label}.result")
            if result not in {"pass", "fail"}:
                raise ReplayEvalError(f"{gate_label}.result must be pass or fail")
            gates.append({"id": _identifier(gate_item["id"], label=f"{gate_label}.id"), "result": result})
        gate_ids = [gate["id"] for gate in gates]
        if len(gate_ids) != len(set(gate_ids)):
            raise ReplayEvalError(f"{label}.gates contains duplicate ids")
        runs.append({
            "fixture_id": fixture_id,
            "scenario": scenario,
            "standing_context_tokens": _nonnegative_int(
                item["standing_context_tokens"], label=f"{label}.standing_context_tokens"
            ),
            "calls": calls,
            "tools": _validate_tools(item["tools"], label=f"{label}.tools"),
            "revisions": _validate_revisions(item["revisions"], label=f"{label}.revisions"),
            "preserved_outputs": _unique_strings(
                item["preserved_outputs"], label=f"{label}.preserved_outputs"
            ),
            "gates": gates,
        })
    run_ids = [run["fixture_id"] for run in runs]
    if len(run_ids) != len(set(run_ids)):
        raise ReplayEvalError(f"telemetry {path.name} repeats a fixture id")
    return {
        "schema_version": 1,
        "telemetry_id": _identifier(raw["telemetry_id"], label="telemetry.telemetry_id"),
        "source_kind": source_kind,
        "controller": controller_value,
        "runs": runs,
    }


def _aggregate_calls(calls: Iterable[dict[str, Any]], *, grouped: bool) -> dict[str, Any]:
    totals = {
        "prompt_tokens": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
    }
    by_tier = {tier: 0 for tier in MODEL_TIER_WEIGHTS}
    relative_units = 0.0
    call_count = 0
    for call in calls:
        count = call["count"] if grouped else 1
        call_count += count
        by_tier[call["model_tier"]] += count
        for field in totals:
            totals[field] += call[field] * count
        available = call["prompt_tokens"] + call["input_tokens"]
        uncached = available - call["cache_read_tokens"] - call["cache_write_tokens"]
        token_units = (
            uncached * TOKEN_WEIGHTS["uncached_input"]
            + call["cache_write_tokens"] * TOKEN_WEIGHTS["cache_write"]
            + call["cache_read_tokens"] * TOKEN_WEIGHTS["cache_read"]
            + call["output_tokens"] * TOKEN_WEIGHTS["output"]
        )
        relative_units += count * MODEL_TIER_WEIGHTS[call["model_tier"]] * token_units / 1000.0
    return {
        "call_count": call_count,
        "calls_by_model_tier": by_tier,
        "tokens": totals,
        "relative_cost_units": round(relative_units, 3),
    }


def evaluate(
    baseline: dict[str, Any],
    fixtures: dict[str, dict[str, Any]],
    telemetry_documents: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered_documents = sorted(telemetry_documents, key=lambda item: item["telemetry_id"])
    telemetry_ids = [item["telemetry_id"] for item in ordered_documents]
    if len(telemetry_ids) != len(set(telemetry_ids)):
        raise ReplayEvalError("telemetry ids must be unique across input files")
    controllers = {
        (item["controller"]["name"], item["controller"]["version"])
        for item in ordered_documents
    }
    if len(controllers) != 1:
        raise ReplayEvalError("all telemetry files must describe one controller name/version")
    runs: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    telemetry_sources = []
    for document in ordered_documents:
        telemetry_sources.append({
            "telemetry_id": document["telemetry_id"],
            "source_kind": document["source_kind"],
            "controller": document["controller"],
        })
        for run in document["runs"]:
            fixture_id = run["fixture_id"]
            if fixture_id in runs:
                raise ReplayEvalError(f"duplicate telemetry for fixture {fixture_id}")
            runs[fixture_id] = (run, document)
    if tuple(sorted(runs)) != tuple(sorted(fixtures)):
        raise ReplayEvalError(
            f"telemetry coverage drifted; expected={sorted(fixtures)}, actual={sorted(runs)}"
        )

    baseline_standing = sum(item["estimated_tokens"] for item in baseline["standing_context"])
    results = []
    for fixture_id in sorted(fixtures):
        fixture = fixtures[fixture_id]
        run, document = runs[fixture_id]
        scenario = run["scenario"]
        if scenario != fixture["expected_scenario"]:
            raise ReplayEvalError(
                f"fixture {fixture_id} requires scenario {fixture['expected_scenario']}, "
                f"not {scenario}"
            )
        baseline_scenario = baseline["scenarios"][scenario]
        baseline_calls = _aggregate_calls(baseline_scenario["call_groups"], grouped=True)
        optimized_calls = _aggregate_calls(run["calls"], grouped=False)
        reduction = 100.0 * (1.0 - run["standing_context_tokens"] / baseline_standing)
        cost_reduction = 100.0 * (
            1.0 - optimized_calls["relative_cost_units"] / baseline_calls["relative_cost_units"]
        )

        expected_outputs = set(fixture["required_outputs"])
        actual_outputs = set(run["preserved_outputs"])
        expected_gates = set(fixture["required_gates"])
        gate_results = {gate["id"]: gate["result"] for gate in run["gates"]}
        missing_outputs = sorted(expected_outputs - actual_outputs)
        unexpected_outputs = sorted(actual_outputs - expected_outputs)
        missing_gates = sorted(expected_gates - set(gate_results))
        unexpected_gates = sorted(set(gate_results) - expected_gates)
        failed_gates = sorted(
            gate for gate in expected_gates if gate_results.get(gate) == "fail"
        )

        scenario_limit = (
            TARGETS["normal_call_max"] if scenario == "normal"
            else TARGETS["worst_case_call_max"]
        )
        checks = {
            "standing_context_reduction": reduction
            >= TARGETS["standing_context_reduction_percent_min"],
            "scenario_call_budget": optimized_calls["call_count"] <= scenario_limit,
            "hard_call_budget": optimized_calls["call_count"] <= TARGETS["hard_call_max"],
            "repair_budget": run["revisions"]["repair_passes"]
            <= TARGETS["repair_passes_max"],
            "required_outputs_preserved": not missing_outputs,
            "required_gates_preserved": not missing_gates and not failed_gates,
        }
        results.append({
            "fixture_id": fixture_id,
            "fixture_kind": fixture["fixture_kind"],
            "fixture_source": fixture["source_label"],
            "telemetry_id": document["telemetry_id"],
            "telemetry_source_kind": document["source_kind"],
            "scenario": scenario,
            "baseline": {
                "standing_context_tokens": baseline_standing,
                **baseline_calls,
                "tools": baseline_scenario["tools"],
                "revisions": baseline_scenario["revisions"],
            },
            "optimized": {
                "standing_context_tokens": run["standing_context_tokens"],
                **optimized_calls,
                "tools": run["tools"],
                "revisions": run["revisions"],
            },
            "standing_context_reduction_percent": round(reduction, 3),
            "relative_cost_reduction_percent": round(cost_reduction, 3),
            "quality_contract": {
                "missing_outputs": missing_outputs,
                "unexpected_outputs": unexpected_outputs,
                "missing_gates": missing_gates,
                "unexpected_gates": unexpected_gates,
                "failed_gates": failed_gates,
            },
            "checks": checks,
            "pass": all(checks.values()),
        })

    identity_material = {
        "baseline": baseline,
        "fixtures": [
            {
                "fixture_id": fixtures[key]["fixture_id"],
                "kind": fixtures[key]["fixture_kind"],
                "expected_scenario": fixtures[key]["expected_scenario"],
                "source_commit": fixtures[key]["source_commit"],
                "artifacts": fixtures[key]["artifacts"],
                "required_outputs": fixtures[key]["required_outputs"],
                "required_gates": fixtures[key]["required_gates"],
            }
            for key in sorted(fixtures)
        ],
        "telemetry": ordered_documents,
        "targets": TARGETS,
        "weights": {"model_tiers": MODEL_TIER_WEIGHTS, "tokens": TOKEN_WEIGHTS},
    }
    return {
        "schema_version": 1,
        "evaluation_id": hashlib.sha256(canonical_bytes(identity_material)).hexdigest(),
        "baseline": {
            "baseline_id": baseline["baseline_id"],
            "source_commit": baseline["source_commit"],
            "estimator": "utf8_bytes_div_4_ceiling_v1",
            "standing_context_tokens": baseline_standing,
            "referenced_context_tokens": sum(
                item["estimated_tokens"] for item in baseline["referenced_context"]
            ),
        },
        "telemetry_sources": telemetry_sources,
        "relative_cost_model": {
            "model_tier_weights": MODEL_TIER_WEIGHTS,
            "token_weights": TOKEN_WEIGHTS,
            "units": "weighted token-thousands; not currency or provider pricing",
        },
        "targets": TARGETS,
        "fixtures": results,
        "summary": {
            "fixture_count": len(results),
            "passed": sum(1 for result in results if result["pass"]),
            "failed": sum(1 for result in results if not result["pass"]),
        },
        "pass": all(result["pass"] for result in results),
    }


def markdown_report(report: dict[str, Any]) -> str:
    status = "PASS" if report["pass"] else "FAIL"
    lines = [
        "# Frozen replay cost and quality evaluation",
        "",
        f"**Overall: {status}**",
        "",
        f"Evaluation `{report['evaluation_id']}` uses baseline commit "
        f"`{report['baseline']['source_commit']}`. Relative cost units are model-agnostic "
        "weighted token-thousands, not dollars or provider pricing.",
        "",
        f"The frozen baseline contains {report['baseline']['standing_context_tokens']:,} "
        f"standing-context tokens and {report['baseline']['referenced_context_tokens']:,} "
        "referenced-context tokens under the declared estimator.",
        "",
        "| Fixture | Source | Scenario | Calls opt/base | Standing reduction | Relative cost reduction | Repairs | Quality | Result |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for item in report["fixtures"]:
        quality = item["quality_contract"]
        quality_ok = not (
            quality["missing_outputs"] or quality["missing_gates"] or quality["failed_gates"]
        )
        lines.append(
            f"| {item['fixture_id']} | {item['fixture_kind']} / "
            f"{item['telemetry_source_kind']} | {item['scenario']} | "
            f"{item['optimized']['call_count']}/{item['baseline']['call_count']} | "
            f"{item['standing_context_reduction_percent']:.1f}% | "
            f"{item['relative_cost_reduction_percent']:.1f}% | "
            f"{item['optimized']['revisions']['repair_passes']} | "
            f"{'preserved' if quality_ok else 'drifted'} | "
            f"{'PASS' if item['pass'] else 'FAIL'} |"
        )
    lines.extend(["", "## Token and tool totals", ""])
    for item in report["fixtures"]:
        tokens = item["optimized"]["tokens"]
        tools = item["optimized"]["tools"]
        tiers = item["optimized"]["calls_by_model_tier"]
        lines.extend([
            f"- **{item['fixture_id']}**: prompt {tokens['prompt_tokens']:,}; input "
            f"{tokens['input_tokens']:,}; output {tokens['output_tokens']:,}; cache read "
            f"{tokens['cache_read_tokens']:,}; cache write {tokens['cache_write_tokens']:,}; "
            f"calls fast/balanced/frontier {tiers['fast']}/{tiers['balanced']}/{tiers['frontier']}; "
            f"search/fetch/other tools {tools['search_calls']}/{tools['fetch_calls']}/"
            f"{tools['other_tool_calls']}; editorial revisions "
            f"{item['optimized']['revisions']['editorial_revisions']}."
        ])
    lines.extend([
        "",
        "## Data provenance",
        "",
    ])
    for item in report["fixtures"]:
        lines.append(
            f"- **{item['fixture_id']}** uses `{item['fixture_kind']}` fixture evidence and "
            f"`{item['telemetry_source_kind']}` controller telemetry. {item['fixture_source']}"
        )
    failed = [item for item in report["fixtures"] if not item["pass"]]
    if failed:
        lines.extend(["", "## Failed checks", ""])
        for item in failed:
            names = [name for name, passed in item["checks"].items() if not passed]
            lines.append(f"- **{item['fixture_id']}**: {', '.join(names)}.")
    lines.append("")
    return "\n".join(lines)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def run_evaluation(
    *, baseline_path: Path, fixtures_path: Path, telemetry_paths: list[Path]
) -> dict[str, Any]:
    baseline = load_baseline(baseline_path)
    fixtures = load_fixtures(fixtures_path)
    telemetry = [load_telemetry(path) for path in telemetry_paths]
    return evaluate(baseline, fixtures, telemetry)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="evaluate one or more controller telemetry exports")
    run.add_argument("--baseline", type=Path, default=EVAL_ROOT / "baseline_context.json")
    run.add_argument("--fixtures", type=Path, default=EVAL_ROOT / "fixtures")
    run.add_argument("--telemetry", type=Path, action="append", required=True)
    run.add_argument("--out-json", type=Path)
    run.add_argument("--out-md", type=Path)
    dry = sub.add_parser("dry-run", help="run the committed synthetic telemetry sample offline")
    dry.add_argument("--out-dir", type=Path, default=ROOT / "out" / "replay-eval")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "dry-run":
        telemetry_paths = sorted((EVAL_ROOT / "telemetry").glob("*.json"))
        baseline_path = EVAL_ROOT / "baseline_context.json"
        fixtures_path = EVAL_ROOT / "fixtures"
        out_json = args.out_dir / "report.json"
        out_md = args.out_dir / "report.md"
    else:
        telemetry_paths = args.telemetry
        baseline_path = args.baseline
        fixtures_path = args.fixtures
        out_json = args.out_json
        out_md = args.out_md
    try:
        report = run_evaluation(
            baseline_path=baseline_path,
            fixtures_path=fixtures_path,
            telemetry_paths=telemetry_paths,
        )
        rendered_json = json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        rendered_md = markdown_report(report)
        if out_json:
            _atomic_write(out_json, rendered_json.encode("utf-8"))
        if out_md:
            _atomic_write(out_md, rendered_md.encode("utf-8"))
        print(
            f"replay_eval: {'PASS' if report['pass'] else 'FAIL'} "
            f"fixtures={report['summary']['fixture_count']} id={report['evaluation_id'][:16]}"
        )
        if out_json or out_md:
            print(f"replay_eval: report_json={out_json or '-'} report_md={out_md or '-'}")
        return 0 if report["pass"] else 1
    except (ReplayEvalError, OSError, ValueError) as exc:
        print(f"replay_eval: invalid input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
