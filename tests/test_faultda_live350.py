import json
import unittest
from faultda_bench.live350.suite import protocol, execute, action_request, checked_send
from faultda_bench.runtime335.suite import fixture


def mock_send(body, probe):
    old = fixture(body, probe)
    return {**old, 'category': 'received', 'request_sent': True}


class LiveBoundaryTests(unittest.TestCase):
    def test_eight_action_instruction_matches_actual_horizon(self):
        r = execute(protocol(), mock_send)
        for q in r['requests']:
            if q['probe'] == 'action':
                text = q['body']['messages'][0]['content']
                self.assertIn('at most eight further tool actions', text)
                self.assertNotIn('at most six further tool actions', text)

    def test_balanced_arm_order(self):
        orders = protocol()['arm_orders']
        self.assertEqual(sum(o[0] == 'direct' for o in orders), 4)
        for i in range(4): self.assertEqual(orders[i], list(reversed(orders[i+4])))

    def test_live_boundary_rejects_script_fixture(self):
        with self.assertRaises(ValueError): checked_send(lambda b,p: {'category':'scripted_fixture','request_sent':False}, {}, 'record', [])

    def test_global_cap_precedes_transport(self):
        called=[]
        def send(body, probe): called.append(True); return mock_send(body, probe)
        with self.assertRaises(ValueError): checked_send(send, {}, 'record', [{}]*136)
        self.assertEqual(called, [])

    def test_exact_record_is_not_reference_substituted(self):
        def send(body, probe):
            if probe=='record': return {'category':'received','request_sent':True,'response':{'choices':[{'message':{'content':'{"bad":"record"}'},'finish_reason':'stop'}]}}
            return mock_send(body, probe)
        r=execute(protocol(),send)
        for row in r['rows']:
            self.assertEqual(row['action_record'], {'bad':'record'} if row['arm']=='shared_model_record' else None)

    def test_provider_error_preserves_unavailable_record(self):
        def send(body, probe):
            if probe=='record': return {'category':'provider_error','request_sent':True,'error_type':'TimeoutError'}
            return mock_send(body, probe)
        r=execute(protocol(),send)
        self.assertEqual(r['summary']['provider_errors'],8)
        for row in r['rows']:
            if row['arm']=='shared_model_record':self.assertEqual(row['action_record'],{'model_record_unavailable':True})

    def test_score_and_hidden_profile_not_in_requests(self):
        r=execute(protocol(),mock_send)
        for q in r['requests']:
            text=json.dumps(q['body'])
            self.assertNotIn('_before_failures_remaining',text)
            self.assertNotIn('before_twice',text)
            self.assertNotIn('stop_permitted_by_checker',text)
