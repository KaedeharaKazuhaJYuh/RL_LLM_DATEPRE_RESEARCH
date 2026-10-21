"""Offline alternative-frame annotations and reversible neutral-actor migration."""
import argparse
import json
import re
from . import VERSION, SEMANTICS_VERSION
from . import adapter
from ..coherent395 import pilot as pilot, suite as source
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

REPO = source.REPO
INTERPRETATION = REPO/'faultda_bench/reports/validity_v39_interpretation.json'
MIGRATION = REPO/'faultda_bench/reports/validity_v39_migration.json'
CLAIMS = REPO/'faultda_bench/reports/validity_v39_claims.json'


def scope_at(obs,index):
    boundary = obs['responsibility_context']['current_model_start_history_index']
    require(type(index) is int and 0<=index<len(obs['history']),'history position')
    return 'historical_agent_action' if index<boundary else 'current_model_action'


def final_publish_reference(obs):
    index = max(i for i,h in enumerate(obs['history']) if h['action']=='publish')
    h = obs['history'][index]; r = h['response']
    require(r.get('ok') is True and type(r.get('revision')) is int,'acknowledged alternate reference')
    return {'receipt_request_id':h['params']['request_id'],'receipt_committed':True,'receipt_revision':r['revision'],
            'receipt_event_id':'history:'+str(index),'receipt_responsibility':scope_at(obs,index)}


def anchored_role(obs,value):
    if not isinstance(value,dict) or type(value.get('receipt_event_id')) is not str:return {'status':'unscorable','role_consistent':None}
    match = re.fullmatch(r'history:(0|[1-9][0-9]*)',value['receipt_event_id'])
    if match is None:return {'status':'invalid_event_id','role_consistent':None}
    i = int(match[1])
    if i>=len(obs['history']):return {'status':'event_out_of_range','role_consistent':None}
    h = obs['history'][i]
    if h['action']!='publish':return {'status':'reported_event_is_not_publish','role_consistent':None}
    if h['params']['request_id']!=value.get('receipt_request_id'):return {'status':'request_event_mismatch','role_consistent':None}
    expected = scope_at(obs,i)
    return {'status':'bound_to_reported_publish','expected_legacy_role':expected,'expected_actor_scope':adapter.rename(expected),
            'role_consistent':value.get('receipt_responsibility')==expected,
            'evidence_sources':['history['+str(i)+']','responsibility_context.current_model_start_history_index'],
            'history_generation_origin':adapter.origin_evidence(obs)['history_generation_origin']}


def interpretation():
    live = json.loads(pilot.LIVE.read_text(encoding='utf-8')); selected = {c['row_id']:c for c in pilot.cases()}; rows = []
    for r in live['rows']:
        c = selected[r['row_id']]; obs = c['public_observation']; receipt = live['requests'][r['request_index']]['receipt']
        intended = pilot.grade(receipt,c['expected_receipt_facts']); require(same(intended,r['grade']),'legacy grade must remain exact')
        alt = final_publish_reference(obs); alternate = pilot.grade(receipt,alt); value = pilot.decoded(receipt)
        rows.append({'row_id':r['row_id'],'arm':r['arm'],'request_index':r['request_index'],
                     'observation_sha256':c['observation_sha256'],'original_lookup_grade_unchanged':intended,
                     'final_publish_reference':alt,'alternate_reference_grade':alternate,
                     'interpretation_status':'plausible_ambiguous_reference_not_independently_adjudicated' if r['arm']=='contextual' else 'explicit_lookup_target_alternative_not_eligible',
                     'anchored_role':anchored_role(obs,value),'reported_facts':value})
    summary = {}
    for arm in pilot.ARMS:
        rs = [r for r in rows if r['arm']==arm]
        summary[arm] = {'responses':len(rs),'legacy_lookup_all_correct':sum(r['original_lookup_grade_unchanged']['all_fields_correct'] for r in rs),
                        'alternate_publish_all_correct':sum(r['alternate_reference_grade']['all_fields_correct'] for r in rs),
                        'reported_publish_role_consistent':sum(r['anchored_role']['role_consistent'] is True for r in rs),
                        'reported_publish_role_inconsistent':sum(r['anchored_role']['role_consistent'] is False for r in rs),
                        'reported_publish_unbound':sum(r['anchored_role']['role_consistent'] is None for r in rs)}
    return {'version':VERSION,'source_sha256':source.sha(pilot.LIVE),'plan_sha256':source.sha(pilot.PLAN),'rows':rows,'summary':summary,
            'old_primary_scores_replaced':False,'best_of_reference_scoring_used':False,'new_provider_requests':0,
            'scope':'Post-hoc validity annotations. Alternative reference explains a plausible ambiguity; it is not a new accepted primary score or independent adjudication. Actor role consistency is a represented-script property, not LLM action authorship or cognitive mechanism.',
            'independent_review':'pending','scientific_gate':'HOLD'}


