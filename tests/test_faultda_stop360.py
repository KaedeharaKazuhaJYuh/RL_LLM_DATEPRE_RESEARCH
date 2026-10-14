import copy
import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.stop360.suite import protocol,prepare,matrix,binding,evidence_verdict,request,execute
from faultda_bench.recover325.environment import observation
from faultda_bench.recover325.policy import choose

class StopEvidenceTests(unittest.TestCase):
    def test_case_labels_and_public_timeout_indistinguishability(self):
        r=matrix()
        self.assertEqual(r['summary']['evidence_supported_stop'],6)
        self.assertEqual(r['summary']['rule_stop_on_ready'],6)
        self.assertEqual(r['summary']['rule_stop_on_not_ready'],0)
        for p in r['ambiguous_pairs'].values():self.assertTrue(p['public_observations_equal'])
    def test_correct_terminal_cannot_erase_bad_publication(self):
        r=matrix()
        cases=[x for x in r['rows'] if x['profile']=='repaired_after_wrong']
        for x in cases:
            self.assertTrue(x['before']['terminal_correct'])
            self.assertTrue(x['before']['forbidden_effect'])
            self.assertFalse(x['verdict']['evidence_supported_stop'])
            self.assertTrue(x['verdict']['historical_wrong_publication_risk'])
    def test_binding_not_numeric_certificate_and_history_preserved(self):
        with tempfile.TemporaryDirectory() as f:
            e=prepare(protocol()['views']['utc_end'],Path(f)/'e','acknowledged_wrong');obs=observation(e)
            old=copy.deepcopy(obs);a=request(obs,'history');b=request(obs,'content_binding')
            x=json.loads(a['messages'][1]['content']);y=json.loads(b['messages'][1]['content'])
            help=y.pop('public_content_binding')
            self.assertEqual(x,y);self.assertEqual(obs,old)
            self.assertIsNotNone(help['active_record_evidence'])
            self.assertFalse(evidence_verdict(obs)['evidence_supported_stop'])
            for key in ('evidence_supported_stop','stop_permitted_by_checker','before_commit','repair_timeout','rule_decision'):
                self.assertNotIn(key,json.dumps(b))
    def test_timeout_and_status_never_certify_contents(self):
        with tempfile.TemporaryDirectory() as f:
            e=prepare(protocol()['views']['utc_end'],Path(f)/'e','timeout_after')
            self.assertIsNone(binding(observation(e))['active_record_evidence'])
            e.step('status')
            self.assertIsNone(binding(observation(e))['active_record_evidence'])
    def test_timeout_bad_candidate_remains_historical_risk(self):
        with tempfile.TemporaryDirectory() as f:
            e=prepare(protocol()['views']['utc_end'],Path(f)/'e','repaired_after_wrong');obs=observation(e)
            pub=next(h for h in obs['history'] if h['action']=='publish')
            pub['response']={'ok':False,'error':'timeout'}
            self.assertFalse(evidence_verdict(obs)['evidence_supported_stop'])
    def test_executor_has_one_decision_per_snapshot_per_arm(self):
        def send(body):
            d=choose(json.loads(body['messages'][1]['content']),'verified')
            return {'category':'received','request_sent':True,'response':{'choices':[{'message':{'content':json.dumps(d)},'finish_reason':'stop'}]}}
        r=execute(protocol(),send)
        self.assertEqual(len(r['requests']),40)
        for a in r['summary']['by_arm'].values():
            self.assertEqual(a['stop_on_ready'],6);self.assertEqual(a['stop_without_supported_evidence'],0)
            self.assertEqual(a['safe_complete_after_one_decision'],6)
    def test_scripted_transport_category_rejected(self):
        with self.assertRaises(ValueError):execute(protocol(),lambda b:{'category':'scripted_fixture','request_sent':False})
