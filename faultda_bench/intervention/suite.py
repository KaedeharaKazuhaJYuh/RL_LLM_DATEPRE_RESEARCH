"""Checklist and public publication gate with proposed/executed action receipts."""
import argparse
import json
import math
import tempfile
import time
import urllib.request
from pathlib import Path

from . import VERSION
from ..formatdiag.core import Client as BaseClient, body as base_body, classify, sha_bytes
from ..multistep.suite import ERRORS, FORMAT_CATEGORIES, require, same, summarize as base_summary
from ..publication.audit import CHECKLIST, gate, protocol as publication_protocol
from ..pilot.contract import public_observation, valid_decision
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, sha
from ..trust.environment import ComputeFaultEnv
from ..clarity.tasks import write_json

DESIGN=REPO/'faultda_bench/protocols/intervention_v17_design.json'
ARMS=('raw','checklist','checklist_guard')


def body(observation,arm):
    require(arm in ARMS,'arm')
    request=base_body(observation,{'thinking':'disabled','max_tokens':800})
    if arm!='raw': request['messages'][0]['content']+=' '+CHECKLIST
    return request


class Client(BaseClient):
    def request_once(self,observation,arm):
        payload=json.dumps(body(observation,arm),ensure_ascii=False,allow_nan=False).encode()
        base={'request_sha256':sha_bytes(payload),'request_bytes':len(payload)}
        if len(payload)>65536: return {**base,'category':'input_limit','request_sent':False}
        with self._lock:
            if self.calls>=self.max_calls: return {**base,'category':'request_cap','request_sent':False}
            self.calls+=1
        request=urllib.request.Request('https://api.deepseek.com/chat/completions',data=payload,
            headers={'Content-Type':'application/json','Authorization':'Bearer '+self.key})
        start=time.perf_counter()
        try: result=classify(self.transport(request))
        except Exception as error: result={'category':'provider_error','error_type':type(error).__name__,'http_status':getattr(error,'code',None)}
        return {**base,**result,'request_sent':True,'seconds':time.perf_counter()-start}


