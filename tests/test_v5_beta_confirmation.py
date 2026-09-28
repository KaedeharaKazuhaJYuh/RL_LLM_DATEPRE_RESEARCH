import json
import unittest

from research.io import ROOT, digest


class ConfirmationProtocolTests(unittest.TestCase):
    def test_train_and_confirmation_sources_are_separate(self):
        train = ROOT / 'tasks/v5/beta_curriculum_v1'
        confirm = ROOT / 'tasks/v5/beta_confirmation_v1'
        train_tasks = json.loads((train / 'tasks.json').read_text(encoding='utf-8'))
        test_tasks = json.loads((confirm / 'tasks.json').read_text(encoding='utf-8'))
        train_manifest = json.loads((train / 'manifest.json').read_text(encoding='utf-8'))
        test_manifest = json.loads((confirm / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(train_tasks), 96)
        self.assertEqual(len(test_tasks), 12)
        self.assertFalse({t['source_id'] for t in train_tasks} &
                         {t['source_id'] for t in test_tasks})
        self.assertEqual(json.loads((train / 'dev_oracle.json').read_text(encoding='utf-8')), {})
        self.assertEqual(json.loads((confirm / 'train_oracle.json').read_text(encoding='utf-8')), {})
        for root, manifest in ((train, train_manifest), (confirm, test_manifest)):
            for name in ('tasks', 'train_oracle', 'dev_oracle'):
                self.assertEqual(digest(root / f'{name}.json'), manifest[f'{name}_sha256'])
        for task in test_tasks:
            self.assertEqual(digest(ROOT / task['dataset']['uri']), task['dataset']['sha256'])


if __name__ == '__main__':
    unittest.main()
