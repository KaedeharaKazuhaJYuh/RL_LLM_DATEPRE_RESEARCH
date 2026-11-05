"""Terminal integrity controls, without protected native data or native scoring."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from research.reliability_reset import terminal_binding185 as binding


class TerminalBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        arms = []
        for name in binding.native_replay185.ARMS:
            directory = f'outputs/{name}/task'
            relative = directory + '/dbs/state.jsonl'
            path = self.root / relative
            path.parent.mkdir(parents=True)
            path.write_bytes(b'software control, not a native task\n')
            files = [{'relative_path': relative, 'bytes': path.stat().st_size,
                      'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]
            tree = hashlib.sha256(json.dumps(files, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            arms.append({'arm': name, 'task_directory': directory, 'files': files, 'tree_sha256': tree})
        self.manifest = self.root / 'binding.json'
        self.manifest.write_text(json.dumps({'date': '2026-10-27', 'arms': arms}), encoding='utf-8')
        self.second = self.root / arms[1]['files'][0]['relative_path']

    def test_original_files_pass_without_starting_a_native_process(self):
        with patch.object(binding.native_replay185, 'replay') as native:
            result = binding.verify(self.root, self.manifest)
        native.assert_not_called()
        self.assertEqual(result['binding_date'], '2026-10-27')
        self.assertEqual(result['verified_task_output_files'], 2)
        self.assertTrue(result['matches_terminal_binding'])
        self.assertEqual(result['new_native_scorer_calls'], 0)

    def test_changed_terminal_bytes_abort_before_replay_even_if_score_would_match(self):
        self.second.write_bytes(b'different state with potentially identical test outcome\n')
        with patch.object(binding.native_replay185, 'replay') as native:
            with self.assertRaisesRegex(ValueError, 'file digest'):
                binding.replay(Path('python'), self.root, self.manifest)
        native.assert_not_called()

    def test_missing_or_extra_terminal_files_are_rejected(self):
        extra = self.second.parent / 'extra.jsonl'
        extra.write_bytes(b'extra')
        with self.assertRaisesRegex(ValueError, 'membership'):
            binding.verify(self.root, self.manifest)
        extra.unlink()
        self.second.unlink()
        with self.assertRaisesRegex(ValueError, 'membership'):
            binding.verify(self.root, self.manifest)

    def test_successful_binding_keeps_the_existing_input_source_and_score_checks(self):
        with patch.object(binding.native_replay185, 'replay', return_value={'matches_recorded_scores': True}) as native:
            result = binding.replay(Path('python'), self.root, self.manifest)
        native.assert_called_once_with(Path('python'), self.root)
        self.assertTrue(result['native_replay']['matches_recorded_scores'])


if __name__ == '__main__':
    unittest.main()
