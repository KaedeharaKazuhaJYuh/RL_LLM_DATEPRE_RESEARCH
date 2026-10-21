import tempfile
import unittest
from pathlib import Path

from faultda_bench.qualify330.suite import protocol, prepare, episode, ambiguous_pair
from faultda_bench.qualify330.environment import observation, QualificationEnv
from faultda_bench.qualify330.policy import choose


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(); self.addCleanup(self.folder.cleanup)
        self.task = protocol()['views']['utc_end']

    def episode(self, profile, budget, policy):
        return episode(self.task, Path(self.folder.name)/(profile+str(budget)+policy),
                       {'view': 'utc_end', 'profile': profile, 'checks': budget, 'policy': policy})

    def test_same_history_can_hide_different_commitment(self):
        pair = ambiguous_pair(self.task, Path(self.folder.name)/'pair')
        self.assertTrue(pair['public_histories_equal_before_inspect'])
        self.assertEqual([d['action'] for d in pair['resolved_decisions']], ['publish', 'stop'])

    def test_repeat_failure_defeats_unconditional_retry_stop(self):
        r = self.episode('before_twice', 4, 'retry_then_stop')
        self.assertTrue(r['evaluation']['false_completion']); self.assertFalse(r['evaluation']['terminal_correct'])
        self.assertEqual(r['evaluation']['agent_wrong_publications'], 0)

    def test_one_failure_only_would_hide_bad_stop_assumption(self):
        for profile in ('before_once', 'after_once'):
            r = self.episode(profile, 3, 'retry_then_stop')
            self.assertTrue(r['evaluation']['safe_complete'])

    def test_retry_once_reconciles_second_failure(self):
        r = self.episode('before_twice', 4, 'retry_once_reconcile')
        self.assertEqual([d['action'] for d in r['decisions']], ['stage', 'publish', 'publish', 'inspect', 'publish', 'stop'])
        self.assertTrue(r['evaluation']['safe_complete']); self.assertEqual(r['evaluation']['duplicate_events'], 0)
        self.assertEqual(r['evaluation']['cost']['checks'], 4)

    def test_inspect_first_needs_second_read_for_second_failure(self):
        r = self.episode('before_twice', 4, 'inspect_first')
        self.assertTrue(r['evaluation']['safe_escalation']); self.assertFalse(r['evaluation']['safe_complete'])
        r = self.episode('before_twice', 5, 'inspect_first')
        self.assertTrue(r['evaluation']['safe_complete']); self.assertEqual(r['evaluation']['cost']['checks'], 5)

    def test_after_commit_retry_cas_rejection_does_not_duplicate(self):
        r = self.episode('after_once', 4, 'retry_once_reconcile')
        self.assertTrue(r['evaluation']['safe_complete']); self.assertEqual(r['evaluation']['duplicate_events'], 0)
        published = [h for h in r['evaluation']['trace'] if h['action'] == 'publish']
        self.assertEqual(len(published), 2); self.assertFalse(published[1]['response']['ok'])
        self.assertEqual(published[0]['params'], published[1]['params'])

    def test_low_budget_rule_escalation_is_not_false_completion(self):
        r = self.episode('before_twice', 3, 'retry_once_reconcile')
        self.assertTrue(r['evaluation']['safe_escalation']); self.assertFalse(r['evaluation']['false_completion'])

    def test_fault_count_is_not_public(self):
        env = prepare(self.task, Path(self.folder.name)/'private', 'before_twice', 4)
        obs = observation(env); self.assertIn('can repeat', obs['reliability_contract']['limits'])
        self.assertNotIn('_before_failures_remaining', str(obs)); self.assertNotIn('before_twice', str(obs))

    def test_invalid_fault_or_budget_rejected(self):
        for kwargs in ({'before_failures': True}, {'before_failures': 3}, {'check_budget': 2}, {'before_failures': 1, 'after_loss': True}):
            with self.assertRaises(ValueError): QualificationEnv(self.task, Path(self.folder.name)/'invalid', **kwargs)

    def test_design_coverage(self):
        p = protocol(); self.assertEqual(len(p['order']), 72)
        self.assertEqual(p['new_api_calls'], 0); self.assertEqual(p['independent_task_clusters'], 1)
