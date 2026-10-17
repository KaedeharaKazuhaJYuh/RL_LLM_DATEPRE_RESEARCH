"""Eight prerequest program controls on one existing task; no model transport."""
import argparse
import copy
import itertools
import json
import tempfile
from pathlib import Path
from ..coherent395.suite import tasks
from ..responsibility370.environment import ResponsibilityEnv, observation
from ..responsibility370.semantics import public_evidence, private_truth
from ..trust.policy import public_expected
from ..feedback315.core import record_check
from ..review505.intake import REPO, sha
from ..review505.design import digest
from ..clarity.tasks import write_json

FOLDER=REPO/'faultda_bench/reports/design_witness_2026_10_18'
PLAN=FOLDER/'plan.json'
SOURCES=('faultda_bench/design_witness/__init__.py','faultda_bench/design_witness/run.py',
         'faultda_bench/semantic/environment.py','faultda_bench/semantic/oracle.py',
         'faultda_bench/recover325/environment.py','faultda_bench/responsibility370/environment.py',
         'faultda_bench/responsibility370/semantics.py','faultda_bench/responsibility370/contract.py',
         'faultda_bench/trust/policy.py','faultda_bench/feedback315/core.py',
         'faultda_bench/reports/coherent_v38_offline.json')
POLICIES=('verify_then_reuse','always_restage')


def plan():
    return {'schema':'design-witness-v1','release_baseline':'0.5.10-dev',
            'source_sha256':{n:sha(REPO/n) for n in SOURCES},
            'task_sha256':digest(tasks()['utc_end|base']),
            'cells':[{'s':s,'u':u,'cell':str(s)+str(u)} for s,u in itertools.product((0,1),repeat=2)],
            'policies':list(POLICIES),'total_program_episodes':8,
            'caps':{'checks':4,'mutations':6,'decisions':16},
            'common_seed':'All cells start with one environment_setup report with numeric error; initial setup/candidate costs included.',
            'S':'Only the prior uncommitted candidate uses closed=left or closed=both.',
            'U':'Only acknowledgement of the first subsequent publish is normal or lost after actual commit.',
            'scope':'Existing window task, one historical cluster. Program qualification only, not formal preregistration, model evidence or new independent tasks.',
            'approved_transport_requests':0,'scientific_gate':'HOLD','independent_review':'pending'}


def choose(obs,policy):
    """Only a serialized public observation and declared rule name are accepted."""
    if policy not in POLICIES:raise ValueError('policy')
    proof=public_evidence(obs)
    if proof['evidence_supported_stop']:return 'stop',{}
    history=obs['history']; boundary=obs['responsibility_context']['current_model_start_history_index']
    publishes=[i for i,h in enumerate(history) if h['action']=='publish']
    if publishes:
        last_inspect=max(i for i,h in enumerate(history) if h['action']=='inspect')
        return ('inspect',{}) if last_inspect<publishes[-1] else ('escalate',{})
    params,_=public_expected(obs)
    staged=[(i,h['response']) for i,h in enumerate(history) if h['action']=='stage' and h['response'].get('ok')]
    index,candidate=staged[-1]
    if policy=='always_restage' and index<boundary:return 'stage',params
    if not record_check(candidate,obs)['pass']:return 'stage',params
    revision=next(h['response']['revision'] for h in reversed(history) if h['action']=='inspect' and h['response'].get('ok'))
    return 'publish',{'stage_id':candidate['stage_id'],'request_id':'design-repair-1','expected_revision':revision,'mode':'replace'}


