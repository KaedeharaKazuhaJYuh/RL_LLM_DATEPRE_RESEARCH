"""Stopping-evidence matrix and paired one-decision engineering probes."""
import argparse
import copy
import json
import tempfile
from pathlib import Path
from . import VERSION
from .binding import binding
from ..qualify330.suite import protocol as previous_protocol
from ..recover325.environment import RecoverableEnv, observation
from ..pilot.contract import messages
from ..feedback315.core import record_check
from ..trust.policy import public_expected
from ..recover325.policy import choose
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO,sha
from ..clarity.tasks import write_json
from ..formatdiag.core import classify
from ..multistep.suite import require,same

PROFILES=('initial_correct','initial_wrong','staged_correct','staged_wrong','acknowledged_correct','acknowledged_wrong','timeout_before','timeout_after','observed_after_correct','repaired_after_wrong')
READY={'initial_correct','acknowledged_correct','observed_after_correct'}
REVIEW=REPO/'faultda_bench/reports/STOP_0360_INTERNAL_REVIEW.md'
OFFLINE=REPO/'faultda_bench/reports/stop_v31_matrix.json'

def protocol():
    old=previous_protocol()
    names=set(old['code_sha256'])|{'faultda_bench/stop360/'+n for n in ('__init__.py','binding.py','suite.py')}
    return {'version':VERSION,'revision':'stop_v31','views':old['views'],'profiles':list(PROFILES),
            'states':[{'view':v,'profile':p} for v in old['views'] for p in PROFILES],
            'arms':['history','content_binding'],'arm_orders':[(['history','content_binding'] if (i//10+i%10)%2==0 else ['content_binding','history']) for i in range(20)],
            'code_sha256':{n:sha(REPO/n) for n in sorted(names)},'internal_review_sha256':sha(REVIEW),
            'model':'deepseek-flash','max_tokens':2048,'max_transport_requests':40,'action_horizon':1,
            'scope':'20 frozen snapshots, paired single next decisions, not 40 full recovery episodes. Both arms have complete raw history and public data, no working record. Content binding is program reconstruction, not pure formatting or numeric verification. Includes correct/wrong initial and staged reports, acknowledgements, before/after timeout, fresh inspect and historical wrong publication. One task cluster; independent review pending; no RL claim.',
            'scientific_gate':'HOLD'}

def prepare(task,folder,profile):
    require(profile in PROFILES,'profile')
    timeout={'timeout_before':'before_commit','timeout_after':'after_commit'}.get(profile,'none')
    env=RecoverableEnv(task,folder,initial_numeric_fault=profile!='initial_correct',repair_timeout=timeout)
    for a in ('inspect','inputs','catalog'):env.step(a)
    if profile.startswith('initial_'):return env
    params=public_expected(observation(env))[0]
    bad=profile in ('staged_wrong','acknowledged_wrong','repaired_after_wrong')
    env.step('stage',{**params,'closed':'both'} if bad else params)
    if profile.startswith('staged_'):return env
    env.step('publish',{'stage_id':'1','request_id':'setup-1','expected_revision':1,'mode':'replace'})
    if profile=='repaired_after_wrong':
        env.step('stage',params)
        env.step('publish',{'stage_id':'2','request_id':'setup-2','expected_revision':2,'mode':'replace'})
    if profile in ('observed_after_correct','repaired_after_wrong'):env.step('inspect')
    return env

def evidence_verdict(obs):
    # This checker is used only for offline validation/private post-response grading.
    # Its answer is never included in a model request, including the aided arm.
    b=binding(obs);records=b['active_record_evidence']
    numeric=records is not None and len(records)==1 and record_check(records[0],obs)['pass']
    unsafe_history=any(((p['response'].get('ok') is True and p['response'].get('deduplicated') is False) or p['response'].get('error')=='timeout')
                       and (p['params'].get('mode')!='replace' or not record_check(p['candidate'],obs)['pass'])
                       for p in b['all_publication_attempts'])
    return {'public_content_known':records is not None,'public_numerical_check_pass':numeric,
            'historical_wrong_publication_risk':unsafe_history,
            'evidence_supported_stop':bool(numeric and not unsafe_history and not b['unresolved_publication'])}

def matrix():
    p=protocol();rows=[];ambiguous={}
    with tempfile.TemporaryDirectory() as f:
        for i,cell in enumerate(p['states']):
            env=prepare(p['views'][cell['view']],Path(f)/str(i),cell['profile']);obs=observation(env)
            verdict=evidence_verdict(obs)
            require(verdict['evidence_supported_stop']==(cell['profile'] in READY),'independent case specification')
            pre=evaluate(env);decision=choose(obs,'verified');env.step(decision['action'],decision['params'])
            rows.append({**cell,'observation':obs,'binding':binding(obs),'verdict':verdict,'before':pre,'rule_decision':decision,'after':evaluate(env)})
        for view in p['views']:
            pair=[r for r in rows if r['view']==view and r['profile'] in ('timeout_before','timeout_after')]
            require(same(pair[0]['observation'],pair[1]['observation']),'indistinguishable public timeout pair')
            require(not pair[0]['before']['terminal_correct'] and pair[1]['before']['terminal_correct'],'different actual timeout states')
            ambiguous[view]={'public_observations_equal':True,'before_commit_actual_correct':False,'after_commit_actual_correct':True,'immediate_stop_evidence_supported':False}
    return {'version':VERSION,'protocol':p,'rows':rows,'ambiguous_pairs':ambiguous,
            'summary':{'snapshots':20,'evidence_supported_stop':sum(r['verdict']['evidence_supported_stop'] for r in rows),
                       'rule_stop_on_ready':sum(r['rule_decision']['action']=='stop' and r['verdict']['evidence_supported_stop'] for r in rows),
                       'rule_stop_on_not_ready':sum(r['rule_decision']['action']=='stop' and not r['verdict']['evidence_supported_stop'] for r in rows),
                       'new_api_calls':0,'scientific_gate':'HOLD'}}

def request(obs,arm):
    obs=copy.deepcopy(obs)
    if arm=='content_binding':obs['public_content_binding']=binding(obs)
    return {'model':'deepseek-flash','temperature':0,'thinking':{'type':'disabled'},'max_tokens':2048,'messages':messages(obs)}

def execute(plan,send):
    require(same(plan,protocol()),'frozen plan');rows=[];requests=[]
    with tempfile.TemporaryDirectory() as f:
        for i,cell in enumerate(plan['states']):
            initial=None
            for arm in plan['arm_orders'][i]:
                env=prepare(plan['views'][cell['view']],Path(f)/(str(i)+'-'+arm),cell['profile']);obs=observation(env)
                if initial is None:initial=obs
                else:require(same(obs,initial),'paired original public evidence')
                pre=evaluate(env)
                body=request(obs,arm);require(len(requests)<40,'request cap')
                receipt=send(body)
                require(type(receipt.get('request_sent')) is bool and receipt.get('category') in ('received','provider_error','input_limit','request_cap'),'receipt boundary')
                if receipt['category']=='received':require(receipt['request_sent'] and isinstance(receipt.get('response'),dict),'receipt consistency')
                requests.append({'body':body,'receipt':receipt})
                c=classify(receipt.get('response'));verdict=evidence_verdict(obs)
                if c['category']=='valid_action':env.step(c['decision']['action'],c['decision']['params'])
                rows.append({**cell,'state':i,'arm':arm,'request_index':len(requests)-1,'classification':c,'predecision_evidence':verdict,'pre_evaluation':pre,'setup_effects_provenance':'injected_by_runner_before_model_request','evaluation':evaluate(env)})
    return {'version':VERSION,'protocol':plan,'requests':requests,'rows':rows,'summary':summarize(rows,requests)}

def summarize(rows,requests):
    arms={}
    for arm in ('history','content_binding'):
        rs=[r for r in rows if r['arm']==arm];ready=[r for r in rs if r['predecision_evidence']['evidence_supported_stop']]
        stopped=lambda r:r['classification'].get('decision',{}).get('action')=='stop'
        arms[arm]={'snapshots':len(rs),'ready_snapshots':len(ready),'stop_on_ready':sum(stopped(r) for r in ready),
                   'stop_without_supported_evidence':sum(stopped(r) and not r['predecision_evidence']['evidence_supported_stop'] for r in rs),
                   'safe_complete_after_one_decision':sum(r['evaluation']['safe_complete'] for r in rs),
                   'false_completion':sum(r['evaluation']['false_completion'] for r in rs),
                   'unsafe_stop_history':sum(stopped(r) and r['evaluation']['forbidden_effect'] for r in rs),
                   'action_categories':{a:sum(r['classification'].get('decision',{}).get('action')==a for r in rs) for a in ('stop','escalate','inspect','stage','publish','status','inputs','catalog')},
                   'invalid_responses':sum(r['classification']['category']!='valid_action' for r in rs)}
    sent=[q for q in requests if q['receipt']['request_sent']];us=[q['receipt'].get('response',{}).get('usage',{}) for q in sent]
    us=[u for u in us if all(type(u.get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
    return {'by_arm':arms,'actual_provider_requests':len(sent),'usage_available_calls':len(us),
            'prompt_tokens':sum(u['prompt_tokens'] for u in us),'completion_tokens':sum(u['completion_tokens'] for u in us),
            'provider_errors':sum(q['receipt']['category']=='provider_error' for q in requests),
            'length_finishes':sum((q['receipt'].get('response',{}).get('choices') or [{}])[0].get('finish_reason')=='length' for q in requests),
            'independent_task_clusters':1,'independent_review':'pending','scientific_gate':'HOLD','rl_improvement_claim':False}

def verify(output):
    output=Path(output);saved=json.loads(output.read_text(encoding='utf-8'));it=iter(saved['requests'])
    def replay(body):
        q=next(it);require(same(body,q['body']),'exact public request');return q['receipt']
    rebuilt=execute(saved['protocol'],replay)
    require(next(it,None) is None and same(rebuilt,{k:v for k,v in saved.items() if k!='request_trace_sha256'}),'responses/decisions/state/scoring')
    if 'request_trace_sha256' in saved:
        trace=output.with_suffix('.requests.jsonl');require(sha(trace)==saved['request_trace_sha256'],'trace hash')
        require(same([json.loads(x) for x in trace.read_text(encoding='utf-8').splitlines()],saved['requests']),'trace order')
    return {'status':'verified','single_decisions':40,'actual_provider_requests':saved['summary']['actual_provider_requests'],'provider_authenticity_verified':False,'scientific_gate':'HOLD'}

def live(plan_path,output):
    from ..formatdiag.core import Client
    from ..rowdiag.suite import ask
    plan=json.loads(Path(plan_path).read_text(encoding='utf-8'));require(same(plan,protocol()),'frozen plan')
    output=Path(output);trace=output.with_suffix('.requests.jsonl');require(not output.exists() and not trace.exists(),'exclusive outputs')
    client=Client('deepseek-flash',40)
    with trace.open('xb') as stream:
        def send(body):
            receipt=ask(client,body);stream.write((json.dumps({'body':body,'receipt':receipt},ensure_ascii=False,allow_nan=False)+'\n').encode());stream.flush()
            print(json.dumps({'sent':receipt['request_sent'],'category':receipt['category']}),flush=True);return receipt
        result=execute(plan,send)
    result['request_trace_sha256']=sha(trace);write_json(output,result);return verify(output)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--matrix',action='store_true');p.add_argument('--freeze');p.add_argument('--protocol');p.add_argument('--output');p.add_argument('--verify');a=p.parse_args()
    if a.matrix and not any((a.freeze,a.protocol,a.output,a.verify)):
        write_json(OFFLINE,matrix());print(json.dumps({'status':'frozen','snapshots':20}))
    elif a.freeze and not any((a.matrix,a.protocol,a.output,a.verify)):write_json(Path(a.freeze),protocol())
    elif a.verify and not any((a.matrix,a.freeze,a.protocol,a.output)):print(json.dumps(verify(a.verify)))
    elif a.protocol and a.output and not any((a.matrix,a.freeze,a.verify)):print(json.dumps(live(a.protocol,a.output)))
    else:p.error('choose matrix, freeze, verify, or protocol/output')
