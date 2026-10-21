"""Export expert episodes on the exact static V5.0.10 RL condition schedule."""
import argparse
import json
import tempfile
from pathlib import Path

from experiments.v4_llm_export import replay
from experiments.v4_llm_grpo import BudgetedGroupSchedule
from research.io import ROOT, append_jsonl, digest, write_json


def run(protocol, seed, out):
    protocol, out = Path(protocol), Path(out)
    if out.exists():
        raise FileExistsError('new output directory required')
    if seed not in (20260921, 20260922, 20260923):
        raise ValueError('seed outside preregistered set')
    manifest = json.loads((protocol / 'manifest.json').read_text(encoding='utf-8'))
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    oracle = json.loads((protocol / 'train_oracle.json').read_text(encoding='utf-8'))
    if (not manifest['train_only'] or len(tasks) != 96 or
            set(oracle) != {task['task_id'] for task in tasks} or
            any(task['split'] != 'train' for task in tasks)):
        raise ValueError('expected frozen train-only rewrite protocol')
    schedule = BudgetedGroupSchedule(tasks, seed, 'schedule_static')
    groups = [schedule.next() for _ in range(16)]
    out.mkdir(parents=True)
    steps = out / 'train_steps.jsonl'
    count = 0
    with tempfile.TemporaryDirectory(prefix='v5_0_10_sft_export_') as scratch:
        for index, (task, fault) in enumerate(groups):
            for member in range(4):
                folder = Path(scratch) / f'group_{index}_member_{member}'
                for row in replay(task, oracle[task['task_id']], folder, fault, True):
                    row.update(group_index=index, member=member)
                    append_jsonl(steps, row)
                    count += 1
    summary = {'schema_version': 'v5-0-10-sft-export-1',
               'protocol_sha256': digest(protocol / 'manifest.json'),
               'seed': seed, 'expert_episodes': 64, 'expert_decision_examples': count,
               'groups': [{'task_id': task['task_id'], 'fault': fault}
                          for task, fault in groups],
               'train_sources': sorted({task['source_id'] for task, _ in groups}),
               'training_steps_sha256': digest(steps), 'evaluation_labels_used': False}
    write_json(out / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=ROOT / 'tasks/v5/rewrite_train_v1')
    parser.add_argument('--seed', type=int, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.protocol, args.seed, args.out), ensure_ascii=False, indent=2))
