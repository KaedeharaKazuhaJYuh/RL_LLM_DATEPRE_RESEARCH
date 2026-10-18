"""Current offline intake/admission audit; preserve historical frozen evidence."""
import argparse
import json
from pathlib import Path
from . import VERSION, intake, lineage
from ..acceptance.audit import pinned_path
from ..review510.audit import audit as previous
from ..clarity.tasks import write_json

REPO = intake.REPO
CATALOG = REPO / 'faultda_bench/protocols/acceptance_v40.json'
FOLDER = intake.FOLDER


def qualification():
    return {'version': VERSION, 'intake': intake.verify(),
            'retrospective_fact_fields': intake.factual_crosscheck(),
            'lineage': lineage.audit(),
            'new_admitted_test_panel': False,
            'metric_scope': 'Prospective common-panel declarations and coverage only; old 72 controls remain retrospective.',
            'new_model_experiments': 0, 'new_provider_requests': 0,
            'new_sources_collected': 0, 'new_training_runs': 0,
            'scientific_gate': 'HOLD', 'approved_transport_requests': 0}


def decision():
    return {'version': VERSION, 'decision': 'NO_GO_LIVE', 'scientific_gate': 'HOLD',
            'reviewed_design_opinions': 'received_four_revise',
            'final_referent_adjudication': 'pending_explicitly_not_final',
            'W4_main_experiment': 'rejected_design_not_statistical_refutation',
            'H_star_operationalization': 'not_qualified_no_live_plan',
            'only_future_question': 'R_actor_receipt_terminal_gap_design_only',
            'new_0515_independent_review': 'pending',
            'novelty_demonstrated': False, 'model_improvement_demonstrated': False,
            'approved_transport_requests': 0, 'new_provider_requests': 0,
            'bindings': {n: intake.sha(REPO/n) for n in (
                'faultda_bench/reports/review515/intake.json',
                'faultda_bench/reports/review515/qualification.json',
                'faultda_bench/docs/REVIEW_0515_PROTOCOL.md')}}


def check_inventory(root=REPO, catalog_path=CATALOG):
    root = Path(root); current = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v39.json').read_text(encoding='utf-8'))
    if current['version'] != VERSION or current['scientific_gate'] != 'HOLD':
        raise ValueError('current catalog scope')
    if not all(current['files'].get(n) == h for n, h in old['files'].items()):
        raise ValueError('historical catalog preservation')
    for n, h in current['files'].items():
        if intake.sha(pinned_path(root, n)) != h:
            raise ValueError('changed frozen evidence: '+n)
    return {'files_verified': len(current['files']), 'catalog_sha256': intake.sha(catalog_path)}


def verify():
    for name, expected in [('qualification.json', qualification()), ('go_no_go.json', decision())]:
        actual = json.loads((FOLDER/name).read_text(encoding='utf-8'))
        if actual != expected:
            raise ValueError('current scope/binding mismatch: '+name)
    return {'status': 'verified', 'received_design_opinions': 4,
            'final_referent_adjudication': 'pending_explicitly_not_final',
            'new_design_independent_review': 'pending',
            'new_admitted_test_panel': False, 'scientific_gate': 'HOLD',
            'new_provider_requests': 0, 'approved_transport_requests': 0}


def audit():
    inventory = check_inventory(); current = verify(); result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['review_v42'] = current
    result['current_review_intake'] = intake.verify()
    result['new_experiment_review']['review_v42'] = 'pending_new_0515_changes'
    result['final_referent_adjudication'] = 'pending_explicitly_not_final'
    result['scientific_gate'] = 'HOLD'; result['approved_transport_requests'] = 0
    result.update(inventory)
    return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--output', type=Path); args = cli.parse_args()
    result = audit()
    if args.output: write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
