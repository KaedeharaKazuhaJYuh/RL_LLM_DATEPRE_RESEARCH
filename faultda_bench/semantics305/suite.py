"""Frozen 2x2x2 prompt contrasts, UTC diagnostics and public-only rule controls."""
import argparse
import json
import math
import random
import tempfile
from decimal import Decimal
from pathlib import Path

from . import VERSION
from .core import VIEWS, view_task, diagnostic_body, diagnostic_score, action_body, ANALYSIS, IDEMPOTENCY, CARRY, NORMALIZE
from ..rowdiag import boundary as prior
from ..rowdiag.suite import ask, decoded
from ..formatdiag.core import Client, classify
from ..pilot.contract import public_observation
from ..trust.policy import public_expected
from ..stopping.suite import prepare
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json
from ..multistep.suite import require, same


def close_output(output, expected):
    return (isinstance(output,dict) and set(output)==set(expected)
        and all(type(output[k]) in (int,float) and math.isfinite(output[k])
            and abs(Decimal(str(output[k]))-v)<=max(Decimal('1e-9'),abs(v)*Decimal('1e-9')) for k,v in expected.items()))


def public_rule(obs):
    params, expected=public_expected(obs)
    inspection=next(h['response'] for h in obs['history'] if h['action']=='inspect')
    records=inspection['records']
    if len(records)==1 and records[0]['version']==params['version'] and close_output(records[0]['output'],expected):
        return {'action':'stop','params':{}}
    staged=[h['response'] for h in obs['history'] if h['action']=='stage' and h['response'].get('ok')]
    if not staged: return {'action':'stage','params':params}
    candidate=staged[-1]
    if candidate['version']!=params['version'] or not close_output(candidate['output'],expected):
        return {'action':'escalate','params':{}}
    # Only called on these unchanged-source, no-concurrency fixed states.
    return {'action':'publish','params':{'stage_id':candidate['stage_id'],'request_id':'rule-correction',
        'expected_revision':inspection['revision'],'mode':'replace'}}


def baseline(task,folder,cell):
    env=prepare(task,folder,cell['mode']); decisions=[]
    for _ in range(6):
        if env.terminal is not None: break
        decision=public_rule(public_observation(env)); decisions.append(decision)
        env.step(decision['action'],decision['params'])
    return {**cell,'decisions':decisions,'evaluation':evaluate(env)}


def diagnostic(task,folder,cell,send):
    env=prepare(task,folder,'healthy'); body=diagnostic_body(public_observation(env),cell['form']); receipt=send(body)
    return {**cell,'request':{'body':body,'receipt':receipt},'score':diagnostic_score(decoded(receipt),task,cell['form'])}


def trajectory(task,folder,cell,send):
    env=prepare(task,folder,cell['mode']); result={**cell,'requests':[],'steps':[]}
    body=diagnostic_body(public_observation(env),'comparisons'); receipt=send(body); evidence=decoded(receipt)
    result['requests'].append({'probe':'verification','body':body,'receipt':receipt})
    result['verification_score']=diagnostic_score(evidence,task,'comparisons')
    if evidence is None: evidence={'model_computation_unavailable':True}
    for step in range(6):
        if env.terminal is not None: break
        obs=public_observation(env); obs['experiment_action_horizon_remaining']=6-step
        body=action_body(obs,evidence,cell); receipt=send(body); classification=classify(receipt.get('response'))
        result['requests'].append({'probe':'action','body':body,'receipt':receipt}); result['steps'].append(classification)
        if classification['category']!='valid_action': break
        decision=classification['decision']; env.step(decision['action'],decision['params'])
    result['evaluation']=evaluate(env)
    result['end_kind']='agent_terminal' if env.terminal is not None else ('response_failure' if result['steps'][-1]['category']!='valid_action' else 'experiment_horizon')
    return result


