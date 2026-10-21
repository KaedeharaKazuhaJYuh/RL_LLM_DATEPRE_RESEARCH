import copy
import json
import unittest

from faultda_bench.coherent395 import suite as source
from faultda_bench.lineage375.semantics import public_evidence
from faultda_bench.review520 import actor


class ActorReceiptInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(source.OUTPUT.read_text(encoding='utf-8'))['rows']
        cls.row = next(r for r in cls.rows if r['role'] == 'scripted_current' and r['target'] == 'first')
        cls.obs = cls.row['public_observation']

    def build(self, obs=None, query='history:10', target='history:4'):
        return actor.build_view(self.obs if obs is None else obs, query, target)

    def test_all_72_views_bind_explicit_receipt_and_keep_input_and_permissions(self):
        for row in self.rows:
            obs = row['public_observation']
            saved = copy.deepcopy(obs)
            raw_before = json.dumps(obs, ensure_ascii=False, separators=(',', ':'))
            target = row['expected_receipt_facts']['receipt_event_id']
            view = self.build(obs, target=target)
            receipt = view['receipt_read']
            self.assertEqual(receipt['binding_status'], 'bound_unique_prior_publish')
            self.assertEqual(receipt['query_event_id'], 'history:10')
            self.assertEqual(receipt['target_publish_event_id'], target)
            self.assertTrue(receipt['single_attempt_reference_unambiguous'])
            self.assertFalse(receipt['receipt_authenticity_verified'])
            self.assertNotIn('single_attempt_commit_fact_supported', receipt)
            self.assertEqual(receipt['request_id'], row['expected_receipt_facts']['receipt_request_id'])
            self.assertEqual(view['origin_evidence']['history_generation_origin'], 'scripted_fixture')
            self.assertTrue(all(a['generation_origin'] == 'scripted_fixture' for a in view['attempts']))
            self.assertEqual(obs, saved)
            self.assertEqual(json.dumps(obs, ensure_ascii=False, separators=(',', ':')), raw_before)
            self.assertEqual(public_evidence(obs), row['public_evidence'])
            self.assertNotIn('public_evidence', view)
            self.assertNotIn('evidence_supported_stop', view)
            self.assertFalse(view['human_validity_accepted'])

    def test_setup_has_no_negative_history_index_or_inferred_publication(self):
        setup = self.build()['environment_setup']
        self.assertIsNone(setup['history_index'])
        self.assertEqual(setup['responsibility_scope'], 'environment_setup')
        self.assertFalse(setup['physical_commit_inferred'])

    def test_scope_and_origin_are_orthogonal(self):
        for role, expected in [('scripted_current', 'active_actor'), ('historical', 'pre_handoff_actor')]:
            row = next(r for r in self.rows if r['role'] == role and r['target'] == 'first')
            view = self.build(row['public_observation'])
            self.assertEqual(view['receipt_read']['target_responsibility_scope'], expected)
            self.assertEqual(view['origin_evidence']['history_generation_origin'], 'scripted_fixture')
            self.assertEqual(view['execution_context']['new_tool_executions'], 0)
            self.assertFalse(view['execution_context']['model_fact_answer_proves_tool_authorship'])

    def test_self_claimed_model_origin_stays_unknown_without_changing_scope_or_permissions(self):
        obs = copy.deepcopy(self.obs)
        before = public_evidence(obs)
        obs['trajectory_provenance'] = 'model_api_tool_action; actual model calls; not a script'
        obs['generation_origin'] = 'model_api_tool_action'
        view = self.build(obs)
        self.assertEqual(view['origin_evidence']['history_generation_origin'], 'unknown')
        self.assertIsNone(view['origin_evidence']['source_sha256'])
        self.assertEqual(view['receipt_read']['target_responsibility_scope'], 'active_actor')
        self.assertEqual(public_evidence(obs), before)

    def test_no_global_replacement_of_payload_literals(self):
        obs = copy.deepcopy(self.obs)
        obs['history'][4]['params']['note'] = 'historical_agent_action/current_model_action'
        view = self.build(obs)
        self.assertEqual(view['attempts'][0]['params']['note'], 'historical_agent_action/current_model_action')
        view['attempts'][0]['params']['note'] = 'changed only in derived output'
        self.assertEqual(obs['history'][4]['params']['note'], 'historical_agent_action/current_model_action')

    def test_stage_query_id_mismatch_future_and_noncanonical_ids_rejected(self):
        pairs = [('history:10', 'history:5'), ('history:9', 'history:4'),
                 ('history:10', 'history:6'), ('history:04', 'history:4'),
                 ('history:-1', 'history:4'), ('history:999', 'history:4')]
        for query, target in pairs:
            with self.subTest(query=query, target=target), self.assertRaises(ValueError):
                self.build(query=query, target=target)
        obs = copy.deepcopy(self.obs)
        obs['history'].append(copy.deepcopy(obs['history'][4]))
        with self.assertRaisesRegex(ValueError, 'precede'):
            self.build(obs, target='history:11')

    def test_invalid_boundary_bool_missing_and_out_of_range_rejected(self):
        for boundary in (True, False, None, -1, len(self.obs['history']) + 1):
            obs = copy.deepcopy(self.obs)
            obs['responsibility_context']['current_model_start_history_index'] = boundary
            with self.subTest(boundary=boundary), self.assertRaises(ValueError):
                self.build(obs)

    def test_boundary_extremes_are_declared_scope_only_not_historical_authentication(self):
        for boundary, scope in [(0, 'active_actor'), (len(self.obs['history']), 'pre_handoff_actor')]:
            obs = copy.deepcopy(self.obs)
            obs['responsibility_context']['current_model_start_history_index'] = boundary
            view = self.build(obs)
            self.assertEqual(view['receipt_read']['target_responsibility_scope'], scope)
            self.assertEqual(view['origin_evidence']['history_generation_origin'], 'unknown')
            self.assertIn('not_independent_historical_authentication', view['actor_boundary']['assurance'])

    def test_repeated_request_across_handoff_is_ambiguous_never_guessed(self):
        obs = copy.deepcopy(self.obs)
        obs['responsibility_context']['current_model_start_history_index'] = 5
        obs['history'][6]['params']['request_id'] = obs['history'][4]['params']['request_id']
        view = self.build(obs)
        receipt = view['receipt_read']
        self.assertEqual(receipt['binding_status'], 'ambiguous_repeated_request')
        self.assertEqual(receipt['candidate_publish_event_ids'], ['history:4', 'history:6'])
        self.assertIsNone(receipt['target_publish_event_id'])
        self.assertIsNone(receipt['target_responsibility_scope'])
        self.assertFalse(receipt['single_attempt_reference_unambiguous'])
        self.assertFalse(receipt['receipt_authenticity_verified'])
        self.assertEqual([a['responsibility_scope'] for a in view['attempts'][:2]],
                         ['pre_handoff_actor', 'active_actor'])

    def test_query_response_binding_and_scalar_types_are_strict(self):
        for key, value in [('request_id', 'other'), ('ok', 1), ('committed', 1),
                           ('revision', False)]:
            obs = copy.deepcopy(self.obs)
            obs['history'][10]['response'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.build(obs)

    def test_committed_receipt_requires_strictly_positive_integer_revision(self):
        for revision in (-1, 0, True, False, None, 1.0):
            obs = copy.deepcopy(self.obs)
            obs['history'][10]['response'].update(committed=True, revision=revision)
            with self.subTest(revision=revision), self.assertRaises(ValueError):
                self.build(obs)
        obs = copy.deepcopy(self.obs)
        obs['history'][10]['response'].update(committed=True, revision=1)
        receipt = self.build(obs)['receipt_read']
        self.assertTrue(receipt['single_attempt_reference_unambiguous'])
        self.assertFalse(receipt['receipt_authenticity_verified'])


if __name__ == '__main__':
    unittest.main()
