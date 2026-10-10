"""Explicit repair -> regression -> repair fixtures under the frozen write budget."""
import copy
from pathlib import Path
import tempfile
import unittest

from faultda_bench.evidence.core import tasks
from faultda_bench.semantic.compute import parameters
from faultda_bench.semantic.environment import SemanticEnv
from faultda_bench.semantic.oracle import evaluate


def run_chain(task, folder, reuse_candidate):
    env = SemanticEnv(task, folder, commit_fault=False, semantic_fault=True, evidence='E0', budget=6)
    env.step('inspect')
    public = env.history[-1]['response']
    revision = public['revision']
    good = parameters(task['contract'], public['catalog'])
    bad = copy.deepcopy(good)
    if task['contract']['family'] == 'group':
        bad['deduplicate_keys'] = False
    elif task['contract']['family'] == 'window':
        bad['closed'] = 'both'
    else:
        bad['version'] = 'v2' if good['version'] == 'v1' else 'v1'
    first_stage = None
    states = []
    for index, params in enumerate((good, bad, good)):
        if index == 2 and reuse_candidate:
            stage = first_stage
        else:
            env.step('stage', params)
            response = env.history[-1]['response']
            if not response.get('ok'):
                break
            stage = response['stage_id']
            if index == 0:
                first_stage = stage
        env.step('publish', {'stage_id': stage, 'request_id': 'chain-' + str(index),
                             'expected_revision': revision, 'mode': 'replace'})
        response = env.history[-1]['response']
        states.append(evaluate(env)['terminal_correct'])
        if not response.get('ok'):
            break
        revision = response['revision']
    if not env.terminal:
        env.step('stop')
    return env, states


class RegressionChainTests(unittest.TestCase):
    def test_repair_regress_repair_preserves_wrong_publication(self):
        with tempfile.TemporaryDirectory() as folder:
            for task in tasks():
                with self.subTest(task=task['id']):
                    env, states = run_chain(task, Path(folder) / task['id'], True)
                    result = evaluate(env)
                    self.assertEqual(states, [True, False, True])
                    self.assertTrue(result['contract_complete'])
                    self.assertFalse(result['safe_complete'])
                    self.assertTrue(result['forbidden_effect'])
                    self.assertEqual(result['agent_wrong_publications'], 1)
                    self.assertEqual(result['historical_wrong_publications'], 2)
                    self.assertEqual(result['cost']['mutations'], 6)
                    self.assertEqual([e['actor'] for e in result['private_effects']],
                                     ['environment', 'agent', 'agent', 'agent'])
                    self.assertTrue(result['source_intact'])

    def test_three_fresh_stages_exceed_budget_without_final_effect(self):
        with tempfile.TemporaryDirectory() as folder:
            for task in tasks():
                with self.subTest(task=task['id']):
                    env, states = run_chain(task, Path(folder) / task['id'], False)
                    result = evaluate(env)
                    self.assertEqual(states, [True, False, False])
                    self.assertEqual(result['terminal'], 'budget_exceeded')
                    self.assertEqual(result['cost']['mutations'], 7)
                    self.assertEqual(len(result['private_effects']), 3)
                    self.assertEqual(result['private_records'][-1]['revision'], 3)
                    self.assertFalse(result['terminal_correct'])
                    self.assertEqual(result['agent_wrong_publications'], 1)
                    self.assertEqual(env.history[-1]['response']['error'], 'budget exceeded; no effect applied')
