import json
import tempfile
import unittest
from pathlib import Path

from experiments.v4_real_fault_audit import run as audit_faults
from research.io import ROOT, digest
from research.v4_real_protocol import SOURCES, build
from research.v4_sequence_env import SequenceEnv


class RealCSVTests(unittest.TestCase):
    def test_frozen_sources_and_paraphrases(self):
        protocol = ROOT / 'tasks/v4/real_csv_v1'
        manifest = json.loads((protocol / 'manifest.json').read_text(encoding='utf-8'))
        tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
        oracle = json.loads((protocol / 'dev_oracle.json').read_text(encoding='utf-8'))
        self.assertEqual(set(SOURCES), set(manifest['sources']))
        self.assertEqual(18, len(tasks))
        self.assertEqual(manifest['tasks_sha256'], digest(protocol / 'tasks.json'))
        self.assertEqual(manifest['dev_oracle_sha256'], digest(protocol / 'dev_oracle.json'))
        self.assertFalse(manifest['external_test'])
        self.assertEqual({0, 1}, {task['paraphrase_id'] for task in tasks})
        for task in tasks:
            self.assertEqual('dev', task['split'])
            self.assertTrue(task['constraints']['isolated_tools'])
            self.assertEqual(task['dataset']['sha256'], digest(ROOT / task['dataset']['uri']))
            mate = next(row for row in tasks if row['source_id'] == task['source_id']
                        and row['pair_family'] == task['pair_family']
                        and row['paraphrase_id'] != task['paraphrase_id'])
            self.assertEqual(oracle[task['task_id']], oracle[mate['task_id']])
            self.assertEqual(task['dataset'], mate['dataset'])

    def test_generator_reproduces_committed_protocol(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as folder:
            target = Path(folder) / 'protocol'
            build(target)
            frozen = ROOT / 'tasks/v4/real_csv_v1'
            for name in ('train_oracle.json', 'dev_oracle.json'):
                self.assertEqual((target / name).read_bytes(), (frozen / name).read_bytes())
            generated_tasks = json.loads((target / 'tasks.json').read_text(encoding='utf-8'))
            frozen_tasks = json.loads((frozen / 'tasks.json').read_text(encoding='utf-8'))
            for generated, original in zip(generated_tasks, frozen_tasks):
                generated['dataset'].pop('uri')
                original['dataset'].pop('uri')
                self.assertEqual(generated, original)
            for source in SOURCES:
                self.assertEqual(digest(target / 'data' / f'{source}.csv'),
                                 digest(frozen / 'data' / f'{source}.csv'))

    def test_timeout_and_partial_write_do_not_enter_committed_state(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as folder:
            result = Path(folder) / 'audit.json'
            summary = audit_faults(ROOT / 'tasks/v4/real_csv_v1', result, limit=1)
            records = json.loads(result.read_text(encoding='utf-8'))['records']
            self.assertEqual(4, summary['passed'])
            self.assertTrue(all(row['input_unchanged'] for row in records))
            self.assertTrue(next(row for row in records if row['fault'] == 'partial_write')
                            ['private_partial_rejected'])

    def test_shared_evaluation_scratch_still_uses_distinct_episode_directories(self):
        protocol = ROOT / 'tasks/v4/real_csv_v1'
        tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
        oracle = json.loads((protocol / 'dev_oracle.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as folder:
            for task in tasks[:2]:
                env = SequenceEnv(task, oracle[task['task_id']], folder)
                if task is tasks[0]:
                    first_directory = env.folder
                else:
                    self.assertNotEqual(first_directory, env.folder)
                for action in [*oracle[task['task_id']]['plan'], 'stop']:
                    env.step(action)
                self.assertTrue(env.result()['passed'])


if __name__ == '__main__':
    unittest.main()
