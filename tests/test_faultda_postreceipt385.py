import copy
import json
import unittest
from faultda_bench.postreceipt385 import suite as s


def receipt(value):
    return {'category':'scripted_fixture','request_sent':False,'response':{'choices':[{'message':{'content':json.dumps(value)}}]}}


class PostReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = s.snapshots()

    def test_all_source_cases_and_boundary(self):
        self.assertEqual([c['source_request_index'] for c in self.cases],[1,3,5,7])
        for c in self.cases:
            self.assertEqual(len(c['observation']['history']),11)
            self.assertIsNone(c['observation']['terminal'])

    def test_window_includes_start_excludes_end(self):
        for c in self.cases:
            n = s.numeric_reference(c['observation'])
            self.assertEqual(n['selected_row_ids'],['1','2','3','4','5'])
            self.assertEqual(n['reference_total'],'117.89')
            self.assertFalse(next(r for r in n['rows'] if r['at_end'])['selected'])
            self.assertTrue(next(r for r in n['rows'] if r['at_start'])['selected'])

    def test_reference_ignores_stage_totals_and_input_order(self):
        o = copy.deepcopy(self.cases[0]['observation']); before = s.numeric_reference(o)
        for h in o['history']:
            if h['action']=='stage':h['response']['output']['total'] = -999
            if h['action']=='inputs':h['response']['versions']['v1'].reverse()
        self.assertEqual(before['reference_total'],s.numeric_reference(o)['reference_total'])
        self.assertEqual(before['selected_row_ids'],s.numeric_reference(o)['selected_row_ids'])

    def test_duplicate_row_ids_rejected(self):
        o = copy.deepcopy(self.cases[0]['observation'])
        rows = o['history'][1]['response']['versions']['v1']; rows[0]['id'] = rows[1]['id']
        with self.assertRaises(ValueError):s.numeric_reference(o)

    def test_receipt_target_is_historical_publish_not_receipt_position(self):
        for c in self.cases:
            e = s.expected(c['observation'])
            self.assertEqual(e['receipt_event_id'],'history:4')
            self.assertEqual(e['receipt_responsibility'],'historical_agent_action')
            self.assertEqual(e['initial_error_responsibility'],'environment_setup')
        self.assertEqual([s.expected(c['observation'])['terminal_action'] for c in self.cases],['stop','escalate','escalate','stop'])

    def test_no_answers_or_private_labels_in_request(self):
        for c in self.cases:
            body = s.request(c['observation'])
            self.assertEqual(json.loads(body['messages'][1]['content']),c['observation'])
            for key in ('source_grade','expected_facts','bad_committed','bad_never_committed','private_final'):
                self.assertNotIn(key,json.dumps(body))

    def test_separate_wrong_membership_from_arithmetic(self):
        obs = self.cases[0]['observation']; v = s.expected(obs)
        v['selected_row_ids'] = ['1','2','3','5','6']; v['reference_total'] = '117.5966666666667'
        g = s.grade(receipt(v),obs)
        self.assertFalse(g['field_correct']['selected_row_ids'])
        self.assertFalse(g['field_correct']['reference_total'])
        self.assertTrue(g['arithmetic_given_reported_row_ids'])
        v['reference_total'] = '100'
        self.assertFalse(s.grade(receipt(v),obs)['arithmetic_given_reported_row_ids'])

    def test_nonexistent_row_is_unscorable_arithmetic(self):
        obs = self.cases[0]['observation']; v = s.expected(obs); v['selected_row_ids'] = ['missing']
        self.assertIsNone(s.grade(receipt(v),obs)['arithmetic_given_reported_row_ids'])

    def test_strict_schema_and_numeric_input(self):
        obs = self.cases[0]['observation']
        for k,value in [('receipt_revision',False),('current_report_correct',1),('reference_total','NaN'),
                        ('reference_total','1e9999999'),('selected_row_ids',['1','1']),('terminal_action','publish')]:
            with self.subTest(k=k,value=value):
                v = s.expected(obs); v[k] = value
                self.assertFalse(s.grade(receipt(v),obs)['schema_valid'])
        for v in ([],{},None):self.assertFalse(s.grade(receipt(v),obs)['schema_valid'])

    def test_literal_reason_not_internal_or_unique_row_attribution(self):
        a = s.offline()['literal_equation_audit']
        self.assertTrue(a['arithmetic_of_stated_terms_correct'])
        self.assertFalse(a['terms_match_required_row_value_multiset'])
        self.assertFalse(a['exact_selected_row_ids_identifiable'])
        self.assertEqual(a['missing_value_multiset'],['23.6'])
        self.assertEqual(a['extra_value_multiset'],['23.3066666666667'])

    def test_scripted_vs_failure_denominators(self):
        r = s.execute(s.protocol(),s.fixture,'scripted')
        self.assertEqual(r['summary']['all_fields_correct'],4)
        self.assertEqual(r['summary']['actual_provider_requests'],0)
        r = s.execute(s.protocol(),lambda b:{'category':'provider_error','request_sent':True},'live')
        self.assertEqual(r['summary']['snapshots'],4)
        self.assertEqual(r['summary']['all_fields_correct'],0)
        self.assertEqual(r['summary']['provider_errors'],4)

    def test_stale_plan_rejected_before_sender(self):
        p = s.protocol(); p['max_transport_requests'] = 5; calls = []
        with self.assertRaises(ValueError):s.execute(p,lambda b:calls.append(b),'live')
        self.assertEqual(calls,[])
