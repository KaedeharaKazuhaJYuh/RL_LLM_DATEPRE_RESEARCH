"""Actual provider cost and paired-state descriptive analysis."""
import argparse
import json
from pathlib import Path
from . import VERSION
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

SOURCE=REPO/'faultda_bench/reports/state_v30_deepseek.json'
OUTPUT=REPO/'faultda_bench/reports/state_v30_accounting.json'


def accounting():
    data=json.loads(SOURCE.read_text(encoding='utf-8')); requests=data['requests']
    def cost(indices):
        qs=[requests[i] for i in indices if requests[i]['receipt']['request_sent']]
        us=[q['receipt'].get('response',{}).get('usage',{}) for q in qs]
        us=[u for u in us if all(type(u.get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
        return {'requests':len(qs),'usage_available':len(us),'prompt_tokens':sum(u['prompt_tokens'] for u in us),
                'completion_tokens':sum(u['completion_tokens'] for u in us),
                'serialized_sent_request_bytes':sum(len(json.dumps(q['body'],ensure_ascii=False,allow_nan=False).encode()) for q in qs)}
    generation_indices=[r['request_index'] for r in data['record_generations']]
    arms={}
    for arm in data['protocol']['arms']:
        rows=[r for r in data['rows'] if r['arm']==arm]; action_indices=[i for r in rows for i in r['request_indices']]
        arms[arm]={'action_cost':cost(action_indices),'standalone_pipeline_cost':cost(action_indices+(generation_indices)),
                   'terminals':{label:sum(r['evaluation']['terminal']==value for r in rows) for label,value in (('stop','stop'),('escalate','escalate'),('budget_exceeded','budget_exceeded'),('nonterminal',None))},
                   'safe_complete':sum(r['evaluation']['safe_complete'] for r in rows),
                   'final_report_correct':sum(r['evaluation']['terminal_correct'] for r in rows),
                   'agent_commit_events':sum(sum(e['actor']=='agent' for e in r['evaluation']['private_effects']) for r in rows),
                   'episodes_with_multiple_agent_commits':sum(sum(e['actor']=='agent' for e in r['evaluation']['private_effects'])>1 for r in rows)}
    pairs=[]
    for state in range(8):
        rs={r['arm']:r for r in data['rows'] if r['state']==state}
        require(set(rs)==set(data['protocol']['arms']),'paired coverage')
        pairs.append({'state':state,**data['protocol']['states'][state],
                      'record_fully_correct':all(v is True for v in data['record_generations'][state]['score'].values()),
                      'arms':{a:{'safe_complete':r['evaluation']['safe_complete'],'safe_escalation':r['evaluation']['safe_escalation'],
                                 'wrong_publications':r['evaluation']['agent_wrong_publications'],'terminal':r['evaluation']['terminal'],
                                 'actions':[v['decision']['action'] if v['category']=='valid_action' else v['category'] for v in r['classifications']]}
                              for a,r in rs.items()}})
    return {'version':VERSION,'source_sha256':sha(SOURCE),'analysis_sha256':sha(Path(__file__)),
            'record_generation_cost':cost(generation_indices),'by_arm':arms,'matched_states':pairs,
            'scientific_gate':'HOLD','independent_review':'pending','independent_task_clusters':1,
            'inference_tests':None,'currency_cost_computed':False}


def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')),accounting()),'actual cost accounting')
    return {'status':'verified','matched_states':8}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args()
    if a.freeze:write_json(OUTPUT,accounting())
    print(json.dumps(verify()))
