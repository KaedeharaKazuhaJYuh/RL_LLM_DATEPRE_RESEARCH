"""Add current scoped review intake while preserving all historical audit results."""
import argparse
import json
from pathlib import Path
from . import VERSION, intake, design
from ..validity500.audit import audit as previous
from ..acceptance.audit import pinned_path, digest

CATALOG = intake.REPO/'faultda_bench/protocols/acceptance_v38.json'


def check_inventory(root=intake.REPO, catalog_path=CATALOG):
    root = Path(root)
    current = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v37.json').read_text(encoding='utf-8'))
    if current['version'] != VERSION or current['scientific_gate'] != 'HOLD':
        raise ValueError('Current scope')
    if not all(current['files'].get(n) == h for n, h in old['files'].items()):
        raise ValueError('Historical freeze changed')
    for name, sha in current['files'].items():
        path = pinned_path(root, name)
        if not path.is_file() or digest(path.read_bytes()) != sha:
            raise ValueError('Changed evidence: '+name)
    return {'files_verified': len(current['files']), 'catalog_sha256': digest(Path(catalog_path).read_bytes())}


def audit():
    inventory = check_inventory()
    result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['review_v40_intake'] = intake.verify()
    result['checks']['review_v40_design'] = design.verify()
    decision = json.loads((intake.SOURCE.parent/'go_no_go.json').read_text(encoding='utf-8'))
    if (decision['decision'] != 'NO_GO_LIVE' or decision['approved_transport_requests'] != 0 or
            decision['scientific_gate'] != 'HOLD' or decision['new_design_independent_review'] != 'pending' or
            decision['review_intake_sha256'] != intake.sha(intake.RECEIPT) or
            decision['source_design_sha256'] != intake.sha(design.OUTPUT) or
            decision['cross_task_plan_sha256'] != intake.sha(design.PLAN)):
        raise ValueError('Current no-go decision and evidence bindings')
    result['checks']['review_v40_decision'] = {'decision': 'NO_GO_LIVE', 'approved_transport_requests': 0}
    result['human_review']['validity_v39'] = {'status': 'accepted_technical_37_groups_only',
            'reviewer': '张雨田', 'source_sha256': intake.sha(intake.SOURCE),
            'reviewer_identity_authenticated': False, 'basis': 'Supplied human Markdown plus direct user assertion'}
    result['new_experiment_review']['validity_v39'] = 'accepted_technical_37_groups_only'
    result['new_experiment_review']['review_v40'] = 'pending'
    result['final_referent_adjudication'] = 'not_performed'
    result['scientific_gate'] = 'HOLD'; result['approved_transport_requests'] = 0
    result.update(inventory)
    return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--output', type=Path); args = cli.parse_args()
    data = audit()
    if args.output:
        from ..clarity.tasks import write_json
        write_json(args.output, data)
    print(json.dumps(data, ensure_ascii=False, indent=2))
