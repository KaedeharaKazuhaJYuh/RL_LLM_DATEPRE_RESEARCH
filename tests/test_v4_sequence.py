import tempfile
import unittest
from pathlib import Path
import numpy as np
from agent.llm import parse_step
from research.v4_sequence_env import build,SequenceEnv
from research.v4_sequence_policy import SequencePolicy,features,CHOICES
from experiments.v4_sequence_composition import build as build_composition


class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.tasks,self.gold=build(self.root/'protocol')

    def test_sources_and_explicit_metric(self):
        train={t['source_id'] for t in self.tasks if t['split']=='train'}
        val={t['source_id'] for t in self.tasks if t['split']=='validation'}
        self.assertFalse(train&val)
        for t in self.tasks:
            if self.gold[t['task_id']]['plan'][-1]=='rolling_mean':self.assertIn(t['params']['other_column'],t['prompt'])

    def test_equivalent_read_and_required_stop(self):
        t=self.tasks[0];g=self.gold[t['task_id']]
        e=SequenceEnv(t,g,self.root/'a')
        for a in ['deduplicate','profile_schema','profile_missingness','stop']:e.step(a)
        self.assertTrue(e.result()['passed'])
        e=SequenceEnv(t,g,self.root/'b')
        for a in ['deduplicate','profile_missingness','profile_missingness','profile_missingness']:e.step(a)
        self.assertFalse(e.result()['passed'])

    def test_failure_preserves_state_and_retry_costs(self):
        t=self.tasks[0];g=self.gold[t['task_id']];e=SequenceEnv(t,g,self.root/'a',True)
        e.step('deduplicate');self.assertFalse(e.history[0]['ok'])
        for a in ['deduplicate','profile_missingness','stop']:e.step(a)
        self.assertTrue(e.result()['passed']);self.assertEqual(3,e.result()['tool_calls'])

    def test_reinforce_changes_policy_without_gold(self):
        t=self.tasks[0];e=SequenceEnv(t,self.gold[t['task_id']],self.root/'a')
        p=SequencePolicy();obs=e.observation();a,cache=p.select(obs,True)
        initial=p.probs(features(obs))[CHOICES.index(a)]
        p.reinforce([cache],1.,0.)
        self.assertGreater(p.probs(features(obs))[CHOICES.index(a)],initial)
        before=p.fingerprint();p.select(obs);self.assertEqual(before,p.fingerprint())

    def test_json_fence_repair_is_local_and_strict(self):
        r,repaired=parse_step('```json\n{"action":"stop"}\n```',[])
        self.assertTrue(repaired);self.assertEqual('stop',r['action'])
        with self.assertRaises(ValueError):parse_step('{"action":"invented"}',[])
        with self.assertRaises(ValueError):parse_step('not JSON',[])

    def test_batch_update_bounds_kl_and_preserves_reference(self):
        t=self.tasks[0];e=SequenceEnv(t,self.gold[t['task_id']],self.root/'batch')
        obs=e.observation();p=SequencePolicy();reference=SequencePolicy()
        action,cache=p.select(obs,True);before=p.probs(cache[0]).copy()
        reference_hash=reference.fingerprint()
        diagnostic=p.batch_reinforce([([cache],1.)],[0.],
            [{'observation':obs,'action':action}],reference,lr=100.,
            bc_weight=0.,kl_weight=0.,max_kl=1e-5)
        after=p.probs(cache[0])
        self.assertTrue(diagnostic['accepted'])
        self.assertLess(diagnostic['step_scale'],1.)
        self.assertLessEqual(float(np.sum(before*np.log(before/after))),1e-5)
        self.assertGreater(after[cache[1]],before[cache[1]])
        self.assertEqual(reference_hash,reference.fingerprint())

    def test_anchor_only_reduces_reference_divergence(self):
        t=self.tasks[0];e=SequenceEnv(t,self.gold[t['task_id']],self.root/'anchor')
        obs=e.observation();p=SequencePolicy();reference=SequencePolicy()
        x=features(obs);p.weights[:,0]+=.3*x
        q=reference.probs(x);before=p.probs(x)
        p.batch_reinforce([],[],[{'observation':obs,'action':'stop'}],
                          reference,bc_weight=0.,kl_weight=1.)
        after=p.probs(x)
        self.assertLess(float(np.sum(q*np.log(q/after))),float(np.sum(q*np.log(q/before))))

    def test_unseen_composition_accepts_expert_and_rejects_seen_pair(self):
        tasks,gold=build_composition(self.root,self.root/'composition')
        train_pairs={tuple(self.gold[t['task_id']]['plan']) for t in self.tasks if t['split']=='train'}
        self.assertTrue(all(tuple(gold[t['task_id']]['plan']) not in train_pairs for t in tasks))
        t=tasks[0];g=gold[t['task_id']]
        expert=SequenceEnv(t,g,self.root/'expert')
        for action in [*g['plan'],'stop']:expert.step(action)
        self.assertTrue(expert.result()['passed'])
        wrong=SequenceEnv(t,g,self.root/'wrong')
        for action in ['fill_missing','describe_numeric','stop']:wrong.step(action)
        self.assertFalse(wrong.result()['passed'])
