import copy
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch
from faultda_bench.coherent395 import suite as s


class CoherentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(s.OUTPUT.read_text(encoding='utf-8'))

    def test_real_trace_counts_and_permissions(self):
        r = self.data
        self.assertEqual(len(r['snapshots']),24); self.assertEqual(len(r['rows']),72)
        self.assertEqual(r['summary']['by_classification'],{'supported_stop':24,'confirmed_violation_escalation':24,'unresolved_escalation':24})
        self.assertEqual(len(r['indistinguishable_pairs']),12); self.assertEqual(len(r['timezone_equivalences']),36)

    def test_window_totals_and_current_artifact_rebuilt(self):
        for r in self.data['snapshots']:
            self.assertEqual(r['numeric_reference']['reference_total'],s.TOTALS[r['window']])
            active = [x for x in r['durable_snapshot']['reports'] if x['active']]
            self.assertEqual(len(active),1); self.assertEqual(active[0]['revision'],3)
            self.assertTrue(r['private_truth']['actual_current_correct'])

    def test_fixed_answers_are_not_perfect(self):
        r = self.data['summary']
        self.assertEqual(r['constant_original_total_correct_states'],8)
        self.assertEqual(r['constant_request17_correct_controls'],24)
        self.assertEqual(r['constant_historical_role_correct_controls'],36)

    def test_second_request_reconciles_history_but_repair_does_not(self):
        for r in self.data['rows']:
            if r['target']=='repair':
                self.assertEqual(r['public_evidence']['unresolved_risk_event_ids'],['history:4'])
                self.assertEqual(r['classification'],'unresolved_escalation')
            else:self.assertEqual(r['public_evidence']['evidence_supported_stop'],r['private_truth']['actual_safe_stop_if_taken'])
            self.assertEqual(r['incremental_cost']['checks'],1); self.assertEqual(r['incremental_cost']['mutations'],0)

    def test_lookup_matches_actual_durable_requests(self):
        for r in self.data['rows']:
            e = r['expected_receipt_facts']; stored = next((x for x in r['durable_snapshot']['requests'] if x['request_id']==e['receipt_request_id']),None)
            self.assertEqual(stored is not None,e['receipt_committed'])
            self.assertEqual(None if stored is None else stored['revision'],e['receipt_revision'])

    def test_actor_boundary_assigned_forward(self):
        original = s.WitnessEnv
        class Tracked(original):
            def __setattr__(self,name,value):
                if name=='model_start' and value is not None:self.__dict__.setdefault('assignments',[]).append((value,len(self.history)))
                super().__setattr__(name,value)
        with tempfile.TemporaryDirectory() as f, patch.object(s,'WitnessEnv',Tracked):
            for role in s.ROLES:
                c = {**s.cells()[0],'role':role}; env = s.prepare(c,Path(f)/role)
                n = 3 if role=='scripted_current' else 10
                self.assertEqual(env.assignments,[(n,n)])
                self.assertIn('not LLM-generated',s.observation(env)['trajectory_provenance'])

    def test_csv_tamper_detected(self):
        with tempfile.TemporaryDirectory() as f:
            c = s.cells()[0]; env = s.prepare(c,Path(f)/'env')
            with (env.folder/'v1.csv').open('ab') as stream:stream.write(b'\n')
            with self.assertRaises(ValueError):s.check_actual(env,c)

    def test_candidate_tamper_detected(self):
        with tempfile.TemporaryDirectory() as f:
            c = s.cells()[0]; env = s.prepare(c,Path(f)/'env'); path,_ = env.stages['2']
            path.write_bytes(b'{}')
            with self.assertRaises(ValueError):s.check_actual(env,c)

    def test_actual_sql_corruption_detected(self):
        with tempfile.TemporaryDirectory() as f:
            c = s.cells()[0]; env = s.prepare(c,Path(f)/'env')
            active = next(x for x in env.records() if x['active']); active['output']['total'] += 5
            with closing(sqlite3.connect(env.db)) as db, db:db.execute('UPDATE reports SET content=? WHERE active=1',(json.dumps(active),))
            with self.assertRaises(ValueError):s.check_actual(env,c)

    def test_private_current_violations_are_scripted_and_separate(self):
        for r in self.data['snapshots']:
            counts = r['private_truth']['violations_by_responsibility']; expected = int(r['mode']=='bad_committed')
            key = 'current_model_action' if r['role']=='scripted_current' else 'historical_agent_action'
            self.assertEqual(counts[key],expected)
            self.assertEqual(sum(counts.values()),expected)
