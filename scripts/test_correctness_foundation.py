#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import deliverable_contract as dc
import run_guard
import ship_gate
import upload_video
from strict_json import StrictJSONError, load_path


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def make_identity_repo(parent: Path, name: str = "repo") -> Path:
    root = parent / name
    (root / "config").mkdir(parents=True)
    (root / "video-engine" / "src").mkdir(parents=True)
    (root / "out" / "dispatch").mkdir(parents=True)
    write_json(
        root / "config" / "compositions.json",
        {
            "schema_version": 1,
            "active_composition": "DispatchDaily",
            "compositions": {
                "DispatchDaily": {
                    "status": "active",
                    "component": "DispatchDaily",
                    "source": "video-engine/src/DispatchDaily.tsx",
                    "source_dependencies": ["video-engine/src/StoryFixture.tsx"],
                    "props": "out/dispatch/episode_props.json",
                },
                "LegacyDispatch": {
                    "status": "legacy",
                    "component": "Legacy",
                    "source": "video-engine/src/StoryFixture.tsx",
                },
            },
        },
    )
    write_json(
        root / "config" / "execution_policy.json",
        {
            "schema_version": 1,
            "mode": "canary",
            "canary_repository": "TestOwner/test-repo",
            "actions": {},
        },
    )
    (root / "video-engine" / "src" / "DispatchDaily.tsx").write_text(
        "export const DispatchDaily = () => null;\n", encoding="utf-8"
    )
    (root / "video-engine" / "src" / "StoryFixture.tsx").write_text(
        "export const StoryFixture = () => null;\n", encoding="utf-8"
    )
    (root / "video-engine" / "src" / "Shared.ts").write_text(
        "export const shared = 1;\n", encoding="utf-8"
    )
    (root / "video-engine" / "src" / "Root.tsx").write_text(
        '<Composition\n        id="DispatchDaily"\n        component={DispatchDaily}\n      />\n',
        encoding="utf-8",
    )
    write_json(root / "out" / "dispatch" / "episode_props.json", {"total": 3000})
    git(root, "init", "-b", "main")
    git(root, "remote", "add", "origin", "https://github.com/TestOwner/test-repo.git")
    git(root, "add", ".")
    git(root, "-c", "user.name=Test Owner", "-c", "user.email=test@example.com", "commit", "-m", "fixture")
    return root


def init_identity(root: Path) -> dict:
    run_guard.init(
        "2026-08-29-test", "DispatchDaily", root=root,
    )
    return run_guard.bind_inputs(root=root)


def copy_delivery_config(root: Path) -> None:
    shutil.copyfile(REPO / "config" / "deliverables.json", root / "config" / "deliverables.json")


