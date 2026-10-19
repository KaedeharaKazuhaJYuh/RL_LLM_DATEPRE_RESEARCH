"""Strict public-packet qualification appended to the frozen historical audit."""
import argparse
import json
from pathlib import Path
from . import VERSION, envelope
from ..review525 import preflight
from ..review525.audit import audit as previous
from ..coherent395 import suite
from ..review515.intake import REPO, sha
from ..acceptance.audit import pinned_path
from ..clarity.tasks import write_json

FOLDER = REPO/'faultda_bench/reports/review530'
CATALOG = REPO/'faultda_bench/protocols/acceptance_v43.json'


def qualification():
    source=json.loads(suite.OUTPUT.read_text(encoding='utf-8'));cases=[];rows=[]
    for i,r in enumerate(source['rows']):
        c={'case_id':f'binding-witness-{i:03d}','public_observation':r['public_observation'],
           'query_event_id':'history:'+str(len(r['public_observation']['history'])-1)}
        packet=envelope.packet(c)
        if packet['request_binding']['target_publish_event_id'] != r['expected_receipt_facts']['receipt_event_id']:
            raise ValueError('public packet/reference mismatch')
        rows.append({'case_id':c['case_id'],'source_observation_sha256':preflight.digest(c['public_observation']),
                     'effective_input_sha256':preflight.digest(packet),'old_reference_match':True})
        cases.append(c)
    a={'name':'internal-arm-a','public_observation_sha256':{c['case_id']:preflight.digest(c['public_observation']) for c in cases},
       'effective_input_sha256':{c['case_id']:preflight.digest(envelope.packet(c)) for c in cases},
       'allowed_tools':['stop','escalate'],'tool_budgets':dict(checks=0,mutations=0,decisions=1,response_bytes=10000,wall_seconds=10),
       'preprocessing':envelope.helper(),'private_truth_access':False}
    import copy
    b=copy.deepcopy(a);b['name']='internal-arm-b'
    return {'version':VERSION,'source_sha256':sha(suite.OUTPUT),'rows':rows,
            'binding_witness':envelope.check(cases,[a,b]),
            'scope':'72 old post-read scripted snapshots and internal configuration witnesses only; no new model, fresh initial task, eligibility approval or actual cost comparison.',
            'new_provider_requests':0,'new_model_tool_executions':0,'scientific_gate':'HOLD',
            'independent_review':'pending_three_focused_new_items'}


def check_inventory(root=REPO,catalog_path=CATALOG):
    root=Path(root);c=json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old=json.loads((root/'faultda_bench/protocols/acceptance_v42.json').read_text(encoding='utf-8'))
    if c['version']!=VERSION or c['scientific_gate']!='HOLD':raise ValueError('scope')
    if not all(c['files'].get(n)==h for n,h in old['files'].items()):raise ValueError('old freeze changed')
    for n,h in c['files'].items():
        if sha(pinned_path(root,n))!=h:raise ValueError('changed frozen evidence '+n)
    return {'files_verified':len(c['files']),'catalog_sha256':sha(catalog_path)}


def audit():
    inventory=check_inventory()
    if json.loads((FOLDER/'qualification.json').read_text(encoding='utf-8'))!=qualification():
        raise ValueError('strict packet qualification changed')
    result=previous();result['previous_release_version']=result['version'];result['version']=VERSION
    result['checks']['review_v45']={'status':'verified','bound_old_public_views':72,
        'effective_packet_binding_verified':True,'runtime_compliance_verified':False,
        'actual_total_costs_equal':None,'new_comparison_plan_admitted':False,'new_provider_requests':0}
    result['new_experiment_review']['review_v45']='pending_strict_packets_and_focused_human_review'
    result.update(inventory);return result


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--output',type=Path);a=cli.parse_args();r=audit()
    if a.output:write_json(a.output,r)
    print(json.dumps(r,ensure_ascii=False,indent=2))
