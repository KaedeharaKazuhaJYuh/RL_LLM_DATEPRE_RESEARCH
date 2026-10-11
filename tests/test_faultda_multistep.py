import tempfile
import json
import unittest
from pathlib import Path
from faultda_bench.multistep.suite import execute, replay, protocol
from faultda_bench.formatdiag.core import Client


class MultistepTests(unittest.TestCase):
    def test_successful_effect_replay_and_forged_completion_rejected(self):
        from faultda_bench.trust.policy import choose_guarded_read
        plan=protocol(); cell=next(c for c in plan['design']['order'] if c['mode']=='healthy')
        task=next(t for t in plan['design']['tasks'] if t['id']==cell['task_id'])
        def transport(request):
            observation=json.loads(json.loads(request.data)['messages'][1]['content'])
            choice=choose_guarded_read(observation)
            choice.setdefault('params',{})
            return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(choice)}}]}
        client=Client('deepseek-flash',17,config={'DEEPSEEK_API_KEY':'fake'},transport=transport)
        with tempfile.TemporaryDirectory() as folder:
            row=execute(task,Path(folder)/'run',cell,client)
            self.assertTrue(row['safe_complete'])
            replay(task,Path(folder)/'replay',row,cell)
            row['safe_complete']=False
            with self.assertRaisesRegex(ValueError,'effect replay'):
                replay(task,Path(folder)/'forged',row,cell)

    def test_independent_quotas_and_step17_rejection(self):
        plan=protocol(); cell=plan['design']['order'][0]; task=next(t for t in plan['design']['tasks'] if t['id']==cell['task_id'])
        def make_client():
            return Client('deepseek-flash',17,config={'DEEPSEEK_API_KEY':'fake'},transport=lambda r:
                {'choices':[{'finish_reason':'stop','message':{'content':'bad JSON'}}]})
        with tempfile.TemporaryDirectory() as folder:
            for i in (0,1):
                client=make_client(); row=execute(task,Path(folder)/str(i),cell,client)
                self.assertEqual(client.calls,17)
                self.assertEqual(row['terminal'],'budget_exceeded')
                self.assertEqual(row['cost']['decisions'],17)
                replay(task,Path(folder)/('replay'+str(i)),row,cell)
                row['receipts'][0]['decision']={'action':'stop','params':{}}
                with self.assertRaisesRegex(ValueError,'failed output repaired'):
                    replay(task,Path(folder)/('forged'+str(i)),row,cell)

    def test_provider_failure_is_not_a_tool_action(self):
        plan=protocol(); cell=plan['design']['order'][0]; task=next(t for t in plan['design']['tasks'] if t['id']==cell['task_id'])
        def fail(r): raise TimeoutError('private exception text')
        client=Client('deepseek-flash',17,config={'DEEPSEEK_API_KEY':'fake'},transport=fail)
        with tempfile.TemporaryDirectory() as folder:
            row=execute(task,Path(folder)/'run',cell,client)
            self.assertEqual(row['terminal'],'provider_error'); self.assertEqual(row['trace'],[])
            self.assertEqual(client.calls,1)
            replay(task,Path(folder)/'replay',row,cell)
