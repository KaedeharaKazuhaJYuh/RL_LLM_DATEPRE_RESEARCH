"""Verify the frozen V5.0.10 held-out episodes without model inference."""
import argparse
import copy
import json
import tempfile
from pathlib import Path

from research.io import ROOT, digest, write_json
from research.v4_sequence_env import SequenceEnv

MODES = ('none', 'transient_read', 'timeout', 'partial_write')


def run(protocol, out):
    protocol, out = Path(protocol), Path(out)
    if out.exists():
        raise FileExistsError('new audit output required')
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    oracle = json.loads((protocol / 'dev_oracle.json').read_text(encoding='utf-8'))
    manifest = json.loads((protocol / 'manifest.json').read_text(encoding='utf-8'))
    if (not manifest['external_test'] or manifest['train_task_count'] != 0 or
            set(oracle) != {task['task_id'] for task in tasks}):
        raise ValueError('expected eval-only held-out protocol')
    records = []
    with tempfile.TemporaryDirectory(prefix='v5_0_10_expert_') as scratch:
        for task in tasks:
            for mode in MODES:
                episode = copy.deepcopy(task)
                if mode in ('timeout', 'partial_write'):
                    episode['constraints']['tool_timeout_seconds'] = .15
                env = SequenceEnv(episode, oracle[task['task_id']], scratch,
                                  fault=mode == 'transient_read',
                                  fault_mode=mode if mode in ('timeout', 'partial_write') else None)
                plan = oracle[task['task_id']]['plan']
                actions = []
                while not env.done:
                    completed = sum(row['ok'] for row in env.history)
                    action = plan[completed] if completed < len(plan) else 'stop'
                    actions.append(action)
                    env.step(action)
                result = env.result()
                private_partial = env.folder / 'step_1/artifact/table.csv'
                partial_present = (private_partial.exists() and
                                   private_partial.read_bytes() == b'incomplete,header\n1,')
                record = {'task_id': task['task_id'], 'fault_kind': mode,
                          'passed': result['passed'], 'injection_applied': env.injected,
                          'private_partial_artifact_present': partial_present,
                          'actions': actions,
                          'tool_history': [{'action': row['action'], 'ok': row['ok'],
                                            'error_type': row.get('error', '').split(':', 1)[0]}
                                           for row in env.history]}
                records.append(record)
    if len(records) != len(tasks) * len(MODES) or any(
            not row['passed'] or row['injection_applied'] != (row['fault_kind'] != 'none')
            for row in records):
        raise AssertionError('held-out expert or fault injection failed')
    if any(row['private_partial_artifact_present'] != (row['fault_kind'] == 'partial_write')
           for row in records):
        raise AssertionError('private partial-write artifact was not isolated')
    report = {'schema_version': 'v5-0-10-expert-audit-1',
              'protocol_sha256': digest(protocol / 'manifest.json'),
              'episodes': len(records), 'passed': len(records), 'records': records}
    write_json(out, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=ROOT / 'tasks/v5/rewrite_holdout_v1')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.protocol, args.out), ensure_ascii=False, indent=2))
