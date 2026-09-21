import unittest

from experiments.v4_llm_grpo import count_passed, fault_conditions, select_train_tasks


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


if __name__ == '__main__':
    unittest.main()
