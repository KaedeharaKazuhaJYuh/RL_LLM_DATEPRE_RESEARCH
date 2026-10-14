"""Bounded live engineering pilot after explicit internal technical review."""
import argparse
import copy
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import VERSION
from .index import revision_index
from ..qualify330.suite import protocol as prior_protocol, prepare
from ..qualify330.environment import observation
from ..qualify330.policy import choose
from ..semantics305.core import diagnostic_body, diagnostic_score, action_body
from ..feedback315.core import public_input
from ..rowdiag.suite import decoded
from ..formatdiag.core import classify
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

DESIGN = REPO/'faultda_bench/protocols/qualify_v28_design.json'
REVIEW = REPO/'faultda_bench/reports/STATE_0355_INTERNAL_REVIEW.md'


def protocol():
    old = prior_protocol(); design = json.loads(DESIGN.read_text(encoding='utf-8'))
    states = [{'view': v, 'profile': p, 'checks': design['checks']} for v in design['views'] for p in design['profiles']]
    names = set(old['code_sha256']) | {'faultda_bench/runtime335/__init__.py','faultda_bench/runtime335/suite.py','faultda_bench/live350/__init__.py','faultda_bench/live350/suite.py','faultda_bench/state355/__init__.py','faultda_bench/state355/suite.py','faultda_bench/state355/index.py'}
    return {'version': VERSION, 'revision': 'state_v30', 'design_sha256': sha(DESIGN), 'internal_review_sha256': sha(REVIEW), 'states': states,
            'views': old['views'], 'arms': ['history', 'revision_index'], 'action_horizon': 8,
            'max_record_requests': 8, 'max_action_requests': 128, 'max_transport_requests': 136,
            'code_sha256': {n: sha(REPO/n) for n in sorted(names)}, 'scientific_gate': 'HOLD',
            'transport': 'deepseek_live_engineering', 'model': 'deepseek-flash', 'temperature': 0, 'thinking': 'disabled', 'max_tokens': 2048, 'arm_orders': [(['history','revision_index'] if (i//4+i%4)%2==0 else ['revision_index','history']) for i in range(8)],
            'scope': 'Both arms receive identical newly generated model record and full history. Treatment adds a program-derived revision index, with no numeric checker, reconstructed report, or action recommendation. Eight shared record generations, sixteen paired unguarded trajectories; balanced arm order. Internal technical review and user-directed engineering run do not constitute independent human/scientific acceptance. All states legally recoverable; no broad efficacy or RL claim.'}


def action_request(obs, record=None, arm='history'):
    obs = copy.deepcopy(obs)
    if arm == 'revision_index': obs['public_revision_index'] = revision_index(obs)
    body = action_body(obs, record, {'analysis': True, 'idempotency': True, 'carry': True})
    body['messages'][0]['content'] = body['messages'][0]['content'].replace(
        'at most six further tool actions', 'at most eight further tool actions')
    body['messages'][0]['content'] += (
        ' The reliability_contract in the supplied observation includes repeated precommit failures '
        'and commit acknowledgement loss. No numerical executor guard or private oracle is provided. '
        'An optional model-family working record can be wrong; use the latest public state.')
    return body


def checked_send(send, body, probe, requests):
    require(len(requests) < 136, 'global transport request cap')
    receipt = send(body, probe)
    require(type(receipt.get('request_sent')) is bool and receipt.get('category') in ('received','provider_error','input_limit','request_cap'), 'live receipt category')
    if receipt['category']=='received': require(receipt['request_sent'] and isinstance(receipt.get('response'),dict), 'received consistency')
    requests.append({'probe': probe, 'body': body, 'receipt': receipt})
    return receipt


def execute(plan, send):
    require(same(plan, protocol()), 'frozen executable plan'); rows = []; generated = []; requests = []
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for index, cell in enumerate(plan['states']):
            task = plan['views'][cell['view']]
            env = prepare(task, root/('record-'+str(index)), cell['profile'], cell['checks'])
            initial = observation(env); body = diagnostic_body(initial, 'normalized')
            receipt = checked_send(send, body, 'record', requests); record = decoded(receipt)
            generated.append({'state': index, 'request_index': len(requests)-1, 'record': record,
                              'score': diagnostic_score(record, task, 'normalized')})
            for arm in plan['arm_orders'][index]:
                env = prepare(task, root/(str(index)+'-'+arm), cell['profile'], cell['checks'])
                require(same(observation(env), initial), 'matched public initial state')
                evidence = record if record is not None else {'model_record_unavailable': True}
                result = {**cell, 'state': index, 'arm': arm, 'record_source': index,
                          'action_record': copy.deepcopy(evidence), 'request_indices': [], 'classifications': []}
                for step in range(8):
                    if env.terminal is not None: break
                    obs = observation(env); obs['experiment_action_horizon_remaining'] = 8-step
                    body = action_request(obs, evidence, arm); receipt = checked_send(send, body, 'action', requests)
                    result['request_indices'].append(len(requests)-1)
                    classification = classify(receipt.get('response')); result['classifications'].append(classification)
                    if classification['category'] != 'valid_action': break
                    decision = classification['decision']; env.step(decision['action'], decision['params'])
                result['evaluation'] = evaluate(env)
                result['end_kind'] = 'terminal' if env.terminal is not None else ('response_failure' if result['classifications'][-1]['category']!='valid_action' else 'experiment_horizon')
                rows.append(result)
    return {'version':VERSION,'protocol':plan,'record_generations':generated,'requests':requests,'rows':rows,'summary':summarize(generated,requests,rows)}


def summarize(generated, requests, rows):
    def totals(rs):
        return {'episodes':len(rs),**{k:sum(int(r['evaluation'][k]) for r in rs) for k in ('safe_complete','safe_escalation','false_completion','agent_wrong_publications','duplicate_events')},
                'unsafe_episodes':sum(bool(r['evaluation']['agent_wrong_publications']) for r in rs),
                'end_kinds':{k:sum(r['end_kind']==k for r in rs) for k in ('terminal','response_failure','experiment_horizon')},
                'cost':{k:sum(r['evaluation']['cost'][k] for r in rs) for k in ('checks','mutations','decisions','response_bytes')}}
    sent=[q for q in requests if q['receipt']['request_sent']]
    usages=[q['receipt'].get('response',{}).get('usage',{}) for q in sent]
    usages=[u for u in usages if all(type(u.get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
    return {'version':VERSION,'shared_record_generations':len(generated),'records_fully_correct':sum(all(v is True for v in r['score'].values()) for r in generated),
            'by_arm':{a:totals([r for r in rows if r['arm']==a]) for a in ('history','revision_index')},
            'by_state_arm':{str(i)+'|'+a:totals([r for r in rows if r['state']==i and r['arm']==a]) for i in range(8) for a in ('history','revision_index')},
            'actual_provider_requests':len(sent),'usage_available_calls':len(usages),'prompt_tokens':sum(u['prompt_tokens'] for u in usages),'completion_tokens':sum(u['completion_tokens'] for u in usages),
            'provider_errors':sum(q['receipt']['category']=='provider_error' for q in requests),'length_finishes':sum((q['receipt'].get('response',{}).get('choices') or [{}])[0].get('finish_reason')=='length' for q in requests),
            'independent_task_clusters':1,'independent_review':'pending','scientific_gate':'HOLD','rl_improvement_claim':False}


def verify(output):
    saved = json.loads(Path(output).read_text(encoding='utf-8')); iterator = iter(saved['requests'])
    def replay(body, probe):
        request = next(iterator); require(request['probe'] == probe and same(request['body'], body), 'exact prompt/record replay')
        return request['receipt']
    rebuilt = execute(saved['protocol'], replay)
    require(next(iterator, None) is None and same(rebuilt, {k:v for k,v in saved.items() if k!='request_trace_sha256'}), 'classifications/records/actions/state/accounting')
    if 'request_trace_sha256' in saved:
        trace = Path(output).with_suffix('.requests.jsonl')
        require(saved['request_trace_sha256'] == sha(trace), 'append-only live response trace')
        require(same([json.loads(x) for x in trace.read_text(encoding='utf-8').splitlines()], saved['requests']), 'trace request order')
    return {'status':'verified','model_trajectories':16,'actual_provider_requests':saved['summary']['actual_provider_requests'],'provider_authenticity_verified':False,'scientific_gate':'HOLD'}


def live(plan_path, output):
    from ..formatdiag.core import Client
    from ..rowdiag.suite import ask
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'));require(same(plan,protocol()),'frozen plan')
    output=Path(output);trace=output.with_suffix('.requests.jsonl')
    require(not output.exists() and not trace.exists(),'exclusive output paths')
    client=None
    def send(body,probe):
        nonlocal client
        if probe=='record': client=Client('deepseek-flash',17)
        receipt=ask(client,body)
        stream.write((json.dumps({'probe':probe,'body':body,'receipt':receipt},ensure_ascii=False,allow_nan=False)+'\n').encode());stream.flush()
        print(json.dumps({'probe':probe,'sent':receipt['request_sent'],'category':receipt['category']}),flush=True)
        return receipt
    with trace.open('xb') as stream:
        result=execute(plan,send)
    result['request_trace_sha256']=sha(trace);write_json(output,result)
    return verify(output)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze');p.add_argument('--protocol');p.add_argument('--output');p.add_argument('--verify');a=p.parse_args()
    if a.freeze and not any((a.protocol,a.output,a.verify)):write_json(Path(a.freeze),protocol())
    elif a.verify and not any((a.freeze,a.protocol,a.output)):print(json.dumps(verify(a.verify)))
    elif a.protocol and a.output and not any((a.freeze,a.verify)):print(json.dumps(live(a.protocol,a.output)))
    else:p.error('choose freeze, verify or protocol/output')
