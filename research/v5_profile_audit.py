"""Summarize repeated synchronized phase profiles without combining nested stages."""
import argparse
import json
import math
import statistics
from pathlib import Path

from research.io import digest, write_json


def _stats(values):
    ordered = sorted(values)
    return {'n': len(values), 'median': statistics.median(ordered),
            'p95_nearest_rank': ordered[math.ceil(.95 * len(ordered)) - 1],
            'min': ordered[0], 'max': ordered[-1]}


def run(paths, out):
    paths, out = [Path(path) for path in paths], Path(out)
    if out.exists():
        raise FileExistsError('new output file required')
    if len(paths) < 2:
        raise ValueError('at least two profiles required')
    profiles = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
    operations = {row['operation'] for row in profiles}
    if len(operations) != 1 or any(not row.get('device_synchronized') for row in profiles):
        raise ValueError('profiles must share an operation and synchronize the device')
    operation = operations.pop()
    compare_fields = {'sft_train': ('steps_sha256', 'max_steps', 'model', 'adapter_sha256'),
                      'grpo_train': ('protocol_sha256', 'adapter_init', 'episodes',
                                     'updated_groups', 'adapter_sha256'),
                      'greedy_eval': ('protocol_sha256', 'episodes', 'model', 'adapter')}
    if operation not in compare_fields:
        raise ValueError('unsupported profile operation')
    fields = compare_fields[operation]
    baseline = {key: profiles[0]['metadata'].get(key) for key in fields}
    if any({key: row['metadata'].get(key) for key in fields} != baseline for row in profiles):
        raise ValueError('workload metadata differs across repetitions')
    stage_sets = [set(row['stages']) for row in profiles]
    if any(stages != stage_sets[0] for stages in stage_sets):
        raise ValueError('phase coverage differs across repetitions')
    stage_calls = [{key: value['calls'] for key, value in row['stages'].items()}
                   for row in profiles]
    if any(calls != stage_calls[0] for calls in stage_calls):
        raise ValueError('phase call counts differ across repetitions')
    runs = [{'path': str(path), 'sha256': digest(path),
             'wall_seconds': profile['wall_seconds'],
             'peak_cuda_allocated_bytes': profile['metadata'].get('peak_cuda_allocated_bytes'),
             'stage_calls': {key: value['calls'] for key, value in profile['stages'].items()}}
            for path, profile in zip(paths, profiles)]
    stages = {stage: _stats([row['stages'][stage]['seconds'] for row in profiles])
              for stage in sorted(stage_sets[0])}
    result = {'schema_version': 'v5-profile-audit-1', 'operation': operation,
              'repetitions': len(paths), 'workload': baseline,
              'wall_seconds': _stats([row['wall_seconds'] for row in profiles]),
              'stages_seconds': stages,
              'peak_cuda_allocated_bytes': _stats([row['metadata']['peak_cuda_allocated_bytes']
                                                    for row in profiles])
              if all(row['metadata'].get('peak_cuda_allocated_bytes') is not None for row in profiles) else None,
              'nested_stages_must_not_be_summed': True, 'runs': runs}
    write_json(out, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('profiles', nargs='+')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.profiles, args.out), ensure_ascii=False, indent=2))
