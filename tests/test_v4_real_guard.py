import unittest

from experiments.v4_llm_eval import eligible_actions


class GuardTests(unittest.TestCase):
    def test_excludes_only_successful_actions(self):
        task = {'allowed_tools': ['deduplicate', 'rolling_mean', 'count_categories']}
        observation = {'history': [{'action': 'deduplicate', 'ok': True},
                                   {'action': 'rolling_mean', 'ok': False}]}
        self.assertEqual(task['allowed_tools'], eligible_actions(task, observation))
        self.assertEqual(['rolling_mean', 'count_categories'],
                         eligible_actions(task, observation, True))


if __name__ == '__main__':
    unittest.main()
