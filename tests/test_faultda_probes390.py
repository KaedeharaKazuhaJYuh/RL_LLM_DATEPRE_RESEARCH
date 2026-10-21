import copy
import unittest
from faultda_bench.probes390 import suite as s


class ProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs = s.old.snapshots()[0]['observation']

    def test_window_exact_boundary_and_timezone_equivalence(self):
        for c in s.old.snapshots():
            self.assertEqual(s.reference('window',c['observation'],{}),{'selected_row_ids':['1','2','3','4','5']})

    def test_boundary_counterexamples_change_answers(self):
        rows = [c for c in s.counter_cases() if c['probe']=='window']
        expected = [['1','2','3','4','5','6'],['2','3','4','5'],['6']]
        for c,ids in zip(rows,expected):self.assertEqual(s.reference('window',c['observation'],{})['selected_row_ids'],ids)

    def test_numeric_probe_uses_requested_ids_not_window(self):
        self.assertEqual(s.reference('arithmetic',self.obs,{'row_ids':['0','7']}),{'reference_total':'46.99'})
        self.assertEqual(s.reference('arithmetic',self.obs,{'row_ids':[]}),{'reference_total':'0'})
        self.assertEqual(s.reference('arithmetic',self.obs,{'row_ids':['2','3','4']}),{'reference_total':'70.8'})

    def test_bad_or_duplicate_operands_rejected(self):
        for ids in (['missing'],['2','2'],[2]):
            with self.assertRaises(ValueError):s.reference('arithmetic',self.obs,{'row_ids':ids})

    def test_receipt_target_differs_from_latest_publish(self):
        for c in s.old.snapshots():
            e = s.reference('receipt',c['observation'],{})
            self.assertEqual(e['receipt_request_id'],'request-17')
            self.assertEqual(e['receipt_event_id'],'history:4')
        for c in s.counter_cases():
            if c['probe']=='receipt':self.assertEqual(s.reference('receipt',c['observation'],{})['receipt_event_id'],'history:8')

    def test_inconsistent_receipt_and_reused_id_rejected(self):
        obs = copy.deepcopy(self.obs); obs['history'][-1]['response']['request_id'] = 'wrong'
        with self.assertRaises(ValueError):s.reference('receipt',obs,{})
        obs = copy.deepcopy(self.obs); obs['history'][8]['params']['request_id'] = 'request-17'
        with self.assertRaises(ValueError):s.reference('receipt',obs,{})
        obs = copy.deepcopy(self.obs); obs['history'][-1]['response']['revision'] = False
        with self.assertRaises(ValueError):s.reference('receipt',obs,{})

    def test_responsibility_at_boundary_and_off_by_one(self):
        e = s.reference('responsibility',self.obs,{'history_indices':[10,8,4]})
        self.assertEqual([r['responsibility'] for r in e['roles']],['historical_agent_action','historical_agent_action','current_model_action'])
        c = next(c for c in s.base_cases() if c['probe']=='responsibility')
        bad = s.negative_controls(c)['off_by_one_boundary']
        self.assertFalse(s.grade('responsibility',self.obs,c['query'],bad)['all_fields_correct'])

    def test_boolean_is_not_history_index_and_out_of_range_rejected(self):
        for ids in ([True],[11],[-1],[4,4]):
            with self.assertRaises(ValueError):s.reference('responsibility',self.obs,{'history_indices':ids})

    def test_prompt_pairs_same_data_schema_and_settings(self):
        for c in s.base_cases():
            a = s.body(c['probe'],'contextual',c['observation'],c['query']); b = s.body(c['probe'],'explicit',c['observation'],c['query'])
            self.assertEqual(a['messages'][1],b['messages'][1]); self.assertNotEqual(a['messages'][0],b['messages'][0])
            self.assertEqual({k:v for k,v in a.items() if k!='messages'},{k:v for k,v in b.items() if k!='messages'})
            self.assertTrue(a['messages'][0]['content'].startswith('Use only supplied public facts. This is fact elicitation; no tool executes. '+s.QUESTIONS[c['probe']][0]))

    def test_grade_rejects_duplicate_ids_boolean_revision_nan_and_bad_roles(self):
        for p,q,v in [('window',{}, {'selected_row_ids':['1','1']}),
                      ('arithmetic',{'row_ids':['1']},{'reference_total':'NaN'}),
                      ('receipt',{}, {**s.reference('receipt',self.obs,{}),'receipt_revision':False}),
                      ('responsibility',{'history_indices':[4]},{'roles':[{'history_index':True,'responsibility':'historical_agent_action'}]})]:
            self.assertFalse(s.grade(p,self.obs,q,v)['schema_valid'])

    def test_constant_answers_pass_original_but_not_counterexamples(self):
        r = s.offline()
        for p,name in [('window','constant_old_ids'),('arithmetic','constant_old_sum'),('responsibility','constant_old_roles')]:
            self.assertEqual(r['summary'][p]['original']['negative_control_correct'][name],4)
            self.assertEqual(r['summary'][p]['counter']['negative_control_correct'][name],0)

    def test_all_reference_cases_and_design_only_budget(self):
        r = s.offline(); self.assertEqual(len(r['rows']),27)
        self.assertTrue(all(x['strong_reference_grade']['all_fields_correct'] for x in r['rows']))
        p = s.draft(); self.assertEqual(len(p['cells']),32)
        self.assertEqual(p['approved_transport_requests'],0)
        self.assertEqual(r['new_provider_requests'],0)
        self.assertEqual(p['scientific_gate'],'HOLD')

    def test_no_answers_or_hidden_grades_in_prompt_payload(self):
        import json
        for c in s.base_cases():
            b = s.body(c['probe'],'explicit',c['observation'],c['query']); payload = json.loads(b['messages'][1]['content'])
            self.assertEqual(set(payload),{'observation','query'})
            self.assertEqual(payload['observation'],c['observation'])
            for k in ('source_grade','expected_facts','bad_committed','private_final'):self.assertNotIn(k,json.dumps(b))
