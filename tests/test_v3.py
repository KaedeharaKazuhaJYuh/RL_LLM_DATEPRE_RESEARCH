import json, tempfile, unittest
from pathlib import Path
from research.benchmark_v3 import build
from research.v3_baselines import evaluate
from research.v3_runtime import run_plan
from research.v3_recovery import evaluate as evaluate_recovery


class V3BenchmarkTests(unittest.TestCase):
    def test_holdouts_and_tracks(self):
        with tempfile.TemporaryDirectory() as d:
            tasks, oracle = build(Path(d), sources=8)
            train = [t for t in tasks if t["split"] == "train"]
            test = [t for t in tasks if t["split"] == "test"]
            self.assertFalse({t["source_id"] for t in train} & {t["source_id"] for t in test})
            self.assertFalse({t["prompt"] for t in train} & {t["prompt"] for t in test})
            self.assertEqual({"single", "composition", "clarification"}, {t["track"] for t in tasks})
            self.assertTrue(all(t["task_id"] in oracle for t in tasks))

    def test_oracle_upper_bound(self):
        result = evaluate("oracle")
        self.assertEqual(result["passed"], result["tasks"])

    def test_multistep_artifact_chaining(self):
        tasks = json.loads("[" + ",".join(Path("tasks/v3/tasks.jsonl").read_text(encoding="utf-8").splitlines()) + "]")
        oracle = json.loads(Path("tasks/v3/oracle.json").read_text(encoding="utf-8"))
        task = next(t for t in tasks if t["split"] == "test" and t["track"] == "composition" and oracle[t["task_id"]]["plan"][0] == "deduplicate")
        with tempfile.TemporaryDirectory() as d:
            row = run_plan(task, oracle[task["task_id"]]["plan"], oracle[task["task_id"]], Path(d))
            self.assertTrue(row["passed"])
            self.assertEqual(row["steps"][0]["result"]["artifact"]["sha256"], row["steps"][1]["input_sha256"])

    def test_parameter_error_recovery(self):
        tasks = json.loads("[" + ",".join(Path("tasks/v3/tasks.jsonl").read_text(encoding="utf-8").splitlines()) + "]")
        oracle = json.loads(Path("tasks/v3/oracle.json").read_text(encoding="utf-8"))
        task = next(t for t in tasks if t["split"] == "test" and oracle[t["task_id"]]["plan"][:1] == ["fill_missing"])
        with tempfile.TemporaryDirectory() as d:
            row = run_plan(task, oracle[task["task_id"]]["plan"], oracle[task["task_id"]], Path(d), recover=True, inject_error=True)
            self.assertTrue(row["passed"]); self.assertTrue(row["recovered"]); self.assertFalse(row["steps"][0]["passed"])

    def test_real_data_frozen_recovery(self):
        with tempfile.TemporaryDirectory() as d:
            result=evaluate_recovery(str(Path(d)/"result.json"))
            self.assertEqual({"abalone","seoul_bike","bike_sharing"},set(result["test_sources"]))
            self.assertFalse(result["updates_during_test"])
            self.assertEqual(102,result["test_examples"])
            self.assertEqual(90,result["execution_passed"])
            self.assertEqual(result["test_examples"],result["safe_outcomes_passed"])
            self.assertTrue(result["policy_sha256"])


if __name__ == "__main__": unittest.main()
