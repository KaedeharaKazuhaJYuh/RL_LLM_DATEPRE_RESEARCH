"""Offline freeze audit for acceptance_v47: v46 preserved plus the 0.5.60 additions.

Verifies that the manifest keeps every v46 byte and adds only finished evidence
and the code that produces or verifies it, and emits the manifest it verifies so
the freeze stays regenerable. Hash verification only; never writes into a frozen
location, never runs a model, never contacts a provider, never rescores.
"""
import argparse
import hashlib
import json
from pathlib import Path

from . import VERSION
from ..acceptance.audit import pinned_path
from ..stats560.core import round_floats

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = 'faultda_bench/protocols/acceptance_v47.json'
BASE_CATALOG = 'faultda_bench/protocols/acceptance_v46.json'
BASE_CATALOG_SHA256 = 'e592b097f2d07a02b66fe9e2551e84d23b5f14b3461bc1dd736b9db1a3b6dcda'
PERFORMANCE = 'faultda_bench/protocols/performance555_v1.json'
ALLOWED_PREFIXES = ('work/',)

# Appended to v46's 660 entries, in this order: the previous manifest first (v46
# led its own additions with v45), then the 0.5.55 performance manifest and its
# optimization files in that manifest's key order, then the 0.5.60 evidence and
# the 0.5.60 version-integrity code. Order is part of the artifact: the manifest
# is committed, so a reordering would show up as a diff with no byte change.
ADDITIONS = (
    'faultda_bench/protocols/acceptance_v46.json',
    'faultda_bench/protocols/performance555_v1.json',
    'faultda_bench/termination555/runtime.py',
    'faultda_bench/termination555/benchmark.py',
    'faultda_bench/termination555/performance_audit.py',
    'tests/test_faultda_termination555_runtime.py',
    'faultda_bench/docs/ARCHITECTURE_ENERGY_0555.md',
    'faultda_bench/reports/PERFORMANCE_0555.md',
    'faultda_bench/reports/termination555_performance/paired_benchmark.json',
    'faultda_bench/reports/termination555_performance/baseline_profile.json',
    'faultda_bench/reports/termination555_performance/optimized_profile.json',
    'faultda_bench/reports/termination555_performance/energy_probe.json',
    'faultda_bench/reports/termination555_performance/validation.json',
    'faultda_bench/protocols/stats560_inputs_v1.json',
    'faultda_bench/stats560/__init__.py',
    'faultda_bench/stats560/core.py',
    'faultda_bench/stats560/audit.py',
    'tests/test_faultda_stats560.py',
    'faultda_bench/docs/UNCERTAINTY_0560.md',
    'faultda_bench/reports/stats560/summary.json',
    'faultda_bench/reports/stats560/summary.md',
    'faultda_bench/reports/RELEASE_0560.md',
    'faultda_bench/reports/RELEASE_0560_VALIDATION.json',
    'faultda_bench/current_evidence/__init__.py',
    'faultda_bench/current_evidence/runner.py',
    'faultda_bench/current_evidence/__main__.py',
    'faultda_bench/release560/__init__.py',
    'faultda_bench/release560/audit.py',
    'tests/test_faultda_current_evidence.py',
    'tests/test_faultda_release560.py',
    'faultda_bench/reports/RELEASE_0560_FREEZE.md',
)

TRUST_BOUNDARY = (
    'Preserve all v46 660 files byte-for-byte and add the 0.5.55 within-version optimization '
    'evidence, the 0.5.60 descriptive-uncertainty evidence and the 0.5.60 version-integrity '
    'code. Hash verification only; no runtime, provider or hidden-world identity attestation; '
    'no new API, model, training or human review.')

