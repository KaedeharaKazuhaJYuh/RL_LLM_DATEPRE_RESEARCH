import copy,hashlib,tempfile,unittest
from pathlib import Path
import numpy as np
from agent.tools import execute_tool,ACTIONS
from research.io import ROOT,write_table,digest,read_table
from research.oracle import expected
from research.runtime import load_bundle,run_task
from research.policies import Policy
from research.features import profile,encode
from verifier.score import verify
class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.dir=Path(self.tmp.name);self.path=self.dir/'data.csv'
        write_table(self.path,['date','value','kind','other'],[{'date':'2026/01/01','value':'1','kind':' a ','other':'2'},{'date':'bad','value':'','kind':'A','other':'4'},{'date':'2026-02','value':'3','kind':'b','other':'6'},{'date':'2026-02','value':'3','kind':'b','other':'6'}])
        self.p={'column':'value','other_column':'other','group_by':'date','lower':0,'upper':2,'window':2}
    def tearDown(self):self.tmp.cleanup()
    def tool(self,a,p=None):return execute_tool(a,{'uri':str(self.path),'params':p or self.p,'artifact_dir':self.dir/'artifact'})
    def check(self,r,g,a='fill_missing',**extra):
        return verify(r,g,[{'tool':a,'ok':True}],{'input_sha256':digest(self.path),'allowed_tools':ACTIONS,'max_tool_calls':1,'max_steps':1,'max_seconds':10,**extra})
    def test_real_median_artifact(self):
        r=self.tool('fill_missing');self.assertEqual(r['answer']['filled_cells'],1);self.assertEqual(read_table(r['artifact']['path'])[1][1]['value'],'3.0');self.assertTrue(self.check(r,expected(self.path,'fill_missing',self.p))['passed'])
    def test_oracle_hand_calculated(self):
        self.assertAlmostEqual(expected(self.path,'describe_numeric',self.p)['expected']['mean'],7/3);self.assertEqual(expected(self.path,'aggregate',self.p)['expected'],{'2026/01/01':1.,'2026-02':6.})
    def test_dates_not_constant(self):
        p={**self.p,'column':'date'};r=self.tool('normalize_dates',p);self.assertEqual(r['answer']['invalid_dates'],1);self.assertEqual(r['artifact']['rows'][0]['date'],'2026-01-01');self.assertTrue(self.check(r,expected(self.path,'normalize_dates',p),'normalize_dates')['passed'])
    def test_clipping(self):self.assertEqual(self.tool('clip_outliers')['answer']['rows_changed'],2)
    def test_dedup(self):self.assertEqual(self.tool('deduplicate')['answer']['removed'],1)
    def test_missing_oracle(self):
        with self.assertRaises(ValueError):verify({'answer':'anything','evidence':[]},{},[],{})
    def test_illegal_zero_reward(self):
        v=self.check(self.tool('fill_missing'),expected(self.path,'fill_missing',self.p),'illegal');self.assertFalse(v['passed']);self.assertEqual(v['score'],0)
    def test_fake_evidence(self):
        r=self.tool('fill_missing');r['evidence']=['placeholder'];self.assertFalse(self.check(r,expected(self.path,'fill_missing',self.p))['passed'])
    def test_artifact_tampering(self):
        r=self.tool('fill_missing');Path(r['artifact']['path']).write_text('wrong',encoding='utf-8');self.assertFalse(self.check(r,expected(self.path,'fill_missing',self.p))['passed'])
    def test_deadline(self):self.assertEqual(self.check(self.tool('fill_missing'),expected(self.path,'fill_missing',self.p),elapsed_seconds=20)['score'],0)
    def test_extra_answer_keys(self):
        r=self.tool('fill_missing');r['answer']['unasked']='x';self.assertFalse(self.check(r,expected(self.path,'fill_missing',self.p))['passed'])
    def test_all_missing(self):
        write_table(self.path,['value'],[{'value':''}])
        with self.assertRaises(ValueError):self.tool('fill_missing')
    def test_no_task_id_shortcut(self):
        with self.assertRaises(ValueError):self.tool('task_analysis')
    def test_nonfinite(self):
        write_table(self.path,['value'],[{'value':'nan'}])
        with self.assertRaises(ValueError):self.tool('describe_numeric')
    def test_digest_streams_without_changing_sha256(self):
        payload=(b'large-model-shard' * 200000) + b'end'
        path=self.dir/'weights.safetensors';path.write_bytes(payload)
        self.assertEqual(hashlib.sha256(payload).hexdigest(),digest(path,chunk_size=65536))
