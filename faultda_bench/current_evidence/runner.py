"""Run the current-evidence acceptance set declared by the registry.

The registry is the single source of truth for which test modules and which
audits make up the current-version evidence job; the CI workflow must call this
module instead of inlining a module list, so the two can never drift apart.
Stdlib only: the job installs numpy for the audits, nothing else.
"""
import argparse
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'faultda_bench/protocols/current_evidence_v1.json'
WORK_PREFIX = 'work/'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def load_registry(path=REGISTRY):
    """Read the registry and validate every invariant the guards depend on."""
    registry = json.loads(Path(path).read_text(encoding='utf-8'))
    _require(registry.get('registry') == 'current_evidence',
             'not a current_evidence registry')
    _require(registry.get('schema') == 1, 'unsupported registry schema')
    _require(registry.get('scientific_gate') == 'HOLD', 'scientific gate is not HOLD')

    modules = registry.get('test_modules') or []
    _require(modules, 'test_modules is empty')
    _require(len(set(modules)) == len(modules), 'duplicate test_modules entry')
    for name in modules:
        _require((ROOT / 'tests' / (name.split('.')[-1] + '.py')).is_file(),
                 'test module has no file on disk: ' + name)

    categories = registry.get('excluded_categories') or []
    excluded = []
    for entry in registry.get('excluded') or []:
        for key in ('module', 'category', 'reason'):
            _require(entry.get(key), 'excluded entry is missing ' + key)
        _require(entry['category'] in categories,
                 'excluded category is not declared: ' + entry['category'])
        excluded.append(entry['module'])
    overlap = sorted(set(modules) & set(excluded))
    _require(not overlap, 'module is both registered and excluded: ' + ', '.join(overlap))

    outputs = []
    for audit in registry.get('audits') or []:
        for key in ('id', 'module', 'args', 'outputs'):
            _require(key in audit, 'audit entry is missing ' + key)
        for name in audit['outputs']:
            _require(name.startswith(WORK_PREFIX), 'audit output is not under work/: ' + name)
        outputs.extend(audit['outputs'])
    artifact = registry.get('artifact') or {}
    for name in artifact.get('paths') or []:
        _require(name.startswith(WORK_PREFIX), 'artifact path is not under work/: ' + name)
    _require(list(artifact.get('paths') or []) == outputs,
             'artifact.paths differs from the audit outputs')
    return registry


def build_suite(registry=None):
    """Load the registered modules with the repository root on ``sys.path``."""
    registry = registry or load_registry()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return unittest.TestSuite([
        unittest.defaultTestLoader.loadTestsFromNames(registry['test_modules'])])


def run_tests(verbose=False, registry=None):
    suite = build_suite(registry)
    result = unittest.TextTestRunner(verbosity=2 if verbose else 1).run(suite)
    return 0 if result.wasSuccessful() else 1


def run_audits(registry=None):
    """Run each declared audit as a subprocess, in order, into a clean work/."""
    registry = registry or load_registry()
    (ROOT / 'work').mkdir(parents=True, exist_ok=True)
    for audit in registry['audits']:
        for name in audit['outputs']:
            if (ROOT / name).exists():
                print('audit output already exists, remove work/ first: ' + name,
                      file=sys.stderr)
                return 1
    for audit in registry['audits']:
        completed = subprocess.run(
            [sys.executable, '-m', audit['module'], *audit['args']], cwd=ROOT)
        if completed.returncode != 0:
            print('audit failed: ' + audit['id'], file=sys.stderr)
            return 1
        for name in audit['outputs']:
            if not (ROOT / name).exists():
                print('audit did not produce its declared output: ' + name, file=sys.stderr)
                return 1
    return 0


def describe(registry=None):
    registry = registry or load_registry()
    return {
        'version': registry['version'],
        'scientific_gate': registry['scientific_gate'],
        'python_version': registry['python_version'],
        'test_module_count': len(registry['test_modules']),
        'test_modules': list(registry['test_modules']),
        'excluded_count': len(registry['excluded']),
        'audits': [{'id': a['id'], 'module': a['module'], 'args': list(a['args']),
                    'outputs': list(a['outputs'])} for a in registry['audits']],
        'artifact_name': registry['artifact']['name'],
        'artifact_paths': list(registry['artifact']['paths']),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true', help='print the registered evidence set')
    group.add_argument('--run-tests', action='store_true', help='run the registered test modules')
    group.add_argument('--run-audits', action='store_true', help='run the registered audits')
    parser.add_argument('--verbose', action='store_true', help='verbose test output')
    args = parser.parse_args(argv)
    if args.list:
        print(json.dumps(describe(), ensure_ascii=False, indent=2))
        return 0
    if args.run_tests:
        return run_tests(verbose=args.verbose)
    return run_audits()


if __name__ == '__main__':
    raise SystemExit(main())
