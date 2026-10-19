"""Verify cumulative bytes and replay the new bounded research analyses."""
import argparse
import hashlib
import json
from pathlib import Path

from . import VERSION
from ..acceptance.audit import pinned_path
from research.binding_probe import run
from research.trajectory_evidence_audit import audit as trajectories
from research.termination_case_analysis import analyze

ROOT = Path(__file__).resolve().parents[2]
CATALOG = 'faultda_bench/protocols/acceptance_v44.json'
OUTPUTS = {
    'research/binding_probe_results_2026_10_19.json': run,
    'research/TRAJECTORY_EVIDENCE_INDEX_2026_10_19.json': trajectories,
    'research/TERMINATION_CASE_ANALYSIS_2026_10_19.json': analyze,
}


def inventory(root=ROOT):
    root = Path(root)
    catalog = json.loads((root / CATALOG).read_text(encoding='utf-8'))
    old = json.loads((root / 'faultda_bench/protocols/acceptance_v43.json').read_text(encoding='utf-8'))
    if catalog['version'] != VERSION or catalog['scientific_gate'] != 'HOLD':
        raise ValueError('release scope changed')
    if not all(catalog['files'].get(n) == h for n, h in old['files'].items()):
        raise ValueError('historical freeze not preserved')
    for name, expected in catalog['files'].items():
        if hashlib.sha256(pinned_path(root, name).read_bytes()).hexdigest() != expected:
            raise ValueError('frozen bytes changed: ' + name)
    return len(catalog['files'])


def audit(historical=False):
    files = inventory()
    for name, generate in OUTPUTS.items():
        if json.loads((ROOT / name).read_text(encoding='utf-8')) != generate():
            raise ValueError('analysis replay mismatch: ' + name)
    plan = json.loads((ROOT / 'faultda_bench/protocols/termination_v46_draft.json').read_text(encoding='utf-8'))
    if (plan['status'] != 'DRAFT_NOT_ADMITTED' or plan['approved_transport_requests'] != 0
            or plan['independent_review'] != 'not_arranged'):
        raise ValueError('draft must not become research or transport approval')
    result = {'version': VERSION, 'status': 'offline_release_verified',
              'files_verified': files, 'analysis_outputs_replayed': len(OUTPUTS),
              'stored_historical_requests_indexed': 247, 'new_provider_requests': 0,
              'scientific_gate': 'HOLD', 'mechanism_go': False,
              'human_review': 'not_arranged', 'draft_admitted': False,
              'historical_semantic_audit_replayed': historical}
    if historical:
        from ..review530.audit import audit as previous
        result['historical'] = previous()
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--historical', action='store_true')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    result = audit(args.historical)
    text = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
    print(text)
