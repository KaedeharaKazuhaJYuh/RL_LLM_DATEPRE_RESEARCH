"""Window membership diagnostics followed by model-generated-evidence decisions."""
import argparse
import json
import math
import random
import tempfile
import urllib.request
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from . import VERSION
from ..stopping.suite import prepare, CLARIFICATION
from ..formatdiag.core import Client, body as base_body, classify
from ..publication.audit import CHECKLIST
from ..pilot.contract import public_observation
from ..evidence.core import tasks
from ..semantic.oracle import reference, evaluate
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

INSTRUCTION = ('Return only JSON with exactly version (string), rows (array), total (number). '
    'List every raw row of the selected contract version once, in input order. Each row must contain '
    'exactly id (the original row id), included (boolean), value (original numerical value or null for missing). '
    'Determine inclusion from the time-window contract and sum only included nonmissing values. '
    'Do not execute a tool action. This is your independent computation, not evaluator feedback.')


def parse(content):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('duplicate key')
            result[key] = value
        return result
    def reject(value): raise ValueError('nonfinite')
    value = json.loads(content, object_pairs_hook=pairs, parse_constant=reject)
    json.dumps(value, allow_nan=False)
    return value


def valid(value):
    number = lambda x: type(x) in (int, float) and math.isfinite(x)
    return (isinstance(value, dict) and set(value) == {'version', 'rows', 'total'}
        and isinstance(value['version'], str) and number(value['total'])
        and isinstance(value['rows'], list) and all(isinstance(r, dict)
        and set(r) == {'id', 'included', 'value'} and type(r['included']) is bool
        and (r['value'] is None or number(r['value'])) for r in value['rows']))


def expected(task):
    version, totals = reference(task)
    c = task['contract']; rows = []
    for r in task['versions'][version]:
        included = datetime.fromisoformat(c['start']) <= datetime.fromisoformat(r['time']) < datetime.fromisoformat(c['end'])
        rows.append({'id': r['id'], 'included': included, 'value': None if r['value'] == '' else float(r['value'])})
    return {'version': version, 'rows': rows, 'total': float(totals['total'])}


def score(value, target):
    if not valid(value): return {'schema': False, 'row_selection': False, 'row_values': False, 'sum_consistent': False, 'total_correct': False}
    close = lambda a,b: abs(Decimal(str(a))-Decimal(str(b))) <= Decimal('1e-9') * max(Decimal(1),abs(Decimal(str(b))))
    actual = sum((Decimal(str(r['value'])) for r in value['rows'] if r['included'] and r['value'] is not None), Decimal(0))
    return {'schema': True,
        'row_selection': value['version'] == target['version'] and [(r['id'],r['included']) for r in value['rows']] == [(r['id'],r['included']) for r in target['rows']],
        'row_values': [(r['id'],r['value']) for r in value['rows']] == [(r['id'],r['value']) for r in target['rows']],
        'sum_consistent': close(value['total'],actual), 'total_correct': close(value['total'],target['total'])}


def request_body(obs, probe, evidence=None):
    if probe == 'rows':
        return {'model':'deepseek-flash','temperature':0,'max_tokens':2048,
            'thinking':{'type':'disabled'},'response_format':{'type':'json_object'},
            'messages':[{'role':'system','content':'You independently analyze the supplied public data. '+INSTRUCTION},
                        {'role':'user','content':json.dumps(obs,ensure_ascii=False,allow_nan=False)}]}
    b = base_body(obs, {'thinking':'disabled','max_tokens':2048})
    b['messages'][0]['content'] += ' ' + CHECKLIST + ' ' + CLARIFICATION
    if probe == 'rows': b['messages'][0]['content'] += ' ' + INSTRUCTION
    elif evidence is not None:
        b['messages'].append({'role':'user','content':'Your earlier computation (not independently verified): '+json.dumps(evidence,allow_nan=False)})
    return b


def ask(client, body):
    payload = json.dumps(body,ensure_ascii=False,allow_nan=False).encode()
    if len(payload)>65536: return {'category':'input_limit','request_sent':False}
    if client.calls >= client.max_calls: return {'category':'request_cap','request_sent':False}
    client.calls += 1
    req = urllib.request.Request('https://api.deepseek.com/chat/completions',data=payload,
        headers={'Content-Type':'application/json','Authorization':'Bearer '+client.key})
    try:
        response = client.transport(req)
        # Whitelist response data only; no headers, credentials, exceptions or hidden reasoning.
        ch = response.get('choices',[])
        safe = {'id':response.get('id'),'model':response.get('model'),'usage':response.get('usage',{}),
            'choices':[{'finish_reason':c.get('finish_reason'),'message':{'content':c.get('message',{}).get('content')}} for c in ch]}
        return {'request_sent':True,'response':safe,'category':'received'}
    except Exception as error:
        return {'request_sent':True,'category':'provider_error','error_type':type(error).__name__,'http_status':getattr(error,'code',None)}


