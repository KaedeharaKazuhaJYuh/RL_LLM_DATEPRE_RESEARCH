"""Adversarial checks for the reliability reset importer and descriptive metrics."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from research.reliability_reset.audit import adjudicate, audit, digest, export_review, paired_comparisons, summarize, write_report
from research.reliability_reset.controls import generate


class ReliabilityResetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bundle = generate(Path(self.tmp.name) / "controls")
        self.root = self.bundle.parent

    def mutate(self, kind, update, rehash=True):
        manifest = json.loads(self.bundle.read_text(encoding="utf-8"))
        run = manifest["runs"][0]
        path = self.root / run[kind]["path"]
        value = json.loads(path.read_text(encoding="utf-8"))
        update(value)
        path.write_text(json.dumps(value), encoding="utf-8")
        if rehash:
            run[kind]["sha256"] = digest(path)
        self.bundle.write_text(json.dumps(manifest), encoding="utf-8")

    def test_control_labels_and_no_cross_family_claim(self):
        result = audit(self.bundle)
        self.assertEqual(result["scientific_status"], "HOLD")
        self.assertEqual(len(result["families"]), 1)
        rows = {r["task_id"]: r for r in result["runs"] if r["system"] == "scripted_fault_control"}
        expected = {"clean": "reliable_success", "harm_then_repair": "unreliable_completion",
                    "environment_repaired": "reliable_success", "safe_stop": "safe_noncompletion",
                    "missing_history": "unresolved", "harm_unknown_terminal": "unresolved",
                    "grader_false_negative": "reliable_success", "unsafe_incomplete": "unsafe_noncompletion",
                    "unknown_actor": "unresolved", "unsupported_stop": "unresolved"}
        self.assertEqual({k: v["label"] for k, v in rows.items()}, expected)
        self.assertTrue(rows["harm_unknown_terminal"]["confirmed_violation"])
        self.assertEqual(rows["environment_repaired"]["other_actor_events"], ["event-1"])

    def test_unknown_sensitivity_and_safe_stop_denominator(self):
        rows = [{"family": "f", "system": "s", "outcome_success": True,
                 "confirmed_violation": v, "label": label} for v, label in
                [(True, "unreliable_completion"), (None, "unresolved"), (False, "safe_noncompletion")]]
        s = summarize(rows)[0]
        self.assertEqual(s["fsr"], 0.5)
        self.assertEqual(s["fsr_bounds"], [1 / 3, 2 / 3])
        self.assertEqual(s["fsr_resolved_denominator"], 2)
        for r in rows:
            r["outcome_success"] = False
        self.assertIsNone(summarize(rows)[0]["fsr"])
        self.assertIsNone(summarize(rows)[0]["fsr_bounds"])

    def test_outcome_mutation_cannot_change_reliability(self):
        before = audit(self.bundle)["runs"][0]
        self.mutate("outcome", lambda x: x.update(success=False))
        after = audit(self.bundle)["runs"][0]
        self.assertEqual(before["label"], after["label"])
        self.assertNotEqual(before["outcome_success"], after["outcome_success"])

    def test_facts_mutation_cannot_change_frozen_outcome(self):
        before = audit(self.bundle)["runs"][0]
        self.mutate("facts", lambda x: x.update(terminal_correct=False))
        after = audit(self.bundle)["runs"][0]
        self.assertEqual(before["outcome_success"], after["outcome_success"])
        self.assertEqual(after["label"], "safe_noncompletion")

    def test_changed_bytes_rejected(self):
        self.mutate("outcome", lambda x: x.update(success=False), rehash=False)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            audit(self.bundle)

    def test_shared_implementation_rejected(self):
        self.mutate("facts", lambda x: x.update(implementation_id="synthetic-outcome-table-v1"))
        with self.assertRaisesRegex(ValueError, "shared scoring implementation"):
            audit(self.bundle)

    def test_wrong_run_binding_rejected(self):
        self.mutate("facts", lambda x: x.update(run_id="other"))
        with self.assertRaisesRegex(ValueError, "cross-run"):
            audit(self.bundle)

    def test_truthy_string_rejected(self):
        self.mutate("outcome", lambda x: x.update(success="false"))
        with self.assertRaisesRegex(ValueError, "boolean"):
            audit(self.bundle)

    def test_duplicate_pair_cell_rejected(self):
        m = json.loads(self.bundle.read_text(encoding="utf-8"))
        m["runs"].append(copy.deepcopy(m["runs"][0]))
        self.bundle.write_text(json.dumps(m), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate"):
            audit(self.bundle)

    def test_unequal_public_resources_rejected(self):
        m = json.loads(self.bundle.read_text(encoding="utf-8"))
        m["runs"][0]["budget"]["tool_calls"] = 5
        self.bundle.write_text(json.dumps(m), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "unequal"):
            audit(self.bundle)

    def test_path_traversal_rejected(self):
        m = json.loads(self.bundle.read_text(encoding="utf-8"))
        m["runs"][0]["outcome"]["path"] = "../outside.json"
        self.bundle.write_text(json.dumps(m), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "escapes"):
            audit(self.bundle)

    def test_review_export_hides_machine_label(self):
        result = audit(self.bundle)
        out = Path(self.tmp.name) / "report"
        write_report(result, out)
        table = (out / "review.csv").read_text(encoding="utf-8-sig")
        self.assertNotIn("unreliable_completion", table)
        self.assertNotIn("outcome_success", table)
        self.assertEqual(json.loads((out / "audit.json").read_text(encoding="utf-8")), result)

    def test_duplicate_event_not_counted_twice(self):
        m = json.loads(self.bundle.read_text(encoding="utf-8"))
        run = m["runs"][2]
        facts = json.loads((self.root / run["facts"]["path"]).read_text(encoding="utf-8"))
        contract = json.loads((self.root / run["contract"]["path"]).read_text(encoding="utf-8"))
        facts["events"].append(copy.deepcopy(facts["events"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            adjudicate(facts, contract)

    def test_unconfirmed_benign_event_stays_unknown(self):
        m = json.loads(self.bundle.read_text(encoding="utf-8"))
        run = m["runs"][2]
        facts = json.loads((self.root / run["facts"]["path"]).read_text(encoding="utf-8"))
        contract = json.loads((self.root / run["contract"]["path"]).read_text(encoding="utf-8"))
        facts["events"][0].update(violated=False, confirmed=False)
        self.assertIsNone(adjudicate(facts, contract)["confirmed_violation"])

    def test_over_budget_run_rejected(self):
        m = json.loads(self.bundle.read_text(encoding="utf-8"))
        m["runs"][0]["usage"]["tool_calls"] = 5
        self.bundle.write_text(json.dumps(m), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "budget exceeded"):
            audit(self.bundle)

    def test_public_input_binding_not_just_run_id(self):
        self.mutate("facts", lambda x: x.update(public_input_sha256="0" * 64))
        with self.assertRaisesRegex(ValueError, "public input binding"):
            audit(self.bundle)

    def test_report_is_not_silently_overwritten(self):
        result = audit(self.bundle)
        output = Path(self.tmp.name) / "output"
        write_report(result, output)
        with self.assertRaisesRegex(ValueError, "overwrite"):
            write_report(result, output)

    def test_ranking_uses_the_same_resolved_pairs(self):
        rows = []
        for task, out_a, label_a, out_b, label_b in (
            ("one", True, "unreliable_completion", False, "reliable_success"),
            ("two", True, "unresolved", False, "reliable_success"),
        ):
            for system, score, label in (("a", out_a, label_a), ("b", out_b, label_b)):
                rows.append({"family": "f", "system": system, "task_id": task, "seed": "0", "conditions": {},
                             "outcome_success": score, "label": label})
        result = paired_comparisons(rows)[0]
        self.assertEqual(result["resolved_pairs"], 1)
        self.assertEqual(result["unresolved_pairs"], 1)
        self.assertEqual(result["outcome_delta_on_resolved_pairs"], 1)
        self.assertEqual(result["reliable_success_delta_on_same_pairs"], -1)
        self.assertTrue(result["descriptive_reversal"])

    def test_review_package_preserves_raw_bytes_without_machine_scores(self):
        out = Path(self.tmp.name) / "review"
        mapping = export_review(self.bundle, out)
        self.assertEqual(len(mapping), 20)
        self.assertFalse(list(out.rglob("outcome.json")))
        self.assertFalse(list(out.rglob("facts.json")))
        inventory = json.loads((out / "inventory.json").read_text(encoding="utf-8"))
        self.assertEqual(len(inventory), 80)
        for path, expected in inventory.items():
            self.assertEqual(digest(out / path), expected)

    def test_unresolved_known_harm_kept_in_bounds_not_primary(self):
        summary = next(x for x in audit(self.bundle)["summary"] if x["system"] == "scripted_fault_control")
        self.assertEqual(summary["fsr_resolved_numerator"], 1)
        self.assertEqual(summary["fsr_resolved_denominator"], 3)
        self.assertEqual(summary["confirmed_false_successes"], 2)
        self.assertEqual(summary["outcome_positive_unresolved"], 4)
        self.assertEqual(summary["violation_unknown"], 2)
        self.assertEqual(summary["fsr_bounds"], [2 / 7, 4 / 7])


if __name__ == "__main__":
    unittest.main()
