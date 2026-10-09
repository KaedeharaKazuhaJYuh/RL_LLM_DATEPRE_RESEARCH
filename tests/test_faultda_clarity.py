import copy
import json
from pathlib import Path
import tempfile
import unittest

from faultda_bench.clarity.tasks import build, clarify, write_json, load
from faultda_bench.clarity.compare import summaries
from faultda_bench.semantic.tasks import load as load_v1
from faultda_bench.semantic.environment import SemanticEnv
from faultda_bench.semantic.oracle import record_correct, evaluate
from faultda_bench.semantic.policies import choose


class ClarityAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.serial = 0

    def env(self, task, **kwargs):
        self.serial += 1
        return SemanticEnv(task, self.root / str(self.serial), **kwargs)

    def test_clarity_changes_only_two_public_contract_fields(self):
        for task in load_v1():
            before = copy.deepcopy(task)
            after = clarify(task)
            self.assertEqual(task, before)
            altered = copy.deepcopy(after)
            altered['contract'].pop('input_binding')
            altered['contract']['output'] = task['contract']['output']
            self.assertEqual(altered, before)
            self.assertIn(task['contract']['column'], after['contract']['input_binding']['value'])

    def test_clarity_preserves_tool_effects_and_oracle_for_all_conditions(self):
        for task in load_v1():
            for c in (False, True):
                for s in (False, True):
                    a = self.env(task, commit_fault=c, semantic_fault=s)
                    b = self.env(clarify(task), commit_fault=c, semantic_fault=s)
                    self.assertEqual(a.records(), b.records())
                    for action in ('inspect', 'inputs', 'catalog', 'stop'):
                        a.step(action)
                        b.step(action)
                        self.assertEqual(a.history[-1], b.history[-1])
                    self.assertEqual(evaluate(a), evaluate(b))

    def test_sources_are_crossed_with_intents_and_natural_keys(self):
        tasks = build()['tasks']
        self.assertEqual(tasks, load())
        self.assertEqual(len(tasks), 24)
        self.assertEqual(len({t['source_id'] for t in tasks}), 3)
        self.assertEqual(len({t['id'] for t in tasks}), 24)
        for source in {t['source_id'] for t in tasks}:
            for family in ('group', 'version'):
                subset = [t for t in tasks if t['source_id'] == source and t['contract']['family'] == family]
                self.assertEqual(len(subset), 4)
        self.assertNotIn('window', {t['contract']['family'] for t in tasks})
        for t in tasks:
            self.assertEqual(len(t['selection_indices']), 8)
            self.assertIn('source column', t['contract']['input_binding']['key'])
            self.assertEqual(len(t['dimension']), len({r['key'] for r in t['versions']['v1']}) + 1)

    def test_every_new_semantic_fault_is_detectable_and_repairable(self):
        for task in load():
            normal = self.env(task)
            self.assertTrue(record_correct(normal.records()[0], normal.task))
            for evidence in ('E0', 'E1'):
                env = self.env(task, commit_fault=True, semantic_fault=True, evidence=evidence, budget=4)
                self.assertFalse(record_correct(env.records()[0], env.task), task['id'])
                while not env.terminal:
                    step = choose(env.observation(), 'static_semantic')
                    env.step(step['action'], step.get('params'))
                self.assertTrue(evaluate(env)['safe_complete'], task['id'])

    def test_json_bytes_are_lf_and_results_cannot_be_overwritten(self):
        path = self.root / 'evidence.json'
        write_json(path, {'name': '中文', 'items': [1, 2]})
        original = path.read_bytes()
        self.assertNotIn(b'\r', original)
        with self.assertRaises(FileExistsError):
            write_json(path, {'replacement': True})
        self.assertEqual(path.read_bytes(), original)

    def test_paired_summary_rejects_duplicate_and_missing_arms(self):
        base = {'task_id': 'one', 'commit_fault': False, 'semantic_fault': False,
                'terminal_correct': True, 'safe_complete': True, 'terminal': 'stop',
                'false_completion': False, 'api_calls': []}
        a = {**base, 'arm': 'original', 'contract_complete': False}
        b = {**base, 'arm': 'explicit', 'contract_complete': True}
        self.assertEqual(summaries([a, b])['paired_completion']['explicit_only'], 1)
        with self.assertRaises(ValueError):
            summaries([a])
        with self.assertRaises(ValueError):
            summaries([a, a, b])

    def test_published_evidence_diagnosis_is_recomputable(self):
        from faultda_bench.clarity.diagnose import diagnose
        from faultda_bench.semantic.tasks import ROOT
        report = ROOT / 'reports/clarity_v2_comparison.json'
        expected = json.loads((ROOT / 'reports/clarity_v2_diagnosis.json').read_text(encoding='utf-8'))
        self.assertEqual(diagnose(report), expected)
