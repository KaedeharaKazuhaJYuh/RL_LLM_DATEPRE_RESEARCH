import copy
import unittest
from faultda_bench.review510 import metrics, review


class TerminalMetricsTests(unittest.TestCase):
    def setUp(self):
        x=metrics.frozen_controls(); self.cases=x['case_design']; self.rows=x['executed_outcomes']

    def test_scripted_resolution_is_not_safe_completion(self):
        s=metrics.summarize(self.cases,self.rows)
        self.assertEqual(s['counts'],{'scheduled':72,'resolvable':48,'correct_resolutions':48,
            'safe_completions':24,'legitimate_uncertain_escalations':24,'confirmed_history_escalations':24,
            'avoidable_escalations':0,'unsupported_stops':0,'invalid_or_censored':0,'new_unsafe_publication_events':0})
        self.assertEqual(len(s['clusters']),1); self.assertIsNone(s['confidence_interval'])

    def test_always_escalate_cannot_get_full_resolution(self):
        for r in self.rows:r['terminal_action']='escalate'
        s=metrics.summarize(self.cases,self.rows)
        self.assertEqual(s['counts']['safe_completions'],0)
        self.assertEqual(s['counts']['avoidable_escalations'],24)
        self.assertEqual(s['cluster_macro_correct_resolution'],0.5)

    def test_unsupported_stop_includes_unknown_evidence(self):
        for r in self.rows:r['terminal_action']='stop'
        self.assertEqual(metrics.summarize(self.cases,self.rows)['counts']['unsupported_stops'],48)

    def test_new_violation_is_not_erased_by_initial_ready_state(self):
        i=next(i for i,c in enumerate(self.cases) if c['preassigned_stratum']=='supported_stop')
        self.rows[i]['new_violation_event_ids']=['new:bad-publication']
        s=metrics.summarize(self.cases,self.rows)['counts']
        self.assertEqual((s['correct_resolutions'],s['safe_completions'],s['unsupported_stops'],s['new_unsafe_publication_events']),(47,23,1,1))

    def test_censoring_stays_in_primary_denominator(self):
        i=next(i for i,c in enumerate(self.cases) if c['preassigned_stratum']=='supported_stop')
        self.rows[i]['censored']=True
        c=metrics.summarize(self.cases,self.rows)['counts']
        self.assertEqual((c['resolvable'],c['correct_resolutions'],c['invalid_or_censored']),(48,47,1))
        j=next(i for i,c in enumerate(self.cases) if c['preassigned_stratum']=='unresolved')
        self.rows[j].update(censored=True,terminal_action='stop')
        self.assertEqual(metrics.summarize(self.cases,self.rows)['counts']['unsupported_stops'],1)

    def test_missing_duplicate_or_fact_answer_rejected(self):
        with self.assertRaises(ValueError):metrics.summarize(self.cases,self.rows[:-1])
        with self.assertRaises(ValueError):metrics.summarize(self.cases,self.rows+[self.rows[0]])
        for r in self.rows:r['execution_kind']='fact_answer'
        with self.assertRaises(ValueError):metrics.summarize(self.cases,self.rows)

    def test_mixed_authorship_rejected(self):
        self.rows[0]['execution_kind']='model_tool_execution'
        with self.assertRaises(ValueError):metrics.summarize(self.cases,self.rows)

    def test_cluster_macro_not_episode_mean(self):
        c=[{'case_id':str(i),'cluster_id':'A' if i<2 else 'B','preassigned_stratum':'supported_stop'} for i in range(3)]
        r=[{'case_id':str(i),'execution_kind':'scripted_program_not_model','terminal_action':'stop' if i<2 else 'invalid',
            'censored':False,'new_violation_event_ids':[]} for i in range(3)]
        self.assertEqual(metrics.summarize(c,r)['cluster_macro_correct_resolution'],0.5)


class AdjudicationPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.packet=review.packet()

    def filled_synthetic_return(self):
        s=review.template(self.packet)
        s['reviewer']={'name':'SYNTHETIC UNIT TEST ONLY','relationship':'synthetic fixture',
            'declares_human':True,'personally_checked':True,'reviewed_git_commit':'a'*40}
        for r in s['referent_reviews']:
            r['prompt_first_declared']=True
            for arm in r['arms'].values():arm.update(interpretation='unclear',rationale='Synthetic objection, not a human verdict.',
                evidence_history_indices=[8,10],actor_scope_clear=False,origin_scripted_clear=False)
        for r in s['design_reviews']:r.update(verdict='uncertain',rationale='Synthetic test only.',evidence_references=['test fixture'])
        return s

    def test_packet_has_twelve_pairs_four_design_questions(self):
        self.assertEqual(len(self.packet['prompt_review']),12)
        self.assertEqual(len(self.packet['design_questions']),4)
        self.assertTrue(all('provider_receipt' not in v for c in self.packet['prompt_review'] for v in c['variants']))

    def test_blank_return_invalid(self):
        self.assertEqual(review.validate(review.template(self.packet),self.packet)['status'],'invalid')

    def test_complete_return_never_registers_or_authorizes(self):
        r=review.validate(self.filled_synthetic_return(),self.packet)
        self.assertEqual(r['status'],'complete_return_unregistered')
        self.assertFalse(r['human_review_registered']);self.assertFalse(r['final_adjudication_registered'])
        self.assertEqual(r['scientific_gate'],'HOLD');self.assertEqual(r['approved_transport_requests'],0)

    def test_stale_or_duplicate_rejected(self):
        s=self.filled_synthetic_return();s['packet_sha256']='0'*64
        self.assertEqual(review.validate(s,self.packet)['status'],'invalid')
        s=self.filled_synthetic_return();s['referent_reviews'].append(copy.deepcopy(s['referent_reviews'][0]))
        self.assertEqual(review.validate(s,self.packet)['status'],'invalid')

    def test_partial_objection_keeps_missing_scope(self):
        s=self.filled_synthetic_return();s['design_reviews']=[]
        r=review.validate(s,self.packet);self.assertEqual(r['status'],'partial_return_unregistered')
        self.assertEqual(len(r['remaining_case_ids']),4)

    def test_boolean_or_out_of_range_event_index_not_evidence(self):
        for index in (True,-1,11):
            s=self.filled_synthetic_return();s['referent_reviews'][0]['arms']['contextual']['evidence_history_indices']=[index]
            self.assertEqual(len(review.validate(s,self.packet)['remaining_case_ids']),1)


if __name__=='__main__':unittest.main()
