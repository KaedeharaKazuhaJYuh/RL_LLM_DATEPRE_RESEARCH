"""Separate window, arithmetic, receipt target and responsibility without hidden truth."""
import argparse
import copy
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from . import VERSION
from ..postreceipt385 import suite as old
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

REPO = old.REPO
OUTPUT = REPO/'faultda_bench/reports/probes_v37_offline.json'
PLAN = REPO/'faultda_bench/reports/probes_v37_draft.json'
PROBES = ('window','arithmetic','receipt','responsibility')
ARMS = ('contextual','explicit')
QUESTIONS = {
    'window':('Return exactly selected_row_ids, an array of unique string row ids. ',
              'Select rows in the window specified by the analysis contract.',
              'Select rows with contract.start <= row.time < contract.end, comparing timezone-aware instants.'),
    'arithmetic':('Return exactly reference_total, a decimal string. ',
                  'Sum the raw value for each row id in query.row_ids.',
                  'Add the raw decimal value once for every row id in query.row_ids; do not apply a time window or business-key deduplication.'),
    'receipt':('Return exactly receipt_request_id (string), receipt_committed (boolean), receipt_revision (integer or null), '
               'and receipt_event_id (history:N for the targeted earlier publish, with zero-based history indexing). ',
               'Report the publication targeted by the final receipt.',
               'Report the publication targeted by observation.history[-1], whose action is receipt_lookup.'),
    'responsibility':('Return exactly roles, an array of objects with history_index (integer) and responsibility '
                      '(environment_setup, historical_agent_action or current_model_action), one per query.history_indices. ',
                      'Classify each queried history action under responsibility_context.',
                      'For each queried history action, indices below current_model_start_history_index are historical_agent_action; indices at or above it are current_model_action.')}


def raw_rows(obs):
    require(obs['contract']['version_policy'] == 'snapshot','snapshot-only probe')
    r = next(h['response'] for h in reversed(obs['history']) if h['action'] == 'inputs')
    rows = r['versions'][obs['contract']['snapshot_version']]
    require(len({x['id'] for x in rows}) == len(rows),'unique source row ids')
    return rows


def reference(probe,obs,query):
    require(probe in PROBES,'known probe')
    if probe == 'window':
        c = obs['contract']; require(c['closed'] == 'left','closed-left window')
        a,b = datetime.fromisoformat(c['start']),datetime.fromisoformat(c['end'])
        require(a.utcoffset() is not None and b.utcoffset() is not None and a < b,'valid aware window')
        ids = []
        for row in raw_rows(obs):
            t = datetime.fromisoformat(row['time']); require(t.utcoffset() is not None,'aware row')
            if row['value'] != '' and a <= t < b:ids.append(row['id'])
        return {'selected_row_ids':sorted(ids)}
    if probe == 'arithmetic':
        ids = query['row_ids']; require(isinstance(ids,list) and all(type(k) is str for k in ids) and len(ids) == len(set(ids)),'unique operand ids')
        values = {x['id']:x['value'] for x in raw_rows(obs)}
        require(all(k in values and values[k] != '' for k in ids),'known nonmissing operands')
        return {'reference_total':str(sum((old.number(values[k]) for k in ids),Decimal(0)))}
    if probe == 'receipt':
        h = obs['history']; last = h[-1]
        require(last['action'] == 'receipt_lookup','explicit final lookup target')
        r = last['response']; key = last['params']['request_id']
        require(r['ok'] is True and r['request_id'] == key and type(r['committed']) is bool,'receipt consistency')
        require((r['committed'] and type(r['revision']) is int and r['revision'] > 0) or (not r['committed'] and r['revision'] is None),'commit/revision types')
        indices = [i for i,x in enumerate(h[:-1]) if x['action'] == 'publish' and x['params']['request_id'] == key]
        require(len(indices) == 1,'unique prior publication id')
        return {'receipt_request_id':key,'receipt_committed':r['committed'],'receipt_revision':r['revision'],'receipt_event_id':'history:'+str(indices[0])}
    indices = query['history_indices']; boundary = obs['responsibility_context']['current_model_start_history_index']
    require(type(boundary) is int and 0 <= boundary <= len(obs['history']),'history boundary')
    require(isinstance(indices,list) and all(type(i) is int and 0 <= i < len(obs['history']) for i in indices) and len(indices) == len(set(indices)),'unique history queries')
    return {'roles':[{'history_index':i,'responsibility':'historical_agent_action' if i < boundary else 'current_model_action'} for i in sorted(indices)]}


