"""Actual minimal-live costs and same-permission terminal evidence accounting."""
import argparse
import json
from . import VERSION
from ..semantic.tasks import REPO,sha
from ..clarity.tasks import write_json
from ..multistep.suite import require,same
SOURCE=REPO/'faultda_bench/reports/receipt_v35_deepseek.json'
OUTPUT=REPO/'faultda_bench/reports/receipt_v35_accounting.json'
def accounting():
    r=json.loads(SOURCE.read_text(encoding='utf-8'));rows=[]
    for x in r['rows']:
        qs=[r['requests'][s['request_index']] for s in x['decisions']];sent=[q for q in qs if q['receipt']['request_sent']]
        us=[q['receipt'].get('response',{}).get('usage',{}) for q in sent]
        us=[u for u in us if all(type(u.get(k)) is int for k in ('prompt_tokens','completion_tokens'))]
        rows.append({'state':x['state'],'view':x['view'],'mode':x['mode'],
                     'actions':[(s['classification'].get('decision') or {}).get('action',s['classification']['category']) for s in x['decisions']],
                     'requests':len(sent),'prompt_tokens':sum(u['prompt_tokens'] for u in us),'completion_tokens':sum(u['completion_tokens'] for u in us),
                     'sent_request_bytes':sum(q['serialized_request_bytes'] for q in sent),
                     'grade':x['grade'],'end_kind':x['end_kind'],'incremental_tool_cost':x['incremental_cost']})
    return {'version':VERSION,'source_sha256':sha(SOURCE),'analysis_sha256':sha(__file__),
            'summary':r['summary'],'rows':rows,'independent_review':'pending','scientific_gate':'HOLD',
            'currency_cost_computed':False,'scope':'Four model trajectories, one task cluster. Strong public-rule baseline and same permissions; no RL training, significance or generalization claim.'}
def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')),accounting()),'actual receipt model cost/grade accounting')
    return {'status':'verified','model_trajectories':4}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args()
    if a.freeze:write_json(OUTPUT,accounting())
    print(json.dumps(verify()))
