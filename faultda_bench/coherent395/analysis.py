"""Descriptive paired evidence and actual provider costs, without capability claims."""
import argparse
import json
from . import VERSION, pilot as p
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

OUTPUT = p.s.REPO/'faultda_bench/reports/coherent_v38_accounting.json'


def accounting():
    live = json.loads(p.LIVE.read_text(encoding='utf-8')); selected = {c['row_id']:c for c in p.cases()}; pairs = []
    for key,c in selected.items():
        rs = [r for r in live['rows'] if r['row_id']==key]
        arms = {}
        for r in rs:
            q = live['requests'][r['request_index']]
            arms[r['arm']] = {'request_index':r['request_index'],'reported_facts':p.decoded(q['receipt']),'grade':r['grade'],'request_bytes':q['serialized_request_bytes']}
        require(len(arms)==2,'complete paired denominator')
        pairs.append({'row_id':key,'window':c['window'],'represented_role':c['role'],'hidden_mode_for_analysis_only':c['mode'],
                      'expected_facts':c['expected_receipt_facts'],'arms':arms})
    return {'version':VERSION,'source_sha256':p.s.sha(p.LIVE),'analysis_sha256':p.s.sha(__file__),'summary':live['summary'],'pairs':pairs,
            'scope':'Paired instruction effect and external fact classifications only. Twelve conditions share one task cluster; conditional role error counts do not identify internal reasoning or causal mediation. No model tool actions, RL or cross-version comparison. No currency cost computed.',
            'independent_review':'pending','scientific_gate':'HOLD'}


def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')),accounting()),'actual paired costs and response accounting')
    return {'status':'verified','paired_conditions':12,'scientific_gate':'HOLD'}


if __name__ == '__main__':
    p_cli = argparse.ArgumentParser(); p_cli.add_argument('--freeze',action='store_true'); args = p_cli.parse_args()
    if args.freeze:write_json(OUTPUT,accounting())
    print(json.dumps(verify()))