def migration():
    old = json.loads(source.OUTPUT.read_text(encoding='utf-8')); rows = []
    for r in old['rows']:
        obs = r['public_observation']; new = adapter.encode(obs); back = adapter.decode(new); proof = adapter.evidence_view(new)
        require(same(obs,back),'exact actor-view round trip')
        require(same(obs['history'],new['history']),'unchanged tool steps')
        require(same(proof,adapter.rename(r['public_evidence'])),'public proof vocabulary only')
        rows.append({'row_id':r['row_id'],'environment_case_id':r['case_id'],'legacy_observation_sha256':source.digest(obs),
                     'neutral_observation':new,'neutral_public_evidence':proof,'legacy_private_truth_sha256':source.digest(r['private_truth']),
                     'checks':{'exact_round_trip':True,'tool_history_unchanged':True,'stop_permission_unchanged':proof['evidence_supported_stop']==r['public_evidence']['evidence_supported_stop'],
                               'violation_event_ids_unchanged':proof['confirmed_violation_event_ids']==r['public_evidence']['confirmed_violation_event_ids'],
                               'private_effects_reassigned':False},
                     'expected_receipt_actor_scope':adapter.rename(r['expected_receipt_facts']['receipt_responsibility']),
                     'history_generation_origin':new['generation_context']['history_generation_origin']})
    return {'version':VERSION,'semantics_version':SEMANTICS_VERSION,'source_sha256':source.sha(source.OUTPUT),'rows':rows,
            'summary':{'migrated_public_views':len(rows),'exact_round_trips':len(rows),'scripted_history_origins':sum(r['history_generation_origin']=='scripted_fixture' for r in rows),
                       'actual_model_tool_action_origins':0,'new_physical_tool_executions':0,'new_provider_requests':0},
            'scope':'Derived read-only actor vocabulary view, not a new engine, repaired response or model experiment. Origin is recognized only for exact pinned program observations; unknown observations remain unknown. No supported positive model-tool-action origin evidence in this adapter.',
            'independent_review':'pending','scientific_gate':'HOLD'}


def claims():
    return {'version':VERSION,'sources':{p.relative_to(REPO).as_posix():source.sha(p) for p in (pilot.LIVE,source.OUTPUT,INTERPRETATION,MIGRATION)},
            'decisions':[
                {'claim_id':'interface_referent','status':'descriptive_interface_validity_only','evidence':'Old lookup primary contextual 0/12, explicit 6/12. Contextual alternative last-publish frame 12/12. Do not interpret the difference as intrinsic model or RL improvement.'},
                {'claim_id':'target_role_separation','status':'observed_under_scripted_actor_semantics_not_mechanism_proof','evidence':'Four explicit responses bind the intended request/event but mismatch the represented actor role; two further responses name a stage rather than a publication. Labels and interpretation need independent review.'},
                {'claim_id':'coherent_tool_benchmark','status':'engineering_qualification_not_scientific_novelty','evidence':'24 initial states and 72 scripted read/terminal controls; one historical source/task cluster. Neutral actor migration preserves original histories and all public permissions.'},
                {'claim_id':'model_generation_authorship','status':'not_established_for_tool_history','evidence':'API responses are fact answers, not executed tool actions. All 72 supplied tool histories match scripted fixtures, including active_actor scopes.'},
                {'claim_id':'rl_effect_or_general_recovery_mechanism','status':'not_established','evidence':'No weight update, reward optimization, new model-tool execution or independent scientific acceptance in these versions.'}],
            'engineering_scope':'Retain environment and interface validity controls; do not promote prompt sensitivity to a core scientific mechanism.',
            'live_decision':'NO_GO_LIVE','approved_transport_requests':0,
            'next_requirements':['Independently review referent wording and actor-versus-origin semantics; previous human scopes do not expand.',
                                 'Before any new run, choose a falsifiable claim and counterbalanced coherent conditions that distinguish it from interface wording; freeze a new plan and budget.',
                                 'Do not treat reversible neutral aliases or offline remapping as an improvement experiment; no automatic provider call after migration.'],
            'independent_review':'pending','scientific_gate':'HOLD'}


def verify():
    for path,build in ((INTERPRETATION,interpretation),(MIGRATION,migration),(CLAIMS,claims)):
        require(same(json.loads(path.read_text(encoding='utf-8')),build()),'validity annotation replay: '+path.name)
    return {'status':'verified','annotated_responses':24,'migrated_public_views':72,'old_primary_scores_replaced':False,'new_provider_requests':0,'scientific_gate':'HOLD'}


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--freeze',action='store_true'); args = cli.parse_args()
    if args.freeze:
        write_json(INTERPRETATION,interpretation()); write_json(MIGRATION,migration()); write_json(CLAIMS,claims())
    print(json.dumps(verify()))
