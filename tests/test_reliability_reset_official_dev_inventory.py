import io
import json
import unittest
import zipfile

from research.reliability_reset.official_dev_inventory import (
    EXPERIMENT,
    summarize_judgments,
    summarize_official_split,
)


class JudgmentTests(unittest.TestCase):
    def test_bounds_keep_unknown_cases_in_denominator(self):
        records = [
            {"case_id": "a", "native": "pass", "safety": "violation", "judgment_reference": "review:a"},
            {"case_id": "b", "native": "pass", "safety": "no_violation", "judgment_reference": "review:b"},
            {"case_id": "c", "native": "pass", "safety": "unknown"},
            {"case_id": "d", "native": "fail", "safety": "violation", "judgment_reference": "review:d"},
        ]
        result = summarize_judgments(records)
        self.assertEqual(result["cells"]["pass"], {"violation": 1, "no_violation": 1, "unknown": 1})
        self.assertEqual(result["native_pass_violation_bounds"], {"lower": 1 / 3, "upper": 2 / 3})

    def test_no_native_pass_has_no_rate(self):
        self.assertIsNone(summarize_judgments([{"case_id": "x", "native": "fail", "safety": "unknown"}])["native_pass_violation_bounds"])

    def test_duplicate_and_unreferenced_labels_are_rejected(self):
        row = {"case_id": "a", "native": "pass", "safety": "unknown"}
        with self.assertRaises(ValueError):
            summarize_judgments([row, row])
        with self.assertRaises(ValueError):
            summarize_judgments([{**row, "safety": "violation"}])


class OfficialInventoryTests(unittest.TestCase):
    def test_reports_and_missing_logs_are_not_safety_evidence(self):
        buffer = io.BytesIO()
        prefix = EXPERIMENT + "/dev/"
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(prefix + "metadata.json", json.dumps({"dataset": "dev", "llm": {"name": "model"}, "method": {"name": "agent"}}))
            archive.writestr(prefix + "tasks/", "")
            archive.writestr(prefix + "tasks/one/evaluation/report.md", "Num Passed Tests : 2\nNum Failed Tests : 0\nNum Total  Tests : 2\n")
            archive.writestr(prefix + "tasks/one/logs/api_calls.jsonl", '{}\n{}\n')
            archive.writestr(prefix + "tasks/two/evaluation/report.md", "Num Passed Tests : 1\nNum Failed Tests : 1\nNum Total  Tests : 2\n")
            archive.writestr(prefix + "tasks/three/evaluation/report.md", "malformed")
            archive.writestr(EXPERIMENT + "/test_normal/tasks/forbidden/evaluation/report.md", "not read")
        with zipfile.ZipFile(buffer) as archive:
            result = summarize_official_split(archive, "dev", {"one", "two", "three", "four"})
            complete = summarize_official_split(archive, "dev", {"one", "two", "three"})
            with self.assertRaises(ValueError):
                summarize_official_split(archive, "test_normal")
        self.assertEqual(result["judgments"]["cases"], 3)
        self.assertEqual(result["judgments"]["cells"]["pass"]["unknown"], 1)
        self.assertEqual(result["judgments"]["cells"]["fail"]["unknown"], 1)
        self.assertEqual(result["judgments"]["cells"]["unknown"]["unknown"], 1)
        self.assertEqual(result["log_coverage"]["tracked_requests"], 2)
        self.assertEqual(result["dataset_coverage"], {"dataset_tasks": 4, "missing_from_outputs": 1, "unexpected_in_outputs": 0})
        self.assertIsNone(result["scenario_outcomes"])
        self.assertEqual(complete["scenario_outcomes"], {"pass": 1, "fail": 1, "unknown": 1})
        self.assertIsNone(result["provider_cost"])

    def test_wrong_split_metadata_is_rejected(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(EXPERIMENT + "/dev/metadata.json", '{"dataset":"train"}')
        with zipfile.ZipFile(buffer) as archive, self.assertRaises(ValueError):
            summarize_official_split(archive, "dev")

    def test_scenario_requires_every_variant_to_pass(self):
        buffer = io.BytesIO()
        prefix = EXPERIMENT + "/dev/"
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr(prefix + "metadata.json", json.dumps({"dataset": "dev", "llm": {"name": "model"}, "method": {"name": "agent"}}))
            archive.writestr(prefix + "tasks/group_1/evaluation/report.md", "Num Passed Tests : 2\nNum Failed Tests : 0\nNum Total  Tests : 2\n")
            archive.writestr(prefix + "tasks/group_2/evaluation/report.md", "Num Passed Tests : 1\nNum Failed Tests : 1\nNum Total  Tests : 2\n")
        with zipfile.ZipFile(buffer) as archive:
            result = summarize_official_split(archive, "dev", {"group_1", "group_2"})
        self.assertEqual(result["scenario_outcomes"], {"pass": 0, "fail": 1, "unknown": 0})


if __name__ == "__main__":
    unittest.main()
