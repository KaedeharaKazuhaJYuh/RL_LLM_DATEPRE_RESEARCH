"""Pair V4.5.5/6 greedy dev results by task and fault without selecting models."""
import argparse
import json
from pathlib import Path

from research.io import ROOT, digest, write_json


SEEDS = (20260921, 20260922, 20260923)
ARMS = ('sft', 'static_shaped', 'dynamic_shaped', 'static_outcome')
SLICES = ('seen_triple:clean', 'seen_triple:fault',
          'unseen_triple:clean', 'unseen_triple:fault')


def records(path):
    payload = json.loads(Path(path).read_text(encoding='utf-8'))
    if payload['episodes'] != 96 or not payload['greedy'] or payload['external_test']:
        raise ValueError(f'not a full greedy development evaluation: {path}')
    rows = {(row['task_id'], bool(row['fault'])): row for row in payload['records']}
    if len(rows) != 96:
        raise ValueError(f'duplicate task-condition row: {path}')
    return payload, rows


def pair(before, after):
    if set(before) != set(after):
        raise ValueError('paired evaluations do not have identical task conditions')
    out = {}
    for name in SLICES:
        selected = [key for key, row in before.items()
                    if row['novelty'] + (':fault' if row['fault'] else ':clean') == name]
        if not selected or any(after[key]['novelty'] != before[key]['novelty'] for key in selected):
            raise ValueError(f'invalid slice: {name}')
        old = sum(bool(before[key]['passed']) for key in selected)
        new = sum(bool(after[key]['passed']) for key in selected)
        gains = sum(not before[key]['passed'] and bool(after[key]['passed']) for key in selected)
        losses = sum(bool(before[key]['passed']) and not after[key]['passed'] for key in selected)
        out[name] = {'n': len(selected), 'before': old, 'after': new,
                     'gain': gains, 'loss': losses, 'delta': new - old}
    out['all'] = {key: sum(row[key] for row in out.values())
                  for key in ('n', 'before', 'after', 'gain', 'loss', 'delta')}
    return out


def build(work):
    result = {'schema_version': 'v4-llm-composition-audit-1', 'seeds': {},
              'external_test': False}
    protocol = ROOT / 'tasks/v4/llm_composition_v1'
    train_ids = {row['task_id'] for row in json.loads((protocol / 'tasks.json').read_text(
        encoding='utf-8')) if row['split'] == 'train'}
    for seed in SEEDS:
        old_path = work / ('v4_llm_hard_sft100_dev_full.json' if seed == SEEDS[0]
                           else f'v4_llm_hard_sft100_seed{seed}_dev_full.json')
        _, old = records(old_path)
        paths = {'sft': work / f'v4_llm_composition_sft100_seed{seed}_dev_full.json'}
        paths.update({arm: work / f'v4_llm_composition_{arm}_seed{seed}_dev_full.json'
                      for arm in ARMS[1:]})
        evaluations = {arm: records(path) for arm, path in paths.items()}
        protocols = {payload['protocol_sha256'] for payload, _ in evaluations.values()}
        if len(protocols) != 1:
            raise ValueError(f'new arms have different dev protocols for seed {seed}')
        training = {}
        for arm in ARMS[1:]:
            folder = work / f'v4_llm_composition_{arm}_seed{seed}'
            summary_path = folder / 'summary.json'
            summary = json.loads(summary_path.read_text(encoding='utf-8'))
            if (summary['episodes'] != 32 or summary['selected_groups'] != 8 or
                    summary['group_size'] != 4 or summary['fault_mode'] != 'both' or
                    summary['protocol_sha256'] not in protocols or
                    summary['adapter_init'] != f'work/v4_llm_composition_sft100_seed{seed}/adapter'):
                raise ValueError(f'incompatible training arm: {summary_path}')
            groups = [(row['task_id'], row['fault']) for row in summary['records']]
            if (len(groups) != 8 or sum(fault for _, fault in groups) != 4 or
                    any(task_id not in train_ids for task_id, _ in groups)):
                raise ValueError(f'unbalanced training arm: {summary_path}')
            training[arm] = {'summary_sha256': digest(summary_path),
                             'sampling_mode': summary['selection_mode'],
                             'reward_mode': summary['reward_mode'],
                             'episodes': summary['episodes'],
                             'task_signal_groups': summary['task_signal_groups'],
                             'updated_groups': summary['updated_groups'],
                             'episode_passed': summary['episode_passed'],
                             'reference_kl_mean': summary['reference_kl_mean'],
                             'clip_fraction_mean': summary['clip_fraction_mean'],
                             'elapsed_seconds': summary['elapsed_seconds'],
                             'adapter_sha256': summary['adapter_sha256'],
                             'groups': groups}
        if training['static_shaped']['groups'] != training['static_outcome']['groups']:
            raise ValueError(f'static reward arms have different scheduled tasks for seed {seed}')
        if training['dynamic_shaped']['groups'][0] != training['static_shaped']['groups'][0]:
            raise ValueError(f'dynamic arm has a different starting task for seed {seed}')
        seed_result = {'old_sft': {'passed': sum(row['passed'] for row in old.values()),
                                   'sha256': digest(old_path)}, 'arms': {}, 'training': training}
        sft = evaluations['sft'][1]
        for arm, (payload, rows) in evaluations.items():
            row = {'passed': payload['passed'], 'sha256': digest(paths[arm]),
                   'vs_old_sft': pair(old, rows)}
            if arm != 'sft':
                row['vs_new_sft'] = pair(sft, rows)
            seed_result['arms'][arm] = row
        for left, right, label in (
                ('static_shaped', 'dynamic_shaped', 'dynamic_vs_static'),
                ('static_outcome', 'static_shaped', 'shaped_vs_outcome')):
            seed_result[label] = pair(evaluations[left][1], evaluations[right][1])
        result['seeds'][str(seed)] = seed_result
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', default='work')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    output = Path(args.out)
    if output.exists():
        raise FileExistsError('new output file required')
    summary = build(Path(args.work))
    write_json(output, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
