import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.rowdiag import isolated as s


class IsolatedDiagnostics(unittest.TestCase):
    def test_prompt_has_one_output_contract(self):
        request=s.request_body({'history':[]},'rows')
        self.assertNotIn('exactly action and params',request['messages'][0]['content'])
        self.assertIn('version (string), rows (array), total (number)',request['messages'][0]['content'])
        self.assertEqual(request['messages'][1]['content'],json.dumps({'history':[]},ensure_ascii=False,allow_nan=False))

    def test_dependency_set_does_not_grow_with_new_modules(self):
        names=s.protocol()['code_sha256']
        self.assertIn('faultda_bench/semantic/oracle.py',names)
        self.assertIn('faultda_bench/rowdiag/isolated.py',names)
        self.assertEqual(names,s.protocol()['code_sha256'])

    def test_valid_model_computation_stop_controls(self):
        task=s.protocol()['task']
        for mode in ('healthy','shared_compute'):
            calls=[]
            def send(body):
                calls.append(body)
                answer=s.expected(task) if len(calls)==1 else {'action':'stop','params':{}}
                return {'request_sent':True,'response':{'choices':[{'finish_reason':'stop','message':{'content':json.dumps(answer)}}]}}
            with tempfile.TemporaryDirectory() as folder:
                row=s.episode(task,Path(folder)/mode,{'mode':mode,'arm':'coupled','repeat':0},send)
            self.assertTrue(all(row['row_score'].values()))
            self.assertEqual(row['evaluation']['safe_complete'],mode=='healthy')
            self.assertEqual(row['evaluation']['false_completion'],mode=='shared_compute')
            self.assertNotIn('row_score',calls[1]['messages'][-1]['content'])
