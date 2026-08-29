#!/usr/bin/env python3
"""Regression tests for the isolated canary side-effect policy."""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import canary_guard as guard


class CanaryGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = guard.load_policy()
        cls.safe_env: dict[str, str] = {}

    def test_policy_is_canary(self):
        self.assertEqual(self.policy["mode"], "canary")
        self.assertEqual(
            self.policy["canary_repository"],
            "Talonsturgill/alaska-ai-dispatch-optimized",
        )

    def test_local_artifacts_are_allowed(self):
        guard.require_action(
            "local_artifact", policy=self.policy, environ=self.safe_env
        )

    def test_only_canary_github_targets_are_allowed(self):
        for action in ("github_push", "github_media_publish"):
            guard.require_action(
                action,
                "https://github.com/Talonsturgill/alaska-ai-dispatch-optimized.git",
                policy=self.policy,
                environ=self.safe_env,
            )
            with self.assertRaises(guard.CanarySafetyError):
                guard.require_action(
                    action,
                    "https://github.com/Talonsturgill/alaska-ai-weekly.git",
                    policy=self.policy,
                    environ=self.safe_env,
                )

    def test_production_and_external_actions_fail_closed(self):
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
                    guard.require_action(
                        action,
                        "production-target",
                        policy=self.policy,
                        environ=self.safe_env,
                    )

    def test_partial_opt_in_does_not_unlock(self):
        latch = self.policy["production_opt_in"]
        partial = {latch["mode_environment"]: latch["mode_value"]}
        self.assertFalse(guard.production_opted_in(self.policy, partial))
        with self.assertRaises(guard.CanarySafetyError):
            guard.require_action(
                "gmail_draft", policy=self.policy, environ=partial
            )

    def test_complete_explicit_opt_in_unlocks_policy(self):
        latch = self.policy["production_opt_in"]
        explicit = {
            latch["mode_environment"]: latch["mode_value"],
            latch["acknowledgement_environment"]: latch[
                "acknowledgement_value"
            ],
        }
        self.assertTrue(guard.production_opted_in(self.policy, explicit))
        guard.require_action("gmail_draft", policy=self.policy, environ=explicit)

    def test_checked_out_origin_is_the_canary(self):
        self.assertEqual(
            guard.require_canary_origin(policy=self.policy, environ=self.safe_env),
            self.policy["canary_repository"],
        )


if __name__ == "__main__":
    unittest.main()