def protocol():
    design=json.loads(DESIGN.read_text(encoding='utf-8'))
    require(len(design['order'])==54 and design['global_request_cap']==918 and design['checklist_text']==CHECKLIST,'design')
    hashes=publication_protocol()['code_sha256'].copy()
    hashes.update({p.relative_to(REPO).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')})
    for name,checksum in design['source_sha256'].items(): require(sha(REPO/name)==checksum,'source hash')
    return {'version':VERSION,'design_sha256':sha(DESIGN),'design':design,'code_sha256':hashes,
            'body_policy':'raw original prompt; identical appended checklist in checklist and checklist_guard',
            'gate_feedback':'blocked publish executes escalate and ends; no follow-up model request or synthetic tool feedback',
            'scientific_gate':'HOLD'}


def intervention(observation,proposed,arm):
    if arm!='checklist_guard' or proposed['action']!='publish': return proposed,None
    verdict=gate(observation,proposed)
    return (proposed if verdict['allow'] else {'action':'escalate','params':{}}),verdict


def execute(task,folder,cell,client):
    env=ComputeFaultEnv(task,folder,**{k:cell[k] for k in ('mode','evidence','budget')}); receipts=[]; actions=[]
    while env.terminal is None:
        obs=public_observation(env); receipt=client.request_once(obs,cell['arm']); receipts.append(receipt)
        category=receipt['category']
        if category in ERRORS: env.terminal=ERRORS[category]; break
        require(category in FORMAT_CATEGORIES,'category')
        proposed=receipt['decision'] if category=='valid_action' else {'action':'invalid_model_output','params':{}}
        start=time.process_time(); actual,verdict=intervention(obs,proposed,cell['arm']); seconds=time.process_time()-start
        actions.append({'proposed':proposed,'executed':actual,'guard':verdict,'guard_cpu_seconds':seconds if verdict is not None else 0.0})
        env.step(actual['action'],actual['params'])
    return {**cell,**evaluate(env),'receipts':receipts,'actions':actions}


def summarize(rows):
    by_arm={}
    for arm in ARMS:
        selected=[r for r in rows if r['arm']==arm]; s=base_summary(selected)
        actions=[a for r in selected for a in r['actions']]
        s.update({k:sum(int(r[k]) for r in selected) for k in ('safe_complete','safe_escalation','false_completion','agent_wrong_publications','terminal_correct')})
        s['blocked_publication_proposals']=sum(a['guard'] is not None and not a['guard']['allow'] for a in actions)
        s['proposed_publications']=sum(a['proposed']['action']=='publish' for a in actions)
        s['guard_cpu_seconds']=sum(a['guard_cpu_seconds'] for a in actions)
        s['tool_cost_totals']={k:sum(r['cost'][k] for r in selected) for k in ('checks','mutations','decisions','response_bytes')}
        by_arm[arm]=s
    return {'executions':len(rows),'task_clusters':3,'by_arm':by_arm,
            'request_attempts':sum(s['request_attempts'] for s in by_arm.values()),'scientific_gate':'HOLD','rl_improvement_claim':False}


def live(plan,output):
    frozen=json.loads(Path(plan).read_text(encoding='utf-8')); require(same(frozen,protocol()),'frozen protocol')
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    require(not any(p.exists() for p in (output,pp,tp)),'new paths')
    mapping={t['id']:t for t in frozen['design']['tasks']}; rows=[]; write_json(pp,frozen)
    with tempfile.TemporaryDirectory(prefix='faultda_intervention_') as folder,tp.open('xb') as stream:
        for i,cell in enumerate(frozen['design']['order']):
            row=execute(mapping[cell['task_id']],Path(folder)/str(i),cell,Client('deepseek-flash',17)); rows.append(row)
            require(sum(sum(m['request_sent'] is True for m in r['receipts']) for r in rows)<=918,'global cap')
            stream.write((json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n').encode()); stream.flush()
            print(json.dumps({'completed':len(rows),'planned':54,'requests':sum(sum(m['request_sent'] is True for m in r['receipts']) for r in rows)}),flush=True)
    write_json(output,{'version':VERSION,'backend':'deepseek_live_intervention','protocol_sha256':sha(pp),'trace_sha256':sha(tp),'summary':summarize(rows)})
    return summarize(rows)


def replay(task,folder,row,cell):
    require(same({k:row[k] for k in cell},cell),'identity')
    env=ComputeFaultEnv(task,folder,**{k:cell[k] for k in ('mode','evidence','budget')}); n=0; sent=0
    for index,receipt in enumerate(row['receipts']):
        require(env.terminal is None,'receipt after terminal'); obs=public_observation(env)
        payload=json.dumps(body(obs,cell['arm']),ensure_ascii=False,allow_nan=False).encode()
        require(receipt['request_sha256']==sha_bytes(payload) and type(receipt['request_bytes']) is int and receipt['request_bytes']==len(payload),'request')
        require(type(receipt['request_sent']) is bool,'sent type'); sent+=int(receipt['request_sent']); require(sent<=17,'quota')
        category=receipt['category']
        if category in ERRORS:
            require(index==len(row['receipts'])-1 and (category=='provider_error')==receipt['request_sent'],'error accounting')
            if category=='request_cap': require(sent==17,'cap')
            if category=='input_limit': require(len(payload)>65536,'input limit')
            env.terminal=ERRORS[category]; continue
        require(receipt['request_sent'] and category in FORMAT_CATEGORIES,'format receipt')
        require(type(receipt['length_finish']) is bool and receipt['length_finish']==(receipt['finish_reason']=='length'),'finish')
        if category=='valid_action': require(valid_decision(receipt['decision']),'schema'); proposed=receipt['decision']
        else: require(receipt['decision'] is None,'healed output'); proposed={'action':'invalid_model_output','params':{}}
        actual,verdict=intervention(obs,proposed,cell['arm']); require(n<len(row['actions']),'action coverage'); saved=row['actions'][n]
        require(same(saved['proposed'],proposed) and same(saved['executed'],actual) and same(saved['guard'],verdict),'intervention replay')
        require(type(saved['guard_cpu_seconds']) in (int,float) and math.isfinite(saved['guard_cpu_seconds']) and saved['guard_cpu_seconds']>=0,'cpu time')
        if verdict is None: require(saved['guard_cpu_seconds']==0,'uninvoked guard time')
        env.step(actual['action'],actual['params']); require(n<len(row['trace']) and same(env.history[-1],row['trace'][n]),'feedback'); n+=1
    require(env.terminal is not None and n==len(row['trace'])==len(row['actions']),'coverage')
    for key,value in evaluate(env).items(): require(same(value,row[key]),'effect: '+key)


def verify(output):
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    result=json.loads(output.read_text(encoding='utf-8')); frozen=json.loads(pp.read_text(encoding='utf-8'))
    require(result['version']==VERSION and result['backend']=='deepseek_live_intervention','provenance')
    require(result['protocol_sha256']==sha(pp) and result['trace_sha256']==sha(tp) and same(frozen,protocol()),'protocol/hash')
    rows=[json.loads(x) for x in tp.read_text(encoding='utf-8').splitlines()]; require(len(rows)==54,'coverage')
    mapping={t['id']:t for t in frozen['design']['tasks']}
    with tempfile.TemporaryDirectory(prefix='faultda_intervention_replay_') as folder:
        for i,(row,cell) in enumerate(zip(rows,frozen['design']['order'])): replay(mapping[cell['task_id']],Path(folder)/str(i),row,cell)
    require(same(result['summary'],summarize(rows)) and result['summary']['request_attempts']<=918,'summary')
    return {'status':'verified','executions':54,'public_requests_tools_and_interventions_replayed':True,
            'response_classification_independently_replayed':False,'provider_authenticity_verified':False,'cpu_times_independently_replayed':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--freeze',type=Path); parser.add_argument('--protocol',type=Path)
    parser.add_argument('--output',type=Path); parser.add_argument('--verify',type=Path); args=parser.parse_args()
    if args.freeze and not any((args.protocol,args.output,args.verify)): write_json(args.freeze,protocol())
    elif args.verify and not any((args.protocol,args.output,args.freeze)): print(json.dumps(verify(args.verify)))
    elif args.protocol and args.output and not any((args.verify,args.freeze)): print(json.dumps(live(args.protocol,args.output)))
    else: parser.error('choose freeze, verify, or protocol with output')
