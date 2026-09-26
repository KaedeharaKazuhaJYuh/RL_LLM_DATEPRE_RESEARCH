import unittest

from experiments.v4_llm_signal_scan import classify_group, selected_tasks
from research.io import ROOT


class TestSignalScan(unittest.TestCase):
    def test_signal_priority_avoids_cost_only_false_positive(self):
        def row(passed, prefix, reward):
            return {'passed': passed, 'matched_prefix': prefix, 'reward': reward}
        self.assertEqual('outcome', classify_group([row(False, 2, .1), row(True, 3, .9)]))
        self.assertEqual('prefix', classify_group([row(False, 1, .1), row(False, 2, .2)]))
        self.assertEqual('cost_only', classify_group([row(False, 1, .1), row(False, 1, .09)]))
        self.assertEqual('zero', classify_group([row(True, 3, .8), row(True, 3, .8)]))

    def test_fixed_scan_covers_only_training_families(self):
        protocol = ROOT / 'tasks/v4/llm_hard_v1'
        chosen = selected_tasks(protocol, 20260926)
        self.assertEqual(8, len(chosen))
        self.assertEqual(list(range(8)), [row['pair_family'] for row in chosen])
        self.assertTrue(all(row['split'] == 'train' for row in chosen))


if __name__ == '__main__':
    unittest.main()
