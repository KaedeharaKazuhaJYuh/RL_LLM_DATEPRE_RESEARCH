import json
import tempfile
import unittest
from pathlib import Path

from research.v5_batch_audit import audit


class BatchAuditTests(unittest.TestCase):
    def test_exact_outputs_required_and_mismatch_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            record = {'task_id': 't', 'source_id': 's', 'novelty': 'seen', 'fault': False,
                      'passed': True, 'reward': 0.9,
                      'steps': [{'action': 'stop', 'raw': '{"action":"stop"}',
                                 'parse_error': None}]}
            base = {'protocol_sha256': 'p', 'model': 'm', 'adapter': 'a',
                    'episodes': 1, 'records': [record]}
            meta = {'protocol_sha256': 'p', 'model': 'm', 'adapter': 'a', 'episodes': 1,
                    'peak_cuda_allocated_bytes': 100}
            timing = {'operation': 'greedy_eval', 'device_synchronized': True,
                      'wall_seconds': 10, 'metadata': {**meta, 'batch_size': 1}}
            files = [root / name for name in ('serial.json', 'serial_profile.json',
                                               'batched.json', 'batched_profile.json')]
            inputs = [base, timing, {**base, 'batch_size': 4},
                      {**timing, 'wall_seconds': 5,
                       'metadata': {**meta, 'batch_size': 4}}]
            for path, value in zip(files, inputs):
                path.write_text(json.dumps(value), encoding='utf-8')
            report = audit(*files, root / 'audit.json')
            self.assertEqual(report['exact_episode_matches'], 1)
            self.assertEqual(report['wall_speedup'], 2)
            inputs[2]['records'] = [{**record, 'steps': [{**record['steps'][0], 'raw': 'different'}]}]
            files[2].write_text(json.dumps(inputs[2]), encoding='utf-8')
            report = audit(*files, root / 'audit2.json')
            self.assertEqual(report['exact_episode_matches'], 0)
            self.assertFalse(report['mismatches'][0]['raw_equal'])


if __name__ == '__main__':
    unittest.main()
