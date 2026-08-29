#!/usr/bin/env python3
"""Two-stage, hash-bound run identity and freshness guard for DispatchDaily.

`init` creates a planning identity before story/source authoring.  It deliberately
does not bless mutable render inputs.  `bind-render-inputs` is the explicit
post-authoring boundary that binds registry, Root, every engine source and render
input, props, branch and HEAD.  Render, artifact, evidence and delivery consumers
require that bound state.  There are no clock, newest-file, generic-Dispatch or
copied-stamp fallbacks.
"""
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
import time
from pathlib import Path, PurePosixPath
from typing import Any

from strict_json import StrictJSONError, canonical_bytes, load_path

STAMP_REL = "out/dispatch/.run_stamp.json"
REGISTRY_REL = "config/compositions.json"
ROOT_SOURCE_REL = "video-engine/src/Root.tsx"
POLICY_REL = "config/execution_policy.json"
STAMP_SCHEMA_VERSION = 4
ACTIVE_COMPOSITION = "DispatchDaily"
COMPOSITION_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:$|[-_])")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_HEAD_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
SHIP_MARKER_RELS = (
    "out/dispatch/SHIP_NOW",
    "out/dispatch/SHIP_NOW.json",
    "out/dispatch/panel_verdict.json",
    "out/dispatch/preflight_receipt.json",
    "out/dispatch/delivery_preview_receipt.json",
)


class StaleArtifactError(RuntimeError):
    """The requested artifact cannot be proven to belong to this run."""


class RunIdentityError(RuntimeError):
    """The run stamp does not identify this exact checkout and input set."""


def _base(root: str | Path | None = None) -> Path:
    return (Path(root) if root is not None else Path.cwd()).resolve()


def _stamp_path(root: str | Path | None = None) -> Path:
    return _base(root) / STAMP_REL


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _engine_sources_sha(root: Path) -> str:
    """Hash every TS/TSX input, including paths, so transitive source drift is visible."""
    source_root = _resolve_inside(root, "video-engine/src", label="engine source directory")
    files: list[Path] = []
    for candidate in source_root.rglob("*"):
        if candidate.suffix not in (".ts", ".tsx") or not candidate.is_file():
            continue
        if candidate.is_symlink():
            raise RunIdentityError("engine source files may not be symlinks")
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            raise RunIdentityError("engine source file escapes the repository") from None
        files.append(resolved)
    if not files:
        raise RunIdentityError("video-engine/src contains no TypeScript sources")
    digest = hashlib.sha256()
    for path in sorted(files, key=lambda item: item.relative_to(root).as_posix()):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _render_inputs(root: Path, registry: dict[str, Any]) -> dict[str, str]:
    """Hash non-source files that can change how identical source/props render."""
    values = registry.get("render_inputs")
    if not isinstance(values, list) or not values or any(not isinstance(v, str) for v in values):
        raise RunIdentityError("composition registry render_inputs must be a non-empty path list")
    canonical = [_safe_rel(value, label="render input") for value in values]
    if len(canonical) != len(set(canonical)):
        raise RunIdentityError("composition registry render_inputs may not contain duplicates")
    facts: dict[str, str] = {}
    for relative in canonical:
        path = _resolve_inside(root, relative, label=f"render input {relative}")
        if not path.is_file() or path.is_symlink():
            raise RunIdentityError(f"render input {relative} must be a regular file")
        facts[relative] = _sha(path)
    return facts


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise RunIdentityError(f"git {' '.join(args)} failed: {detail[-1] if detail else 'unknown error'}")
    return result.stdout.strip()


def _is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", ancestor, descendant],
        capture_output=True, text=True, timeout=20,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    detail = (result.stderr or result.stdout).strip().splitlines()
    raise RunIdentityError(
        f"git ancestry check failed: {detail[-1] if detail else 'unknown error'}"
    )


def _origin_identity(root: Path) -> str:
    origin = _canonical_origin(_git(root, "remote", "get-url", "origin"))
    configured_push = subprocess.run(
        ["git", "-C", str(root), "config", "--get-all", "remote.origin.pushurl"],
        capture_output=True, text=True, timeout=20,
    )
    if configured_push.returncode not in (0, 1):
        raise RunIdentityError("could not inspect origin pushurl")
    if configured_push.stdout.strip():
        raise RunIdentityError("origin may not have a configured pushurl")
    raw_push = [
        line for line in _git(root, "remote", "get-url", "--push", "--all", "origin").splitlines()
        if line
    ]
    if len(raw_push) != 1 or _canonical_origin(raw_push[0]) != origin:
        raise RunIdentityError("origin must resolve to exactly one identical push URL")
    return origin


