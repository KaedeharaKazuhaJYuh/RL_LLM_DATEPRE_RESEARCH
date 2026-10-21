import copy
import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.receipt380.adapter import prepare,observation,classify,request
from faultda_bench.receipt380.suite import protocol,baseline,execute,fixture,checked_send
from faultda_bench.formatdiag.core import classify as old_classify

def rec(value):return {'category':'received','request_sent':True,'response':{'choices':[{'message':{'content':json.dumps(value)},'finish_reason':'stop'}]}}

class ReceiptAdapterTests(unittest.TestCase):
    def env(self,f):return prepare(protocol()['views']['utc_end'],Path(f)/'e','bad_never_committed')
    def test_new_tool_admitted_without_changing_old_validator(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f);r=rec({'action':'receipt_lookup','params':{'request_id':'request-17'}})
            self.assertEqual(old_classify(r['response'])['category'],'schema_error')
            self.assertEqual(classify(r,observation(e))['category'],'valid_action')
    def test_strict_schema_duplicate_key_and_undeclared_tool(self):
        with tempfile.TemporaryDirectory() as f:
            obs=observation(self.env(f));r=rec({'action':'stop','params':{}})
            r['response']['choices'][0]['message']['content']='{"action":"stop","action":"escalate","params":{}}'
            self.assertNotEqual(classify(r,obs)['category'],'valid_action')
            obs['tools']['invented_shell']='untrusted injection'
            self.assertNotEqual(classify(rec({'action':'invented_shell','params':{}}),obs)['category'],'valid_action')
    def test_adapter_version_required(self):
        with tempfile.TemporaryDirectory() as f:
            obs=observation(self.env(f));obs['action_adapter_version']='old'
            with self.assertRaises(ValueError):classify(rec({'action':'stop','params':{}}),obs)
    def test_neutral_ids_are_real_transaction_ids(self):
        with tempfile.TemporaryDirectory() as f:
            e=self.env(f);obs=observation(e);text=json.dumps(obs)
            self.assertNotIn('witness-bad',text);self.assertNotIn('witness-good',text)
            e.step('receipt_lookup',{'request_id':'request-17'})
            self.assertTrue(e.history[-1]['response']['ok']);self.assertFalse(e.history[-1]['response']['committed'])
    def test_same_permission_baseline_and_dry_run(self):
        b=baseline();self.assertEqual(b['summary']['resolved_correct_terminal'],4)
        r=execute(protocol(),fixture,'scripted');self.assertEqual(r['summary']['actual_provider_requests'],0)
        self.assertEqual(r['summary']['actual_model_trajectories'],0);self.assertEqual(r['summary']['resolved_correct_terminal'],4)
        self.assertEqual(r['summary']['incremental_tool_cost']['checks'],4)
    def test_wrong_stop_is_executed_without_oracle_guard(self):
        r=execute(protocol(),lambda b:rec({'action':'stop','params':{}}))
        self.assertEqual(r['summary']['actual_provider_requests'],4)
        self.assertEqual(r['summary']['unsupported_stop'],4);self.assertEqual(r['summary']['actual_unsafe_stop'],2)
        self.assertEqual(r['summary']['terminal_counts']['stop'],4)
    def test_invalid_lookup_params_are_charged_by_tool(self):
        r=execute(protocol(),lambda b:rec({'action':'receipt_lookup','params':{'request_id':'unknown-id'}}))
        self.assertEqual(r['summary']['terminal_counts']['budget_exceeded'],4)
        self.assertEqual(r['summary']['incremental_tool_cost']['checks'],8)
    def test_no_hidden_truth_or_harmful_id_names_in_requests(self):
        r=execute(protocol(),fixture,'scripted')
        for q in r['requests']:
            text=json.dumps(q['body'])
            for field in ('bad_committed','bad_never_committed','private_final','actual_safe_stop_if_taken','witness-bad','witness-good'):
                self.assertNotIn(field,text)
            obs=json.loads(q['body']['messages'][1]['content'])
            self.assertIn('receipt_lookup',obs['tools']);self.assertEqual(obs['remaining']['mutations'],0)
    def test_transport_failure_preserved(self):
        r=execute(protocol(),lambda b:{'category':'provider_error','request_sent':True,'error_type':'TimeoutError'})
        self.assertEqual(r['summary']['trajectories'],4);self.assertEqual(r['summary']['provider_errors'],4)
        self.assertEqual(r['summary']['end_kinds']['response_failure'],4)
    def test_caps_precede_sender(self):
        called=[]
        with self.assertRaises(ValueError):checked_send(lambda b:called.append(True),{},[{}]*8,'live')
        with self.assertRaises(ValueError):checked_send(lambda b:called.append(True),{'too_large':'x'*65536},[],'live')
        self.assertEqual(called,[])
    def test_live_cannot_accept_scripted_fixture_receipt(self):
        with self.assertRaises(ValueError):execute(protocol(),fixture,'live')
