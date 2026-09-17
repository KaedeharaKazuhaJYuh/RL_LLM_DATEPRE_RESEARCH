"""Frozen, paired stochastic execution audit of the existing V4 checkpoints."""
import argparse
import json
import tempfile
from pathlib import Path
import numpy as np

from experiments.v4_sequence_train import rollout
from research.io import ROOT, write_json
from research.v4_sequence_policy import SequencePolicy


METHODS = ('supervised', 'original_reinforce', 'batch_only', 'batch_anchored')


def checkpoint(method, seed, original, stable):
    directory = original if method in ('supervised', 'original_reinforce') else stable
    filename = ('supervised_reinforce' if method == 'original_reinforce' else method)
    with np.load(directory / f'{filename}_{seed}.npz') as data:
        return data['weights'].copy()


def run(out, original, stable, repeats=20, seeds=(1, 2, 3)):
    out = Path(out)
    if out.exists():
        raise FileExistsError('new output directory required')
    if repeats < 1:
        raise ValueError('repeats must be positive')
    original, stable = Path(original), Path(stable)
    tasks = json.loads((original / 'protocol/tasks.json').read_text(encoding='utf-8'))
    gold = json.loads((original / 'protocol/oracle.json').read_text(encoding='utf-8'))
    validation = [t for t in tasks if t['split'] == 'validation']
    assert not {t['source_id'] for t in validation} & {t['source_id'] for t in tasks if t['split'] == 'train'}
    out.mkdir(parents=True)
    records = []
    with tempfile.TemporaryDirectory(prefix='v4_stochastic_') as scratch:
        for seed in seeds:
            for method in METHODS:
                policy = SequencePolicy(seed)
                policy.weights = checkpoint(method, seed, original, stable)
                frozen = policy.fingerprint()
                for task in validation:
                    for fault in (False, True):
                        for repeat in range(repeats):
                            # Paired random-number stream per seed/task/fault/repeat.
                            # The same stream does not imply identical sampled actions.
                            sample_seed = np.random.SeedSequence([seed, int(task['task_id'], 16), int(fault), repeat])
                            policy.rng = np.random.default_rng(sample_seed)
                            result, _, _ = rollout(policy, task, gold[task['task_id']], scratch, fault, True)
                            records.append({'method': method, 'seed': seed, 'source_id': task['source_id'],
                                            'task_id': task['task_id'], 'fault': fault, 'repeat': repeat, **result})
                assert frozen == policy.fingerprint(), 'evaluation changed weights'
    groups = []
    for method in METHODS:
        rows = [r for r in records if r['method'] == method]
        groups.append({'method': method, 'episodes': len(rows),
                       'passed': sum(r['passed'] for r in rows),
                       'pass_rate': float(np.mean([r['passed'] for r in rows])),
                       'mean_reward': float(np.mean([r['reward'] for r in rows])),
                       'mean_calls': float(np.mean([r['tool_calls'] for r in rows])),
                       'clean_pass_rate': float(np.mean([r['passed'] for r in rows if not r['fault']])),
                       'fault_pass_rate': float(np.mean([r['passed'] for r in rows if r['fault']]))})
    # Source is the independent resampling unit; there are only two sources.
    source_results = []
    for method in METHODS:
        for source in sorted({t['source_id'] for t in validation}):
            rows = [r for r in records if r['method'] == method and r['source_id'] == source]
            source_results.append({'method': method, 'source_id': source,
                                   'episodes': len(rows), 'pass_rate': float(np.mean([r['passed'] for r in rows]))})
    manifest = {'protocol': 'v4-sequence-1', 'mode': 'sampled execution, frozen checkpoint',
                'methods': list(METHODS), 'seeds': list(seeds), 'repeats_per_task_condition': repeats,
                'selection': 'fixed checkpoints, no validation tuning', 'external_test': False,
                'pairing': 'same RNG seed per task/condition/repeat; actions may diverge',
                'independent_validation_sources': len({t['source_id'] for t in validation})}
    write_json(out / 'manifest.json', manifest)
    write_json(out / 'records.json', records)
    summary = {'manifest': manifest, 'groups': groups, 'source_results': source_results}
    write_json(out / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--original', default=str(ROOT / 'work/v4_sequence_train_001'))
    parser.add_argument('--stable', default=str(ROOT / 'work/v4_sequence_stable_001'))
    parser.add_argument('--repeats', type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(run(args.out, args.original, args.stable, args.repeats)['groups'], ensure_ascii=False, indent=2))
