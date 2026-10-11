import tempfile
import unittest
from pathlib import Path

from faultda_bench.allocation.suite import execute, order, run, summarize
from faultda_bench.allocation.verify import same
from faultda_bench.evidence.core import tasks


class AllocationTests(unittest.TestCase):
    def test_factorial_coverage(self):
        cells = order()
        self.assertEqual(len(cells), 576)
        self.assertEqual(len({tuple(c.values()) for c in cells}), 576)

    def test_common_executor_and_strong_negative_control(self):
        with tempfile.TemporaryDirectory() as folder:
            for i, task in enumerate(tasks()):
                rows = []
                for arm in ('fixed', 'random', 'conditional', 'strong'):
                    cell = dict(task_id=task['id'], evidence='E1', commit_fault=True,
                                semantic_fault=True, budget=3, arm=arm, seed=0)
                    rows.append(execute(task, Path(folder) / f'{i}-{arm}', cell))
                self.assertTrue(all(r['safe_complete'] for r in rows))
                self.assertEqual({r['cost']['checks'] for r in rows}, {3})
                self.assertEqual(summarize(rows)['conditional_minus_strong_safe_completions'], 0)
                a, b = rows[-2:]
                self.assertTrue(same({k: v for k, v in a.items() if k != 'arm'},
                                     {k: v for k, v in b.items() if k != 'arm'}))

    def test_no_padding_or_overbudget_calls(self):
        with tempfile.TemporaryDirectory() as folder:
            task = tasks()[0]
            for budget in (1, 3):
                cell = dict(task_id=task['id'], evidence='E0', commit_fault=False,
                            semantic_fault=False, budget=budget, arm='conditional', seed=0)
                row = execute(task, Path(folder) / str(budget), cell)
                self.assertTrue(row['safe_complete'])
                self.assertEqual(row['cost']['checks'], 1)
                self.assertEqual(row['cost']['mutations'], 1)

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'result.json'
            path.write_text('existing', encoding='utf-8')
            with self.assertRaises(FileExistsError):
                run(path)
            self.assertEqual(path.read_text(), 'existing')

    def test_strict_replay_types(self):
        self.assertFalse(same({'checks': True}, {'checks': 1}))


if __name__ == '__main__':
    unittest.main()