def protocol():
    base=prior.protocol()['base_task']; require(sha(REPO/base['source_path'])==base['source_sha256'],'source')
    controls=[{'kind':'baseline','view':v,'mode':m} for v in VIEWS for m in ('healthy','shared_compute')]
    probes=[{'kind':'diagnostic','view':v,'form':f,'repeat':r} for v in VIEWS for f in ('comparisons','normalized') for r in (0,1)]
    episodes=[{'kind':'trajectory','mode':m,'analysis':a,'idempotency':i,'carry':c,'repeat':r}
        for m in ('healthy','shared_compute') for a in (False,True) for i in (False,True) for c in (False,True) for r in (0,1)]
    rng=random.Random(2026101205); rng.shuffle(probes); rng.shuffle(episodes)
    names=set(prior.protocol()['code_sha256']) | {p.relative_to(REPO).as_posix() for p in Path(__file__).parent.glob('*.py') if p.name in ('__init__.py','core.py','suite.py')}
    return {'version':VERSION,'revision':'semantics_v22','base_task':base,'views':{v:view_task(base,v) for v in VIEWS},
        'order':controls+probes+episodes,'code_sha256':{n:sha(REPO/n) for n in sorted(names)},
        'factor_instructions':{'analysis':ANALYSIS,'idempotency':IDEMPOTENCY,'carry':CARRY,'normalize':NORMALIZE},
        'max_requests':240,'per_trajectory_requests':7,'diagnostic_requests':16,'action_horizon':6,
        'independent_task_clusters':1,'max_tokens':2048,'thinking':'disabled','scientific_gate':'HOLD',
        'scope':'Eight rule controls, sixteen timezone probes, thirty-two 2x2x2 prompt trajectories; unchanged tool semantics, public-only model handoff, unequal actual costs; no new human review or RL training'}


