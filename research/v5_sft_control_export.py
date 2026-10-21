"""Export an expert SFT control on the frozen V5 beta RL training schedule."""

import argparse
import json
import tempfile
from pathlib import Path

from experiments.v4_llm_export import replay
from experiments.v4_llm_grpo import BudgetedGroupSchedule
from research.io import ROOT, append_jsonl, digest, write_json


def scheduled_groups(tasks, seed, count=16):
    schedule = BudgetedGroupSchedule(tasks, seed, 'schedule_static')
    return [schedule.next() for _ in range(count)]


def run(protocol, rl_summary_path, out):
    protocol, rl_summary_path, out = map(Path, (protocol, rl_summary_path, out))
    if out.exists():
        raise FileExistsError('new output directory required')
    manifest = json.loads((protocol / 'manifest.json').read_text(encoding='utf-8'))
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    oracle = json.loads((protocol / 'train_oracle.json').read_text(encoding='utf-8'))
    rl = json.loads(rl_summary_path.read_text(encoding='utf-8'))
    if (not manifest['train_only'] or manifest['dev_tasks'] or
            any(task['split'] != 'train' for task in tasks) or
            set(oracle) != {task['task_id'] for task in tasks}):
        raise ValueError('SFT control requires a train-only protocol')
    if (rl['protocol_sha256'] != digest(protocol / 'manifest.json') or
            rl['selection_mode'] != 'schedule_static' or rl['group_size'] != 4 or
            rl['episode_budget'] != 64 or rl['selected_groups'] != 16 or
            rl['seed'] not in (20260921, 20260922, 20260923)):
        raise ValueError('RL run does not match the frozen beta schedule')
    groups = scheduled_groups(tasks, rl['seed'])
    if [(task['task_id'], fault) for task, fault in groups] != [
            (row['task_id'], row['fault']) for row in rl['records']]:
        raise ValueError('RL run used a different task-condition schedule')

    out.mkdir(parents=True)
    steps = out / 'train_steps.jsonl'
    count = 0
    with tempfile.TemporaryDirectory(prefix='v5_sft_control_') as scratch:
        for group_index, (task, fault) in enumerate(groups):
            for member in range(4):
                folder = Path(scratch) / f'group_{group_index}_member_{member}'
                for row in replay(task, oracle[task['task_id']], folder, fault,
                                  collect=True):
                    row.update(group_index=group_index, member=member)
                    append_jsonl(steps, row)
                    count += 1
    summary = {
        'schema_version': 'v5-sft-control-export-1',
        'protocol_sha256': digest(protocol / 'manifest.json'),
        'rl_summary_sha256': digest(rl_summary_path),
        'seed': rl['seed'], 'train_sources': sorted({task['source_id'] for task, _ in groups}),
        'groups': [{'task_id': task['task_id'], 'fault': fault}
                   for task, fault in groups],
        'expert_episodes': 64, 'expert_decision_examples': count,
        'training_steps_sha256': digest(steps),
        'matched_rl_optimizer_steps': rl['updated_groups'] * rl['ppo_epochs'],
        'evaluation_labels_used': False,
    }
    write_json(out / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', default=str(ROOT / 'tasks/v5/beta_curriculum_v1'))
    parser.add_argument('--rl-summary', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.protocol, args.rl_summary, args.out),
                     ensure_ascii=False, indent=2))