def make_artifacts(root: Path, stamp: dict) -> dict[str, dict]:
    cfg = dc.load_config(root=root)
    facts = {}
    for role in dc.EXPECTED_ROLES:
        spec = cfg["roles"][role]
        target = root.joinpath(*spec["path"].split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        size = max(spec["minimum_bytes"], 1) + 17
        target.write_bytes((role.encode("ascii") * (size // len(role) + 1))[:size])
        os.utime(target, (stamp["started_at"] + 2, stamp["started_at"] + 2))
        facts[str(target.resolve())] = {
            "width": spec["width"],
            "height": spec["height"],
            "duration_seconds": 100.0 if spec["media_type"] == "video" else None,
            "streams": {"video": spec["video_streams"], "audio": spec["audio_streams"]},
            "video_codecs": ["h264"] if spec["media_type"] == "video" else ["png"],
            "audio_codecs": ["aac"] if spec["audio_streams"] else [],
        }
    return facts


class RunGuardTests(unittest.TestCase):
    def test_missing_unknown_case_mismatch_and_non_ascii_composition_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            script = REPO / "scripts" / "run_guard.py"
            missing = subprocess.run(
                [sys.executable, str(script), "init", "--run-id", "2026-08-29"],
                cwd=root, capture_output=True, text=True,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertNotIn("Traceback", missing.stderr)
            for composition in ("Unknown", "dispatchdaily", "DispatchDailý"):
                with self.subTest(composition=composition):
                    with self.assertRaises(run_guard.RunIdentityError):
                        run_guard.init("2026-08-29", composition, root=root)
            stamp = init_identity(root)
            ok, reason = run_guard.check_identity(
                root=root, expected_composition="dispatchdaily", require_props=True
            )
            self.assertFalse(ok)
            self.assertIn("expected", reason)
            self.assertEqual(stamp["composition"], "DispatchDaily")

    def test_stamp_binds_all_identity_fields_and_current_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            stamp = init_identity(root)
            expected = {
                "schema_version", "run_id", "date", "composition", "mode", "repository",
                "origin", "worktree_root", "branch", "git_head", "props_path", "props_sha256",
                "source_path", "source_sha256", "source_dependencies", "registry_sha256",
                "root_source_sha256", "engine_sources_sha256",
            }
            self.assertTrue(expected <= set(stamp))
            ok, reason = run_guard.check_identity(root=root, expected_composition="DispatchDaily")
            self.assertTrue(ok, reason)

    def test_copied_stamp_branch_head_props_registry_root_and_dependency_drift_fail(self):
        mutations = {
            "branch": lambda root: git(root, "switch", "-c", "other"),
            "head": lambda root: (
                (root / "head.txt").write_text("drift", encoding="utf-8"),
                git(root, "add", "head.txt"),
                git(root, "-c", "user.name=Test Owner", "-c", "user.email=test@example.com", "commit", "-m", "drift"),
            ),
            "props": lambda root: (root / "out" / "dispatch" / "episode_props.json").write_text("{}\n", encoding="utf-8"),
            "registry": lambda root: (root / "config" / "compositions.json").write_text(
                (root / "config" / "compositions.json").read_text(encoding="utf-8") + " ", encoding="utf-8"
            ),
            "root": lambda root: (root / "video-engine" / "src" / "Root.tsx").write_text("changed\n", encoding="utf-8"),
            "dependency": lambda root: (root / "video-engine" / "src" / "StoryFixture.tsx").write_text("changed\n", encoding="utf-8"),
            "transitive source": lambda root: (root / "video-engine" / "src" / "Shared.ts").write_text("export const shared = 2;\n", encoding="utf-8"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                root = make_identity_repo(Path(td))
                init_identity(root)
                mutate(root)
                ok, reason = run_guard.check_identity(root=root, expected_composition="DispatchDaily")
                self.assertFalse(ok)
                self.assertTrue(reason)
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            first = make_identity_repo(base, "first")
            init_identity(first)
            second = make_identity_repo(base, "second")
            target = second / "out" / "dispatch" / ".run_stamp.json"
            target.write_bytes((first / "out" / "dispatch" / ".run_stamp.json").read_bytes())
            ok, reason = run_guard.check_identity(root=second, require_props=True)
            self.assertFalse(ok)
            self.assertIn("worktree", reason)

    def test_relative_path_uses_supplied_root_and_rejects_equal_stamp_outside_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            first = make_identity_repo(base, "first")
            stamp = init_identity(first)
            second = base / "cwd"
            (second / "out" / "dispatch").mkdir(parents=True)
            (second / "out" / "dispatch" / "current.txt").write_text("wrong", encoding="utf-8")
            current = first / "out" / "dispatch" / "current.txt"
            current.write_text("right", encoding="utf-8")
            os.utime(current, (stamp["started_at"] + 1, stamp["started_at"] + 1))
            old_cwd = Path.cwd()
            try:
                os.chdir(second)
                ok, reason = run_guard.check_path("out/dispatch/current.txt", root=first)
            finally:
                os.chdir(old_cwd)
            self.assertTrue(ok, reason)
            outside = base / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            ok, reason = run_guard.check_path(outside, root=first)
            self.assertFalse(ok)
            self.assertIn("outside", reason)
            os.utime(current, (stamp["started_at"], stamp["started_at"]))
            ok, reason = run_guard.check_path("out/dispatch/current.txt", root=first)
            self.assertFalse(ok)
            self.assertIn("does not postdate", reason)
            link = first / "out" / "dispatch" / "escape.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                return
            ok, _reason = run_guard.check_path("out/dispatch/escape.txt", root=first)
            self.assertFalse(ok)

    def test_duplicate_key_and_non_object_stamp_fail_without_traceback(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            stamp_path = root / run_guard.STAMP_REL
            stamp_path.write_text('{"schema_version":2,"schema_version":2}\n', encoding="utf-8")
            ok, reason = run_guard.check_identity(root=root)
            self.assertFalse(ok)
            self.assertIn("duplicate", reason)
            stamp_path.write_text("[]\n", encoding="utf-8")
            ok, reason = run_guard.check_identity(root=root)
            self.assertFalse(ok)
            self.assertIn("object", reason)

    def test_registry_uniqueness_registered_props_real_date_and_canonical_stamp_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            with self.assertRaisesRegex(run_guard.RunIdentityError, "real calendar date"):
                run_guard.init("2026-99-99", "DispatchDaily", root=root)
            with self.assertRaisesRegex(run_guard.RunIdentityError, "registered path"):
                run_guard.init(
                    "2026-08-29", "DispatchDaily", props="out/dispatch/other.json", root=root,
                )
            registry_path = root / "config" / "compositions.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["compositions"]["LegacyDispatch"]["status"] = "active"
            write_json(registry_path, registry)
            with self.assertRaisesRegex(run_guard.RunIdentityError, "only DispatchDaily active"):
                init_identity(root)

        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            init_identity(root)
            stamp_path = root / run_guard.STAMP_REL
            stamp = json.loads(stamp_path.read_text(encoding="utf-8"))
            alternate = root / "out" / "dispatch" / "alternate_props.json"
            alternate.write_bytes((root / "out" / "dispatch" / "episode_props.json").read_bytes())
            stamp["props_path"] = "out/dispatch/alternate_props.json"
            stamp["props_sha256"] = run_guard._sha(alternate)
            write_json(stamp_path, stamp)
            ok, reason = run_guard.check_identity(root=root)
            self.assertFalse(ok)
            self.assertIn("props_path does not match", reason)


class DeliverableContractTests(unittest.TestCase):
    def prepared(self, parent: Path):
        root = make_identity_repo(parent)
        copy_delivery_config(root)
        stamp = init_identity(root)
        facts = make_artifacts(root, stamp)
        probe = lambda path: dict(facts[str(Path(path).resolve())])
        return root, stamp, facts, probe

    def test_exact_five_roles_and_both_poster_sizes_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, _facts, probe = self.prepared(Path(td))
            manifest = dc.build_manifest(root=root, probe=probe)
            self.assertEqual(set(manifest["artifacts"]), set(dc.EXPECTED_ROLES))
            self.assertEqual(
                (manifest["artifacts"]["poster_square"]["width"], manifest["artifacts"]["poster_square"]["height"]),
                (1080, 1080),
            )
            self.assertEqual(
                (manifest["artifacts"]["poster_thumb_vertical"]["width"], manifest["artifacts"]["poster_thumb_vertical"]["height"]),
                (540, 960),
            )
            checked, problems = dc.validate_manifest(root=root, probe=probe)
            self.assertIsNotNone(checked)
            self.assertEqual(problems, [])

    def test_same_size_mtime_preserving_mutation_fails_sha(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, _facts, probe = self.prepared(Path(td))
            dc.build_manifest(root=root, probe=probe)
            target = root / "out" / "dispatch" / "dispatch_square.mp4"
            stat = target.stat()
            data = bytearray(target.read_bytes())
            data[0] ^= 1
            target.write_bytes(data)
            os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            _manifest, problems = dc.validate_manifest(root=root, probe=probe)
            self.assertTrue(any("square SHA-256 changed" in problem for problem in problems), problems)

    def test_each_of_five_artifact_mutations_fails(self):
        for role in dc.EXPECTED_ROLES:
            with self.subTest(role=role), tempfile.TemporaryDirectory() as td:
                root, _stamp, _facts, probe = self.prepared(Path(td))
                manifest = dc.build_manifest(root=root, probe=probe)
                target = root.joinpath(*manifest["artifacts"][role]["path"].split("/"))
                stat = target.stat()
                payload = bytearray(target.read_bytes())
                payload[-1] ^= 1
                target.write_bytes(payload)
                os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                _checked, problems = dc.validate_manifest(root=root, probe=probe)
                self.assertTrue(any(role in problem and "SHA-256" in problem for problem in problems), problems)

    def test_wrong_dimensions_streams_duration_and_forbidden_4x5_fail_cleanly(self):
        cases = (
            ("dimensions", "vertical_hosted", {"width": 1080, "height": 1918}, "expected 1080x1920"),
            ("forbidden", "vertical_hosted", {"width": 1080, "height": 1350}, "forbidden dimensions"),
            ("streams", "square", {"streams": {"video": 1, "audio": 0}}, "streams are"),
            ("duration", "mobile", {"duration_seconds": 12.0}, "duration"),
        )
        for label, role, override, expected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                root, _stamp, facts, _probe = self.prepared(Path(td))
                cfg = dc.load_config(root=root)
                path = root.joinpath(*cfg["roles"][role]["path"].split("/")).resolve()
                facts[str(path)].update(override)
                probe = lambda target: dict(facts[str(Path(target).resolve())])
                with self.assertRaisesRegex(dc.DeliverableContractError, expected):
                    dc.build_manifest(root=root, probe=probe)

    def test_config_cannot_redefine_exact_role_dimensions_or_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            copy_delivery_config(root)
            cfg_path = root / "config" / "deliverables.json"
            original = json.loads(cfg_path.read_text(encoding="utf-8"))
            for field, value in (("height", 1918), ("path", "out/dispatch/another.mp4")):
                with self.subTest(field=field):
                    changed = json.loads(json.dumps(original))
                    changed["roles"]["vertical_hosted"][field] = value
                    write_json(cfg_path, changed)
                    with self.assertRaisesRegex(dc.DeliverableContractError, "vertical_hosted must be"):
                        dc.load_config(root=root)

    def test_pre_stamp_and_equal_stamp_artifacts_fail(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            copy_delivery_config(root)
            cfg = dc.load_config(root=root)
            for role in dc.EXPECTED_ROLES:
                spec = cfg["roles"][role]
                path = root.joinpath(*spec["path"].split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"x" * (spec["minimum_bytes"] + 17))
            stamp = init_identity(root)
            facts = {}
            for role in dc.EXPECTED_ROLES:
                spec = cfg["roles"][role]
                path = root.joinpath(*spec["path"].split("/")).resolve()
                os.utime(path, (stamp["started_at"], stamp["started_at"]))
                facts[str(path)] = {
                    "width": spec["width"], "height": spec["height"],
                    "duration_seconds": 100.0 if spec["media_type"] == "video" else None,
                    "streams": {"video": spec["video_streams"], "audio": spec["audio_streams"]},
                    "video_codecs": [], "audio_codecs": [],
                }
            with self.assertRaisesRegex(dc.DeliverableContractError, "does not postdate"):
                dc.build_manifest(root=root, probe=lambda target: facts[str(Path(target).resolve())])

    def test_config_rejects_duplicate_colliding_absolute_backslash_traversal_and_unicode_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            copy_delivery_config(root)
            cfg = json.loads((root / "config" / "deliverables.json").read_text(encoding="utf-8"))
            bad_values = (
                "C:/outside.mp4", "//server/share.mp4", "../outside.mp4",
                "out\\dispatch\\bad.mp4", "out/dispatch/Qargiŋ.mp4",
            )
            for index, bad in enumerate(bad_values):
                with self.subTest(path=bad):
                    changed = json.loads(json.dumps(cfg))
                    changed["roles"]["vertical_hosted"]["path"] = bad
                    bad_path = root / "config" / f"bad-{index}.json"
                    write_json(bad_path, changed)
                    with self.assertRaises(dc.DeliverableContractError):
                        dc.load_config(root=root, config_path=bad_path)
            collided = json.loads(json.dumps(cfg))
            collided["roles"]["square"]["path"] = collided["roles"]["vertical_hosted"]["path"]
            bad_path = root / "config" / "collision.json"
            write_json(bad_path, collided)
            with self.assertRaisesRegex(dc.DeliverableContractError, "collision"):
                dc.load_config(root=root, config_path=bad_path)
            duplicate = root / "config" / "duplicate.json"
            duplicate.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
            with self.assertRaises(StrictJSONError):
                load_path(duplicate)

    def test_publication_receipt_requires_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, _facts, probe = self.prepared(Path(td))
            manifest = dc.build_manifest(root=root, probe=probe)
            entry = manifest["artifacts"]["vertical_hosted"]
            with self.assertRaisesRegex(dc.DeliverableContractError, "do not match"):
                dc.record_publication(
                    "vertical_hosted", "https://example.invalid/master.mp4",
                    remote_bytes=entry["bytes"], remote_sha256="0" * 64, root=root,
                    probe=probe,
                )
            dc.record_publication(
                "vertical_hosted", "https://example.invalid/master.mp4",
                remote_bytes=entry["bytes"], remote_sha256=entry["sha256"], root=root,
                probe=probe,
            )
            receipt = dc.require_publication_url(
                "vertical_hosted", "https://example.invalid/master.mp4", root=root, probe=probe
            )
            self.assertEqual(receipt["sha256"], entry["sha256"])
            manifest_path = root / dc.EXPECTED_MANIFEST_PATH
            tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
            tampered["publications"]["vertical_hosted"]["sha256"] = "f" * 64
            write_json(manifest_path, tampered)
            _checked, problems = dc.validate_manifest(root=root, probe=probe)
            self.assertTrue(any("published vertical_hosted bytes" in p for p in problems), problems)

    def test_manifest_duplicate_keys_and_non_object_fail_concisely(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, _facts, probe = self.prepared(Path(td))
            dc.build_manifest(root=root, probe=probe)
            target = root / dc.EXPECTED_MANIFEST_PATH
            target.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
            _manifest, problems = dc.validate_manifest(root=root, probe=probe)
            self.assertIn("duplicate", ";".join(problems))
            self.assertNotIn("Traceback", ";".join(problems))
            target.write_text("[]\n", encoding="utf-8")
            _manifest, problems = dc.validate_manifest(root=root, probe=probe)
            self.assertIn("JSON object", ";".join(problems))

    def test_remote_verifier_reads_and_hashes_exact_published_bytes(self):
        class Response:
            status = 200
            headers = {"Content-Type": "video/mp4"}

            def __init__(self, payload):
                self.payload = payload
                self.offset = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, size):
                chunk = self.payload[self.offset:self.offset + size]
                self.offset += len(chunk)
                return chunk

        with tempfile.TemporaryDirectory() as td:
            local = Path(td) / "fixture.mp4"
            payload = b"exact-published-bytes"
            local.write_bytes(payload)
            with mock.patch.object(upload_video, "urlopen", return_value=Response(payload)):
                ok, detail, remote_bytes, remote_sha = upload_video.verify_exact(
                    "https://example.invalid/fixture.mp4", str(local)
                )
            self.assertTrue(ok, detail)
            self.assertEqual(remote_bytes, len(payload))
            self.assertEqual(remote_sha, dc.sha256_file(local))
            changed = bytes([payload[0] ^ 1]) + payload[1:]
            with mock.patch.object(upload_video, "urlopen", return_value=Response(changed)):
                ok, detail, _bytes, _sha = upload_video.verify_exact(
                    "https://example.invalid/fixture.mp4", str(local)
                )
            self.assertFalse(ok)
            self.assertIn("SHA-256", detail)

    def test_real_ffprobe_fixture_has_named_media_facts(self):
        package = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
        ffmpeg = next(package.glob("Gyan.FFmpeg_*/*/bin/ffmpeg.exe"), None)
        ffprobe = next(package.glob("Gyan.FFmpeg_*/*/bin/ffprobe.exe"), None)
        if not ffmpeg or not ffprobe:
            self.skipTest("local ffmpeg fixture tools unavailable")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "tiny.mp4"
            result = subprocess.run(
                [
                    str(ffmpeg), "-y", "-f", "lavfi", "-i", "color=c=navy:s=64x64:d=0.5:r=10",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(target),
                    "-loglevel", "error",
                ], capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with mock.patch.dict(os.environ, {"PATH": str(ffprobe.parent) + os.pathsep + os.environ.get("PATH", "")}):
                facts = dc.probe_media(target)
            self.assertEqual((facts["width"], facts["height"]), (64, 64))
            self.assertEqual(facts["streams"], {"video": 1, "audio": 1})
            self.assertGreater(facts["duration_seconds"], 0)


class GateBlocked(Exception):
    def __init__(self, reasons):
        self.reasons = reasons
        super().__init__("; ".join(str(reason) for reason in reasons))


def manifest_fixture() -> dict:
    artifacts = {}
    dimensions = {
        "vertical_hosted": (1080, 1920, 1, 1, 100.0),
        "square": (1080, 1080, 1, 1, 100.0),
        "mobile": (720, 1280, 1, 1, 100.0),
        "poster_square": (1080, 1080, 1, 0, None),
        "poster_thumb_vertical": (540, 960, 1, 0, None),
    }
    for index, (role, (width, height, video, audio, duration)) in enumerate(dimensions.items(), 1):
        artifacts[role] = {
            "path": f"out/dispatch/{role}.bin", "media_type": "video" if duration else "image",
            "width": width, "height": height, "duration_seconds": duration,
            "streams": {"video": video, "audio": audio}, "bytes": index * 1000,
            "sha256": f"{index:064x}", "video_codecs": [], "audio_codecs": [],
        }
    return {"schema_version": 1, "identity": {"run_id": "fixture"}, "artifacts": artifacts, "publications": {}}


class ShipGateTests(unittest.TestCase):
    def make_sfx_repo(self, parent: Path):
        root = make_identity_repo(parent)
        stamp = init_identity(root)
        audio = root / "out" / "dispatch" / "audio" / "master.wav"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(b"current-audio-master")
        os.utime(audio, (stamp["started_at"] + 1, stamp["started_at"] + 1))
        path = root / "out" / "dispatch" / "sfx_events.json"
        events = [{"t": float(index + 1), "kind": f"hit_{index}"} for index in range(6)]
        write_json(path, {
            "count": 6,
            "video_seconds": 100.0,
            "kinds": [f"hit_{index}" for index in range(6)],
            "audio": {
                "path": "out/dispatch/audio/master.wav",
                "bytes": audio.stat().st_size,
                "sha256": ship_gate.sha(audio),
            },
            "events": events,
        })
        os.utime(path, (stamp["started_at"] + 2, stamp["started_at"] + 2))
        return root, stamp, path, events

    def test_valid_sfx_and_malformed_missing_wrong_type_stale_and_out_of_range(self):
        with tempfile.TemporaryDirectory() as td:
            root, stamp, path, events = self.make_sfx_repo(Path(td))
            facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertEqual(problems, [])
            self.assertEqual(facts["count"], 6)
            path.write_text("{bad", encoding="utf-8")
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertTrue(problems)
            self.assertNotIn("Traceback", ";".join(problems))
            write_json(path, {"events": "wrong"})
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertIn("must be a list", ";".join(problems))
            bad = list(events)
            bad[0] = {"t": float("nan"), "kind": "Hit"}
            write_json(path, {"events": bad})
            os.utime(path, (stamp["started_at"], stamp["started_at"]))
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            joined = ";".join(problems)
            self.assertIn("finite", joined)
            self.assertIn("does not postdate", joined)
            self.assertNotIn("Traceback", joined)
            bad = list(events)
            bad[0] = {"t": 1.0, "kind": "Hit"}
            bad[1] = {"t": 101, "kind": "ok"}
            write_json(path, {"events": bad})
            os.utime(path, (stamp["started_at"], stamp["started_at"]))
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            joined = ";".join(problems)
            self.assertIn("lowercase ASCII", joined)
            self.assertIn("beyond", joined)
            self.assertIn("does not postdate", joined)
            path.unlink()
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertIn("no out/dispatch/sfx_events.json", problems)

    def test_same_size_mtime_preserving_audio_mutation_invalidates_sfx_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, path, _events = self.make_sfx_repo(Path(td))
            audio = root / "out" / "dispatch" / "audio" / "master.wav"
            stat = audio.stat()
            payload = bytearray(audio.read_bytes())
            payload[0] ^= 1
            audio.write_bytes(payload)
            os.utime(audio, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertIn("audio facts do not match", ";".join(problems))

    def run_check(self, directory: Path, *, evidence_now=None, sfx_now=None, verdict_mutator=None):
        manifest = manifest_fixture()
        artifacts = {role: entry["sha256"] for role, entry in manifest["artifacts"].items()}
        evidence = {"contact.jpg": "a" * 64}
        sfx = {"path": "out/dispatch/sfx_events.json", "sha256": "b" * 64, "count": 6,
               "kinds": ["hit"], "first_seconds": 1.0, "last_seconds": 6.0,
               "audio": {"path": "out/dispatch/audio/master.wav", "bytes": 12,
                         "sha256": "e" * 64}}
        media_facts = {
            role: {"sha256": entry["sha256"], "bytes": entry["bytes"],
                   "duration_seconds": entry["duration_seconds"], "streams": entry["streams"]}
            for role, entry in manifest["artifacts"].items()
        }
        verdict = {
            "median": 9.0, "judges": [8.8, 9.0, 9.2], "artifacts": artifacts,
            "evidence": evidence, "manifest_digest": dc.contract_digest(manifest),
            "media_facts": media_facts, "sfx": sfx,
        }
        if verdict_mutator:
            verdict_mutator(verdict)
        verdict_path = directory / "panel_verdict.json"
        write_json(verdict_path, verdict)
        render = directory / "render"
        render.mkdir()
        with mock.patch.object(ship_gate, "VERDICT", verdict_path), \
             mock.patch.object(ship_gate, "RENDER", render), \
             mock.patch.object(ship_gate, "ATTEMPTS", directory / "attempts.json"), \
             mock.patch.object(ship_gate, "check_render_is_current"), \
             mock.patch.object(ship_gate, "check_not_blank"), \
             mock.patch.object(ship_gate, "check_beats_delivered"), \
             mock.patch.object(ship_gate, "artifact_state", return_value=(artifacts, evidence_now or evidence, manifest)), \
             mock.patch.object(ship_gate, "sfx_facts", return_value=(sfx_now or sfx, [])), \
             mock.patch.object(ship_gate, "ship_threshold", return_value=8.6), \
             mock.patch.object(ship_gate, "owner_release", return_value=None), \
             mock.patch.object(ship_gate, "run_date", return_value="2026-08-29"):
            ship_gate.cmd_check(mock.Mock())
        return render

    def test_valid_sfx_reaches_evidence_comparison_and_passes(self):
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            render = self.run_check(Path(td))
            self.assertTrue((render / "SHIP_NOW").is_file())

    def test_post_panel_sfx_and_evidence_mutations_fail_by_hash(self):
        cases = (
            ({"contact.jpg": "c" * 64}, None, "review evidence contact.jpg changed"),
            (None, {"path": "out/dispatch/sfx_events.json", "sha256": "d" * 64,
                    "count": 6, "kinds": ["hit"], "first_seconds": 1.0,
                    "last_seconds": 6.0,
                    "audio": {"path": "out/dispatch/audio/master.wav", "bytes": 12,
                              "sha256": "e" * 64}},
             "sfx_events.json changed"),
        )
        for evidence, sfx, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as td, \
                 mock.patch.object(ship_gate, "fail", side_effect=lambda reasons, median=None: (_ for _ in ()).throw(GateBlocked(reasons))):
                with self.assertRaisesRegex(GateBlocked, expected):
                    self.run_check(Path(td), evidence_now=evidence, sfx_now=sfx)

    def test_malformed_verdict_is_concise_gate_failure(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            verdict = directory / "panel_verdict.json"
            verdict.write_text('{"median":9,"median":8}\n', encoding="utf-8")
            with mock.patch.object(ship_gate, "VERDICT", verdict), \
                 mock.patch.object(ship_gate, "check_render_is_current"), \
                 mock.patch.object(ship_gate, "check_not_blank"), \
                 mock.patch.object(ship_gate, "check_beats_delivered"), \
                 mock.patch.object(ship_gate, "fail", side_effect=lambda reasons, median=None: (_ for _ in ()).throw(GateBlocked(reasons))):
                with self.assertRaises(GateBlocked) as caught:
                    ship_gate.cmd_check(mock.Mock())
            self.assertIn("duplicate", str(caught.exception))
            self.assertNotIn("Traceback", str(caught.exception))

    def test_wrong_type_evidence_is_concise_gate_failure(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(ship_gate, "fail", side_effect=lambda reasons, median=None: (_ for _ in ()).throw(GateBlocked(reasons))):
            with self.assertRaisesRegex(GateBlocked, "verdict evidence must be an object"):
                self.run_check(Path(td), verdict_mutator=lambda verdict: verdict.update(evidence=[]))


class StaticContractTests(unittest.TestCase):
    def test_one_active_registration_no_generic_fallback_and_explicit_package_props(self):
        root = (REPO / "video-engine" / "src" / "Root.tsx").read_text(encoding="utf-8")
        self.assertEqual(root.count('id="DispatchDaily"'), 1)
        self.assertNotIn('id="Dispatch"', root)
        registry = json.loads((REPO / "config" / "compositions.json").read_text(encoding="utf-8"))
        active = [name for name, record in registry["compositions"].items() if record["status"] == "active"]
        self.assertEqual(active, ["DispatchDaily"])
        package = json.loads((REPO / "video-engine" / "package.json").read_text(encoding="utf-8"))
        self.assertIn("DispatchDaily", package["scripts"]["render"])
        self.assertIn("--props=", package["scripts"]["render"])
        for name in ("render.sh", "render_parallel.sh", "probe_frames.sh"):
            text = (REPO / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("DispatchDaily", text)
            self.assertNotIn("${RUN_COMP:-Dispatch}", text)

    def test_encoder_and_consumers_share_hosted_vertical_and_vertical_thumb(self):
        encoder = (REPO / "scripts" / "encode_deliverables.sh").read_text(encoding="utf-8")
        self.assertIn("dispatch_mastering_source.mp4", encoder)
        self.assertIn("dispatch_master_hosted.mp4", encoder)
        self.assertIn("poster_thumb_vertical.jpg", encoder)
        self.assertIn("scale=540:960", encoder)
        for name in (
            "ship_gate.py", "build_evidence.py", "caption_render_check.py", "chroma_check.py",
            "credits_check.py", "edge_bleed_check.py", "motion_check.py", "vo_audio_check.py",
        ):
            text = (REPO / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("dispatch_master_hosted.mp4", text, name)
        loop = (REPO / "scripts" / "dispatch_loop.sh").read_text(encoding="utf-8")
        self.assertIn("RETIRED", loop)
        self.assertIn("exit 2", loop)


if __name__ == "__main__":
    unittest.main()
