#!/usr/bin/env python3
"""Focused offline contracts for the compact daily controller."""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import daily_scope_guard as scope
import dispatch_controller as controller
import dispatch_story_packet as packet_builder
from strict_json import StrictJSONError, load_path


SOURCE_ROOT = Path(__file__).resolve().parent.parent
RUN_DATE = "2026-08-28"


def claim(index: int) -> dict:
    return {
        "id": f"C{index:02d}",
        "claim": f"Verified Alaska claim number {index} with a bounded factual statement.",
        "source_url": f"https://example.org/source-{(index - 1) % 3}",
        "source_outlet": "Primary record",
        "source_is_primary": True,
        "fetched": True,
        "date_of_source": RUN_DATE,
        "confidence": 0.95,
        "notes": "Keep the source hedge and geographic scope.",
    }


class TempControllerRoot:
    def __init__(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "config" / "schemas").mkdir(parents=True)
        (self.root / "prompts").mkdir()
        shutil.copy2(SOURCE_ROOT / "config" / "daily_controller.json", self.root / "config" / "daily_controller.json")
        shutil.copy2(SOURCE_ROOT / "config" / "deliverables.json", self.root / "config" / "deliverables.json")
        shutil.copy2(
            SOURCE_ROOT / "config" / "schemas" / "dispatch_story_packet.schema.json",
            self.root / "config" / "schemas" / "dispatch_story_packet.schema.json",
        )
        shutil.copy2(
            SOURCE_ROOT / "config" / "episode_props.schema.json",
            self.root / "config" / "episode_props.schema.json",
        )
        shutil.copy2(SOURCE_ROOT / "prompts" / "dispatch_controller.md", self.root / "prompts" / "dispatch_controller.md")
        shutil.copy2(SOURCE_ROOT / "prompts" / "dispatch_context.md", self.root / "prompts" / "dispatch_context.md")

    def close(self) -> None:
        self.temp.cleanup()


def make_fact_pack(base: Path, count: int = 20) -> Path:
    run = base / "runs" / RUN_DATE
    run.mkdir(parents=True)
    (run / "selection.md").write_text(
        "# Selection\n\n## THE STORY\n\n**A verified Alaska system changed this week.** It matters now.\n\n"
        "## WHY THIS ONE, against the four criteria in order\n\nConcrete Alaska impact and strong visual potential.\n\n"
        "## THE ANGLE\n\nShow the mechanism and the honest limitation instead of saying AI helps.\n",
        encoding="utf-8",
    )
    (run / "scout_merge.md").write_text(
        "# Merge\n\n## CANDIDATE 1 (SELECTED)\n\nTwo independent paths found the same primary record.\n",
        encoding="utf-8",
    )
    (run / "claims.json").write_text(
        json.dumps({"run_date": RUN_DATE, "claims": [claim(i) for i in range(1, count + 1)]}),
        encoding="utf-8",
    )
    (run / "run_state.json").write_text(
        json.dumps({"run_date": RUN_DATE, "complete": True}), encoding="utf-8"
    )
    return run


def write_authored_outputs(root: Path, outputs: dict[str, str], *, short_voiceover: bool = False) -> dict:
    vo_path = root / outputs["voiceover_text"]
    vo_path.parent.mkdir(parents=True, exist_ok=True)
    vo_path.write_text(
        "far too short" if short_voiceover else " ".join(["Alaska"] * 270),
        encoding="utf-8",
    )
    props = json.loads(
        (SOURCE_ROOT / "video-engine" / "fixtures" / "dispatch-2026-08-28.json")
        .read_text(encoding="utf-8")
    )
    storyboard = {"shots": [{"id": scene["id"]} for scene in props["scenes"]]}
    (root / outputs["storyboard"]).write_text(json.dumps(storyboard), encoding="utf-8")
    (root / outputs["episode_props"]).write_text(json.dumps(props), encoding="utf-8")
    return props


