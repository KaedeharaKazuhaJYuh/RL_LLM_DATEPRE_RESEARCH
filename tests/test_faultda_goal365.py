import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.goal365.suite import protocol,request,truth,response,diagnostic_score,execute,ARMS
from faultda_bench.stop360.suite import prepare
from faultda_bench.recover325.environment import observation
from faultda_bench.recover325.policy import choose

def receipt(value):return {'category':'received','request_sent':True,'response':{'choices':[{'message':{'content':json.dumps(value)},'finish_reason':'stop'}]}}

class GoalDiagnosisTests(unittest.TestCase):
    def test_matched_user_observation_and_conflict_free_system(self):
        with tempfile.TemporaryDirectory() as f:
            obs=observation(prepare(protocol()['views']['utc_end'],Path(f)/'e','initial_correct'))
            bodies={a:request(obs,a) for a in ARMS}
            self.assertEqual(len({b['messages'][1]['content'] for b in bodies.values()}),1)
            for a,b in bodies.items():
                text=b['messages'][0]['content']
                self.assertEqual('Completion criterion:' in text,a.startswith('clear'))
                self.assertEqual('reference_total' in text,a.endswith('diagnosis'))
                if a.endswith('diagnosis'):self.assertNotIn('exactly action and params;',text)
                self.assertNotIn('117.89',text)
                self.assertNotIn('public_content_binding',b['messages'][1]['content'])
    def test_strict_diagnostic_types(self):
        d={'reference_total':True,'active_content_known':True,'active_total':1,'historical_publication_risk':False,'task_complete':True,'decision':{'action':'stop','params':{}}}
        self.assertEqual(response(receipt(d),'base_diagnosis')[0]['category'],'diagnostic_schema_error')
        d['reference_total']=117.89;d['task_complete']=1
        self.assertEqual(response(receipt(d),'base_diagnosis')[0]['category'],'diagnostic_schema_error')
    def test_huge_integer_diagnosis_rejected_without_crash(self):
        d={'reference_total':10**400,'active_content_known':True,'active_total':1,'historical_publication_risk':False,'task_complete':True,'decision':{'action':'stop','params':{}}}
        self.assertEqual(response(receipt(d),'base_diagnosis')[0]['category'],'diagnostic_schema_error')
    def test_wrong_facts_do_not_guard_actions(self):
        def send(body):
            if 'reference_total' in body['messages'][0]['content']:
                return receipt({'reference_total':-999,'active_content_known':False,'active_total':None,'historical_publication_risk':False,'task_complete':False,'decision':{'action':'stop','params':{}}})
            return receipt({'action':'escalate','params':{}})
        r=execute(protocol(),send)
        for x in r['rows']:
            if x['arm'].endswith('diagnosis'):
                self.assertEqual(x['evaluation']['terminal'],'stop')
                self.assertFalse(x['diagnostic_score']['reference_total'])
    def test_no_hidden_score_and_balanced_order(self):
        p=protocol()
        for a in ARMS:
            for j in range(4):self.assertEqual(sum(o[j]==a for o in p['arm_orders']),5)
        def send(body):
            text=json.dumps(body)
            for field in ('private_public_fact_reference','pre_evaluation','evidence_supported_stop','profile','rule_decision'):
                self.assertNotIn('"'+field+'"',text)
            obs=json.loads(body['messages'][1]['content']);d=choose(obs,'verified')
            return receipt({**truth(obs),'decision':d} if 'reference_total' in body['messages'][0]['content'] else d)
        r=execute(p,send)
        self.assertEqual(len(r['requests']),80)
        for a in r['summary']['by_arm'].values():self.assertEqual(a['stop_on_ready'],6)
    def test_unknown_timeout_not_private_contents(self):
        with tempfile.TemporaryDirectory() as f:
            task=protocol()['views']['utc_end'];answers=[]
            for p in ('timeout_before','timeout_after'):
                obs=observation(prepare(task,Path(f)/p,p));answers.append(truth(obs))
            self.assertEqual(answers[0],answers[1]);self.assertFalse(answers[1]['active_content_known']);self.assertIsNone(answers[1]['active_total'])
    def test_supplier_failure_stays_in_denominator(self):
        r=execute(protocol(),lambda b:{'category':'provider_error','request_sent':True,'error_type':'TimeoutError'})
        for a in r['summary']['by_arm'].values():self.assertEqual(a['snapshots'],20);self.assertEqual(a['invalid_responses'],20)
    def test_scripted_receipt_rejected(self):
        with self.assertRaises(ValueError):execute(protocol(),lambda b:{'category':'scripted_fixture','request_sent':False})
