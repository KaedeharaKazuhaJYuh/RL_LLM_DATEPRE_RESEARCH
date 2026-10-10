import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from faultda_bench.decision.core import prepare, public_input, judgement_reference, score_judgement, transition
from faultda_bench.decision.verify import verify
from faultda_bench.evidence.core import tasks
from faultda_bench.semantic.compute import calculate, parameters
from faultda_bench.semantic.oracle import evaluate


class DecisionTests(unittest.TestCase):
    def test_public_calculation_matches_private_reference(self):
        with tempfile.TemporaryDirectory() as folder:
            for task in tasks():
                for state in ('committed_correct', 'committed_wrong'):
                    env = prepare(task, Path(folder) / (task['id'] + state), state)
                    public = env.observation()
                    data = public['history'][-1]['response']
                    params = parameters(public['contract'], data['catalog'])
                    expected = judgement_reference(env)
                    answer = {'expected_version': params['version'], 'expected_output': calculate(
                        data['versions'][params['version']], data['dimension'], public['contract'], params),
                        'observed_report_correct': state == 'committed_correct'}
                    self.assertTrue(score_judgement(answer, expected)['exact'])

    def test_advice_is_public_only_and_does_not_execute(self):
        with tempfile.TemporaryDirectory() as folder:
            env = prepare(tasks()[0], Path(folder) / 'env', 'committed_wrong')
            before, public = evaluate(env), env.observation()
            original = copy.deepcopy(public)
            with patch('faultda_bench.decision.core.reference', side_effect=AssertionError('private access')):
                wire = public_input(public, 'advice')
            self.assertEqual(wire.pop('optional_rule_advice')['decision']['action'], 'stage')
            self.assertEqual(wire, original)
            self.assertEqual(public, original)
            self.assertEqual(evaluate(env), before)

    def test_wrong_publication_after_correct_is_counted(self):
        with tempfile.TemporaryDirectory() as folder:
            task = tasks()[0]
            env = prepare(task, Path(folder) / 'env', 'committed_correct')
            params = parameters(task['contract'], task['catalog'])
            params['deduplicate_keys'] = False
            transition(env, {'action': 'stage', 'params': params})
            stage = env.history[-1]['response']['stage_id']
            result = transition(env, {'action': 'publish', 'params': {
                'stage_id': stage, 'request_id': 'bad', 'expected_revision': 1, 'mode': 'replace'}})
            self.assertTrue(result['regression'])
            transition(env, {'action': 'escalate'})
            self.assertTrue(evaluate(env)['forbidden_effect'])

    def test_judgement_rejects_coercion_and_extra_keys(self):
        expected = {'expected_version': 'v1', 'expected_output': {'total': '1'}, 'observed_report_correct': True}
        good = {**expected, 'expected_output': {'total': 1.0}}
        self.assertTrue(score_judgement(good, expected)['exact'])
        for bad in ({**good, 'expected_output': {'total': True}},
                    {**good, 'observed_report_correct': 1}, {**good, 'extra': 1},
                    {**good, 'expected_output': {'total': float('nan')}}, None):
            self.assertFalse(score_judgement(bad, expected)['exact'])

    def test_frozen_run_replays_and_rejects_tampered_summary(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'run.json'
            subprocess.run([sys.executable, '-m', 'faultda_bench.decision.run', '--output', str(path)],
                           check=True, stdout=subprocess.DEVNULL)
            self.assertEqual(verify(path)['episodes'], 36)
            result = json.loads(path.read_text(encoding='utf-8'))
            result['summary'][0]['safe_complete'] += 1
            path.write_text(json.dumps(result), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'summary'):
                verify(path)
