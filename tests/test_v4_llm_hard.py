import tempfile
import unittest
from pathlib import Path

from experiments.v4_llm_export import replay
from research.io import ROOT
from research.v4_llm_hard_protocol import build
from research.v4_sequence_env import SequenceEnv


class HardProtocolTests(unittest.TestCase):
    def test_three_step_clean_and_fault_expert_fit_declared_budget(self):
        with tempfile.TemporaryDirectory(prefix='hard_protocol_', dir=ROOT / 'work') as folder:
            protocol = Path(folder) / 'protocol'
            tasks, train, _ = build(protocol)
            task = next(t for t in tasks if t['split'] == 'train')
            gold = train[task['task_id']]
            self.assertEqual(3, len(gold['plan']))
            clean = replay(task, gold, Path(folder) / 'clean', False, False)
            fault = replay(task, gold, Path(folder) / 'fault', True, False)
            self.assertEqual([], clean)
            self.assertEqual([], fault)

    def test_environment_reads_protocol_budgets(self):
        with tempfile.TemporaryDirectory(prefix='hard_budget_', dir=ROOT / 'work') as folder:
            tasks, train, _ = build(Path(folder) / 'protocol')
            task = next(t for t in tasks if t['split'] == 'train')
            env = SequenceEnv(task, train[task['task_id']], Path(folder) / 'episode', fault=True)
            observation = env.observation()
            self.assertEqual(4, observation['remaining_calls'])
            self.assertEqual(5, observation['remaining_decisions'])
            for action in [train[task['task_id']]['plan'][0], *train[task['task_id']]['plan'], 'stop']:
                env.step(action)
            result = env.result()
            self.assertTrue(result['passed'])
            self.assertEqual(4, result['tool_calls'])
            self.assertEqual(5, result['decisions'])
            self.assertEqual(0, result['extra_calls'])
            self.assertEqual(3, result['matched_prefix'])
            self.assertEqual(1.0, result['progress'])

    def test_progress_reward_distinguishes_correct_prefix_from_wrong_action(self):
        with tempfile.TemporaryDirectory(prefix='hard_reward_', dir=ROOT / 'work') as folder:
            tasks, train, _ = build(Path(folder) / 'protocol')
            task = next(t for t in tasks if t['split'] == 'train')
            gold = train[task['task_id']]
            prefix = SequenceEnv(task, gold, Path(folder) / 'prefix')
            prefix.step(gold['plan'][0])
            prefix.step(gold['plan'][1])
            prefix.step('stop')
            prefix_result = prefix.result()
            wrong = SequenceEnv(task, gold, Path(folder) / 'wrong')
            wrong.step('profile_schema')
            wrong.step('stop')
            wrong_result = wrong.result()
            self.assertFalse(prefix_result['passed'])
            self.assertFalse(wrong_result['passed'])
            self.assertEqual(2, prefix_result['matched_prefix'])
            self.assertEqual(0, wrong_result['matched_prefix'])
            self.assertGreater(prefix_result['reward'], wrong_result['reward'])


if __name__ == '__main__':
    unittest.main()
