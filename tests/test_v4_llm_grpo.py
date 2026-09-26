import unittest

from experiments.v4_llm_grpo import (count_passed, fault_conditions,
                                      groups_from_scan, has_learning_signal,
                                      select_train_tasks)


class TestV4LlmGrpo(unittest.TestCase):
    def test_balanced_seeded_selection(self):
        tasks = [
            {'task_id': f'{family}-{source}', 'split': 'train',
             'pair_family': family, 'source_id': source}
            for source in range(3) for family in range(4)
        ]
        first = select_train_tasks(tasks, 8, 7)
        second = select_train_tasks(tasks, 8, 7)
        self.assertEqual([x['task_id'] for x in first], [x['task_id'] for x in second])
        self.assertEqual({0, 1, 2, 3}, {x['pair_family'] for x in first})
        self.assertEqual({0: 2, 1: 2, 2: 2, 3: 2},
                         {family: sum(x['pair_family'] == family for x in first)
                          for family in range(4)})

    def test_selection_excludes_non_train_tasks(self):
        tasks = [
            {'task_id': 'train', 'split': 'train', 'pair_family': 0},
            {'task_id': 'dev', 'split': 'dev', 'pair_family': 1},
        ]
        self.assertEqual(['train'], [x['task_id'] for x in select_train_tasks(tasks, 2, 1)])

    def test_fault_conditions_are_separate(self):
        self.assertEqual((False,), fault_conditions('clean'))
        self.assertEqual((True,), fault_conditions('fault'))
        self.assertEqual((False, True), fault_conditions('both'))

    def test_positive_shaped_reward_is_not_counted_as_success(self):
        records = [{'passed': [False, True]}, {'passed': [False, False]}]
        rewards = [0.07, 1.11, 0.01, -0.03]
        self.assertEqual(1, count_passed(records))
        self.assertEqual(3, sum(x > 0 for x in rewards))

    def test_scan_selects_only_verified_train_signal(self):
        tasks = [{'task_id': 'a', 'pair_family': 0, 'split': 'train'},
                 {'task_id': 'b', 'pair_family': 1, 'split': 'train'},
                 {'task_id': 'dev', 'pair_family': 2, 'split': 'dev'}]
        scan = {'schema_version': 'v4-llm-signal-scan-1', 'seed': 1, 'model': 'deepseek',
                'protocol_sha256': 'protocol', 'adapter_sha256': {'a': 'hash'},
                'group_size': 4, 'temperature': .9, 'max_new_tokens': 48,
                'records': [
                    {'task_id': 'a', 'pair_family': 0, 'fault': False, 'signal': 'zero'},
                    {'task_id': 'a', 'pair_family': 0, 'fault': True, 'signal': 'outcome'},
                    {'task_id': 'b', 'pair_family': 1, 'fault': False, 'signal': 'prefix'}]}
        kwargs = dict(seed=1, model='deepseek', protocol_sha256='protocol', adapter_sha256={'a': 'hash'},
                      group_size=4, temperature=.9, max_new_tokens=48, limit=8)
        self.assertEqual([('a', True), ('b', False)],
                         [(task['task_id'], fault) for task, fault in
                          groups_from_scan(tasks, scan, **kwargs)])
        with self.assertRaisesRegex(ValueError, 'adapter_sha256 mismatch'):
            groups_from_scan(tasks, scan, **{**kwargs, 'adapter_sha256': {}})

    def test_cost_difference_alone_is_not_task_signal(self):
        self.assertFalse(has_learning_signal([
            {'passed': False, 'matched_prefix': 1, 'reward': .11},
            {'passed': False, 'matched_prefix': 1, 'reward': .09}]))
        self.assertTrue(has_learning_signal([
            {'passed': False, 'matched_prefix': 1},
            {'passed': False, 'matched_prefix': 2}]))


if __name__ == '__main__':
    unittest.main()