class ConfigContractTests(unittest.TestCase):
    def test_authoritative_daily_shape_and_budgets(self) -> None:
        config = controller._config(SOURCE_ROOT)
        self.assertEqual(config["timezone"], "America/Anchorage")
        self.assertEqual(config["runtime_seconds"], {"minimum": 112, "maximum": 130})
        self.assertEqual(config["voiceover_words"], {"minimum": 262, "maximum": 282})
        formats = config["video_formats"]
        self.assertEqual(set(formats), {"master", "square", "mobile"})
        self.assertEqual(
            {(item["width"], item["height"]) for item in formats.values()},
            {(1080, 1920), (1080, 1080), (720, 1280)},
        )
        self.assertEqual(config["forbidden_video_formats"], [
            {"width": 1080, "height": 1350, "aspect_ratio": "4:5"}
        ])
        self.assertEqual(len(config["models"]["normal_plan"]), 8)
        self.assertEqual(len(config["models"]["worst_case_plan"]), 14)
        self.assertEqual(config["budgets"]["hard_model_call_cap"], 15)
        self.assertEqual(config["models"]["normal_plan"].count("showrunner"), 1)
        self.assertEqual(config["models"]["worst_case_plan"].count("showrunner"), 1)
        self.assertEqual(config["models"]["worst_case_plan"].count("judge"), 6)
        self.assertEqual(config["episode_props_contract"], {
            "schema_version": 2,
            "schema": "config/episode_props.schema.json",
            "composition": "DispatchDaily",
            "daily_typescript_edits": False,
        })

    def test_prompt_context_measurement(self) -> None:
        config = controller._config(SOURCE_ROOT)
        prompt = (SOURCE_ROOT / config["context"]["controller_prompt"]).read_bytes()
        context = (SOURCE_ROOT / config["context"]["standing_context"]).read_bytes()
        prompt_tokens = packet_builder.estimate_tokens_bytes(prompt)
        context_tokens = packet_builder.estimate_tokens_bytes(context)
        self.assertLessEqual(prompt_tokens, 6000)
        self.assertLessEqual(context_tokens, 6000)
        self.assertLessEqual(prompt_tokens + context_tokens, 12000)
        self.assertLess(prompt_tokens + context_tokens, 0.30 * 35227)

    def test_story_schema_is_strict_and_bounded(self) -> None:
        schema = load_path(
            SOURCE_ROOT / "config" / "schemas" / "dispatch_story_packet.schema.json",
            label="story schema",
        )
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["claims"]["maxItems"], 12)
        self.assertEqual(
            schema["properties"]["measurement"]["properties"]["maximum_estimated_tokens"]["const"],
            5000,
        )


class StoryPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = TempControllerRoot()
        self.carousel_temp = tempfile.TemporaryDirectory()
        self.carousel = Path(self.carousel_temp.name)

    def tearDown(self) -> None:
        self.carousel_temp.cleanup()
        self.layout.close()

    def test_fact_pack_is_zero_search_and_under_five_thousand(self) -> None:
        make_fact_pack(self.carousel, count=25)
        result = packet_builder.build_packet(
            root=self.layout.root, run_date=RUN_DATE, carousel_root=self.carousel
        )
        self.assertEqual(result["mode"], "carousel_fact_pack")
        self.assertEqual(result["research"]["broad_searches_used"], 0)
        self.assertEqual(len(result["claims"]), 12)
        self.assertLessEqual(result["measurement"]["estimated_tokens"], 5000)
        self.assertEqual(result["measurement"]["utf8_bytes"], len(packet_builder._render(result)))

    def test_bounded_fallback_accepts_ten_and_rejects_eleven_searches(self) -> None:
        fallback = self.layout.root / "fallback.json"
        candidate = {
            "id": "candidate-1",
            "selected": True,
            "headline": "A source-backed Alaska development",
            "angle": "Explain the concrete mechanism and limit.",
            "why_it_matters": "The change affects an Alaska decision.",
            "claims": [claim(i) for i in range(1, 5)],
        }
        value = {
            "schema_version": 1,
            "run_date": RUN_DATE,
            "broad_searches_used": 10,
            "candidates": [candidate],
        }
        fallback.write_text(json.dumps(value), encoding="utf-8")
        result = packet_builder.build_packet(
            root=self.layout.root, run_date=RUN_DATE, carousel_root=self.carousel,
            fallback_path=fallback,
        )
        self.assertEqual(result["mode"], "bounded_fallback")
        self.assertEqual(result["research"]["broad_searches_used"], 10)
        value["broad_searches_used"] = 11
        fallback.write_text(json.dumps(value), encoding="utf-8")
        with self.assertRaises(packet_builder.PacketError):
            packet_builder.build_packet(
                root=self.layout.root, run_date=RUN_DATE, carousel_root=self.carousel,
                fallback_path=fallback,
            )

    def test_duplicate_json_key_fails_closed(self) -> None:
        run = make_fact_pack(self.carousel, count=4)
        (run / "run_state.json").write_text(
            '{"run_date":"2026-08-28","run_date":"2026-08-28","complete":true}',
            encoding="utf-8",
        )
        with self.assertRaises(StrictJSONError):
            packet_builder.build_packet(
                root=self.layout.root, run_date=RUN_DATE, carousel_root=self.carousel
            )


class ControllerFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.layout = TempControllerRoot()
        self.root = self.layout.root
        self.carousel_temp = tempfile.TemporaryDirectory()
        self.carousel = Path(self.carousel_temp.name)
        make_fact_pack(self.carousel, count=8)
        packet = packet_builder.build_packet(
            root=self.root, run_date=RUN_DATE, carousel_root=self.carousel
        )
        packet_path = self.root / "out" / "dispatch" / "dispatch_story_packet.json"
        controller._atomic_json(packet_path, packet)
        controller.build_context(root=self.root)
        with mock.patch.object(controller, "create_snapshot"):
            controller.initialize(root=self.root, run_id="2026-08-28-canary", run_date=RUN_DATE)
        self.scope = mock.patch.object(controller, "check_scope", return_value=(True, "ok"))
        self.scope.start()

    def tearDown(self) -> None:
        self.scope.stop()
        self.carousel_temp.cleanup()
        self.layout.close()

    def evidence(self, name: str, count: int = 1) -> list[str]:
        paths: list[str] = []
        for index in range(count):
            rel = f"out/dispatch/{name}-{index}.json"
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"name": name, "index": index}), encoding="utf-8")
            paths.append(rel)
        return paths

    def advance_to(self, target: str) -> dict:
        state = controller.load_state(self.root)
        while state["phase"] != target:
            phase = state["phase"]
            if phase == "planning":
                evidence = self.evidence("scope")
            elif phase == "packet_context":
                evidence = [
                    "out/dispatch/dispatch_story_packet.json",
                    "out/dispatch/controller_context.json",
                ]
            elif phase == "vo_storyboard_episode_props":
                outputs = controller._config(self.root)["authoring_outputs"]
                write_authored_outputs(self.root, outputs)
                evidence = list(outputs.values())
            else:
                minimum = controller._config(self.root)["state_machine"]["evidence_minimums"][phase]
                evidence = self.evidence(phase, minimum)
            state = controller.advance(root=self.root, outcome="pass", evidence_paths=evidence)
        return state

    def test_one_repair_then_blocked_quality(self) -> None:
        state = self.advance_to("judges_round_1")
        state = controller.advance(
            root=self.root, outcome="fail", evidence_paths=self.evidence("round1", 3)
        )
        self.assertEqual(state["phase"], "repair")
        self.assertEqual(state["repair_rounds"], 1)
        state = controller.advance(
            root=self.root, outcome="pass", evidence_paths=self.evidence("repair")
        )
        self.assertEqual(state["phase"], "judges_round_2")
        state = controller.advance(
            root=self.root, outcome="fail", evidence_paths=self.evidence("round2", 3)
        )
        self.assertEqual(state["phase"], "BLOCKED_QUALITY")
        with self.assertRaises(controller.ControllerError):
            controller.advance(root=self.root, outcome="pass", evidence_paths=self.evidence("extra"))

    def test_reserve_complete_and_eval_export_schema(self) -> None:
        self.advance_to("angle")
        reservation = controller.reserve_call(
            root=self.root, role="showrunner", estimated_input_tokens=1200,
            maximum_output_tokens=500, estimated_cost_usd=0.5,
        )
        completed = controller.complete_call(
            root=self.root, reservation_id=reservation["reservation_id"],
            prompt_tokens=1000, input_tokens=200, output_tokens=300,
            cache_read_tokens=800, cache_write_tokens=100, cost_usd=0.45,
        )
        self.assertEqual(completed["budget_problems"], [])
        with self.assertRaises(controller.ControllerError):
            controller.reserve_call(
                root=self.root, role="showrunner", estimated_input_tokens=1000,
                maximum_output_tokens=400, estimated_cost_usd=0.4,
            )
        exported = controller.export_eval(
            root=self.root, scenario="worst_case", source_kind="measured",
            fetch_calls=4, other_tool_calls=2, editorial_revisions=0,
            preserved_outputs=["vertical_hosted", "square", "mobile"],
            gates=["claims=pass", "preflight=pass", "ship=pass"],
            output_rel="out/dispatch/eval.json",
        )
        controller.validate_eval_telemetry(exported)
        run = exported["runs"][0]
        self.assertEqual(run["fixture_id"], RUN_DATE)
        self.assertEqual(run["calls"][0]["model_tier"], "frontier")
        self.assertEqual(run["standing_context_tokens"], 1294)
        with self.assertRaises(controller.ControllerError):
            controller.export_eval(
                root=self.root, scenario="normal", source_kind="measured",
                fetch_calls=0, other_tool_calls=0, editorial_revisions=0,
                preserved_outputs=["vertical_hosted"], gates=["ship=pass"],
                output_rel="out/dispatch/invalid-eval.json",
            )

    def test_cache_accounting_fails_closed(self) -> None:
        self.advance_to("angle")
        reservation = controller.reserve_call(
            root=self.root, role="showrunner", estimated_input_tokens=1000,
            maximum_output_tokens=500, estimated_cost_usd=0.2,
        )
        with self.assertRaises(controller.ControllerError):
            controller.complete_call(
                root=self.root, reservation_id=reservation["reservation_id"],
                prompt_tokens=100, input_tokens=100, output_tokens=10,
                cache_read_tokens=201, cache_write_tokens=0, cost_usd=0.2,
            )

    def test_authoring_phase_blocks_short_voiceover(self) -> None:
        self.advance_to("vo_storyboard_episode_props")
        outputs = controller._config(self.root)["authoring_outputs"]
        write_authored_outputs(self.root, outputs, short_voiceover=True)
        with self.assertRaises(controller.ControllerError):
            controller.advance(
                root=self.root, outcome="pass", evidence_paths=list(outputs.values())
            )

    def test_authoring_phase_rejects_legacy_or_unsourced_historical_props(self) -> None:
        self.advance_to("vo_storyboard_episode_props")
        outputs = controller._config(self.root)["authoring_outputs"]
        props = write_authored_outputs(self.root, outputs)
        props.pop("schemaVersion")
        (self.root / outputs["episode_props"]).write_text(json.dumps(props), encoding="utf-8")
        with self.assertRaisesRegex(controller.ControllerError, "schema-v2 DispatchDaily"):
            controller.advance(
                root=self.root, outcome="pass", evidence_paths=list(outputs.values())
            )

        props = write_authored_outputs(self.root, outputs)
        props["episode"]["provenance"]["kind"] = "historical_reconstruction"
        (self.root / outputs["episode_props"]).write_text(json.dumps(props), encoding="utf-8")
        with self.assertRaisesRegex(controller.ControllerError, "historical scenes require"):
            controller.advance(
                root=self.root, outcome="pass", evidence_paths=list(outputs.values())
            )


class DailyScopeTests(unittest.TestCase):
    def test_source_paths_are_denied_and_runtime_output_is_allowed(self) -> None:
        config = controller._config(SOURCE_ROOT)
        forbidden = scope.forbidden_reasons(
            [
                "prompts/dispatch_controller.md",
                ".claude/agents/scorer.md",
                "scripts/dispatch_controller.py",
                "config/daily_controller.json",
                "video-engine/src/lib/motion.tsx",
                "video-engine/src/DispatchDaily.tsx",
            ],
            config,
        )
        self.assertEqual(len(forbidden), 6)
        self.assertEqual(scope.forbidden_reasons(["out/dispatch/episode_props.json"], config), [])
        self.assertTrue(config["daily_scope"]["weekly_maintenance_is_separate"])
        self.assertFalse(config["daily_scope"]["daily_controller_may_enter_maintenance"])


if __name__ == "__main__":
    unittest.main()
