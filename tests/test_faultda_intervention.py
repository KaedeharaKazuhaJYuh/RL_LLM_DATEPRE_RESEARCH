import copy
import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.intervention.suite import body, Client, execute, replay, protocol, intervention


class InterventionTests(unittest.TestCase):
    def test_verified_candidate_allowed_and_stop_not_guarded(self):
        from faultda_bench.evidence.core import tasks
        from faultda_bench.trust.environment import ComputeFaultEnv
        from faultda_bench.semantic.compute import parameters
        from faultda_bench.pilot.contract import public_observation
        task=tasks()[0]
        with tempfile.TemporaryDirectory() as folder:
            env=ComputeFaultEnv(task,Path(folder)/'env',mode='healthy',evidence='E1',budget=3)
            for action in ('inspect','inputs','catalog'): env.step(action)
            env.step('stage',parameters(task['contract'],task['catalog']))
            choice={'action':'publish','params':{'stage_id':'1','request_id':'r','expected_revision':1,'mode':'replace'}}
            actual,verdict=intervention(public_observation(env),choice,'checklist_guard')
            self.assertEqual(actual,choice); self.assertTrue(verdict['allow'])
            stop={'action':'stop','params':{}}
            self.assertEqual(intervention(public_observation(env),stop,'checklist_guard'),(stop,None))

    def test_prompt_is_identical_between_checklist_arms(self):
        self.assertEqual(body({},'checklist'),body({},'checklist_guard'))
        a=body({},'raw'); b=body({},'checklist'); self.assertNotEqual(a,b)
        a['messages'][0]=b['messages'][0]; self.assertEqual(a,b)

    def test_blocked_publish_records_proposed_and_executed_actions(self):
        plan=protocol(); cell=next(c for c in plan['design']['order'] if c['arm']=='checklist_guard')
        task=next(t for t in plan['design']['tasks'] if t['id']==cell['task_id'])
        choice={'action':'publish','params':{'stage_id':'missing','request_id':'r','expected_revision':1,'mode':'replace'}}
        captured=[]
        def transport(request):
            captured.append(json.loads(request.data))
            return {'choices':[{'finish_reason':'stop','message':{'content':json.dumps(choice)}}]}
        client=Client('deepseek-flash',17,config={'DEEPSEEK_API_KEY':'fake'},transport=transport)
        with tempfile.TemporaryDirectory() as folder:
            row=execute(task,Path(folder)/'run',cell,client)
            self.assertEqual(client.calls,1); self.assertEqual(row['terminal'],'escalate')
            self.assertEqual(row['actions'][0]['proposed'],choice)
            self.assertEqual(row['actions'][0]['executed']['action'],'escalate')
            self.assertEqual(row['cost']['mutations'],1)
            self.assertTrue(row['safe_escalation'])
            replay(task,Path(folder)/'replay',row,cell)
            forged=copy.deepcopy(row); forged['actions'][0]['guard']['allow']=True
            with self.assertRaisesRegex(ValueError,'intervention replay'): replay(task,Path(folder)/'forged',forged,cell)

    def test_raw_invalid_output_is_counted_not_intervened(self):
        plan=protocol(); cell=next(c for c in plan['design']['order'] if c['arm']=='raw')
        task=next(t for t in plan['design']['tasks'] if t['id']==cell['task_id'])
        client=Client('deepseek-flash',17,config={'DEEPSEEK_API_KEY':'fake'},transport=lambda r:
            {'choices':[{'finish_reason':'length','message':{'content':'{'}}]})
        with tempfile.TemporaryDirectory() as folder:
            row=execute(task,Path(folder)/'run',cell,client)
            self.assertEqual(client.calls,17); self.assertEqual(row['terminal'],'budget_exceeded')
            self.assertTrue(all(a['guard'] is None for a in row['actions']))
            replay(task,Path(folder)/'replay',row,cell)