FREEZE_RULE = {
    'included': 'A file is frozen when it is finished evidence of a shipped version, or the '
                'code/test that produces or verifies that evidence. Concretely: everything '
                'already frozen in v46; the 0.5.55 within-version performance manifest and its '
                'optimization files; the 0.5.60 stats560 module, input manifest, committed '
                'summary artifacts, release report, validation JSON and uncertainty doc, with '
                'their test file; and the 0.5.60 version-integrity runner, v47 audit, their '
                'test files and the freeze report.',
    'excluded': 'A file is NOT frozen when it records the project\'s current state rather than '
                'a fixed version\'s evidence, and therefore changes by design on every release. '
                'Freezing such a file would make the next release fail this audit.',
    'rationale': 'The freeze exists to prove that evidence did not move after it was reviewed. '
                 'A living document carries no evidence and must stay editable; an acceptance '
                 'manifest that hashed one would convert every future release into a '
                 'self-inflicted audit failure.',
    'self_reference': 'A manifest never hashes itself; acceptance_v47.json is absent from '
                      'files, following v6..v46.',
}

EXCLUDED_LIVING_DOCUMENTS = {
    'README.md': 'Living document: project overview rewritten every release; '
                 '`scripts.release_version --check` requires its heading to track VERSION.',
    'faultda_bench/README.md': 'Living document: benchmark overview rewritten every release.',
    'CHANGELOG.md': 'Living document: gains an entry every release by definition.',
    'docs/PROJECT_HISTORY.md': 'Living document: appended every release.',
    'docs/REPRODUCIBILITY.md': 'Living document: reproduction steps change whenever tooling or '
                               'entry points change.',
    'VERSION': 'Release-state file: the single place the version number is bumped.',
    '.gitattributes': 'Living config: gains a `text eol=lf` line for every new Markdown '
                      'artifact.',
    '.github/workflows/faultda-current.yml': 'Living CI config for the CURRENT version; must '
                                             'stay editable so a new version can add an audit '
                                             'step.',
    'faultda_bench/protocols/current_evidence_v1.json':
        'Living registry: the single source of truth for the current-evidence job, which must '
        'gain test modules and audits every release. Integrity is enforced by '
        'tests/test_faultda_current_evidence.py, not by a hash.',
    'docs/en/FAULTDA_BENCH_OVERVIEW.md':
        'Living document: English mirror of README.md; refreshed whenever README is. It carries '
        'no evidence — the figures it cites live in the frozen stats560 summary artifacts.',
    'faultda_bench/protocols/acceptance_v47.json':
        'A manifest cannot hash itself; v48 will freeze it, exactly as v46 froze v45.',
}


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def verify_files(root, manifest):
    """Hash every listed file; takes a manifest dict so a test can reduce it."""
    root = Path(root)
    for name, expected in manifest['files'].items():
        target = pinned_path(root, name)
        _require(target.is_file(), 'missing frozen evidence: ' + name)
        _require(_sha(target.read_bytes()) == expected, 'frozen bytes changed: ' + name)
    return len(manifest['files'])


def check_scope(manifest, base_bytes, root=ROOT):
    """Assert the freeze is additive: v46 preserved, additions appended in order."""
    _require(manifest['version'] == VERSION, 'freeze version')
    _require(manifest['scientific_gate'] == 'HOLD', 'a byte freeze is not a scientific result')
    _require(manifest['new_experiments'] == [], 'a byte freeze introduces no experiment')
    _require(manifest['new_experiments_human_reviewed'] is False,
             'old human signatures cannot approve new evidence')
    _require(manifest['base_catalog'] == BASE_CATALOG, 'base catalog')
    _require(manifest['base_catalog_sha256'] == BASE_CATALOG_SHA256 == _sha(base_bytes),
             'base catalog differs from the fixed 0.5.55 release')
    base = json.loads(base_bytes)['files']
    _require(manifest['base_catalog_files'] == len(base), 'base catalog file count')
    files = manifest['files']
    _require(all(files.get(name) == checksum for name, checksum in base.items()),
             'v46 freeze not preserved')
    _require(list(files) == list(base) + list(ADDITIONS),
             'files must be the v46 entries in v46 order followed by the additions in order')
    _require(MANIFEST not in files, 'a manifest never hashes itself')
    _require(tuple(manifest['excluded_living_documents']) == tuple(EXCLUDED_LIVING_DOCUMENTS),
             'living document exclusion list changed')
    for name in manifest['excluded_living_documents']:
        _require(pinned_path(root, name).is_file(), 'excluded living document is missing: ' + name)
        _require(name not in files, 'a living document must not be frozen: ' + name)
    return len(ADDITIONS)


