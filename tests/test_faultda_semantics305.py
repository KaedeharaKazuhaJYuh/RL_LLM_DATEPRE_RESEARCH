import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
from faultda_bench.semantics305 import core as c, suite as s
from faultda_bench.formatdiag.core import Client


def reply(value):
    return {'category':'received','request_sent':True,'response':{'choices':[{'finish_reason':'stop','message':{'content':json.dumps(value)}}]}}


def answer(task,normalized=False):
    value=s.prior.expected(task)
    for row,source in zip(value['rows'],task['versions'][value['version']]):
        instant=datetime.fromisoformat(source['time'])
        row['ge_start']=instant>=datetime.fromisoformat(task['contract']['start'])
        row['lt_end']=instant<datetime.fromisoformat(task['contract']['end'])
        if normalized: row['time_utc']=instant.astimezone(timezone.utc).isoformat()
    if normalized:
        for key in ('start','end'): value[key+'_utc']=datetime.fromisoformat(task['contract'][key]).astimezone(timezone.utc).isoformat()
    return value


class Semantics305Tests(unittest.TestCase):
    def test_views_preserve_actual_instants_and_values(self):
        p=s.protocol(); original=p['base_task']
        for task in p['views'].values():
            self.assertEqual(s.prior.expected(task)['total'],117.89)
            for row,old in zip(task['versions']['v1'],original['versions']['v1']):
                self.assertEqual(datetime.fromisoformat(row['time']),datetime.fromisoformat(old['time']))
                self.assertEqual(row['value'],old['value'])
            scores=c.diagnostic_score(answer(task,True),task,'normalized')
            self.assertTrue(all(scores.values()))

    def test_bad_utc_fact_is_separate_from_selection_and_total(self):
        task=s.protocol()['views']['plus8_end']; value=answer(task,True)
        value['end_utc']=task['contract']['end']
        scores=c.diagnostic_score(value,task,'normalized')
        self.assertTrue(scores['total_correct']); self.assertTrue(scores['row_selection']); self.assertFalse(scores['utc_facts'])
        value['end_utc']='2015-02-02T15:24:59'
        self.assertFalse(c.diagnostic_score(value,task,'normalized')['utc_facts'])
        value['rows'][0]['lt_end']=1
        self.assertFalse(c.diagnostic_score(value,task,'normalized')['schema'])

    def test_prompt_factors_are_independent_and_do_not_change_evidence(self):
        obs={'history':[]}; evidence={'arbitrary_model_answer':999}
        off={'analysis':False,'idempotency':False,'carry':False}
        base=c.action_body(obs,evidence,off)
        for flag,text in (('analysis',c.ANALYSIS),('idempotency',c.IDEMPOTENCY),('carry',c.CARRY)):
            request=c.action_body(obs,evidence,{**off,flag:True})
            self.assertEqual(request['messages'][1:],base['messages'][1:])
            self.assertEqual(request['messages'][0]['content'],base['messages'][0]['content']+' '+text)
        self.assertEqual(obs,{'history':[]}); self.assertEqual(evidence,{'arbitrary_model_answer':999})

    def test_public_rule_positive_and_fault_negative(self):
        p=s.protocol()
        with tempfile.TemporaryDirectory() as folder:
            for view,task in p['views'].items():
                for mode in ('healthy','shared_compute'):
                    r=s.baseline(task,Path(folder)/(view+mode),{'kind':'baseline','view':view,'mode':mode})
                    self.assertEqual(r['evaluation']['safe_complete'],mode=='healthy')
                    self.assertEqual(r['evaluation']['safe_escalation'],mode=='shared_compute')
                    self.assertEqual(r['evaluation']['agent_wrong_publications'],0)
                    self.assertEqual(r['evaluation']['cost']['checks'],3)

    def test_correct_verification_does_not_force_completion(self):
        p=s.protocol(); task=p['base_task']; bodies=[]
        cell={'kind':'trajectory','mode':'healthy','analysis':True,'idempotency':True,'carry':True,'repeat':0}
        def send(body):
            bodies.append(body)
            return reply(answer(task) if len(bodies)==1 else {'action':'escalate','params':{}})
        with tempfile.TemporaryDirectory() as folder: r=s.trajectory(task,Path(folder)/'case',cell,send)
        self.assertTrue(r['verification_score']['total_correct']); self.assertFalse(r['evaluation']['safe_complete'])
        self.assertTrue(r['evaluation']['safe_escalation'])
        self.assertNotIn('verification_score',json.dumps(bodies[1])); self.assertIn('not independently verified',bodies[1]['messages'][-1]['content'])

    def test_receipt_empty_choices_summary_is_safe(self):
        p=s.protocol(); cell=next(x for x in p['order'] if x['kind']=='diagnostic')
        with tempfile.TemporaryDirectory() as folder:
            r=s.diagnostic(p['views'][cell['view']],Path(folder)/'case',cell,lambda b:{'category':'received','request_sent':True,'response':{'choices':[]}})
        self.assertFalse(r['score']['schema']); self.assertEqual(s.summarize([r])['length_finishes'],0)

    def test_full_fake_replay_rejects_rehashed_fake_decision(self):
        p=s.protocol(); responses=[]
        for cell in p['order']:
            if cell['kind']=='baseline': continue
            task=p['base_task'] if cell['kind']=='trajectory' else p['views'][cell['view']]
            responses.append(reply(answer(task,cell.get('form')=='normalized'))['response'])
            if cell['kind']=='trajectory': responses.append(reply({'action':'stop','params':{}})['response'])
        it=iter(responses)
        factory=lambda model,max_calls:Client(model,max_calls,config={'DEEPSEEK_API_KEY':'fake'},transport=lambda req:next(it))
        with tempfile.TemporaryDirectory() as folder:
            plan=Path(folder)/'plan.json'; output=Path(folder)/'result.json'; s.write_json(plan,p)
            with patch.object(s,'Client',side_effect=factory): result=s.live(plan,output)
            self.assertEqual(result['trajectories'],32)
            trace=output.with_suffix('.jsonl'); rows=[json.loads(x) for x in trace.read_text().splitlines()]
            rows[24]['steps'][0]['decision']['action']='escalate'
            trace.write_text(''.join(json.dumps(x)+'\n' for x in rows),encoding='utf-8')
            summary=json.loads(output.read_text()); summary['trace_sha256']=s.sha(trace); output.write_text(json.dumps(summary))
            with self.assertRaisesRegex(ValueError,'classification'): s.verify(output)
