"""Scope regression tests for the actual returned human Markdown."""
import copy
import unittest
from faultda_bench.review515 import intake


class IntakeTests(unittest.TestCase):
    def test_received_opinions_do_not_register_final_or_new_work(self):
        r = intake.expected()
        self.assertEqual(intake.verify(r)['design_opinions_received'], 4)
        self.assertEqual(len(r['referent_opinions']), 12)
        self.assertEqual(set(r['design_opinions'].values()), {'revise'})
        self.assertFalse(r['final_adjudication_registered'])
        self.assertFalse(r['new_0515_changes_independently_reviewed'])
        self.assertFalse(r['old_scores_replaced'])

    def test_received_review_cannot_be_promoted_by_editing_receipt(self):
        for field, value in [('final_adjudication_registered', True),
                             ('approved_transport_requests', 1),
                             ('scientific_gate', 'GO'),
                             ('old_37_group_scope_expanded', True),
                             ('reviewer_identity_authenticated', True)]:
            with self.subTest(field=field):
                r = copy.deepcopy(intake.expected()); r[field] = value
                with self.assertRaises(ValueError): intake.verify(r)

    def test_fact_fields_do_not_become_recovery_or_causal_evidence(self):
        r = intake.factual_crosscheck()
        self.assertEqual(r['explicit_core_fact_fields_correct'], '12/12')
        self.assertEqual(r['scripted_current_role_mismatches'], '6/6')
        self.assertEqual(len(r['invalid_stage_event_references']), 2)
        self.assertIn('no new score, causal attribution', r['scope'])


if __name__ == '__main__': unittest.main()
