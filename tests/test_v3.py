import json, tempfile, unittest
from pathlib import Path
from research.benchmark_v3 import build
from research.v3_baselines import evaluate


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


if __name__ == "__main__": unittest.main()
