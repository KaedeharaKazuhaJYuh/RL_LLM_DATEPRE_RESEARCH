"""Frozen-policy development probe: unseen two-tool combinations and wording."""
import argparse
import copy
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np

from experiments.v4_sequence_stochastic import METHODS, checkpoint
from experiments.v4_sequence_train import rollout
from research.io import ROOT, write_json
from research.v4_sequence_env import SequenceEnv
from research.v4_sequence_policy import SequencePolicy


# None of these ordered pairs occurs in v4-sequence-1 training.
PROBES = (
    (('fill_missing', 'aggregate'), '先用中位数补齐 {value} 的空值并保存，再按 {date} 分组求 {value} 总和，空日期保留为一组。'),
    (('clip_outliers', 'describe_numeric'), '先把 {value} 的数值截断至 [0,100] 并保存，再报告处理后该列的计数、最小值、最大值与均值。'),
    (('deduplicate', 'correlate'), '先删去完全相同的记录并保存，再计算 {value} 与 {metric} 在完整数值对上的皮尔逊相关系数。'),
    (('normalize_categories', 'profile_missingness'), '先修整 {category}：去首尾空格并转为大写，保存后给出所有列的空值比例。'),
    (('normalize_dates', 'profile_schema'), '先把 {date} 统一为 YYYY-MM-DD，无法解析的日期置空并保存，再报告列名和总行数。'),
    (('fill_missing', 'count_categories'), '先用中位数填补 {value} 的空值并保存，然后精确统计 {category} 的各类别频数。'),
)


def build(original, out):
    original, out = Path(original), Path(out)
    prior = json.loads((original / 'protocol/tasks.json').read_text(encoding='utf-8'))
    old_gold = json.loads((original / 'protocol/oracle.json').read_text(encoding='utf-8'))
    train_pairs = {tuple(old_gold[t['task_id']]['plan']) for t in prior if t['split'] == 'train'}
    assert all(pair not in train_pairs for pair, _ in PROBES)
    sources = sorted({t['source_id'] for t in prior if t['split'] == 'validation'})
    tasks, gold = [], {}
    for source in sources:
        base = next(t for t in prior if t['source_id'] == source)
        for index, (pair, wording) in enumerate(PROBES):
            task = copy.deepcopy(base)
            p = task['params']
            tid = hashlib.sha256(f'v4-composition-dev-1/{source}/{index}'.encode()).hexdigest()[:16]
            task.update(task_id=tid, split='composition_dev', template_id=f'composition_{index}',
                        prompt=wording.format(value=p['column'], date=p['date_column'],
                                              metric=p['other_column'], category=p['category_column'])
                               + ' 完成要求后选择 stop，不做额外清理。',
                        constraints={'max_steps': 4, 'max_tool_calls': 3, 'max_seconds': 120})
            tasks.append(task)
            gold[tid] = {'plan': list(pair)}
    out.mkdir(parents=True)
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'oracle.json', gold)
    write_json(out / 'protocol.json', {'version': 'v4-composition-dev-1',
        'purpose': 'development probe, not blind test', 'held_out_ordered_pairs': True,
        'source_independence': 'same two V4 validation sources, no new external sources',
        'parameter_mode': 'identical public deterministic bindings',
        'tool_budget': 3, 'decision_budget': 4, 'fault': 'one first-read failure'})
    return tasks, gold


def run(out, original, stable, seeds=(1, 2, 3)):
    out, original, stable = Path(out), Path(original), Path(stable)
    if out.exists():
        raise FileExistsError('new output directory required')
    tasks, gold = build(original, out / 'protocol')
    records = []
    with tempfile.TemporaryDirectory(prefix='v4_compose_') as scratch:
        for task in tasks:
            for fault in (False, True):
                env = SequenceEnv(task, gold[task['task_id']], scratch, fault)
                for action in ([gold[task['task_id']]['plan'][0]] if not fault else
                               [gold[task['task_id']]['plan'][0]] * 2):
                    env.step(action)
                env.step(gold[task['task_id']]['plan'][1])
                env.step('stop')
                if not env.result()['passed']:
                    raise AssertionError(f'expert trajectory failed {task["task_id"]}, fault={fault}')
        for seed in seeds:
            for method in METHODS:
                policy = SequencePolicy(seed)
                policy.weights = checkpoint(method, seed, original, stable)
                frozen = policy.fingerprint()
                for task in tasks:
                    for fault in (False, True):
                        result, _, steps = rollout(policy, task, gold[task['task_id']], scratch, fault)
                        records.append({'seed': seed, 'method': method, 'task_id': task['task_id'],
                                        'source_id': task['source_id'], 'template_id': task['template_id'],
                                        'fault': fault, 'actions': [s['action'] for s in steps], **result})
                assert frozen == policy.fingerprint()
    groups = []
    for method in METHODS:
        rows = [r for r in records if r['method'] == method]
        groups.append({'method': method, 'episodes': len(rows), 'passed': sum(r['passed'] for r in rows),
                       'pass_rate': float(np.mean([r['passed'] for r in rows])),
                       'mean_reward': float(np.mean([r['reward'] for r in rows]))})
    summary = {'protocol': 'v4-composition-dev-1', 'seeds': list(seeds), 'groups': groups,
               'tasks': len(tasks), 'independent_sources': 2, 'external_test': False,
               'checkpoint_selection': 'frozen from prior work; no tuning on this probe'}
    write_json(out / 'records.json', records)
    write_json(out / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    parser.add_argument('--original', default=str(ROOT / 'work/v4_sequence_train_001'))
    parser.add_argument('--stable', default=str(ROOT / 'work/v4_sequence_stable_001'))
    args = parser.parse_args()
    print(json.dumps(run(args.out, args.original, args.stable)['groups'], ensure_ascii=False, indent=2))
