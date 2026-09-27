"""Check the frozen source-held-out closing protocol without network access."""
import json
import unittest

from research.io import ROOT, digest, read_table
from research.v3_real_data import SOURCES as V3_SOURCES


class FinalHoldoutTest(unittest.TestCase):
    def test_frozen_protocol_integrity_and_source_separation(self):
        folder = ROOT / 'tasks/v4/final_holdout_v1'
        manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
        tasks = json.loads((folder / 'tasks.json').read_text(encoding='utf-8'))
        oracle = json.loads((folder / 'dev_oracle.json').read_text(encoding='utf-8'))
        old_urls = {value['url'] for value in V3_SOURCES.values()}
        old_manifest = json.loads((ROOT / 'tasks/v4/real_csv_v1/manifest.json').read_text(encoding='utf-8'))
        old_urls.update(value['upstream_url'] for value in old_manifest['sources'].values())
        self.assertTrue(manifest['external_test'])
        self.assertEqual(len(tasks), 12)
        self.assertEqual(set(oracle), {task['task_id'] for task in tasks})
        self.assertEqual({spec['license'] for spec in manifest['sources'].values()}, {'CC BY 4.0'})
        self.assertFalse({spec['upstream_url'] for spec in manifest['sources'].values()} & old_urls)
        for filename, field in [('tasks.json', 'tasks_sha256'),
                                ('dev_oracle.json', 'dev_oracle_sha256'),
                                ('train_oracle.json', 'train_oracle_sha256')]:
            self.assertEqual(digest(folder / filename), manifest[field])
        for task in tasks:
            dataset = task['dataset']
            self.assertEqual(digest(ROOT / dataset['uri']), dataset['sha256'])
            columns, rows = read_table(ROOT / dataset['uri'])
            self.assertEqual(columns, dataset['columns'])
            self.assertEqual(len(rows), 240)
            self.assertTrue(task['constraints']['isolated_tools'])
        self.assertEqual({(task['source_id'], task['pair_family'], task['paraphrase_id'])
                          for task in tasks},
                         {(source, family, paraphrase) for source in ('uci_forest', 'uci_rice')
                          for family in range(3) for paraphrase in (0, 1)})


if __name__ == '__main__':
    unittest.main()
