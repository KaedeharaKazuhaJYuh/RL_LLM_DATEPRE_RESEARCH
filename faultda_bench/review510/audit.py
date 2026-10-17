"""Offline qualification; independent review and scientific admission remain pending."""
import argparse
import json
from pathlib import Path
from . import VERSION, metrics, review
from ..review505.audit import audit as previous
from ..review505.intake import REPO, sha
from ..acceptance.audit import pinned_path

CATALOG = REPO/'faultda_bench/protocols/acceptance_v39.json'


def check_inventory(root=REPO, catalog_path=CATALOG):
    root = Path(root); catalog = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v38.json').read_text(encoding='utf-8'))
    if catalog['version'] != VERSION or catalog['scientific_gate'] != 'HOLD': raise ValueError('scope')
    if not all(catalog['files'].get(n) == h for n,h in old['files'].items()): raise ValueError('historical preservation')
    for n,h in catalog['files'].items():
        if sha(pinned_path(root,n)) != h: raise ValueError('changed evidence '+n)
    return {'files_verified':len(catalog['files']), 'catalog_sha256':sha(catalog_path)}


def verify():
    packet = json.loads(review.PACKET.read_text(encoding='utf-8'))
    if packet != review.packet(): raise ValueError('review packet source binding')
    template = json.loads(review.TEMPLATE.read_text(encoding='utf-8'))
    if template != review.template(packet): raise ValueError('unsigned review template')
    if review.validate(template,packet)['status'] != 'invalid': raise ValueError('unsigned return cannot pass')
    stored = json.loads((review.FOLDER/'metrics_qualification.json').read_text(encoding='utf-8'))
    if stored != metrics.frozen_controls(): raise ValueError('metric qualification replay')
    decision = json.loads((review.FOLDER/'go_no_go.json').read_text(encoding='utf-8'))
    if decision != {'version':VERSION, 'decision':'NO_GO_LIVE', 'scientific_gate':'HOLD',
                    'approved_transport_requests':0, 'independent_new_design_review':'pending',
                    'final_referent_adjudication':'pending', 'new_sources_collected':0,
                    'new_model_experiments':0, 'packet_sha256':sha(review.PACKET),
                    'metrics_sha256':sha(review.FOLDER/'metrics_qualification.json')}:
        raise ValueError('no-go scope and bindings')
    return {'status':'verified','referent_pairs':12,'design_questions':4,
            'scripted_metric_controls':72,'independent_task_clusters':1,
            'new_provider_requests':0,'scientific_gate':'HOLD','independent_review':'pending'}


def audit():
    inventory=check_inventory(); result=previous()
    result['previous_release_version']=result['version']; result['version']=VERSION
    result['checks']['review_v41']=verify(); result['new_experiment_review']['review_v41']='pending'
    result.update(inventory); return result


if __name__ == '__main__':
    cli=argparse.ArgumentParser(); cli.add_argument('--output',type=Path); a=cli.parse_args(); result=audit()
    if a.output:
        from ..clarity.tasks import write_json
        write_json(a.output,result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
