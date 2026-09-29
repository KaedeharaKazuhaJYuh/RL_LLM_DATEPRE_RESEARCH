"""Audit the V5 beta RL policy against a matched two-step SFT continuation."""

import argparse
import json
import random
import tempfile
from collections import defaultdict
from pathlib import Path

from research.io import ROOT, digest, write_json
from research.v5_beta_audit import BASE_SHA, SEEDS, SFT_SHA, _indexed
from research.v5_beta_confirmation_audit import PROTOCOL_SHA, TRAIN_SHA, run as rerun_beta


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def task_cluster_interval(rows, before, after):
    """Exploratory interval: resample tasks, keeping all seeds and faults together."""
    nets = defaultdict(int)
    for row in rows:
        nets[row['task_id']] += int(row[after]) - int(row[before])
    values = [nets[key] for key in sorted(nets)]
    rng = random.Random(20260929)
    draws = sorted(sum(rng.choices(values, k=len(values))) for _ in range(20000))
    return [draws[499], draws[19499]]


def run(work, out):
    work, out = Path(work).resolve(), Path(out)
    if out.exists():
        raise FileExistsError('new audit output required')
    protocol = ROOT / 'tasks/v5/beta_confirmation_v1'
    train_protocol = ROOT / 'tasks/v5/beta_curriculum_v1'
    if (digest(protocol / 'manifest.json') != PROTOCOL_SHA or
            digest(train_protocol / 'manifest.json') != TRAIN_SHA or
            digest(work / 'modelscope_deepseek_r1_1p5b/model.safetensors') != BASE_SHA):
        raise ValueError('frozen protocol or base weights changed')
    tasks = {task['task_id']: task for task in read(protocol / 'tasks.json')}
    confirm_sources = {task['source_id'] for task in tasks.values()}
    with tempfile.TemporaryDirectory(prefix='v5_beta_rerun_') as scratch:
        beta_path = Path(scratch) / 'beta.json'
        beta = rerun_beta(work, beta_path)
        frozen = ROOT / 'reports/v5_beta1_confirmation_paired_audit.json'
        if digest(beta_path) != digest(frozen):
            raise ValueError('beta paired audit no longer matches frozen record')

    baseline = {(row['seed'], row['task_id'], row['fault_kind']): row
                for row in beta['paired_records']}
    rows, seeds = [], []
    slices = defaultdict(lambda: {'n': 0, 'control': 0, 'rl': 0, 'gain': 0, 'loss': 0})
    for seed, init_sha in zip(SEEDS, SFT_SHA):
        export_dir = work / f'v5_0_05_sft_export_seed{seed}'
        train_dir = work / f'v5_0_05_sft_control_seed{seed}'
        eval_path = work / f'v5_0_05_sft_control_eval_seed{seed}.json'
        rl_summary = work / f'v5_beta1_curriculum_grpo_seed{seed}/summary.json'
        export, training, evaluation, rl = map(read, (
            export_dir / 'summary.json', train_dir / 'summary.json', eval_path, rl_summary))
        adapter = train_dir / 'adapter/adapter_model.safetensors'
        checks = (
            export['seed'] == training['seed'] == seed,
            export['protocol_sha256'] == TRAIN_SHA,
            export['rl_summary_sha256'] == digest(rl_summary),
            export['expert_episodes'] == 64,
            export['expert_decision_examples'] == training['examples'],
            export['training_steps_sha256'] == digest(export_dir / 'train_steps.jsonl')
            == training['training_steps_sha256'],
            export['matched_rl_optimizer_steps'] == training['max_steps']
            == rl['updated_groups'] * rl['ppo_epochs'],
            not export['evaluation_labels_used'],
            not (set(export['train_sources']) & confirm_sources),
            Path(training['adapter_init']).resolve() ==
            (work / f'v4_llm_composition_sft100_seed{seed}/adapter').resolve(),
            training['adapter_init_sha256']['adapter_model.safetensors'] == init_sha,
            training['local_base_weights_sha256']['model.safetensors'] == BASE_SHA,
            training['adapter_sha256']['adapter_model.safetensors'] == digest(adapter),
            evaluation['protocol_sha256'] == PROTOCOL_SHA,
            Path(evaluation['adapter']).resolve() == adapter.parent.resolve(),
        )
        if not all(checks):
            raise ValueError(f'SFT control provenance mismatch for seed {seed}: {checks}')
        indexed = _indexed(evaluation, tasks)
        gain = loss = 0
        for (task_id, fault), control in indexed.items():
            old = baseline[(seed, task_id, fault)]
            task = tasks[task_id]
            a, b = bool(control['passed']), old['rl_passed']
            gain += b and not a
            loss += a and not b
            row = {'seed': seed, 'task_id': task_id, 'source_id': task['source_id'],
                   'pair_family': task['pair_family'], 'paraphrase_id': task['paraphrase_id'],
                   'fault_kind': fault, 'initial_sft_passed': old['sft_passed'],
                   'control_passed': a, 'rl_passed': b,
                   'control_actions': [step['action'] for step in control['steps']],
                   'rl_actions': old['rl_actions']}
            rows.append(row)
            for name in (f"source:{task['source_id']}", f"family:{task['pair_family']}",
                         f'fault:{fault}'):
                item = slices[name]
                item['n'] += 1
                item['control'] += a
                item['rl'] += b
                item['gain'] += b and not a
                item['loss'] += a and not b
        seeds.append({'seed': seed, 'initial_sft_passed': next(
            item['sft_passed'] for item in beta['seeds'] if item['seed'] == seed),
            'control_passed': evaluation['passed'],
            'rl_passed': next(item['rl_passed'] for item in beta['seeds'] if item['seed'] == seed),
            'rl_minus_control_gain': gain, 'rl_minus_control_loss': loss,
            'rl_minus_control_net': gain - loss,
            'expert_episodes': 64, 'expert_decision_examples': training['examples'],
            'optimizer_steps': training['max_steps'],
            'export_sha256': digest(export_dir / 'summary.json'),
            'training_summary_sha256': digest(train_dir / 'summary.json'),
            'control_adapter_sha256': digest(adapter),
            'control_eval_sha256': digest(eval_path)})
    total_control = sum(item['control_passed'] for item in seeds)
    total_rl = sum(item['rl_passed'] for item in seeds)
    output = {'schema_version': 'v5-sft-control-audit-1',
              'confirmation_protocol_sha256': PROTOCOL_SHA,
              'training_protocol_sha256': TRAIN_SHA,
              'frozen_beta_audit_sha256': digest(frozen),
              'base_weights_sha256': BASE_SHA,
              'initial_sft_passed': sum(item['initial_sft_passed'] for item in seeds),
              'control_passed': total_control, 'rl_passed': total_rl,
              'rl_minus_control_net': total_rl - total_control,
              'exploratory_control_minus_initial_task_bootstrap_95pct':
                  task_cluster_interval(rows, 'initial_sft_passed', 'control_passed'),
              'exploratory_rl_minus_control_task_bootstrap_95pct':
                  task_cluster_interval(rows, 'control_passed', 'rl_passed'),
              'rl_exceeds_matched_sft_criterion': (total_rl > total_control and
                  sum(item['rl_passed'] >= item['control_passed'] for item in seeds) >= 2),
              'seeds': seeds, 'slices': dict(sorted(slices.items())),
              'paired_records': rows,
              'limitation': 'matched expert episodes and optimizer steps; not equal FLOPs or a new blind test'}
    write_json(out, output)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--work', default=str(ROOT / 'work'))
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    result = run(args.work, args.out)
    print(json.dumps({key: result[key] for key in (
        'initial_sft_passed', 'control_passed', 'rl_passed',
        'rl_minus_control_net', 'rl_exceeds_matched_sft_criterion')},
        ensure_ascii=False, indent=2))
