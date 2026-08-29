#!/usr/bin/env python3
"""Focused deterministic and adversarial tests for the offline replay evaluator."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replay_eval as evaluator


class ReplayEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.eval_root = cls.root / "eval" / "replay"
        cls.baseline = evaluator.load_baseline(cls.eval_root / "baseline_context.json")
        cls.fixtures = evaluator.load_fixtures(cls.eval_root / "fixtures")
        cls.telemetry = [
            evaluator.load_telemetry(path)
            for path in sorted((cls.eval_root / "telemetry").glob("*.json"))
        ]

    def evaluate(self, telemetry=None):
        return evaluator.evaluate(
            copy.deepcopy(self.baseline),
            copy.deepcopy(self.fixtures),
            copy.deepcopy(telemetry if telemetry is not None else self.telemetry),
        )

    def test_committed_sample_passes_with_expected_budget_results(self):
        report = self.evaluate()
        self.assertTrue(report["pass"])
        self.assertEqual(report["summary"], {"fixture_count": 3, "passed": 3, "failed": 0})
        self.assertEqual(report["baseline"]["standing_context_tokens"], 34726)
        self.assertEqual(report["baseline"]["referenced_context_tokens"], 64793)
        by_id = {item["fixture_id"]: item for item in report["fixtures"]}
        self.assertEqual(by_id["2026-08-12"]["optimized"]["call_count"], 7)
        self.assertEqual(by_id["2026-08-13"]["optimized"]["call_count"], 7)
        self.assertEqual(by_id["2026-08-28"]["optimized"]["call_count"], 12)
        self.assertEqual(by_id["2026-08-28"]["optimized"]["revisions"]["repair_passes"], 1)
        self.assertGreaterEqual(
            min(item["standing_context_reduction_percent"] for item in report["fixtures"]),
            evaluator.TARGETS["standing_context_reduction_percent_min"],
        )

    def test_report_is_order_independent_and_markdown_is_deterministic(self):
        first = self.evaluate(self.telemetry)
        second = self.evaluate(list(reversed(self.telemetry)))
        self.assertEqual(first, second)
        self.assertEqual(evaluator.markdown_report(first), evaluator.markdown_report(second))
        self.assertIn("`synthetic` controller telemetry", evaluator.markdown_report(first))

    def test_fixture_provenance_is_explicit(self):
        self.assertEqual(self.fixtures["2026-08-12"]["fixture_kind"], "archived_exact")
        self.assertEqual(self.fixtures["2026-08-13"]["fixture_kind"], "derived_source")
        self.assertEqual(self.fixtures["2026-08-28"]["fixture_kind"], "synthetic_contract")
        self.assertTrue(self.fixtures["2026-08-12"]["exact_artifacts"])
        self.assertFalse(self.fixtures["2026-08-28"]["exact_artifacts"])

    def test_every_budget_and_quality_loss_fails_closed(self):
        cases = {}

        low_reduction = copy.deepcopy(self.telemetry)
        low_reduction[0]["runs"][0]["standing_context_tokens"] = 20000
        cases["standing_context_reduction"] = low_reduction

        too_many_calls = copy.deepcopy(self.telemetry)
        source_call = too_many_calls[0]["runs"][0]["calls"][0]
        for index in range(3):
            clone = copy.deepcopy(source_call)
            clone["id"] = f"extra_{index}"
            too_many_calls[0]["runs"][0]["calls"].append(clone)
        cases["scenario_call_budget"] = too_many_calls

        too_many_repairs = copy.deepcopy(self.telemetry)
        too_many_repairs[2]["runs"][0]["revisions"]["repair_passes"] = 2
        cases["repair_budget"] = too_many_repairs

        lost_output = copy.deepcopy(self.telemetry)
        lost_output[0]["runs"][0]["preserved_outputs"].remove("claims")
        cases["required_outputs_preserved"] = lost_output

        failed_gate = copy.deepcopy(self.telemetry)
        failed_gate[0]["runs"][0]["gates"][0]["result"] = "fail"
        cases["required_gates_preserved"] = failed_gate

        missing_gate = copy.deepcopy(self.telemetry)
        missing_gate[0]["runs"][0]["gates"].pop()
        cases["required_gates_preserved_missing"] = missing_gate

        for name, telemetry in cases.items():
            with self.subTest(name=name):
                report = self.evaluate(telemetry)
                self.assertFalse(report["pass"])

    def test_search_counts_and_additional_outputs_are_reported_not_invented_budgets(self):
        telemetry = copy.deepcopy(self.telemetry)
        run = telemetry[0]["runs"][0]
        run["tools"]["search_calls"] = 3
        run["tools"]["fetch_calls"] = 12
        run["preserved_outputs"].append("additional_preview")
        run["gates"].append({"id": "advisory_flow", "result": "pass"})
        report = self.evaluate(telemetry)
        item = next(item for item in report["fixtures"] if item["fixture_id"] == "2026-08-12")
        self.assertTrue(item["pass"])
        self.assertEqual(item["optimized"]["tools"]["search_calls"], 3)
        self.assertEqual(item["optimized"]["tools"]["fetch_calls"], 12)
        self.assertEqual(item["quality_contract"]["unexpected_outputs"], ["additional_preview"])
        self.assertEqual(item["quality_contract"]["unexpected_gates"], ["advisory_flow"])

    def test_hard_call_cap_is_independent_of_scenario_limit(self):
        telemetry = copy.deepcopy(self.telemetry)
        run = telemetry[2]["runs"][0]
        source_call = run["calls"][0]
        for index in range(4):
            clone = copy.deepcopy(source_call)
            clone["id"] = f"hard_cap_extra_{index}"
            run["calls"].append(clone)
        report = self.evaluate(telemetry)
        item = next(item for item in report["fixtures"] if item["fixture_id"] == "2026-08-28")
        self.assertFalse(item["checks"]["scenario_call_budget"])
        self.assertFalse(item["checks"]["hard_call_budget"])

    def test_telemetry_schema_rejects_extra_keys_duplicate_calls_and_cache_overclaim(self):
        source = json.loads(
            (self.eval_root / "telemetry" / "2026-08-12.json").read_text(encoding="utf-8")
        )
        mutations = []
        extra = copy.deepcopy(source)
        extra["unexpected"] = True
        mutations.append(extra)
        duplicate = copy.deepcopy(source)
        duplicate["runs"][0]["calls"].append(copy.deepcopy(duplicate["runs"][0]["calls"][0]))
        mutations.append(duplicate)
        cache = copy.deepcopy(source)
        call = cache["runs"][0]["calls"][0]
        call["cache_read_tokens"] = call["prompt_tokens"] + call["input_tokens"] + 1
        mutations.append(cache)
        boolean_token = copy.deepcopy(source)
        boolean_token["runs"][0]["calls"][0]["prompt_tokens"] = True
        mutations.append(boolean_token)
        zero_token = copy.deepcopy(source)
        call = zero_token["runs"][0]["calls"][0]
        for field in (
            "prompt_tokens", "input_tokens", "output_tokens", "cache_read_tokens",
            "cache_write_tokens",
        ):
            call[field] = 0
        mutations.append(zero_token)

        for index, value in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "telemetry.json"
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(evaluator.ReplayEvalError):
                    evaluator.load_telemetry(path)

    def test_strict_json_rejects_duplicate_keys_and_non_finite_values(self):
        payloads = (
            '{"schema_version":1,"schema_version":1}',
            '{"schema_version":NaN}',
            '{"schema_version":1e9999}',
        )
        for payload in payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "bad.json"
                path.write_text(payload, encoding="utf-8")
                with self.assertRaises(evaluator.ReplayEvalError):
                    evaluator.load_telemetry(path)

    def test_baseline_hash_drift_is_rejected(self):
        source = json.loads(
            (self.eval_root / "baseline_context.json").read_text(encoding="utf-8")
        )
        source["standing_context"][0]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "baseline.json"
            path.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaisesRegex(evaluator.ReplayEvalError, "frozen Git blob"):
                evaluator.load_baseline(path)

    def test_fixture_rejects_path_escape_and_synthetic_exactness_lie(self):
        source = json.loads(
            (self.eval_root / "fixtures" / "2026-08-13.json").read_text(encoding="utf-8")
        )
        escape = copy.deepcopy(source)
        escape["artifacts"][0]["path"] = "../outside"
        synthetic_lie = copy.deepcopy(source)
        synthetic_lie["fixture_kind"] = "synthetic_contract"
        for value in (escape, synthetic_lie):
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "fixture.json"
                path.write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(evaluator.ReplayEvalError):
                    evaluator.load_fixture(path)

    def test_duplicate_and_incomplete_telemetry_coverage_is_rejected(self):
        duplicate = copy.deepcopy(self.telemetry)
        duplicate.append(copy.deepcopy(duplicate[0]))
        with self.assertRaisesRegex(evaluator.ReplayEvalError, "telemetry ids"):
            self.evaluate(duplicate)
        with self.assertRaisesRegex(evaluator.ReplayEvalError, "coverage"):
            self.evaluate(self.telemetry[:2])

    def test_scenario_relabel_and_mixed_controller_are_rejected(self):
        relabeled = copy.deepcopy(self.telemetry)
        relabeled[0]["runs"][0]["scenario"] = "worst_case"
        with self.assertRaisesRegex(evaluator.ReplayEvalError, "requires scenario"):
            self.evaluate(relabeled)

        mixed = copy.deepcopy(self.telemetry)
        mixed[0]["controller"]["version"] = "different-version"
        with self.assertRaisesRegex(evaluator.ReplayEvalError, "one controller"):
            self.evaluate(mixed)


if __name__ == "__main__":
    unittest.main()
