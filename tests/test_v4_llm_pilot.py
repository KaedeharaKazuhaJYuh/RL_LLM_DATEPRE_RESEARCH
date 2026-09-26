import json
import tempfile
import unittest
from pathlib import Path

from experiments.v4_llm_export import model_input, replay
from research.io import ROOT
from research.v4_sequence_env import SequenceEnv


PROTOCOL = ROOT / 'tasks/v4/llm_pilot_v1'


class V4LLMPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = json.loads((PROTOCOL / 'tasks.json').read_text(encoding='utf-8'))
        cls.train_gold = json.loads((PROTOCOL / 'train_oracle.json').read_text(encoding='utf-8'))
        cls.dev_gold = json.loads((PROTOCOL / 'dev_oracle.json').read_text(encoding='utf-8'))

    def test_source_and_composition_disjoint(self):
        train = [x for x in self.tasks if x['split'] == 'train']
        dev = [x for x in self.tasks if x['split'] == 'dev']
        self.assertEqual((len(train), len(dev)), (128, 48))
        self.assertFalse({x['source_id'] for x in train} & {x['source_id'] for x in dev})
        train_pairs = {tuple(g['plan']) for g in self.train_gold.values()}
        unseen = {tuple(self.dev_gold[t['task_id']]['plan']) for t in dev if t['composition_novelty'] == 'unseen_pair'}
        self.assertFalse(train_pairs & unseen)
        self.assertEqual((len(train_pairs), len(unseen)), (8, 4))

    def test_public_input_excludes_oracle_and_fault_retry(self):
        task = self.tasks[0]
        gold = self.train_gold[task['task_id']]
        with tempfile.TemporaryDirectory() as scratch:
            env = SequenceEnv(task, gold, scratch, fault=True)
            public = model_input(task, env.observation())
            self.assertNotIn('plan', json.dumps(public))
            self.assertNotIn('task_id', json.dumps(public))
            steps = replay(task, gold, scratch, fault=True, collect=True)
            self.assertEqual([x['action'] for x in steps], [gold['plan'][0], gold['plan'][0], gold['plan'][1], 'stop'])


if __name__ == '__main__':
    unittest.main()
