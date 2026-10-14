"""Per-arm cost and matched one-step evidence attribution."""
import argparse
import json
from pathlib import Path
from . import VERSION
from ..semantic.tasks import REPO,sha
from ..clarity.tasks import write_json
from ..multistep.suite import require,same
SOURCE=REPO/'faultda_bench/reports/goal_v32_deepseek.json'
OUTPUT=REPO/'faultda_bench/reports/goal_v32_accounting.json'
def accounting():
    r=json.loads(SOURCE.read_text(encoding='utf-8'));arms={}
    for arm in r['protocol']['arms']:
        rows=[x for x in r['rows'] if x['arm']==arm]
        qs=[r['requests'][x['request_index']] for x in rows]
        sent=[q for q in qs if q['receipt']['request_sent']]
        us=[q['receipt'].get('response',{}).get('usage',{}) for q in sent]
        us=[u for u in us if all(type(u.get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
        arms[arm]={'requests':len(sent),'prompt_tokens':sum(u['prompt_tokens'] for u in us),
                   'completion_tokens':sum(u['completion_tokens'] for u in us),
                   'serialized_sent_request_bytes':sum(len(json.dumps(q['body'],ensure_ascii=False,allow_nan=False).encode()) for q in sent),
                   'incremental_tool_cost':{k:sum(x['evaluation']['cost'][k]-x['pre_evaluation']['cost'][k] for x in rows) for k in ('checks','mutations','decisions','response_bytes')},
                   'diagnosis_stage_counts':{
                       'valid':sum(x['classification']['category']=='valid_action' and x['diagnostic_score'] is not None for x in rows),
                       'ready_four_facts_correct':sum(x['private_public_fact_reference']['task_complete'] and x['classification']['category']=='valid_action' and x['diagnostic_score'] is not None and all(x['diagnostic_score'][k] for k in ('reference_total','active_content_known','active_total','historical_publication_risk')) for x in rows),
                       'ready_four_facts_correct_but_completion_false':sum(x['private_public_fact_reference']['task_complete'] and x['classification']['category']=='valid_action' and x['diagnostic_score'] is not None and all(x['diagnostic_score'][k] for k in ('reference_total','active_content_known','active_total','historical_publication_risk')) and x['diagnostic_response']['task_complete'] is False for x in rows),
                       'claims_complete_but_decision_not_stop':sum(x['classification']['category']=='valid_action' and x['diagnostic_response'] is not None and x['diagnostic_response'].get('task_complete') is True and x['classification']['decision']['action']!='stop' for x in rows)},
                   'new_wrong_publications_from_model_decision':sum(x['evaluation']['agent_wrong_publications']-x['pre_evaluation']['agent_wrong_publications'] for x in rows),
                   'new_duplicate_events_from_model_decision':sum(x['evaluation']['duplicate_events']-x['pre_evaluation']['duplicate_events'] for x in rows)}
    pairs=[]
    for i,cell in enumerate(r['protocol']['states']):
        rows=[x for x in r['rows'] if x['state']==i]
        pairs.append({**cell,'state':i,'evidence_supported_stop':rows[0]['private_public_fact_reference']['task_complete'],
                      'arms':{x['arm']:{'decision':x['classification'].get('decision'),'category':x['classification']['category'],
                                       'safe_complete':x['evaluation']['safe_complete'],'terminal_correct':x['evaluation']['terminal_correct'],'diagnostic_score':x['diagnostic_score'],'diagnostic_response':x['diagnostic_response']} for x in rows}})
    return {'version':VERSION,'source_sha256':sha(SOURCE),'analysis_sha256':sha(Path(__file__)),
            'by_arm':arms,'matched_states':pairs,'scientific_gate':'HOLD','independent_review':'pending',
            'scope':'Factorial goal clarification and diagnostic output; one next decision per snapshot. Setup effects were injected by the runner; only incremental effects are attributable to the model action. Same snapshot budgets, actual costs reported. No complete recovery or inference test.'}
def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')),accounting()),'per-arm accounting and attribution')
    return {'status':'verified','matched_states':20}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args()
    if a.freeze:write_json(OUTPUT,accounting())
    print(json.dumps(verify()))
