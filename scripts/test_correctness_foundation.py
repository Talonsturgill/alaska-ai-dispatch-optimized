#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import copy
import io
import importlib.util
import array
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import wave
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
REPO = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import deliverable_contract as dc
import build_evidence
import build_scenes
import credits_contract
import credits_check
import delivery_preview
import dispatch_email
import episode_contract
import evidence_contract
import mastering_contract
import mix_json_contract
import no_exit
import panel_ledger
import preflight
import render_contract
import run_guard
import sfx_contract
import ship_gate
import ship_marker
import upload_video
import video_judge_contract
from strict_json import StrictJSONError, canonical_bytes, load_path, loads


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
            "render_inputs": [
                "video-engine/package.json",
                "video-engine/package-lock.json",
                "video-engine/remotion.config.ts",
                "video-engine/tsconfig.json",
            ],
            "compositions": {
                "DispatchDaily": {
                    "status": "active",
                    "component": "DispatchDaily",
                    "source": "video-engine/src/DispatchDaily.tsx",
                    "source_dependencies": ["video-engine/src/StoryFixture.tsx"],
                    "props": "out/dispatch/episode_props.json",
                    "mute_render_path": "out/dispatch/render/video_mute.mp4",
                    "render_receipt_path": "out/dispatch/render/render_receipt.json",
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
    write_json(
        root / "out" / "dispatch" / "episode_props.json",
        {
            "total": 3000,
            "fps": 30,
            "scenes": [{"from": 0, "dur": 2700}],
            "credits": {"frames": 300, "seconds": 10.0},
        },
    )
    write_json(root / "video-engine" / "package.json", {"private": True})
    write_json(root / "video-engine" / "package-lock.json", {"lockfileVersion": 3})
    write_json(root / "video-engine" / "tsconfig.json", {"compilerOptions": {}})
    (root / "video-engine" / "remotion.config.ts").write_text("export {};\n", encoding="utf-8")
    git(root, "init", "-b", "main")
    git(root, "remote", "add", "origin", "https://github.com/TestOwner/test-repo.git")
    git(root, "add", ".")
    git(root, "-c", "user.name=Test Owner", "-c", "user.email=test@example.com", "commit", "-m", "fixture")
    return root


def init_identity(root: Path) -> dict:
    run_guard.init(
        "2026-08-29-test", "DispatchDaily", root=root,
    )
    return run_guard.bind_render_inputs(root=root)


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
            "video_codecs": list(spec["allowed_video_codecs"]),
            "audio_codecs": ["aac"] if spec["audio_streams"] else [],
            "fps": 30.0 if spec["media_type"] == "video" else 25.0,
            "frame_count": 3000 if spec["media_type"] == "video" else 1,
        }
    return facts


def make_render(root: Path, stamp: dict):
    target = root / render_contract.CANONICAL_RENDER_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"canonical-mute-render" * 100)
    os.utime(target, (stamp["started_at"] + 1, stamp["started_at"] + 1))
    facts = {
        "width": 1080,
        "height": 1920,
        "frames": 3000,
        "duration_seconds": 100.0,
        "streams": {"video": 1, "audio": 0},
    }
    probe = lambda _path: dict(facts)
    render_contract.record_render(root=root, probe=probe)
    return probe


def make_sfx_events(root: Path, *, count: int = 6, spacing: float = 10.0) -> list[dict]:
    events = []
    for index in range(count):
        relative = f"assets/sfx/hit_{index}_v1.wav"
        take = root.joinpath(*relative.split("/"))
        take.parent.mkdir(parents=True, exist_ok=True)
        take.write_bytes((f"take-{index}".encode("ascii")) * 200)
        planned = float(index * spacing)
        events.append({
            "t": planned + 0.005,
            "planned_t": planned,
            "kind": f"hit_{index}",
            "class": "standard",
            "pan": 0.1,
            "take": relative,
            "take_sha256": sfx_contract.sha256_file(take),
            "family": "impact",
            "pitch_cents": 12.5,
            "gain_db": -9.5,
        })
    return events


def fake_tool_facts() -> dict:
    return {
        "ffmpeg": {"path": "C:/fixture/ffmpeg", "version": "ffmpeg fixture"},
        "ffprobe": {"path": "C:/fixture/ffprobe", "version": "ffprobe fixture"},
        "python": {"path": "C:/fixture/python", "version": "3.fixture"},
    }


def fake_audio_lineage(_root: Path, source_relative: str, roles: dict[str, str]) -> dict:
    return {
        "algorithm": "aligned-pcm-spectral-cepstral-v3",
        "sample_rate": mastering_contract.AUDIO_SAMPLE_RATE,
        "block_samples": mastering_contract.AUDIO_BLOCK_SAMPLES,
        "spectral": {
            "window_samples": mastering_contract.AUDIO_SPECTRAL_WINDOW,
            "bins": mastering_contract.AUDIO_SPECTRAL_BINS,
            "windows": mastering_contract.AUDIO_SPECTRAL_WINDOWS,
        },
        "aac_packet_sha256": "b" * 64,
        "tolerances": {
            "minimum_envelope_correlation": mastering_contract.AUDIO_MIN_ENVELOPE_CORRELATION,
            "maximum_envelope_normalized_error": mastering_contract.AUDIO_MAX_ENVELOPE_NORMALIZED_ERROR,
            "minimum_waveform_correlation": mastering_contract.AUDIO_MIN_WAVEFORM_CORRELATION,
            "maximum_waveform_normalized_error": mastering_contract.AUDIO_MAX_WAVEFORM_NORMALIZED_ERROR,
            "minimum_spectral_similarity": mastering_contract.AUDIO_MIN_SPECTRAL_SIMILARITY,
            "maximum_cepstral_distance": mastering_contract.AUDIO_MAX_CEPSTRAL_DISTANCE,
            "maximum_duration_delta_seconds": mastering_contract.AUDIO_MAX_DURATION_DELTA_SECONDS,
            "maximum_lag_blocks": mastering_contract.AUDIO_MAX_LAG_BLOCKS,
        },
        "source": {
            "path": source_relative, "container_sha256": "0" * 64,
            "decoded_pcm_sha256": "1" * 64,
            "feature_fingerprint_sha256": "a" * 64, "sample_count": 1600000,
            "duration_seconds": 100.0,
        },
        "roles": {
            role: {
                "path": relative, "container_sha256": f"{index + 5:x}" * 64,
                "decoded_pcm_sha256": f"{index + 2:x}" * 64,
                "encoded_audio_packet_sha256": "b" * 64,
                "feature_fingerprint_sha256": "a" * 64, "sample_count": 1600000,
                "duration_seconds": 100.0, "envelope_correlation": 0.999,
                "envelope_normalized_error": 0.01, "waveform_correlation": 0.999,
                "waveform_normalized_error": 0.01, "spectral_similarity": 0.999,
                "cepstral_distance": 0.01, "lag_samples": 0,
                "duration_delta_seconds": 0.0,
            }
            for index, (role, relative) in enumerate(roles.items())
        },
    }


def make_mastering_sources(root: Path, stamp: dict) -> None:
    audio = root.joinpath(*sfx_contract.AUDIO_REL.split("/"))
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"audio-master" * 200)
    os.utime(audio, (stamp["started_at"] + 1, stamp["started_at"] + 1))
    sfx_contract.write_sidecar(audio, make_sfx_events(root), root=root)
    vo = root / "out" / "dispatch" / "audio" / "vo.wav"
    vo.write_bytes(b"voice" * 300)
    write_json(root / "out" / "dispatch" / "audio" / "words.json", {"words": []})
    (root / "out" / "dispatch" / "music_bed.wav").write_bytes(b"music" * 300)
    for relative in mastering_contract.SOURCE_TOOLS:
        target = root.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO.joinpath(*relative.split("/")), target)


def make_mastering(root: Path, stamp: dict, render_probe) -> dict:
    """Create canonical sources and transactionally bind the already-made five files."""
    make_mastering_sources(root, stamp)
    preserved = {}
    for relative in (
        mastering_contract.MASTERING_SOURCE_REL,
        *mastering_contract.EXPECTED_ARTIFACTS.values(),
    ):
        path = root.joinpath(*relative.split("/"))
        if path.is_file():
            preserved[relative] = path.read_bytes()
    mastering_contract.prepare_mastering(
        root=root, render_probe=render_probe, tool_probe=fake_tool_facts,
    )
    for relative, payload in preserved.items():
        path = root.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    internal = root.joinpath(*mastering_contract.MASTERING_SOURCE_REL.split("/"))
    internal.parent.mkdir(parents=True, exist_ok=True)
    if not internal.exists():
        internal.write_bytes(b"internal-master" * 100)
    return mastering_contract.finalize_mastering(
        root=root, render_probe=render_probe, tool_probe=fake_tool_facts,
        audio_probe=fake_audio_lineage,
    )


