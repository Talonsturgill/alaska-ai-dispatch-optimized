#!/usr/bin/env python3
"""Fail closed if a daily run edits source or enters weekly maintenance scope."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from canary_guard import CanarySafetyError, require_canary_origin
from strict_json import StrictJSONError, load_path


ROOT = Path(__file__).resolve().parent.parent
CONFIG_REL = "config/daily_controller.json"
SNAPSHOT_REL = "out/dispatch/daily_scope_snapshot.json"
SNAPSHOT_KEYS = {
    "schema_version", "mode", "repository", "worktree_root", "branch",
    "git_head", "config_sha256", "clean_at_start",
}


class ScopeError(RuntimeError):
    """A daily run crossed its source boundary."""


def _git(root: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, check=False,
        text=not binary, timeout=20,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", "replace") if binary else result.stderr
        raise ScopeError(f"git {' '.join(args)} failed: {str(stderr).strip()}")
    return result.stdout


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _config(root: Path) -> dict[str, Any]:
    value = load_path(root / CONFIG_REL, label="daily controller config")
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ScopeError("daily controller config must be a schema-v1 object")
    scope = value.get("daily_scope")
    if not isinstance(scope, dict):
        raise ScopeError("daily controller config is missing daily_scope")
    if scope.get("weekly_maintenance_is_separate") is not True:
        raise ScopeError("weekly maintenance must remain separate")
    if scope.get("daily_controller_may_enter_maintenance") is not False:
        raise ScopeError("daily controller may not enter maintenance")
    return value


def _path(value: str) -> str:
    if "\\" in value or value.startswith("/"):
        raise ScopeError("Git returned a non-canonical repository path")
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts:
        raise ScopeError("Git returned an unsafe repository path")
    return pure.as_posix()


def changed_paths(root: Path) -> list[str]:
    tracked = _git(root, "diff", "--name-only", "-z", "HEAD", binary=True)
    untracked = _git(
        root, "ls-files", "--others", "--exclude-standard", "-z", binary=True
    )
    assert isinstance(tracked, bytes) and isinstance(untracked, bytes)
    try:
        values = (tracked + untracked).decode("utf-8", "strict").split("\0")
    except UnicodeDecodeError:
        raise ScopeError("changed Git paths are not valid UTF-8") from None
    return sorted({_path(value) for value in values if value})


def forbidden_reasons(paths: list[str], config: dict[str, Any]) -> list[str]:
    scope = config["daily_scope"]
    allowed = tuple(scope["allowed_runtime_prefixes"])
    prefixes = tuple(scope["forbidden_prefixes"])
    exact = set(scope["forbidden_exact_paths"])
    reasons: list[str] = []
    for raw in paths:
        path = _path(raw)
        if path in exact or path.startswith(prefixes):
            reasons.append(f"daily source edit forbidden: {path}")
        elif not path.startswith(allowed):
            reasons.append(f"path is outside daily runtime scope: {path}")
    return reasons


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def create_snapshot(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    config = _config(root)
    repository = require_canary_origin(root)
    paths = changed_paths(root)
    reasons = forbidden_reasons(paths, config)
    if paths or reasons:
        detail = "; ".join(reasons or ["daily runs require a clean source tree"])
        raise ScopeError(detail)
    snapshot = {
        "schema_version": 1,
        "mode": "daily",
        "repository": repository,
        "worktree_root": str(root),
        "branch": str(_git(root, "branch", "--show-current")).strip(),
        "git_head": str(_git(root, "rev-parse", "HEAD")).strip(),
        "config_sha256": _sha(root / CONFIG_REL),
        "clean_at_start": True,
    }
    if not snapshot["branch"]:
        raise ScopeError("daily run requires a named branch")
    _atomic_json(root / SNAPSHOT_REL, snapshot)
    return snapshot


def check_scope(root: Path = ROOT) -> tuple[bool, str]:
    root = root.resolve()
    try:
        config = _config(root)
        value = load_path(root / SNAPSHOT_REL, label="daily scope snapshot")
        if not isinstance(value, dict) or set(value) != SNAPSHOT_KEYS:
            raise ScopeError("daily scope snapshot has unknown or missing fields")
        if value["schema_version"] != 1 or value["mode"] != "daily" or value["clean_at_start"] is not True:
            raise ScopeError("daily scope snapshot contract is invalid")
        if value["worktree_root"] != str(root):
            raise ScopeError("daily scope snapshot belongs to another worktree")
        if value["repository"] != require_canary_origin(root):
            raise ScopeError("daily scope repository changed")
        if value["branch"] != str(_git(root, "branch", "--show-current")).strip():
            raise ScopeError("daily scope branch changed")
        if value["git_head"] != str(_git(root, "rev-parse", "HEAD")).strip():
            raise ScopeError("daily scope Git HEAD changed")
        if value["config_sha256"] != _sha(root / CONFIG_REL):
            raise ScopeError("daily controller config changed")
        paths = changed_paths(root)
        reasons = forbidden_reasons(paths, config)
        if reasons:
            raise ScopeError("; ".join(reasons))
        if paths:
            raise ScopeError("unexpected non-ignored runtime paths: " + ", ".join(paths))
        return True, "daily source scope is clean and bound"
    except (ScopeError, StrictJSONError, CanarySafetyError, OSError, ValueError) as exc:
        return False, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("snapshot", "check"))
    args = parser.parse_args()
    try:
        if args.command == "snapshot":
            snapshot = create_snapshot()
            print(json.dumps({"status": "ok", "branch": snapshot["branch"], "head": snapshot["git_head"]}, sort_keys=True))
            return 0
        ok, reason = check_scope()
        print(("OK: " if ok else "FAIL: ") + reason)
        return 0 if ok else 1
    except (ScopeError, StrictJSONError, CanarySafetyError, OSError, ValueError) as exc:
        print(f"daily_scope_guard: FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
