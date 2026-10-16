import copy
import json
import unittest
from faultda_bench.coherent395 import pilot as p


class PilotTests(unittest.TestCase):
    def test_selection_covers_all_conditions_and_balances_answers(self):
        cs = p.cases(); self.assertEqual(len(cs),12)
        self.assertEqual(sum(c['expected_receipt_facts']['receipt_committed'] for c in cs),6)
        for key in ('request-17','request-23','request-31'):
            self.assertEqual(sum(c['expected_receipt_facts']['receipt_request_id']==key for c in cs),4)
        self.assertEqual(sum(c['expected_receipt_facts']['receipt_responsibility']=='historical_agent_action' for c in cs),6)

    def test_only_final_sentence_changes(self):
        for c in p.cases():
            a = p.body(c['public_observation'],'contextual'); b = p.body(c['public_observation'],'explicit')
            self.assertEqual(a['messages'][1],b['messages'][1])
            self.assertEqual(a['messages'][0]['content'].rsplit('. ',1)[0],b['messages'][0]['content'].rsplit('. ',1)[0])
            self.assertEqual({k:v for k,v in a.items() if k!='messages'},{k:v for k,v in b.items() if k!='messages'})

    def test_payload_contains_no_grader_or_hidden_mode(self):
        for c in p.cases():
            b = p.body(c['public_observation'],'explicit'); obs = json.loads(b['messages'][1]['content'])
            self.assertEqual(set(obs),{'observation'})
            for key in ('bad_committed','bad_never_committed','expected_receipt_facts','private_truth'):self.assertNotIn(key,json.dumps(b))

    def test_scripted_dry_run_and_failure_denominator(self):
        r = p.execute(p.protocol(),p.fixture,'scripted')
        self.assertEqual(r['summary']['actual_provider_requests'],0)
        self.assertEqual(r['summary']['paired_all_correct']['both_correct'],12)
        r = p.execute(p.protocol(),lambda b:{'category':'provider_error','request_sent':True},'live')
        self.assertEqual(r['summary']['provider_errors'],24)
        self.assertEqual(r['summary']['paired_all_correct']['neither_correct'],12)

    def test_strict_schema_boolean_revision_and_wrong_role(self):
        c = p.cases()[0]; e = c['expected_receipt_facts']; v = copy.deepcopy(e)
        def receipt(v):return {'category':'scripted_fixture','request_sent':False,'response':{'choices':[{'message':{'content':json.dumps(v)}}]}}
        v['receipt_revision'] = False
        self.assertFalse(p.grade(receipt(v),e)['schema_valid'])
        v = {**e,'receipt_responsibility':'current_model_action' if e['receipt_responsibility']=='historical_agent_action' else 'historical_agent_action'}
        self.assertTrue(p.grade(receipt(v),e)['exact_target_wrong_role'])
        self.assertFalse(p.grade(receipt(v),e)['all_fields_correct'])

    def test_duplicate_json_keys_rejected(self):
        r = {'category':'received','request_sent':True,'response':{'choices':[{'message':{'content':'{"receipt_request_id":"a","receipt_request_id":"b"}'}}]}}
        self.assertFalse(p.grade(r,p.cases()[0]['expected_receipt_facts'])['schema_valid'])

    def test_stale_plan_rejected_before_any_send(self):
        plan = p.protocol(); plan['max_transport_requests'] = 25; calls = []
        with self.assertRaises(ValueError):p.execute(plan,lambda b:calls.append(b),'live')
        self.assertEqual(calls,[])