def _canonical_origin(value: str) -> str:
    text = value.strip()
    match = re.fullmatch(r"https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?", text, re.I)
    if not match:
        raise RunIdentityError("origin must be one canonical https://github.com/owner/repository.git URL")
    return f"https://github.com/{match.group(1)}/{match.group(2)}.git"


def _repo_slug(origin: str) -> str:
    match = re.fullmatch(r"https://github\.com/([^/]+)/([^/]+)\.git", origin, re.I)
    if not match:
        raise RunIdentityError("cannot derive repository identity from origin")
    return f"{match.group(1)}/{match.group(2)}"


def _safe_rel(value: str, *, label: str) -> str:
    if (
        not isinstance(value, str) or not value or not value.isascii() or "\\" in value
        or not SAFE_PATH_RE.fullmatch(value) or re.match(r"^[A-Za-z]:", value)
    ):
        raise RunIdentityError(f"{label} must be a non-empty ASCII repo-relative POSIX path")
    pure = PurePosixPath(value)
    if (
        pure.is_absolute() or ".." in pure.parts or any(part in ("", ".") for part in pure.parts)
        or pure.as_posix() != value
    ):
        raise RunIdentityError(f"{label} must stay inside the repository")
    return pure.as_posix()


def _resolve_inside(root: Path, relative: str, *, label: str, must_exist: bool = True) -> Path:
    rel = _safe_rel(relative, label=label)
    candidate = root.joinpath(*PurePosixPath(rel).parts)
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as exc:
        raise RunIdentityError(f"{label} cannot be resolved: {exc}") from None
    try:
        resolved.relative_to(root)
    except ValueError:
        raise RunIdentityError(f"{label} escapes the repository") from None
    if candidate.is_symlink():
        raise RunIdentityError(f"{label} may not be a symlink")
    return resolved


def _registry(root: Path) -> tuple[dict[str, Any], Path]:
    path = _resolve_inside(root, REGISTRY_REL, label="composition registry")
    value = load_path(path, label="composition registry")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise RunIdentityError("composition registry must be a schema_version 1 object")
    compositions = value.get("compositions")
    if not isinstance(compositions, dict):
        raise RunIdentityError("composition registry.compositions must be an object")
    if value.get("active_composition") != ACTIVE_COMPOSITION:
        raise RunIdentityError(f"composition registry active_composition must be {ACTIVE_COMPOSITION}")
    active = [
        name for name, record in compositions.items()
        if isinstance(record, dict) and record.get("status") == "active"
    ]
    if active != [ACTIVE_COMPOSITION]:
        raise RunIdentityError(f"composition registry must mark only {ACTIVE_COMPOSITION} active")
    for name in compositions:
        if not isinstance(name, str) or not name.isascii() or not COMPOSITION_RE.fullmatch(name):
            raise RunIdentityError("every registered composition key must be an ASCII identifier")
    _render_inputs(root, value)
    return value, path


def composition_record(composition: str, root: str | Path | None = None) -> dict[str, Any]:
    base = _base(root)
    if not isinstance(composition, str) or not composition.isascii() or not COMPOSITION_RE.fullmatch(composition):
        raise RunIdentityError("composition must be a case-sensitive ASCII identifier")
    registry, _ = _registry(base)
    record = registry["compositions"].get(composition)
    if not isinstance(record, dict):
        raise RunIdentityError(f"composition {composition!r} is not registered")
    if composition == ACTIVE_COMPOSITION and record.get("status") != "active":
        raise RunIdentityError(f"{ACTIVE_COMPOSITION} must be the one active composition")
    if composition != ACTIVE_COMPOSITION and record.get("status") != "legacy":
        raise RunIdentityError(f"non-active composition {composition!r} must be explicitly legacy")
    source = _safe_rel(record.get("source", ""), label=f"source for {composition}")
    _resolve_inside(base, source, label=f"source for {composition}")
    dependencies = record.get("source_dependencies", [])
    if not isinstance(dependencies, list) or any(not isinstance(item, str) for item in dependencies):
        raise RunIdentityError("composition source_dependencies must be a list of paths")
    canonical_dependencies = [_safe_rel(item, label="composition dependency") for item in dependencies]
    if len(canonical_dependencies) != len(set(canonical_dependencies)):
        raise RunIdentityError("composition source_dependencies may not contain duplicates")
    if composition == ACTIVE_COMPOSITION:
        _safe_rel(record.get("props", ""), label=f"props for {composition}")
    return record


