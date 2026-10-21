import copy
import json
import unittest
from faultda_bench.review525 import preflight as p
from faultda_bench.coherent395 import suite


class PublicComparisonPreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = json.loads(suite.OUTPUT.read_text(encoding='utf-8'))['rows']

    def case(self):
        return {'case_id': 'synthetic-test-only', 'public_observation': copy.deepcopy(self.rows[0]['public_observation']), 'query_event_id': 'history:10'}

    def arms(self, c):
        a = {'name': 'rule', 'public_observation_sha256': {c['case_id']: p.digest(c['public_observation'])},
             'allowed_tools': ['inspect', 'receipt_lookup'],
             'tool_budgets': dict(checks=2, mutations=0, decisions=4, response_bytes=10000, wall_seconds=10),
             'preprocessing': {'code_sha256': 'a'*64, 'view_schema': 'public-request-binding-v1', 'charged': True},
             'private_truth_access': False}
        b = copy.deepcopy(a); b['name'] = 'model'
        return [a, b]

    def test_all_72_targets_derive_from_public_request_without_reference_argument(self):
        for r in self.rows:
            obs = r['public_observation']; saved = copy.deepcopy(obs)
            answer = p.resolve(obs, 'history:10')
            self.assertEqual(answer['target_publish_event_id'], r['expected_receipt_facts']['receipt_event_id'])
            self.assertEqual(obs, saved)
            self.assertFalse(answer['generation_origin_attested'])
            self.assertFalse(answer['safety_or_stop_permission_computed'])

    def test_private_or_reference_fields_rejected_even_if_not_used(self):
        for key in ('expected_receipt_facts', 'private_truth', 'row_id', 'hidden_mode'):
            obs = self.case()['public_observation']; obs[key] = 'extra'
            with self.subTest(key=key), self.assertRaises(ValueError): p.resolve(obs, 'history:10')

    def test_noncurrent_query_cannot_use_later_history(self):
        obs = self.case()['public_observation']; obs['history'].append(copy.deepcopy(obs['history'][9]))
        with self.assertRaisesRegex(ValueError, 'snapshot'): p.resolve(obs, 'history:10')

    def test_unsupported_semantics_and_nonpublic_common_tool_rejected(self):
        c = self.case(); c['public_observation']['responsibility_contract']['semantics_version'] = 'other'
        with self.assertRaises(ValueError): p.resolve(c['public_observation'], 'history:10')
        c = self.case(); arms = self.arms(c)
        for a in arms: a['allowed_tools'].append('private_inspect')
        with self.assertRaises(ValueError): p.compare_setup([c], arms)

    def test_multiple_attempts_keep_ambiguity_and_no_origin_attestation(self):
        obs = self.case()['public_observation']; obs['history'][6]['params']['request_id'] = obs['history'][4]['params']['request_id']
        a = p.resolve(obs, 'history:10')
        self.assertEqual(a['binding_status'], 'ambiguous_repeated_request')
        self.assertIsNone(a['target_publish_event_id'])
        self.assertEqual(len(a['candidate_attempts']), 2)
        self.assertFalse(a['receipt_authenticity_verified'])

    def test_receipt_response_substitution_rejected(self):
        obs = self.case()['public_observation']; obs['history'][10]['response']['request_id'] = 'wrong'
        with self.assertRaises(ValueError): p.resolve(obs, 'history:10')

    def test_extra_receipt_fields_cannot_leak_through_the_derived_result(self):
        obs = self.case()['public_observation']
        obs['history'][10]['response']['expected_receipt_facts'] = {'private': 'answer'}
        with self.assertRaises(ValueError): p.resolve(obs, 'history:10')

    def test_matching_declarations_never_become_cost_or_science_evidence(self):
        c = self.case(); result = p.compare_setup([c], self.arms(c))
        self.assertFalse(result['execution_compliance_verified'])
        self.assertFalse(result['ability_gap_measured'])
        self.assertIsNone(result['actual_total_costs_equal'])
        self.assertFalse(result['independent_task_eligibility_verified'])
        self.assertEqual(result['approved_transport_requests'], 0)

    def test_unmatched_permissions_budget_helper_or_input_rejected(self):
        for kind in ('tools', 'budget', 'helper', 'input', 'delete', 'oracle'):
            c = self.case(); arms = self.arms(c)
            if kind == 'tools': arms[1]['allowed_tools'].append('private_inspect')
            elif kind == 'budget': arms[1]['tool_budgets']['checks'] += 1
            elif kind == 'helper': arms[1]['preprocessing']['code_sha256'] = 'b'*64
            elif kind == 'input': arms[1]['public_observation_sha256'][c['case_id']] = 'f'*64
            elif kind == 'delete': arms[1]['public_observation_sha256'] = {}
            else: arms[1]['private_truth_access'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError): p.compare_setup([c], arms)

    def test_missing_accounting_or_boolean_budget_rejected(self):
        for kind in ('free', 'missing', 'bool', 'negative'):
            c = self.case(); arms = self.arms(c)
            for a in arms:
                if kind == 'free': a['preprocessing']['charged'] = False
                elif kind == 'missing': a['tool_budgets'].pop('response_bytes')
                elif kind == 'bool': a['tool_budgets']['checks'] = True
                else: a['tool_budgets']['checks'] = -1
            with self.subTest(kind=kind), self.assertRaises(ValueError): p.compare_setup([c], arms)


if __name__ == '__main__': unittest.main()