def query_for(probe,obs):
    if probe == 'arithmetic':return {'row_ids':sorted(r['id'] for r in raw_rows(obs))}
    if probe == 'responsibility':return {'history_indices':[4,8,10]}
    return {}


def body(probe,arm,obs,query):
    require(probe in PROBES and arm in ARMS,'known prompt cell')
    schema,contextual,explicit = QUESTIONS[probe]
    text = schema+(contextual if arm == 'contextual' else explicit)
    return {'model':'deepseek-flash','temperature':0,'thinking':{'type':'disabled'},'max_tokens':2048,
            'response_format':{'type':'json_object'},'messages':[{'role':'system','content':'Use only supplied public facts. This is fact elicitation; no tool executes. '+text},
            {'role':'user','content':json.dumps({'observation':obs,'query':query},ensure_ascii=False,allow_nan=False)}]}


def grade(probe,obs,query,value):
    e = reference(probe,obs,query); valid = isinstance(value,dict) and set(value) == set(e)
    if valid and probe == 'window':
        ids = value['selected_row_ids']; valid = isinstance(ids,list) and all(type(k) is str for k in ids) and len(set(ids)) == len(ids)
    elif valid and probe == 'arithmetic':
        try:old.number(value['reference_total'])
        except ValueError:valid = False
    elif valid and probe == 'receipt':
        valid = type(value['receipt_request_id']) is str and type(value['receipt_event_id']) is str and type(value['receipt_committed']) is bool
        valid = valid and (value['receipt_revision'] is None or type(value['receipt_revision']) is int)
    elif valid:
        roles = value['roles']
        valid = isinstance(roles,list) and all(isinstance(r,dict) and set(r) == {'history_index','responsibility'} and type(r['history_index']) is int and r['responsibility'] in ('environment_setup','historical_agent_action','current_model_action') for r in roles)
        valid = valid and len({r['history_index'] for r in roles}) == len(roles)
    fields = {k:False for k in e}
    if valid:
        for k in fields:
            if k == 'reference_total':fields[k] = abs(old.number(value[k])-old.number(e[k])) <= Decimal('1e-9')
            elif k == 'selected_row_ids':fields[k] = sorted(value[k]) == e[k]
            elif k == 'roles':fields[k] = same(sorted(value[k],key=lambda r:r['history_index']),e[k])
            else:fields[k] = type(value[k]) is type(e[k]) and value[k] == e[k]
    return {'schema_valid':bool(valid),'field_correct':fields,'all_fields_correct':all(fields.values())}


def base_cases():
    return [{'case_id':c['case_id']+'|'+p,'probe':p,'source_request_index':c['source_request_index'],
             'kind':'frozen_original_public_snapshot','observation':copy.deepcopy(c['observation']),
             'query':query_for(p,c['observation'])} for p in PROBES for c in old.snapshots()]


