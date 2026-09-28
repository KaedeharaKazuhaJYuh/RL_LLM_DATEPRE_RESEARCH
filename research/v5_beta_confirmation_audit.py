"""Frozen paired audit for the second V5 beta source holdout."""
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from research.io import ROOT, digest, write_json
from research.v5_beta_audit import BASE_SHA, FAULTS, SEEDS, SFT_SHA, _indexed

PROTOCOL_SHA = 'e18137564a4234de0461b4623c927b4db5bf88cc894862d5610aa0844e64331c'
TRAIN_SHA = '15af9fde24ed0c8955f50db3fc0fe272540f4a4cbc32e961c9c4c065b88b88ff'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def run(work, out):
    protocol = ROOT / 'tasks/v5/beta_confirmation_v1'
    if digest(protocol / 'manifest.json') != PROTOCOL_SHA:
        raise ValueError('confirmation protocol changed')
    if digest(ROOT / 'work/modelscope_deepseek_r1_1p5b/model.safetensors') != BASE_SHA:
        raise ValueError('base weights changed')
    tasks = {task['task_id']: task for task in read(protocol / 'tasks.json')}
    curriculum = ROOT / 'tasks/v5/beta_curriculum_v1'
    if digest(curriculum / 'manifest.json') != TRAIN_SHA:
        raise ValueError('train curriculum changed')
    train_ids = {task['task_id'] for task in read(curriculum / 'tasks.json')}
    results = []
    paired_records = []
    gains = losses = clean_sft = clean_rl = 0
    slices = defaultdict(lambda: {'n': 0, 'sft': 0, 'rl': 0, 'gain': 0, 'loss': 0})
    for seed, expected_sft_sha in zip(SEEDS, SFT_SHA):
        sft_adapter = work / f'v4_llm_composition_sft100_seed{seed}/adapter'
        rl_dir = work / f'v5_beta1_curriculum_grpo_seed{seed}'
        rl_adapter = rl_dir / 'adapter'
        if digest(sft_adapter / 'adapter_model.safetensors') != expected_sft_sha:
            raise ValueError('SFT adapter changed')
        train = read(rl_dir / 'summary.json')
        checks = {'seed': seed, 'protocol_sha256': TRAIN_SHA, 'adapter_init':
                  sft_adapter.relative_to(ROOT).as_posix(), 'external_test': False,
                  'episodes': 64, 'selected_groups': 16, 'group_size': 4,
                  'ppo_epochs': 2, 'selection_mode': 'schedule_static',
                  'reward_mode': 'shaped', 'learning_rate': 2e-6,
                  'temperature': 0.9, 'clip_range': 0.2, 'kl_beta': 0.02}
        for key, expected in checks.items():
            if train.get(key) != expected:
                raise ValueError(f'training {seed} {key} differs from frozen recipe')
        if set(train['task_ids']) - train_ids:
            raise ValueError('non-training task entered RL update')
        rl_sha = digest(rl_adapter / 'adapter_model.safetensors')
        if train['adapter_sha256']['adapter_model.safetensors'] != rl_sha:
            raise ValueError('RL adapter hash differs from training summary')
        pair = []
        for label, adapter in (('sft', sft_adapter), ('rl', rl_adapter)):
            path = work / f'v5_beta1_confirmation_{label}_seed{seed}.json'
            evaluation = read(path)
            if evaluation.get('protocol_sha256') != PROTOCOL_SHA or Path(
                    evaluation['adapter']).resolve() != adapter.resolve():
                raise ValueError('evaluation used wrong protocol or adapter')
            pair.append((path, evaluation, _indexed(evaluation, tasks)))
        first, second = pair[0][2], pair[1][2]
        seed_gain = seed_loss = seed_clean_sft = seed_clean_rl = 0
        for (task_id, fault), before in first.items():
            after = second[(task_id, fault)]
            task = tasks[task_id]
            a, b = bool(before['passed']), bool(after['passed'])
            seed_gain += b and not a
            seed_loss += a and not b
            if fault == 'none':
                seed_clean_sft += a
                seed_clean_rl += b
            paired_records.append({'seed': seed, 'task_id': task_id,
                                   'source_id': task['source_id'],
                                   'pair_family': task['pair_family'],
                                   'paraphrase_id': task['paraphrase_id'],
                                   'fault_kind': fault, 'sft_passed': a, 'rl_passed': b,
                                   'sft_actions': [step['action'] for step in before['steps']],
                                   'rl_actions': [step['action'] for step in after['steps']]})
            for name in (f'source:{task["source_id"]}', f'language:{task["paraphrase_id"]}',
                         f'family:{task["pair_family"]}', f'fault:{fault}'):
                row = slices[name]
                row['n'] += 1
                row['sft'] += a
                row['rl'] += b
                row['gain'] += b and not a
                row['loss'] += a and not b
        gains += seed_gain
        losses += seed_loss
        clean_sft += seed_clean_sft
        clean_rl += seed_clean_rl
        results.append({'seed': seed, 'sft_passed': pair[0][1]['passed'],
                        'rl_passed': pair[1][1]['passed'], 'gain': seed_gain,
                        'loss': seed_loss, 'net': seed_gain - seed_loss,
                        'clean_sft': seed_clean_sft, 'clean_rl': seed_clean_rl,
                        'updated_groups': train['updated_groups'], 'training_episodes': 64,
                        'sft_adapter_sha256': expected_sft_sha,
                        'rl_adapter_sha256': rl_sha,
                        'sft_eval_sha256': digest(pair[0][0]),
                        'rl_eval_sha256': digest(pair[1][0])})
    criterion = (gains > losses and sum(r['net'] > 0 for r in results) >= 2 and
                 min(r['net'] for r in results) >= -2 and clean_rl >= clean_sft)
    # Exploratory uncertainty only: resample 12 tasks, preserving their seeds/faults.
    task_nets = defaultdict(int)
    for row in paired_records:
        task_nets[row['task_id']] += int(row['rl_passed']) - int(row['sft_passed'])
    rng = random.Random(20260928)
    values = [task_nets[key] for key in sorted(task_nets)]
    resamples = sorted(sum(rng.choices(values, k=len(values))) for _ in range(20000))
    output = {'schema_version': 'v5-beta1-confirmation-audit-1',
              'protocol_sha256': PROTOCOL_SHA, 'train_protocol_sha256': TRAIN_SHA,
              'base_sha256': BASE_SHA, 'seeds': results,
              'paired_gains': gains, 'paired_losses': losses, 'net': gains - losses,
              'clean_sft': clean_sft, 'clean_rl': clean_rl,
              'preregistered_initial_improvement_criterion_met': criterion,
              'exploratory_task_bootstrap_net_95pct': [resamples[499], resamples[19499]],
              'slices': dict(sorted(slices.items())),
              'paired_records': paired_records}
    write_json(out, output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', type=Path, default=ROOT / 'work')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.work.resolve(), args.out), ensure_ascii=False, indent=2))
