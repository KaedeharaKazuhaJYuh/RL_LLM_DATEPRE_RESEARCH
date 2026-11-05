"""Fault-exposure denominators, public-prefix fidelity and missingness checks."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from research.reliability_reset.claim_screen import ARMS, after_timeout, differences, screen, summarize


class ClaimScreenTests(unittest.TestCase):
    @staticmethod
    def rows():
        return [{"task_id": "one", "interface": "canonical", "arm": arm,
                 "activated": arm != "feasible_tools", "safe_escalation": True,
                 "task_completed": False, "prefix": {"available": arm != "feasible_tools", "public_prefix_sha256": "prefix",
                                                        "next_original_proposal": {"action": "escalate"},
                                                        "continuation_requests": 1, "continuation_tokens": 10}}
                for arm in ARMS]

    def test_pre_activation_escalation_remains_in_planned_denominator(self):
        result = summarize(self.rows())
        projected = next(r for r in result["totals"] if r["arm"] == "feasible_tools")
        self.assertEqual(projected["planned"], 1)
        self.assertEqual(projected["activated"], 0)
        self.assertEqual(projected["safe_escalations_all_planned"], 1)
        self.assertEqual(projected["safe_escalations_after_activation"], 0)
        pair = result["paired_descriptions"][1]
        self.assertEqual(pair["activation_differs"], 1)
        self.assertEqual(pair["both_activated"], 0)

    def test_same_task_id_is_not_enough_for_equal_public_prefix(self):
        rows = self.rows()
        rows[1]["prefix"]["public_prefix_sha256"] = "different"
        result = summarize(rows)["paired_descriptions"][0]
        self.assertEqual(result["both_activated"], 1)
        self.assertEqual(result["exact_prefix_pairs"], 0)
        self.assertEqual(result["different_or_missing_prefix"], 1)

    def test_duplicate_missing_arm_and_missing_outcome_are_not_silently_dropped(self):
        cases = [self.rows() + [self.rows()[0]], self.rows()[:-1]]
        missing = self.rows()
        missing[0]["task_completed"] = None
        cases.append(missing)
        for rows in cases:
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    summarize(rows)

    def test_identifier_difference_is_reported_and_not_normalized_away(self):
        a = {"history": [{"params": {"request_id": "req-1"}, "response": {"value": 12}}]}
        b = copy.deepcopy(a)
        b["history"][0]["params"]["request_id"] = "repair-1"
        self.assertEqual(differences(a, b), [{"path": "$.history[0].params.request_id", "left": "req-1", "right": "repair-1"}])
        self.assertEqual(a["history"][0]["params"]["request_id"], "req-1")

    def test_no_trigger_and_missing_continuation_are_distinct(self):
        self.assertEqual(after_timeout({"steps": []}, [], "canonical")["reason"], "fault_not_activated")
        execution = {"steps": [{"action": "publish", "response": {"error": "timeout"}}],
                     "decisions": [{"kind": "tool_action"}], "dispatch": []}
        self.assertEqual(after_timeout(execution, [], "canonical")["reason"], "no_recorded_post_fault_decision")

    def test_original_archive_is_screened_without_model_or_new_executions(self):
        archive = Path("research/reliability_reset/evidence/1.0.55/deepseek-feasible-interface-1.0.55.zip")
        expected = json.loads(archive.with_name("PUBLIC_RECORD.json").read_text())["sha256"]
        with patch("urllib.request.urlopen", side_effect=AssertionError("offline only")), \
             patch("research.reliability_reset.recovery_credit.SemanticEnv", side_effect=AssertionError("no new task execution")), \
             patch("faultda_bench.semantic.policies.calculate", side_effect=AssertionError("no numerical oracle or recomputation")):
            result = screen(archive, expected)
        self.assertEqual(result["source_responses_reparsed"], 207)
        self.assertEqual(result["post_fault_records"], 17)
        self.assertEqual(result["public_rule_escalation_proposals"], 17)
        self.assertEqual(result["unique_public_prefixes"], 4)
        self.assertEqual(result["paired_descriptions"][0]["exact_prefix_pairs"], 6)
        comparison = result["paired_descriptions"][1]
        self.assertEqual(comparison["exact_prefix_pairs"], 4)
        self.assertEqual(comparison["immediate_escalation_increased_on_exact_prefix"], 2)
        self.assertEqual(comparison["left_continuation_requests_on_exact_prefix"], 6)
        self.assertEqual(comparison["right_continuation_requests_on_exact_prefix"], 4)
        diff = next(r for r in comparison["pair_details"] if not r["exact_prefix"])
        self.assertEqual([r["path"] for r in diff["public_differences"]], ["$.history[2].params.request_id"])
        self.assertEqual(result["new_api_calls"], 0)
        self.assertEqual(result["new_model_trajectories"], 0)


if __name__ == "__main__":
    unittest.main()
