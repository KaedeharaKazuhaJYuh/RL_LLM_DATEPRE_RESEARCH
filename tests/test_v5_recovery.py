import tempfile
import unittest
from pathlib import Path

from agent.native_rolling import rolling_mean
from research.v5_recovery_env import RecoveryEnv, MODES, expert_action
from research.v5_recovery_protocol import load


class RecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks, cls.oracle, _ = load()

    def test_expert_all_sources_families_and_faults(self):
        tasks = [t for t in self.tasks if t['split'] == 'dev']
        with tempfile.TemporaryDirectory() as folder:
            for index, (task, mode) in enumerate((t, m) for t in tasks for m in MODES):
                env = RecoveryEnv(task, self.oracle[task['task_id']], Path(folder)/str(index), mode)
                while not env.done:
                    env.step(expert_action(env.observation()))
                self.assertTrue(env.result()['passed'], (task['task_id'], mode))

    def test_faults_observationally_identical_before_inspection(self):
        task = self.tasks[0]
        with tempfile.TemporaryDirectory() as folder:
            envs = [RecoveryEnv(task, self.oracle[task['task_id']], Path(folder)/m, m)
                    for m in MODES[1:]]
            self.assertEqual(envs[0].observation(), envs[1].observation())
            self.assertEqual(envs[1].observation(), envs[2].observation())
            for env in envs:
                env.step('inspect_commit')
            self.assertEqual(['absent', 'committed', 'absent'], [e.known for e in envs])

    def test_fork_isolation_duplicate_and_receipt_corruption(self):
        task = self.tasks[0]
        with tempfile.TemporaryDirectory() as folder:
            env = RecoveryEnv(task, self.oracle[task['task_id']], Path(folder)/'root', 'after_commit')
            before = env.state_digest()
            branch = env.fork(Path(folder)/'branch')
            branch.step('retry')
            branch.step('continue')
            self.assertTrue(branch.result()['duplicate_commit'])
            self.assertFalse(branch.result()['passed'])
            self.assertEqual(before, env.state_digest())
            env.current.write_text('corrupt', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'receipt'):
                env.step('inspect_commit')

    def test_native_invalid_window_is_rejected_before_ffi(self):
        for window in (-1, 0, True, 1.5):
            with self.subTest(window=window), self.assertRaises(ValueError):
                rolling_mean([1, 2], window)


if __name__ == '__main__':
    unittest.main()
