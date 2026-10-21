"""Pin all four old/new pairs for review; scope checks do not authenticate people."""
import argparse
import json
import re
from pathlib import Path
from . import VERSION
from . import suite as s
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

REGISTRY = s.REPO/'faultda_bench/reports/postreceipt_v36_review_registry.json'
TEMPLATE = s.REPO/'faultda_bench/reports/postreceipt_v36_review_template.json'
CHECKS = ('raw_rows_and_window','selected_row_arithmetic','receipt_target_and_revision',
          'responsibility_boundary','current_vs_historical_correctness','terminal_permission',
          'original_vs_diagnostic_scope','prompt_ambiguity_and_scoring')


def registry():
    old = s.offline(); live = json.loads(s.LIVE.read_text(encoding='utf-8')); cases = {}
    for a,b,q in zip(old['rows'],live['rows'],live['requests']):
        require(a['case_id'] == b['case_id'], 'case alignment')
        cases[a['case_id']] = {'pair_sha256':s.digest({'offline_case':a,'diagnostic_receipt':q['receipt'],'diagnostic_grade':b['grade']}),
                               'source_request_index':a['source_request_index'],'diagnostic_request_index':b['request_index']}
    return {'version':VERSION,'source_files':{p.relative_to(s.REPO).as_posix():s.sha(p) for p in (s.SOURCE,s.OFFLINE,s.PLAN,s.LIVE)},
            'cases':cases,'required_checks':list(CHECKS),'independent_review':'pending','scientific_gate':'HOLD'}


def template(reg):
    return {'version':VERSION,'reviewer':{'name':None,'declares_human':None,'personally_checked':None,'reviewed_git_commit':None},
            'overall_verdict':None,'case_reviews':[{'case_id':k,'pair_sha256':v['pair_sha256'],
                'checks':{c:None for c in CHECKS},'verdict':None,'comments':''} for k,v in reg['cases'].items()],
            'notice':'Only fill personally reviewed cases; partial returns allowed. Include prompt/scoring objections. Declarations are not identity verification or scientific acceptance.'}


def validate(sub,reg):
    issues = []; checked = []; seen = set()
    if not isinstance(sub,dict):sub = {}; issues.append('submission must be object')
    if sub.get('version') != VERSION:issues.append('version mismatch')
    r = sub.get('reviewer'); r = r if isinstance(r,dict) else {}
    if type(r.get('name')) is not str or not r['name'].strip():issues.append('name missing')
    if r.get('declares_human') is not True or r.get('personally_checked') is not True:issues.append('personal human declaration missing')
    if type(r.get('reviewed_git_commit')) is not str or re.fullmatch('[a-fA-F0-9]{40}',r['reviewed_git_commit']) is None:issues.append('full commit SHA required')
    if sub.get('overall_verdict') not in ('pass','change','reject'):issues.append('overall verdict missing')
    entries = sub.get('case_reviews'); entries = entries if isinstance(entries,list) else []
    for row in entries:
        if not isinstance(row,dict):issues.append('non-object case'); continue
        key = row.get('case_id')
        if type(key) is not str or key not in reg['cases']:issues.append('unknown case'); continue
        if key in seen:issues.append('duplicate case'); continue
        seen.add(key)
        if row.get('pair_sha256') != reg['cases'][key]['pair_sha256']:issues.append('stale pair'); continue
        checks = row.get('checks')
        if not isinstance(checks,dict) or set(checks) != set(CHECKS):issues.append('check scope mismatch'); continue
        if not all(checks[k] is True for k in CHECKS):continue
        if row.get('verdict') not in ('pass','change','reject') or type(row.get('comments')) is not str:issues.append('case verdict/comments missing'); continue
        checked.append(key)
    if not checked:issues.append('no complete personally checked cases')
    return {'status':'invalid' if issues else 'scope_validated_identity_unverified','issues':issues,'checked_case_ids':checked,
            'remaining_case_ids':[k for k in reg['cases'] if k not in checked],'reviewer_identity_authenticated':False,
            'human_review_registered':False,'reviewed_commit_resolved':False,'independent_review':'pending','scientific_gate':'HOLD'}


def verify():
    reg = json.loads(REGISTRY.read_text(encoding='utf-8'))
    require(same(reg,registry()),'four-pair review registry')
    require(same(json.loads(TEMPLATE.read_text(encoding='utf-8')),template(reg)),'blank unsigned template')
    require(validate(template(reg),reg)['status'] == 'invalid','unsigned cannot count')
    return {'status':'verified','scope_cases':4,'independent_review':'pending','scientific_gate':'HOLD'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze',action='store_true'); p.add_argument('--submission',type=Path); p.add_argument('--output',type=Path); a = p.parse_args()
    if a.freeze and not (a.submission or a.output):
        reg = registry(); write_json(REGISTRY,reg); write_json(TEMPLATE,template(reg)); print(json.dumps(verify()))
    elif a.submission and a.output and not a.freeze:
        verify(); sub = json.loads(a.submission.read_text(encoding='utf-8')); result = validate(sub,registry())
        result['submission_sha256'] = s.sha(a.submission); write_json(a.output,result); print(json.dumps(result))
    elif not any((a.freeze,a.submission,a.output)):print(json.dumps(verify()))
    else:p.error('choose freeze, submission/output, or verify')