def decoded(receipt):
    try: return parse(receipt['response']['choices'][0]['message']['content'])
    except (KeyError, IndexError, TypeError, ValueError): return None


def protocol():
    task = next(t for t in tasks() if t['contract']['family']=='window')
    cells = [{'mode':mode,'arm':arm,'repeat':r} for mode in ('healthy','shared_compute') for arm in ('direct','coupled') for r in range(3)]
    random.Random(2026101201).shuffle(cells)
    # Pin all benchmark Python dependencies, including private scorers, not just the immediate imports.
    original=json.loads((REPO/'faultda_bench/reports/rowdiag_v19_plan.json').read_text())
    names=set(original['code_sha256']) | {'faultda_bench/rowdiag/isolated.py'}
    files=[REPO/name for name in sorted(names)]
    return {'version':VERSION,'revision':'isolated_v20','task':task,'order':cells,'code_sha256':{p.relative_to(REPO).as_posix():sha(p) for p in files},
        'max_requests':18,'max_tokens':2048,'scientific_gate':'HOLD','scope':'one window task cluster; 12 one-step decisions and 6 preceding row probes; unequal API cost; no full recovery claim',
        'response_policy':'whitelisted content, id, model, finish reason, usage; no reasoning or credentials; local consistency is not provider authentication'}


def episode(task,folder,cell,send):
    env = prepare(task,folder,cell['mode']); obs = public_observation(env)
    result = {**cell,'requests':[]}; evidence = None
    if cell['arm']=='coupled':
        b = request_body(obs,'rows'); rec = send(b); evidence = decoded(rec)
        result['requests'].append({'body':b,'receipt':rec})
        result['row_score'] = score(evidence,expected(task))
        # Never hand private scores or a corrected answer back to the model.
        if evidence is None: evidence = {'model_computation_unavailable':True}
    b = request_body(obs,'action',evidence); rec = send(b)
    result['requests'].append({'body':b,'receipt':rec})
    classification = classify(rec.get('response')); result['action_classification'] = classification
    if classification['category']=='valid_action':
        d = classification['decision']; env.step(d['action'],d['params'])
    else: env.terminal='probe_output_failure'
    result['evaluation'] = evaluate(env)
    return result


def verify(output):
    output = Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    summary=json.loads(output.read_text()); frozen=json.loads(pp.read_text()); require(same(frozen,protocol()),'protocol')
    require(summary['protocol_sha256']==sha(pp) and summary['trace_sha256']==sha(tp),'hashes')
    rows=[json.loads(x) for x in tp.read_text().splitlines()]; require(len(rows)==12,'coverage')
    with tempfile.TemporaryDirectory() as folder:
        for i,(cell,row) in enumerate(zip(frozen['order'],rows)):
            requests=iter(row['requests'])
            def send(body):
                saved=next(requests); require(same(saved['body'],body),'public request and model-only handoff')
                return saved['receipt']
            require(same(row,episode(frozen['task'],Path(folder)/str(i),cell,send)),'response parsing and effects')
            require(next(requests,None) is None,'extra request')
    return {'status':'verified','episodes':12,'response_classification_replayed':True,'provider_authenticity_verified':False}


def live(plan,output):
    frozen=json.loads(Path(plan).read_text()); require(same(frozen,protocol()),'freeze before live')
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    require(not any(p.exists() for p in (output,pp,tp)),'exclusive new output'); write_json(pp,frozen)
    client=Client('deepseek-flash',18)
    with tempfile.TemporaryDirectory() as folder,tp.open('xb') as stream:
        for i,cell in enumerate(frozen['order']):
            row=episode(frozen['task'],Path(folder)/str(i),cell,lambda b:ask(client,b))
            stream.write((json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n').encode()); stream.flush()
            print(json.dumps({'completed':i+1,'planned':12,'requests':client.calls}),flush=True)
    write_json(output,{'version':VERSION,'protocol_sha256':sha(pp),'trace_sha256':sha(tp),'requests':client.calls,'scientific_gate':'HOLD'})
    return verify(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--freeze'); p.add_argument('--protocol'); p.add_argument('--output'); p.add_argument('--verify'); a=p.parse_args()
    if a.freeze and not any((a.protocol,a.output,a.verify)): write_json(Path(a.freeze),protocol())
    elif a.verify and not any((a.freeze,a.protocol,a.output)): print(json.dumps(verify(a.verify)))
    elif a.protocol and a.output and not any((a.freeze,a.verify)): print(json.dumps(live(a.protocol,a.output)))
    else: p.error('choose freeze, verify, or protocol/output')
