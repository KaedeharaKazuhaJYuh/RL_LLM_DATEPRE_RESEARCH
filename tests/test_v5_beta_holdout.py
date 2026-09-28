import json
import unittest

from research.io import ROOT, digest


class BetaHoldoutTests(unittest.TestCase):
    def test_frozen_protocol_is_source_only_and_reachable(self):
        folder = ROOT / 'tasks/v5/beta_holdout_v1'
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        tasks = json.loads((folder / 'tasks.json').read_text(encoding='utf-8'))
        train = json.loads((folder / 'train_oracle.json').read_text(encoding='utf-8'))
        dev = json.loads((folder / 'dev_oracle.json').read_text(encoding='utf-8'))
        self.assertEqual(train, {})
        self.assertEqual(len(tasks), 12)
        self.assertEqual({task['task_id'] for task in tasks}, set(dev))
        self.assertEqual({task['source_id'] for task in tasks},
                         {'uci_banknote', 'uci_occupancy'})
        for name in ('tasks', 'train_oracle', 'dev_oracle'):
            self.assertEqual(digest(folder / f'{name}.json'), manifest[f'{name}_sha256'])
        for task in tasks:
            self.assertEqual(task['split'], 'dev')
            self.assertEqual(digest(ROOT / task['dataset']['uri']), task['dataset']['sha256'])
            self.assertEqual(len(dev[task['task_id']]['plan']), 2)


if __name__ == '__main__':
    unittest.main()
