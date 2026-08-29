#!/usr/bin/env python3
"""Permanent fail-closed boundary for the Dispatch optimization canary.

There is intentionally no environment variable, command-line flag, or runtime
override that unlocks a production action. Production delivery belongs in the
production repository after deliberate review, never in this lab checkout.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = ROOT / "config" / "execution_policy.json"

_OWNER = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})"
_REPOSITORY = r"[A-Za-z0-9_.-]{1,100}"
_SLUG_RE = re.compile(rf"^(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY})$")
_HTTPS_REMOTE_RE = re.compile(
    rf"^https://github\.com/(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY}?)(?:\.git)?$"
)
_SSH_REMOTE_RE = re.compile(
    rf"^git@github\.com:(?P<owner>{_OWNER})/(?P<repo>{_REPOSITORY}?)(?:\.git)?$"
)

EXPECTED_ACTIONS = {
    "local_artifact",
    "github_push",
    "github_media_publish",
    "external_media_upload",
    "gmail_draft",
    "gmail_draft_receipt",
    "production_repo_push",
    "site_feed_publish",
    "social_publish",
}


class CanarySafetyError(RuntimeError):
    """Raised before an action can cross the lab boundary."""


def parse_repository_slug(value: str) -> str:
    """Accept only an exact GitHub owner/repository identifier."""
    if not isinstance(value, str) or value != value.strip():
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: non-canonical repository identifier {value!r}"
        )
    match = _SLUG_RE.fullmatch(value)
    if not match:
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: invalid repository identifier {value!r}"
        )
    return f"{match.group('owner')}/{match.group('repo')}"


def parse_github_remote(value: str) -> str:
    """Parse a canonical github.com HTTPS or SSH remote, anchored end to end."""
    if not isinstance(value, str) or value != value.strip():
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: non-canonical GitHub remote {value!r}"
        )
    match = _HTTPS_REMOTE_RE.fullmatch(value) or _SSH_REMOTE_RE.fullmatch(value)
    if not match:
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: remote must be an exact github.com repository URL, got {value!r}"
        )
    return f"{match.group('owner')}/{match.group('repo')}"


def target_repository(value: str | None) -> str:
    """Normalize an exact repository slug or canonical GitHub remote."""
    if not value:
        raise CanarySafetyError("CANARY SAFETY BLOCKED: repository target is required")
    try:
        return parse_repository_slug(value)
    except CanarySafetyError:
        return parse_github_remote(value)


def load_policy(path: Path = POLICY_PATH) -> dict:
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: execution policy is missing or invalid: {path} ({exc})"
        ) from exc

    expected_top = {"schema_version", "mode", "canary_repository", "actions"}
    if set(policy) != expected_top:
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: execution policy keys must be exactly "
            + ", ".join(sorted(expected_top))
        )
    if policy["schema_version"] != 1 or policy["mode"] != "canary":
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: this repository requires schema 1 in permanent canary mode"
        )
    canary_repository = parse_repository_slug(policy["canary_repository"])
    if canary_repository != policy["canary_repository"]:
        raise CanarySafetyError("CANARY SAFETY BLOCKED: canary repository must be canonical")

    actions = policy["actions"]
    if not isinstance(actions, dict) or set(actions) != EXPECTED_ACTIONS:
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: policy must define exactly the known action set"
        )
    for action, rule in actions.items():
        if not isinstance(rule, dict) or rule.get("decision") not in {
            "allow_local",
            "allow_repository",
            "deny",
        }:
            raise CanarySafetyError(
                f"CANARY SAFETY BLOCKED: invalid policy rule for {action!r}"
            )
        decision = rule["decision"]
        if decision == "allow_local" and (action != "local_artifact" or set(rule) != {"decision"}):
            raise CanarySafetyError(
                "CANARY SAFETY BLOCKED: allow_local is valid only for local_artifact"
            )
        if decision == "allow_repository":
            if set(rule) != {"decision", "repositories"} or not isinstance(
                rule["repositories"], list
            ):
                raise CanarySafetyError(
                    f"CANARY SAFETY BLOCKED: {action!r} needs an explicit repository list"
                )
            repositories = [parse_repository_slug(item) for item in rule["repositories"]]
            if repositories != [canary_repository]:
                raise CanarySafetyError(
                    f"CANARY SAFETY BLOCKED: {action!r} may name only the canary repository"
                )
        if decision == "deny" and set(rule) != {"decision"}:
            raise CanarySafetyError(
                f"CANARY SAFETY BLOCKED: deny rule for {action!r} carries unused fields"
            )
    return policy


def require_action(
    action: str, target: str | None = None, *, policy: dict | None = None
) -> None:
    """Permit only actions explicitly allowed by the immutable canary policy."""
    policy = policy or load_policy()
    rule = policy["actions"].get(action)
    if rule is None:
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: undeclared action {action!r} is denied"
        )
    decision = rule["decision"]
    if decision == "allow_local":
        return
    if decision == "allow_repository":
        repository = target_repository(target)
        if repository.lower() in {item.lower() for item in rule["repositories"]}:
            return
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: {action} target {repository!r} is not the canary "
            f"repository {policy['canary_repository']!r}"
        )
    raise CanarySafetyError(
        f"CANARY SAFETY BLOCKED: action {action!r} is permanently disabled in this lab. "
        "Keep the result local or in the canary repository."
    )


def _git_result(root: Path, *args: str):
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result


def _git_lines(root: Path, *args: str) -> list[str]:
    result = _git_result(root, *args)
    if result.returncode != 0:
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: git {' '.join(args)} failed while validating origin"
        )
    return [line for line in result.stdout.splitlines() if line]


def _git_config_values(root: Path, key: str) -> list[str] | None:
    """Return configured values, distinguishing an absent key from an empty value."""
    result = _git_result(root, "config", "--local", "--get-all", key)
    if result.returncode == 1:
        return None
    if result.returncode != 0:
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: cannot inspect git config key {key!r}"
        )
    return result.stdout.splitlines()


def require_canary_origin(root: Path = ROOT, *, policy: dict | None = None) -> str:
    """Require one exact fetch URL, no pushurl override, and a matching push URL."""
    policy = policy or load_policy()
    remote_names = _git_lines(root, "remote")
    if remote_names != ["origin"]:
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: origin must be the checkout's only configured remote"
        )

    explicit_pushurls = _git_config_values(root, "remote.origin.pushurl")
    if explicit_pushurls is not None:
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: origin has an explicit pushurl; alternate push destinations "
            "are forbidden in the lab"
        )

    configured_fetch_urls = _git_config_values(root, "remote.origin.url")
    fetch_urls = _git_lines(root, "remote", "get-url", "--all", "origin")
    push_urls = _git_lines(root, "remote", "get-url", "--push", "--all", "origin")
    if (
        configured_fetch_urls is None
        or len(configured_fetch_urls) != 1
        or len(fetch_urls) != 1
        or len(push_urls) != 1
    ):
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: origin must have exactly one fetch URL and one push URL"
        )
    if configured_fetch_urls != fetch_urls:
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: configured and effective fetch URLs differ; URL rewrites "
            "are forbidden in the lab"
        )
    fetch_slug = parse_github_remote(fetch_urls[0])
    push_slug = parse_github_remote(push_urls[0])
    expected = policy["canary_repository"]
    if fetch_urls[0] != push_urls[0] or fetch_slug != push_slug:
        raise CanarySafetyError(
            "CANARY SAFETY BLOCKED: origin fetch and push remotes must be identical"
        )
    if fetch_slug.lower() != expected.lower():
        raise CanarySafetyError(
            f"CANARY SAFETY BLOCKED: origin is {fetch_slug!r}; expected {expected!r}"
        )
    require_action("github_push", fetch_slug, policy=policy)
    return fetch_slug


def self_test(policy: dict) -> None:
    require_action("local_artifact", policy=policy)
    require_action("github_push", policy["canary_repository"], policy=policy)
    require_action(
        "github_media_publish",
        f"https://github.com/{policy['canary_repository']}.git",
        policy=policy,
    )
    for action, target in (
        ("github_push", "Talonsturgill/alaska-ai-weekly"),
        ("github_push", "Talonsturgill/alaskaaicarousels"),
        ("site_feed_publish", "Talonsturgill/alaskaaicarousels"),
        ("gmail_draft", "docket@alaskaaihq.com"),
        ("external_media_upload", "https://tmpfiles.org"),
        ("undeclared_action", "anything"),
    ):
        try:
            require_action(action, target, policy=policy)
        except CanarySafetyError:
            continue
        raise CanarySafetyError(
            f"CANARY SAFETY SELF-TEST FAILED: {action} unexpectedly allowed {target}"
        )

    hostile_remotes = (
        "https://github.com.evil/Talonsturgill/alaska-ai-dispatch-optimized.git",
        "https://evilgithub.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
        "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git?target=evil",
        "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git#fragment",
        "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized/extra",
        "https://user@github.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
        "https://github.com:443/Talonsturgill/alaska-ai-dispatch-optimized.git",
    )
    for remote in hostile_remotes:
        try:
            parse_github_remote(remote)
        except CanarySafetyError:
            continue
        raise CanarySafetyError(
            f"CANARY SAFETY SELF-TEST FAILED: hostile remote accepted: {remote}"
        )
    require_canary_origin(policy=policy)


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
                        "origin": require_canary_origin(policy=policy),
                        "canary_repository": policy["canary_repository"],
                        "production_override": "none",
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
