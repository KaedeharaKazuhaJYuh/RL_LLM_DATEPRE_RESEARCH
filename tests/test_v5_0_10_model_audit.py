import json
import tempfile
import unittest
from pathlib import Path

from research.v5_0_10_model_audit import EVAL_SHA, MODES, indexed_eval


class ModelAuditTests(unittest.TestCase):
    def test_complete_four_fault_grid_and_early_model_stop(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'eval.json'
            adapter = Path(folder) / 'adapter'
            tasks = {f't{i}': {'source_id': 'uci_online_shoppers'} for i in range(6)}
            rows = [{'task_id': task_id, 'source_id': 'uci_online_shoppers',
                     'fault_kind': mode, 'fault': mode != 'none',
                     'injection_applied': False, 'passed': False, 'steps': []}
                    for task_id in tasks for mode in MODES]
            result = {'protocol_sha256': EVAL_SHA, 'episodes': 24,
                      'adapter': str(adapter), 'greedy': True,
                      'fault_modes': list(MODES), 'passed': 0, 'records': rows}
            path.write_text(json.dumps(result), encoding='utf-8')
            self.assertEqual(len(indexed_eval(path, adapter, tasks)), 24)
            result['records'][1]['fault_kind'] = 'none'
            path.write_text(json.dumps(result), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'invalid evaluation episode'):
                indexed_eval(path, adapter, tasks)


if __name__ == '__main__':
    unittest.main()
