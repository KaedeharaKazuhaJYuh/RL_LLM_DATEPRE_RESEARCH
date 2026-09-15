import json
import tempfile
import unittest
from pathlib import Path
from experiments.v4_multistep import episode
from research.io import ROOT,load_jsonl


class MultiStepTests(unittest.TestCase):
    def test_feedback_chaining_repair_and_reward(self):
        gold=json.loads((ROOT/'tasks/v3/oracle.json').read_text(encoding='utf-8'))
        task=next(t for t in load_jsonl('tasks/v3/tasks.jsonl') if t['split']=='train' and gold[t['task_id']]['plan']==['fill_missing','describe_numeric'])
        class Client:
            last_usage={}
            def choose_step(self,task,state,allowed):
                assert 'gold' not in state and 'reward' not in state
                done=sum(h['observation']['ok'] for h in state['history'])
                if done==2:return {'action':'stop'}
                return {'action':['fill_missing','describe_numeric'][done],'params':{'column':task['params']['column']}}
        with tempfile.TemporaryDirectory() as d:
            clean=episode(task,gold[task['task_id']],Client(),Path(d)/'clean')
            repaired=episode(task,gold[task['task_id']],Client(),Path(d)/'repair',True)
            self.assertTrue(clean['passed'] and repaired['passed'])
            self.assertEqual(3,repaired['tool_calls'])
            self.assertLess(repaired['reward'],clean['reward'])
            self.assertEqual(clean['trace'][0]['observation']['output_sha256'],clean['trace'][1]['observation']['input_sha256'])
            self.assertFalse(repaired['trace'][0]['observation']['ok'])

    def test_stop_without_work_is_not_success(self):
        gold=json.loads((ROOT/'tasks/v3/oracle.json').read_text(encoding='utf-8'))
        task=next(t for t in load_jsonl('tasks/v3/tasks.jsonl') if t['split']=='train' and t['track']=='composition')
        class Client:
            last_usage={}
            def choose_step(self,*args):return {'action':'stop'}
        with tempfile.TemporaryDirectory() as d:
            result=episode(task,gold[task['task_id']],Client(),d)
            self.assertFalse(result['passed'])
            self.assertLess(result['reward'],0)
