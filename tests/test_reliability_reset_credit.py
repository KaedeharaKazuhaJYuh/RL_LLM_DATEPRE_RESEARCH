"""Recovery-credit intervention, replacement and budget-isolation controls."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from faultda_bench.semantic.policies import choose
from faultda_bench.semantic.tasks import load
from research.reliability_reset.recovery_credit import build, run, summarize


class RecoveryCreditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.tasks = {t["id"]: t for t in load()}
        cls.summary = build(cls.root / "study", ["group-01", "window-01", "version-01"])
        cls.rows = json.loads((cls.root / "study" / "runs.json").read_text(encoding="utf-8"))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def execution(self, system, condition="semantic_error", budget=4, task="group-01"):
        row = next(r for r in self.rows if r["system"] == system and r["condition"] == condition
                   and r["checks_budget"] == budget and r["task_id"] == task)
        return json.loads((self.root / "study" / row["evidence"]).read_text(encoding="utf-8"))

    def test_primary_helper_and_replacement_have_matched_public_inputs(self):
        self.assertEqual(self.summary["executions"], 252)
        self.assertEqual(self.summary["triplet_count"], 108)
        self.assertEqual(self.summary["environment_families"], 1)
        self.assertIsNone(self.summary["independent_sample_size"])
        self.assertEqual(self.summary["native_exact_agree"], 252)

    def test_assistance_gain_is_not_mistaken_for_gain_over_replacement(self):
        t = next(t for t in self.summary["triplets"] if t["task_id"] == "group-01" and t["condition"] == "semantic_error"
                 and t["checks_budget"] == 4 and t["policy"] == "generic_verify")
        self.assertEqual((t["A"], t["AH"], t["H"]), (0, 1, 1))
        self.assertEqual(t["assistance_gain"], 1)
        self.assertEqual(t["gain_over_replacement"], 0)

    def test_helper_does_not_receive_fresh_budget_at_handoff(self):
        t = next(t for t in self.summary["triplets"] if t["task_id"] == "group-01" and t["condition"] == "semantic_error"
                 and t["checks_budget"] == 1 and t["policy"] == "generic_verify")
        self.assertEqual((t["A"], t["AH"], t["H"]), (0, 0, 1))
        combined = self.execution("generic_verify+helper", budget=1)
        self.assertEqual(combined["cost"]["checks"], 1)
        self.assertEqual(combined["terminal"], "escalate")

    def test_handoff_is_charged_and_is_not_a_stop_followed_by_more_actions(self):
        execution = self.execution("generic_verify+helper")
        cost = execution["cost"]
        self.assertEqual(cost["decisions"], cost["tool_decisions"] + cost["handoff_decisions"])
        self.assertEqual(cost["handoff_decisions"], 1)
        handoff = next(d for d in execution["decisions"] if d["kind"] == "handoff")
        self.assertEqual(handoff["proposal"]["action"], "stop")
        self.assertEqual(execution["steps"][-1]["action"], "stop")
        self.assertTrue(all(s["action"] not in ("stop", "escalate") for s in execution["steps"][:-1]))
        self.assertEqual({s["actor"] for s in execution["steps"]}, {"primary", "helper"})

    def test_help_can_reduce_completion_without_creating_a_safety_violation(self):
        t = next(t for t in self.summary["triplets"] if t["task_id"] == "group-01" and t["condition"] == "healthy"
                 and t["checks_budget"] == 1 and t["policy"] == "generic_verify")
        self.assertEqual((t["A"], t["AH"], t["H"]), (1, 0, 1))
        execution = self.execution("generic_verify+helper", "healthy", budget=1)
        self.assertEqual(execution["terminal"], "escalate")
        self.assertTrue(execution["independent_assessment"]["snapshot_correct"])
        self.assertFalse(execution["independent_assessment"]["forbidden_effect"])
        self.assertEqual(execution["cost"]["checks"], 1)
        self.assertLess(execution["cost"]["decisions"], 16)

    def test_controllers_only_receive_serialized_public_observation(self):
        seen = []
        def spy(observation, policy):
            self.assertEqual(set(observation), {"contract", "tools", "initial_feedback", "remaining", "history", "terminal"})
            self.assertNotIn("reference", json.dumps(observation))
            seen.append(policy)
            return choose(observation, policy)
        result = run(self.tasks["group-01"], self.root / "spy", "semantic_error", 4, "generic_verify", True, spy)
        self.assertTrue(result["independent_assessment"]["safe_complete"])
        self.assertEqual(set(seen), {"generic_verify"})  # helper never invokes the primary dispatcher

    def test_benign_row_order_preserves_all_native_and_exact_successes(self):
        for system in ("generic_verify", "version_refresh", "task_semantic", "helper_only"):
            for task in ("group-01", "window-01", "version-01"):
                clean = self.execution(system, "healthy", task=task)
                benign = self.execution(system, "benign_reorder", task=task)
                self.assertTrue(benign["independent_assessment"]["safe_complete"])
                self.assertEqual(clean["independent_assessment"]["reference"], benign["independent_assessment"]["reference"])
                self.assertEqual(clean["native_result"]["safe_complete"], benign["native_result"]["safe_complete"])

    def test_before_after_commit_have_equal_feedback_but_distinct_persisted_state(self):
        before = self.execution("helper_only", "before_commit_timeout")
        after = self.execution("helper_only", "after_commit_timeout")
        self.assertEqual(before["public_input"]["initial_feedback"], after["public_input"]["initial_feedback"])
        self.assertEqual(len(before["initial_records"]), 0)
        self.assertEqual(len(after["initial_records"]), 1)
        self.assertTrue(before["independent_assessment"]["safe_complete"])
        self.assertTrue(after["independent_assessment"]["safe_complete"])

    def test_fraction_reference_catches_semantics_in_each_intent(self):
        for task in ("group-01", "window-01", "version-01"):
            strong = self.execution("helper_only", task=task)
            self.assertFalse(strong["native_result"]["private_records"][0]["output"] ==
                             strong["native_result"]["private_records"][-1]["output"]
                             and strong["native_result"]["private_records"][0]["version"] ==
                             strong["native_result"]["private_records"][-1]["version"])
            self.assertTrue(strong["independent_assessment"]["safe_complete"])
            self.assertEqual(strong["independent_assessment"]["wrong_publications"], [])

    def test_all_costs_are_bounded_without_hidden_helper_operations(self):
        for row in self.rows:
            cost = row["cost"]
            self.assertLessEqual(cost["checks"], row["caps"]["checks"])
            self.assertLessEqual(cost["mutations"], 6)
            self.assertLessEqual(cost["decisions"], 16)
            self.assertEqual(cost["decisions"], cost["tool_decisions"] + cost["handoff_decisions"])

    def test_mismatched_budget_and_duplicate_cells_are_rejected(self):
        rows = copy.deepcopy(self.rows)
        target = next(r for r in rows if r["system"].endswith("+helper"))
        target["caps"]["checks"] += 1
        with self.assertRaisesRegex(ValueError, "unmatched"):
            summarize(rows)
        with self.assertRaisesRegex(ValueError, "duplicate experiment cell"):
            summarize(self.rows + [self.rows[0]])

    def test_frozen_design_is_bound_and_existing_output_not_overwritten(self):
        design = json.loads((self.root / "study" / "study_design.json").read_text(encoding="utf-8"))
        self.assertEqual(design["expected_executions"], 252)
        self.assertEqual(design["model_calls"], 0)
        self.assertEqual(len(design["tasks"]), 3)
        self.assertEqual(len({self.execution(s)["design_sha256"] for s in ("generic_verify", "generic_verify+helper", "helper_only")}), 1)
        with self.assertRaisesRegex(ValueError, "must be new"):
            build(self.root / "study")


if __name__ == "__main__":
    unittest.main()
