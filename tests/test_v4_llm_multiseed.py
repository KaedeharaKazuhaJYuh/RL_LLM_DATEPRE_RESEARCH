import unittest

from experiments.v4_llm_multiseed_summary import paired_summary


class MultiSeedSummaryTests(unittest.TestCase):
    def test_paired_gain_and_loss_are_counted_from_terminal_pass(self):
        baseline = {'records': [
            {'task_id': 'a', 'fault': False, 'passed': False},
            {'task_id': 'b', 'fault': True, 'passed': True},
            {'task_id': 'c', 'fault': False, 'passed': True},
        ]}
        treated = {'records': [
            {'task_id': 'a', 'fault': False, 'passed': True},
            {'task_id': 'b', 'fault': True, 'passed': False},
            {'task_id': 'c', 'fault': False, 'passed': True},
        ]}
        summary = paired_summary(baseline, treated)
        self.assertEqual(1, summary['gained'])
        self.assertEqual(1, summary['lost'])
        self.assertEqual(1, summary['unchanged_pass'])
        self.assertEqual(0, summary['unchanged_fail'])

    def test_pair_order_mismatch_is_rejected(self):
        baseline = {'records': [{'task_id': 'a', 'fault': False, 'passed': False}]}
        treated = {'records': [{'task_id': 'b', 'fault': False, 'passed': False}]}
        with self.assertRaises(ValueError):
            paired_summary(baseline, treated)


if __name__ == '__main__':
    unittest.main()
