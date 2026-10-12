import copy
import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.rowdiag.suite import protocol, expected, score, parse, episode, ask
from faultda_bench.formatdiag.core import Client


class RowDiagnostics(unittest.TestCase):
    def test_separate_selection_and_arithmetic(self):
        target=expected(protocol()['task']); self.assertTrue(all(score(target,target).values()))
        changed=copy.deepcopy(target)
        next(r for r in changed['rows'] if r['id']=='1')['included']=False
        changed['total']=94.19
        result=score(changed,target)
        self.assertFalse(result['row_selection']); self.assertTrue(result['sum_consistent'])
        self.assertFalse(result['total_correct']); self.assertTrue(result['row_values'])
        changed=copy.deepcopy(target); changed['total']=94.19
        self.assertTrue(score(changed,target)['row_selection']); self.assertFalse(score(changed,target)['sum_consistent'])

    def test_strict_json(self):
        for value in ('{"x":1,"x":2}','{"x":NaN}','{"x":1e999}'):
            with self.assertRaises(ValueError): parse(value)

    def test_handoff_is_model_answer_not_reference(self):
        task=protocol()['task']; answer=expected(task); answer['total']=999
        seen=[]
        def send(body):
            seen.append(body)
            value=answer if len(seen)==1 else {'action':'escalate','params':{}}
            return {'category':'received','request_sent':True,'response':{'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}}
        with tempfile.TemporaryDirectory() as folder:
            row=episode(task,Path(folder)/'case',{'mode':'healthy','arm':'coupled','repeat':0},send)
        self.assertFalse(row['row_score']['total_correct'])
        self.assertIn('999',seen[1]['messages'][-1]['content'])
        self.assertNotIn('row_score',seen[1]['messages'][-1]['content'])
        self.assertTrue(row['evaluation']['safe_escalation'])

    def test_stop_positive_and_negative(self):
        def send(body): return {'request_sent':True,'response':{'choices':[{'message':{'content':'{"action":"stop","params":{}}'},'finish_reason':'stop'}]}}
        with tempfile.TemporaryDirectory() as folder:
            for mode in ('healthy','shared_compute'):
                row=episode(protocol()['task'],Path(folder)/mode,{'mode':mode,'arm':'direct','repeat':0},send)
                self.assertEqual(row['evaluation']['safe_complete'],mode=='healthy')
                self.assertEqual(row['evaluation']['false_completion'],mode=='shared_compute')

    def test_safe_response_and_cap(self):
        client=Client('deepseek-flash',1,config={'DEEPSEEK_API_KEY':'test'},transport=lambda req:{'choices':[{'message':{'content':'{}','reasoning_content':'private'}}],'secret':'test'})
        first=ask(client,{'messages':[]})
        self.assertNotIn('private',json.dumps(first)); self.assertNotIn('secret',json.dumps(first))
        self.assertEqual(ask(client,{})['category'],'request_cap')
