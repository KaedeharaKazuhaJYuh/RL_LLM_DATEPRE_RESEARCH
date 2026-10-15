"""Descriptive accounting, not causal attribution or cross-protocol improvement."""
import argparse
import json
from decimal import Decimal
from . import VERSION
from . import suite as s
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

OUTPUT = s.REPO/'faultda_bench/reports/postreceipt_v36_accounting.json'


def accounting():
    r = json.loads(s.LIVE.read_text(encoding='utf-8')); rows = []
    for case,row,q in zip(s.snapshots(),r['rows'],r['requests']):
        v = s.decoded(q['receipt']); obs = case['observation']; ref = s.numeric_reference(obs)
        ids = v.get('selected_row_ids',[]) if isinstance(v,dict) else []
        values = {x['id']:x['value'] for x in ref['rows']}
        actual_sum = sum((s.number(values[k]) for k in ids),Decimal(0)) if len(set(ids)) == len(ids) and all(k in values for k in ids) else None
        rows.append({'case_id':case['case_id'],'source_request_index':case['source_request_index'],
                     'original_terminal':s.decoded(case['source_terminal_response'])['action'],
                     'diagnostic_reported_facts':v,'grade':row['grade'],
                     'missing_required_ids':sorted(set(ref['selected_row_ids'])-set(ids)),
                     'extra_selected_ids':sorted(set(ids)-set(ref['selected_row_ids'])),
                     'sum_of_reported_rows':None if actual_sum is None else str(actual_sum),
                     'expected_total':ref['reference_total']})
    return {'version':VERSION,'source_sha256':s.sha(s.LIVE),'analysis_sha256':s.sha(__file__),
            'summary':r['summary'],'rows':rows,'scripted_reference_all_fields_correct':4,
            'scripted_reference_provider_requests':0,
            'limit':'Original action and new diagnostic use different prompts/outcome definitions. Never compare 3/4 and 0/4 as capability change. Row ids and arithmetic here are reported outputs, not internal reasoning. Fixed program reference is a reference checker, not a new learned baseline.',
            'independent_review':'pending','scientific_gate':'HOLD'}


def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')),accounting()),'diagnostic row and cost accounting')
    return {'status':'verified','snapshots':4}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze',action='store_true'); a = p.parse_args()
    if a.freeze:write_json(OUTPUT,accounting())
    print(json.dumps(verify()))
