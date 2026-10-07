"""Audit the preregistered V5.0.10 baseline/SFT/RL paired evaluation."""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from research.io import ROOT, digest, write_json

SEEDS = (20260921, 20260922, 20260923)
MODES = ('none', 'transient_read', 'timeout', 'partial_write')
TRAIN_SHA = '10542a0ad8bdd4dffc921e45bc1a61b231e3f75f808644cb7fb850569f2d6fdf'
EVAL_SHA = '4b710398c260c306dab7231b7a8dfee14a986412785d5b8bbd589fa94cd919b0'
BASE_SHA = '58858233513d76b8703e72eed6ce16807b523328188e13329257fb9594462945'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def indexed_eval(path, adapter, tasks):
    data = read(path)
    if (data.get('protocol_sha256') != EVAL_SHA or data.get('episodes') != 24 or
            not data.get('adapter') or Path(data['adapter']).resolve() != adapter.resolve() or
            not data.get('greedy') or
            data.get('batch_size', 1) != 1 or data.get('fault_modes') != list(MODES)):
        raise ValueError(f'evaluation metadata mismatch: {path}')
    rows = {}
    for record in data['records']:
        task_id, mode = record['task_id'], record.get('fault_kind')
        key = (task_id, mode)
        if (task_id not in tasks or mode not in MODES or key in rows or
                record['source_id'] != tasks[task_id]['source_id'] or
                record['fault'] != (mode != 'none')):
            raise ValueError(f'invalid evaluation episode: {path} {key}')
        if (mode != 'none') != record.get('injection_applied'):
            raise ValueError(f'fault injection missing: {path} {key}')
        rows[key] = record
    expected = {(task_id, mode) for task_id in tasks for mode in MODES}
    if set(rows) != expected or data['passed'] != sum(bool(row['passed']) for row in rows.values()):
        raise ValueError(f'evaluation incomplete: {path}')
    return rows