def counter_cases():
    """Synthetic fact-only checks, never executed or scored as recovered Agent tasks."""
    base = old.snapshots()[0]['observation']; rows = []
    for key,change in [('include_end','end'),('exclude_start','start'),('only_end','both')]:
        o = copy.deepcopy(base); c = o['contract']; a,b = datetime.fromisoformat(c['start']),datetime.fromisoformat(c['end'])
        if change == 'end':c['end'] = (b+timedelta(microseconds=1)).isoformat()
        if change == 'start':c['start'] = (a+timedelta(microseconds=1)).isoformat()
        if change == 'both':c.update(start=b.isoformat(),end=(b+timedelta(microseconds=1)).isoformat())
        rows.append({'case_id':'counter|window|'+key,'probe':'window','observation':o,'query':{}})
    for ids in ([],['0','7'],['1','2','3','4','5']):
        rows.append({'case_id':'counter|arithmetic|'+(','.join(ids) or 'empty'),'probe':'arithmetic','observation':copy.deepcopy(base),'query':{'row_ids':ids}})
    for index in (0,1):
        o = copy.deepcopy(old.snapshots()[index]['observation']); o['history'][-1]['params']['request_id'] = 'request-31'
        o['history'][-1]['response'] = {'ok':True,'request_id':'request-31','committed':True,'revision':3}
        rows.append({'case_id':'counter|receipt|repair-'+str(index),'probe':'receipt','observation':o,'query':{}})
    for boundary in (0,8,11):
        o = copy.deepcopy(base); o['responsibility_context']['current_model_start_history_index'] = boundary
        rows.append({'case_id':'counter|responsibility|'+str(boundary),'probe':'responsibility','observation':o,'query':{'history_indices':[4,8,10]}})
    for r in rows:r['kind'] = 'synthetic_fact_only_not_environment_trajectory'
    return rows


def negative_controls(case):
    p,o,q = case['probe'],case['observation'],case['query']; e = reference(p,o,q)
    if p == 'window':
        c = o['contract']; a,b = datetime.fromisoformat(c['start']),datetime.fromisoformat(c['end'])
        return {'constant_old_ids':{'selected_row_ids':['1','2','3','4','5']},
                'closed_both':{'selected_row_ids':sorted(r['id'] for r in raw_rows(o) if a <= datetime.fromisoformat(r['time']) <= b)}}
    if p == 'arithmetic':
        seen = set(); total = Decimal(0)
        for r in raw_rows(o):
            if r['id'] in q['row_ids'] and r['key'] not in seen:total += old.number(r['value']); seen.add(r['key'])
        fixed = reference(p,old.snapshots()[0]['observation'],query_for(p,old.snapshots()[0]['observation']))
        return {'constant_old_sum':fixed,'deduplicate_business_key':{'reference_total':str(total)}}
    if p == 'receipt':
        h = o['history']; i = max(i for i,x in enumerate(h) if x['action'] == 'publish'); x = h[i]
        return {'last_publish_instead_of_lookup_target':{'receipt_request_id':x['params']['request_id'],'receipt_committed':True,'receipt_revision':x['response'].get('revision'),'receipt_event_id':'history:'+str(i)},
                'constant_request17':reference(p,old.snapshots()[0]['observation'],{})}
    b = o['responsibility_context']['current_model_start_history_index']
    return {'all_current_model':{'roles':[{'history_index':i,'responsibility':'current_model_action'} for i in q['history_indices']]},
            'off_by_one_boundary':{'roles':[{'history_index':i,'responsibility':'historical_agent_action' if i <= b else 'current_model_action'} for i in q['history_indices']]},
            'constant_old_roles':reference(p,old.snapshots()[0]['observation'],q)}


