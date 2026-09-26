import json
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from experiments.v4_pilot import run, state_hash
from research.features import DIM
from research.v4_hybrid import HybridPolicy
from agent.llm import LLMClient


class MockClient:
    model='mock-only'
    last_usage={}
    def choose(self, task, state, allowed):
        assert task['split'] in ('train','validation')
        assert not ({'gold','expected','training_action'} & set(state))
        return {'action':'profile_schema'}


class HybridTests(unittest.TestCase):
    def test_warm_prior_follows_hint_and_can_be_corrected(self):
        policy=HybridPolicy({'x':'fill_missing'},warm_start=True)
        task={'task_id':'x'};x=np.zeros(DIM)
        self.assertEqual('fill_missing',policy.select(task,x)[0])
        action,_=policy.select(task,x,training=True)
        policy.update(action,x,-1)
        self.assertNotEqual('fill_missing',policy.select(task,x)[0])

    def test_cache_reuse_and_budget_preflight(self):
        class NoCalls(MockClient):
            def choose(self,*args):raise AssertionError('cache should avoid network')
        with tempfile.TemporaryDirectory() as d:
            first=Path(d)/'first';second=Path(d)/'second'
            run(MockClient(),first,limit=1,epochs=1,seeds=(1,),live=False)
            result=run(NoCalls(),second,limit=1,epochs=1,seeds=(1,),live=False,
                       cache_dirs=(first,),warm_start=True,max_new_requests=0)
            self.assertEqual(2,result['cache_reused'])
            self.assertEqual(4,len(result['results']))
            with self.assertRaisesRegex(ValueError,'budget exceeded'):
                run(NoCalls(),Path(d)/'third',limit=2,cache_dirs=(first,),max_new_requests=0,live=False)

    def test_deepseek_request_uses_public_fields(self):
        config={'DEEPSEEK_API_KEY':'mock-secret','DEEPSEEK_MODEL':'deepseek-chat','LLM_TEMPERATURE':'0'}
        response=io.BytesIO(json.dumps({'id':'mock-response','usage':{'prompt_tokens':4},
                                     'choices':[{'message':{'content':'{"action":"profile_schema"}'}}]}).encode())
        with patch('agent.llm.settings',return_value=config), patch('agent.llm.credential_present',return_value=True):
            client=LLMClient()
        task={'prompt':'show schema','params':{},'constraints':{'max_seconds':10},'gold':'hidden'}
        with patch('agent.llm.urllib.request.urlopen',return_value=response) as call:
            result=client.choose(task,{'history':[]},['profile_schema'])
        request=call.call_args.args[0]
        body=json.loads(request.data)
        public=json.loads(body['messages'][1]['content'])
        self.assertNotIn('gold',public)
        self.assertEqual('https://api.deepseek.com/chat/completions',request.full_url)
        self.assertEqual('profile_schema',result['action'])
        self.assertEqual(4,client.last_usage['prompt_tokens'])

    def test_reward_updates_and_eval_freezes(self):
        p=HybridPolicy({'a':'profile_schema','b':'profile_schema'})
        x=np.ones(DIM)
        before=state_hash(p)
        action,_=p.select({'task_id':'a'},x,training=True)
        p.update(action,x,1.)
        self.assertNotEqual(before,state_hash(p))
        frozen=state_hash(p)
        self.assertEqual(p.select({'task_id':'a'},x),p.select({'task_id':'b'},x))
        self.assertEqual(frozen,state_hash(p))
        with self.assertRaises(RuntimeError):p.update(action,x,1.)

    def test_local_integration_is_not_live_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run'
            result=run(MockClient(),out,limit=2,epochs=2,seeds=(1,),live=False)
            self.assertFalse(result['live_api'])
            self.assertFalse(result['test_split_used'])
            self.assertFalse(result['llm_weights_updated'])
            self.assertEqual(0,result['api_requests'])
            self.assertEqual(3,len(result['results']))
            self.assertEqual(2,len(result['frozen_policies']))
            self.assertTrue((out/'deepseek_bandit_seed1.npz').is_file())
            with self.assertRaises(FileExistsError):run(MockClient(),out,live=False)

    def test_api_error_is_redacted(self):
        class Failure(MockClient):
            def choose(self,*args):raise ValueError('private-token-must-not-leak')
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'run'
            with self.assertRaisesRegex(RuntimeError,'collection stopped') as exc:
                run(Failure(),out,limit=1,live=False)
            self.assertNotIn('private-token',str(exc.exception))
            self.assertNotIn('private-token',(out/'failure.json').read_text())


if __name__=='__main__':unittest.main()
