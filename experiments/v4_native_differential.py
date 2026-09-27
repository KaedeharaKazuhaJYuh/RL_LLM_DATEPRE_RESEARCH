"""Compare the standalone C++ rolling mean with the Python reference."""
import argparse
import json
import math
import random
import statistics
import subprocess
import time
from pathlib import Path

from agent.tools import number
from research.io import ROOT, digest, read_table, write_json


def reference(values, window):
    if window < 1:
        raise ValueError('invalid window')
    return [statistics.mean(values[i-window+1:i+1])
            for i in range(window-1, len(values))]


def native(binary, values, window):
    started = time.perf_counter()
    payload = str(window) + '\n' + '\n'.join(format(v, '.17g') for v in values) + '\n'
    completed = subprocess.run([str(binary)], input=payload, text=True,
                               capture_output=True, check=True)
    output = [float(row) for row in completed.stdout.splitlines()]
    return output, time.perf_counter() - started


def compare(binary, name, values, window, repeats):
    started = time.perf_counter()
    expected = reference(values, window)
    python_times = [time.perf_counter() - started]
    observed, first_seconds = native(binary, values, window)
    if len(observed) != len(expected):
        raise AssertionError(f'{name}: output length differs')
    max_abs = max((abs(a - b) for a, b in zip(observed, expected)), default=0.0)
    if any(not math.isclose(a, b, abs_tol=1e-6, rel_tol=1e-6)
           for a, b in zip(observed, expected)):
        raise AssertionError(f'{name}: numeric mismatch, max absolute error {max_abs}')
    times = [first_seconds]
    for _ in range(repeats - 1):
        started = time.perf_counter()
        reference(values, window)
        python_times.append(time.perf_counter() - started)
        _, elapsed = native(binary, values, window)
        times.append(elapsed)
    return {'case': name, 'rows': len(values), 'window': window,
            'output_rows': len(expected), 'max_absolute_error': max_abs,
            'python_reference_median_seconds': statistics.median(python_times),
            'python_reference_p95_seconds': sorted(python_times)[math.ceil(.95 * len(python_times)) - 1],
            'native_cli_median_seconds': statistics.median(times),
            'native_cli_p95_seconds': sorted(times)[math.ceil(.95 * len(times)) - 1]}


def run(binary, out, *, repeats=10):
    binary, out = Path(binary).resolve(strict=True), Path(out)
    if out.exists() or repeats < 1:
        raise ValueError('new output file and positive repeats required')
    protocol = ROOT / 'tasks/v4/real_csv_v1'
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    cases = []
    for source_id in sorted({task['source_id'] for task in tasks}):
        task = next(task for task in tasks if task['source_id'] == source_id)
        _, rows = read_table(ROOT / task['dataset']['uri'])
        values = [number(row[task['params']['other_column']]) for row in rows]
        cases.append(compare(binary, source_id, values, 3, repeats))
    rng = random.Random(20260927)
    for length in (1_000, 100_000):
        values = [rng.uniform(1, 100) for _ in range(length)]
        cases.append(compare(binary, f'stress_{length}', values, 3, repeats))
    cases.append(compare(binary, 'large_finite', [1e308, 1e308], 2, repeats))
    result = {'version': 'v4-native-differential-1',
              'protocol_sha256': digest(protocol / 'manifest.json'),
              'binary_sha256': digest(binary), 'repeats': repeats,
              'tolerance': {'abs': 1e-6, 'rel': 1e-6},
              'scope': 'standalone numeric CLI, not full tool or episode',
              'cases': cases, 'passed': len(cases)}
    write_json(out, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--repeats', type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(run(args.binary, args.out, repeats=args.repeats), indent=2))
