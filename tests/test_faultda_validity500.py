import copy
import json
import unittest
from faultda_bench.validity500 import suite as s, adapter as a, SEMANTICS_VERSION


class ValidityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(s.source.OUTPUT.read_text(encoding='utf-8'))
        cls.obs = cls.source['rows'][0]['public_observation']

    def test_old_primary_and_alternate_frames_are_separate(self):
        r = s.interpretation()
        self.assertFalse(r['old_primary_scores_replaced']); self.assertFalse(r['best_of_reference_scoring_used'])
        self.assertEqual(r['summary']['contextual']['legacy_lookup_all_correct'],0)
        self.assertEqual(r['summary']['contextual']['alternate_publish_all_correct'],12)
        self.assertEqual(r['summary']['explicit']['legacy_lookup_all_correct'],6)
        self.assertEqual(r['summary']['explicit']['alternate_publish_all_correct'],0)
        self.assertTrue(all('not_eligible' in x['interpretation_status'] for x in r['rows'] if x['arm']=='explicit'))

    def test_reported_actor_anchor_rejects_stage_and_mismatched_id(self):
        v = {'receipt_event_id':'history:5','receipt_request_id':'request-17','receipt_responsibility':'historical_agent_action'}
        self.assertEqual(s.anchored_role(self.obs,v)['status'],'reported_event_is_not_publish')
        v['receipt_event_id'] = 'history:4'; v['receipt_request_id'] = 'unknown'
        self.assertEqual(s.anchored_role(self.obs,v)['status'],'request_event_mismatch')
        v['receipt_event_id'] = 'history:-1'
        self.assertEqual(s.anchored_role(self.obs,v)['status'],'invalid_event_id')
        v['receipt_event_id'] = 'history:999'
        self.assertEqual(s.anchored_role(self.obs,v)['status'],'event_out_of_range')

    def test_role_annotation_does_not_infer_cognition_or_authorship(self):
        r = s.interpretation()['summary']
        self.assertEqual(r['contextual']['reported_publish_role_consistent'],12)
        self.assertEqual(r['explicit']['reported_publish_role_consistent'],6)
        self.assertEqual(r['explicit']['reported_publish_role_inconsistent'],4)
        self.assertEqual(r['explicit']['reported_publish_unbound'],2)

    def test_all_actor_views_round_trip_and_keep_history(self):
        for row in self.source['rows']:
            obs = row['public_observation']; new = a.encode(obs)
            self.assertEqual(new['responsibility_contract']['semantics_version'],SEMANTICS_VERSION)
            self.assertEqual(a.decode(new),obs)
            self.assertEqual(new['history'],obs['history'])
            self.assertNotIn('current_model_start_history_index',new['responsibility_context'])

    def test_stop_and_violation_permissions_unchanged(self):
        for r in self.source['rows']:
            mapped = a.evidence_view(a.encode(r['public_observation']))
            self.assertEqual(mapped,a.rename(r['public_evidence']))

    def test_active_actor_never_implies_model_generated_actions(self):
        current = next(r for r in self.source['rows'] if r['role']=='scripted_current')
        new = a.encode(current['public_observation']); proof = a.evidence_view(new)
        self.assertTrue(any(e['responsibility']=='active_actor' for e in proof['events']))
        self.assertEqual(new['generation_context']['history_generation_origin'],'scripted_fixture')
        self.assertFalse(new['generation_context']['provider_authenticity_verified'])

    def test_unpinned_self_declared_model_origin_remains_unknown(self):
        obs = copy.deepcopy(self.obs); obs['trajectory_provenance'] = 'current_model_action generated this'
        new = a.encode(obs)
        self.assertEqual(new['generation_context']['history_generation_origin'],'unknown')
        self.assertIsNone(new['generation_context']['source_sha256'])
        self.assertEqual(a.decode(new),obs)

    def test_forged_origin_and_boolean_alias_rejected(self):
        for key,value in [('history_generation_origin','model_api_tool_action'),('source_sha256','0'*64),('provider_authenticity_verified',0)]:
            new = a.encode(self.obs); new['generation_context'][key] = value
            with self.assertRaises(ValueError):a.decode(new)

    def test_mixed_version_or_reserved_fields_rejected(self):
        new = a.encode(self.obs); new['responsibility_context']['semantics_version'] = 'old'
        with self.assertRaises(ValueError):a.decode(new)
        with self.assertRaises(ValueError):a.encode(a.encode(self.obs))
        obs = copy.deepcopy(self.obs); obs['generation_contract'] = {}
        with self.assertRaises(ValueError):a.encode(obs)

    def test_role_alias_key_collision_rejected(self):
        with self.assertRaises(ValueError):a.rename({'current_model_action':1,'active_actor':2})

    def test_migration_has_no_new_actions_or_provider_calls(self):
        r = s.migration()
        self.assertEqual(r['summary']['exact_round_trips'],72)
        self.assertEqual(r['summary']['scripted_history_origins'],72)
        self.assertEqual(r['summary']['actual_model_tool_action_origins'],0)
        self.assertEqual(r['summary']['new_physical_tool_executions'],0)
        self.assertEqual(r['summary']['new_provider_requests'],0)

    def test_scientific_decisions_do_not_authorize_new_api_or_rl_claim(self):
        r = s.claims()
        self.assertEqual(r['approved_transport_requests'],0)
        self.assertEqual(r['live_decision'],'NO_GO_LIVE')
        self.assertEqual(r['scientific_gate'],'HOLD')
        self.assertEqual(next(c for c in r['decisions'] if c['claim_id']=='rl_effect_or_general_recovery_mechanism')['status'],'not_established')
