import unittest

from research.v5_beta_audit import FAULTS, _indexed


class BetaAuditTests(unittest.TestCase):
    def test_index_requires_every_task_condition_once(self):
        records = [{'task_id': task, 'fault_kind': fault, 'passed': True}
                   for task in ('a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l')
                   for fault in FAULTS]
        result = {'episodes': 48, 'fault_modes': list(FAULTS), 'greedy': True,
                  'passed': 48, 'records': records}
        self.assertEqual(len(_indexed(result, {r['task_id'] for r in records})), 48)
        result['records'] = [*records[:-1], records[0]]
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            _indexed(result, {r['task_id'] for r in records})


if __name__ == '__main__':
    unittest.main()