class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tasks,cls.oracles=load_bundle()
    def test_disjoint_sources(self):
        s=[{t['source_id'] for t in self.tasks if t['split']==s} for s in ('train','validation','test')];self.assertFalse(s[0]&s[1] or s[0]&s[2] or s[1]&s[2])
    def test_hashes_schema(self):
        for t in self.tasks:self.assertEqual(digest(ROOT/t['dataset']['uri']),t['dataset']['sha256']);self.assertEqual(read_table(t['dataset']['uri'])[0],t['dataset']['columns'])
    def test_no_singletons(self):self.assertTrue(all(len(t['allowed_tools'])==12 for t in self.tasks))
    def test_distinct_task_features(self):
        ts=[t for t in self.tasks if t['source_id']=='source_00'];self.assertEqual(len({tuple(encode(t,profile(t['dataset']['uri']))) for t in ts}),12)
    def test_id_invariant(self):
        t=self.tasks[0];other={**t,'task_id':'opaque'};p=Policy();self.assertEqual(p.select(t,encode(t,profile(t['dataset']['uri'])))[0],p.select(other,encode(other,profile(other['dataset']['uri'])))[0])
    def test_frozen_evaluation(self):
        t=self.tasks[0];p=Policy('bandit');before=p.b.copy()
        with tempfile.TemporaryDirectory() as d:r=run_task(t,p,self.oracles[t['task_id']],d)
        self.assertTrue(np.array_equal(before,p.b));self.assertIn('next_state',r);self.assertIn('observation',r['trace'][0])
    def test_missing_file_record(self):
        t=copy.deepcopy(self.tasks[0]);t['dataset']['uri']='does-not-exist.csv'
        with tempfile.TemporaryDirectory() as d:r=run_task(t,Policy(),self.oracles[t['task_id']],d)
        self.assertFalse(r['passed']);self.assertIn('FileNotFoundError',r['termination_reason'])
    def test_legacy_data_restored(self):
        for f in ('sample.csv','churn.csv','students.csv'):self.assertGreater(len(read_table('tasks/variants/value_v1/data/'+f)[0]),1)
    def test_checkpoint_roundtrip(self):
        p=Policy('bandit');x=np.ones(106);p.update('aggregate',x,.95)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'model.npz';p.save(path);other=Policy('bandit');other.load(path)
        self.assertTrue(np.array_equal(p.b,other.b));self.assertTrue(np.array_equal(p.inv,other.inv))
    def test_llm_mock_public_inputs(self):
        task=next(t for t in self.tasks if self.oracles[t['task_id']]['training_action']=='profile_schema')
        class Mock:
            last_usage={'prompt_tokens':10,'completion_tokens':2}
            def choose(self,t,state,allowed):
                assert 'expected' not in t and 'gold' not in t
                assert state['data_profile']['columns']
                return {'action':'profile_schema','rationale':'schema requested'}
        p=Policy('rule');p.mode='llm';p.llm=Mock()
        with tempfile.TemporaryDirectory() as d:r=run_task(task,p,self.oracles[task['task_id']],d)
        self.assertTrue(r['passed']);self.assertEqual(r['cost']['input_tokens'],10);self.assertIsNone(r['action_probability'])
    def test_budget_prevents_execution(self):
        t=copy.deepcopy(self.tasks[0]);t['constraints']['max_tool_calls']=0
        with tempfile.TemporaryDirectory() as d:r=run_task(t,Policy(),self.oracles[t['task_id']],d)
        self.assertEqual(r['tool_calls'],0);self.assertEqual(r['score'],0)
if __name__=='__main__':unittest.main()
