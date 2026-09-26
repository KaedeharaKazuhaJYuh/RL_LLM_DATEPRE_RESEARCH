"""Aggregate paired frozen evaluations across SFT/GRPO seeds."""
import argparse
import json
import random
import statistics
from pathlib import Path

from research.io import digest, write_json


def paired_summary(baseline, treated):
    before = baseline['records']
    after = treated['records']
    if len(before) != len(after):
        raise ValueError('paired evaluations have different lengths')
    pairs = []
    for left, right in zip(before, after):
        key_left = (left['task_id'], bool(left['fault']))
        key_right = (right['task_id'], bool(right['fault']))
        if key_left != key_right:
            raise ValueError(f'paired evaluation order mismatch: {key_left} != {key_right}')
        pairs.append((left, right))
    return {
        'episodes': len(pairs),
        'baseline_passed': sum(x['passed'] for x, _ in pairs),
        'treated_passed': sum(y['passed'] for _, y in pairs),
        'gained': sum(not x['passed'] and y['passed'] for x, y in pairs),
        'lost': sum(x['passed'] and not y['passed'] for x, y in pairs),
        'unchanged_pass': sum(x['passed'] and y['passed'] for x, y in pairs),
        'unchanged_fail': sum(not x['passed'] and not y['passed'] for x, y in pairs),
    }


def percentile(values, probability):
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * probability)]


def run(entries, out, bootstrap_samples=10000, bootstrap_seed=20260926):
    rows = []
    for seed, baseline_path, treated_path, training_path in entries:
        baseline_path, treated_path, training_path = map(Path, (baseline_path, treated_path, training_path))
        baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
        treated = json.loads(treated_path.read_text(encoding='utf-8'))
        training = json.loads(training_path.read_text(encoding='utf-8'))
        paired = paired_summary(baseline, treated)
        rows.append({'seed': int(seed), **paired,
                     'delta': paired['treated_passed'] - paired['baseline_passed'],
                     'updated_groups': training['updated_groups'],
                     'skipped_zero_advantage_groups': training['skipped_zero_advantage_groups'],
                     'training_episode_passed': training['episode_passed'],
                     'reference_kl_mean': training['reference_kl_mean'],
                     'baseline_sha256': digest(baseline_path),
                     'treated_sha256': digest(treated_path),
                     'training_sha256': digest(training_path)})
    deltas = [row['delta'] for row in rows]
    rng = random.Random(bootstrap_seed)
    boot = [statistics.mean(rng.choices(deltas, k=len(deltas)))
            for _ in range(bootstrap_samples)]
    summary = {'schema_version': 'v4-llm-multiseed-1', 'runs': rows,
               'seeds': [row['seed'] for row in rows],
               'mean_baseline_passed': statistics.mean(row['baseline_passed'] for row in rows),
               'mean_treated_passed': statistics.mean(row['treated_passed'] for row in rows),
               'mean_delta': statistics.mean(deltas),
               'delta_sample_sd': statistics.stdev(deltas) if len(deltas) > 1 else 0.0,
               'delta_bootstrap_95_interval': [percentile(boot, .025), percentile(boot, .975)],
               'positive_runs': sum(delta > 0 for delta in deltas),
               'negative_runs': sum(delta < 0 for delta in deltas),
               'tied_runs': sum(delta == 0 for delta in deltas),
               'bootstrap_samples': bootstrap_samples, 'bootstrap_seed': bootstrap_seed,
               'external_test': False}
    write_json(out, summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='append', nargs=4, required=True,
                        metavar=('SEED', 'BASELINE', 'TREATED', 'TRAINING'))
    parser.add_argument('--out', required=True)
    parser.add_argument('--bootstrap-samples', type=int, default=10000)
    parser.add_argument('--bootstrap-seed', type=int, default=20260926)
    args = parser.parse_args()
    print(json.dumps(run(args.run, args.out, args.bootstrap_samples, args.bootstrap_seed),
                     ensure_ascii=False, indent=2))
