"""Replay integrity checks only; mocks are not native benchmark observations."""
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from research.reliability_reset import native_replay185 as native


def output(arm, success, passed, failed, num_tests=2):
    return native.SENTINEL + json.dumps(dict(arm=arm, success=success, passed=passed,
                                           failed=failed, num_tests=num_tests))


class NativeReplayIntegrityTests(unittest.TestCase):
    def test_each_arm_requires_its_own_native_subprocess_and_matching_source_binding(self):
        values = [SimpleNamespace(returncode=0, stdout=output('reference', True, 2, 0)),
                  SimpleNamespace(returncode=0, stdout=output('legal_title_exchange', False, 1, 1))]
        with patch.object(native, 'verify_original_inputs') as inputs, \
             patch.object(native.subprocess, 'run', side_effect=values) as run:
            result = native.replay(Path('native-python'), Path('native-root'))
        inputs.assert_called_once()
        self.assertEqual(run.call_count, 2)
        self.assertEqual([call.args[0][-2] for call in run.call_args_list], list(native.ARMS))
        self.assertEqual(run.call_args_list[0].args[0][-1], run.call_args_list[1].args[0][-1])
        self.assertEqual(result['native_score_source_files_verified'], 5)
        self.assertTrue(result['matches_recorded_scores'])

    def test_missing_or_duplicate_score_sentinel_is_rejected(self):
        row = output('reference', True, 2, 0)
        for value in ('', row + '\n' + row):
            with self.assertRaisesRegex(ValueError, 'missing or ambiguous'):
                native.parse_score(value, 'reference')

    def test_wrong_arm_partial_test_suite_and_false_success_are_rejected(self):
        bad = [output('other', True, 2, 0), output('reference', True, 1, 0, 1),
               output('reference', True, 1, 1), output('reference', 1, 2, 0)]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                native.parse_score(value, 'reference')

    def test_input_mismatch_aborts_before_any_native_execution(self):
        with patch.object(native, 'verify_original_inputs', side_effect=ValueError('digest')), \
             patch.object(native.subprocess, 'run') as run:
            with self.assertRaisesRegex(ValueError, 'digest'):
                native.replay(Path('python'), Path('root'))
        run.assert_not_called()

    def test_worker_failure_cannot_become_a_zero_test_success(self):
        with patch.object(native, 'verify_original_inputs'), \
             patch.object(native.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            with self.assertRaisesRegex(RuntimeError, 'worker failed'):
                native.replay(Path('python'), Path('root'))

    def test_same_process_cache_like_false_success_is_rejected(self):
        values = [SimpleNamespace(returncode=0, stdout=output('reference', True, 2, 0)),
                  SimpleNamespace(returncode=0, stdout=output('legal_title_exchange', True, 2, 0))]
        with patch.object(native, 'verify_original_inputs'), \
             patch.object(native.subprocess, 'run', side_effect=values):
            with self.assertRaisesRegex(ValueError, 'differs from frozen'):
                native.replay(Path('python'), Path('root'))


if __name__ == '__main__':
    unittest.main()
