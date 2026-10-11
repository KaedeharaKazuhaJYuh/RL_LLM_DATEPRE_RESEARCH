import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from faultda_bench.evidence.core import tasks
from faultda_bench.surface.policy import matches
from faultda_bench.surface.suite import execute, run
from faultda_bench.surface.verify import verify


class SurfaceTests(unittest.TestCase):
    def test_staging_evidence_succeeds_with_two_reads_in_every_family(self):
        with tempfile.TemporaryDirectory() as folder:
            for i, task in enumerate(tasks()):
                for arm in ('read_reference', 'stage_reference'):
                    cell = dict(task_id=task['id'], evidence='E1', budget=2,
                                commit_fault=True, semantic_fault=True, arm=arm)
                    row = execute(task, Path(folder) / f'{i}-{arm}', cell)
                    self.assertEqual(row['safe_complete'], arm == 'stage_reference')
                    self.assertEqual(row['cost']['checks'], 2)
                    if arm == 'stage_reference':
                        self.assertNotIn('inputs', [s['action'] for s in row['trace']])
                        self.assertEqual(row['cost']['mutations'], 3)
                        self.assertEqual(row['agent_wrong_publications'], 0)

    def test_correct_report_exposes_write_tradeoff(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = []
            for arm in ('read_reference', 'stage_reference'):
                cell = dict(task_id=tasks()[0]['id'], evidence='E1', budget=3,
                            commit_fault=False, semantic_fault=False, arm=arm)
                rows.append(execute(tasks()[0], Path(folder) / arm, cell))
            self.assertTrue(all(r['safe_complete'] for r in rows))
            self.assertEqual([r['cost']['checks'] for r in rows], [3, 2])
            self.assertEqual([r['cost']['mutations'] for r in rows], [1, 2])

    def test_candidate_match_binds_hash_version_and_numeric_type(self):
        candidate = dict(version='v1', input_sha256='bound', output={'total': 1.0})
        self.assertTrue(matches(candidate, candidate))
        for changed in (dict(candidate, version='v2'), dict(candidate, input_sha256='other'),
                        dict(candidate, output={'total': True}), dict(candidate, output={'total': float('nan')})):
            self.assertFalse(matches(changed, candidate))

    def test_full_replay_and_rehashed_ledger_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'result.json'
            run(path)
            self.assertEqual(verify(path)['executions'], 144)
            result = json.loads(path.read_text())
            tp = path.with_suffix('.jsonl')
            rows = [json.loads(line) for line in tp.read_text().splitlines()]
            rows[0]['private_records'][0]['output'] = {'total': 999}
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
