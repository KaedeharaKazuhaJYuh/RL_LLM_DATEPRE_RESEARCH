import json
import math
import os
import random
import statistics
import tempfile
import unittest
from pathlib import Path

from agent.native_rolling import rolling_mean
from research.io import ROOT
from research.v4_sequence_env import SequenceEnv


@unittest.skipUnless(os.environ.get('V5_ROLLING_LIB') and
                     Path(os.environ.get('V5_ROLLING_LIB', '')).is_file(),
                     'optional native library not built')
class NativeRollingTests(unittest.TestCase):
    def test_edge_cases_and_elementwise_differential(self):
        rng = random.Random(20260927)
        for length, window in ((0, 1), (2, 3), (4, 1), (4, 2), (1000, 7)):
            values = [rng.uniform(-100, 100) for _ in range(length)]
            expected = [statistics.mean(values[i-window+1:i+1])
                        for i in range(window-1, length)]
            actual = rolling_mean(values, window)
            self.assertEqual(len(actual), len(expected))
            for left, right in zip(actual, expected):
                self.assertTrue(math.isclose(left, right, rel_tol=1e-10, abs_tol=1e-10))
        for invalid in ([math.nan], [math.inf]):
            with self.assertRaisesRegex(ValueError, 'rejected'):
                rolling_mean(invalid, 1)

    def test_complete_real_episode_preserves_verifier_result(self):
        folder = ROOT / 'tasks/v4/real_csv_v1'
        tasks = json.loads((folder / 'tasks.json').read_text(encoding='utf-8'))
        oracle = json.loads((folder / 'dev_oracle.json').read_text(encoding='utf-8'))
        task = next(t for t in tasks if t['pair_family'] == 0)
        original = os.environ.get('V5_ROLLING_BACKEND')
        try:
            with tempfile.TemporaryDirectory() as scratch:
                for backend in ('python', 'native'):
                    os.environ['V5_ROLLING_BACKEND'] = backend
                    env = SequenceEnv(task, oracle[task['task_id']], Path(scratch) / backend)
                    for action in (*oracle[task['task_id']]['plan'], 'stop'):
                        env.step(action)
                    self.assertTrue(env.result()['passed'], backend)
        finally:
            if original is None:
                os.environ.pop('V5_ROLLING_BACKEND', None)
            else:
                os.environ['V5_ROLLING_BACKEND'] = original


if __name__ == '__main__':
    unittest.main()
