"""Offline audit of pinned evidence and explicitly scoped human review."""
import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from . import VERSION

REPO = Path(__file__).resolve().parents[2]
CATALOG = REPO / 'faultda_bench/protocols/acceptance_v11.json'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pinned_path(root, relative):
    require(isinstance(relative, str), 'path must be a string')
    path = Path(relative)
    require(not path.is_absolute() and '..' not in path.parts and '\\' not in relative,
            'invalid relative path')
    target = (root / path).resolve()
    require(target.is_relative_to(root.resolve()), 'path escapes repository')
    return target


def check_inventory(root=REPO, catalog_path=CATALOG):
    """The committed catalog is the trust anchor; never rewrite it during audit."""
    root = Path(root)
    catalog = json.loads(Path(catalog_path).read_text(encoding='utf-8'))
    require(catalog['version'] in ('0.2.25-dev', '0.2.30-dev', '0.2.35-dev', '0.2.50-dev', '0.2.55-dev', VERSION), 'catalog version')
    require(catalog['scientific_gate'] == 'HOLD', 'scientific gate is not a test result')
    files = catalog['files']
    require(isinstance(files, dict) and len(files) > 30, 'incomplete inventory')
    for relative, checksum in files.items():
        target = pinned_path(root, relative)
        require(target.is_file(), 'missing evidence: ' + relative)
        require(digest(target.read_bytes()) == checksum, 'changed evidence: ' + relative)
    receipt_path = 'faultda_bench/reports/human_review_round2_2026_10_11/receipt.json'
    archive_path = receipt_path.replace('receipt.json', 'submitted_records.zip')
    require(receipt_path in files and archive_path in files, 'human provenance missing')
    receipt = json.loads(pinned_path(root, receipt_path).read_text(encoding='utf-8'))
    require(type(receipt['human_tasks_passed']) is int and receipt['human_tasks_passed'] == 24,
            'human task scope')
    require(receipt['new_regression_fixtures_human_reviewed'] is False,
            'old review cannot approve new fixtures')
    require(receipt['boundary_scripts_supplied_in_this_round'] is False,
            'declared checks must not become independently replayed checks')
    require(receipt['scientific_recommendation'].startswith('HOLD;'), 'review recommendation')
    with zipfile.ZipFile(pinned_path(root, archive_path)) as archive:
        for record in receipt['received_files']:
            data = archive.read(record['name'])
            require(digest(data) == record['sha256'] and len(data) == record['bytes'],
                    'original human review mismatch')
    regression_review = {'status': 'pending', 'cases': 6}
    if catalog['version'] != '0.2.25-dev':
        review_base = 'faultda_bench/reports/regression_review_2026_10_11/'
        require(all(review_base + n in files for n in ('receipt.json', 'submitted_review.md')),
                'new review provenance missing')
        new_receipt = json.loads(pinned_path(root, review_base + 'receipt.json').read_text(encoding='utf-8'))
        original = pinned_path(root, review_base + 'submitted_review.md').read_bytes()
        require(digest(original) == new_receipt['submitted_review_sha256']
                and len(original) == new_receipt['submitted_review_bytes'], 'new review original mismatch')
        require(new_receipt['reviewed_version'] == '0.2.20-dev'
                and type(new_receipt['cases_passed']) is int and new_receipt['cases_passed'] == 6,
                'new review scope')
        expected = [[task, reuse] for task in ('group-01', 'window-01', 'version-01') for reuse in (True, False)]
        require(json.dumps(new_receipt['case_keys']) == json.dumps(expected), 'review case coverage')
        require(new_receipt['scientific_gate'] == 'HOLD', 'review cannot lift scientific gate')
        regression_review = {'status': 'passed', 'cases': 6, 'reviewer': new_receipt['reviewer'],
                             'reviewed_version': new_receipt['reviewed_version'],
                             'identity_basis': new_receipt['identity_basis']}
    return {'files_verified': len(files), 'catalog_sha256': digest(Path(catalog_path).read_bytes()),
            'new_experiment_review': {name: 'pending' for name in {
                '0.2.35-dev': ('allocation_v8',),
                '0.2.50-dev': ('allocation_v8', 'surface_v9'),
                '0.2.55-dev': ('allocation_v8', 'surface_v9', 'trust_v10'),
                VERSION: ('allocation_v8', 'surface_v9', 'trust_v10', 'pilot_v11'),
            }.get(catalog['version'], ())},
            'human_review': {'development_tasks': {'status': 'passed', 'tasks': 24},
                             'legacy_diagnostics': {'status': 'passed', 'tasks': 3},
                             'new_regression_cases': regression_review,
                             'identity_basis': 'user-confirmed personal human review',
                             'declared_boundary_checks': 22,
                             'boundary_scripts_independently_replayed': False},
            'scientific_gate': 'HOLD', 'scientific_release_ready': False}


def audit(full_replay=False):
    require(sys.flags.optimize == 0, 'Run without -O: historical verifiers contain assertions')
    inventory = check_inventory()
    # Fixed dispatch only; the catalog cannot select commands or imported code.
    from ..semantic.verify_results import verify as semantic
    from ..clarity.verify import verify as clarity
    from ..evidence.verify import verify as evidence
    from ..decision.verify import verify as decision
    from ..regression.verify import verify as regression
    from ..allocation.verify import verify as allocation
    from ..surface.verify import verify as surface
    from ..trust.verify import verify as trust
    from ..pilot.verify import verify as pilot
    reports = REPO / 'faultda_bench/reports'
    checks = {'semantic_v1': semantic(replay=full_replay)}
    for name in ('cross_source_v2_results', 'clarity_v2_comparison'):
        checks[name] = clarity(reports / (name + '.json'), replay=full_replay)
    for verifier, names in ((evidence, ('evidence_v3_offline', 'evidence_v3_api')),
                            (decision, ('decision_v4_offline', 'decision_v4_api')),
                            (regression, ('regression_v5_results',)),
                            (allocation, ('allocation_v8_results',)),
                            (surface, ('surface_v9_results',)),
                            (trust, ('trust_v10_results',)),
                            (pilot, ('pilot_v11_offline',))):
        for name in names:
            checks[name] = verifier(reports / (name + '.json'))
    return {'version': VERSION, 'machine_status': 'verified', 'api_requests': 0,
            'historical_large_suites_replayed': full_replay, 'checks': checks, **inventory}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--full-replay', action='store_true', help='also replay large v1/v2 suites')
    parser.add_argument('--output', type=Path, help='write new JSON exclusively; never overwrite evidence')
    args = parser.parse_args()
    result = audit(args.full_replay)
    encoded = (json.dumps(result, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    if args.output:
        with args.output.open('xb') as stream:
            stream.write(encoded)
    print(encoded.decode('utf-8'), end='')


if __name__ == '__main__':
    main()
