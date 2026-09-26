import json
import tempfile
import unittest
from pathlib import Path

from research.io import ROOT
from research.v4_llm_composition_protocol import build


class CompositionProtocolTests(unittest.TestCase):
    def test_train_extension_preserves_dev_and_held_out_triples(self):
        parent = ROOT / 'tasks/v4/llm_hard_v1'
        with tempfile.TemporaryDirectory(prefix='composition_', dir=ROOT / 'work') as folder:
            out = Path(folder) / 'protocol'
            manifest = build(out, parent)
            old = json.loads((parent / 'tasks.json').read_text(encoding='utf-8'))
            new = json.loads((out / 'tasks.json').read_text(encoding='utf-8'))
            train = json.loads((out / 'train_oracle.json').read_text(encoding='utf-8'))
            dev = json.loads((out / 'dev_oracle.json').read_text(encoding='utf-8'))
            self.assertEqual([row for row in old if row['split'] == 'dev'],
                             [row for row in new if row['split'] == 'dev'])
            self.assertEqual(192, manifest['train_tasks'])
            self.assertEqual(48, manifest['dev_tasks'])
            self.assertEqual(4, len(manifest['added_train_families']))
            self.assertEqual(manifest['dev_oracle_sha256'],
                             manifest['parent_dev_oracle_sha256'])
            held_out = {tuple(plan) for plan in manifest['held_out_dev_families']}
            self.assertFalse({tuple(row['plan']) for row in train.values()} & held_out)
            self.assertEqual(set(dev), {row['task_id'] for row in old if row['split'] == 'dev'})


if __name__ == '__main__':
    unittest.main()
