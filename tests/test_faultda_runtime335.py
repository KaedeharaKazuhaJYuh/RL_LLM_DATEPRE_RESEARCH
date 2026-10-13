import copy
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from faultda_bench.runtime335.suite import protocol, execute, fixture, scripted_receipt, action_request, checked_send


class RuntimeTests(unittest.TestCase):
    def test_dry_run_creates_no_provider_client(self):
        with patch('faultda_bench.pilot.client.Client.__init__', side_effect=AssertionError('provider client forbidden')):
            r = execute(protocol(), fixture)
        self.assertEqual(r['summary']['scripted_trajectories'], 16)
        self.assertEqual(r['summary']['scripted_record_envelopes'], 8)
        self.assertEqual(r['summary']['actual_provider_requests'], 0)
        self.assertEqual(r['summary']['new_model_results'], 0)

    def test_matched_initial_context_and_private_fields_not_sent(self):
        r = execute(protocol(), fixture)
        for state in range(8):
            pair = [v for v in r['rows'] if v['state'] == state]
            bodies = [r['requests'][v['request_indices'][0]]['body'] for v in pair]
            self.assertEqual(bodies[0]['messages'][:2], bodies[1]['messages'][:2])
            self.assertNotIn('before_twice', str(bodies)); self.assertNotIn('_before_failures_remaining', str(bodies))

    def test_record_error_not_replaced_by_reference(self):
        def send(body, probe): return scripted_receipt({'bad': 'record'}) if probe == 'record' else fixture(body, probe)
        r = execute(protocol(), send)
        for row in r['rows']:
            self.assertEqual(row['action_record'], {'bad': 'record'} if row['arm'] == 'shared_model_record' else None)

    def test_missing_record_has_explicit_unavailable_marker(self):
        def send(body, probe): return scripted_receipt(None) if probe == 'record' else fixture(body, probe)
        r = execute(protocol(), send)
        for row in r['rows']:
            if row['arm'] == 'shared_model_record': self.assertEqual(row['action_record'], {'model_record_unavailable': True})

    def test_provider_receipt_cannot_be_accepted_as_fixture(self):
        def send(body, probe): return {'category': 'received', 'request_sent': True}
        with self.assertRaises(ValueError): checked_send(send, {}, 'record', [])

    def test_global_budget_checked_before_callback(self):
        invoked = []
        def send(body, probe): invoked.append(True); return scripted_receipt(None)
        with self.assertRaises(ValueError): checked_send(send, {}, 'record', [{}]*136)
        self.assertEqual(invoked, [])

    def test_modified_plan_rejected(self):
        p = protocol(); p['max_transport_requests'] = 137
        with self.assertRaises(ValueError): execute(p, fixture)

    def test_action_prompts_have_no_active_report_program_verdict(self):
        r = execute(protocol(), fixture)
        for q in r['requests']:
            if q['probe'] == 'action':
                self.assertNotIn('stop_permitted_by_checker', str(q['body']))
                self.assertNotIn('active_report_verified', str(q['body']))
