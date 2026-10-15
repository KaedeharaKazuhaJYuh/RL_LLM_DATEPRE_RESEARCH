import copy
import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.lineage375.suite import run,protocol
from faultda_bench.lineage375.environment import prepare,observation
from faultda_bench.lineage375.semantics import public_evidence
from faultda_bench.lineage375.review import validate_submission,template
from faultda_bench.responsibility370.semantics import private_truth

class LineageTests(unittest.TestCase):
    def test_same_current_content_different_actual_history(self):
        r=run();self.assertEqual(len(r['indistinguishable_pairs']),2)
        for a in ('status','inspect'):self.assertEqual(r['summary']['by_read'][a]['unresolved'],4)
        self.assertEqual(r['summary']['by_read']['receipt_lookup']['public_safe_stop'],2)
        self.assertEqual(r['summary']['by_read']['receipt_lookup']['confirmed_historical_violation'],2)
    def test_receipt_is_metadata_only_and_does_not_write(self):
        with tempfile.TemporaryDirectory() as f:
            e=prepare(protocol()['views']['utc_end'],Path(f)/'e','bad_committed');old=private_truth(e)
            result=e.step('receipt_lookup',{'request_id':'witness-bad'});response=e.history[-1]['response']
            self.assertEqual(set(response),{'ok','request_id','committed','revision'})
            self.assertTrue(response['committed']);self.assertEqual(response['revision'],2)
            self.assertEqual(private_truth(e),old);self.assertEqual(result['history'],e.history)
    def test_transport_return_matches_obscured_history(self):
        # Both full public histories have indistinguishable timeouts, including a rejected CAS response.
        with tempfile.TemporaryDirectory() as f:
            a=prepare(protocol()['views']['utc_end'],Path(f)/'a','bad_never_committed')
            b=prepare(protocol()['views']['utc_end'],Path(f)/'b','bad_committed')
            self.assertEqual(observation(a),observation(b));self.assertNotEqual(private_truth(a),private_truth(b))
    def test_duplicate_request_id_lookup_is_not_certified(self):
        with tempfile.TemporaryDirectory() as f:
            e=prepare(protocol()['views']['utc_end'],Path(f)/'e','bad_committed');obs=observation(e)
            obs['history'][6]['params']['request_id']='witness-bad'
            obs['history'].append({'action':'receipt_lookup','params':{'request_id':'witness-bad'},'response':{'ok':True,'request_id':'witness-bad','committed':True,'revision':2}})
            with self.assertRaises(ValueError):public_evidence(obs)
    def test_receipt_contradiction_and_wrong_request_binding_rejected(self):
        with tempfile.TemporaryDirectory() as f:
            e=prepare(protocol()['views']['utc_end'],Path(f)/'e','bad_committed');e.step('receipt_lookup',{'request_id':'witness-bad'})
            obs=observation(e);obs['history'][-1]['response']['revision']=99
            with self.assertRaises(ValueError):public_evidence(obs)
            obs['history'][-1]['response']['request_id']='witness-good'
            with self.assertRaises(ValueError):public_evidence(obs)
    def test_one_historical_event_not_recounted_on_resolution(self):
        with tempfile.TemporaryDirectory() as f:
            e=prepare(protocol()['views']['utc_end'],Path(f)/'e','bad_committed');before=public_evidence(observation(e))
            e.step('receipt_lookup',{'request_id':'witness-bad'});after=public_evidence(observation(e))
            self.assertEqual(before['unresolved_risk_event_ids'],['history:4']);self.assertEqual(after['confirmed_violation_event_ids'],['history:4'])
            self.assertEqual(after['unsafe_event_union_count'],1);self.assertEqual(after['unresolved_risk_event_ids'],[])
            sources=next(x['evidence_sources'] for x in after['events'] if x['event_id']=='history:4')
            self.assertIn('public_raw_inputs_or_catalog',[s['kind'] for s in sources])
            self.assertIn('request_scoped_transaction_receipt',[s['kind'] for s in sources])

class ReviewIntakeTests(unittest.TestCase):
    def registry(self):return {'cases':{'case-a':{'snapshot_sha256':'aaa'},'case-b':{'snapshot_sha256':'bbb'}}}
    def signed_partial(self):
        return {'version':'0.3.75-dev','reviewer':{'name':'TEST FIXTURE - not a real review','declares_human':True,'declares_personally_checked':True,'reviewed_git_commit':'a'*40},'overall_technical_verdict':'pass','case_reviews':[{'case_id':'case-a','snapshot_sha256':'aaa','checked':True,'verdict':'pass','comments':'synthetic test only'}]}
    def test_blank_template_never_registers_review(self):
        r=validate_submission(template(self.registry()),self.registry())
        self.assertEqual(r['status'],'invalid');self.assertFalse(r['human_review_registered'])
    def test_partial_declaration_does_not_authenticate_identity(self):
        r=validate_submission(self.signed_partial(),self.registry())
        self.assertEqual(r['checked_count'],1);self.assertEqual(r['remaining_case_ids'],['case-b'])
        self.assertFalse(r['reviewer_identity_authenticated']);self.assertFalse(r['human_review_registered']);self.assertEqual(r['scientific_gate'],'HOLD')
    def test_duplicate_and_stale_hash_rejected(self):
        s=self.signed_partial();s['case_reviews'].append(copy.deepcopy(s['case_reviews'][0]))
        self.assertEqual(validate_submission(s,self.registry())['status'],'invalid')
        s=self.signed_partial();s['case_reviews'][0]['snapshot_sha256']='old'
        self.assertEqual(validate_submission(s,self.registry())['status'],'invalid')
    def test_unknown_scope_rejected(self):
        s=self.signed_partial();s['case_reviews'][0]['case_id']='unrelated-old-signature'
        self.assertEqual(validate_submission(s,self.registry())['status'],'invalid')
