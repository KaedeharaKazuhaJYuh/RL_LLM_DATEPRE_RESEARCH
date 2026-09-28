"""Audit frozen paired SFT/GRPO evaluations without selecting a new model."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from research.io import ROOT, digest, write_json

SEEDS = (20260921, 20260922, 20260923)
FAULTS = ('none', 'transient_read', 'timeout', 'partial_write')
BASE_SHA = '58858233513d76b8703e72eed6ce16807b523328188e13329257fb9594462945'
SFT_SHA = (
    '867a6c91b74a1c4a8b233de6511977e7876008c17ace9df8bab12a877696c9ff',
    '268cc2423789691eec5bc73bd62c78a480c425ab1edb3f74efaab81b16c2ca3a',
    '6c402eafee2cf01cf6c2addae89e765e9cbc05f938356c0cae16e963a921a993',
)


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _indexed(result, task_ids):
    if result.get('episodes') != 48 or result.get('fault_modes') != list(FAULTS) or not result.get('greedy'):
        raise ValueError('incomplete or non-frozen evaluation')
    records = {}
    for row in result['records']:
        key = (row['task_id'], row.get('fault_kind'))
        if row['task_id'] not in task_ids or key in records or row.get('fault_kind') not in FAULTS:
            raise ValueError('evaluation has unknown or duplicate task-condition')
        records[key] = row
    if set(records) != {(task, fault) for task in task_ids for fault in FAULTS}:
        raise ValueError('evaluation is missing task-condition pairs')
    if sum(bool(r['passed']) for r in records.values()) != result['passed']:
        raise ValueError('evaluation total does not match records')
    return records


def run(work, out):
    protocol = ROOT / 'tasks/v5/beta_holdout_v1'
    tasks = {t['task_id']: t for t in _read(protocol / 'tasks.json')}
    protocol_sha = digest(protocol / 'manifest.json')
    if protocol_sha != '6387bc6780dc6b5b594e5e8fa4709da9a343b6e786270e87ea56a00bb6ba994c':
        raise ValueError('frozen protocol changed')
    if digest(ROOT / 'work/modelscope_deepseek_r1_1p5b/model.safetensors') != BASE_SHA:
        raise ValueError('base weights changed')
    train_tasks = {t['task_id'] for t in _read(ROOT / 'tasks/v4/llm_composition_v1/tasks.json')
                   if t['split'] == 'train'}
    rows = []
    all_gains = all_losses = clean_before = clean_after = 0
    updated_seeds = 0
    slices = defaultdict(lambda: {'n': 0, 'sft': 0, 'rl': 0, 'gain': 0, 'loss': 0})
    for seed, sft_hash in zip(SEEDS, SFT_SHA):
        sft_adapter = work / f'v4_llm_composition_sft100_seed{seed}/adapter'
        rl_dir = work / f'v5_beta1_grpo_seed{seed}'
        rl_adapter = rl_dir / 'adapter'
        if digest(sft_adapter / 'adapter_model.safetensors') != sft_hash:
            raise ValueError(f'SFT adapter {seed} changed')
        training = _read(rl_dir / 'summary.json')
        checks = {'seed': seed, 'updates': 1, 'episodes': 64, 'selected_groups': 16,
                  'group_size': 4, 'ppo_epochs': 2, 'selection_mode': 'schedule_static',
                  'reward_mode': 'shaped', 'temperature': 0.9,
                  'learning_rate': 2e-6, 'clip_range': 0.2, 'kl_beta': 0.02,
                  'adapter_init': sft_adapter.relative_to(ROOT).as_posix(),
                  'external_test': False}
        for key, value in checks.items():
            if training.get(key) != value:
                raise ValueError(f'training {seed} {key} differs from preregistration')
        if set(training['task_ids']) - train_tasks:
            raise ValueError('holdout or dev task entered training')
        rl_hash = digest(rl_adapter / 'adapter_model.safetensors')
        if training['adapter_sha256']['adapter_model.safetensors'] != rl_hash:
            raise ValueError('trained adapter hash differs from summary')
        updated_seeds += training['updated_groups'] > 0
        pair = []
        for label, adapter in (('sft', sft_adapter), ('rl', rl_adapter)):
            path = work / f'v5_beta1_{label}_seed{seed}.json'
            result = _read(path)
            if result.get('protocol_sha256') != protocol_sha or Path(result['adapter']).resolve() != adapter.resolve():
                raise ValueError(f'evaluation {seed}/{label} used wrong protocol or adapter')
            pair.append((path, result, _indexed(result, tasks)))
        before, after = pair[0][2], pair[1][2]
        gain = loss = seed_clean_before = seed_clean_after = 0
        for key, left in before.items():
            right = after[key]
            task = tasks[key[0]]
            a, b = bool(left['passed']), bool(right['passed'])
            gain += b and not a
            loss += a and not b
            if key[1] == 'none':
                seed_clean_before += a
                seed_clean_after += b
            for tag in (f'source:{task["source_id"]}', f'language:{task["paraphrase_id"]}',
                        f'family:{task["pair_family"]}', f'fault:{key[1]}'):
                bucket = slices[tag]
                bucket['n'] += 1
                bucket['sft'] += a
                bucket['rl'] += b
                bucket['gain'] += b and not a
                bucket['loss'] += a and not b
        all_gains += gain
        all_losses += loss
        clean_before += seed_clean_before
        clean_after += seed_clean_after
        rows.append({'seed': seed, 'sft_passed': pair[0][1]['passed'],
                     'rl_passed': pair[1][1]['passed'], 'gain': gain, 'loss': loss,
                     'net': gain - loss, 'clean_sft': seed_clean_before,
                     'clean_rl': seed_clean_after, 'updated_groups': training['updated_groups'],
                     'training_episodes': training['episodes'], 'sft_adapter_sha256': sft_hash,
                     'rl_adapter_sha256': rl_hash,
                     'sft_eval_sha256': digest(pair[0][0]), 'rl_eval_sha256': digest(pair[1][0])})
    criterion = (all_gains > all_losses and sum(r['net'] > 0 for r in rows) >= 2 and
                 min(r['net'] for r in rows) >= -2 and clean_after >= clean_before and
                 updated_seeds >= 2)
    summary = {'schema_version': 'v5-beta1-paired-audit-1', 'protocol_sha256': protocol_sha,
               'base_sha256': BASE_SHA, 'seeds': rows, 'paired_gains': all_gains,
               'paired_losses': all_losses, 'net': all_gains - all_losses,
               'clean_sft': clean_before, 'clean_rl': clean_after,
               'updated_seeds': updated_seeds,
               'preregistered_initial_improvement_criterion_met': criterion,
               'slices': dict(sorted(slices.items()))}
    write_json(out, summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, default=ROOT / 'work')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.work.resolve(), args.out), ensure_ascii=False, indent=2))
