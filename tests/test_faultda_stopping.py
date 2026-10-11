import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from faultda_bench.stopping.suite import body, parse, prepare, protocol, execute, CLARIFICATION
from faultda_bench.pilot.contract import public_observation


class StoppingTests(unittest.TestCase):
    def test_identical_public_states_and_only_clarification_changes(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('network')): plan=protocol()
        self.assertEqual(len(plan['order']),48); self.assertEqual(len(plan['snapshots']),6)
        for obs in plan['snapshots'].values():
            self.assertEqual(obs['remaining']['checks'],0)
            self.assertEqual([e['action'] for e in obs['history']],['inspect','inputs','catalog'])
            self.assertNotIn('reference',obs); self.assertNotIn('mode',obs)
            for probe in ('judgement','action'):
                before=body(obs,{'probe':probe,'arm':'checklist'}); after=body(obs,{'probe':probe,'arm':'clarified'})
                after['messages'][0]['content']=after['messages'][0]['content'].replace(' '+CLARIFICATION,'')
                self.assertEqual(before,after)

    def test_strict_judgement_parser(self):
        def response(text): return {'choices':[{'finish_reason':'stop','message':{'content':text}}]}
        good='{"expected_version":"v1","expected_output":{"total":1},"observed_report_correct":true}'
        self.assertEqual(parse(response(good),'judgement')['category'],'valid_judgement')
        for text in (good.replace(':1}',':NaN}'),good.replace(':1}',':1e999}'),good.replace(':true',':1'),
                     good.replace('"v1"','"v1","expected_version":"v2"')):
            self.assertNotEqual(parse(response(text),'judgement')['category'],'valid_judgement')
        self.assertEqual(parse(response(None),'judgement')['category'],'empty_content')

    def test_one_step_stop_correct_and_wrong_scored_separately(self):
        from faultda_bench.evidence.core import tasks
        class Fake:
            def request_once(self,obs,cell):
                self.assert_no_private= 'reference' not in obs
                return {'category':'valid_action','request_sent':True,'decision':{'action':'stop','params':{}}}
        task=tasks()[0]
        with tempfile.TemporaryDirectory() as folder:
            for mode in ('healthy','shared_compute'):
                cell={'task_id':task['id'],'mode':mode,'arm':'clarified','probe':'action','repeat':0}
                fake=Fake(); row=execute(task,Path(folder)/mode,cell,fake)
                self.assertTrue(fake.assert_no_private)
                self.assertEqual(row['evaluation']['safe_complete'],mode=='healthy')
                self.assertEqual(row['evaluation']['false_completion'],mode=='shared_compute')
                self.assertEqual(row['evaluation']['cost']['checks'],3)

    def test_judgement_does_not_execute_action_or_feed_answer_forward(self):
        from faultda_bench.evidence.core import tasks
        class Fake:
            def request_once(self,obs,cell):
                return {'category':'schema_error','request_sent':True,'decision':None}
        task=tasks()[0]; cell={'task_id':task['id'],'mode':'healthy','arm':'checklist','probe':'judgement','repeat':0}
        with tempfile.TemporaryDirectory() as folder:
            row=execute(task,Path(folder)/'run',cell,Fake())
            self.assertNotIn('evaluation',row)
            self.assertFalse(row['judgement_score']['exact'])
            obs=public_observation(prepare(task,Path(folder)/'other','healthy'))
            self.assertNotIn('expected_output',body(obs,{'probe':'action','arm':'checklist'})['messages'][1]['content'])
