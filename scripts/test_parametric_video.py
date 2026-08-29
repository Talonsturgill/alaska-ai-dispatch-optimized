#!/usr/bin/env python3
"""Fast structural regressions for the fixed DispatchDaily composition."""
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "video-engine" / "fixtures"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class ParametricVideoTests(unittest.TestCase):
    def test_schema_is_strict_for_every_declared_object(self):
        schema = load(ROOT / "config" / "episode_props.schema.json")
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

        def visit(value, path="root"):
            if isinstance(value, dict):
                if value.get("type") == "object" or "properties" in value:
                    self.assertIs(value.get("additionalProperties"), False, path)
                for key, child in value.items():
                    visit(child, f"{path}.{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    visit(child, f"{path}[{index}]")

        visit(schema)

    def test_frozen_fixtures_obey_timing_references_and_provenance(self):
        paths = sorted(FIXTURES.glob("dispatch-2026-08-*.json"))
        self.assertEqual([path.name for path in paths], [
            "dispatch-2026-08-12.json",
            "dispatch-2026-08-13.json",
            "dispatch-2026-08-28.json",
        ])
        for path in paths:
            with self.subTest(path=path.name):
                props = load(path)
                self.assertEqual(props["schemaVersion"], 2)
                self.assertEqual(props["fps"], 30)
                self.assertGreaterEqual(props["total"], 112 * 30)
                self.assertLessEqual(props["total"], 130 * 30)
                self.assertEqual(props["safeZones"], {
                    "squareTop": 420, "squareBottom": 1500,
                    "actionLeft": 72, "actionRight": 1008,
                    "captionTop": 1328, "captionBottom": 1484,
                })
                self.assertEqual(round(props["credits"]["seconds"] * 30), props["credits"]["frames"])
                expected = 0
                source_ids = {source["id"] for source in props["sources"]}
                asset_ids = {asset["id"] for asset in props["assets"]}
                self.assertEqual(len(source_ids), len(props["sources"]))
                self.assertEqual(len(asset_ids), len(props["assets"]))
                for scene in props["scenes"]:
                    self.assertEqual(scene["from"], expected)
                    expected += scene["dur"]
                    self.assertTrue(set(scene["sourceIds"]).issubset(source_ids))
                    if scene.get("assetId"):
                        self.assertIn(scene["assetId"], asset_ids)
                self.assertEqual(expected + props["credits"]["frames"], props["total"])
                self.assertTrue(set(props["credits"]["sourceIds"]).issubset(source_ids))
                story_seconds = expected / 30
                self.assertTrue(all(cue["t"] + cue["d"] <= story_seconds for cue in props["captions"]))
                self.assertTrue(all(word["end"] <= story_seconds for word in props["wordTimings"]))

                synthetic = props["episode"]["provenance"]["kind"] == "synthetic_canary"
                if synthetic:
                    self.assertIn("not a historical episode", props["episode"]["provenance"]["notice"])
                    self.assertEqual(props["sources"], [])
                    self.assertEqual(props["credits"]["sourceIds"], [])
                    self.assertTrue(all(scene["sourceIds"] == [] for scene in props["scenes"]))
                else:
                    self.assertIn("Historical reconstruction", props["episode"]["provenance"]["notice"])
                    self.assertTrue(props["sources"])
                    self.assertTrue(all(scene["sourceIds"] for scene in props["scenes"]))

    def test_active_registry_names_one_parametric_component(self):
        registry = load(ROOT / "config" / "compositions.json")
        active = registry["compositions"]["DispatchDaily"]
        self.assertEqual(registry["active_composition"], "DispatchDaily")
        self.assertEqual(active["template_kind"], "parametric_dispatch_daily")
        self.assertIs(active["generic_daily_template"], True)
        self.assertEqual(active["props_schema"], "config/episode_props.schema.json")
        self.assertEqual(active["default_duration_in_frames"], 3600)
        self.assertEqual(len(active["frozen_fixtures"]), 3)
        self.assertEqual(active["source_dependencies"], [
            "video-engine/src/DispatchDailyComposition.tsx",
        ])

    def test_runtime_parser_and_component_fail_closed_without_historical_wrapper(self):
        adapter = (ROOT / "video-engine" / "src" / "DispatchDaily.tsx").read_text(encoding="utf-8")
        parser = (ROOT / "video-engine" / "src" / "DispatchDailySchema.ts").read_text(encoding="utf-8")
        component = (ROOT / "video-engine" / "src" / "DispatchDailyComposition.tsx").read_text(encoding="utf-8")
        root = (ROOT / "video-engine" / "src" / "Root.tsx").read_text(encoding="utf-8")
        self.assertNotIn("Ep0813", adapter)
        self.assertIn("validateDispatchDailyProps(rawProps)", adapter)
        self.assertIn("validateDispatchDailyProps(fixture0812)", adapter)
        self.assertIn(".strict()", parser)
        self.assertIn("superRefine", parser)
        self.assertIn("synthetic canaries may not masquerade as sourced history", parser)
        self.assertIn("<EndCredits", component)
        self.assertIn('name="ACCESSIBLE_CAPTIONS"', component)
        self.assertIn("dispatchDailyMetadata(props)", root)
        self.assertEqual(root.count('id="DispatchDaily"'), 1)


if __name__ == "__main__":
    unittest.main()
