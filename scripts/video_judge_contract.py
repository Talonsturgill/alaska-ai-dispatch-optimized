#!/usr/bin/env python3
"""Strict rubric-derived video judge cards for the parametric canary film.

A judge card is not a scalar score.  It is a closed measurement of one exact
render/evidence/preflight state against every axis in the canonical dispatch
rubric.  This module owns the only terminal video-card schema.
"""
from __future__ import annotations

import hashlib
import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from deliverable_contract import DeliverableContractError, contract_digest, require_manifest
from evidence_contract import EvidenceContractError, evidence_manifest_sha, require_evidence_manifest
from preflight import PreflightContractError, require_preflight_receipt
from run_guard import load_stamp
from strict_json import StrictJSONError, load_path

ROOT = Path(__file__).resolve().parent.parent
RUBRIC_REL = "config/dispatch_rubric.yaml"
RENDER_RECEIPT_REL = "out/dispatch/render/render_receipt.json"
CARD_SCHEMA_VERSION = 1
JUDGE_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,30}[a-z0-9])?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
AXIS_EVIDENCE_CAPABILITIES = {
    "Hook & retention": {"visual", "timeline"},
    "Illustration craft & detail": {"visual"},
    "Motion & animation craft": {"visual", "motion"},
    "Composition & staging": {"visual"},
    "Color & grade": {"visual"},
    "Typography & captions": {"visual", "captions"},
    "Sound design & mix": {"audio"},
    "VO–illustration sync & entertainment": {"visual", "audio", "timeline"},
    "Accuracy & sourcing": {"source_claims"},
    "Alaska authenticity & cultural respect": {"visual", "story"},
    "Writing & story clarity": {"story"},
}


class VideoJudgeContractError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(base: Path, relative: str, *, label: str) -> Path:
    if (
        not isinstance(relative, str) or not relative or not relative.isascii()
        or "\\" in relative or PurePosixPath(relative).is_absolute()
        or any(part in {"", ".", ".."} for part in relative.split("/"))
    ):
        raise VideoJudgeContractError(f"{label} must be a canonical repo-relative POSIX path")
    logical = base.joinpath(*relative.split("/"))
    current = base
    for part in relative.split("/"):
        current = current / part
        if current.is_symlink():
            raise VideoJudgeContractError(f"{label} path may not contain symlinks")
    try:
        logical.resolve(strict=True).relative_to(base)
    except (OSError, ValueError) as exc:
        raise VideoJudgeContractError(f"{label} is missing or unsafe: {exc}") from None
    if not logical.is_file():
        raise VideoJudgeContractError(f"{label} is not a file")
    return logical