def summarize(rows):
    diagnostics=[r for r in rows if r['kind']=='diagnostic']; episodes=[r for r in rows if r['kind']=='trajectory']
    controls=[r for r in rows if r['kind']=='baseline']
    metrics=('safe_complete','safe_escalation','false_completion','agent_wrong_publications')
    def totals(rs):
        return {'episodes':len(rs),**{k:sum(int(r['evaluation'][k]) for r in rs) for k in metrics},
            'cost':{k:sum(r['evaluation']['cost'][k] for r in rs) for k in ('checks','mutations','decisions','response_bytes')}}
    by_factors={}
    for a in (False,True):
        for i in (False,True):
            for c in (False,True):
                rs=[r for r in episodes if (r['analysis'],r['idempotency'],r['carry'])==(a,i,c)]
                by_factors[f'A{int(a)}I{int(i)}C{int(c)}']={**totals(rs),
                    'by_mode':{m:totals([r for r in rs if r['mode']==m]) for m in ('healthy','shared_compute')},
                    'correct_front_verifications':sum(r['verification_score']['total_correct'] is True and r['verification_score']['row_selection'] is True for r in rs),
                    'end_kinds':{k:sum(r['end_kind']==k for r in rs) for k in ('agent_terminal','response_failure','experiment_horizon')},
                    'request_attempts':sum(q['receipt']['request_sent'] is True for r in rs for q in r['requests'])}
    timezone_results={f:{v:{'probes':len(rs),**{k:sum(r['score'][k] is True for r in rs) for k in ('schema','row_selection','row_values','sum_consistent','total_correct','comparison_facts','utc_facts')}}
        for v in VIEWS for rs in [[r for r in diagnostics if r['form']==f and r['view']==v]]} for f in ('comparisons','normalized')}
    queries=[r['request'] for r in diagnostics]+[q for r in episodes for q in r['requests']]
    sent=[q['receipt'] for q in queries if q['receipt']['request_sent'] is True]
    usages=[r['response']['usage'] for r in sent if isinstance(r.get('response',{}).get('usage'),dict)
        and all(type(r['response']['usage'].get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
    return {'version':VERSION,'independent_task_clusters':1,'rule_controls':totals(controls),'timezone_results':timezone_results,
        'by_factors':by_factors,'trajectories':totals(episodes),'request_attempts':len(sent),
        'usage_available_calls':len(usages),'prompt_tokens':sum(u['prompt_tokens'] for u in usages),'completion_tokens':sum(u['completion_tokens'] for u in usages),
        'provider_errors':sum(r['category']=='provider_error' for r in sent),
        'length_finishes':sum((q['receipt'].get('response',{}).get('choices') or [{}])[0].get('finish_reason')=='length' for q in queries),
        'scientific_gate':'HOLD','rl_improvement_claim':False}


def verify(output):
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    result=json.loads(output.read_text()); frozen=json.loads(pp.read_text()); require(same(frozen,protocol()),'protocol')
    require(result['protocol_sha256']==sha(pp) and result['trace_sha256']==sha(tp),'artifact hashes')
    rows=[json.loads(x) for x in tp.read_text().splitlines()]; require(len(rows)==len(frozen['order'])==56,'coverage')
    with tempfile.TemporaryDirectory() as folder:
        for index,(cell,row) in enumerate(zip(frozen['order'],rows)):
            task=frozen['base_task'] if cell['kind']=='trajectory' else frozen['views'][cell['view']]
            if cell['kind']=='baseline': rebuilt=baseline(task,Path(folder)/str(index),cell)
            else:
                records=[row['request']] if cell['kind']=='diagnostic' else row['requests']; saved=iter(records)
                def send(body):
                    q=next(saved); require(same(q['body'],body),'public request and model-only evidence')
                    receipt=q['receipt']; require(type(receipt['request_sent']) is bool,'sent type')
                    require(receipt['category'] in ('received','provider_error','input_limit','request_cap'),'category')
                    if receipt['category']=='received': require(receipt['request_sent'] is True and isinstance(receipt['response'],dict),'response consistency')
                    return receipt
                rebuilt=(diagnostic if cell['kind']=='diagnostic' else trajectory)(task,Path(folder)/str(index),cell,send)
                require(next(saved,None) is None,'extra requests')
                require(len(records)<=(1 if cell['kind']=='diagnostic' else 7),'episode request cap')
            require(same(row,rebuilt),'classification, scores and effects')
    require(same(result['summary'],summarize(rows)) and result['summary']['request_attempts']<=240,'summary/cap')
    return {'status':'verified','rule_controls':8,'timezone_probes':16,'trajectories':32,
        'response_classification_replayed':True,'provider_authenticity_verified':False,'scientific_gate':'HOLD'}


def live(plan,output):
    frozen=json.loads(Path(plan).read_text()); require(same(frozen,protocol()),'frozen plan')
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    require(not any(p.exists() for p in (output,pp,tp)),'exclusive paths'); write_json(pp,frozen)
    rows=[]; requests=0
    with tempfile.TemporaryDirectory() as folder,tp.open('xb') as stream:
        for index,cell in enumerate(frozen['order']):
            task=frozen['base_task'] if cell['kind']=='trajectory' else frozen['views'][cell['view']]
            if cell['kind']=='baseline': row=baseline(task,Path(folder)/str(index),cell)
            else:
                client=Client('deepseek-flash',1 if cell['kind']=='diagnostic' else 7)
                row=(diagnostic if cell['kind']=='diagnostic' else trajectory)(task,Path(folder)/str(index),cell,lambda body:ask(client,body))
                requests+=client.calls
            rows.append(row); stream.write((json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n').encode()); stream.flush()
            print(json.dumps({'completed':len(rows),'planned':56,'requests':requests}),flush=True)
    write_json(output,{'version':VERSION,'protocol_sha256':sha(pp),'trace_sha256':sha(tp),'summary':summarize(rows)})
    return verify(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--freeze'); p.add_argument('--protocol'); p.add_argument('--output'); p.add_argument('--verify'); a=p.parse_args()
    if a.freeze and not any((a.protocol,a.output,a.verify)): write_json(Path(a.freeze),protocol())
    elif a.verify and not any((a.freeze,a.protocol,a.output)): print(json.dumps(verify(a.verify)))
    elif a.protocol and a.output and not any((a.freeze,a.verify)): print(json.dumps(live(a.protocol,a.output)))
    else: p.error('choose freeze, verify, or protocol/output')
