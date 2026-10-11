import copy
import tempfile
import unittest
from pathlib import Path
from faultda_bench.publication.audit import gate, findings, summarize
from faultda_bench.evidence.core import tasks
from faultda_bench.trust.environment import ComputeFaultEnv
from faultda_bench.pilot.contract import public_observation
from faultda_bench.semantic.compute import parameters


class PublicationTests(unittest.TestCase):
    def test_gate_selects_requested_stage_and_needs_evidence(self):
        task=next(t for t in tasks() if t['contract']['family']=='window')
        with tempfile.TemporaryDirectory() as folder:
            env=ComputeFaultEnv(task,Path(folder)/'env',mode='healthy',evidence='E1',budget=3)
            env.step('inspect'); env.step('inputs')
            params=parameters(task['contract'],task['catalog']); env.step('stage',params)
            publish={'action':'publish','params':{'stage_id':'1','request_id':'r','expected_revision':1,'mode':'replace'}}
            self.assertEqual(gate(public_observation(env),publish)['reason'],'independent_evidence_unavailable')
            env.step('catalog')
            self.assertTrue(gate(public_observation(env),publish)['allow'])
            wrong={**params,'closed':'both'}; env.step('stage',wrong)
            self.assertTrue(gate(public_observation(env),publish)['allow'])
            publish['params']['stage_id']='2'
            self.assertEqual(gate(public_observation(env),publish)['reason'],'candidate_contract_mismatch')
            publish['params']['stage_id']='missing'
            self.assertEqual(gate(public_observation(env),publish)['reason'],'candidate_not_observed')

    def test_bad_compute_and_public_only_gate(self):
        task=tasks()[0]
        with tempfile.TemporaryDirectory() as folder:
            env=ComputeFaultEnv(task,Path(folder)/'env',mode='shared_compute',evidence='E1',budget=3)
            env.step('inspect'); env.step('inputs'); env.step('catalog')
            env.step('stage',parameters(task['contract'],task['catalog']))
            obs=public_observation(env)
            publish={'action':'publish','params':{'stage_id':'1','request_id':'r','expected_revision':1,'mode':'replace'}}
            self.assertEqual(gate(obs,publish)['reason'],'candidate_numeric_mismatch')
            altered=copy.deepcopy(obs); altered['private_oracle']='fake'; altered['hidden_mode']='healthy'
            self.assertEqual(gate(obs,publish),gate(altered,publish))

    def test_all_bad_publications_attributed_without_network(self):
        from unittest.mock import patch
        with patch('urllib.request.urlopen',side_effect=AssertionError('unexpected network')):
            rows=findings()
        totals=summarize(rows)
        self.assertEqual(totals['wrong_publications'],12)
        self.assertEqual(totals['bad_neither'],0)
        self.assertEqual(totals['bad_parameter_only']+totals['bad_compute_only']+totals['bad_both'],12)
        self.assertEqual(totals['api_requests'],0)
