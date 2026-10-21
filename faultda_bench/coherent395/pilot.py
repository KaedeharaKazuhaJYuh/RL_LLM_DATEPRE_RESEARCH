"""Predeclared 12 paired receipt-target probes, not a recovery or RL experiment."""
import argparse
import json
from pathlib import Path
from . import VERSION, suite as s
from ..rowdiag.suite import decoded
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

PLAN = s.REPO/'faultda_bench/reports/coherent_v38_plan.json'
DRY = s.REPO/'faultda_bench/reports/coherent_v38_dry.json'
LIVE = s.REPO/'faultda_bench/reports/coherent_v38_deepseek.json'
GO = s.REPO/'faultda_bench/reports/COHERENT_0395_GO_NO_GO.json'
REVIEW = s.REPO/'faultda_bench/reports/COHERENT_0395_INTERNAL_REVIEW.md'
FIELDS = ('receipt_request_id','receipt_committed','receipt_revision','receipt_event_id','receipt_responsibility')
ARMS = ('contextual','explicit')


def cases():
    data = json.loads(s.OUTPUT.read_text(encoding='utf-8')); view = s.cells()[0]['view']; result = []
    for cell in s.cells():
        if cell['view'] != view:continue
        target = 'first' if (list(s.WINDOWS).index(cell['window'])+s.ROLES.index(cell['role']))%2==0 else 'second'
        r = next(r for r in data['rows'] if r['case_id']==cell['case_id'] and r['target']==target)
        result.append(r)
    require(len(result)==12,'all twelve selected states')
    return result


def body(obs,arm):
    require(arm in ARMS,'arm')
    sentence = ('Report the publication targeted by the final receipt.' if arm=='contextual' else
                'Report the publication targeted by observation.history[-1], whose action is receipt_lookup.')
    system = ('Use only supplied public facts. Return exactly one JSON object with receipt_request_id (string), '
              'receipt_committed (boolean), receipt_revision (integer or null), receipt_event_id (history:N for the targeted earlier publish, zero-based history indexing), '
              'and receipt_responsibility (environment_setup, historical_agent_action or current_model_action under responsibility_context). '
              'The history is a labelled scripted counterexample; use its represented actor boundary without resetting it for this fact-elicitation request. '
              'No tool executes and no correctness feedback is supplied. '+sentence)
    return {'model':'deepseek-flash','temperature':0,'thinking':{'type':'disabled'},'max_tokens':1024,'response_format':{'type':'json_object'},
            'messages':[{'role':'system','content':system},{'role':'user','content':json.dumps({'observation':obs},ensure_ascii=False,allow_nan=False)}]}


def protocol():
    selected = cases(); cells = []
    for i,c in enumerate(selected):
        for arm in (ARMS if i%2==0 else tuple(reversed(ARMS))):
            b = body(c['public_observation'],arm); size = len(json.dumps(b,ensure_ascii=False,allow_nan=False).encode())
            require(size <= 65536,'planned request size')
            cells.append({'row_id':c['row_id'],'arm':arm,'body_sha256':s.digest(b)})
    return {'version':VERSION,'source_sha256':s.sha(s.OUTPUT),'code_sha256':{n:s.sha(s.REPO/n) for n in ('faultda_bench/coherent395/__init__.py','faultda_bench/coherent395/suite.py','faultda_bench/coherent395/pilot.py')},
            'internal_review_sha256':s.sha(REVIEW),'cells':cells,'max_transport_requests':24,'max_request_bytes':65536,'max_sent_request_bytes_total':1572864,
            'max_completion_tokens_per_request':1024,'max_completion_tokens_total':24576,'input_token_limit':'not pre-counted; request byte caps plus actual provider usage',
            'primary':'paired all-five-fields-correct difference over 12 same-snapshot prompt pairs',
            'secondary':['exact target request_id and event_id','receipt metadata correctness','role incorrect despite exact target; conditional descriptive count, not a causal effect'],
            'hypotheses':['Clarifying only the receipt referent changes explicit target/combined fact correctness.','A correct target may still be assigned the wrong represented actor role.'],
            'order':'alternate arm order across fixed cases; one request per cell, no retries or selective supplementation',
            'scope':'Three related windows x two represented scripted actor roles x two hidden histories, one UTC rendering. Same public observation/output schema and settings within a pair; one final system sentence differs. Twelve condition pairs are one data/task cluster, not twelve independent tasks. No tool execution, stop score, training or improvement claim. Previous 32-cell draft remains unapproved.',
            'independent_review':'pending','scientific_gate':'HOLD'}


