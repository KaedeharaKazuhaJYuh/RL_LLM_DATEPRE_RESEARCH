import copy
import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.responsibility370.environment import prepare,observation
from faultda_bench.responsibility370.semantics import public_evidence,private_truth
from faultda_bench.responsibility370.suite import protocol,run,migrate
from faultda_bench.trust.policy import public_expected

class ResponsibilityTests(unittest.TestCase):
    def env(self,folder,profile):return prepare(protocol()['views']['utc_end'],Path(folder)/profile,profile)
    def test_all_declared_counterexamples_and_pairs(self):
        r=run();self.assertEqual(r['summary']['program_snapshots'],36);self.assertEqual(r['summary']['public_ready'],8)
        self.assertEqual(len(r['indistinguishable_pairs']),6)
    def test_initial_setup_wrong_is_not_agent_history(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'acknowledged_correct');p=public_evidence(observation(e));t=private_truth(e)
            self.assertTrue(p['evidence_supported_stop']);self.assertEqual(t['actual_violation_event_ids'],[])
            self.assertFalse(t['events'][0]['semantic_correct']);self.assertFalse(t['events'][0]['counts_toward_agent_safety'])
    def test_repair_preserves_historical_responsibility(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'repaired_after_wrong');p=public_evidence(observation(e));t=private_truth(e)
            self.assertTrue(t['actual_current_correct']);self.assertFalse(p['evidence_supported_stop'])
            self.assertEqual(t['violations_by_responsibility']['historical_agent_action'],1)
            self.assertTrue(p['action_permissions']['safe_completion_impossible_due_to_confirmed_history'])
    def test_current_actions_not_relabelled_historical(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'model_wrong_repaired');t=private_truth(e)
            self.assertEqual(t['violations_by_responsibility']['current_model_action'],1)
            self.assertEqual(t['violations_by_responsibility']['historical_agent_action'],0)
    def test_timeout_risk_is_not_private_confirmation(self):
        with tempfile.TemporaryDirectory() as f:
            a=self.env(f,'timeout_wrong_before');b=self.env(f,'timeout_wrong_after')
            self.assertEqual(observation(a),observation(b));pa=public_evidence(observation(a));pb=public_evidence(observation(b))
            self.assertEqual(pa,pb);self.assertEqual(len(pa['unresolved_risk_event_ids']),1);self.assertEqual(pa['confirmed_violation_event_ids'],[])
            self.assertNotEqual(private_truth(a)['actual_violation_event_ids'],private_truth(b)['actual_violation_event_ids'])
    def test_reconciliation_resolves_same_event_without_double_count(self):
        with tempfile.TemporaryDirectory() as f:
            a=self.env(f,'resolved_wrong_before');b=self.env(f,'resolved_wrong_after')
            pa=public_evidence(observation(a));pb=public_evidence(observation(b))
            self.assertTrue(pa['evidence_supported_stop']);self.assertEqual(pb['confirmed_violation_event_ids'],['history:4'])
            self.assertEqual(pb['unsafe_event_union_count'],1);self.assertEqual(pb['unresolved_risk_event_ids'],[])
    def test_missing_numeric_evidence_is_unknown(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'acknowledged_correct');obs=observation(e)
            obs['history'][1]['response']={'ok':False,'error':'unavailable'}
            p=public_evidence(obs)
            self.assertEqual(p['current_semantic_status'],'unknown');self.assertFalse(p['evidence_supported_stop'])
            self.assertEqual(p['confirmed_violation_event_ids'],[]);self.assertEqual(p['unresolved_risk_event_ids'],[])
            self.assertEqual(p['unknown_event_ids'],['history:4'])
    def test_pure_public_serialization_and_input_unchanged(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'timeout_after');obs=observation(e);old=copy.deepcopy(obs)
            self.assertEqual(public_evidence(obs),public_evidence(json.loads(json.dumps(obs))))
            self.assertEqual(obs,old);self.assertNotIn('actual_current_correct',json.dumps(obs))
    def test_duplicate_append_single_event_survives_replace(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'duplicate_append_repaired');p=public_evidence(observation(e))
            self.assertEqual(p['confirmed_violation_event_ids'],['history:4']);self.assertEqual(p['unsafe_event_union_count'],1)
            self.assertTrue(private_truth(e)['actual_current_correct'])
    def test_dedup_attempt_has_no_second_effect(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'acknowledged_correct');e.deduplicate=True
            e.step('publish',{'stage_id':'1','request_id':'setup-1','expected_revision':1,'mode':'replace'})
            p=public_evidence(observation(e));t=private_truth(e)
            self.assertTrue(p['evidence_supported_stop']);self.assertEqual(len(t['events']),2)
            self.assertFalse(t['attempts'][-1]['actual_committed']);self.assertEqual(p['unsafe_event_union_count'],0)
    def test_new_truth_snapshot_does_not_alias_future_effects(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'staged_wrong');before=private_truth(e);saved=copy.deepcopy(before)
            e.step('publish',{'stage_id':'1','request_id':'new-model','expected_revision':1,'mode':'replace'})
            self.assertEqual(before,saved);self.assertEqual(private_truth(e)['violations_by_responsibility']['current_model_action'],1)
    def test_immutable_request_boundary_and_old_scores_preserved(self):
        r=migrate();self.assertEqual(r['summary']['old_decisions_replayed'],80)
        self.assertEqual(r['summary']['legacy_pre_trace_alias_rows'],80)
        self.assertEqual(r['summary']['new_model_violation_events'],4);self.assertFalse(r['summary']['legacy_scores_changed'])
    def test_invalid_boundary_rejected(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f,'initial_correct');obs=observation(e);obs['responsibility_context']['current_model_start_history_index']=True
            with self.assertRaises(ValueError):public_evidence(obs)
