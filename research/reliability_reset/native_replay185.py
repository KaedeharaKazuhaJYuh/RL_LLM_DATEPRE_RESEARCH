"""Replay two recorded program controls with one native process per arm.

Needs a separately installed, pinned AppWorld runtime and protected local inputs.
No model, API trajectory, scoring patch or package installation is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


ROOT = Path(__file__).parent
ARMS = ('reference', 'legal_title_exchange')
EXPECTED = ((True, 2, 0), (False, 1, 1))
SENTINEL = 'FAULTDA185_SCORE='
WORKER = '''
import json, sys, hashlib
from pathlib import Path
import appworld
from appworld import update_root
from appworld.evaluator import evaluate_task
source = Path(appworld.__file__).parent
for relative, expected in json.loads(sys.argv[3]).items():
    if hashlib.sha256((source / relative).read_bytes()).hexdigest() != expected:
        raise ValueError('Native scoring source digest mismatch')
update_root(sys.argv[1])
t = evaluate_task('82e2fac_1', experiment_name='faultda185_' + sys.argv[2], save_report=False)
print('FAULTDA185_SCORE=' + json.dumps(dict(arm=sys.argv[2], success=t.success,
    passed=t.pass_count, failed=t.fail_count, num_tests=t.num_tests)))
'''


def verify_original_inputs(native_root: Path) -> None:
    binding = json.loads((ROOT / 'evidence/1.0.80/NATIVE_PREFLIGHT_180.json').read_text(encoding='utf-8'))
    for row in binding['original_task_packet'] + binding['original_base_databases']:
        data = (native_root / row['path']).read_bytes()
        if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Original native input digest mismatch')


def scoring_sources() -> dict[str, str]:
    manifest = json.loads((ROOT / 'evidence/1.0.80/SOURCE_MANIFEST_180.json').read_text(encoding='utf-8'))
    wanted = {'src/appworld/evaluator.py', 'src/appworld/collections/models.py',
              'src/appworld/apps/lib/models/orm.py', 'src/appworld/apps/lib/models/db.py',
              'src/appworld/task.py'}
    found = {r['path'].removeprefix('src/appworld/'): r['sha256']
             for r in manifest['files'] if r['path'] in wanted}
    if len(found) != len(wanted):
        raise ValueError('Incomplete native scoring-source binding')
    return found


def parse_score(stdout: str, arm: str) -> dict:
    lines = [line[len(SENTINEL):] for line in stdout.splitlines() if line.startswith(SENTINEL)]
    if len(lines) != 1:
        raise ValueError('Native score output missing or ambiguous')
    row = json.loads(lines[0])
    if row.get('arm') != arm or type(row.get('success')) is not bool:
        raise ValueError('Native score arm/type mismatch')
    if any(type(row.get(key)) is not int or row[key] < 0 for key in ('passed', 'failed', 'num_tests')):
        raise ValueError('Invalid native test counts')
    if row['passed'] + row['failed'] != row['num_tests'] or row['num_tests'] != 2:
        raise ValueError('Incomplete original full test suite')
    if row['success'] != (row['passed'] == row['num_tests']):
        raise ValueError('Native success inconsistent with original full test counts')
    return row


def replay(native_python: Path, native_root: Path) -> dict:
    verify_original_inputs(native_root)
    sources = json.dumps(scoring_sources(), sort_keys=True)
    results = []
    for arm, expected in zip(ARMS, EXPECTED):
        child = subprocess.run([str(native_python.resolve()), '-c', WORKER,
                                str(native_root.resolve()), arm, sources],
                               capture_output=True, text=True, timeout=180)
        if child.returncode:
            # No protected stack frames or response contents are put in a public receipt.
            raise RuntimeError(f'Native score worker failed for {arm}; exit {child.returncode}')
        row = parse_score(child.stdout, arm)
        if (row['success'], row['passed'], row['failed']) != expected:
            raise ValueError(f'Native score differs from frozen original control: {arm}')
        results.append(row)
    return {'version': '1.0.85', 'per_arm_process_isolation': True,
            'original_input_files_verified': 37, 'native_score_source_files_verified': len(scoring_sources()),
            'results': results, 'matches_recorded_scores': True,
            'new_environment_trajectories': 0, 'new_model_api_calls': 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('native_python', type=Path)
    parser.add_argument('native_root', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Refusing to overwrite a native replay record')
    result = replay(args.native_python, args.native_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(result, handle, indent=2)
        handle.write('\n')
    print('Both original native control scores replayed in separate processes.')


if __name__ == '__main__':
    main()
