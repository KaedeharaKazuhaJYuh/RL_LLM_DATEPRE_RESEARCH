"""Registration accepts the actual relay without erasing review objections."""
import copy
import unittest
from faultda_bench.review520 import registration as r
from faultda_bench.review515 import intake


class RegistrationTests(unittest.TestCase):
    def test_registration_keeps_all_twelve_existing_opinions(self):
        new = r.expected(); old = intake.expected()
        self.assertEqual(new['case_opinions'], old['referent_opinions'])
        self.assertTrue(r.verify(new)['final_adjudication_registered'])
        self.assertEqual(new['design_opinions'], old['design_opinions'])
        self.assertTrue(all(c['contextual'] == 'both_plausible' for c in new['case_opinions']))

    def test_consent_is_transcription_not_signature_or_new_science(self):
        self.assertEqual(r.consent_record()['user_answer'], '审阅者已明确同意正式登记')
        new = r.expected()
        self.assertFalse(new['source_signature_received'])
        self.assertFalse(new['reviewer_identity_authenticated'])
        self.assertFalse(new['new_0520_interface_independently_reviewed'])
        self.assertFalse(new['old_37_group_scope_expanded'])
        self.assertEqual(new['scientific_gate'], 'HOLD')
        self.assertEqual(new['approved_transport_requests'], 0)

    def test_registration_cannot_discard_an_objection_or_change_interpretation(self):
        for mutation in ('opinion', 'objection', 'signature', 'science', 'old_scores'):
            with self.subTest(mutation=mutation):
                new = copy.deepcopy(r.expected())
                if mutation == 'opinion': new['case_opinions'][0]['contextual'] = 'lookup'
                elif mutation == 'objection': new['retained_objections'].pop()
                elif mutation == 'signature': new['source_signature_received'] = True
                elif mutation == 'science': new['scientific_gate'] = 'GO'
                else: new['old_scores_replaced'] = True
                with self.assertRaises(ValueError): r.verify(new)

    def test_historical_nonfinal_intake_is_not_rewritten(self):
        self.assertFalse(intake.expected()['final_adjudication_registered'])
        self.assertEqual(intake.sha(intake.SOURCE), intake.SOURCE_SHA256)
        self.assertTrue(r.expected()['final_adjudication_registered'])


if __name__ == '__main__': unittest.main()