def check_inventory(root=ROOT, catalog_path=ROOT / MANIFEST):
    """The committed manifest is the trust anchor; never rewrite it during audit."""
    root = Path(root)
    catalog_bytes = Path(catalog_path).read_bytes()
    manifest = json.loads(catalog_bytes.decode('utf-8'))
    base_bytes = pinned_path(root, BASE_CATALOG).read_bytes()
    additions = check_scope(manifest, base_bytes, root)
    return {'files_verified': verify_files(root, manifest), 'additions_verified': additions,
            'base_catalog_files': manifest['base_catalog_files'],
            'catalog_sha256': _sha(catalog_bytes), 'v46_preserved': True}


def emit_manifest(root=ROOT):
    """Build the v47 manifest dict; returns it and never writes into protocols/."""
    root = Path(root)
    base_bytes = pinned_path(root, BASE_CATALOG).read_bytes()
    _require(_sha(base_bytes) == BASE_CATALOG_SHA256,
             'base catalog differs from the fixed 0.5.55 release')
    base = json.loads(base_bytes)['files']
    files = dict(base)
    for name in ADDITIONS:
        _require(name not in files, 'addition is already frozen in v46: ' + name)
        files[name] = _sha(pinned_path(root, name).read_bytes())
    return {'version': VERSION, 'scientific_gate': 'HOLD', 'trust_boundary': TRUST_BOUNDARY,
            'new_experiments': [], 'new_experiments_human_reviewed': False,
            'base_catalog': BASE_CATALOG, 'base_catalog_sha256': BASE_CATALOG_SHA256,
            'base_catalog_files': len(base), 'performance_catalog': PERFORMANCE,
            'freeze_rule': FREEZE_RULE,
            'excluded_living_documents': EXCLUDED_LIVING_DOCUMENTS, 'files': files}


def audit(root=ROOT):
    inventory = check_inventory(root, Path(root) / MANIFEST)
    return {'version': VERSION, 'status': 'offline_freeze_verified',
            'base_catalog': BASE_CATALOG, 'base_catalog_files': inventory['base_catalog_files'],
            'files_verified': inventory['files_verified'],
            'additions_verified': inventory['additions_verified'],
            'catalog_sha256': inventory['catalog_sha256'], 'v46_preserved': True,
            'living_documents_excluded': len(EXCLUDED_LIVING_DOCUMENTS),
            'files_modified': 0, 'new_provider_requests': 0, 'new_model_executions': 0,
            'rescored': False, 'scientific_gate': 'HOLD'}


def _frozen_names(root):
    """The names v47 freezes; computable before the manifest itself exists."""
    base = json.loads(pinned_path(root, BASE_CATALOG).read_text(encoding='utf-8'))['files']
    return set(base) | set(ADDITIONS)


def _guard(path, root, frozen):
    path = Path(path).resolve()
    root = Path(root).resolve()
    if not path.is_relative_to(root):
        return path
    rel = path.relative_to(root).as_posix()
    if rel in frozen or rel.startswith('faultda_bench/protocols/'):
        raise ValueError('refusing to write a frozen location: ' + rel)
    if not rel.startswith(ALLOWED_PREFIXES):
        raise ValueError('output inside the repository must be under work/: ' + rel)
    return path


def write_result(result, output, root=ROOT):
    """Write JSON exclusively; the manifest and every frozen name stay read-only."""
    target = _guard(output, root, _frozen_names(root))
    if target.exists():
        raise FileExistsError('refusing to overwrite: ' + str(target))
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(round_floats(result), ensure_ascii=False, indent=2) + '\n')
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='write the audit result; work/ only')
    parser.add_argument('--emit-manifest', type=Path,
                        help='write a freshly built manifest; work/ only')
    args = parser.parse_args(argv)
    if args.emit_manifest:
        write_result(emit_manifest(), args.emit_manifest)
    result = audit()
    if args.output:
        write_result(result, args.output)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
