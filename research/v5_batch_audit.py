"""Audit greedy batched inference against a serial run of the same workload."""
import argparse
import json
from pathlib import Path

from research.io import digest, write_json


def audit(serial_result, serial_profile, batched_result, batched_profile, out):
    paths = [Path(p) for p in (serial_result, serial_profile, batched_result, batched_profile)]
    serial, serial_timing, batched, batched_timing = [
        json.loads(p.read_text(encoding='utf-8')) for p in paths]
    if serial.get('batch_size', 1) != 1 or batched.get('batch_size', 1) <= 1:
        raise ValueError('expected serial and batched evaluations')
    for field in ('protocol_sha256', 'model', 'adapter', 'episodes', 'fault_modes'):
        if serial.get(field) != batched.get(field):
            raise ValueError(f'evaluation {field} differs')
    for field in ('operation', 'device_synchronized'):
        if serial_timing.get(field) != batched_timing.get(field):
            raise ValueError(f'profile {field} differs')
    if serial_timing['operation'] != 'greedy_eval' or not serial_timing['device_synchronized']:
        raise ValueError('synchronized greedy profiles required')
    for field in ('protocol_sha256', 'model', 'adapter', 'episodes'):
        if serial_timing['metadata'].get(field) != batched_timing['metadata'].get(field):
            raise ValueError(f'profile metadata {field} differs')
    if serial_timing['metadata'].get('batch_size') != 1 or (
            batched_timing['metadata'].get('batch_size') != batched['batch_size']):
        raise ValueError('profile batch size differs')
    for field in ('max_new_tokens', 'fault_modes', 'action_guard'):
        a, b = serial_timing['metadata'], batched_timing['metadata']
        if field in a and field in b and a[field] != b[field]:
            raise ValueError(f'profile metadata {field} differs')
    if (len(serial['records']) != len(batched['records']) or
            len(serial['records']) != serial['episodes']):
        raise ValueError('record count differs')
    mismatches = []
    for index, (a, b) in enumerate(zip(serial['records'], batched['records'])):
        identity = ('task_id', 'source_id', 'novelty', 'fault', 'fault_kind')
        if any(a.get(key) != b.get(key) for key in identity):
            raise ValueError(f'episode order or identity differs at {index}')
        steps_a = [(s['action'], s['raw'], s['parse_error']) for s in a['steps']]
        steps_b = [(s['action'], s['raw'], s['parse_error']) for s in b['steps']]
        if steps_a != steps_b or a['passed'] != b['passed'] or a['reward'] != b['reward']:
            mismatches.append({'index': index, 'task_id': a['task_id'],
                               'serial_actions': [s[0] for s in steps_a],
                               'batched_actions': [s[0] for s in steps_b],
                               'serial_passed': a['passed'], 'batched_passed': b['passed'],
                               'raw_equal': [s[1] for s in steps_a] == [s[1] for s in steps_b]})
    elapsed_a, elapsed_b = serial_timing['wall_seconds'], batched_timing['wall_seconds']
    if elapsed_a <= 0 or elapsed_b <= 0:
        raise ValueError('invalid profile duration')
    report = {'schema_version': 'v5-batch-audit-1',
              'input_sha256': {p.name: digest(p) for p in paths},
              'protocol_sha256': serial['protocol_sha256'],
              'episodes': serial['episodes'], 'batch_size': batched['batch_size'],
              'exact_episode_matches': serial['episodes'] - len(mismatches),
              'mismatches': mismatches,
              'serial_wall_seconds': elapsed_a, 'batched_wall_seconds': elapsed_b,
              'wall_speedup': elapsed_a / elapsed_b,
              'serial_peak_cuda_allocated_bytes': serial_timing['metadata']['peak_cuda_allocated_bytes'],
              'batched_peak_cuda_allocated_bytes': batched_timing['metadata']['peak_cuda_allocated_bytes']}
    write_json(out, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('serial_result')
    parser.add_argument('serial_profile')
    parser.add_argument('batched_result')
    parser.add_argument('batched_profile')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.serial_result, args.serial_profile,
                           args.batched_result, args.batched_profile, args.out),
                     ensure_ascii=False, indent=2))