def offline():
    rows = []
    for c in base_cases()+counter_cases():
        p,o,q = c['probe'],c['observation'],c['query']; e = reference(p,o,q)
        controls = {k:grade(p,o,q,v) for k,v in negative_controls(c).items()}
        require(grade(p,o,q,e)['all_fields_correct'],'reference baseline')
        rows.append({**c,'public_payload_sha256':old.digest({'observation':o,'query':q}),'expected':e,'strong_reference_grade':grade(p,o,q,e),'negative_control_grades':controls})
    summary = {}
    for p in PROBES:
        groups = {k:[r for r in rows if r['probe'] == p and r['kind'] == v] for k,v in [('original','frozen_original_public_snapshot'),('counter','synthetic_fact_only_not_environment_trajectory')]}
        summary[p] = {k:{'cases':len(rs),'strong_reference_correct':sum(r['strong_reference_grade']['all_fields_correct'] for r in rs),
                         'negative_control_correct':{name:sum(r['negative_control_grades'][name]['all_fields_correct'] for r in rs) for name in rs[0]['negative_control_grades']}} for k,rs in groups.items()}
    return {'version':VERSION,'source_sha256':old.sha(old.SOURCE),'previous_diagnostic_sha256':old.sha(old.LIVE),'rows':rows,'summary':summary,
            'original_probe_cases':16,'synthetic_fact_counter_cases':11,'new_provider_requests':0,
            'scope':'Program references and deliberately wrong rules only. Synthetic changed questions are not coherent recovery trajectories; do not use stale report/ledger fields to score terminal safety. Four original snapshots share one task cluster.',
            'independent_review':'pending','scientific_gate':'HOLD'}


def draft():
    cells = []
    for case in base_cases():
        for arm in ARMS:
            b = body(case['probe'],arm,case['observation'],case['query'])
            size = len(json.dumps(b,ensure_ascii=False,allow_nan=False).encode()); require(size <= 65536,'candidate byte cap')
            cells.append({'cell_id':case['case_id']+'|'+arm,'case_id':case['case_id'],'probe':case['probe'],'arm':arm,
                          'body':b,'serialized_request_bytes':size,'body_sha256':old.digest(b)})
    for c in base_cases():
        pair = [x for x in cells if x['case_id'] == c['case_id']]
        require(pair[0]['body']['messages'][1] == pair[1]['body']['messages'][1],'pair has exactly equal public data')
    return {'version':VERSION,'status':'design_only_NOT_APPROVED_FOR_LIVE','source_sha256':old.sha(old.SOURCE),
            'previous_diagnostic_sha256':old.sha(old.LIVE),'code_sha256':old.sha(__file__),
            'cells':cells,'candidate_requests':32,
            'approved_transport_requests':0,'candidate_upper_limits':{'per_request_completion_tokens':2048,'completion_tokens_total':65536,'request_bytes_each':65536,'request_bytes_total':2097152},
            'primary_per_probe':'paired all-fields-correct differences on the same four original snapshots; no pooling across probes or independent-episode claim',
            'one_changed_component':'Within a probe pair only one instruction sentence changes; output schema, user payload, model and caps are identical. Clarification is a bundled wording treatment, not an isolated cognitive mechanism.',
            'comparison_limits':'Focused schemas differ from old omnibus diagnostic; cross-probe inputs/queries differ. Neither contrast estimates the cause of earlier decisions. Equal caps and public payload are not equal actual token/currency cost.',
            'no_go_reason':'Constant old answers pass all four original numeric/role probes. Fact counterexamples catch them, but remain synthetic and not coherent recovery tasks. Draft outcome/wording validity and independent review are not established; another prompt-sensitivity run does not yet decide scientific mechanism.',
            'next_go_conditions':['Independent inspectable wording/scorer review or resolve concrete technical objections under internal review; never treat it as scientific acceptance.',
                                  'Predeclare whether to counterbalance query answers in coherent task states; fix task/cluster denominator and a falsifiable competing explanation.',
                                  'Freeze a new executable plan, failure accounting and costs before any separately bounded GO; this module has no live entry point.'],
            'independent_review':'pending','scientific_gate':'HOLD'}


def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')),offline()),'reference/counterexample replay')
    require(same(json.loads(PLAN.read_text(encoding='utf-8')),draft()),'same-data paired prompt draft')
    return {'status':'verified','original_probe_cases':16,'synthetic_fact_counter_cases':11,'candidate_prompt_cells':32,'actual_provider_requests':0,'independent_review':'pending','scientific_gate':'HOLD'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze',action='store_true'); a = p.parse_args()
    if a.freeze:write_json(OUTPUT,offline()); write_json(PLAN,draft())
    print(json.dumps(verify()))