def _root_registration(root: Path, composition: str, component: str) -> None:
    path = _resolve_inside(root, ROOT_SOURCE_REL, label="Root.tsx")
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        r'<Composition\s+id="' + re.escape(composition) + r'"\s+component=\{' + re.escape(component) + r'\}',
        re.MULTILINE,
    )
    count = len(pattern.findall(text))
    if count != 1:
        raise RunIdentityError(
            f"Root.tsx must register {composition} with component {component} exactly once (found {count})"
        )
    if re.search(r'<Composition\s+id="Dispatch"\b', text):
        raise RunIdentityError("Root.tsx may not register the retired generic Dispatch composition")


def _policy_identity(root: Path) -> tuple[str, str]:
    policy = load_path(_resolve_inside(root, POLICY_REL, label="execution policy"), label="execution policy")
    if not isinstance(policy, dict):
        raise RunIdentityError("execution policy must be an object")
    mode = policy.get("mode")
    repository = policy.get("canary_repository")
    if mode != "canary" or not isinstance(repository, str) or not repository:
        raise RunIdentityError("execution policy must name this canary repository in canary mode")
    return mode, repository


def _date_for(run_id: str, run_date: str | None) -> str:
    if not isinstance(run_id, str) or not run_id.strip() or not run_id.isascii():
        raise RunIdentityError("run_id must be a non-empty ASCII string")
    match = DATE_RE.match(run_id)
    value = run_date or (match.group(1) if match else None)
    if not value or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise RunIdentityError("date is required unless run_id begins with YYYY-MM-DD")
    try:
        if dt.date.fromisoformat(value).isoformat() != value:
            raise ValueError
    except ValueError:
        raise RunIdentityError("date must be a real calendar date in YYYY-MM-DD form") from None
    return value


def render_binding_digest(stamp: dict[str, Any]) -> str:
    """Digest only pixel-affecting bound inputs, never wall-clock or run metadata."""
    if not isinstance(stamp, dict) or stamp.get("binding_state") != "render_bound":
        raise RunIdentityError("render inputs are not bound")
    value = {
        "composition": stamp.get("composition"),
        "registry": {"path": stamp.get("registry_path"), "sha256": stamp.get("registry_sha256")},
        "root": {"path": stamp.get("root_source_path"), "sha256": stamp.get("root_source_sha256")},
        "source": {"path": stamp.get("source_path"), "sha256": stamp.get("source_sha256")},
        "source_dependencies": stamp.get("source_dependencies"),
        "engine_sources_sha256": stamp.get("engine_sources_sha256"),
        "render_inputs": stamp.get("render_inputs"),
        "props": {"path": stamp.get("props_path"), "sha256": stamp.get("props_sha256")},
    }
    try:
        digest = hashlib.sha256(canonical_bytes(value)).hexdigest()
    except StrictJSONError as exc:
        raise RunIdentityError(f"render binding cannot be represented canonically: {exc}") from None
    return digest


def _clear_ship_markers(root: Path) -> None:
    """Earlier identity receipts must never control a newly planned run."""
    for relative in SHIP_MARKER_RELS:
        target = root.joinpath(*relative.split("/"))
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        except IsADirectoryError:
            raise RunIdentityError(f"stale ship marker path is a directory: {relative}") from None


