#!/usr/bin/env python3
"""Fail-closed side-effect policy for the Dispatch optimization canary.

The original pipeline predates this lab repository and contains valid production
publishers. This module keeps those publishers reusable while refusing their
destinations by default. It has no network side effects; callers must invoke it
before they write, upload, draft, or push.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "config" / "execution_policy.json"


class CanarySafetyError(RuntimeError):
    """Raised when an action falls outside the committed canary boundary."""


def load_policy(path: Path = POLICY_PATH) -> dict:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: execution policy is missing or invalid: {path} ({exc})"
        ) from exc
    required = {"schema_version", "mode", "canary_repository", "production_opt_in"}
    missing = sorted(required - set(policy))
    if missing:
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: execution policy is incomplete; missing "
            + ", ".join(missing)
        )
    if policy["mode"] != "canary":
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: this lab checkout requires policy mode 'canary'"
        )
    return policy


def repository_slug(target: str | None) -> str:
    """Normalize an owner/repo string or common GitHub remote URL."""
    raw = (target or "").strip().rstrip("/")
    if not raw:
        return ""
    raw = re.sub(r"\.git$", "", raw, flags=re.IGNORECASE)
    match = re.search(r"github\.com[/:]([^/]+)/([^/]+)$", raw, flags=re.IGNORECASE)
    if match:
        return f"{match.group(1)}/{match.group(2)}"
    if re.fullmatch(r"[^/\s]+/[^/\s]+", raw):
        return raw
    return ""


def production_opted_in(
    policy: dict | None = None, environ: Mapping[str, str] | None = None
) -> bool:
    policy = policy or load_policy()
    environ = os.environ if environ is None else environ
    latch = policy["production_opt_in"]
    return (
        environ.get(latch["mode_environment"]) == latch["mode_value"]
        and environ.get(latch["acknowledgement_environment"])
        == latch["acknowledgement_value"]
    )


def require_action(
    action: str,
    target: str | None = None,
    *,
    policy: dict | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Permit a declared action or raise before its first side effect."""
    policy = policy or load_policy()
    if production_opted_in(policy, environ):
        return

    allowed = policy.get("allowed_without_opt_in", {})
    if action == "local_artifact" and allowed.get(action) is True:
        return

    permitted_targets = allowed.get(action)
    if isinstance(permitted_targets, list):
        slug = repository_slug(target)
        if slug and slug.lower() in {item.lower() for item in permitted_targets}:
            return
        target_note = slug or (target or "<missing target>")
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: {action} target {target_note!r} is not the canary "
            f"repository {policy['canary_repository']!r}"
        )

    raise CanarySafetyError(
        f"CANARY SAFETY BLOCKED: action {action!r} is disabled in canary mode. "
        "Keep the result local or in the canary repository. Do not set the production "
        "latch without explicit owner authorization for this exact run."
    )


def origin_slug(root: Path = ROOT) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: this checkout has no readable origin remote"
        )
    slug = repository_slug(result.stdout.strip())
    if not slug:
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: cannot identify GitHub repository from origin "
            f"{result.stdout.strip()!r}"
        )
    return slug


def require_canary_origin(
    root: Path = ROOT,
    *,
    policy: dict | None = None,
    environ: Mapping[str, str] | None = None,
) -> str:
    policy = policy or load_policy()
    slug = origin_slug(root)
    if production_opted_in(policy, environ):
        return slug
    expected = policy["canary_repository"]
    if slug.lower() != expected.lower():
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: origin is {slug!r}; expected {expected!r}"
        )
    return slug


def self_test(policy: dict) -> None:
    safe_env: dict[str, str] = {}
    require_action("local_artifact", policy=policy, environ=safe_env)
    require_action(
        "github_push", policy["canary_repository"], policy=policy, environ=safe_env
    )
    require_action(
        "github_media_publish",
        f"https://github.com/{policy['canary_repository']}.git",
        policy=policy,
        environ=safe_env,
    )
    for action, target in (
        ("github_push", "Talonsturgill/alaska-ai-weekly"),
        ("github_push", "Talonsturgill/alaskaaicarousels"),
        ("site_feed_publish", "Talonsturgill/alaskaaicarousels"),
        ("gmail_draft", "docket@alaskaaihq.com"),
        ("external_media_upload", "https://tmpfiles.org"),
    ):
        try:
            require_action(action, target, policy=policy, environ=safe_env)
        except CanarySafetyError:
            continue
        raise CanarySafetyError(
            f"CANARY SAFETY SELF-TEST FAILED: {action} unexpectedly allowed {target}"
        )
    require_canary_origin(policy=policy, environ=safe_env)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("self-test")
    check = sub.add_parser("check")
    check.add_argument("action")
    check.add_argument("--target", default="")
    args = parser.parse_args()

    try:
        policy = load_policy()
        if args.command == "status":
            print(
                json.dumps(
                    {
                        "mode": policy["mode"],
                        "production_opt_in": production_opted_in(policy),
                        "origin": origin_slug(),
                        "canary_repository": policy["canary_repository"],
                    },
                    sort_keys=True,
                )
            )
        elif args.command == "self-test":
            self_test(policy)
            print("CANARY SAFETY SELF-TEST: PASS")
        else:
            require_action(args.action, args.target, policy=policy)
            print(f"CANARY SAFETY: ALLOWED {args.action}")
    except CanarySafetyError as exc:
        print(str(exc), file=sys.stderr)
        return 42
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