def _rubric_subset(path: Path) -> tuple[float, list[dict[str, Any]]]:
    """Parse the authoritative rubric fields without a runtime YAML dependency.

    The repository declares PyYAML for the full automation, but release validation
    also runs in lean verification environments. The rubric's authoritative card
    fields use a deliberately small YAML subset: a scalar threshold followed by an
    ordered list of double-quoted names and numeric weights. This parser validates
    that exact spelling and rejects duplicate keys at the rubric and criterion level.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise VideoJudgeContractError(f"dispatch rubric cannot be read: {exc}") from None
    if sum(1 for line in lines if line.strip() == "rubric:") != 1:
        raise VideoJudgeContractError("dispatch rubric must contain exactly one rubric mapping")
    direct_keys: set[str] = set()
    threshold: float | None = None
    criteria_line: int | None = None
    for index, line in enumerate(lines):
        match = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*):(?:\s|$)", line)
        if not match:
            continue
        key = match.group(1)
        if key in direct_keys:
            raise VideoJudgeContractError(f"dispatch rubric has duplicate key {key!r}")
        direct_keys.add(key)
        value = line.split(":", 1)[1].split("#", 1)[0].strip()
        if key == "ship_threshold":
            try:
                threshold = float(value)
            except (TypeError, ValueError, OverflowError):
                raise VideoJudgeContractError("dispatch rubric ship_threshold is invalid") from None
        elif key == "criteria":
            if value:
                raise VideoJudgeContractError("dispatch rubric criteria must be a block list")
            criteria_line = index
    if threshold is None or criteria_line is None:
        raise VideoJudgeContractError("dispatch rubric needs ship_threshold and criteria")
    axes: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_keys: set[str] = set()
    for line in lines[criteria_line + 1:]:
        if line and not line.startswith("    ") and not line.lstrip().startswith("#"):
            break
        name_match = re.match(r'^    - name:\s*("(?:[^"\\]|\\.)*")\s*$', line)
        if name_match:
            if current is not None:
                axes.append(current)
            try:
                name = json.loads(name_match.group(1))
            except (json.JSONDecodeError, UnicodeError) as exc:
                raise VideoJudgeContractError(f"dispatch rubric axis name is invalid: {exc}") from None
            current = {"name": name}
            current_keys = {"name"}
            continue
        key_match = re.match(r"^      ([A-Za-z0-9_][A-Za-z0-9_-]*):(?:\s|$)", line)
        if not key_match or current is None:
            continue
        key = key_match.group(1)
        if key in current_keys:
            raise VideoJudgeContractError(
                f"dispatch rubric axis {current.get('name')!r} has duplicate key {key!r}"
            )
        current_keys.add(key)
        if key == "weight":
            raw = line.split(":", 1)[1].split("#", 1)[0].strip()
            try:
                current["weight"] = float(raw)
            except (TypeError, ValueError, OverflowError):
                raise VideoJudgeContractError(
                    f"dispatch rubric axis {current.get('name')!r} weight is invalid"
                ) from None
    if current is not None:
        axes.append(current)
    return threshold, axes


def rubric_contract(*, root: str | Path = ROOT) -> dict[str, Any]:
    base = Path(root).resolve()
    path = _inside(base, RUBRIC_REL, label="dispatch rubric")
    threshold, criteria = _rubric_subset(path)
    if (
        isinstance(threshold, bool) or not isinstance(threshold, (int, float))
        or not math.isfinite(float(threshold)) or not 0 <= float(threshold) <= 10
    ):
        raise VideoJudgeContractError("dispatch rubric ship_threshold must be finite in 0..10")
    if not isinstance(criteria, list) or not criteria:
        raise VideoJudgeContractError("dispatch rubric criteria must be a non-empty list")
    axes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, criterion in enumerate(criteria):
        if not isinstance(criterion, dict):
            raise VideoJudgeContractError(f"dispatch rubric criterion {index} must be a mapping")
        name = criterion.get("name")
        weight = criterion.get("weight")
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise VideoJudgeContractError(f"dispatch rubric criterion {index} has invalid name")
        if name in seen:
            raise VideoJudgeContractError(f"dispatch rubric axis is duplicated: {name}")
        if (
            isinstance(weight, bool) or not isinstance(weight, (int, float))
            or not math.isfinite(float(weight)) or float(weight) <= 0
        ):
            raise VideoJudgeContractError(f"dispatch rubric axis {name} has invalid weight")
        seen.add(name)
        axes.append({"name": name, "weight": float(weight)})
    total_weight = sum(axis["weight"] for axis in axes)
    if abs(total_weight - 1.0) > 1e-9:
        raise VideoJudgeContractError(
            f"dispatch rubric axis weights must total 1.0, got {total_weight:.12g}"
        )
    if {axis["name"] for axis in axes} != set(AXIS_EVIDENCE_CAPABILITIES):
        raise VideoJudgeContractError(
            "dispatch rubric axes do not match the closed video evidence capability map"
        )
    return {
        "path": RUBRIC_REL,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "ship_threshold": float(threshold),
        "axes": axes,
    }


def current_binding(*, root: str | Path = ROOT) -> tuple[dict[str, Any], set[str]]:
    base = Path(root).resolve()
    stamp = load_stamp(base)
    if not isinstance(stamp, dict):
        raise VideoJudgeContractError("run stamp is missing or unreadable")
    try:
        delivery = require_manifest(root=base)
        evidence = require_evidence_manifest(root=base, delivery_manifest=delivery)
        preflight = require_preflight_receipt(root=base)
    except (DeliverableContractError, EvidenceContractError, PreflightContractError) as exc:
        raise VideoJudgeContractError(f"terminal judge inputs are invalid: {exc}") from None
    render_path = _inside(base, RENDER_RECEIPT_REL, label="render receipt")
    render = delivery.get("render")
    if not isinstance(render, dict) or not SHA256_RE.fullmatch(
        str(render.get("render_binding_sha256", ""))
    ):
        raise VideoJudgeContractError("delivery manifest has no canonical render binding")
    binding = {
        "run_id": stamp.get("run_id"),
        "run_date": stamp.get("date"),
        "composition": stamp.get("composition"),
        "render_receipt_sha256": sha256_file(render_path),
        "render_binding_sha256": render["render_binding_sha256"],
        "delivery_manifest_digest": contract_digest(delivery),
        "evidence_manifest_sha256": evidence_manifest_sha(root=base),
        "evidence_delivery_manifest_digest": evidence.get("delivery_manifest_digest"),
        "preflight_receipt_sha256": preflight.get("sha256"),
    }
    if any(not isinstance(binding[key], str) or not binding[key] for key in binding):
        raise VideoJudgeContractError("current judge binding is incomplete")
    allowed = set(evidence.get("expected_artifacts", []))
    if not allowed or any(not isinstance(value, str) for value in allowed):
        raise VideoJudgeContractError("evidence manifest has no canonical expected artifact set")
    return binding, allowed


def _finite_score(value: Any, *, label: str) -> float:
    if (
        isinstance(value, bool) or not isinstance(value, (int, float))
        or not math.isfinite(float(value)) or not 0 <= float(value) <= 10
    ):
        raise VideoJudgeContractError(f"{label} must be finite in 0..10")
    return float(value)


def _evidence_list(value: Any, *, allowed: set[str], label: str) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise VideoJudgeContractError(f"{label} must contain at least one evidence observation")
    normalized: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"artifact", "observation"}:
            raise VideoJudgeContractError(f"{label}[{index}] fields are not canonical")
        artifact, observation = item.get("artifact"), item.get("observation")
        if artifact not in allowed:
            raise VideoJudgeContractError(
                f"{label}[{index}] names non-manifest evidence artifact {artifact!r}"
            )
        if not isinstance(observation, str) or not observation.strip():
            raise VideoJudgeContractError(f"{label}[{index}] observation is empty")
        normalized.append({"artifact": artifact, "observation": observation.strip()})
    return normalized


def _artifact_capabilities(path: str) -> set[str]:
    name = PurePosixPath(path).name.lower()
    suffix = PurePosixPath(path).suffix.lower()
    capabilities: set[str] = set()
    if name == "audio_report.json":
        capabilities.update({"audio", "timeline"})
    elif name == "audio_card.png":
        capabilities.update({"audio", "timeline"})
    elif name == "caption_cues.json":
        capabilities.update({"captions", "timeline", "story"})
    elif name == "motion.json":
        capabilities.update({"visual", "motion", "timeline"})
    elif name == "story_claims_sources.json":
        capabilities.update({"story", "source_claims"})
    elif suffix in {".jpg", ".jpeg", ".png"}:
        capabilities.add("visual")
        if "strip" in name:
            capabilities.update({"motion", "timeline"})
    return capabilities


def _require_axis_evidence_capabilities(
    axis_name: str, evidence: list[dict[str, str]], *, label: str,
) -> None:
    required = AXIS_EVIDENCE_CAPABILITIES.get(axis_name)
    if required is None:
        raise VideoJudgeContractError(f"{label} has no canonical evidence capability rule")
    actual: set[str] = set()
    for observation in evidence:
        actual.update(_artifact_capabilities(observation["artifact"]))
    missing = sorted(required - actual)
    if missing:
        raise VideoJudgeContractError(
            f"{label} lacks required evidence capabilities: {', '.join(missing)}"
        )


def computed_total(axes: list[dict[str, Any]]) -> float:
    return round(sum(float(axis["score"]) * float(axis["weight"]) for axis in axes), 6)


def validate_card(
    path: str | Path,
    *,
    root: str | Path = ROOT,
    binding: dict[str, Any] | None = None,
    rubric: dict[str, Any] | None = None,
    allowed_evidence: set[str] | None = None,
) -> dict[str, Any]:
    base = Path(root).resolve()
    target = Path(path)
    if not target.is_absolute():
        target = base / target
    try:
        resolved = target.resolve(strict=True)
        resolved.relative_to(base)
    except (OSError, ValueError) as exc:
        raise VideoJudgeContractError(f"judge card is missing or outside the repository: {exc}") from None
    if target.is_symlink() or not resolved.is_file():
        raise VideoJudgeContractError("judge card is missing or unsafe")
    try:
        card = load_path(resolved, label="video judge card")
    except (StrictJSONError, OSError) as exc:
        raise VideoJudgeContractError(str(exc)) from None
    if not isinstance(card, dict):
        raise VideoJudgeContractError("video judge card must be a JSON object")
    expected_fields = {
        "schema_version", "judge_id", "binding", "rubric", "axes",
        "weighted_total", "hard_blockers",
    }
    if set(card) != expected_fields or card.get("schema_version") != CARD_SCHEMA_VERSION:
        raise VideoJudgeContractError("video judge card fields/schema are not canonical")
    judge_id = card.get("judge_id")
    if not isinstance(judge_id, str) or not JUDGE_ID_RE.fullmatch(judge_id):
        raise VideoJudgeContractError("judge_id must be lowercase ASCII letters/digits/_/-")
    if binding is None or allowed_evidence is None:
        binding, allowed_evidence = current_binding(root=base)
    if rubric is None:
        rubric = rubric_contract(root=base)
    if card.get("binding") != binding:
        raise VideoJudgeContractError(f"judge card {judge_id} is bound to different run bytes")
    if card.get("rubric") != rubric:
        raise VideoJudgeContractError(f"judge card {judge_id} rubric/weights/threshold drifted")
    axes = card.get("axes")
    if not isinstance(axes, list) or len(axes) != len(rubric["axes"]):
        raise VideoJudgeContractError(f"judge card {judge_id} must contain every rubric axis exactly once")
    normalized_axes: list[dict[str, Any]] = []
    for index, (axis, expected) in enumerate(zip(axes, rubric["axes"])):
        if not isinstance(axis, dict) or set(axis) != {"name", "weight", "score", "evidence"}:
            raise VideoJudgeContractError(f"judge card {judge_id} axis {index} fields are not canonical")
        if axis.get("name") != expected["name"]:
            raise VideoJudgeContractError(f"judge card {judge_id} has missing/extra/reordered rubric axes")
        if axis.get("weight") != expected["weight"]:
            raise VideoJudgeContractError(f"judge card {judge_id} axis {expected['name']} weight drifted")
        normalized_evidence = _evidence_list(
            axis.get("evidence"), allowed=allowed_evidence,
            label=f"{judge_id}.{expected['name']} evidence",
        )
        _require_axis_evidence_capabilities(
            expected["name"], normalized_evidence,
            label=f"{judge_id}.{expected['name']} evidence",
        )
        normalized_axes.append({
            "name": expected["name"],
            "weight": expected["weight"],
            "score": _finite_score(axis.get("score"), label=f"{judge_id}.{expected['name']} score"),
            "evidence": normalized_evidence,
        })
    wanted_total = computed_total(normalized_axes)
    total = _finite_score(card.get("weighted_total"), label=f"{judge_id}.weighted_total")
    if abs(total - wanted_total) > 1e-9:
        raise VideoJudgeContractError(
            f"judge card {judge_id} weighted_total is {total}, recomputed {wanted_total}"
        )
    blockers = card.get("hard_blockers")
    if not isinstance(blockers, list):
        raise VideoJudgeContractError(f"judge card {judge_id} hard_blockers must be a list")
    axis_names = {axis["name"] for axis in rubric["axes"]}
    for index, blocker in enumerate(blockers):
        if not isinstance(blocker, dict) or set(blocker) != {"axis", "what", "evidence"}:
            raise VideoJudgeContractError(f"judge card {judge_id} blocker {index} fields are not canonical")
        if blocker.get("axis") not in axis_names:
            raise VideoJudgeContractError(f"judge card {judge_id} blocker {index} has unknown axis")
        if not isinstance(blocker.get("what"), str) or not blocker["what"].strip():
            raise VideoJudgeContractError(f"judge card {judge_id} blocker {index} is empty")
        blocker_evidence = _evidence_list(
            blocker.get("evidence"), allowed=allowed_evidence,
            label=f"{judge_id}.hard_blockers[{index}].evidence",
        )
        _require_axis_evidence_capabilities(
            blocker["axis"], blocker_evidence,
            label=f"{judge_id}.hard_blockers[{index}].evidence",
        )
    return card


def require_three_cards(
    paths: list[str | Path] | tuple[str | Path, ...],
    *,
    root: str | Path = ROOT,
    binding: dict[str, Any] | None = None,
    rubric: dict[str, Any] | None = None,
    allowed_evidence: set[str] | None = None,
) -> list[dict[str, Any]]:
    if not isinstance(paths, (list, tuple)) or len(paths) != 3:
        raise VideoJudgeContractError("terminal panel requires exactly three video judge card paths")
    base = Path(root).resolve()
    resolved = []
    for path in paths:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = base / candidate
        try:
            normalized = candidate.resolve(strict=True)
            normalized.relative_to(base)
        except (OSError, ValueError) as exc:
            raise VideoJudgeContractError(f"judge card path is missing or unsafe: {exc}") from None
        resolved.append(normalized)
    if len(set(resolved)) != 3:
        raise VideoJudgeContractError("terminal panel requires three unique judge card paths")
    if binding is None or allowed_evidence is None:
        binding, allowed_evidence = current_binding(root=base)
    if rubric is None:
        rubric = rubric_contract(root=base)
    cards = [
        validate_card(
            path, root=base, binding=binding, rubric=rubric,
            allowed_evidence=allowed_evidence,
        )
        for path in resolved
    ]
    ids = [card["judge_id"] for card in cards]
    if len(set(ids)) != 3:
        raise VideoJudgeContractError("terminal panel requires exactly three unique judge IDs")
    return [
        {
            "path": path.relative_to(base).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "judge_id": card["judge_id"],
            "weighted_total": computed_total(card["axes"]),
            "hard_blockers": card["hard_blockers"],
        }
        for path, card in zip(resolved, cards)
    ]


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("context", help="print current binding/rubric/evidence paths for judges")
    check = sub.add_parser("check", help="validate one strict video judge card")
    check.add_argument("--card", required=True)
    panel = sub.add_parser("panel", help="validate exactly three unique video judge cards")
    panel.add_argument("--cards", nargs=3, required=True)
    args = parser.parse_args()
    try:
        if args.command == "context":
            binding, allowed = current_binding()
            print(json.dumps({
                "schema_version": CARD_SCHEMA_VERSION,
                "binding": binding,
                "rubric": rubric_contract(),
                "allowed_evidence": sorted(allowed),
            }, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
            return 0
        if args.command == "check":
            card = validate_card(args.card)
            print(f"video_judge_contract: PASS {card['judge_id']} {card['weighted_total']:.6f}")
            return 0
        cards = require_three_cards(args.cards)
        totals = [card["weighted_total"] for card in cards]
        blockers = sum(len(card["hard_blockers"]) for card in cards)
        print(
            f"video_judge_contract: PASS ids={[card['judge_id'] for card in cards]} "
            f"totals={totals} median={statistics.median(totals):.6f} blockers={blockers}"
        )
        return 0 if blockers == 0 else 1
    except (VideoJudgeContractError, OSError, TypeError, ValueError) as exc:
        print(f"video_judge_contract: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
