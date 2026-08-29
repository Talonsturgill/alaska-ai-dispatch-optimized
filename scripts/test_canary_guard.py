#!/usr/bin/env python3
"""Unit tests for the permanent canary policy and strict remote parser."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canary_guard as guard


def completed(stdout: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr="", returncode=returncode)


class CanaryGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = guard.load_policy()

    def test_policy_is_complete_permanent_canary(self):
        self.assertEqual(set(self.policy), {
            "schema_version", "mode", "canary_repository", "actions"
        })
        self.assertEqual(self.policy["mode"], "canary")
        self.assertEqual(
            self.policy["canary_repository"],
            "Talonsturgill/alaska-ai-dispatch-optimized",
        )
        policy_text = json.dumps(self.policy)
        self.assertNotIn("opt_in", policy_text)
        self.assertNotIn("environment", policy_text)
        self.assertFalse(hasattr(guard, "production_opted_in"))

    def test_local_and_canary_repository_actions_are_the_only_allowed_actions(self):
        guard.require_action("local_artifact", policy=self.policy)
        for action in ("github_push", "github_media_publish"):
            guard.require_action(
                action,
                "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
                policy=self.policy,
            )
            with self.assertRaises(guard.CanarySafetyError):
                guard.require_action(
                    action,
                    "Talonsturgill/alaska-ai-weekly",
                    policy=self.policy,
                )

    def test_denied_and_undeclared_actions_have_no_runtime_bypass(self):
        for action in (
            "site_feed_publish",
            "gmail_draft",
            "gmail_draft_receipt",
            "external_media_upload",
            "production_repo_push",
            "social_publish",
            "unknown_action",
        ):
            with self.subTest(action=action):
                with self.assertRaises(guard.CanarySafetyError):
                    guard.require_action(action, "anything", policy=self.policy)

    def test_canonical_github_remotes_are_accepted(self):
        expected = "Talonsturgill/alaska-ai-dispatch-optimized"
        for remote in (
            "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
            "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized",
            "git@github.com:Talonsturgill/alaska-ai-dispatch-optimized.git",
            "git@github.com:Talonsturgill/alaska-ai-dispatch-optimized",
        ):
            with self.subTest(remote=remote):
                self.assertEqual(guard.parse_github_remote(remote), expected)

    def test_hostile_or_ambiguous_remotes_are_rejected(self):
        hostile = (
            "https://github.com.evil/Talonsturgill/alaska-ai-dispatch-optimized.git",
            "https://evilgithub.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
            "http://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
            "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git?x=1",
            "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git#x",
            "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized/extra",
            "https://user@github.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
            "https://github.com:443/Talonsturgill/alaska-ai-dispatch-optimized.git",
            "ssh://git@github.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
            " https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
        )
        for remote in hostile:
            with self.subTest(remote=remote):
                with self.assertRaises(guard.CanarySafetyError):
                    guard.parse_github_remote(remote)

    def test_origin_requires_identical_fetch_and_push_urls(self):
        url = "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git"
        with mock.patch.object(
            guard.subprocess,
            "run",
            side_effect=[
                completed("origin\n"),
                completed(returncode=1),
                completed(url + "\n"),
                completed(url + "\n"),
                completed(url + "\n"),
            ],
        ):
            self.assertEqual(
                guard.require_canary_origin(Path("X:/canary"), policy=self.policy),
                self.policy["canary_repository"],
            )

    def test_explicit_pushurl_is_always_rejected(self):
        url = "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git"
        with mock.patch.object(
            guard.subprocess,
            "run",
            side_effect=[completed("origin\n"), completed(url + "\n")],
        ) as run:
            with self.assertRaisesRegex(guard.CanarySafetyError, "explicit pushurl"):
                guard.require_canary_origin(Path("X:/canary"), policy=self.policy)
        self.assertEqual(run.call_count, 2)

    def test_even_empty_explicit_pushurl_is_rejected(self):
        with mock.patch.object(
            guard.subprocess,
            "run",
            side_effect=[completed("origin\n"), completed("\n")],
        ):
            with self.assertRaisesRegex(guard.CanarySafetyError, "explicit pushurl"):
                guard.require_canary_origin(Path("X:/canary"), policy=self.policy)

    def test_mismatched_or_foreign_origin_is_rejected(self):
        canary = "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git"
        foreign = "https://github.com/Talonsturgill/alaska-ai-weekly.git"
        for fetch, push in ((canary, foreign), (foreign, foreign)):
            with self.subTest(fetch=fetch, push=push), mock.patch.object(
                guard.subprocess,
                "run",
                side_effect=[
                    completed("origin\n"),
                    completed(returncode=1),
                    completed(fetch + "\n"),
                    completed(fetch + "\n"),
                    completed(push + "\n"),
                ],
            ):
                with self.assertRaises(guard.CanarySafetyError):
                    guard.require_canary_origin(Path("X:/canary"), policy=self.policy)

    def test_multiple_or_hostile_origin_urls_are_rejected(self):
        canary = "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git"
        evil = "https://github.com.evil/Talonsturgill/alaska-ai-dispatch-optimized.git"
        cases = ((canary + "\n" + evil, canary), (evil, evil))
        for fetch, push in cases:
            with self.subTest(fetch=fetch), mock.patch.object(
                guard.subprocess,
                "run",
                side_effect=[
                    completed("origin\n"),
                    completed(returncode=1),
                    completed(fetch + "\n"),
                    completed(fetch + "\n"),
                    completed(push + "\n"),
                ],
            ):
                with self.assertRaises(guard.CanarySafetyError):
                    guard.require_canary_origin(Path("X:/canary"), policy=self.policy)

    def test_extra_remote_is_rejected_before_url_inspection(self):
        with mock.patch.object(
            guard.subprocess, "run", return_value=completed("origin\nproduction\n")
        ) as run:
            with self.assertRaisesRegex(guard.CanarySafetyError, "only configured remote"):
                guard.require_canary_origin(Path("X:/canary"), policy=self.policy)
        self.assertEqual(run.call_count, 1)

    def test_unknown_or_extra_policy_fields_fail_closed(self):
        invalid = dict(self.policy)
        invalid["runtime_override"] = True
        with mock.patch.object(Path, "read_text", return_value=json.dumps(invalid)):
            with self.assertRaises(guard.CanarySafetyError):
                guard.load_policy(Path("ignored.json"))


if __name__ == "__main__":
    unittest.main()
