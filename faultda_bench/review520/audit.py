"""Append current registration/interface/routing checks to immutable old audits."""
import argparse
import json
from pathlib import Path
from . import VERSION, registration, suite
from ..review515.audit import audit as previous
from ..review515.intake import REPO, sha
from ..acceptance.audit import pinned_path
from ..clarity.tasks import write_json

CATALOG = REPO / 'faultda_bench/protocols/acceptance_v41.json'
FOLDER = registration.FOLDER
LITERATURE = REPO / 'faultda_bench/docs/R_COMPARISON_0520.md'
INTERFACE = REPO / 'faultda_bench/docs/ACTOR_0520_PROTOCOL.md'


def decision():
    return {'version': VERSION, 'date': '2026-10-19',
            'mechanism_route': 'NO_GO_CURRENT_R_INCREMENT_NOT_ESTABLISHED',
            'engineering_route': 'retain_engineering_diagnostic_benchmark',
            'decision_origin': 'internal_project_routing_not_independent_scientific_acceptance',
            'R_scope': 'capability_diagnostic_question_only_no_observed_gap_or_new_mechanism',
            'W4_main_experiment': 'remains_rejected_design',
            'final_referent_adjudication': 'registered_existing_12_with_objections',
            'new_actor_interface_independent_review': 'pending',
            'new_design_scientific_review': 'pending', 'unseen_tasks_prepared': False,
            'new_sources_collected': 0, 'new_model_tool_executions': 0,
            'new_provider_requests': 0, 'new_training_runs': 0,
            'scientific_gate': 'HOLD', 'decision': 'NO_GO_LIVE',
            'approved_transport_requests': 0,
            'evidence_bindings': {p.relative_to(REPO).as_posix(): sha(p) for p in (
                registration.CONSENT, registration.REGISTRATION, LITERATURE, INTERFACE,
                FOLDER/'actor_views.json')}}


def check_inventory(root=REPO, catalog_path=CATALOG):
    root = Path(root); current = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v40.json').read_text(encoding='utf-8'))
    if current['version'] != VERSION or current['scientific_gate'] != 'HOLD':
        raise ValueError('current scope')
    if not all(current['files'].get(n) == h for n, h in old['files'].items()):
        raise ValueError('old catalog preservation')
    for n, h in current['files'].items():
        if sha(pinned_path(root, n)) != h: raise ValueError('changed frozen evidence: '+n)
    return {'files_verified': len(current['files']), 'catalog_sha256': sha(catalog_path)}


def verify():
    human = registration.verify()
    if json.loads((FOLDER/'actor_views.json').read_text(encoding='utf-8')) != suite.build():
        raise ValueError('explicit actor interface qualification changed')
    if json.loads((FOLDER/'go_no_go.json').read_text(encoding='utf-8')) != decision():
        raise ValueError('research routing/bindings changed')
    return {'status': 'verified', 'final_referent_registration': human,
            'scripted_derived_views': 72, 'new_model_tool_executions': 0,
            'human_interface_validity': 'pending', 'mechanism_route': 'NO_GO_CURRENT_R',
            'new_provider_requests': 0, 'scientific_gate': 'HOLD'}


def audit():
    inventory = check_inventory(); current = verify(); result = previous()
    result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['review_v43'] = current
    result['current_referent_registration'] = registration.verify()
    result['final_referent_adjudication'] = 'registered_existing_12_with_objections'
    result['human_review']['referent_0520'] = registration.verify()
    result['new_experiment_review']['review_v43'] = 'pending_new_interface_and_routing'
    result['current_mechanism_route'] = 'NO_GO_CURRENT_R_INCREMENT_NOT_ESTABLISHED'
    result['scientific_gate'] = 'HOLD'; result['approved_transport_requests'] = 0
    result.update(inventory)
    return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--output', type=Path); args = cli.parse_args()
    result = audit()
    if args.output: write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
