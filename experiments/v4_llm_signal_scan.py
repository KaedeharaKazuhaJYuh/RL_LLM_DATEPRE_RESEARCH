"""No-update GRPO signal audit on training tasks only.

Task selection is fixed before rollout sampling and never reads dev examples.
"""
import argparse
import json
import random
import tempfile
from pathlib import Path

import torch

from experiments.v4_llm_grpo import rollout, select_train_tasks
from research.io import ROOT, digest, write_json


def classify_group(members):
    """Separate outcome/process signal from reward differences due only to cost."""
    if len(members) < 2:
        raise ValueError('at least two rollouts are required')
    passed = {bool(row['passed']) for row in members}
    prefixes = {int(row['matched_prefix']) for row in members}
    rewards = {round(float(row['reward']), 8) for row in members}
    if len(passed) > 1:
        return 'outcome'
    if len(prefixes) > 1:
        return 'prefix'
    if len(rewards) > 1:
        return 'cost_only'
    return 'zero'


def selected_tasks(protocol, selection_seed):
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    families = {row['pair_family'] for row in tasks if row['split'] == 'train'}
    picked = select_train_tasks(tasks, len(families), selection_seed)
    if len(picked) != len(families) or {row['pair_family'] for row in picked} != families:
        raise ValueError('scan must cover every training family exactly once')
    return sorted(picked, key=lambda row: row['pair_family'])


def run(args):
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA GPU required for policy rollouts')
    if args.group_size < 2:
        raise ValueError('group size must be at least two')
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    out = Path(args.out)
    if out.exists():
        raise FileExistsError('new output directory required')
    out.mkdir(parents=True)
    protocol = Path(args.protocol)
    tasks = selected_tasks(protocol, args.selection_seed)
    oracle = json.loads((protocol / 'train_oracle.json').read_text(encoding='utf-8'))
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    policy = PeftModel.from_pretrained(
        AutoModelForCausalLM.from_pretrained(args.model, dtype=torch.bfloat16,
                                             trust_remote_code=False).cuda(),
        args.adapter, is_trainable=False)
    policy.eval()
    records = []
    with tempfile.TemporaryDirectory(prefix='v4_signal_scan_') as scratch:
        for task in tasks:
            for fault in (False, True):
                members = []
                for member in range(args.group_size):
                    folder = Path(scratch) / f'{task["task_id"]}_{int(fault)}_{member}'
                    reward, trajectory, score = rollout(
                        policy, tokenizer, task, oracle[task['task_id']], folder,
                        fault=fault, args=args)
                    members.append({'reward': reward,
                                    'passed': bool(score.get('passed')),
                                    'matched_prefix': int(score.get('matched_prefix', 0)),
                                    'progress': float(score.get('progress', 0.0)),
                                    'parse_error': bool(score.get('parse_error')),
                                    'tool_calls': score.get('tool_calls'),
                                    'decisions': score.get('decisions'),
                                    'actions': [step['action'] for step in trajectory]})
                record = {'task_id': task['task_id'], 'pair_family': task['pair_family'],
                          'fault': fault, 'signal': classify_group(members), 'members': members}
                records.append(record)
                print(f'family={task["pair_family"]} fault={fault} signal={record["signal"]}',
                      flush=True)
                # Persist completed groups so an interrupted scan remains auditable.
                write_json(out / 'partial.json', {'records': records})
    counts = {signal: sum(row['signal'] == signal for row in records)
              for signal in ('outcome', 'prefix', 'cost_only', 'zero')}
    summary = {'schema_version': 'v4-llm-signal-scan-1', 'method': 'train-only-no-update',
               'seed': args.seed, 'selection_seed': args.selection_seed,
               'model': args.model, 'adapter': args.adapter,
               'protocol_sha256': digest(protocol / 'manifest.json'),
               'adapter_sha256': {p.name: digest(p) for p in Path(args.adapter).glob('*.safetensors')},
               'group_size': args.group_size, 'temperature': args.temperature,
               'max_new_tokens': args.max_new_tokens,
               'tasks': len(tasks), 'groups': len(records), 'signal_counts': counts,
               'trainable_signal_groups': counts['outcome'] + counts['prefix'],
               'external_test': False, 'records': records}
    write_json(out / 'summary.json', summary)
    (out / 'partial.json').unlink()
    return {key: value for key, value in summary.items() if key != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', default=str(ROOT / 'tasks/v4/llm_hard_v1'))
    parser.add_argument('--model', default='work/modelscope_deepseek_r1_1p5b')
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--selection-seed', type=int, default=20260926)
    parser.add_argument('--group-size', type=int, default=4)
    parser.add_argument('--temperature', type=float, default=.9)
    parser.add_argument('--max-new-tokens', type=int, default=48)
    args = parser.parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))
