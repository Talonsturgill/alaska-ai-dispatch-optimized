#!/usr/bin/env python3
"""Mocked integration tests proving refusal precedes every outward side effect."""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
ROOT = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))

import canary_guard
import dispatch_email
import gmail_draft
import publish_feed
import record_draft
import upload_video


BLOCKED = canary_guard.CanarySafetyError("blocked by integration test")


class PublisherBoundaryTests(unittest.TestCase):
    def test_site_feed_refusal_precedes_gate_clone_write_network_and_push(self):
        argv = [
            "publish_feed.py", "--id", "test", "--date", "2026-08-28",
            "--title", "Test", "--caption", "Test", "--video-url",
            "https://example.invalid/test.mp4",
        ]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(publish_feed, "require_action", side_effect=BLOCKED), \
             mock.patch.object(publish_feed, "require_ship_gate") as ship_gate, \
             mock.patch.object(publish_feed, "run") as run, \
             mock.patch.object(publish_feed.tempfile, "TemporaryDirectory") as tempdir, \
             mock.patch.object(Path, "write_text") as write_text:
            with self.assertRaises(SystemExit):
                publish_feed.main()
        ship_gate.assert_not_called()
        run.assert_not_called()
        tempdir.assert_not_called()
        write_text.assert_not_called()

    def test_dispatch_email_refusal_precedes_reads_network_write_and_payload(self):
        argv = [
            "dispatch_email.py", "--post", "missing.txt",
            "--video-url-vertical", "https://example.invalid/test.mp4",
        ]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(dispatch_email, "require_action", side_effect=BLOCKED), \
             mock.patch.object(dispatch_email, "fresh") as fresh, \
             mock.patch.object(dispatch_email.subprocess, "run") as network, \
             mock.patch.object(Path, "write_text") as write_text, \
             mock.patch("builtins.print") as output:
            with self.assertRaises(SystemExit):
                dispatch_email.main()
        fresh.assert_not_called()
        network.assert_not_called()
        write_text.assert_not_called()
        output.assert_not_called()

    def test_weekly_email_refusal_precedes_reads_write_and_payload(self):
        argv = [
            "gmail_draft.py", "--post-md", "missing.md", "--image", "missing.png",
            "--sources", "missing-sources.json", "--score", "missing-score.json",
            "--date", "2026-08-28", "--branch", "canary",
        ]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(gmail_draft, "require_action", side_effect=BLOCKED), \
             mock.patch.object(Path, "read_text") as read_text, \
             mock.patch.object(Path, "read_bytes") as read_bytes, \
             mock.patch.object(Path, "write_text") as write_text, \
             mock.patch("builtins.print") as output:
            with self.assertRaises(SystemExit):
                gmail_draft.main()
        read_text.assert_not_called()
        read_bytes.assert_not_called()
        write_text.assert_not_called()
        output.assert_not_called()

    def test_gmail_receipt_refusal_precedes_directory_and_file_write(self):
        argv = ["record_draft.py", "--draft-id", "fake"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(record_draft, "require_action", side_effect=BLOCKED), \
             mock.patch.object(record_draft.os, "makedirs") as makedirs, \
             mock.patch("builtins.open", mock.mock_open()) as open_file, \
             mock.patch.object(record_draft.json, "dump") as dump:
            self.assertEqual(record_draft.main(), 42)
        makedirs.assert_not_called()
        open_file.assert_not_called()
        dump.assert_not_called()

    def test_foreign_github_media_refusal_precedes_worktree_copy_commit_and_push(self):
        with mock.patch.object(upload_video.os.path, "getsize", return_value=1) as getsize, \
             mock.patch.object(upload_video, "sh") as shell, \
             mock.patch.object(upload_video, "require_canary_origin", side_effect=BLOCKED), \
             mock.patch.object(upload_video.tempfile, "mkdtemp") as mkdtemp, \
             mock.patch.object(upload_video.shutil, "copyfile") as copyfile:
            with self.assertRaises(canary_guard.CanarySafetyError):
                upload_video.via_github("missing.mp4", "test.mp4")
        mkdtemp.assert_not_called()
        copyfile.assert_not_called()
        getsize.assert_not_called()
        shell.assert_not_called()

    def test_rclone_secret_is_never_decoded_written_or_probed(self):
        argv = ["upload_video.py", "--file", "missing.mp4", "--no-github"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.dict(os.environ, {"RCLONE_CONFIG_B64": "c2VjcmV0"}), \
             mock.patch("base64.b64decode") as decode, \
             mock.patch("builtins.open", mock.mock_open()) as open_file, \
             mock.patch.object(upload_video, "sh") as shell:
            self.assertEqual(upload_video.main(), 1)
        decode.assert_not_called()
        open_file.assert_not_called()
        shell.assert_not_called()

    def test_failed_canary_upload_has_no_external_fallback(self):
        argv = ["upload_video.py", "--file", "missing.mp4"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(upload_video, "via_github", side_effect=RuntimeError("push failed")), \
             mock.patch.object(upload_video.subprocess, "run") as network:
            self.assertEqual(upload_video.main(), 1)
        network.assert_not_called()

    def test_setup_has_no_auto_push_hook_and_connectors_are_denied(self):
        setup = (ROOT / "scripts" / "setup_env.sh").read_text(encoding="utf-8")
        self.assertNotIn("core.hooksPath", setup)
        self.assertNotIn("git push", setup)
        self.assertFalse((ROOT / ".githooks" / "post-commit").exists())
        for settings_path in (
            ROOT / ".claude" / "settings.json",
            ROOT / ".claude" / "settings.local.json",
        ):
            permissions = json.loads(settings_path.read_text(encoding="utf-8"))["permissions"]
            self.assertIn("mcp__Gmail", permissions["deny"])
            self.assertIn("mcp__github", permissions["deny"])
            self.assertNotIn("mcp__Gmail", permissions["allow"])
            self.assertNotIn("mcp__github", permissions["allow"])


if __name__ == "__main__":
    unittest.main()