def run(work=ROOT / 'work', out=ROOT / 'work/v5_0_10_model_audit.json'):
    work, out = Path(work), Path(out)
    if out.exists():
        raise FileExistsError('new audit output required')
    train = ROOT / 'tasks/v5/rewrite_train_v1'
    eval_protocol = ROOT / 'tasks/v5/rewrite_holdout_v1'
    if (digest(train / 'manifest.json') != TRAIN_SHA or
            digest(eval_protocol / 'manifest.json') != EVAL_SHA or
            digest(work / 'modelscope_deepseek_r1_1p5b/model.safetensors') != BASE_SHA):
        raise ValueError('frozen protocol or base weights changed')
    train_tasks = read(train / 'tasks.json')
    tasks = {task['task_id']: task for task in read(eval_protocol / 'tasks.json')}
    if (len(tasks) != 6 or any(task['source_id'] != 'uci_online_shoppers' for task in tasks) or
            {task['source_id'] for task in train_tasks} &
            {task['source_id'] for task in tasks}):
        raise ValueError('source isolation failed')
    experts = read(ROOT / 'reports/v5_0_10_expert_audit.json')
    if experts['protocol_sha256'] != EVAL_SHA or experts['passed'] != 24:
        raise ValueError('held-out expert validation failed')
    paired = []
    seed_rows = []
    slices = defaultdict(lambda: {'n': 0, 'baseline': 0, 'sft': 0, 'rl': 0})
    for seed in SEEDS:
        original_adapter = work / f'v5_0_05_sft_control_seed{seed}/adapter'
        rl_dir = work / f'v5_0_10_rl_seed{seed}'
        sft_dir = work / f'v5_0_10_sft_seed{seed}'
        export_dir = work / f'v5_0_10_sft_export_seed{seed}'
        initial_sha = digest(original_adapter / 'adapter_model.safetensors')
        rl = read(rl_dir / 'summary.json')
        sft = read(sft_dir / 'summary.json')
        export = read(export_dir / 'summary.json')
        checks = {'seed': seed, 'protocol_sha256': TRAIN_SHA,
                  'adapter_init': original_adapter.relative_to(ROOT).as_posix(),
                  'selection_mode': 'schedule_static', 'episode_budget': 64,
                  'selected_groups': 16, 'episodes': 64, 'group_size': 4,
                  'ppo_epochs': 2, 'reward_mode': 'shaped', 'temperature': 0.9,
                  'max_new_tokens': 48, 'learning_rate': 2e-6,
                  'clip_range': 0.2, 'kl_beta': 0.02, 'external_test': False}
        if any(rl.get(key) != value for key, value in checks.items()):
            raise ValueError(f'RL training recipe mismatch: {seed}')
        if (export['protocol_sha256'] != TRAIN_SHA or export['seed'] != seed or
                export['expert_episodes'] != 64 or
                [(row['task_id'], row['fault']) for row in rl['records']] !=
                [(row['task_id'], row['fault']) for row in export['groups']]):
            raise ValueError(f'SFT/RL group schedule mismatch: {seed}')
        if (sft['seed'] != seed or sft['adapter_init'] != checks['adapter_init'] or
                sft['adapter_init_sha256'].get('adapter_model.safetensors') != initial_sha or
                sft['max_steps'] != rl['updated_groups'] * 2 or
                sft['training_steps_sha256'] != export['training_steps_sha256'] or
                sft['examples'] != export['expert_decision_examples'] or
                sft['external_test'] or sft['model'] != rl['model']):
            raise ValueError(f'SFT training recipe mismatch: {seed}')
        adapters = {'baseline': original_adapter, 'sft': sft_dir / 'adapter',
                    'rl': rl_dir / 'adapter'}
        results, hashes = {}, {}
        for label, adapter in adapters.items():
            path = work / f'v5_0_10_eval_{label}_seed{seed}.json'
            results[label] = indexed_eval(path, adapter, tasks)
            hashes[f'{label}_eval_sha256'] = digest(path)
            hashes[f'{label}_adapter_sha256'] = digest(adapter / 'adapter_model.safetensors')
        if (hashes['sft_adapter_sha256'] != sft['adapter_sha256']['adapter_model.safetensors'] or
                hashes['rl_adapter_sha256'] != rl['adapter_sha256']['adapter_model.safetensors']):
            raise ValueError(f'trained adapter hash mismatch: {seed}')
        counts = {label: sum(bool(row['passed']) for row in result.values())
                  for label, result in results.items()}
        for task_id, mode in sorted(results['baseline']):
            task = tasks[task_id]
            outcome = {label: bool(results[label][task_id, mode]['passed'])
                       for label in adapters}
            actions = {f'{label}_actions': [step['action'] for step in
                       results[label][task_id, mode]['steps']] for label in adapters}
            paired.append({'seed': seed, 'task_id': task_id, 'fault_kind': mode,
                           'pair_family': task['pair_family'],
                           'language': 'zh' if task['paraphrase_id'] == 0 else 'en',
                           **outcome, **actions})
            for key in (f'family:{task["pair_family"]}',
                        f'language:{"zh" if task["paraphrase_id"] == 0 else "en"}',
                        f'fault:{mode}'):
                for label in adapters:
                    slices[key][label] += int(outcome[label])
                slices[key]['n'] += 1
        seed_rows.append({'seed': seed, **counts, 'rl_minus_sft': counts['rl'] - counts['sft'],
                          'rl_updated_groups': rl['updated_groups'],
                          'sft_optimization_steps': sft['max_steps'],
                          'expert_decision_examples': export['expert_decision_examples'],
                          'export_sha256': digest(export_dir / 'summary.json'),
                          **hashes})
    totals = {label: sum(row[label] for row in seed_rows) for label in ('baseline', 'sft', 'rl')}
    gains = sum(row['rl'] and not row['sft'] for row in paired)
    losses = sum(row['sft'] and not row['rl'] for row in paired)
    clean = slices['fault:none']
    criterion = (totals['rl'] > totals['sft'] and
                 sum(row['rl_minus_sft'] >= 0 for row in seed_rows) >= 2 and
                 min(row['rl_minus_sft'] for row in seed_rows) >= -2 and
                 clean['rl'] >= clean['sft'])
    report = {'schema_version': 'v5-0-10-model-audit-1',
              'train_protocol_sha256': TRAIN_SHA, 'eval_protocol_sha256': EVAL_SHA,
              'base_sha256': BASE_SHA, 'episodes_per_method': len(paired),
              'seeds': seed_rows, 'totals': totals, 'rl_vs_sft_gain': gains,
              'rl_vs_sft_loss': losses,
              'preregistered_rl_better_than_matched_sft': criterion,
              'slices': dict(sorted(slices.items())), 'paired_records': paired}
    write_json(out, report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT / 'work')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.work, args.out)
    print(json.dumps({k: report[k] for k in ('totals', 'rl_vs_sft_gain',
                    'rl_vs_sft_loss', 'preregistered_rl_better_than_matched_sft')},
                     ensure_ascii=False, indent=2))
