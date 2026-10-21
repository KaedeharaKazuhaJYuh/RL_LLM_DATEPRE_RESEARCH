"""Review boundaries, proposition-level witnesses and admission refusals."""
import copy
import json
import unittest
from faultda_bench.review505 import intake, design


class ReviewIntakeTests(unittest.TestCase):
    def test_source_bound_human_scope(self):
        r = intake.verify()
        self.assertEqual(r['groups'], 37)
        self.assertFalse(r['reviewer_identity_authenticated'])
        self.assertEqual(r['final_referent_adjudication'], 'not_performed')

    def test_cannot_promote_science_or_new_design(self):
        original = json.loads(intake.RECEIPT.read_text(encoding='utf-8'))
        for key, value in [('scientific_gate', 'GO'), ('new_design_independently_reviewed', True),
                           ('independent_final_referent_adjudication', 'complete'),
                           ('reviewer_json_attachments_received', True)]:
            with self.subTest(key=key):
                r = copy.deepcopy(original); r[key] = value
                with self.assertRaises(ValueError): intake.verify(r)

    def test_stale_or_unreviewed_case_rejected(self):
        original = json.loads(intake.RECEIPT.read_text(encoding='utf-8'))
        for key, value in [('source_sha256', '0'*64), ('reviewed_commit', 'a'*40),
                           ('case_bindings', {}), ('technical_groups_passed', 72)]:
            r = copy.deepcopy(original); r[key] = value
            with self.assertRaises(ValueError): intake.verify(r)


class EvidenceDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.result = design.build()

    def test_frozen_analysis_replays(self):
        self.assertEqual(json.loads(design.OUTPUT.read_text(encoding='utf-8')), self.result)

    def test_counterworlds_depend_on_proposition_not_world_count(self):
        rows = [{'row_id': str(i), 'public_observation': {'same': True},
                 'private_truth': {'actual_safe_stop_if_taken': v}} for i, v in enumerate([True, True])]
        self.assertFalse(design.counterworld_groups(rows)[0]['proven_insufficient_for_safe_stop'])
        rows[1]['private_truth']['actual_safe_stop_if_taken'] = False
        self.assertTrue(design.counterworld_groups(rows)[0]['proven_insufficient_for_safe_stop'])

    def test_counterworld_denominators(self):
        self.assertEqual(self.result['summary']['public_identical_opposite_truth_classes'], 6)
        self.assertEqual(self.result['summary']['preassigned_opposite_truth_pairs'], 12)
        self.assertEqual(self.result['summary']['insufficient_read_controls'], 24)
        self.assertEqual(self.result['summary']['publicly_decisive_read_controls'], 48)

    def test_strong_public_rule_resolves_without_new_rollouts(self):
        rule = self.result['strong_public_rule']
        self.assertEqual((rule['resolved'], rule['supported_stops'], rule['confirmed_history_escalations']), (24, 12, 12))
        for row in rule['rows']:
            self.assertEqual({k: row['cost'][k] for k in ('checks', 'mutations', 'decisions')},
                             {'checks': 1, 'mutations': 0, 'decisions': 2})

    def test_model_fact_answers_are_not_action_outcomes(self):
        self.assertEqual(self.result['summary']['model_action_decisions_observed_here'], 0)
        self.assertEqual(self.result['scientific_increment'], 'not_established')
        self.assertEqual(self.result['scientific_gate'], 'HOLD')


class AdmissionTests(unittest.TestCase):
    def plan(self):
        return json.loads(design.PLAN.read_text(encoding='utf-8'))

    def complete_synthetic_declarations(self):
        p = self.plan()
        p['future_clusters'] = [{'upstream_lineage': 'synthetic-test-'+str(i),
                                 'generator_family': 'synthetic-'+str(i), 'independent_truth_review': True}
                                for i in range(3)]
        for key in ('frozen_test_sha256', 'external_commit_anchor', 'power_plan', 'minimum_effect',
                    'wording_adjudication', 'generator_leakage_review'): p[key] = 'synthetic-test-declaration-only'
        return p

    def test_current_plan_not_admitted(self):
        self.assertTrue(design.admission_issues(self.plan()))
        self.assertEqual(design.verify()['admission'], 'NOT_ADMITTED')

    def test_complete_schema_does_not_authorize_api(self):
        p = self.complete_synthetic_declarations()
        self.assertEqual(design.admission_issues(p), [])
        p['approved_transport_requests'] = 1
        self.assertIn('no API authorization', design.admission_issues(p))

    def test_historical_or_duplicate_lineage_fails(self):
        for lineage in ('uci_occupancy', 'uci_auto_mpg', 'uci_glass', 'auto_mpg', 'glass', 'synthetic-test-0'):
            p = self.complete_synthetic_declarations(); p['future_clusters'][1]['upstream_lineage'] = lineage
            self.assertTrue(design.admission_issues(p))
        p = self.complete_synthetic_declarations()
        p['future_clusters'][1]['generator_family'] = p['future_clusters'][0]['generator_family']
        self.assertTrue(design.admission_issues(p))

    def test_missing_safety_or_cost_or_stratum_fails(self):
        for key in ('mandatory_safety_metric', 'actual_cost_reporting', 'preassigned_resolvable_stratum',
                    'generator_leakage_review', 'power_plan', 'external_commit_anchor'):
            p = self.complete_synthetic_declarations(); p[key] = None
            self.assertTrue(design.admission_issues(p))

    def test_intent_and_hold_boundaries(self):
        p = self.complete_synthetic_declarations(); p['analysis_intents'] = ['group']
        self.assertTrue(design.admission_issues(p))
        p = self.complete_synthetic_declarations(); p['scientific_gate'] = 'GO'
        self.assertTrue(design.admission_issues(p))


if __name__ == '__main__': unittest.main()
