import copy
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from faultda_bench.rowdiag import boundary as s


def receipt(answer):
    return {'request_sent':True,'category':'received','response':{'choices':[{'finish_reason':'stop','message':{'content':json.dumps(answer)}}]}}


class BoundaryTests(unittest.TestCase):
    def test_reference_endpoint_and_timezone_controls(self):
        p=s.protocol(); totals={v:s.expected(t)['total'] for v,t in p['variants'].items()}
        self.assertEqual(totals['endpoint_equal'],117.89)
        self.assertEqual(totals['endpoint_outside'],117.89)
        self.assertEqual(totals['equivalent_offset'],117.89)
        self.assertAlmostEqual(totals['endpoint_inside'],141.1966666666667)
        for variant,task in p['variants'].items():
            row=next(r for r in s.expected(task)['rows'] if r['id']=='6')
            self.assertEqual(row['included'],variant=='endpoint_inside')
            self.assertEqual(task['versions'],p['base_task']['versions'])

    def comparison_answer(self,task):
        answer=s.expected(task)
        for r,original in zip(answer['rows'],task['versions'][answer['version']]):
            r['ge_start']=datetime.fromisoformat(original['time'])>=datetime.fromisoformat(task['contract']['start'])
            r['lt_end']=datetime.fromisoformat(original['time'])<datetime.fromisoformat(task['contract']['end'])
        return answer

    def test_comparison_facts_independent_of_correct_total(self):
        task=s.protocol()['base_task']; answer=self.comparison_answer(task)
        self.assertTrue(all(s.row_score(answer,task,'comparisons').values()))
        next(r for r in answer['rows'] if r['id']=='6')['lt_end']=True
        scores=s.row_score(answer,task,'comparisons')
        self.assertFalse(scores['comparison_facts']); self.assertTrue(scores['total_correct'])
        answer['rows'][0]['lt_end']=1
        self.assertFalse(s.row_score(answer,task,'comparisons')['schema'])

    def test_valid_handoff_does_not_force_stop_or_leak_score(self):
        task=s.protocol()['base_task']; seen=[]
        def send(body):
            seen.append(body)
            return receipt(self.comparison_answer(task) if len(seen)==1 else {'action':'escalate','params':{}})
        with tempfile.TemporaryDirectory() as folder:
            row=s.trajectory(task,Path(folder)/'case',{'mode':'healthy','arm':'comparisons','repeat':0},send)
        self.assertTrue(all(row['row_score'].values()))
        self.assertTrue(row['evaluation']['safe_escalation']); self.assertFalse(row['evaluation']['safe_complete'])
        self.assertNotIn('row_score',seen[1]['messages'][-1]['content'])
        self.assertIn('not independently verified',seen[1]['messages'][-1]['content'])

    def test_finite_multistep_repair_and_wrong_stop(self):
        task=s.protocol()['base_task']
        choices=[{'action':'stage','params':{'version':'v1','deduplicate_keys':True,'closed':'left'}},
            {'action':'publish','params':{'stage_id':'1','request_id':'test','expected_revision':1,'mode':'replace'}},
            {'action':'stop','params':{}}]
        for mode in ('healthy','shared_compute'):
            steps=iter(choices)
            with tempfile.TemporaryDirectory() as folder:
                row=s.trajectory(task,Path(folder)/mode,{'mode':mode,'arm':'direct','repeat':0},lambda body:receipt(next(steps)))
            self.assertEqual(len(row['requests']),3)
            self.assertEqual(row['evaluation']['safe_complete'],mode=='healthy')
            self.assertEqual(row['evaluation']['false_completion'],mode=='shared_compute')
            self.assertEqual(row['evaluation']['agent_wrong_publications'],int(mode=='shared_compute'))

    def test_horizon_does_not_become_failure_or_escalation(self):
        task=s.protocol()['base_task']
        with tempfile.TemporaryDirectory() as folder:
            row=s.trajectory(task,Path(folder)/'case',{'mode':'healthy','arm':'direct','repeat':0},
                lambda body:receipt({'action':'not_a_tool','params':{}}))
        self.assertEqual(row['end_kind'],'response_failure'); self.assertIsNone(row['evaluation']['terminal'])
        with tempfile.TemporaryDirectory() as folder:
            row=s.trajectory(task,Path(folder)/'case',{'mode':'healthy','arm':'direct','repeat':0},
                lambda body:receipt({'action':'stage','params':{'version':'missing'}}))
        self.assertEqual(row['end_kind'],'agent_terminal')
        self.assertEqual(row['evaluation']['terminal'],'budget_exceeded')
        self.assertFalse(row['evaluation']['safe_escalation'])

    def test_full_fake_live_replay_and_forged_classification(self):
        from unittest.mock import patch
        from faultda_bench.formatdiag.core import Client
        p=s.protocol(); responses=[]
        for cell in p['probe_order']:
            task=p['variants'][cell['variant']]
            responses.append(receipt(s.expected(task) if cell['form']=='rows' else self.comparison_answer(task))['response'])
        for cell in p['trajectory_order']:
            if cell['arm']!='direct':
                responses.append(receipt(s.expected(p['base_task']) if cell['arm']=='rows' else self.comparison_answer(p['base_task']))['response'])
            responses.append(receipt({'action':'stop','params':{}})['response'])
        replies=iter(responses)
        client=Client('deepseek-flash',96,config={'DEEPSEEK_API_KEY':'fake'},transport=lambda req:next(replies))
        with tempfile.TemporaryDirectory() as folder:
            plan=Path(folder)/'plan.json'; output=Path(folder)/'results.json'
            s.write_json(plan,p)
            with patch.object(s,'Client',return_value=client): result=s.live(plan,output)
            self.assertEqual(result['trajectories'],12)
            trace=output.with_suffix('.jsonl'); rows=[json.loads(x) for x in trace.read_text().splitlines()]
            rows[16]['steps'][0]['decision']['action']='escalate'
            trace.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
            summary=json.loads(output.read_text()); summary['trace_sha256']=s.sha(trace); output.write_text(json.dumps(summary))
            with self.assertRaisesRegex(ValueError,'classification'): s.verify(output)