def load_quality_gate_module():
    path = REPO / ".claude" / "skills" / "alaska-dispatch" / "quality_gate.py"
    spec = importlib.util.spec_from_file_location("canonical_quality_gate", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StrictJSONTests(unittest.TestCase):
    def test_nonfinite_overflow_recursion_unicode_and_canonical_nan_fail_concisely(self):
        for payload in ("1e999", "[" * 2000 + "0" + "]" * 2000, "9" * 5000):
            with self.subTest(prefix=payload[:12]):
                with self.assertRaises(StrictJSONError) as caught:
                    loads(payload, label="fixture")
                self.assertNotIn("Traceback", str(caught.exception))
        with self.assertRaises(StrictJSONError):
            canonical_bytes({"bad": float("nan")})
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "bad.json"
            target.write_bytes(b'{"bad":"\xff"}')
            with self.assertRaises(StrictJSONError) as caught:
                load_path(target, label="fixture")
            self.assertIn("cannot be read", str(caught.exception))

    def test_build_evidence_email_and_claim_boundaries_reject_duplicate_or_non_object(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out"
            out.mkdir()
            write_json(out / "episode_props.json", {})
            (out / "vo_lines.json").write_text(
                '{"lines":[],"lines":[]}\n', encoding="utf-8",
            )
            with self.assertRaisesRegex(StrictJSONError, "duplicate"):
                build_evidence.load_run_inputs(out)
            (out / "vo_lines.json").write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(StrictJSONError, "object"):
                build_evidence.load_run_inputs(out)
            sources = root / "sources.json"
            sources.write_text("[]\n", encoding="utf-8")
            with self.assertRaisesRegex(StrictJSONError, "object"):
                dispatch_email.load_sources(sources)
            sources.write_text('{"sources":[],"sources":[]}\n', encoding="utf-8")
            with self.assertRaisesRegex(StrictJSONError, "duplicate"):
                dispatch_email.load_sources(sources)

            engine = root / "Engine.tsx"
            voice = root / "vo.txt"
            engine.write_text("export {};\n", encoding="utf-8")
            voice.write_text("voice\n", encoding="utf-8")
            for payload in ('{"claims":[],"claims":[]}', "[]"):
                claims = root / "claims.json"
                claims.write_text(payload + "\n", encoding="utf-8")
                result = subprocess.run(
                    [sys.executable, str(REPO / "scripts" / "claims_contract_check.py"),
                     "--claims", str(claims), "--vo", str(voice), "--engine", str(engine)],
                    capture_output=True, text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("Traceback", result.stderr + result.stdout)

    def test_dispatch_mix_required_json_rejects_duplicate_nonobject_and_bad_timing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            words = root / "words.json"
            lines = root / "vo_lines.json"
            bad_words = (
                '{"words":[],"words":[]}',
                "[]",
                '{"words":[{"s":1.0,"e":0.5}]}',
            )
            for payload in bad_words:
                with self.subTest(words=payload):
                    words.write_text(payload + "\n", encoding="utf-8")
                    with self.assertRaises(mix_json_contract.MixInputError) as caught:
                        mix_json_contract.load_words(words)
                    self.assertNotIn("Traceback", str(caught.exception))
            for payload in ('{"lines":[],"lines":[]}', "[]"):
                with self.subTest(lines=payload):
                    lines.write_text(payload + "\n", encoding="utf-8")
                    with self.assertRaises(mix_json_contract.MixInputError) as caught:
                        mix_json_contract.load_vo_lines(lines)
                    self.assertNotIn("Traceback", str(caught.exception))
            with self.assertRaises(mix_json_contract.MixInputError):
                mix_json_contract.load_loudnorm('{"input_i":"-14","input_i":"-13"}')


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
                "origin", "worktree_root", "branch", "planning_git_head", "git_head",
                "started_at", "binding_state", "bound_at", "props_path", "props_sha256",
                "registry_path", "source_path", "source_sha256", "source_dependencies",
                "registry_sha256", "root_source_path", "root_source_sha256",
                "engine_sources_sha256", "render_inputs", "render_binding_sha256",
            }
            self.assertTrue(expected <= set(stamp))
            ok, reason = run_guard.check_identity(root=root, expected_composition="DispatchDaily")
            self.assertTrue(ok, reason)

    def test_planning_then_explicit_bind_allows_authoring_only_before_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            planning = run_guard.init("2026-08-29-plan", "DispatchDaily", root=root)
            self.assertEqual(planning["binding_state"], "planning")
            ok, reason = run_guard.check_identity(root=root)
            self.assertFalse(ok)
            self.assertIn("bind-render-inputs", reason)
            ok, reason = run_guard.check_identity(root=root, require_props=False)
            self.assertTrue(ok, reason)

            source = root / "video-engine" / "src" / "DispatchDaily.tsx"
            props = root / "out" / "dispatch" / "episode_props.json"
            source.write_text("export const DispatchDaily = () => 'authored';\n", encoding="utf-8")
            authored = json.loads(props.read_text(encoding="utf-8"))
            authored["captions"] = []
            write_json(props, authored)
            git(root, "add", "video-engine/src/DispatchDaily.tsx")
            git(root, "-c", "user.name=Test Owner", "-c", "user.email=test@example.com",
                "commit", "-m", "author replay inputs")
            ok, reason = run_guard.check_identity(root=root, require_props=False)
            self.assertTrue(ok, reason)
            bound = run_guard.bind_render_inputs(root=root)
            self.assertEqual(bound["binding_state"], "render_bound")
            self.assertRegex(bound["render_binding_sha256"], r"^[0-9a-f]{64}$")

            props.write_text(props.read_text(encoding="utf-8") + " ", encoding="utf-8")
            ok, reason = run_guard.check_identity(root=root)
            self.assertFalse(ok)
            self.assertIn("props changed", reason)
            with self.assertRaisesRegex(run_guard.RunIdentityError, "retired"):
                run_guard.bind_inputs(root=root)

    def test_copied_stamp_branch_props_registry_root_render_and_dependency_drift_fail(self):
        mutations = {
            "branch": lambda root: git(root, "switch", "-c", "other"),
            "props": lambda root: (root / "out" / "dispatch" / "episode_props.json").write_text("{}\n", encoding="utf-8"),
            "registry": lambda root: (root / "config" / "compositions.json").write_text(
                (root / "config" / "compositions.json").read_text(encoding="utf-8") + " ", encoding="utf-8"
            ),
            "root": lambda root: (root / "video-engine" / "src" / "Root.tsx").write_text("changed\n", encoding="utf-8"),
            "dependency": lambda root: (root / "video-engine" / "src" / "StoryFixture.tsx").write_text("changed\n", encoding="utf-8"),
            "transitive source": lambda root: (root / "video-engine" / "src" / "Shared.ts").write_text("export const shared = 2;\n", encoding="utf-8"),
            "render input": lambda root: (root / "video-engine" / "package.json").write_text(
                '{"private":false}\n', encoding="utf-8"
            ),
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

    def test_descendant_head_is_allowed_only_while_every_bound_input_is_unchanged(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            stamp = init_identity(root)
            (root / "artifact.txt").write_text("artifact-only commit", encoding="utf-8")
            git(root, "add", "artifact.txt")
            git(root, "-c", "user.name=Test Owner", "-c", "user.email=test@example.com", "commit", "-m", "artifact")
            ok, reason = run_guard.check_identity(root=root, expected_composition="DispatchDaily")
            self.assertTrue(ok, reason)
            self.assertNotEqual(git(root, "rev-parse", "HEAD"), stamp["git_head"])
            (root / "video-engine" / "package.json").write_text('{"private":false}\n', encoding="utf-8")
            ok, reason = run_guard.check_identity(root=root, expected_composition="DispatchDaily")
            self.assertFalse(ok)
            self.assertIn("render inputs changed", reason)

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


class CreditsContractTests(unittest.TestCase):
    def fixture(self, root: Path):
        out = root / "out" / "dispatch"
        out.mkdir(parents=True)
        source = root / "Episode.tsx"
        source.write_text(
            '<Sequence name="CREDITS"><EndCredits /></Sequence>\n', encoding="utf-8",
        )
        credit = "Test Track by Test Composer, CC BY 4.0"
        write_json(out / "episode_props.json", {
            "total": 3900,
            "credits": {
                "frames": 369, "seconds": 12.3, "music": credit,
                "sources": ["NSF AWARD 123456"], "site": "alaskaaihq.com",
            },
        })
        write_json(out / "music_credit.json", {"credit": credit})
        write_json(out / "sources.json", {"sources": [{
            "id": "s1", "title": "National Science Foundation award 123456",
            "url": "https://api.nsf.gov/services/v1/awards/123456.json",
        }]})
        (out / "dispatch_master_hosted.mp4").write_bytes(b"fixture video")
        return out, source

    def test_credits_reject_duplicate_nonobject_missing_sources_and_failed_duration_probe(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out, source = self.fixture(root)
            original = (out / "episode_props.json").read_text(encoding="utf-8")
            with mock.patch.object(credits_check, "OUT", str(out)), \
                 mock.patch.object(credits_check, "REPO", str(root)), \
                 mock.patch.object(credits_check, "registered_episode", return_value=str(source)):
                (out / "episode_props.json").write_text(
                    '{"credits":{},"credits":{}}\n', encoding="utf-8",
                )
                with self.assertRaisesRegex(StrictJSONError, "duplicate"):
                    credits_check.main()
                (out / "episode_props.json").write_text("[]\n", encoding="utf-8")
                with self.assertRaisesRegex(StrictJSONError, "object"):
                    credits_check.main()
                (out / "episode_props.json").write_text(original, encoding="utf-8")
                (out / "sources.json").unlink()
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(credits_check.main(), 1)
                write_json(out / "sources.json", {"sources": [{
                    "id": "s1", "title": "National Science Foundation award 123456",
                    "url": "https://api.nsf.gov/services/v1/awards/123456.json",
                }]})
                with mock.patch.object(
                    credits_check, "_probe_duration",
                    side_effect=RuntimeError("named duration probe failure"),
                ), self.assertRaisesRegex(RuntimeError, "named duration probe failure"):
                    credits_check.main()

    def test_credits_require_exact_shared_labels_and_fail_closed_on_contract_errors(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out, source = self.fixture(root)
            props_path = out / "episode_props.json"
            props = json.loads(props_path.read_text(encoding="utf-8"))
            props["credits"]["sources"] = ["MADE UP SOURCE"]
            write_json(props_path, props)
            with mock.patch.object(credits_check, "OUT", str(out)), \
                 mock.patch.object(credits_check, "REPO", str(root)), \
                 mock.patch.object(credits_check, "registered_episode", return_value=str(source)), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(credits_check.main(), 1)

            valid = {
                "sources": [{
                    "id": "s1", "title": "National Science Foundation award 123456",
                    "url": "https://api.nsf.gov/services/v1/awards/123456.json",
                }],
            }
            duplicate = copy.deepcopy(valid)
            duplicate["sources"].append(copy.deepcopy(duplicate["sources"][0]))
            with self.assertRaisesRegex(credits_contract.CreditsSourceError, "duplicate source id"):
                credits_contract.derive_source_labels(duplicate)
            wrong_type = copy.deepcopy(valid)
            wrong_type["sources"][0]["used_in_film"] = "yes"
            with self.assertRaisesRegex(credits_contract.CreditsSourceError, "must be boolean"):
                credits_contract.derive_source_labels(wrong_type)
            with self.assertRaisesRegex(credits_contract.CreditsSourceError, "must be an object"):
                credits_contract.derive_source_labels({"sources": ["not-an-object"]})

            with mock.patch.object(
                credits_check.importlib, "import_module",
                side_effect=ImportError("fixture missing contract"),
            ), self.assertRaisesRegex(RuntimeError, "cannot be imported"):
                credits_check.main()
            incomplete = type("IncompleteCreditsContract", (), {
                "CONTRACT_VERSION": 1, "CREDITS_MIN_S": 10.0, "CREDITS_TAIL_S": 2.3,
            })()
            with mock.patch.object(credits_check.importlib, "import_module", return_value=incomplete), \
                 self.assertRaisesRegex(RuntimeError, "missing derive_source_labels"):
                credits_check.main()


class EpisodeRenderIntegrationTests(unittest.TestCase):
    def test_build_timing_mix_sidecar_render_manifest_and_sfx_share_credits_duration(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            copy_delivery_config(root)
            run_guard.init("2026-08-29-integration", "DispatchDaily", root=root)
            credits = {"frames": 300, "seconds": 10.0}
            lines = [{"idx": 0, "start": 0.0, "end": 90.0}]
            timing = build_scenes.derive_episode_timing(lines, [0], credits)
            props = {
                "total": timing["total"],
                "fps": timing["fps"],
                "scenes": timing["scenes"],
                "credits": credits,
            }
            write_json(root / "out" / "dispatch" / "episode_props.json", props)
            stamp = run_guard.bind_render_inputs(root=root)
            episode = episode_contract.episode_facts(root=root)
            self.assertEqual(episode["credits_frames"], 300)
            self.assertEqual(episode["duration_seconds"], 101.0)

            audio = root / sfx_contract.AUDIO_REL
            audio.parent.mkdir(parents=True, exist_ok=True)
            audio.write_bytes(b"audio-master" * 200)
            os.utime(audio, (stamp["started_at"] + 1, stamp["started_at"] + 1))
            events = make_sfx_events(root)
            sidecar = sfx_contract.write_sidecar(audio, events, root=root)
            self.assertEqual(sidecar["video_seconds"], 101.0)

            render = root / render_contract.CANONICAL_RENDER_REL
            render.parent.mkdir(parents=True, exist_ok=True)
            render.write_bytes(b"mute-render" * 300)
            os.utime(render, (stamp["started_at"] + 3, stamp["started_at"] + 3))
            render_facts = {
                "width": 1080, "height": 1920, "frames": timing["total"],
                "duration_seconds": 101.0, "streams": {"video": 1, "audio": 0},
            }
            render_probe = lambda _path: dict(render_facts)
            render_contract.record_render(root=root, probe=render_probe)

            artifact_facts = make_artifacts(root, stamp)
            for facts in artifact_facts.values():
                if facts["duration_seconds"] is not None:
                    facts["duration_seconds"] = 101.0
                    facts["frame_count"] = timing["total"]
            probe = lambda path: dict(artifact_facts[str(Path(path).resolve())])
            make_mastering(root, stamp, render_probe)
            manifest = dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                                         mastering_audio_probe=fake_audio_lineage)
            self.assertEqual(manifest["episode"]["duration_seconds"], 101.0)
            facts, problems = sfx_contract.sidecar_facts(root=root)
            self.assertEqual(problems, [])
            self.assertEqual(facts["episode"], manifest["episode"])

    def test_render_receipt_rejects_alternate_path_and_same_size_hash_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            stamp = init_identity(root)
            probe = make_render(root, stamp)
            receipt = render_contract.require_render(root=root, probe=probe)
            target = root / render_contract.CANONICAL_RENDER_REL
            stat = target.stat()
            changed = bytearray(target.read_bytes())
            changed[0] ^= 1
            target.write_bytes(changed)
            os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            _receipt, problems = render_contract.validate_render(root=root, probe=probe)
            self.assertTrue(any("artifact" in problem for problem in problems), problems)
            target.write_bytes(bytes(changed))
            alternate = root / render_contract.RETIRED_RENDER_PATHS[0]
            alternate.parent.mkdir(parents=True, exist_ok=True)
            alternate.write_bytes(b"stale")
            _receipt, problems = render_contract.validate_render(root=root, probe=probe)
            self.assertTrue(any("alternate" in problem for problem in problems), problems)

    def test_prepare_removes_only_canonical_stale_render_and_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            stamp = init_identity(root)
            make_render(root, stamp)
            target = root / render_contract.CANONICAL_RENDER_REL
            receipt = root / render_contract.RECEIPT_REL
            self.assertTrue(target.is_file())
            self.assertTrue(receipt.is_file())
            render_contract.prepare_render(root=root)
            self.assertFalse(target.exists())
            self.assertFalse(receipt.exists())

            target.write_bytes(b"would-be-stale")
            receipt.write_text("{}\n", encoding="utf-8")
            alternate = root / render_contract.RETIRED_RENDER_PATHS[0]
            alternate.parent.mkdir(parents=True, exist_ok=True)
            alternate.write_bytes(b"retired")
            with self.assertRaisesRegex(render_contract.RenderContractError, "alternate"):
                render_contract.prepare_render(root=root)
            self.assertTrue(target.exists())
            self.assertTrue(receipt.exists())

    def test_chunk_receipt_binds_full_render_digest_exact_range_and_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            init_identity(root)
            chunk = root / "out" / "dispatch" / "chunk.mp4"
            receipt = root / "out" / "dispatch" / "chunk.json"
            chunk.write_bytes(b"chunk-bytes" * 100)
            facts = {
                "width": 1080, "height": 1920, "frames": 100,
                "duration_seconds": 100 / 30,
                "streams": {"video": 1, "audio": 0},
            }
            probe = lambda _path: dict(facts)
            recorded = render_contract.record_chunk(
                chunk, receipt, index=0, start=0, end=99, total=3000,
                root=root, probe=probe,
            )
            self.assertRegex(recorded["render_binding_sha256"], r"^[0-9a-f]{64}$")
            checked = render_contract.require_chunk(
                chunk, receipt, index=0, start=0, end=99, total=3000,
                root=root, probe=probe,
            )
            self.assertEqual(checked["chunk"], {"index": 0, "start": 0, "end": 99, "total": 3000})
            with self.assertRaisesRegex(render_contract.RenderContractError, "chunk"):
                render_contract.require_chunk(
                    chunk, receipt, index=0, start=1, end=100, total=3000,
                    root=root, probe=probe,
                )
            stat = chunk.stat()
            changed = bytearray(chunk.read_bytes())
            changed[0] ^= 1
            chunk.write_bytes(changed)
            os.utime(chunk, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            with self.assertRaisesRegex(render_contract.RenderContractError, "artifact"):
                render_contract.require_chunk(
                    chunk, receipt, index=0, start=0, end=99, total=3000,
                    root=root, probe=probe,
                )


class MasteringTransactionTests(unittest.TestCase):
    def test_prepare_clears_every_stale_success_before_missing_source_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            copy_delivery_config(root)
            stamp = init_identity(root)
            render_probe = make_render(root, stamp)
            stale = set(mastering_contract.CONTROL_PATHS) | set(mastering_contract.OUTPUT_PATHS)
            for relative in stale:
                path = root.joinpath(*relative.split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"stale-success")
            with self.assertRaises(mastering_contract.MasteringContractError):
                mastering_contract.prepare_mastering(
                    root=root, render_probe=render_probe, tool_probe=fake_tool_facts,
                )
            self.assertTrue(all(not root.joinpath(*relative.split("/")).exists() for relative in stale))

    def test_finalize_rejects_output_that_does_not_postdate_intent(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            copy_delivery_config(root)
            stamp = init_identity(root)
            render_probe = make_render(root, stamp)
            make_mastering_sources(root, stamp)
            intent = mastering_contract.prepare_mastering(
                root=root, render_probe=render_probe, tool_probe=fake_tool_facts,
            )
            internal = root.joinpath(*mastering_contract.MASTERING_SOURCE_REL.split("/"))
            internal.parent.mkdir(parents=True, exist_ok=True)
            internal.write_bytes(b"internal")
            for relative in mastering_contract.EXPECTED_ARTIFACTS.values():
                path = root.joinpath(*relative.split("/"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"post-intent-output")
            stale = root.joinpath(*mastering_contract.EXPECTED_ARTIFACTS["vertical_hosted"].split("/"))
            old_ns = intent["prepared_at_ns"] - 1_000_000_000
            os.utime(stale, ns=(old_ns, old_ns))
            with self.assertRaisesRegex(mastering_contract.MasteringContractError, "does not postdate"):
                mastering_contract.finalize_mastering(
                    root=root, render_probe=render_probe, tool_probe=fake_tool_facts,
                    audio_probe=fake_audio_lineage,
                )

    def test_real_decoded_audio_identity_accepts_aac_and_rejects_timbre_and_track_attacks(self):
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            self.skipTest("local ffmpeg unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            master = root.joinpath(*sfx_contract.AUDIO_REL.split("/"))
            master.parent.mkdir(parents=True)

            def run(*argv):
                result = subprocess.run([ffmpeg, "-y", *argv], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

            run(
                "-f", "lavfi", "-i",
                "aevalsrc=0.25*sin(2*PI*440*t)*(1+0.7*sin(2*PI*0.7*t)):d=4:s=48000",
                str(master),
            )
            roles = {role: mastering_contract.EXPECTED_ARTIFACTS[role]
                     for role in mastering_contract.AUDIO_ROLES}
            for relative in roles.values():
                target = root.joinpath(*relative.split("/"))
                target.parent.mkdir(parents=True, exist_ok=True)
                run(
                    "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=4",
                    "-i", str(master), "-shortest", "-c:v", "libx264", "-c:a", "aac",
                    str(target),
                )
            lineage = mastering_contract.decoded_audio_lineage(root, sfx_contract.AUDIO_REL, roles)
            self.assertEqual(set(lineage["roles"]), set(mastering_contract.AUDIO_ROLES))
            self.assertTrue(all(
                facts["waveform_correlation"] >= mastering_contract.AUDIO_MIN_WAVEFORM_CORRELATION
                for facts in lineage["roles"].values()
            ))
            correct_bytes = {
                role: root.joinpath(*relative.split("/")).read_bytes()
                for role, relative in roles.items()
            }
            attack_expressions = {
                # Exact reviewer reproduction: same fundamental and AM envelope,
                # but an audibly different square-wave timbre.
                "square-440": (
                    "0.25*sgn(sin(2*PI*440*t))*(1+0.7*sin(2*PI*0.7*t))"
                ),
                # The added third harmonic preserves every fundamental zero
                # crossing and the exact slow envelope; envelope+ZCR cannot tell.
                "same-envelope-zcr": (
                    "0.18*(sin(2*PI*440*t)+0.45*sin(2*PI*1320*t))"
                    "*(1+0.7*sin(2*PI*0.7*t))"
                ),
                "wrong-880-track": (
                    "0.25*sin(2*PI*880*t)*(1+0.7*sin(2*PI*0.7*t))"
                ),
            }
            attack_wavs = {}
            for attack_name, expression in attack_expressions.items():
                attack_wav = root / f"{attack_name}.wav"
                attack_wavs[attack_name] = attack_wav
                run("-f", "lavfi", "-i", f"aevalsrc={expression}:d=4:s=48000", str(attack_wav))

            with wave.open(str(master), "rb") as source_wave:
                params = source_wave.getparams()
                pcm = array.array("h")
                pcm.frombytes(source_wave.readframes(params.nframes))
            block_samples = round(params.framerate * 0.05)
            reversed_pcm = array.array("h", pcm)
            phase_pcm = array.array("h", pcm)
            for offset in range(0, len(pcm), block_samples):
                reversed_pcm[offset:offset + block_samples] = array.array(
                    "h", reversed_pcm[offset:offset + block_samples][::-1]
                )
                if (offset // block_samples) % 2:
                    phase_pcm[offset:offset + block_samples] = array.array(
                        "h", (-value for value in phase_pcm[offset:offset + block_samples])
                    )
            for attack_name, attack_pcm in (
                ("reversed-each-50ms", reversed_pcm),
                ("alternating-block-phase", phase_pcm),
            ):
                attack_wav = root / f"{attack_name}.wav"
                with wave.open(str(attack_wav), "wb") as target_wave:
                    target_wave.setparams(params)
                    target_wave.writeframes(attack_pcm.tobytes())
                attack_wavs[attack_name] = attack_wav

            for attack_name, attack_wav in attack_wavs.items():
                attack_video = root / f"{attack_name}.mp4"
                run(
                    "-f", "lavfi", "-i", "color=c=black:s=64x64:r=30:d=4",
                    "-i", str(attack_wav), "-shortest", "-c:v", "libx264", "-c:a", "aac",
                    "-b:a", "192k", str(attack_video),
                )
                for role, relative in roles.items():
                    target = root.joinpath(*relative.split("/"))
                    target.write_bytes(attack_video.read_bytes())
                    with self.subTest(attack=attack_name, role=role), self.assertRaisesRegex(
                        mastering_contract.MasteringContractError,
                        rf"{role}.*(waveform|spectral|cepstral|wrong audio)",
                    ):
                        mastering_contract.decoded_audio_lineage(root, sfx_contract.AUDIO_REL, roles)
                    target.write_bytes(correct_bytes[role])


class DeliverableContractTests(unittest.TestCase):
    def prepared(self, parent: Path):
        root = make_identity_repo(parent)
        copy_delivery_config(root)
        stamp = init_identity(root)
        render_probe = make_render(root, stamp)
        facts = make_artifacts(root, stamp)
        probe = lambda path: dict(facts[str(Path(path).resolve())])
        make_mastering(root, stamp, render_probe)
        return root, stamp, facts, probe, render_probe

    def test_exact_five_roles_and_both_poster_sizes_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, _facts, probe, render_probe = self.prepared(Path(td))
            manifest = dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                                         mastering_audio_probe=fake_audio_lineage)
            self.assertEqual(set(manifest["artifacts"]), set(dc.EXPECTED_ROLES))
            self.assertEqual(
                (manifest["artifacts"]["poster_square"]["width"], manifest["artifacts"]["poster_square"]["height"]),
                (1080, 1080),
            )
            self.assertEqual(
                (manifest["artifacts"]["poster_thumb_vertical"]["width"], manifest["artifacts"]["poster_thumb_vertical"]["height"]),
                (540, 960),
            )
            checked, problems = dc.validate_manifest(root=root, probe=probe, render_probe=render_probe,
                                                     mastering_audio_probe=fake_audio_lineage)
            self.assertIsNotNone(checked)
            self.assertEqual(problems, [])

    def test_same_size_mtime_preserving_mutation_fails_sha(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, _facts, probe, render_probe = self.prepared(Path(td))
            dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                              mastering_audio_probe=fake_audio_lineage)
            target = root / "out" / "dispatch" / "dispatch_square.mp4"
            stat = target.stat()
            data = bytearray(target.read_bytes())
            data[0] ^= 1
            target.write_bytes(data)
            os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            _manifest, problems = dc.validate_manifest(root=root, probe=probe, render_probe=render_probe,
                                                       mastering_audio_probe=fake_audio_lineage)
            self.assertTrue(any("square SHA-256 changed" in problem for problem in problems), problems)

    def test_each_of_five_artifact_mutations_fails(self):
        for role in dc.EXPECTED_ROLES:
            with self.subTest(role=role), tempfile.TemporaryDirectory() as td:
                root, _stamp, _facts, probe, render_probe = self.prepared(Path(td))
                manifest = dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                                             mastering_audio_probe=fake_audio_lineage)
                target = root.joinpath(*manifest["artifacts"][role]["path"].split("/"))
                stat = target.stat()
                payload = bytearray(target.read_bytes())
                payload[-1] ^= 1
                target.write_bytes(payload)
                os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                _checked, problems = dc.validate_manifest(root=root, probe=probe, render_probe=render_probe,
                                                          mastering_audio_probe=fake_audio_lineage)
                self.assertTrue(any(role in problem and "SHA-256" in problem for problem in problems), problems)

    def test_wrong_dimensions_streams_duration_and_forbidden_4x5_fail_cleanly(self):
        cases = (
            ("dimensions", "vertical_hosted", {"width": 1080, "height": 1918}, "expected 1080x1920"),
            ("forbidden", "vertical_hosted", {"width": 1080, "height": 1350}, "forbidden dimensions"),
            ("streams", "square", {"streams": {"video": 1, "audio": 0}}, "streams are"),
            ("duration", "mobile", {"duration_seconds": 12.0}, "duration"),
            ("fps", "mobile", {"fps": 29.97}, "required 30 fps"),
            ("frames", "square", {"frame_count": 2990}, "frame count"),
            ("codec", "square", {"video_codecs": ["hevc"]}, "video codecs"),
        )
        for label, role, override, expected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as td:
                root, _stamp, facts, _probe, render_probe = self.prepared(Path(td))
                cfg = dc.load_config(root=root)
                path = root.joinpath(*cfg["roles"][role]["path"].split("/")).resolve()
                facts[str(path)].update(override)
                probe = lambda target: dict(facts[str(Path(target).resolve())])
                with self.assertRaisesRegex(dc.DeliverableContractError, expected):
                    dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                                      mastering_audio_probe=fake_audio_lineage)

    def test_post_encode_master_audio_and_sfx_replacement_break_mastering_lineage(self):
        for relative, expected in (
            (sfx_contract.AUDIO_REL, "audio"),
            (sfx_contract.SIDECAR_REL, "SFX|sfx|ledger"),
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as td:
                root, _stamp, _facts, probe, render_probe = self.prepared(Path(td))
                dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                                  mastering_audio_probe=fake_audio_lineage)
                target = root.joinpath(*relative.split("/"))
                stat = target.stat()
                payload = bytearray(target.read_bytes())
                payload[len(payload) // 2] ^= 1
                target.write_bytes(payload)
                os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
                _manifest, problems = dc.validate_manifest(
                    root=root, probe=probe, render_probe=render_probe,
                    mastering_audio_probe=fake_audio_lineage,
                )
                message = "; ".join(problems)
                self.assertRegex(message, expected)
                self.assertNotIn("Traceback", message)

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
            render_probe = make_render(root, stamp)
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
                    "fps": 30.0 if spec["media_type"] == "video" else 25.0,
                    "frame_count": 3000 if spec["media_type"] == "video" else 1,
                }
            make_mastering(root, stamp, render_probe)
            # Transactional prepare intentionally deletes/recreates old outputs. Force
            # the resulting files back to the stamp boundary to exercise the delivery
            # contract's independent pre-stamp rejection.
            for role in dc.EXPECTED_ROLES:
                path = root.joinpath(*cfg["roles"][role]["path"].split("/"))
                os.utime(path, (stamp["started_at"], stamp["started_at"]))
            with self.assertRaisesRegex(dc.DeliverableContractError, "does not postdate"):
                dc.build_manifest(
                    root=root,
                    probe=lambda target: facts[str(Path(target).resolve())],
                    render_probe=render_probe,
                    mastering_audio_probe=fake_audio_lineage,
                )

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
            root, _stamp, _facts, probe, render_probe = self.prepared(Path(td))
            manifest = dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                                         mastering_audio_probe=fake_audio_lineage)
            entry = manifest["artifacts"]["vertical_hosted"]
            commit = "c" * 40
            name = dc.publication_name(manifest, "vertical_hosted")
            url = (
                f"https://raw.githubusercontent.com/{manifest['identity']['repository']}/"
                f"{commit}/media/{name}"
            )
            with self.assertRaisesRegex(dc.DeliverableContractError, "do not match"):
                dc.record_publication(
                    "vertical_hosted", url,
                    remote_bytes=entry["bytes"], remote_sha256="0" * 64, root=root,
                    media_name=name, media_commit_sha=commit,
                    probe=probe, render_probe=render_probe,
                    mastering_audio_probe=fake_audio_lineage,
                )
            dc.record_publication(
                "vertical_hosted", url,
                remote_bytes=entry["bytes"], remote_sha256=entry["sha256"], root=root,
                media_name=name, media_commit_sha=commit,
                probe=probe, render_probe=render_probe,
                mastering_audio_probe=fake_audio_lineage,
            )
            receipt = dc.require_publication_url(
                "vertical_hosted", url, root=root, probe=probe,
                render_probe=render_probe, mastering_audio_probe=fake_audio_lineage,
                verify_remote=False,
            )
            self.assertEqual(receipt["artifact"]["sha256"], entry["sha256"])
            self.assertEqual(receipt["media_name"], name)
            self.assertIn(entry["sha256"], name)
            other_commit = "e" * 40
            other_url = (
                f"https://raw.githubusercontent.com/{manifest['identity']['repository']}/"
                f"{other_commit}/media/{name}"
            )
            with self.assertRaisesRegex(dc.DeliverableContractError, "immutable"):
                dc.record_publication(
                    "vertical_hosted", other_url,
                    remote_bytes=entry["bytes"], remote_sha256=entry["sha256"], root=root,
                    media_name=name, media_commit_sha=other_commit,
                    probe=probe, render_probe=render_probe,
                    mastering_audio_probe=fake_audio_lineage,
                )
            manifest_path = root / dc.EXPECTED_MANIFEST_PATH
            tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
            tampered["publications"]["vertical_hosted"]["verified_sha256"] = "f" * 64
            write_json(manifest_path, tampered)
            _checked, problems = dc.validate_manifest(root=root, probe=probe, render_probe=render_probe,
                                                       mastering_audio_probe=fake_audio_lineage)
            self.assertTrue(any("verified_sha256" in p for p in problems), problems)

    def test_manifest_duplicate_keys_and_non_object_fail_concisely(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, _facts, probe, render_probe = self.prepared(Path(td))
            dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                              mastering_audio_probe=fake_audio_lineage)
            target = root / dc.EXPECTED_MANIFEST_PATH
            target.write_text('{"schema_version":1,"schema_version":1}\n', encoding="utf-8")
            _manifest, problems = dc.validate_manifest(root=root, probe=probe, render_probe=render_probe,
                                                       mastering_audio_probe=fake_audio_lineage)
            self.assertIn("duplicate", ";".join(problems))
            self.assertNotIn("Traceback", ";".join(problems))
            target.write_text("[]\n", encoding="utf-8")
            _manifest, problems = dc.validate_manifest(root=root, probe=probe, render_probe=render_probe,
                                                       mastering_audio_probe=fake_audio_lineage)
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

    def test_publication_consumer_refetches_full_object_and_rejects_collision(self):
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
            root, _stamp, _facts, probe, render_probe = self.prepared(Path(td))
            manifest = dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                                         mastering_audio_probe=fake_audio_lineage)
            commit = "d" * 40
            role = "vertical_hosted"
            entry = manifest["artifacts"][role]
            name = dc.publication_name(manifest, role)
            url = (
                f"https://raw.githubusercontent.com/{manifest['identity']['repository']}/"
                f"{commit}/media/{name}"
            )
            dc.record_publication(
                role, url, remote_bytes=entry["bytes"], remote_sha256=entry["sha256"],
                media_name=name, media_commit_sha=commit, root=root,
                probe=probe, render_probe=render_probe,
                mastering_audio_probe=fake_audio_lineage,
            )
            payload = root.joinpath(*entry["path"].split("/")).read_bytes()
            receipt = dc.require_publication_url(
                role, url, root=root, probe=probe, render_probe=render_probe,
                mastering_audio_probe=fake_audio_lineage,
                opener=lambda *_args, **_kwargs: Response(payload),
            )
            self.assertEqual(receipt["verified_sha256"], entry["sha256"])
            changed = bytes([payload[0] ^ 1]) + payload[1:]
            with self.assertRaisesRegex(dc.DeliverableContractError, "bytes/hash"):
                dc.require_publication_url(
                    role, url, root=root, probe=probe, render_probe=render_probe,
                    mastering_audio_probe=fake_audio_lineage,
                    opener=lambda *_args, **_kwargs: Response(changed),
                )

            manifest_path = root / dc.EXPECTED_MANIFEST_PATH
            tampered = json.loads(manifest_path.read_text(encoding="utf-8"))
            copied = dict(tampered["publications"][role])
            copied["role"] = "square"
            copied["artifact"] = {
                "path": tampered["artifacts"]["square"]["path"],
                "bytes": tampered["artifacts"]["square"]["bytes"],
                "sha256": tampered["artifacts"]["square"]["sha256"],
            }
            tampered["publications"]["square"] = copied
            write_json(manifest_path, tampered)
            _checked, problems = dc.validate_manifest(
                root=root, probe=probe, render_probe=render_probe,
                mastering_audio_probe=fake_audio_lineage,
            )
            joined = "; ".join(problems)
            self.assertIn("collides across", joined)
            self.assertNotIn("Traceback", joined)

    def test_real_ffprobe_fixture_has_named_media_facts(self):
        ffmpeg = shutil.which("ffmpeg")
        ffprobe = shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            self.skipTest("local ffmpeg fixture tools unavailable")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "tiny.mp4"
            result = subprocess.run(
                [
                    ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=navy:s=64x64:d=0.5:r=30",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", "-shortest",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(target),
                    "-loglevel", "error",
                ], capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            with mock.patch.dict(
                os.environ,
                {"PATH": str(Path(ffprobe).parent) + os.pathsep + os.environ.get("PATH", "")},
            ):
                facts = dc.probe_media(target)
            self.assertEqual((facts["width"], facts["height"]), (64, 64))
            self.assertEqual(facts["streams"], {"video": 1, "audio": 1})
            self.assertGreater(facts["duration_seconds"], 0)
            self.assertAlmostEqual(facts["fps"], 30.0)
            self.assertIn(facts["frame_count"], (15, 16))


class EvidenceAndPreviewContractTests(unittest.TestCase):
    def prepared(self, parent: Path):
        root = make_identity_repo(parent)
        copy_delivery_config(root)
        stamp = init_identity(root)
        render_probe = make_render(root, stamp)
        facts = make_artifacts(root, stamp)
        probe = lambda path: dict(facts[str(Path(path).resolve())])
        make_mastering(root, stamp, render_probe)
        manifest = dc.build_manifest(root=root, probe=probe, render_probe=render_probe,
                                     mastering_audio_probe=fake_audio_lineage)
        write_json(
            root / "out" / "dispatch" / "vo_lines.json",
            {"lines": [{"idx": 0, "start": 0.0, "end": 90.0, "text": "fixture"}]},
        )
        write_json(
            root / "out" / "dispatch" / "audio" / "words.json",
            {"words": [{"word": "fixture", "start": 0.0, "end": 0.5}]},
        )
        write_json(root / "out" / "dispatch" / "claims.json", {"claims": []})
        write_json(root / "out" / "dispatch" / "sources.json", {"sources": []})
        write_json(root / "out" / "dispatch" / "vo_script.json", {"lines": []})
        (root / "out" / "dispatch" / "audio" / "vo.wav").write_bytes(b"fixture-vo")
        return root, stamp, manifest, probe, render_probe

    def test_evidence_manifest_binds_exact_vertical_delivery_generator_and_every_file(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, manifest, _probe, _render_probe = self.prepared(Path(td))
            scripts = root / "scripts"
            scripts.mkdir(parents=True, exist_ok=True)
            for name in ("build_evidence.py", "audio_report.py", "audio_evidence.py"):
                shutil.copyfile(REPO / "scripts" / name, scripts / name)
            evidence = root / "out" / "evidence"
            evidence.mkdir(parents=True)
            (evidence / "contact.jpg").write_bytes(b"jpeg-evidence")
            write_json(evidence / "motion.json", {"note": "measured", "strips": {}})
            (evidence / "audio_card.png").write_bytes(b"png-evidence")
            write_json(evidence / "audio_report.json", {
                "measured_on": "square.mp4", "also_covers_master": True,
                "master_measured": {}, "master_identity": "bound", "tool": "fixture",
                "delivered_i": -14.0, "delivered_tp": -2.0, "delivered_lra": 7.0,
                "targets": {}, "pass": {}, "vo_gaps_ge_0_35s": 1,
                "vo_gaps_ge_0_50s": 1, "vo_silence_in_gaps_s": 1.0,
                "last_word_ends_s": 90.0, "longest_gaps": [], "diagnosis": "fixture",
            })
            outputs = {
                "visual": ["out/evidence/contact.jpg", "out/evidence/motion.json"],
                "audio_report": ["out/evidence/audio_report.json"],
                "audio_card": ["out/evidence/audio_card.png"],
            }
            producers = {
                name: {"parameters": {"fixture": True}, "outputs": role_outputs}
                for name, role_outputs in outputs.items()
            }
            expected = sorted(path for values in outputs.values() for path in values)
            with self.assertRaisesRegex(
                evidence_contract.EvidenceContractError,
                "parameters are invalid",
            ):
                bad_producers = json.loads(json.dumps(producers))
                bad_producers["visual"]["parameters"] = {"contact_frames": float("nan")}
                evidence_contract.build_evidence_manifest(
                    root=root,
                    producers=bad_producers,
                    expected_artifacts=expected,
                    delivery_manifest=manifest,
                )
            built = evidence_contract.build_evidence_manifest(
                root=root,
                producers=producers,
                expected_artifacts=expected,
                delivery_manifest=manifest,
            )
            self.assertEqual(
                built["vertical_hosted"]["sha256"],
                manifest["artifacts"]["vertical_hosted"]["sha256"],
            )
            self.assertEqual(built["delivery_manifest_digest"], dc.contract_digest(manifest))
            self.assertEqual(
                set(built["artifacts"]),
                set(expected),
            )
            checked, problems = evidence_contract.validate_evidence_manifest(
                root=root, delivery_manifest=manifest,
            )
            self.assertIsNotNone(checked)
            self.assertEqual(problems, [])
            authored = root / "out" / "dispatch" / "vo_lines.json"
            authored_stat = authored.stat()
            authored_original = authored.read_bytes()
            authored_mutated = authored_original.replace(b"fixture", b"fixturE")
            self.assertEqual(len(authored_mutated), len(authored_original))
            authored.write_bytes(authored_mutated)
            os.utime(authored, ns=(authored_stat.st_atime_ns, authored_stat.st_mtime_ns))
            _checked, problems = evidence_contract.validate_evidence_manifest(
                root=root, delivery_manifest=manifest,
            )
            self.assertIn("producer source/input bytes", "; ".join(problems))
            authored.write_bytes(authored_original)
            os.utime(authored, ns=(authored_stat.st_atime_ns, authored_stat.st_mtime_ns))
            stale = evidence / "stale.png"
            stale.write_bytes(b"stale-allowed-extension")
            _checked, problems = evidence_contract.validate_evidence_manifest(
                root=root, delivery_manifest=manifest,
            )
            self.assertIn("artifact set", "; ".join(problems))
            stale.unlink()
            target = evidence / "contact.jpg"
            stat = target.stat()
            payload = bytearray(target.read_bytes())
            payload[0] ^= 1
            target.write_bytes(payload)
            os.utime(target, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            _checked, problems = evidence_contract.validate_evidence_manifest(
                root=root, delivery_manifest=manifest,
            )
            self.assertIn("hashes changed", "; ".join(problems))
            evidence_manifest_path = root.joinpath(*evidence_contract.MANIFEST_REL.split("/"))
            evidence_manifest_path.write_text(
                '{"schema_version":2,"schema_version":2}\n', encoding="utf-8",
            )
            checked, problems = evidence_contract.validate_evidence_manifest(
                root=root, delivery_manifest=manifest,
            )
            self.assertIsNone(checked)
            self.assertIn("duplicate", "; ".join(problems))
            evidence_manifest_path.write_text("[]\n", encoding="utf-8")
            checked, problems = evidence_contract.validate_evidence_manifest(
                root=root, delivery_manifest=manifest,
            )
            self.assertIsNone(checked)
            self.assertIn("object", "; ".join(problems))

    def test_evidence_recreate_removes_stale_files_and_manifest_rejects_new_leftovers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            stale = root / "out" / "evidence"
            stale.mkdir(parents=True)
            (stale / "old.png").write_bytes(b"stale")
            recreated = evidence_contract.recreate_evidence_directory(root=root)
            self.assertEqual(list(recreated.iterdir()), [])

    def test_preflight_blocks_until_exact_terminal_evidence_is_current(self):
        delivery = {"identity": {"run_id": "2026-08-29-test"}}
        evidence = {
            "identity": {"run_id": "2026-08-29-test"},
            "artifacts": {"out/evidence/contact.jpg": {}},
        }
        with mock.patch(
            "deliverable_contract.require_manifest", return_value=delivery,
        ), mock.patch(
            "evidence_contract.require_evidence_manifest", return_value=evidence,
        ):
            ok, message = preflight.evidence_is_current()
        self.assertTrue(ok, message)
        self.assertIn("producer-bound manifest", message)

        with mock.patch(
            "deliverable_contract.require_manifest", return_value=delivery,
        ), mock.patch(
            "evidence_contract.require_evidence_manifest",
            side_effect=evidence_contract.EvidenceContractError("terminal evidence is stale"),
        ):
            ok, message = preflight.evidence_is_current()
        self.assertFalse(ok)
        self.assertEqual(message, "terminal evidence is stale")

    def test_terminal_preview_requires_current_verdict_and_hash_binds_html(self):
        with tempfile.TemporaryDirectory() as td:
            root, stamp, manifest, _probe, _render_probe = self.prepared(Path(td))
            preview = root.joinpath(*delivery_preview.PREVIEW_REL.split("/"))
            preview.parent.mkdir(parents=True, exist_ok=True)
            commit = "a" * 40
            vertical_url = f"https://example.test/{commit}/vertical.mp4"
            square_url = f"https://example.test/{commit}/square.mp4"
            manifest["publications"] = {
                "vertical_hosted": {"url": vertical_url, "media_commit_sha": commit},
                "square": {"url": square_url, "media_commit_sha": commit},
            }
            preview.write_text("<html>arbitrary text only</html>", encoding="utf-8")
            verdict = root / "out" / "dispatch" / "panel_verdict.json"
            write_json(verdict, {"run_id": stamp["run_id"], "median": 9.0})
            ship_state = {"manifest": manifest, "median": 9.0, "threshold": 7.0}
            verified = []
            verifier = lambda role, url: verified.append((role, url)) or {"url": url}
            with self.assertRaisesRegex(
                delivery_preview.DeliveryPreviewError, "exact vertical_hosted URL",
            ):
                delivery_preview.record_delivery_preview(
                    preview, ship_state=ship_state, root=root,
                    publication_verifier=verifier,
                )
            preview.write_text(
                f'<html><a href="{vertical_url}">vertical</a>'
                f'<a href="{square_url}">square</a><span>terminal</span></html>',
                encoding="utf-8",
            )
            receipt = delivery_preview.record_delivery_preview(
                preview, ship_state=ship_state, root=root,
                publication_verifier=verifier,
            )
            self.assertEqual(receipt["run_date"], stamp["date"])
            checked, problems = delivery_preview.validate_delivery_preview(
                root=root, ship_state=ship_state, publication_verifier=verifier,
            )
            self.assertIsNotNone(checked)
            self.assertEqual(problems, [])
            stat = preview.stat()
            changed = preview.read_text(encoding="utf-8").replace("terminal", "tampered")
            preview.write_text(changed, encoding="utf-8")
            os.utime(preview, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            _checked, problems = delivery_preview.validate_delivery_preview(
                root=root, ship_state=ship_state, publication_verifier=verifier,
            )
            self.assertIn("preview", "; ".join(problems))
            self.assertGreaterEqual(verified.count(("vertical_hosted", vertical_url)), 3)
            self.assertGreaterEqual(verified.count(("square", square_url)), 3)
            verdict.unlink()
            _checked, problems = delivery_preview.validate_delivery_preview(
                root=root, ship_state=ship_state,
            )
            self.assertIn("ship verdict is missing", "; ".join(problems))

    def test_no_exit_requires_strict_ship_and_terminal_preview(self):
        state = {"manifest": manifest_fixture(), "median": 9.0, "threshold": 7.0}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            out = root / "out" / "dispatch"
            out.mkdir(parents=True)
            with mock.patch.object(no_exit, "ROOT", root), \
                 mock.patch.object(no_exit, "OUT", out), \
                 mock.patch.object(no_exit, "require_ship_verdict", return_value=state), \
                 mock.patch.object(no_exit, "require_delivery_preview", return_value={"schema_version": 1}):
                delivered, lines = no_exit.video_state()
            self.assertTrue(delivered, lines)
            with mock.patch.object(no_exit, "ROOT", root), \
                 mock.patch.object(no_exit, "OUT", out), \
                 mock.patch.object(
                     no_exit, "require_ship_verdict",
                     side_effect=ship_gate.GateInputError("current-run verdict missing"),
                 ), \
                 mock.patch.object(
                     no_exit, "require_delivery_preview",
                     side_effect=delivery_preview.DeliveryPreviewError("terminal preview missing"),
                 ):
                delivered, lines = no_exit.video_state()
            self.assertFalse(delivered)
            self.assertIn("current-run verdict missing", "; ".join(lines))


class GateBlocked(Exception):
    def __init__(self, reasons):
        self.reasons = reasons
        super().__init__("; ".join(str(reason) for reason in reasons))


class VideoJudgeContractTests(unittest.TestCase):
    def fixture(self, root: Path):
        (root / "config").mkdir(parents=True)
        shutil.copyfile(REPO / "config" / "dispatch_rubric.yaml", root / "config" / "dispatch_rubric.yaml")
        rubric = video_judge_contract.rubric_contract(root=root)
        binding = {
            "run_id": "fixture", "run_date": "2026-08-29", "composition": "DispatchDaily",
            "render_receipt_sha256": "1" * 64, "render_binding_sha256": "2" * 64,
            "delivery_manifest_digest": "3" * 64, "evidence_manifest_sha256": "4" * 64,
            "evidence_delivery_manifest_digest": "5" * 64,
            "preflight_receipt_sha256": "6" * 64,
        }
        allowed = {
            "out/evidence/contact-sheet.jpg",
            "out/evidence/motion.json",
            "out/evidence/caption_cues.json",
            "out/evidence/audio_report.json",
            "out/evidence/story_claims_sources.json",
        }
        return rubric, binding, allowed

    def card(self, rubric, binding, allowed, judge_id, *, score=8.0):
        capability_artifacts = {
            "visual": "out/evidence/contact-sheet.jpg",
            "timeline": "out/evidence/motion.json",
            "motion": "out/evidence/motion.json",
            "captions": "out/evidence/caption_cues.json",
            "audio": "out/evidence/audio_report.json",
            "source_claims": "out/evidence/story_claims_sources.json",
            "story": "out/evidence/story_claims_sources.json",
        }
        axes = []
        for axis in rubric["axes"]:
            artifacts = sorted({
                capability_artifacts[capability]
                for capability in video_judge_contract.AXIS_EVIDENCE_CAPABILITIES[axis["name"]]
            })
            axes.append({
                "name": axis["name"], "weight": axis["weight"], "score": score,
                "evidence": [
                    {"artifact": artifact, "observation": f"observed {axis['name']} in {artifact}"}
                    for artifact in artifacts
                ],
            })
        return {
            "schema_version": 1, "judge_id": judge_id, "binding": binding,
            "rubric": rubric, "axes": axes,
            "weighted_total": video_judge_contract.computed_total(axes),
            "hard_blockers": [],
        }

    def test_three_unique_cards_recompute_math_and_reject_arbitrary_or_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rubric, binding, allowed = self.fixture(root)
            paths = []
            for index, score in enumerate((7.2, 8.1, 9.0), 1):
                path = root / f"judge-{index}.json"
                write_json(path, self.card(rubric, binding, allowed, f"judge-{index}", score=score))
                paths.append(path)
            facts = video_judge_contract.require_three_cards(
                paths, root=root, binding=binding, rubric=rubric, allowed_evidence=allowed,
            )
            self.assertEqual([fact["weighted_total"] for fact in facts], [7.2, 8.1, 9.0])

            write_json(root / "scalar.json", {"judge_id": "judge-x", "weighted_total": 10})
            with self.assertRaisesRegex(video_judge_contract.VideoJudgeContractError, "fields/schema"):
                video_judge_contract.validate_card(
                    root / "scalar.json", root=root, binding=binding,
                    rubric=rubric, allowed_evidence=allowed,
                )
            duplicate = self.card(rubric, binding, allowed, "judge-1")
            write_json(root / "duplicate.json", duplicate)
            with self.assertRaisesRegex(video_judge_contract.VideoJudgeContractError, "unique judge IDs"):
                video_judge_contract.require_three_cards(
                    [paths[0], paths[1], root / "duplicate.json"], root=root,
                    binding=binding, rubric=rubric, allowed_evidence=allowed,
                )

    def test_wrong_axes_weights_total_evidence_and_rubric_drift_fail(self):
        mutations = (
            (lambda card: card["axes"].pop(), "every rubric axis"),
            (lambda card: card["axes"][0].update(weight=0.99), "weight drifted"),
            (lambda card: card.update(weighted_total=9.999), "recomputed"),
            (lambda card: card["axes"][0]["evidence"][0].update(artifact="arbitrary.jpg"),
             "non-manifest"),
        )
        for mutate, expected in mutations:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                rubric, binding, allowed = self.fixture(root)
                card = self.card(rubric, binding, allowed, "judge-1")
                mutate(card)
                path = root / "card.json"
                write_json(path, card)
                with self.assertRaisesRegex(video_judge_contract.VideoJudgeContractError, expected):
                    video_judge_contract.validate_card(
                        path, root=root, binding=binding, rubric=rubric,
                        allowed_evidence=allowed,
                    )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rubric, binding, allowed = self.fixture(root)
            path = root / "card.json"
            write_json(path, self.card(rubric, binding, allowed, "judge-1"))
            drifted = json.loads(json.dumps(rubric))
            drifted["ship_threshold"] = 7.1
            with self.assertRaisesRegex(video_judge_contract.VideoJudgeContractError, "rubric"):
                video_judge_contract.validate_card(
                    path, root=root, binding=binding, rubric=drifted,
                    allowed_evidence=allowed,
                )

    def test_axis_evidence_capabilities_reject_still_only_sound_and_audio_only_visual(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            rubric, binding, allowed = self.fixture(root)
            card = self.card(rubric, binding, allowed, "judge-1")
            axes = {axis["name"]: axis for axis in card["axes"]}
            axes["Sound design & mix"]["evidence"] = [{
                "artifact": "out/evidence/contact-sheet.jpg", "observation": "still only",
            }]
            path = root / "still-sound.json"
            write_json(path, card)
            with self.assertRaisesRegex(video_judge_contract.VideoJudgeContractError, "audio"):
                video_judge_contract.validate_card(
                    path, root=root, binding=binding, rubric=rubric, allowed_evidence=allowed,
                )

            card = self.card(rubric, binding, allowed, "judge-1")
            axes = {axis["name"]: axis for axis in card["axes"]}
            axes["Illustration craft & detail"]["evidence"] = [{
                "artifact": "out/evidence/audio_report.json", "observation": "audio only",
            }]
            path = root / "audio-visual.json"
            write_json(path, card)
            with self.assertRaisesRegex(video_judge_contract.VideoJudgeContractError, "visual"):
                video_judge_contract.validate_card(
                    path, root=root, binding=binding, rubric=rubric, allowed_evidence=allowed,
                )

            valid = self.card(rubric, binding, allowed, "judge-1")
            path = root / "valid-mixed.json"
            write_json(path, valid)
            checked = video_judge_contract.validate_card(
                path, root=root, binding=binding, rubric=rubric, allowed_evidence=allowed,
            )
            self.assertEqual(checked["judge_id"], "judge-1")

    def test_panel_ledger_recomputes_median_and_hard_blockers(self):
        cards = [
            {"judge_id": f"judge-{index}", "weighted_total": total, "hard_blockers": []}
            for index, total in enumerate((7.2, 8.1, 9.0), 1)
        ]
        with mock.patch.object(panel_ledger, "round_cards", return_value=cards), \
             mock.patch.object(panel_ledger, "rubric_contract", return_value={"ship_threshold": 7.0}):
            result = panel_ledger.round_result(1)
        self.assertEqual(result["median"], 8.1)
        self.assertTrue(result["pass"])
        cards[1]["hard_blockers"] = [{"what": "wrong number"}]
        with mock.patch.object(panel_ledger, "round_cards", return_value=cards), \
             mock.patch.object(panel_ledger, "rubric_contract", return_value={"ship_threshold": 7.0}):
            result = panel_ledger.round_result(1)
        self.assertFalse(result["pass"])


class ObjectivePreflightContractTests(unittest.TestCase):
    def test_quality_gate_accepts_only_canonical_manifest_evidence_mastering_and_sfx(self):
        gate = load_quality_gate_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            evidence_path = root / "out" / "evidence" / "evidence_manifest.json"
            write_json(evidence_path, {"fixture": True})
            audio = {"path": sfx_contract.AUDIO_REL, "bytes": 12, "sha256": "a" * 64}
            mastering = {
                "path": mastering_contract.RECEIPT_REL, "bytes": 100, "sha256": "b" * 64,
                "identity": {"run_id": "fixture"}, "audio_master": audio,
                "sfx": {"path": sfx_contract.SIDECAR_REL, "sha256": "c" * 64, "audio": audio},
                "artifacts": {},
            }
            delivery = {
                "schema_version": dc.MANIFEST_SCHEMA_VERSION,
                "identity": {"run_id": "fixture"}, "episode": {}, "render": {},
                "mastering": mastering,
                "artifacts": {role: {} for role in dc.EXPECTED_ROLES}, "publications": {},
            }
            evidence = {
                "schema_version": evidence_contract.SCHEMA_VERSION,
                "identity": {"run_id": "fixture", "run_date": "2026-08-29", "composition": "DispatchDaily"},
                "artifacts": {"out/evidence/contact.jpg": {"bytes": 1, "sha256": "d" * 64}},
            }
            sfx = {"path": sfx_contract.SIDECAR_REL, "sha256": "c" * 64, "audio": audio}
            audio_report = {
                "path": "out/evidence/audio_report.json", "bytes": 100,
                "sha256": "e" * 64, "delivered_i": -14.0,
                "delivered_tp": -1.5, "delivered_lra": 7.0,
                "pass": {"loudness": True, "true_peak": True, "lra": True},
            }
            report = gate.evaluate(
                root=root,
                manifest_loader=lambda **_kwargs: delivery,
                evidence_loader=lambda **_kwargs: evidence,
                mastering_loader=lambda **_kwargs: mastering,
                sfx_loader=lambda **_kwargs: (sfx, []),
                audio_report_loader=lambda **_kwargs: audio_report,
            )
            self.assertEqual(report["status"], "pass")
            self.assertEqual(
                [item["id"] for item in report["checks"]],
                ["delivery_manifest_v4", "mastering_audio_lineage_v3",
                 "evidence_manifest_v3", "sole_sfx_ledger_v3",
                 "delivered_audio_report_v1"],
            )
            with self.assertRaisesRegex(gate.QualityGateError, "does not match"):
                gate.evaluate(
                    root=root,
                    manifest_loader=lambda **_kwargs: delivery,
                    evidence_loader=lambda **_kwargs: evidence,
                    mastering_loader=lambda **_kwargs: mastering,
                    sfx_loader=lambda **_kwargs: ({**sfx, "audio": {"sha256": "e" * 64}}, []),
                    audio_report_loader=lambda **_kwargs: audio_report,
                )

    def test_quality_gate_requires_hash_bound_truthful_delivered_audio_measurements(self):
        gate = load_quality_gate_module()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "out" / "evidence" / "audio_report.json"
            value = {
                "measured_on": "dispatch_square.mp4",
                "also_covers_master": True,
                "master_measured": {"i": -14.1, "tp": -1.6, "lra": 7.1},
                "delivered_i": -14.0,
                "delivered_tp": -1.5,
                "delivered_lra": 7.0,
                "pass": {"loudness": True, "true_peak": True, "lra": True},
            }

            def declare(payload):
                write_json(path, payload)
                return {"artifacts": {gate.AUDIO_REPORT_REL: {
                    "bytes": path.stat().st_size, "sha256": dc.sha256_file(path),
                }}}

            evidence = declare(value)
            facts = gate.audio_report_facts(root=root, evidence=evidence)
            self.assertEqual(facts["delivered_i"], -14.0)
            self.assertEqual(facts["master_measured"]["lra"], 7.1)

            failed = copy.deepcopy(value)
            failed["pass"]["true_peak"] = False
            with self.assertRaisesRegex(gate.QualityGateError, "failed loudness"):
                gate.audio_report_facts(root=root, evidence=declare(failed))
            lying_lra = copy.deepcopy(value)
            lying_lra["delivered_lra"] = 20.0
            with self.assertRaisesRegex(gate.QualityGateError, "outside 6..9"):
                gate.audio_report_facts(root=root, evidence=declare(lying_lra))
            wrong_master = copy.deepcopy(value)
            wrong_master["master_measured"]["i"] = -10.0
            with self.assertRaisesRegex(gate.QualityGateError, "do not agree"):
                gate.audio_report_facts(root=root, evidence=declare(wrong_master))
            clipped_master = copy.deepcopy(value)
            clipped_master["master_measured"]["tp"] = -0.2
            with self.assertRaisesRegex(gate.QualityGateError, "hosted-master"):
                gate.audio_report_facts(root=root, evidence=declare(clipped_master))

            evidence = declare(value)
            original_stat = path.stat()
            mutated = path.read_bytes().replace(b"-14.0", b"-13.9", 1)
            self.assertEqual(len(mutated), original_stat.st_size)
            path.write_bytes(mutated)
            os.utime(path, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
            with self.assertRaisesRegex(gate.QualityGateError, "bytes do not match"):
                gate.audio_report_facts(root=root, evidence=evidence)

            path.write_text('{"pass":{},"pass":{}}\n', encoding="utf-8")
            duplicate_evidence = {"artifacts": {gate.AUDIO_REPORT_REL: {
                "bytes": path.stat().st_size, "sha256": dc.sha256_file(path),
            }}}
            with self.assertRaisesRegex(gate.QualityGateError, "duplicate"):
                gate.audio_report_facts(root=root, evidence=duplicate_evidence)

    def test_preflight_receipt_is_atomic_exact_and_hash_drift_invalidates_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            authored = {
                relative: {
                    "path": relative, "bytes": index + 1,
                    "sha256": f"{index + 1:064x}",
                }
                for index, relative in enumerate(sorted(preflight.REQUIRED_AUTHORED_INPUTS))
            }
            for index, relative in enumerate((
                "video-engine/tsconfig.json",
                "video-engine/package.json",
                "video-engine/package-lock.json",
                "video-engine/remotion.config.ts",
                ".claude/agents/scorer.md",
                ".claude/agents/dispatch-fixer.md",
                "prompts/dispatch_routine.md",
                "config/panel_protocol.md",
            ), len(authored) + 1):
                authored[relative] = {
                    "path": relative, "bytes": index, "sha256": f"{index:064x}",
                }
            tools = {
                "scripts/build_scenes.py": {
                    "path": "scripts/build_scenes.py", "bytes": 7, "sha256": "c" * 64,
                },
                "scripts/preflight.py": {
                    "path": "scripts/preflight.py", "bytes": 9, "sha256": "d" * 64,
                },
            }
            check_ids = [spec["id"] for spec in preflight.required_check_specs()]
            lineage = {
                "scope_id": preflight.PREFLIGHT_SCOPE_ID,
                "inputs": sorted(authored),
                "tools": sorted(tools),
                "external_tools": ["ffmpeg", "remotion_cli", "typescript_compiler"],
                "consumers": {
                    "typescript_engine": ["video-engine/tsconfig.json"],
                    "terminal_judging": [".claude/agents/scorer.md"],
                },
                "checks": {
                    check_id: {"scope_id": preflight.PREFLIGHT_SCOPE_ID}
                    for check_id in check_ids
                },
            }
            state = (
                {"run_id": "fixture", "delivery_manifest_digest": "a" * 64},
                authored,
                tools,
                {
                    "ffmpeg": {"path": "fixture", "version": "fixture", "bytes": 1,
                               "sha256": "1" * 64},
                    "typescript_compiler": {"path": "fixture-tsc", "version": "5.9.3",
                                             "bytes": 2, "sha256": "2" * 64},
                    "remotion_cli": {"path": "fixture-remotion", "version": "4.0.399",
                                     "bytes": 3, "sha256": "3" * 64},
                },
                lineage,
            )
            results = [
                {
                    "id": spec["id"], "label": spec["label"], "exit_code": 0,
                    "stdout_sha256": "d" * 64, "stderr_sha256": "e" * 64,
                }
                for spec in preflight.required_check_specs()
            ]
            with mock.patch.object(preflight, "_current_contract_state", return_value=state):
                receipt = preflight.record_preflight_receipt(results, root=root)
                self.assertEqual(receipt["binding"], state[0])
                self.assertTrue(all(item["result"] == "pass" for item in receipt["required_checks"]))
                checked, problems = preflight.validate_preflight_receipt(root=root)
                self.assertIsNotNone(checked)
                self.assertEqual(problems, [])
            self.assertTrue(preflight.REQUIRED_AUTHORED_INPUTS.issubset(authored))
            self.assertIn("scripts/build_scenes.py", tools)
            self.assertEqual(set(lineage["checks"]), set(check_ids))
            # Every required check is declared against one exhaustive closed scope.
            self.assertTrue(all(
                value == {"scope_id": preflight.PREFLIGHT_SCOPE_ID}
                for value in lineage["checks"].values()
            ))

            # Mutations across every authored check family invalidate the receipt even
            # when the check output itself and all other facts are unchanged.
            families = (
                "out/dispatch/claims.json",
                "out/dispatch/vo_script.txt",
                "out/dispatch/vo_script.json",
                "out/dispatch/music_credit.json",
                "out/dispatch/sources.json",
                "out/dispatch/audio/vo.wav",
                "out/dispatch/audio/words.json",
                "out/dispatch/music_bed.wav",
                "video-engine/tsconfig.json",
                "video-engine/package.json",
                "video-engine/package-lock.json",
                "video-engine/remotion.config.ts",
                ".claude/agents/scorer.md",
                ".claude/agents/dispatch-fixer.md",
                "prompts/dispatch_routine.md",
                "config/panel_protocol.md",
            )
            for relative in families:
                drifted_state = list(copy.deepcopy(state))
                drifted_state[1][relative]["sha256"] = "f" * 64
                with self.subTest(relative=relative), mock.patch.object(
                    preflight, "_current_contract_state", return_value=tuple(drifted_state),
                ):
                    _checked, problems = preflight.validate_preflight_receipt(root=root)
                self.assertIn("input bytes or hashes changed", "; ".join(problems))
            drifted_tools = list(copy.deepcopy(state))
            drifted_tools[2]["scripts/build_scenes.py"]["sha256"] = "e" * 64
            with mock.patch.object(
                preflight, "_current_contract_state", return_value=tuple(drifted_tools),
            ):
                _checked, problems = preflight.validate_preflight_receipt(root=root)
            self.assertIn("tool source bytes or hashes changed", "; ".join(problems))
            for runtime_name in ("typescript_compiler", "remotion_cli"):
                drifted_runtime = list(copy.deepcopy(state))
                drifted_runtime[3][runtime_name]["sha256"] = "f" * 64
                with self.subTest(runtime=runtime_name), mock.patch.object(
                    preflight, "_current_contract_state", return_value=tuple(drifted_runtime),
                ):
                    _checked, problems = preflight.validate_preflight_receipt(root=root)
                self.assertIn("external tool paths/versions changed", "; ".join(problems))
            drifted = ({**state[0], "delivery_manifest_digest": "f" * 64}, *state[1:])
            with mock.patch.object(preflight, "_current_contract_state", return_value=drifted):
                _checked, problems = preflight.validate_preflight_receipt(root=root)
            self.assertIn("binding changed", "; ".join(problems))

            (root / preflight.RECEIPT_REL).unlink()
            failed = json.loads(json.dumps(results))
            failed[0]["exit_code"] = 1
            with mock.patch.object(preflight, "_current_contract_state", return_value=state), \
                 self.assertRaises(preflight.PreflightContractError):
                preflight.record_preflight_receipt(failed, root=root)
            self.assertFalse((root / preflight.RECEIPT_REL).exists())


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
            "sha256": f"{index:064x}",
            "video_codecs": ["h264"] if duration else (["png"] if role == "poster_square" else ["mjpeg"]),
            "audio_codecs": ["aac"] if audio else [],
            "fps": 30.0 if duration else 25.0,
            "frame_count": 3000 if duration else 1,
        }
    return {
        "schema_version": dc.MANIFEST_SCHEMA_VERSION,
        "identity": {
            "run_id": "fixture", "date": "2026-08-29",
            "composition": "DispatchDaily", "repository": "TestOwner/test-repo",
        },
        "episode": {"total_frames": 3000, "fps": 30, "duration_seconds": 100.0},
        "render": {"artifact": {"sha256": "9" * 64}},
        "mastering": {"path": mastering_contract.RECEIPT_REL, "sha256": "8" * 64},
        "artifacts": artifacts,
        "publications": {},
    }


class ShipGateTests(unittest.TestCase):
    def make_sfx_repo(self, parent: Path):
        root = make_identity_repo(parent)
        stamp = init_identity(root)
        audio = root / "out" / "dispatch" / "audio" / "master.wav"
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(b"current-audio-master")
        os.utime(audio, (stamp["started_at"] + 1, stamp["started_at"] + 1))
        path = root / "out" / "dispatch" / "sfx_events.json"
        events = make_sfx_events(root, spacing=1.0)
        payload = sfx_contract.write_sidecar(audio, events, root=root)
        return root, stamp, path, events, payload

    def test_valid_sfx_and_malformed_missing_wrong_type_stale_and_out_of_range(self):
        with tempfile.TemporaryDirectory() as td:
            root, stamp, path, events, payload = self.make_sfx_repo(Path(td))
            facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertEqual(problems, [])
            self.assertEqual(facts["count"], 6)
            path.write_text("{bad", encoding="utf-8")
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertTrue(problems)
            self.assertNotIn("Traceback", ";".join(problems))
            wrong = dict(payload)
            wrong["events"] = "wrong"
            write_json(path, wrong)
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertIn("must be a list", ";".join(problems))
            bad = list(events)
            bad[0] = {"t": float("nan"), "kind": "Hit"}
            malformed = dict(payload)
            malformed["events"] = bad
            write_json(path, malformed)
            os.utime(path, (stamp["started_at"], stamp["started_at"]))
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            joined = ";".join(problems)
            self.assertIn("non-finite", joined)
            self.assertIn("does not postdate", joined)
            self.assertNotIn("Traceback", joined)
            bad = list(events)
            bad[0] = {"t": 1.0, "kind": "Hit"}
            bad[1] = {"t": 101, "kind": "ok"}
            malformed = dict(payload)
            malformed["events"] = bad
            write_json(path, malformed)
            os.utime(path, (stamp["started_at"], stamp["started_at"]))
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            joined = ";".join(problems)
            self.assertIn("lowercase ASCII", joined)
            self.assertIn("within the delivered duration", joined)
            self.assertIn("does not postdate", joined)
            malformed = json.loads(json.dumps(payload))
            malformed["events"][0]["unexpected"] = True
            malformed["events"][1]["pan"] = 2.0
            write_json(path, malformed)
            future_ns = time.time_ns() + 2_000_000_000
            os.utime(path, ns=(future_ns, future_ns))
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            joined = ";".join(problems)
            self.assertIn("fields are not canonical", joined)
            self.assertIn("pan must be finite in -1..1", joined)
            self.assertNotIn("Traceback", joined)
            malformed = json.loads(json.dumps(payload))
            malformed["events"][0]["t"] = 10 ** 400
            write_json(path, malformed)
            os.utime(path, ns=(future_ns, future_ns))
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertIn("must be finite", ";".join(problems))
            self.assertNotIn("Traceback", ";".join(problems))
            path.unlink()
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertIn("no out/dispatch/sfx_events.json", problems)

    def test_same_size_mtime_preserving_audio_mutation_invalidates_sfx_binding(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, path, _events, _payload = self.make_sfx_repo(Path(td))
            audio = root / "out" / "dispatch" / "audio" / "master.wav"
            stat = audio.stat()
            payload = bytearray(audio.read_bytes())
            payload[0] ^= 1
            audio.write_bytes(payload)
            os.utime(audio, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            _facts, problems = ship_gate.sfx_facts(path, duration_seconds=100.0, root=root)
            self.assertIn("audio facts do not match", ";".join(problems))

    def test_take_mutation_and_legacy_split_ledger_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root, _stamp, path, events, _payload = self.make_sfx_repo(Path(td))
            take = root.joinpath(*events[0]["take"].split("/"))
            stat = take.stat()
            changed = bytearray(take.read_bytes())
            changed[0] ^= 1
            take.write_bytes(changed)
            os.utime(take, ns=(stat.st_atime_ns, stat.st_mtime_ns))
            _facts, problems = ship_gate.sfx_facts(path, root=root)
            self.assertIn("resolved take", "; ".join(problems))
            legacy = root.joinpath(*sfx_contract.LEGACY_SIDECAR_REL.split("/"))
            legacy.write_text('{"events":[]}\n', encoding="utf-8")
            _facts, problems = ship_gate.sfx_facts(path, root=root)
            self.assertIn("legacy", "; ".join(problems))

    def run_check(
        self, directory: Path, *, evidence_now=None, sfx_now=None,
        verdict_mutator=None, raw_verdict=None, release_error=None, write_verdict=True,
        preflight_error=None,
    ):
        manifest = manifest_fixture()
        artifacts = {role: entry["sha256"] for role, entry in manifest["artifacts"].items()}
        evidence_binding = {
            "path": "out/evidence/evidence_manifest.json",
            "sha256": "d" * 64,
            "delivery_manifest_digest": dc.contract_digest(manifest),
            "vertical_hosted": {
                "path": manifest["artifacts"]["vertical_hosted"]["path"],
                "bytes": manifest["artifacts"]["vertical_hosted"]["bytes"],
                "sha256": manifest["artifacts"]["vertical_hosted"]["sha256"],
            },
            "producers": {"visual": {"sha256": "f" * 64}},
            "expected_artifacts": ["out/evidence/contact.jpg"],
            "artifacts": {
                "out/evidence/contact.jpg": {"bytes": 10, "sha256": "a" * 64},
            },
        }
        evidence = {
            relative: entry["sha256"]
            for relative, entry in evidence_binding["artifacts"].items()
        }
        sfx = {"path": "out/dispatch/sfx_events.json", "sha256": "b" * 64, "count": 6,
               "run_id": "fixture", "run_date": "2026-08-29",
               "composition": "DispatchDaily", "episode": manifest["episode"],
               "kinds": ["hit"], "first_seconds": 1.0, "last_seconds": 6.0,
               "audio": {"path": "out/dispatch/audio/master.wav", "bytes": 12,
                         "sha256": "e" * 64}}
        media_facts = {
            role: {"sha256": entry["sha256"], "bytes": entry["bytes"],
                   "duration_seconds": entry["duration_seconds"], "streams": entry["streams"],
                   "fps": entry["fps"], "frame_count": entry["frame_count"]}
            for role, entry in manifest["artifacts"].items()
        }
        preflight_facts = {
            "path": "out/dispatch/preflight_receipt.json", "bytes": 100,
            "sha256": "9" * 64,
            "binding": {"run_id": "fixture", "delivery_manifest_digest": dc.contract_digest(manifest)},
            "required_checks": [], "tool_sources": {},
        }
        judge_cards = [
            {
                "path": f"out/dispatch/judge_cards/judge-{index}.json",
                "bytes": 100 + index,
                "sha256": f"{index + 5:x}" * 64,
                "judge_id": f"judge-{index}",
                "weighted_total": total,
                "hard_blockers": [],
            }
            for index, total in enumerate((8.8, 9.0, 9.2), 1)
        ]
        verdict = {
            "recorded_at": "2026-08-29T00:00:00Z",
            "run_id": "fixture", "run_date": "2026-08-29",
            "composition": "DispatchDaily",
            "median": 9.0, "judge_totals": [8.8, 9.0, 9.2],
            "judge_cards": judge_cards,
            "rubric": {"path": "config/dispatch_rubric.yaml", "bytes": 10,
                       "sha256": "7" * 64, "ship_threshold": 7.0},
            "owner_release": None, "effective_threshold": 7.0, "notes": "",
            "artifacts": artifacts,
            "evidence": evidence, "manifest_digest": dc.contract_digest(manifest),
            "evidence_manifest": evidence_binding,
            "media_facts": media_facts, "sfx": sfx,
            "blankness": {
                "algorithm": "local-structure-v2",
                "vertical_sha256": manifest["artifacts"]["vertical_hosted"]["sha256"],
                "duration_seconds": 100.0, "sample_count": 28,
                "threshold": 0.995, "maximum_low_information_fraction": 0.4,
            },
            "preflight": preflight_facts,
        }
        if verdict_mutator:
            verdict_mutator(verdict)
        render = directory / "out" / "dispatch"
        render.mkdir(parents=True)
        write_json(
            render / ".run_stamp.json",
            {"run_id": "fixture", "date": "2026-08-29", "composition": "DispatchDaily"},
        )
        verdict_path = render / "panel_verdict.json"
        if write_verdict:
            if raw_verdict is None:
                write_json(verdict_path, verdict)
            else:
                verdict_path.write_text(raw_verdict, encoding="utf-8")
        current_binding = evidence_now if evidence_now is not None else evidence_binding
        current_sfx = sfx_now if sfx_now is not None else sfx
        with contextlib.ExitStack() as stack:
            for name, value in (
                ("ROOT", directory), ("VERDICT", verdict_path), ("RENDER", render),
                ("ATTEMPTS", directory / "attempts.json"),
            ):
                stack.enter_context(mock.patch.object(ship_gate, name, value))
            stack.enter_context(mock.patch.object(ship_gate, "check_beats_delivered"))
            stack.enter_context(mock.patch.object(ship_gate, "check_identity", return_value=(True, "ok")))
            stack.enter_context(mock.patch.object(ship_gate, "require_manifest", return_value=manifest))
            if preflight_error is None:
                stack.enter_context(mock.patch.object(
                    ship_gate, "require_preflight_receipt", return_value=preflight_facts,
                ))
            else:
                stack.enter_context(mock.patch.object(
                    ship_gate, "require_preflight_receipt", side_effect=preflight_error,
                ))
            stack.enter_context(mock.patch.object(
                ship_gate, "load_stamp",
                return_value={"run_id": "fixture", "date": "2026-08-29", "composition": "DispatchDaily"},
            ))
            stack.enter_context(mock.patch.object(ship_gate, "rubric_facts", return_value=verdict["rubric"]))
            if release_error is None:
                stack.enter_context(mock.patch.object(ship_gate, "owner_release", return_value=None))
            else:
                stack.enter_context(mock.patch.object(ship_gate, "owner_release", side_effect=release_error))
            stack.enter_context(mock.patch.object(ship_gate, "evidence_binding", return_value=current_binding))
            stack.enter_context(mock.patch.object(ship_gate, "sfx_facts", return_value=(current_sfx, [])))
            stack.enter_context(mock.patch.object(ship_gate, "blankness_facts", return_value=verdict["blankness"]))
            stack.enter_context(mock.patch.object(ship_gate, "require_three_cards", return_value=judge_cards))
            stack.enter_context(mock.patch.object(
                ship_gate, "fail",
                side_effect=lambda reasons, median=None: (_ for _ in ()).throw(GateBlocked(reasons)),
            ))
            ship_gate.cmd_check(mock.Mock())
        return render

    def test_valid_sfx_reaches_evidence_comparison_and_passes(self):
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            render = self.run_check(Path(td))
            self.assertTrue((render / "SHIP_NOW").is_file())
            marker = load_path(render / "SHIP_NOW", label="SHIP_NOW marker")
            self.assertEqual(marker["schema_version"], 1)
            self.assertEqual(marker["run_id"], "fixture")

    def test_failed_or_missing_preflight_blocks_record_check_and_ship_marker(self):
        error = preflight.PreflightContractError("required quality gate failed")
        with mock.patch.object(ship_gate, "require_preflight_receipt", side_effect=error), \
             mock.patch.object(ship_gate, "check_render_is_current") as render_check, \
             mock.patch.object(
                 ship_gate, "fail",
                 side_effect=lambda reasons, median=None: (_ for _ in ()).throw(GateBlocked(reasons)),
             ), \
             self.assertRaisesRegex(GateBlocked, "objective preflight"):
            ship_gate.cmd_record(mock.Mock(cards=["j1.json", "j2.json", "j3.json"], notes=""))
        render_check.assert_not_called()

        with tempfile.TemporaryDirectory() as td, \
             self.assertRaisesRegex(GateBlocked, "objective preflight"):
            root = Path(td)
            self.run_check(root, preflight_error=error)
        self.assertFalse((root / "out" / "dispatch" / "SHIP_NOW").exists())

    def test_ship_marker_rejects_stale_verdict_and_new_init_removes_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = make_identity_repo(Path(td))
            init_identity(root)
            out = root / "out" / "dispatch"
            verdict = {"run_id": "2026-08-29-test", "median": 9.0}
            write_json(out / "panel_verdict.json", verdict)
            state = {"verdict": verdict, "manifest": manifest_fixture()}
            ship_marker.record_ship_marker(state, root=root)
            self.assertEqual(
                ship_marker.validate_ship_marker(root=root, ship_state=state)[1], [],
            )
            write_json(out / "panel_verdict.json", {"run_id": "2026-08-29-test", "median": 8.0})
            write_json(out / "preflight_receipt.json", {"schema_version": 1})
            _marker, problems = ship_marker.validate_ship_marker(root=root, ship_state=state)
            self.assertIn("verdict", "; ".join(problems))
            run_guard.init("2026-08-30-test", "DispatchDaily", root=root)
            self.assertFalse((out / "SHIP_NOW").exists())
            self.assertFalse((out / "panel_verdict.json").exists())
            self.assertFalse((out / "preflight_receipt.json").exists())

    def test_post_panel_sfx_and_evidence_mutations_fail_by_hash(self):
        cases = (
            ({
                "path": "out/evidence/evidence_manifest.json", "sha256": "c" * 64,
                "delivery_manifest_digest": dc.contract_digest(manifest_fixture()),
                "vertical_hosted": {
                    "path": "out/dispatch/vertical_hosted.bin", "bytes": 1000,
                    "sha256": "1".zfill(64),
                },
                "producers": {"visual": {"sha256": "f" * 64}},
                "expected_artifacts": ["out/evidence/contact.jpg"],
                "artifacts": {"out/evidence/contact.jpg": {"bytes": 10, "sha256": "c" * 64}},
             }, None, "review evidence hashes changed"),
            (None, {"path": "out/dispatch/sfx_events.json", "sha256": "d" * 64,
                    "run_id": "fixture", "run_date": "2026-08-29",
                    "composition": "DispatchDaily", "episode": manifest_fixture()["episode"],
                    "count": 6, "kinds": ["hit"], "first_seconds": 1.0,
                    "last_seconds": 6.0,
                    "audio": {"path": "out/dispatch/audio/master.wav", "bytes": 12,
                              "sha256": "e" * 64}},
             "sfx/audio evidence changed"),
        )
        for evidence, sfx, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as td:
                with self.assertRaisesRegex(GateBlocked, expected):
                    self.run_check(Path(td), evidence_now=evidence, sfx_now=sfx)

    def test_malformed_verdict_is_concise_gate_failure(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(GateBlocked) as caught:
                self.run_check(
                    Path(td), raw_verdict='{"median":9,"median":8}\n',
                )
            self.assertIn("duplicate", str(caught.exception))
            self.assertNotIn("Traceback", str(caught.exception))

    def test_wrong_type_evidence_is_concise_gate_failure(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(GateBlocked, "review evidence hashes changed"):
                self.run_check(Path(td), verdict_mutator=lambda verdict: verdict.update(evidence=[]))

    def test_missing_verdict_median_lie_and_stale_release_fail(self):
        cases = (
            ({"write_verdict": False}, "panel verdict is missing"),
            ({"verdict_mutator": lambda value: value.update(median=8.9)}, "internally computed median"),
            ({"release_error": ship_gate.GateInputError("active owner release belongs to a different run; stale releases hard-fail")},
             "stale releases hard-fail"),
        )
        for kwargs, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as td:
                with self.assertRaisesRegex(GateBlocked, expected):
                    self.run_check(Path(td), **kwargs)

    def test_record_computes_three_score_median_and_binds_rubric(self):
        manifest = manifest_fixture()
        artifacts = {role: entry["sha256"] for role, entry in manifest["artifacts"].items()}
        evidence_binding = {
            "path": "out/evidence/evidence_manifest.json", "sha256": "d" * 64,
            "delivery_manifest_digest": dc.contract_digest(manifest),
            "vertical_hosted": {}, "producers": {},
            "expected_artifacts": ["out/evidence/contact.jpg"],
            "artifacts": {"out/evidence/contact.jpg": {"bytes": 1, "sha256": "a" * 64}},
        }
        sfx = {"path": "out/dispatch/sfx_events.json", "sha256": "b" * 64, "count": 6}
        captured = {}
        rubric = {"path": "config/dispatch_rubric.yaml", "bytes": 10,
                  "sha256": "7" * 64, "ship_threshold": 7.0, "axes": []}
        judge_cards = [
            {"path": f"out/dispatch/judge_cards/judge-{index}.json", "bytes": 100,
             "sha256": f"{index + 1:x}" * 64, "judge_id": f"judge-{index}",
             "weighted_total": total, "hard_blockers": []}
            for index, total in enumerate((9.2, 8.0, 8.8), 1)
        ]
        with mock.patch.object(ship_gate, "check_render_is_current"), \
             mock.patch.object(ship_gate, "require_preflight_receipt", return_value={
                 "path": "out/dispatch/preflight_receipt.json", "bytes": 100,
                 "sha256": "9" * 64, "binding": {}, "required_checks": [], "tool_sources": {},
             }), \
             mock.patch.object(ship_gate, "check_not_blank", return_value={"vertical_sha256": "1".zfill(64)}), \
             mock.patch.object(ship_gate, "artifact_state", return_value=(artifacts, {"contact": "a" * 64}, manifest)), \
             mock.patch.object(ship_gate, "evidence_binding", return_value=evidence_binding), \
             mock.patch.object(ship_gate, "rubric_facts", return_value=rubric), \
             mock.patch.object(ship_gate, "load_stamp", return_value={"run_id": "fixture", "date": "2026-08-29", "composition": "DispatchDaily"}), \
             mock.patch.object(ship_gate, "owner_release", return_value=None), \
             mock.patch.object(ship_gate, "sfx_facts", return_value=(sfx, [])), \
             mock.patch.object(ship_gate, "require_three_cards", return_value=judge_cards), \
             mock.patch.object(ship_gate, "atomic_json", side_effect=lambda _path, value: captured.update(value)), \
             contextlib.redirect_stdout(io.StringIO()):
            ship_gate.cmd_record(mock.Mock(cards=["j1.json", "j2.json", "j3.json"], notes="bound"))
            with mock.patch.object(
                ship_gate, "fail", side_effect=lambda reasons, median=None: (_ for _ in ()).throw(GateBlocked(reasons))
            ), mock.patch.object(
                ship_gate, "require_three_cards",
                side_effect=video_judge_contract.VideoJudgeContractError("exactly three cards required"),
            ), self.assertRaisesRegex(GateBlocked, "exactly three"):
                ship_gate.cmd_record(mock.Mock(cards=["one.json"], notes="invalid"))
        self.assertEqual(captured["median"], 8.8)
        self.assertEqual(captured["rubric"], rubric)
        self.assertEqual(captured["judge_totals"], [9.2, 8.0, 8.8])
        self.assertEqual(captured["judge_cards"], judge_cards)

    def test_blankness_probe_and_decode_fail_closed_without_traceback(self):
        manifest = manifest_fixture()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            video = root.joinpath(*manifest["artifacts"]["vertical_hosted"]["path"].split("/"))
            video.parent.mkdir(parents=True)
            video.write_bytes(b"fixture")
            failed_probe = mock.Mock(returncode=1, stderr="named ffprobe failure", stdout="")
            with mock.patch.object(ship_gate, "ROOT", root), \
                 mock.patch.object(ship_gate, "require_manifest", return_value=manifest), \
                 mock.patch("subprocess.run", return_value=failed_probe):
                with self.assertRaises(ship_gate.GateInputError) as caught:
                    ship_gate.blankness_facts(n=1)
            self.assertIn("named ffprobe failure", str(caught.exception))
            self.assertNotIn("Traceback", str(caught.exception))

            probe_ok = mock.Mock(returncode=0, stderr="", stdout="100.0")
            decode_no_file = mock.Mock(returncode=0, stderr="", stdout="")
            with mock.patch.object(ship_gate, "ROOT", root), \
                 mock.patch.object(ship_gate, "require_manifest", return_value=manifest), \
                 mock.patch("subprocess.run", side_effect=[probe_ok, decode_no_file]):
                with self.assertRaises(ship_gate.GateInputError) as caught:
                    ship_gate.blankness_facts(n=1)
            self.assertIn("sample 0", str(caught.exception))
            self.assertNotIn("Traceback", str(caught.exception))


class StaticContractTests(unittest.TestCase):
    def test_replay_prompt_closed_judge_pack_and_canonical_quality_preflight(self):
        prompt = (REPO / "prompts" / "dispatch_routine.md").read_text(encoding="utf-8")
        normalized_prompt = " ".join(prompt.split())
        self.assertIn("PARAMETRIC COMPOSITION SCOPE", prompt)
        self.assertIn("fixed, reusable Remotion engine", normalized_prompt)
        self.assertIn("daily TSX or engine edits are forbidden", normalized_prompt)
        self.assertIn("2026-08-28 fixture is explicitly synthetic", normalized_prompt)
        self.assertIn("Exactly what B1 proves mechanically", prompt)
        for required_name in (
            "schema-v4 delivery bytes", "transactional mastering/audio lineage",
            "schema-v3 evidence provenance", "sole schema-v3 SFX ledger",
            "caption band", "caption spelling", "rendered captions",
            "plate overlap", "zoom clipping", "claims contract", "credits",
            "VO-claims checks",
        ):
            self.assertIn(required_name, normalized_prompt)
        self.assertNotIn("--judges", prompt)
        self.assertIn("ship_gate.py record --cards", prompt)
        self.assertNotIn("Each run you create ONE finished", prompt)
        self.assertNotIn("automation outputs a SHOWSTOPPER every run", prompt)

        scorer = (REPO / ".claude" / "agents" / "scorer.md").read_text(encoding="utf-8")
        flow = (REPO / ".claude" / "agents" / "flow-critic.md").read_text(encoding="utf-8")
        for name, text in (("scorer", scorer), ("flow", flow)):
            self.assertIn("out/evidence/evidence_manifest.json", text, name)
            self.assertIn("config/dispatch_rubric.yaml", text, name)
            self.assertIn("expected_artifacts", text, name)
            self.assertIn("Do not open", text, name)
            self.assertIn("NON-TERMINAL", text, name)
        quality = (
            REPO / ".claude" / "skills" / "alaska-dispatch" / "quality_gate.py"
        ).read_text(encoding="utf-8")
        self.assertIn("MANIFEST_SCHEMA_VERSION", quality)
        self.assertIn("EVIDENCE_SCHEMA_VERSION", quality)
        self.assertIn("SFX_SCHEMA_VERSION", quality)
        self.assertIn("mastering_binding", quality)
        self.assertNotIn("out/dispatch/review", quality)
        self.assertNotIn("frames_v3/", quality)
        preflight_text = (REPO / "scripts" / "preflight.py").read_text(encoding="utf-8")
        self.assertIn(".claude/skills/alaska-dispatch/quality_gate.py", preflight_text)
        self.assertIn("record_preflight_receipt", preflight_text)
        self.assertIn("require_preflight_receipt", preflight_text)

        correctness = (REPO / "docs" / "CORRECTNESS_FOUNDATION.md").read_text(encoding="utf-8")
        self.assertNotIn("--judges", correctness)
        self.assertLess(
            correctness.index("python3 scripts/preflight.py"),
            correctness.index("python3 scripts/video_judge_contract.py context"),
        )
        self.assertIn("three real scorer runs", correctness)
        self.assertIn("mastering_contract.py prepare", correctness)
        self.assertIn("There is no standalone observational record path", correctness)

        rubric_text = (REPO / "config" / "dispatch_rubric.yaml").read_text(encoding="utf-8")
        composition_line = next(
            line for line in rubric_text.splitlines() if "safe areas honored" in line
        )
        self.assertIn("derived 1:1 square", composition_line)
        self.assertNotIn("4:5", composition_line)
        self.assertIn("delivered_audio_report", rubric_text)
        self.assertIn("collective_preflight", rubric_text)

        mix = (REPO / "scripts" / "dispatch_mix.py").read_text(encoding="utf-8")
        self.assertNotIn("json.load", mix)
        self.assertNotIn("gap-lift SKIPPED", mix)

        mastering = (REPO / "scripts" / "mastering_contract.py").read_text(encoding="utf-8")
        self.assertIn('choices=("prepare", "finalize", "check")', mastering)
        self.assertNotIn("record_mastering", mastering)

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
        self.assertIn("render_contract.py prepare", package["scripts"]["render"])
        self.assertIn("render_contract.py record", package["scripts"]["render"])
        for name in ("render.sh", "render_parallel.sh", "probe_frames.sh"):
            text = (REPO / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("DispatchDaily", text)
            self.assertNotIn("${RUN_COMP:-Dispatch}", text)
        for name in ("render.sh", "render_parallel.sh"):
            text = (REPO / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("render_contract.py prepare", text)
            self.assertIn("render_contract.py record", text)
        parallel = (REPO / "scripts" / "render_parallel.sh").read_text(encoding="utf-8")
        self.assertIn("render_contract.py binding-digest", parallel)
        self.assertIn("render_contract.py chunk-record", parallel)
        self.assertIn("render_contract.py chunk-check", parallel)
        self.assertNotIn("cut -c1-16", parallel)
        self.assertIn("ship_marker.py check", parallel)
        self.assertNotIn("[ -f out/dispatch/SHIP_NOW", parallel)
        final_entrypoints = {
            "render.sh": (REPO / "scripts" / "render.sh").read_text(encoding="utf-8"),
            "render_parallel.sh": (REPO / "scripts" / "render_parallel.sh").read_text(encoding="utf-8"),
            "encode_deliverables.sh": (REPO / "scripts" / "encode_deliverables.sh").read_text(encoding="utf-8"),
            "package.json": package["scripts"]["render"],
        }
        for name, text in final_entrypoints.items():
            self.assertIn("render/video_mute.mp4", text, name)
            self.assertNotIn("render_mute.mp4", text, name)
            self.assertNotIn("out/dispatch/video_mute.mp4", text, name)

    def test_encoder_and_consumers_share_hosted_vertical_and_vertical_thumb(self):
        encoder = (REPO / "scripts" / "encode_deliverables.sh").read_text(encoding="utf-8")
        self.assertIn("dispatch_mastering_source.mp4", encoder)
        self.assertIn("dispatch_master_hosted.mp4", encoder)
        self.assertIn("poster_thumb_vertical.jpg", encoder)
        self.assertIn("scale=540:960", encoder)
        self.assertLess(
            encoder.index("mastering_contract.py prepare"),
            encoder.index('if [ -n "${1:-}" ]'),
        )
        for name in (
            "ship_gate.py", "build_evidence.py", "caption_render_check.py", "chroma_check.py",
            "credits_check.py", "edge_bleed_check.py", "motion_check.py", "vo_audio_check.py",
        ):
            text = (REPO / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn("dispatch_master_hosted.mp4", text, name)
        loop = (REPO / "scripts" / "dispatch_loop.sh").read_text(encoding="utf-8")
        self.assertIn("RETIRED", loop)
        self.assertIn("exit 2", loop)
        minerals = (REPO / "scripts" / "dispatch_mix_minerals.py").read_text(encoding="utf-8")
        self.assertIn("RETIRED", minerals)
        self.assertIn("return 2", minerals)
        self.assertNotIn("json.dump", minerals)
        self.assertNotIn("subprocess.run", minerals)

        prompt = (REPO / "prompts" / "dispatch_routine.md").read_text(encoding="utf-8")
        build_index = prompt.index("python3 scripts/build_evidence.py")
        judge_index = prompt.index("GATE B: editor")
        self.assertLess(build_index, judge_index)
        self.assertIn("NON-TERMINAL early-look", prompt)
        self.assertNotIn("--no-freshness-check", prompt)
        panel = (REPO / "config" / "panel_protocol.md").read_text(encoding="utf-8")
        self.assertIn("build_evidence.py", panel)
        self.assertIn("evidence_manifest.json", panel)
        self.assertIn("make_review_sheets.py", panel)

        for name in (
            "dispatch_mix.py", "audio_evidence.py", "audio_report.py",
            "build_evidence.py", "flow_check.py", "ship_gate.py",
        ):
            text = (REPO / "scripts" / name).read_text(encoding="utf-8")
            if name in {"flow_check.py", "ship_gate.py", "dispatch_mix.py"}:
                # These files name the legacy location only to remove or reject it.
                self.assertNotIn('open(os.path.join(AUD, "sfx_events.json"', text, name)
            self.assertNotIn('"audio/sfx_events.json"', text, name)


if __name__ == "__main__":
    unittest.main()
