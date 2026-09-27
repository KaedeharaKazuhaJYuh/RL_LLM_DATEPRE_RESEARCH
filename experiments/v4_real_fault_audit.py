"""Replay frozen public-CSV tasks through the opt-in isolated tool boundary."""
import argparse
import copy
import json
import tempfile
from pathlib import Path

from research.io import ROOT, digest, write_json
from research.v4_sequence_env import SequenceEnv

FAULTS = ('none', 'transient_read', 'timeout', 'partial_write')


def run(protocol, out, *, limit=0):
    protocol, out = Path(protocol), Path(out)
    if out.exists():
        raise FileExistsError('new output file required')
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    oracle = json.loads((protocol / 'dev_oracle.json').read_text(encoding='utf-8'))
    if limit:
        tasks = tasks[:limit]
    records = []
    with tempfile.TemporaryDirectory(prefix='v4_real_fault_', dir=ROOT / 'work') as scratch:
        for task in tasks:
            for fault in FAULTS:
                current = copy.deepcopy(task)
                if fault in ('timeout', 'partial_write'):
                    current['constraints']['tool_timeout_seconds'] = .15
                episode = Path(scratch) / task['task_id'] / fault
                env = SequenceEnv(current, oracle[task['task_id']], episode,
                                  fault=fault == 'transient_read',
                                  fault_mode=fault if fault in ('timeout', 'partial_write') else None)
                initial = digest(ROOT / task['dataset']['uri'])
                first_failed = False
                private_partial = False
                plan = oracle[task['task_id']]['plan']
                if fault != 'none':
                    env.step(plan[0])
                    first_failed = bool(env.history and not env.history[0]['ok'])
                    private_partial = (env.folder / 'step_1' / 'artifact' / 'table.csv').exists()
                    if not first_failed or env.current != ROOT / task['dataset']['uri']:
                        raise AssertionError('failed attempt changed committed state')
                    if digest(ROOT / task['dataset']['uri']) != initial:
                        raise AssertionError('failed attempt changed input')
                    if fault == 'partial_write' and not private_partial:
                        raise AssertionError('partial fault did not create a private partial file')
                for action in (*plan, 'stop'):
                    env.step(action)
                result = env.result()
                if not result['passed'] or digest(ROOT / task['dataset']['uri']) != initial:
                    raise AssertionError(f'expert recovery failed: {task["task_id"]}/{fault}')
                records.append({'task_id': task['task_id'], 'source_id': task['source_id'],
                                'pair_family': task['pair_family'],
                                'paraphrase_id': task['paraphrase_id'], 'fault': fault,
                                'passed': result['passed'], 'first_failed': first_failed,
                                'private_partial_rejected': fault == 'partial_write' and private_partial,
                                'tool_calls': result['tool_calls'],
                                'input_unchanged': True})
    summary = {'version': 'v4-real-fault-audit-1', 'protocol_sha256':
               digest(protocol / 'manifest.json'), 'tasks': len(tasks),
               'episodes': len(records), 'passed': sum(r['passed'] for r in records),
               'by_fault': {mode: {'n': sum(r['fault'] == mode for r in records),
                                   'passed': sum(r['passed'] for r in records if r['fault'] == mode)}
                            for mode in FAULTS}, 'records': records}
    write_json(out, summary)
    return {k: v for k, v in summary.items() if k != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', default=str(ROOT / 'tasks/v4/real_csv_v1'))
    parser.add_argument('--out', required=True)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(run(args.protocol, args.out, limit=args.limit), indent=2))
