"""Paired offline checks; never rerun, repair or rescore model actions."""
import copy, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from . import VERSION
from .core import check
from ..semantic.tasks import REPO, sha
from ..rowdiag.suite import decoded
from ..multistep.suite import require, same
from ..clarity.tasks import write_json

SOURCE=REPO/'faultda_bench/reports/semantics_v22_deepseek.jsonl'
PLAN=REPO/'faultda_bench/reports/semantics_v22_plan.json'
OUTPUT=REPO/'faultda_bench/reports/consistency_v23_results.json'

def run():
    plan=json.loads(PLAN.read_text()); traces=[json.loads(x) for x in SOURCE.read_text().splitlines()]
    rows=[]
    for index,r in enumerate(traces):
        if r['kind']!='diagnostic' or r['form']!='normalized': continue
        task=plan['views'][r['view']]; version=task['contract']['version'] if 'version' in task['contract'] else 'v1'
        public={'version':version,'start':task['contract']['start'],'end':task['contract']['end'],'rows':task['versions'][version]}
        answer=decoded(r['request']['receipt'])
        rows.append({'source_index':index,'view':r['view'],'repeat':r['repeat'],'internal':check(answer),'bound':check(answer,public),'frozen_score':r['score']})
    # Construct public-evidence adversarial controls from a correct historical record.
    sample=next(r for r in traces if r['kind']=='diagnostic' and r['form']=='normalized' and r['view']=='utc_end')
    correct=decoded(sample['request']['receipt']); task=plan['views']['utc_end']
    public={'version':correct['version'],'start':task['contract']['start'],'end':task['contract']['end'],'rows':task['versions'][correct['version']]}
    shifted=copy.deepcopy(correct)
    for k in ('start_utc','end_utc'): shifted[k]=(datetime.fromisoformat(shifted[k])+timedelta(days=1)).isoformat()
    for r in shifted['rows']: r['time_utc']=(datetime.fromisoformat(r['time_utc'])+timedelta(days=1)).isoformat()
    forged=copy.deepcopy(correct); selected=next(r for r in forged['rows'] if r['included'] and r['value'] is not None)
    selected['value']=float(selected['value'])+10; forged['total']=float(forged['total'])+10
    duplicate=copy.deepcopy(correct); duplicate['rows'].append(copy.deepcopy(duplicate['rows'][0]))
    bad_flag=copy.deepcopy(correct); bad_flag['rows'][0]['lt_end']='false'
    controls=[]
    for name,record,want_internal,want_bound in [('correct',correct,True,True),('shift_all_instants',shifted,True,False),('forge_value_and_sum',forged,True,False),('duplicate_id',duplicate,False,False),('string_boolean',bad_flag,False,False),('missing_record',None,False,False)]:
        a,b=check(record),check(record,public)
        require(a['pass']==want_internal and b['pass']==want_bound,'control '+name)
        controls.append({'name':name,'record':record,'internal':a,'bound':b})
    files=['faultda_bench/consistency310/'+n for n in ('__init__.py','core.py','suite.py')]
    return {'version':VERSION,'source_sha256':sha(SOURCE),'plan_sha256':sha(PLAN),'code_sha256':{n:sha(REPO/n) for n in files},'rows':rows,'controls':controls,'summary':{'historical_records':len(rows),'internal_rejected':sum(not r['internal']['pass'] for r in rows),'bound_rejected':sum(not r['bound']['pass'] for r in rows),'controls':len(controls),'new_api_calls':0,'model_improvement_established':False,'scientific_gate':'HOLD','new_human_review':False}}

def verify():
    require(same(json.loads(OUTPUT.read_text()),run()),'paired checks reproducibility')
    return {'status':'verified','version':VERSION,**run()['summary']}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--freeze',action='store_true'); a=p.parse_args()
    if a.freeze: write_json(OUTPUT,run())
    print(json.dumps(verify(),ensure_ascii=False))