def grade(receipt,expected):
    v = decoded(receipt); valid = isinstance(v,dict) and set(v)==set(FIELDS)
    if valid:
        valid = all(type(v[k]) is str for k in ('receipt_request_id','receipt_event_id','receipt_responsibility')) and type(v['receipt_committed']) is bool
        valid = valid and (v['receipt_revision'] is None or type(v['receipt_revision']) is int)
        valid = valid and v['receipt_responsibility'] in ('environment_setup','historical_agent_action','current_model_action')
    fields = {k:bool(valid and type(v[k]) is type(expected[k]) and v[k]==expected[k]) for k in FIELDS}
    target = fields['receipt_request_id'] and fields['receipt_event_id']
    return {'schema_valid':bool(valid),'field_correct':fields,'all_fields_correct':all(fields.values()),
            'exact_target':bool(target),'exact_target_wrong_role':bool(target and not fields['receipt_responsibility'])}


def execute(plan,send,transport):
    require(same(plan,protocol()) and transport in ('scripted','live'),'frozen plan/transport')
    source = {c['row_id']:c for c in cases()}; requests = []; rows = []
    for cell in plan['cells']:
        c = source[cell['row_id']]; b = body(c['public_observation'],cell['arm']); size = len(json.dumps(b,ensure_ascii=False,allow_nan=False).encode())
        require(s.digest(b)==cell['body_sha256'] and len(requests)<24 and size<=65536,'pre-send request cap/binding')
        require(sum(q['serialized_request_bytes'] for q in requests)+size<=1572864,'total bytes before sender')
        receipt = send(b)
        if transport=='scripted':require(receipt.get('category')=='scripted_fixture' and receipt.get('request_sent') is False,'scripted boundary')
        else:
            require(type(receipt.get('request_sent')) is bool and receipt.get('category') in ('received','provider_error','input_limit','request_cap'),'live boundary')
            if receipt['category']=='received':require(receipt['request_sent'] and isinstance(receipt.get('response'),dict),'received consistency')
        requests.append({'body':b,'receipt':receipt,'serialized_request_bytes':size})
        rows.append({**cell,'request_index':len(requests)-1,'grade':grade(receipt,c['expected_receipt_facts'])})
    byarm = {}
    for arm in ARMS:
        rs = [r for r in rows if r['arm']==arm]
        byarm[arm] = {'cells':len(rs),**{k:sum(r['grade'][k] for r in rs) for k in ('schema_valid','all_fields_correct','exact_target','exact_target_wrong_role')},
                      'field_correct':{k:sum(r['grade']['field_correct'][k] for r in rs) for k in FIELDS}}
    pairs = {'both_correct':0,'contextual_only':0,'explicit_only':0,'neither_correct':0}
    for c in source:
        d = {r['arm']:r['grade']['all_fields_correct'] for r in rows if r['row_id']==c}
        k = 'both_correct' if all(d.values()) else ('contextual_only' if d['contextual'] else ('explicit_only' if d['explicit'] else 'neither_correct'))
        pairs[k] += 1
    sent = [q for q in requests if q['receipt']['request_sent']]; usage = [q['receipt'].get('response',{}).get('usage',{}) for q in sent]
    usage = [u for u in usage if all(type(u.get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
    return {'version':VERSION,'transport':transport,'protocol':plan,'requests':requests,'rows':rows,
            'summary':{'actual_provider_requests':len(sent),'scripted_requests':len(requests) if transport=='scripted' else 0,'by_arm':byarm,'paired_all_correct':pairs,
                       'explicit_minus_contextual_correct':byarm['explicit']['all_fields_correct']-byarm['contextual']['all_fields_correct'],
                       'usage_available_calls':len(usage),'prompt_tokens':sum(u['prompt_tokens'] for u in usage),'completion_tokens':sum(u['completion_tokens'] for u in usage),
                       'sent_request_bytes':sum(q['serialized_request_bytes'] for q in sent),'provider_errors':sum(q['receipt']['category']=='provider_error' for q in requests),
                       'length_finishes':sum((q['receipt'].get('response',{}).get('choices') or [{}])[0].get('finish_reason')=='length' for q in requests),
                       'model_tool_executions':0,'independent_task_clusters':1,'rl_improvement_claim':False,'independent_review':'pending','scientific_gate':'HOLD'}}


def fixture(b):
    obs = json.loads(b['messages'][1]['content'])['observation']; e = s.reference('receipt',obs,{})
    index = int(e['receipt_event_id'].split(':')[1]); e['receipt_responsibility'] = 'historical_agent_action' if index<obs['responsibility_context']['current_model_start_history_index'] else 'current_model_action'
    return {'category':'scripted_fixture','request_sent':False,'response':{'choices':[{'message':{'content':json.dumps(e)},'finish_reason':'stop'}]}}


def verify(output):
    output = Path(output); saved = json.loads(output.read_text(encoding='utf-8')); it = iter(saved['requests'])
    def replay(b):
        q = next(it); require(same(q['body'],b),'exact request replay'); return q['receipt']
    rebuilt = execute(saved['protocol'],replay,saved['transport'])
    require(next(it,None) is None and same(rebuilt,{k:v for k,v in saved.items() if k!='request_trace_sha256'}),'response/field/paired/denominator replay')
    if 'request_trace_sha256' in saved:
        trace = output.with_suffix('.requests.jsonl'); require(s.sha(trace)==saved['request_trace_sha256'],'trace hash')
        require(same([json.loads(x) for x in trace.read_text(encoding='utf-8').splitlines()],[{'body':q['body'],'receipt':q['receipt']} for q in saved['requests']]),'trace order')
    return {'status':'verified','cells':24,'provider_authenticity_verified':False,'scientific_gate':'HOLD'}


def live(output):
    plan = json.loads(PLAN.read_text(encoding='utf-8')); require(same(plan,protocol()),'frozen plan')
    s.verify(); verify(DRY); go = json.loads(GO.read_text(encoding='utf-8'))
    require(go['decision']=='GO_bounded_paired_diagnostic' and go['max_transport_requests']==24,'bounded internal GO')
    require(go['plan_sha256']==s.sha(PLAN) and go['dry_sha256']==s.sha(DRY) and go['source_sha256']==s.sha(s.OUTPUT),'prospective GO inputs')
    require(go['scientific_gate']=='HOLD' and go['independent_review']=='pending','review scope')
    output = Path(output); trace = output.with_suffix('.requests.jsonl'); require(not output.exists() and not trace.exists(),'exclusive outputs')
    from ..formatdiag.core import Client
    from ..rowdiag.suite import ask
    client = Client('deepseek-flash',24)
    with trace.open('xb') as stream:
        def send(b):
            r = ask(client,b); stream.write((json.dumps({'body':b,'receipt':r},ensure_ascii=False,allow_nan=False)+'\n').encode()); stream.flush()
            print(json.dumps({'category':r['category'],'sent':r['request_sent']}),flush=True); return r
        data = execute(plan,send,'live')
    data['request_trace_sha256'] = s.sha(trace); write_json(output,data); return verify(output)


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze',action='store_true'); p.add_argument('--dry-run',type=Path); p.add_argument('--live',type=Path); p.add_argument('--verify',type=Path); a = p.parse_args()
    require(sum(bool(v) for v in vars(a).values())==1,'choose one operation')
    if a.freeze:write_json(PLAN,protocol())
    elif a.dry_run:write_json(a.dry_run,execute(protocol(),fixture,'scripted')); print(json.dumps(verify(a.dry_run)))
    elif a.live:print(json.dumps(live(a.live)))
    else:print(json.dumps(verify(a.verify)))
