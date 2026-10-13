import copy
import tempfile
import unittest
from pathlib import Path

from faultda_bench.recover325.suite import protocol, environment, episode, source_audit
from faultda_bench.recover325.policy import choose
from faultda_bench.feedback315.core import public_input, record_check
from faultda_bench.recover325.environment import observation as public_observation
from faultda_bench.semantic.oracle import evaluate


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.task = protocol()['views']['utc_end']

    def env(self, profile): return environment(self.task, Path(self.folder.name)/profile, profile)

    def test_initial_error_with_healthy_candidate(self):
        env = self.env('uncertain_wrong'); obs = public_observation(env)
        initial = obs['history'][0]['response']['records'][0]
        self.assertEqual(initial['params']['closed'], 'left'); self.assertFalse(record_check(initial, obs)['pass'])
        env.step('stage', public_input(obs)[0]); obs = public_observation(env)
        self.assertTrue(record_check(obs['history'][-1]['response'], obs)['pass'])
        self.assertNotIn('_initial_numeric_fault', str(obs))

    def test_correct_timeout_does_not_trigger_rewrite(self):
        env = self.env('uncertain_correct'); obs = public_observation(env)
        self.assertFalse(obs['initial_feedback']['ok'])
        self.assertEqual(choose(obs, 'verified')['action'], 'stop')

    def test_absent_report_has_legal_stage_publish_stop(self):
        cell = {'view': 'utc_end', 'profile': 'uncertain_absent', 'policy': 'verified'}
        r = episode(self.task, Path(self.folder.name)/'absent', cell)
        self.assertEqual([d['action'] for d in r['decisions']], ['stage', 'publish', 'stop'])
        self.assertTrue(r['evaluation']['safe_complete'])

    def test_ack_loss_reconciles_without_second_publish(self):
        for profile in ('uncertain_wrong_ack_loss', 'uncertain_absent_ack_loss'):
            r = episode(self.task, Path(self.folder.name)/profile, {'view': 'utc_end', 'profile': profile, 'policy': 'verified'})
            self.assertEqual([d['action'] for d in r['decisions']], ['stage', 'publish', 'inspect', 'stop'])
            self.assertTrue(r['evaluation']['safe_complete']); self.assertEqual(r['evaluation']['duplicate_events'], 0)
            self.assertEqual(r['evaluation']['cost']['checks'], 4)

    def test_reconciliation_budget_exhaustion_is_escalation(self):
        env = self.env('uncertain_absent_ack_loss'); env.budget = 3
        for _ in range(2):
            d = choose(public_observation(env), 'verified'); env.step(d['action'], d['params'])
        self.assertEqual(choose(public_observation(env), 'verified')['action'], 'escalate')

    def test_metadata_does_not_use_numerical_verdict(self):
        obs = public_observation(self.env('uncertain_wrong'))
        self.assertEqual(choose(obs, 'metadata_only')['action'], 'stop')
        self.assertEqual(choose(obs, 'verified')['action'], 'stage')

    def test_metadata_history_ablation_not_secretly_strong(self):
        env = self.env('unrecoverable_shared'); obs = public_observation(env)
        env.step('stage', public_input(obs)[0])
        env.step('publish', {'stage_id': '1', 'request_id': 'x', 'expected_revision': 1, 'mode': 'replace'})
        obs = public_observation(env)
        self.assertEqual(choose(obs, 'metadata_only')['action'], 'stop')
        self.assertEqual(choose(obs, 'verified')['action'], 'escalate')

    def test_irrecoverable_candidate_is_not_published(self):
        r = episode(self.task, Path(self.folder.name)/'irrecoverable', {'view': 'utc_end', 'profile': 'unrecoverable_shared', 'policy': 'verified'})
        self.assertEqual([d['action'] for d in r['decisions']], ['stage', 'escalate'])
        self.assertTrue(r['evaluation']['safe_escalation']); self.assertEqual(r['evaluation']['agent_wrong_publications'], 0)

    def test_source_audit_retains_real_events_not_guard_rollout(self):
        r = source_audit(); self.assertEqual(r['wrong_publication_events'], 9)
        self.assertEqual(r['public_check_rejects'], 9); self.assertTrue(r['posthoc_check_only'])
        self.assertFalse(r['model_guard_benefit_established'])

    def test_profiles_not_duplicate_untriggered_ack_fault(self):
        p = protocol(); self.assertEqual(len(p['order']), 64)
        correct_profiles = [r for r in p['profiles'] if r[0].startswith('uncertain_correct')]
        self.assertEqual(len(correct_profiles), 1)

    def test_before_after_timeout_same_response_different_commit(self):
        states = []
        for profile in ('uncertain_absent_ack_loss', 'uncertain_absent_before_commit'):
            env = self.env(profile)
            for _ in range(2):
                d = choose(public_observation(env), 'verified'); env.step(d['action'], d['params'])
            states.append((env.history[-1]['response'], len(env.records())))
        self.assertEqual(states[0][0], states[1][0]); self.assertEqual(states[0][1], 1); self.assertEqual(states[1][1], 0)

    def test_before_commit_retries_after_inspect_with_fresh_revision(self):
        r = episode(self.task, Path(self.folder.name)/'retry', {'view': 'utc_end', 'profile': 'uncertain_wrong_before_commit', 'policy': 'verified'})
        self.assertEqual([d['action'] for d in r['decisions']], ['stage', 'publish', 'inspect', 'publish', 'stop'])
        self.assertTrue(r['evaluation']['safe_complete']); self.assertEqual(r['evaluation']['duplicate_events'], 0)
        self.assertEqual(r['evaluation']['cost']['mutations'], 4)

    def test_public_contract_includes_ack_uncertainty(self):
        obs = public_observation(self.env('uncertain_absent_ack_loss'))
        self.assertIn('before commit', obs['reliability_contract']['limits'])
        self.assertNotIn('acknowledgement loss are excluded', str(obs))