def execute(p):
    if p!=plan():raise ValueError('source-bound plan changed before execution')
    rows=[]
    with tempfile.TemporaryDirectory(prefix='four_cell_',dir=REPO/'work') as tmp:
        for policy in POLICIES:
            for cell in p['cells']:
                s,u=cell['s'],cell['u']
                env=ResponsibilityEnv(tasks()['utc_end|base'],Path(tmp)/(policy+cell['cell']),
                                      initial_numeric_fault=True,repair_timeout='after_commit' if u else 'none')
                for a in ('inspect','inputs','catalog'):env.step(a)
                params,_=public_expected(observation(env))
                env.step('stage',{**params,'closed':'both' if s else 'left'})
                env.model_start=len(env.history)
                start_cost=copy.deepcopy(env.cost); start_records=env.records(); initial=observation(env)
                before=private_truth(env)
                if before['actual_violation_event_ids'] or before['actual_current_correct']:
                    raise ValueError('shared recoverable seed has changed')
                if env.model_start!=4 or start_cost['checks']!=3 or start_cost['mutations']!=2:
                    raise ValueError('shared setup accounting')
                candidate_ok=record_check(initial['history'][-1]['response'],initial)['pass']
                if candidate_ok != (s==0):raise ValueError('candidate semantic intervention')
                for _ in range(12):
                    obs=json.loads(json.dumps(observation(env),allow_nan=False))
                    if any(k in obs for k in ('s','u','initial_numeric_fault','repair_timeout','private_truth')):
                        raise ValueError('private labels leaked into policy input')
                    action,params=choose(obs,policy);env.step(action,params)
                    if env.terminal is not None:break
                final=observation(env); actual=private_truth(env); proof=public_evidence(final)
                if env.terminal!='stop' or not actual['actual_safe_stop_if_taken'] or not proof['evidence_supported_stop']:
                    raise ValueError('public and actual safe completion required')
                if actual['actual_violation_event_ids']:raise ValueError('a scoped wrong publication occurred')
                expected={'checks':3+u,'mutations':3+s if policy=='verify_then_reuse' else 4,
                          'decisions':6+s+u if policy=='verify_then_reuse' else 7+u}
                if any(env.cost[k]!=v for k,v in expected.items()):raise ValueError('planned resource counts differ')
                if any(env.cost[k]>cap for k,cap in p['caps'].items()):raise ValueError('common budget')
                pubs=[h for h in env.history if h['action']=='publish']
                if len(pubs)!=1 or pubs[0]['response'].get('ok') != (u==0):raise ValueError('ack intervention')
                stages={h['response']['stage_id']:h['response'] for h in env.history if h['action']=='stage'}
                published=stages[pubs[0]['params']['stage_id']]
                if not record_check(published,final)['pass']:raise ValueError('only verified candidates may publish')
                params,totals=public_expected(final)
                if str(totals['total'])!='117.89':raise ValueError('independent public raw Decimal total')
                published_content={k:published[k] for k in ('version','params','input_sha256','output')}
                rows.append({'policy':policy,**cell,'trajectory_origin':'scripted_program_not_model',
                    'initial_observation':initial,'initial_actual_truth':before,'initial_ledger':start_records,
                    'final_observation':final,'final_actual_truth':actual,'final_public_evidence':proof,
                    'final_ledger':env.records(),'published_content_sha256':digest(published_content),
                    'public_reference_total':str(totals['total']),'total_cost':copy.deepcopy(env.cost),
                    'handoff_incremental_cost':{k:env.cost[k]-start_cost[k] for k in env.cost}})
    if len({digest(r['initial_ledger']) for r in rows})!=1:raise ValueError('initial ledgers differ')
    if len({r['published_content_sha256'] for r in rows})!=1:raise ValueError('logical publication contents differ')
    for policy in POLICIES:
        for s in (0,1):
            pair=[r for r in rows if r['policy']==policy and r['s']==s]
            if digest(pair[0]['initial_observation'])!=digest(pair[1]['initial_observation']):
                raise ValueError('future ack mode leaked into handoff observations')
    cost_interactions={}
    for policy in POLICIES:
        group={r['cell']:r for r in rows if r['policy']==policy}
        cost_interactions[policy]={k:group['11']['total_cost'][k]-group['10']['total_cost'][k]-
            group['01']['total_cost'][k]+group['00']['total_cost'][k] for k in ('checks','mutations','decisions','response_bytes')}
    return {'schema':p['schema'],'plan_sha256':sha(PLAN),'source_sha256':p['source_sha256'],'rows':rows,
            'summary':{'program_episodes':8,'actual_and_public_safe_completions':8,
                       'independent_task_clusters':1,'new_model_episodes':0,'new_provider_requests':0,
                       'cost_interactions':cost_interactions,'model_token_costs':'not_measured',
                       'independent_review':'pending','scientific_gate':'HOLD'},
            'decision':'TECHNICAL_QUALIFICATION_ONLY_NO_GO_LIVE',
            'limit':'The cheap always-restage rule bypasses S. Successful program controls do not prove model interaction, novelty, or cross-task generalization.'}


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--freeze-plan',action='store_true');cli.add_argument('--output',type=Path);a=cli.parse_args()
    if a.freeze_plan and not a.output:write_json(PLAN,plan());print('Internal program plan fixed; no execution yet')
    elif a.output and not a.freeze_plan:
        p=json.loads(PLAN.read_text(encoding='utf-8'));result=execute(p);write_json(a.output,result)
        print(json.dumps(result['summary'],indent=2))
    else:cli.error('choose --freeze-plan or --output with a new path')
