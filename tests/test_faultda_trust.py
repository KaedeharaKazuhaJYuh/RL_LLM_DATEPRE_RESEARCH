import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from faultda_bench.evidence.core import tasks
from faultda_bench.semantic.compute import parameters
from faultda_bench.semantic.oracle import record_correct
from faultda_bench.trust.environment import ComputeFaultEnv
from faultda_bench.trust.suite import execute, run
from faultda_bench.trust.verify import verify


class TrustTests(unittest.TestCase):
    def test_hidden_mode_and_same_public_preexecution_observation(self):
        with tempfile.TemporaryDirectory() as folder:
            observations = []
            for mode in ('healthy', 'stage_only', 'shared_compute'):
                env = ComputeFaultEnv(tasks()[0], Path(folder) / mode, mode=mode, evidence='E1', budget=3)
                observations.append(env.observation())
            self.assertTrue(all(o == observations[0] for o in observations))
            self.assertNotIn('mode', observations[0])

    def test_bad_numbers_are_real_staged_file_with_valid_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            task = tasks()[0]
            env = ComputeFaultEnv(task, Path(folder) / 'env', mode='shared_compute', evidence='E1', budget=3)
            env.step('stage', parameters(task['contract'], task['catalog']))
            path, checksum = env.stages['1']
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), checksum)
            record = json.loads(path.read_text())
            self.assertFalse(record_correct(record, env.task))
            self.assertEqual(record['output'], env.records()[0]['output'])

    def test_shared_error_agreement_false_completion_and_guard_escalation(self):
        with tempfile.TemporaryDirectory() as folder:
            for i, task in enumerate(tasks()):
                for arm in ('stage_reference', 'read_reference', 'guarded_read'):
                    cell = dict(task_id=task['id'], evidence='E1', budget=3, mode='shared_compute', arm=arm)
                    row = execute(task, Path(folder) / f'{i}-{arm}', cell)
                    self.assertEqual(row['false_completion'], arm != 'guarded_read')
                    self.assertEqual(row['agent_wrong_publications'], int(arm == 'read_reference'))
                    if arm == 'guarded_read':
                        self.assertTrue(row['safe_escalation'])
                        self.assertFalse(row['terminal_correct'])

    def test_stage_only_correct_report_preserved_by_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = []
            for arm in ('stage_reference', 'guarded_read'):
                cell = dict(task_id=tasks()[0]['id'], evidence='E1', budget=3, mode='stage_only', arm=arm)
                rows.append(execute(tasks()[0], Path(folder) / arm, cell))
            self.assertEqual([r['safe_complete'] for r in rows], [False, True])
            self.assertEqual([r['agent_wrong_publications'] for r in rows], [1, 0])

    def test_full_replay_and_rehashed_feedback_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'result.json'
            run(path)
            self.assertEqual(verify(path)['executions'], 144)
            result = json.loads(path.read_text())
            tp = path.with_suffix('.jsonl')
            rows = [json.loads(line) for line in tp.read_text().splitlines()]
            rows[0]['trace'][0]['response']['revision'] = 999
            data = ('\n'.join(json.dumps(r) for r in rows) + '\n').encode()
            tp.write_bytes(data)
            result['trace_sha256'] = hashlib.sha256(data).hexdigest()
            path.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError, 'full effect replay'):
                verify(path)

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'result.json'
            path.write_text('original')
            with self.assertRaises(FileExistsError):
                run(path)
            self.assertEqual(path.read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
