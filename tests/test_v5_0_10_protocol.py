import json
import unittest

from research.io import ROOT, digest
from research.v5_0_10_model_audit import EVAL_SHA, TRAIN_SHA


class RewriteProtocolTests(unittest.TestCase):
    def test_frozen_source_and_prompt_isolation(self):
        train = ROOT / 'tasks/v5/rewrite_train_v1'
        held = ROOT / 'tasks/v5/rewrite_holdout_v1'
        self.assertEqual(digest(train / 'manifest.json'), TRAIN_SHA)
        self.assertEqual(digest(held / 'manifest.json'), EVAL_SHA)
        training = json.loads((train / 'tasks.json').read_text(encoding='utf-8'))
        evaluation = json.loads((held / 'tasks.json').read_text(encoding='utf-8'))
        self.assertEqual(len(training), 96)
        self.assertEqual(len(evaluation), 6)
        self.assertTrue(all(t['split'] == 'train' for t in training))
        self.assertTrue(all(t['split'] == 'dev' for t in evaluation))
        self.assertFalse({t['source_id'] for t in training} &
                         {t['source_id'] for t in evaluation})
        self.assertFalse({t['prompt'] for t in training} &
                         {t['prompt'] for t in evaluation})
        old = []
        for name in ('beta_curriculum_v1', 'beta_holdout_v1', 'beta_confirmation_v1'):
            path = ROOT / 'tasks/v5' / name / 'tasks.json'
            old.extend(json.loads(path.read_text(encoding='utf-8')))
        self.assertFalse({t['prompt'] for t in evaluation} & {t['prompt'] for t in old})
        self.assertEqual(len({t['dataset']['sha256'] for t in evaluation}), 1)


if __name__ == '__main__':
    unittest.main()
