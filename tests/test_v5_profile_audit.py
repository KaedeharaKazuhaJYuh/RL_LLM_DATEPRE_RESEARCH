import json
import tempfile
import unittest
from pathlib import Path

from research.v5_profile_audit import run
from research.stage_profile import StageProfile


class ProfileAuditTests(unittest.TestCase):
    def test_device_sync_wraps_phase_even_on_failure(self):
        calls = []
        profile = StageProfile(synchronize=lambda: calls.append('sync'))
        with self.assertRaisesRegex(RuntimeError, 'stop'):
            with profile.measure('phase'):
                raise RuntimeError('stop')
        self.assertEqual(calls, ['sync', 'sync'])
        self.assertEqual(profile.stages['phase']['calls'], 1)

    def test_repeated_profiles_require_comparable_workloads(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            paths = [root / f'profile_{i}.json' for i in range(3)]
            for i, path in enumerate(paths):
                path.write_text(json.dumps({
                    'operation': 'sft_train', 'device_synchronized': True,
                    'wall_seconds': 3 + i,
                    'stages': {'train_loop': {'calls': 1, 'seconds': 2 + i}},
                    'metadata': {'steps_sha256': 'fixed', 'max_steps': 2,
                                 'model': 'local', 'peak_cuda_allocated_bytes': 100 + i}}))
            summary = run(paths, root / 'audit.json')
            self.assertEqual(summary['wall_seconds']['median'], 4)
            self.assertEqual(summary['wall_seconds']['p95_nearest_rank'], 5)
            self.assertTrue(summary['nested_stages_must_not_be_summed'])
            paths[2].write_text(paths[2].read_text().replace('"max_steps": 2', '"max_steps": 3'))
            with self.assertRaisesRegex(ValueError, 'workload metadata differs'):
                run(paths, root / 'invalid.json')


if __name__ == '__main__':
    unittest.main()
