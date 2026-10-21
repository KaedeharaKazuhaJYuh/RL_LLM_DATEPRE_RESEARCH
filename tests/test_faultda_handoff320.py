import copy
import json
import tempfile
import unittest
from pathlib import Path

from faultda_bench.handoff320.suite import protocol, trajectory, summarize
from faultda_bench.consistency310.suite import run as old_records


def receipt(value):
    return {'category': 'received', 'request_sent': True, 'response': {
        'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value)}}]}}


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.p = protocol(); self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.correct = old_records()['controls'][0]['record']
        self.seed = next(s for s in self.p['seeds'] if s['view'] == 'plus8_end' and s['repeat'] == 0)
        self.task = self.p['views']['plus8_end']

    def cell(self, arm, mode='healthy'):
        return {'kind': 'trajectory', 'view': 'plus8_end', 'repeat': 0, 'seed': 2, 'arm': arm, 'mode': mode}

    def test_same_initial_seed_in_all_arms(self):
        initials = []
        for arm in ('review_only', 'checked_review', 'flags_only'):
            count = 0
            def send(body):
                nonlocal count
                count += 1
                return receipt(self.correct if arm != 'flags_only' and count == 1 else {'action': 'escalate', 'params': {}})
            r = trajectory(self.task, Path(self.folder.name)/arm, self.cell(arm), self.seed, send)
            initials.append(r['initial_record'])
        self.assertEqual(initials, [self.seed['record']]*3)

    def test_actual_corrected_record_reaches_action(self):
        bodies = []
        def send(body):
            bodies.append(body)
            return receipt(self.correct if len(bodies) == 1 else {'action': 'stop', 'params': {}})
        r = trajectory(self.task, Path(self.folder.name)/'corrected', self.cell('checked_review'), self.seed, send)
        self.assertFalse(r['initial_score']['total_correct']); self.assertTrue(r['revision_score']['total_correct'])
        self.assertEqual(r['action_record'], self.correct); self.assertTrue(r['evaluation']['safe_complete'])
        last = bodies[1]['messages'][-1]['content']
        self.assertIn(json.dumps(self.correct, allow_nan=False), last)
        self.assertNotIn('Program check', json.dumps(bodies[1]))

    def test_flags_only_is_not_active_report_verdict(self):
        bodies = []
        def send(body): bodies.append(body); return receipt({'action': 'escalate', 'params': {}})
        r = trajectory(self.task, Path(self.folder.name)/'flags', self.cell('flags_only'), self.seed, send)
        self.assertEqual(len(bodies), 1); self.assertIsNone(r['revision_score'])
        self.assertEqual(r['action_record'], self.seed['record'])
        text = json.dumps(bodies[0]); self.assertIn('comparison:6', text)
        self.assertNotIn('active_report_verified', text); self.assertNotIn('stop_permitted_by_checker', text)

    def test_revision_uses_current_faulty_state(self):
        bodies = []
        def send(body): bodies.append(body); return receipt(self.correct if len(bodies) == 1 else {'action': 'escalate', 'params': {}})
        trajectory(self.task, Path(self.folder.name)/'fault', self.cell('checked_review', 'shared_compute'), self.seed, send)
        obs = json.loads(bodies[0]['messages'][1]['content'])
        self.assertAlmostEqual(obs['history'][0]['response']['records'][0]['output']['total'], 118.89)
        self.assertNotIn('shared_compute', json.dumps(bodies))

    def test_no_guard_intercepts_false_stop(self):
        def send(body): return receipt({'action': 'stop', 'params': {}})
        r = trajectory(self.task, Path(self.folder.name)/'unguarded', self.cell('flags_only', 'shared_compute'), self.seed, send)
        self.assertTrue(r['evaluation']['false_completion']); self.assertEqual(r['evaluation']['terminal'], 'stop')

    def test_bad_revision_not_replaced_by_hidden_correct_answer(self):
        n = 0
        def send(body):
            nonlocal n
            n += 1
            return receipt({'bad': 'shape'} if n == 1 else {'action': 'escalate', 'params': {}})
        r = trajectory(self.task, Path(self.folder.name)/'bad', self.cell('checked_review'), self.seed, send)
        self.assertFalse(r['revision_score']['schema']); self.assertEqual(r['action_record'], {'bad': 'shape'})

    def test_missing_revision_is_explicit_unavailable(self):
        n = 0
        def send(body):
            nonlocal n
            n += 1
            return {'category': 'provider_error', 'request_sent': True, 'error_type': 'TimeoutError'} if n == 1 else receipt({'action': 'escalate', 'params': {}})
        r = trajectory(self.task, Path(self.folder.name)/'missing', self.cell('checked_review'), self.seed, send)
        self.assertEqual(r['action_record'], {'model_record_unavailable': True})

    def test_plan_coverage_and_cost_cap(self):
        self.assertEqual(len(self.p['order']), 56); self.assertEqual(self.p['max_requests'], 320)
        for seed in range(8):
            cells = [c for c in self.p['order'] if c.get('seed') == seed]
            self.assertEqual(len(cells), 6)
        self.assertEqual(self.p['independent_task_clusters'], 1)