def init(
    run_id: str,
    composition: str,
    *,
    run_date: str | None = None,
    props: str | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Create a planning stamp; render inputs remain deliberately unbound."""
    base = _base(root)
    record = composition_record(composition, base)
    if composition != ACTIVE_COMPOSITION:
        raise RunIdentityError(f"new runs must use {ACTIVE_COMPOSITION}; {composition} is legacy")
    component = record.get("component")
    if not isinstance(component, str) or not component:
        raise RunIdentityError(f"composition {composition} has no component")
    _root_registration(base, composition, component)
    _resolve_inside(base, REGISTRY_REL, label="composition registry")
    _registry(base)
    _resolve_inside(base, ROOT_SOURCE_REL, label="Root.tsx")
    source_rel = _safe_rel(record["source"], label="composition source")
    _resolve_inside(base, source_rel, label="composition source")
    registered_props = _safe_rel(record.get("props", ""), label="registered props")
    props_rel = _safe_rel(props, label="props") if props is not None else registered_props
    if props_rel != registered_props:
        raise RunIdentityError(
            f"{ACTIVE_COMPOSITION} props must use the registered path {registered_props}"
        )
    props_path = _resolve_inside(base, props_rel, label="props", must_exist=False)
    origin = _origin_identity(base)
    mode, policy_repository = _policy_identity(base)
    repository = _repo_slug(origin)
    if repository.lower() != policy_repository.lower():
        raise RunIdentityError("origin repository does not match execution policy")
    branch = _git(base, "branch", "--show-current")
    if not branch:
        raise RunIdentityError("detached HEAD is not a valid run identity")
    planning_head = _git(base, "rev-parse", "HEAD")
    stamp: dict[str, Any] = {
        "schema_version": STAMP_SCHEMA_VERSION,
        "run_id": run_id,
        "date": _date_for(run_id, run_date),
        "composition": composition,
        "mode": mode,
        "repository": repository,
        "origin": origin,
        "worktree_root": str(base),
        "branch": branch,
        "planning_git_head": planning_head,
        "git_head": planning_head,
        "started_at": time.time(),
        "binding_state": "planning",
        "bound_at": None,
        "registry_path": REGISTRY_REL,
        "registry_sha256": None,
        "root_source_path": ROOT_SOURCE_REL,
        "root_source_sha256": None,
        "source_path": source_rel,
        "source_sha256": None,
        "source_dependencies": {},
        "engine_sources_sha256": None,
        "render_inputs": {},
        "props_path": props_rel,
        "props_sha256": None,
        "render_binding_sha256": None,
    }
    _clear_ship_markers(base)
    _atomic_json(_stamp_path(base), stamp)
    return stamp


def load_stamp(root: str | Path | None = None) -> dict[str, Any] | None:
    path = _stamp_path(root)
    if not path.is_file():
        return None
    try:
        value = load_path(path, label="run stamp")
    except StrictJSONError:
        return None
    return value if isinstance(value, dict) else None


def _identity_problems(
    root: Path, stamp: dict[str, Any], *, expected_composition: str | None = None,
    require_bound: bool = True,
) -> list[str]:
    problems: list[str] = []
    required = {
        "schema_version", "run_id", "date", "composition", "mode", "repository", "origin",
        "worktree_root", "branch", "planning_git_head", "git_head", "started_at",
        "binding_state", "bound_at", "registry_path",
        "registry_sha256", "root_source_path", "root_source_sha256", "source_path",
        "source_sha256", "source_dependencies", "props_path", "props_sha256",
        "engine_sources_sha256", "render_inputs", "render_binding_sha256",
    }
    missing = sorted(required - set(stamp))
    if missing:
        return ["run stamp is missing: " + ", ".join(missing)]
    unknown = sorted(set(stamp) - required)
    if unknown:
        problems.append("run stamp has unknown fields: " + ", ".join(unknown))
    for field in (
        "run_id", "date", "composition", "mode", "repository", "origin", "worktree_root",
        "branch", "planning_git_head", "git_head", "registry_path", "root_source_path",
        "source_path", "props_path",
    ):
        if not isinstance(stamp.get(field), str) or not stamp[field]:
            problems.append(f"run stamp {field} must be a non-empty string")

    def positive_number(value: Any) -> bool:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        try:
            return math.isfinite(float(value)) and float(value) > 0
        except (TypeError, ValueError, OverflowError):
            return False

    if not positive_number(stamp.get("started_at")):
        problems.append("run stamp started_at must be a finite positive number")
    for field in ("planning_git_head", "git_head"):
        if not isinstance(stamp.get(field), str) or not GIT_HEAD_RE.fullmatch(stamp[field]):
            problems.append(f"run stamp {field} must be a full lowercase Git object ID")
    state = stamp.get("binding_state")
    if state not in ("planning", "render_bound"):
        problems.append("run stamp binding_state must be planning or render_bound")
    if require_bound and state != "render_bound":
        problems.append("render inputs are not bound; run bind-render-inputs after authoring")
    hash_fields = (
        "registry_sha256", "root_source_sha256", "source_sha256",
        "engine_sources_sha256", "props_sha256", "render_binding_sha256",
    )
    if state == "planning":
        if stamp.get("git_head") != stamp.get("planning_git_head"):
            problems.append("planning stamp git_head must equal planning_git_head")
        if stamp.get("bound_at") is not None:
            problems.append("planning stamp bound_at must be null")
        for field in hash_fields:
            if stamp.get(field) is not None:
                problems.append(f"planning stamp {field} must be null until bind-render-inputs")
        if stamp.get("source_dependencies") != {}:
            problems.append("planning stamp source_dependencies must be empty")
        if stamp.get("render_inputs") != {}:
            problems.append("planning stamp render_inputs must be empty")
    elif state == "render_bound":
        if not positive_number(stamp.get("bound_at")):
            problems.append("render-bound stamp bound_at must be a finite positive number")
        for field in hash_fields:
            if not isinstance(stamp.get(field), str) or not SHA256_RE.fullmatch(stamp[field]):
                problems.append(f"run stamp {field} must be a lowercase SHA-256")
    try:
        _date_for(str(stamp.get("run_id", "")), str(stamp.get("date", "")))
    except RunIdentityError as exc:
        problems.append(str(exc))
    if stamp.get("schema_version") != STAMP_SCHEMA_VERSION:
        problems.append(f"run stamp schema_version must be {STAMP_SCHEMA_VERSION}")
    composition = stamp.get("composition")
    if expected_composition is not None and composition != expected_composition:
        problems.append(f"run stamp composition is {composition!r}, expected {expected_composition!r}")
    if composition != ACTIVE_COMPOSITION:
        problems.append(f"active run composition must be exactly {ACTIVE_COMPOSITION!r}")
    if stamp.get("worktree_root") != str(root):
        problems.append("run stamp belongs to a different worktree root")
    record: dict[str, Any] = {}
    try:
        record = composition_record(str(composition), root)
        _root_registration(root, str(composition), str(record.get("component", "")))
    except (RunIdentityError, StrictJSONError) as exc:
        problems.append(str(exc))
    checks = (
        ("origin", lambda: _origin_identity(root)),
        ("branch", lambda: _git(root, "branch", "--show-current")),
    )
    for field, current in checks:
        try:
            if stamp.get(field) != current():
                problems.append(f"{field} changed since run init")
        except RunIdentityError as exc:
            problems.append(str(exc))
    try:
        current_head = _git(root, "rev-parse", "HEAD")
        stamped_head = str(
            stamp.get("git_head" if state == "render_bound" else "planning_git_head", "")
        )
        if current_head != stamped_head and not _is_ancestor(root, stamped_head, current_head):
            problems.append("current HEAD is not equal to or a descendant of stamped git_head")
    except RunIdentityError as exc:
        problems.append(str(exc))
    dependencies = stamp.get("source_dependencies")
    if not isinstance(dependencies, dict):
        problems.append("run stamp source_dependencies must be an object")
    elif state == "render_bound":
        expected_dependencies = record.get("source_dependencies", []) if isinstance(record, dict) else []
        if not isinstance(expected_dependencies, list) or set(dependencies) != set(expected_dependencies):
            problems.append("run stamp composition dependency set does not match the registry")
        for relative, expected_hash in dependencies.items():
            if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
                problems.append(f"composition dependency {relative} has an invalid stamped hash")
                continue
            try:
                path = _resolve_inside(root, str(relative), label="composition dependency")
                if _sha(path) != expected_hash:
                    problems.append(f"composition dependency {relative} changed since render binding")
            except RunIdentityError as exc:
                problems.append(str(exc))
    try:
        mode, repository = _policy_identity(root)
        if stamp.get("mode") != mode:
            problems.append("execution mode changed since run init")
        if str(stamp.get("repository", "")).lower() != repository.lower():
            problems.append("repository identity changed since run init")
    except (RunIdentityError, StrictJSONError) as exc:
        problems.append(str(exc))
    if state == "render_bound":
        for path_field, hash_field, label in (
            ("registry_path", "registry_sha256", "composition registry"),
            ("root_source_path", "root_source_sha256", "Root.tsx"),
            ("source_path", "source_sha256", "composition source"),
        ):
            try:
                path = _resolve_inside(root, str(stamp.get(path_field, "")), label=label)
                if _sha(path) != stamp.get(hash_field):
                    problems.append(f"{label} changed since render binding")
            except RunIdentityError as exc:
                problems.append(str(exc))
    if stamp.get("registry_path") != REGISTRY_REL:
        problems.append("run stamp registry_path is not canonical")
    if stamp.get("root_source_path") != ROOT_SOURCE_REL:
        problems.append("run stamp root_source_path is not canonical")
    if isinstance(record, dict):
        if stamp.get("source_path") != record.get("source"):
            problems.append("run stamp source_path does not match the registry")
        if stamp.get("props_path") != record.get("props"):
            problems.append("run stamp props_path does not match the registry")
    if state == "render_bound":
        try:
            if _engine_sources_sha(root) != stamp.get("engine_sources_sha256"):
                problems.append("engine source tree changed since render binding")
        except RunIdentityError as exc:
            problems.append(str(exc))
    render_inputs = stamp.get("render_inputs")
    if not isinstance(render_inputs, dict):
        problems.append("run stamp render_inputs must be an object")
    elif state == "render_bound":
        try:
            registry, _ = _registry(root)
            current_render_inputs = _render_inputs(root, registry)
            if render_inputs != current_render_inputs:
                problems.append("bound render inputs changed since render binding")
        except RunIdentityError as exc:
            problems.append(str(exc))
    if state == "render_bound":
        try:
            props_path = _resolve_inside(
                root, str(stamp.get("props_path", "")), label="props", must_exist=False
            )
            want = stamp.get("props_sha256")
            if not props_path.is_file():
                problems.append("hash-bound props file is missing")
            elif _sha(props_path) != want:
                problems.append("props changed since render binding")
        except RunIdentityError as exc:
            problems.append(str(exc))
        try:
            if stamp.get("render_binding_sha256") != render_binding_digest(stamp):
                problems.append("render binding digest does not match the stamped inputs")
        except RunIdentityError as exc:
            problems.append(str(exc))
    return problems


def check_identity(
    *, root: str | Path | None = None, expected_composition: str | None = None,
    require_props: bool = True,
) -> tuple[bool, str]:
    base = _base(root)
    path = _stamp_path(base)
    if not path.is_file():
        return False, f"run not stamped (no {STAMP_REL})"
    try:
        raw = load_path(path, label="run stamp")
    except StrictJSONError as exc:
        return False, str(exc)
    if not isinstance(raw, dict):
        return False, "run stamp must be a JSON object"
    problems = _identity_problems(
        base, raw, expected_composition=expected_composition, require_bound=require_props
    )
    message = (
        "run identity and render binding match checkout and inputs"
        if require_props else "planning identity matches checkout"
    )
    return (False, "; ".join(problems)) if problems else (True, message)


def bind_render_inputs(*, root: str | Path | None = None) -> dict[str, Any]:
    """Atomically bind every pixel-affecting input after authoring is complete."""
    base = _base(root)
    path = _stamp_path(base)
    raw = load_path(path, label="run stamp")
    if not isinstance(raw, dict):
        raise RunIdentityError("run stamp must be a JSON object")
    problems = _identity_problems(base, raw, require_bound=False)
    if problems:
        raise RunIdentityError("; ".join(problems))
    if raw.get("binding_state") == "render_bound":
        return raw
    record = composition_record(str(raw["composition"]), base)
    _root_registration(base, str(raw["composition"]), str(record.get("component", "")))
    registry, registry_path = _registry(base)
    root_source = _resolve_inside(base, ROOT_SOURCE_REL, label="Root.tsx")
    source_rel = _safe_rel(record.get("source", ""), label="composition source")
    source = _resolve_inside(base, source_rel, label="composition source")
    dependencies: dict[str, str] = {}
    for item in record.get("source_dependencies", []):
        relative = _safe_rel(item, label="composition dependency")
        dependencies[relative] = _sha(
            _resolve_inside(base, relative, label="composition dependency")
        )
    props = _resolve_inside(base, str(raw["props_path"]), label="props")
    raw.update(
        {
            "binding_state": "render_bound",
            "bound_at": time.time(),
            "git_head": _git(base, "rev-parse", "HEAD"),
            "registry_sha256": _sha(registry_path),
            "root_source_sha256": _sha(root_source),
            "source_path": source_rel,
            "source_sha256": _sha(source),
            "source_dependencies": dependencies,
            "engine_sources_sha256": _engine_sources_sha(base),
            "render_inputs": _render_inputs(base, registry),
            "props_path": _safe_rel(record.get("props", ""), label="registered props"),
            "props_sha256": _sha(props),
            "render_binding_sha256": None,
        }
    )
    raw["render_binding_sha256"] = render_binding_digest(raw)
    final_problems = _identity_problems(base, raw, require_bound=True)
    if final_problems:
        raise RunIdentityError("; ".join(final_problems))
    _atomic_json(path, raw)
    return raw


def bind_inputs(*, root: str | Path | None = None) -> dict[str, Any]:
    """Retired ambiguous boundary; callers must name the post-authoring transition."""
    raise RunIdentityError("bind-inputs is retired; use bind-render-inputs after authoring")


def _artifact_path(path: str | Path, root: Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        resolved = candidate.resolve(strict=False)
        try:
            resolved.relative_to(root)
        except ValueError:
            raise StaleArtifactError("artifact path is outside the stamped repository") from None
        return resolved
    try:
        if "\\" in str(path):
            raise StaleArtifactError("artifact path must use POSIX separators")
        relative = _safe_rel(PurePosixPath(str(path)).as_posix(), label="artifact")
        return _resolve_inside(root, relative, label="artifact", must_exist=False)
    except RunIdentityError as exc:
        raise StaleArtifactError(str(exc)) from None


def check_path(path: str | Path, root: str | Path | None = None) -> tuple[bool, str]:
    """Check a current-run artifact, resolving relative paths against `root` only."""
    base = _base(root)
    ok, reason = check_identity(root=base, require_props=True)
    if not ok:
        return False, reason
    stamp = load_stamp(base)
    assert stamp is not None
    try:
        target = _artifact_path(path, base)
    except StaleArtifactError as exc:
        return False, str(exc)
    if not target.is_file():
        return False, f"{path} does not exist"
    if target.is_symlink():
        return False, f"{path} may not be a symlink"
    if target.stat().st_mtime <= float(stamp["started_at"]):
        return False, f"STALE: {path} does not postdate run_id={stamp.get('run_id')}"
    return True, "fresh"


def fresh(
    path: str | Path, *, check: bool = True, root: str | Path | None = None,
) -> str:
    if not check:
        return str(path)
    ok, reason = check_path(path, root)
    if not ok:
        raise StaleArtifactError(reason)
    return str(_artifact_path(path, _base(root)))


def stamp_digest(root: str | Path | None = None) -> str:
    stamp = load_stamp(root)
    if stamp is None:
        raise RunIdentityError("run stamp is missing or unreadable")
    return hashlib.sha256(canonical_bytes(stamp)).hexdigest()


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    init_parser = sub.add_parser("init", help="create a planning identity before authoring")
    init_parser.add_argument("--run-id", required=True)
    init_parser.add_argument("--date")
    init_parser.add_argument("--composition", required=True)
    init_parser.add_argument("--props")
    check_parser = sub.add_parser("check", help="check one current-run artifact")
    check_parser.add_argument("path")
    identity_parser = sub.add_parser("require-identity", help="validate checkout and bound inputs")
    identity_parser.add_argument(
        "--allow-planning", action="store_true",
        help="validate only the pre-authoring planning identity",
    )
    composition_parser = sub.add_parser("require-composition", help="validate exact composition and inputs")
    composition_parser.add_argument("--composition", required=True)
    sub.add_parser("bind-render-inputs", help="bind source, engine, config and props after authoring")
    sub.add_parser("bind-inputs", help="retired; use bind-render-inputs")
    args = parser.parse_args()
    try:
        if args.cmd == "init":
            stamp = init(args.run_id, args.composition, run_date=args.date, props=args.props)
            print(
                f"planning run stamped: run_id={stamp['run_id']} "
                f"composition={stamp['composition']} head={stamp['planning_git_head'][:12]} "
                f"state=planning -> {STAMP_REL}"
            )
            return 0
        if args.cmd == "bind-render-inputs":
            stamp = bind_render_inputs()
            print(
                "render inputs bound: "
                f"composition={stamp['composition']} "
                f"binding={stamp['render_binding_sha256']}"
            )
            return 0
        if args.cmd == "bind-inputs":
            raise RunIdentityError("bind-inputs is retired; use bind-render-inputs after authoring")
        if args.cmd == "check":
            ok, reason = check_path(args.path)
        elif args.cmd == "require-identity":
            ok, reason = check_identity(require_props=not args.allow_planning)
        else:
            ok, reason = check_identity(expected_composition=args.composition, require_props=True)
        print(("OK: " if ok else "FAIL: ") + reason, file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 1
    except (RunIdentityError, StrictJSONError, OSError, ValueError) as exc:
        print(f"run_guard: FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
