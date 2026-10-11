"""Independent episode request quotas and replayable public tool effects."""
import argparse
import json
import tempfile
from pathlib import Path

from . import VERSION
from ..formatdiag.core import Client, body, sha_bytes
from ..formatdiag.suite import protocol as diagnostic_protocol
from ..pilot.contract import public_observation, valid_decision
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, sha
from ..trust.environment import ComputeFaultEnv
from ..clarity.tasks import write_json

DESIGN = REPO / 'faultda_bench/protocols/multistep_v15_design.json'
CONFIG = {'thinking': 'disabled', 'max_tokens': 800}
ERRORS = {'provider_error': 'provider_error', 'input_limit': 'input_limit', 'request_cap': 'api_budget_exceeded'}
FORMAT_CATEGORIES = {'valid_action','empty_content','json_error','schema_error','response_shape'}


def require(value, message):
    if not value: raise ValueError(message)


def same(a,b):
    return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)


def protocol():
    design=json.loads(DESIGN.read_text(encoding='utf-8'))
    require(design['thinking']=={'type':'disabled'} and design['per_episode_request_cap']==17
            and design['global_request_cap']==306 and len(design['order'])==18,'design limits')
    hashes=diagnostic_protocol()['code_sha256'].copy()
    hashes.update({p.relative_to(REPO).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')})
    return {'version':VERSION,'design_sha256':sha(DESIGN),'design':design,'code_sha256':hashes,
            'receipt_policy':'invalid output becomes an invalid action; no schema repair; original step-17 rejection retained',
            'scientific_gate':'HOLD'}


def execute(task, folder, cell, client):
    env=ComputeFaultEnv(task,folder,**{k:cell[k] for k in ('mode','evidence','budget')})
    receipts=[]
    while env.terminal is None:
        receipt=client.request_once(public_observation(env),CONFIG)
        receipts.append(receipt)
        category=receipt['category']
        if category in ERRORS:
            env.terminal=ERRORS[category]
            break
        require(category in FORMAT_CATEGORIES,'unknown receipt category')
        decision=receipt['decision'] if category=='valid_action' else {'action':'invalid_model_output','params':{}}
        # Original environment applies and counts rejected attempts, including step 17.
        env.step(decision['action'],decision['params'])
    return {**cell,**evaluate(env),'receipts':receipts}


def summarize(rows):
    sent=[m for r in rows for m in r['receipts'] if m['request_sent'] is True]
    usages=[m['usage'] for m in sent if isinstance(m.get('usage'),dict)
            and all(type(m['usage'].get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
    fields=('safe_complete','false_completion','safe_escalation','agent_wrong_publications')
    return {'executions':len(rows),'task_clusters':3,
            'by_mode':{mode:{k:sum(int(r[k]) for r in rows if r['mode']==mode) for k in fields}
                       for mode in ('healthy','stage_only','shared_compute')},
            'terminal_counts':{t:sum(r['terminal']==t for r in rows) for t in sorted({r['terminal'] for r in rows})},
            'request_attempts':len(sent),'valid_action_calls':sum(m['category']=='valid_action' for m in sent),
            'format_failure_calls':sum(m['category'] in FORMAT_CATEGORIES-{'valid_action'} for m in sent),
            'length_finish':sum(m.get('length_finish') is True for m in sent),
            'usage_available_calls':len(usages),
            'reported_prompt_tokens':sum(u['prompt_tokens'] for u in usages) if usages else None,
            'reported_completion_tokens':sum(u['completion_tokens'] for u in usages) if usages else None,
            'actual_models':sorted({m['model'] for m in sent if isinstance(m.get('model'),str)}),
            'scientific_gate':'HOLD','rl_improvement_claim':False}


def live(plan,output):
    frozen=json.loads(Path(plan).read_text(encoding='utf-8')); require(same(frozen,protocol()),'frozen protocol')
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    require(not any(p.exists() for p in (output,pp,tp)),'use new paths')
    mapping={t['id']:t for t in frozen['design']['tasks']}; rows=[]
    write_json(pp,frozen)
    with tempfile.TemporaryDirectory(prefix='faultda_multistep_') as folder,tp.open('xb') as stream:
        for i,cell in enumerate(frozen['design']['order']):
            client=Client('deepseek-flash',17)
            row=execute(mapping[cell['task_id']],Path(folder)/str(i),cell,client)
            rows.append(row)
            require(sum(sum(m['request_sent'] is True for m in r['receipts']) for r in rows)<=306,'global cap')
            stream.write((json.dumps(row,ensure_ascii=False,allow_nan=False)+'\n').encode()); stream.flush()
            print(json.dumps({'completed':len(rows),'planned':18,'requests':sum(sum(m['request_sent'] is True for m in r['receipts']) for r in rows)}),flush=True)
    write_json(output,{'version':VERSION,'backend':'deepseek_live_multistep','protocol_sha256':sha(pp),
                       'trace_sha256':sha(tp),'summary':summarize(rows)})
    return summarize(rows)


def replay(task,folder,row,cell):
    require(same({k:row[k] for k in cell},cell),'cell identity')
    env=ComputeFaultEnv(task,folder,**{k:cell[k] for k in ('mode','evidence','budget')})
    event_index=0; sent=0
    for index,receipt in enumerate(row['receipts']):
        require(env.terminal is None,'receipt after terminal')
        payload=json.dumps(body(public_observation(env),CONFIG),ensure_ascii=False,allow_nan=False).encode()
        require(receipt['request_sha256']==sha_bytes(payload) and type(receipt['request_bytes']) is int
                and receipt['request_bytes']==len(payload),'public request replay')
        require(type(receipt['request_sent']) is bool,'request sent type')
        if receipt['request_sent']: sent+=1
        require(sent<=17,'episode cap')
        category=receipt['category']
        if category in ERRORS:
            require(index==len(row['receipts'])-1,'error must end episode')
            require((category=='provider_error')==receipt['request_sent'],'error accounting')
            if category=='request_cap': require(sent==17,'unjustified cap')
            if category=='input_limit': require(len(payload)>65536,'unjustified input limit')
            env.terminal=ERRORS[category]
            continue
        require(receipt['request_sent'] and category in FORMAT_CATEGORIES,'format receipt')
        require(type(receipt['length_finish']) is bool and receipt['length_finish']==(receipt['finish_reason']=='length'),'finish consistency')
        if category=='valid_action':
            require(valid_decision(receipt['decision']),'decision schema')
            decision=receipt['decision']
        else:
            require(receipt['decision'] is None,'failed output repaired')
            decision={'action':'invalid_model_output','params':{}}
        env.step(decision['action'],decision['params'])
        require(event_index<len(row['trace']) and same(env.history[-1],row['trace'][event_index]),'tool feedback')
        event_index+=1
    require(env.terminal is not None and event_index==len(row['trace']),'terminal and trace coverage')
    for key,value in evaluate(env).items(): require(same(value,row[key]),'effect replay: '+key)


def verify(output):
    output=Path(output); pp=output.with_suffix('.protocol.json'); tp=output.with_suffix('.jsonl')
    result=json.loads(output.read_text(encoding='utf-8')); frozen=json.loads(pp.read_text(encoding='utf-8'))
    require(result['version']==VERSION and result['backend']=='deepseek_live_multistep','provenance')
    require(result['protocol_sha256']==sha(pp) and result['trace_sha256']==sha(tp),'artifact hash')
    require(same(frozen,protocol()),'complete protocol')
    rows=[json.loads(x) for x in tp.read_text(encoding='utf-8').splitlines()]
    require(len(rows)==18,'coverage'); mapping={t['id']:t for t in frozen['design']['tasks']}
    with tempfile.TemporaryDirectory(prefix='faultda_multistep_replay_') as folder:
        for i,(row,cell) in enumerate(zip(rows,frozen['design']['order'])):
            replay(mapping[cell['task_id']],Path(folder)/str(i),row,cell)
    require(same(result['summary'],summarize(rows)) and result['summary']['request_attempts']<=306,'summary/cap')
    return {'status':'verified','executions':18,'tool_effects_and_public_requests_replayed':True,
            'response_classification_independently_replayed':False,'provider_authenticity_verified':False}


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--freeze',type=Path); parser.add_argument('--protocol',type=Path)
    parser.add_argument('--output',type=Path); parser.add_argument('--verify',type=Path); args=parser.parse_args()
    if args.freeze and not any((args.protocol,args.output,args.verify)): write_json(args.freeze,protocol())
    elif args.verify and not any((args.protocol,args.output,args.freeze)): print(json.dumps(verify(args.verify)))
    elif args.protocol and args.output and not any((args.verify,args.freeze)): print(json.dumps(live(args.protocol,args.output)))
    else: parser.error('choose freeze, verify, or protocol with output')
