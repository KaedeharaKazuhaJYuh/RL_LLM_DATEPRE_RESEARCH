"""Review scope validation only; never authenticates a human or grants acceptance."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from . import VERSION
from .suite import OUTPUT
from ..semantic.tasks import REPO,sha
from ..clarity.tasks import write_json
from ..multistep.suite import require,same
OLD=REPO/'faultda_bench/reports/responsibility_v33_results.json'
REGISTRY=REPO/'faultda_bench/reports/review_v34_registry.json'
TEMPLATE=REPO/'faultda_bench/reports/review_v34_return_template.json'

def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False).encode()).hexdigest()

def registry():
    old=json.loads(OLD.read_text(encoding='utf-8'));new=json.loads(OUTPUT.read_text(encoding='utf-8'));cases={}
    for i,row in enumerate(old['rows']):
        key='v33|'+row['view']+'|'+row['profile']
        cases[key]={'snapshot_sha256':digest(row),'source_file':OLD.relative_to(REPO).as_posix(),'row_index':i,'semantics_version':'responsibility-v1'}
    for i,row in enumerate(new['snapshots']):
        key='v34|'+row['case_id']
        cases[key]={'snapshot_sha256':digest(row),'source_file':OUTPUT.relative_to(REPO).as_posix(),'row_index':i,'semantics_version':'responsibility-v1.1-receipt-witness'}
    return {'version':VERSION,'scope':'36 existing responsibility cases plus 4 new history witnesses. Not scientific novelty acceptance.',
            'source_files':{p.relative_to(REPO).as_posix():sha(p) for p in (OLD,OUTPUT)},'cases':cases,
            'independent_review':'pending','scientific_gate':'HOLD'}

def template(reg):
    return {'version':VERSION,'reviewer':{'name':None,'declares_human':None,'declares_personally_checked':None,'reviewed_git_commit':None},
            'overall_technical_verdict':None,
            'case_reviews':[{'case_id':k,'snapshot_sha256':v['snapshot_sha256'],'checked':None,'verdict':None,'comments':''} for k,v in reg['cases'].items()],
            'instructions':'Fill only cases personally reviewed; partial submissions are allowed. pass/change/reject are technical verdicts. Identity statements require user confirmation and do not grant scientific acceptance.'}

def validate_submission(submitted,reg):
    issues=[];reviewer=submitted.get('reviewer',{}) if isinstance(submitted,dict) else {}
    if not isinstance(submitted,dict):return {'status':'invalid','issues':['submission must be an object'],'reviewer_identity_authenticated':False,'human_review_registered':False,'checked_count':0,'independent_review':'pending','scientific_gate':'HOLD'}
    if submitted.get('version')!=VERSION:issues.append('version mismatch')
    if not isinstance(reviewer,dict):reviewer={};issues.append('reviewer object missing')
    if type(reviewer.get('name')) is not str or not reviewer['name'].strip():issues.append('reviewer name missing')
    if reviewer.get('declares_human') is not True:issues.append('human declaration missing')
    if reviewer.get('declares_personally_checked') is not True:issues.append('personal-check declaration missing')
    commit=reviewer.get('reviewed_git_commit')
    if type(commit) is not str or re.fullmatch('[0-9a-fA-F]{40}',commit) is None:issues.append('reviewed commit must be a full SHA; format check is not commit resolution')
    if submitted.get('overall_technical_verdict') not in ('pass','change','reject'):issues.append('technical verdict missing')
    entries=submitted.get('case_reviews');entries=entries if isinstance(entries,list) else []
    seen=set();checked=[]
    for row in entries:
        if not isinstance(row,dict):issues.append('non-object case');continue
        key=row.get('case_id')
        if type(key) is not str or key not in reg['cases']:issues.append('unknown case id');continue
        if key in seen:issues.append('duplicate case id: '+key);continue
        seen.add(key)
        if row.get('snapshot_sha256')!=reg['cases'][key]['snapshot_sha256']:issues.append('stale/tampered case: '+key);continue
        if row.get('checked') is not True:continue
        if row.get('verdict') not in ('pass','change','reject'):issues.append('case verdict missing: '+key);continue
        if type(row.get('comments')) is not str:issues.append('case comments must be text: '+key);continue
        checked.append(key)
    if not checked:issues.append('no personally checked cases')
    return {'status':'invalid' if issues else 'scope_validated_identity_unverified','issues':issues,
            'checked_case_ids':checked,'checked_count':len(checked),'total_scope_cases':len(reg['cases']),
            'remaining_case_ids':[k for k in reg['cases'] if k not in checked],
            'reviewer_identity_authenticated':False,'human_review_registered':False,
            'reviewed_commit_resolved':False,'next_step':'Combine scope checks with trusted identity/personal-review confirmation and inspect findings before recording acceptance. Reuse prior trusted confirmation when applicable; ask only for missing evidence.',
            'independent_review':'pending','scientific_gate':'HOLD'}

def verify():
    reg=json.loads(REGISTRY.read_text(encoding='utf-8'));require(same(reg,registry()),'review registry source/case hashes')
    require(same(json.loads(TEMPLATE.read_text(encoding='utf-8')),template(reg)),'blank review template')
    require(validate_submission(template(reg),reg)['status']=='invalid','unsigned template cannot count as review')
    return {'status':'verified','scope_cases':len(reg['cases']),'independent_review':'pending','scientific_gate':'HOLD'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');p.add_argument('--validate-submission',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.freeze and not any((a.validate_submission,a.output)):
        reg=registry();write_json(REGISTRY,reg);write_json(TEMPLATE,template(reg));print(json.dumps(verify()))
    elif a.validate_submission and a.output and not a.freeze:
        verify();reg=json.loads(REGISTRY.read_text(encoding='utf-8'));sub=json.loads(a.validate_submission.read_text(encoding='utf-8'))
        result=validate_submission(sub,reg);result['submission_sha256']=sha(a.validate_submission);write_json(a.output,result);print(json.dumps(result,ensure_ascii=False))
    elif not any((a.freeze,a.validate_submission,a.output)):print(json.dumps(verify()))
    else:p.error('choose freeze, verify, or validate-submission/output')
