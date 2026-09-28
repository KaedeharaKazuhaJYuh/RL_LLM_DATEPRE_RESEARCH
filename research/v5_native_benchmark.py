"""Compare the optional native rolling kernel and complete CSV tool workload."""
import argparse
import json
import math
import os
import statistics
import tempfile
import time
from pathlib import Path

from agent.native_rolling import rolling_mean
from agent.tools import ACTIONS, execute_tool
from research.io import ROOT, digest, write_json, write_table
from research.v4_sequence_env import SequenceEnv


def measure(call, repeats):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        result = call()
        times.append(time.perf_counter() - start)
    return result, {'median_seconds': statistics.median(times),
                    'min_seconds': min(times), 'max_seconds': max(times),
                    'repetitions': repeats}


def compare(left, right):
    if len(left) != len(right):
        raise AssertionError('rolling output length mismatch')
    maximum = 0.0
    for a, b in zip(left, right):
        difference = abs(a - b)
        maximum = max(maximum, difference)
        if not math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10):
            raise AssertionError(f'rolling output mismatch: {a} versus {b}')
    return maximum


def run(out, repeats=3):
    out = Path(out)
    if out.exists():
        raise FileExistsError('new output file required')
    if repeats < 2:
        raise ValueError('at least two repetitions required')
    if not os.environ.get('V5_ROLLING_LIB'):
        raise RuntimeError('V5_ROLLING_LIB is required')
    rows = []
    for count in (1000, 100000, 1000000):
        numbers = [float(i % 97) / 10 for i in range(count)]
        window = 3
        reference, python = measure(
            lambda: [statistics.mean(numbers[i-window+1:i+1])
                     for i in range(window-1, count)], repeats)
        produced, native = measure(lambda: rolling_mean(numbers, window), repeats)
        rows.append({'size': count, 'stage': 'numeric_kernel_with_python_boundary',
                     'python': python, 'native': native,
                     'max_absolute_difference': compare(reference, produced),
                     'native_speedup': python['median_seconds'] / native['median_seconds']})
    original = os.environ.get('V5_ROLLING_BACKEND')
    try:
        with tempfile.TemporaryDirectory(prefix='v5_native_bench_', dir=ROOT / 'work') as folder:
            path = Path(folder) / 'input.csv'
            for count in (1000, 100000):
                write_table(path, ['value'], [{'value': str(float(i % 97) / 10)}
                                               for i in range(count)])
                args = {'uri': str(path), 'params': {'column': 'value', 'window': 3}}
                os.environ['V5_ROLLING_BACKEND'] = 'python'
                baseline, python = measure(lambda: execute_tool('rolling_mean', args), repeats)
                os.environ['V5_ROLLING_BACKEND'] = 'native'
                actual, native = measure(lambda: execute_tool('rolling_mean', args), repeats)
                rows.append({'size': count, 'stage': 'complete_csv_tool_call',
                             'input_sha256': digest(path), 'python': python, 'native': native,
                             'max_absolute_difference': compare(baseline['answer']['values'],
                                                                actual['answer']['values']),
                             'native_speedup': python['median_seconds'] / native['median_seconds']})
            # The isolated worker has a deliberate 2 MB reply cap. Benchmark
            # 10k rows under that cap and 100k rows in-process without relaxing it.
            for count, isolated in ((100000, False), (10000, True)):
                write_table(path, ['value'], [{'value': str(float(i % 97) / 10)}
                                               for i in range(count)])
                task = {'task_id': 'v5_native_bench', 'source_id': 'generated_performance_only',
                        'split': 'dev', 'prompt': 'Report rolling mean of value, then stop.',
                        'dataset': {'uri': path.relative_to(ROOT).as_posix(),
                                    'columns': ['value'], 'sha256': digest(path)},
                        'params': {'column': 'value', 'category_column': 'value',
                                   'date_column': 'value', 'other_column': 'value',
                                   'window': 3, 'lower': 0, 'upper': 100},
                        'allowed_tools': ACTIONS,
                        'constraints': {'max_steps': 2, 'max_tool_calls': 1,
                                        'max_seconds': 120, 'isolated_tools': isolated,
                                        'tool_timeout_seconds': 30}}

                def episode():
                    with tempfile.TemporaryDirectory(prefix='episode_', dir=folder) as scratch:
                        env = SequenceEnv(task, {'plan': ['rolling_mean']}, scratch)
                        env.step('rolling_mean')
                        env.step('stop')
                        outcome = env.result()
                        if not outcome['passed']:
                            raise AssertionError(f'end-to-end rolling task failed: {env.history}')
                        return outcome

                os.environ['V5_ROLLING_BACKEND'] = 'python'
                _, python = measure(episode, repeats)
                os.environ['V5_ROLLING_BACKEND'] = 'native'
                _, native = measure(episode, repeats)
                rows.append({'size': count, 'stage': 'isolated_verified_episode' if isolated
                             else 'inprocess_verified_episode',
                             'input_sha256': digest(path), 'python': python, 'native': native,
                             'native_speedup': python['median_seconds'] / native['median_seconds']})
    finally:
        if original is None:
            os.environ.pop('V5_ROLLING_BACKEND', None)
        else:
            os.environ['V5_ROLLING_BACKEND'] = original
    result = {'schema_version': 'v5-native-benchmark-1',
              'library_sha256': digest(os.environ['V5_ROLLING_LIB']),
              'repetitions': repeats, 'rows': rows}
    write_json(out, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--repeats', type=int, default=3)
    arguments = parser.parse_args()
    print(json.dumps(run(arguments.out, arguments.repeats), indent=2))
