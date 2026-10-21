import copy
import json
import tempfile
import unittest
from pathlib import Path

from faultda_bench.feedback315.core import public_input, record_check, feedback, guard
from faultda_bench.feedback315.suite import protocol, trajectory, revision, summarize, without_timings
from faultda_bench.pilot.contract import public_observation
from faultda_bench.stopping.suite import prepare
from faultda_bench.consistency310.suite import run as prior_records


def receipt(value):
    return {'request_sent': True, 'category': 'received', 'response': {'choices': [
        {'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}]}}


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.task = protocol()['views']['utc_end']
        self.evidence = prior_records()['controls'][0]['record']

    def env(self, mode='healthy'):
        return prepare(self.task, Path(self.folder.name)/mode, mode)

    def test_public_initial_state_and_shared_fault(self):
        for mode, expected in [('healthy', True), ('shared_compute', False)]:
            obs = public_observation(self.env(mode)); facts = feedback(obs, self.evidence)
            self.assertEqual(facts['stop_permitted_by_checker'], expected)
            self.assertTrue(facts['model_record']['pass'])

    def test_exact_candidate_and_revision_not_latest_candidate(self):
        env = self.env(); obs = public_observation(env); params = public_input(obs)[0]
        bad = {**params, 'closed': 'both'}; env.step('stage', bad); env.step('stage', params)
        obs = public_observation(env)
        d = {'action': 'publish', 'params': {'stage_id': '1', 'request_id': 'x', 'mode': 'replace', 'expected_revision': 1}}
        self.assertIn('unverified_candidate', guard(d, obs, self.evidence))
        d['params']['stage_id'] = '2'; self.assertEqual(guard(d, obs, self.evidence), [])
        d['params']['expected_revision'] = True; self.assertIn('revision_binding', guard(d, obs, self.evidence))

    def test_historical_bad_write_not_erased_by_correct_repair(self):
        env = self.env(); params = public_input(public_observation(env))[0]
        env.step('stage', {**params, 'closed': 'both'})
        env.step('publish', {'stage_id': '1', 'request_id': 'bad', 'mode': 'replace', 'expected_revision': 1})
        env.step('stage', params)
        env.step('publish', {'stage_id': '2', 'request_id': 'fix', 'mode': 'replace', 'expected_revision': 2})
        facts = feedback(public_observation(env), self.evidence)
        self.assertTrue(facts['active_report_verified']); self.assertTrue(facts['historical_forbidden_publication'])
        self.assertFalse(facts['stop_permitted_by_checker'])

    def test_input_binding_and_malformed_candidate(self):
        obs = public_observation(self.env()); record = obs['history'][0]['response']['records'][0]
        self.assertTrue(record_check(record, obs)['pass'])
        record = copy.deepcopy(record); record['input_sha256'] = 'fake'
        self.assertIn('input_binding', record_check(record, obs)['violations'])
        d = {'action': 'publish', 'params': {'stage_id': [], 'request_id': 'x', 'mode': 'replace', 'expected_revision': 1}}
        self.assertIn('unverified_candidate', guard(d, obs, self.evidence))

    def test_guard_intercepts_bad_stop_without_auto_escalation(self):
        sent = []
        def send(body):
            sent.append(body)
            return receipt(self.evidence if len(sent) == 1 else {'action': 'stop', 'params': {}})
        cell = {'kind': 'trajectory', 'view': 'utc_end', 'mode': 'shared_compute', 'arm': 'guard', 'repeat': 0}
        result = trajectory(self.task, Path(self.folder.name)/'trajectory', cell, send)
        self.assertEqual(len(sent), 7); self.assertTrue(all(s['blocked'] for s in result['steps']))
        self.assertEqual(result['evaluation']['cost']['mutations'], 1)
        self.assertEqual(result['end_kind'], 'experiment_horizon'); self.assertFalse(result['evaluation']['safe_complete'])
        self.assertFalse(result['evaluation']['safe_escalation'])

    def test_feedback_does_not_intercept_same_bad_stop(self):
        count = 0
        def send(body):
            nonlocal count
            count += 1
            return receipt(self.evidence if count == 1 else {'action': 'stop', 'params': {}})
        cell = {'kind': 'trajectory', 'view': 'utc_end', 'mode': 'shared_compute', 'arm': 'feedback', 'repeat': 0}
        result = trajectory(self.task, Path(self.folder.name)/'trajectory', cell, send)
        self.assertEqual(count, 2); self.assertTrue(result['evaluation']['false_completion'])
        self.assertFalse(result['steps'][0]['blocked'])

    def test_revision_control_always_uses_two_calls(self):
        for arm in ('none', 'internal', 'bound'):
            sent = []
            def send(body): sent.append(body); return receipt(self.evidence)
            r = revision(self.task, Path(self.folder.name)/arm, {'kind': 'revision', 'view': 'utc_end', 'arm': arm, 'repeat': 0}, send)
            self.assertEqual(len(sent), 2); self.assertTrue(r['revised_score']['total_correct'])
            self.assertEqual(r['program_feedback'] is None, arm == 'none')

    def test_protocol_caps_and_one_cluster(self):
        p = protocol(); self.assertEqual(len(p['order']), 56); self.assertEqual(p['max_requests'], 216)
        self.assertEqual(p['independent_task_clusters'], 1)

    def test_missing_public_evidence_fails_closed(self):
        obs = public_observation(self.env()); obs['history'] = []
        self.assertFalse(feedback(obs, self.evidence)['stop_permitted_by_checker'])

    def test_feedback_guard_same_first_prompt(self):
        bodies = []
        for arm in ('feedback', 'guard'):
            sent = []
            def send(body): sent.append(body); return receipt(self.evidence if len(sent) == 1 else {'action': 'escalate', 'params': {}})
            trajectory(self.task, Path(self.folder.name)/arm, {'kind': 'trajectory', 'view': 'utc_end', 'mode': 'healthy', 'arm': arm, 'repeat': 0}, send)
            bodies.append(sent[1])
        self.assertEqual(bodies[0], bodies[1])
