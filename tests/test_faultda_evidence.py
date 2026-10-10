import copy
from pathlib import Path
import tempfile
import unittest

from faultda_bench.evidence.core import STATES, tasks, prepare, present, restore, observed_facts, fact_score
from faultda_bench.semantic.oracle import evaluate
from faultda_bench.semantic.policies import choose


class EvidenceTests(unittest.TestCase):
    def test_lossless_public_presentation(self):
        with tempfile.TemporaryDirectory() as folder:
            for state in STATES:
                env = prepare(tasks()[0], Path(folder) / state, state)
                observation = env.observation()
                before = copy.deepcopy(observation)
                self.assertEqual(restore(present(observation, 'indexed')), observation)
                self.assertEqual(before, observation)
                self.assertEqual(observed_facts(observation), observed_facts(present(observation, 'indexed')))

    def test_stale_evidence_is_not_hidden_truth(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = prepare(tasks()[0], Path(folder) / 'candidate', 'candidate')
            conflict = prepare(tasks()[0], Path(folder) / 'conflict', 'conflict')
            self.assertEqual(candidate.observation(), conflict.observation())
            self.assertEqual(observed_facts(conflict.observation())['observed_revision'], 1)
            self.assertEqual(conflict.records()[-1]['revision'], 2)
            stage_id = observed_facts(conflict.observation())['stage_id']
            conflict.step('publish', {'stage_id': stage_id, 'request_id': 'test', 'expected_revision': 1, 'mode': 'replace'})
            self.assertFalse(conflict.history[-1]['response']['ok'])
            self.assertIn('inspect state before retry', conflict.history[-1]['response']['error'])
            self.assertEqual(conflict.records()[-1]['revision'], 2)
            candidate.step('publish', {'stage_id': stage_id, 'request_id': 'test', 'expected_revision': 1, 'mode': 'replace'})
            self.assertTrue(candidate.history[-1]['response']['ok'])

    def test_rule_policy_recovers_all_observable_states(self):
        with tempfile.TemporaryDirectory() as folder:
            for task in tasks():
                for state in STATES:
                    env = prepare(task, Path(folder) / (task['id'] + state), state)
                    for _ in range(16):
                        if env.terminal:
                            break
                        decision = choose(env.observation(), 'task_semantic')
                        env.step(decision['action'], decision.get('params'))
                    result = evaluate(env)
                    self.assertTrue(result['safe_escalation'] if state == 'opaque' else result['safe_complete'])
                    self.assertFalse(result['forbidden_effect'])

    def test_fact_score_strict_types_and_keys(self):
        with tempfile.TemporaryDirectory() as folder:
            expected = observed_facts(prepare(tasks()[0], Path(folder) / 'env', 'candidate').observation())
            self.assertTrue(fact_score(expected, expected)['exact'])
            self.assertFalse(fact_score({**expected, 'observed_revision': True}, expected)['exact'])
            self.assertFalse(fact_score({**expected, 'extra': None}, expected)['exact'])
            self.assertFalse(fact_score(None, expected)['exact'])

    def test_invalid_index_rejected(self):
        with self.assertRaises(ValueError):
            restore({'events_by_action': {'inspect': [{'position': 1, 'event': {}}]}})
