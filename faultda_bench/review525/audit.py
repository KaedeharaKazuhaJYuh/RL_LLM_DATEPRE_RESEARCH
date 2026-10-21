"""Bounded offline public-input preflight; no new research admission."""
import argparse
import json
from pathlib import Path
from . import VERSION, preflight
from ..review520.audit import audit as previous
from ..coherent395 import suite
from ..review515.intake import REPO, sha
from ..acceptance.audit import pinned_path
from ..clarity.tasks import write_json

FOLDER = REPO/'faultda_bench/reports/review525'
CATALOG = REPO/'faultda_bench/protocols/acceptance_v42.json'


def qualification():
    source = json.loads(suite.OUTPUT.read_text(encoding='utf-8')); rows = []
    for r in source['rows']:
        obs = r['public_observation']; before = preflight.digest(obs)
        binding = preflight.resolve(obs, 'history:'+str(len(obs['history'])-1))
        # The reference is consulted only AFTER the public-only function returns.
        # It is not a function argument or a new scored model response.
        if binding['target_publish_event_id'] != r['expected_receipt_facts']['receipt_event_id']:
            raise ValueError('public-derived target disagrees with old reference')
        if before != preflight.digest(obs): raise ValueError('observation mutated')
        rows.append({'source_observation_sha256': before, 'public_binding': binding,
                     'old_reference_match': True})
    return {'version': VERSION, 'source_sha256': sha(suite.OUTPUT), 'rows': rows,
            'publicly_resolved_old_views': len(rows), 'independent_task_clusters': 1,
            'model_responses_rescored': 0, 'new_model_tool_executions': 0,
            'new_physical_executions': 0, 'new_provider_requests': 0,
            'comparison_plans_admitted': 0, 'actual_cost_equality_measured': False,
            'scope': 'Old post-read scripted snapshots only; not fresh initial trials, model improvement or a scientific test. Setup matching is exercised by synthetic unit fixtures, not an admitted experiment.',
            'scientific_gate': 'HOLD', 'approved_transport_requests': 0}


def check_inventory(root=REPO, catalog_path=CATALOG):
    root = Path(root); c = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    old = json.loads((root/'faultda_bench/protocols/acceptance_v41.json').read_text(encoding='utf-8'))
    if c['version'] != VERSION or c['scientific_gate'] != 'HOLD': raise ValueError('scope')
    if not all(c['files'].get(n) == h for n,h in old['files'].items()): raise ValueError('old freeze changed')
    for n,h in c['files'].items():
        if sha(pinned_path(root,n)) != h: raise ValueError('changed frozen evidence '+n)
    return {'files_verified': len(c['files']), 'catalog_sha256': sha(catalog_path)}


def audit():
    inventory = check_inventory()
    if json.loads((FOLDER/'qualification.json').read_text(encoding='utf-8')) != qualification():
        raise ValueError('public resolution qualification changed')
    result = previous(); result['previous_release_version'] = result['version']; result['version'] = VERSION
    result['checks']['review_v44'] = {'status': 'verified', 'publicly_resolved_old_views': 72,
            'setup_execution_authenticated': False, 'new_comparison_plan_admitted': False,
            'actual_cost_equality_measured': False, 'new_provider_requests': 0}
    result['new_experiment_review']['review_v44'] = 'pending_new_public_resolver_and_comparison_contract'
    result['scientific_gate'] = 'HOLD'; result['approved_transport_requests'] = 0
    result.update(inventory)
    return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser(); cli.add_argument('--output',type=Path); args = cli.parse_args()
    r = audit()
    if args.output: write_json(args.output,r)
    print(json.dumps(r,ensure_ascii=False,indent=2))
