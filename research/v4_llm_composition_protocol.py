"""Extend the hard protocol with train-only three-step combinations."""
import copy
import hashlib
import json
from pathlib import Path

from research.io import ROOT, digest, write_json


VERSION = 'v4-llm-composition-1'
PARENT = ROOT / 'tasks/v4/llm_hard_v1'
FAMILIES = (
    (('fill_missing', 'deduplicate', 'describe_numeric'),
     '先用中位数补齐 {value}，再删除完全重复记录，最后报告处理后该列的描述统计。'),
    (('clip_outliers', 'fill_missing', 'correlate'),
     '先将 {value} 截断到 [0,100]，再用中位数补齐空值，最后计算它与 {metric} 的相关系数。'),
    (('normalize_dates', 'clip_outliers', 'aggregate'),
     '先将 {date} 规范为 YYYY-MM-DD，再把 {value} 截断到 [0,100]，最后按规范后的日期汇总数值。'),
    (('normalize_categories', 'clip_outliers', 'count_categories'),
     '先规范 {category} 的空格与大小写，再将 {value} 截断到 [0,100]，最后统计处理后的类别频数。'),
)


def build(out=None, parent=PARENT):
    out = Path(out or ROOT / 'tasks/v4/llm_composition_v1').resolve()
    parent = Path(parent).resolve()
    if out.exists():
        raise FileExistsError('new output directory required')
    if not out.is_relative_to(ROOT):
        raise ValueError('output must be inside repository')
    old_tasks = json.loads((parent / 'tasks.json').read_text(encoding='utf-8'))
    train_oracle = json.loads((parent / 'train_oracle.json').read_text(encoding='utf-8'))
    dev_oracle = json.loads((parent / 'dev_oracle.json').read_text(encoding='utf-8'))
    parent_manifest = json.loads((parent / 'manifest.json').read_text(encoding='utf-8'))
    previous = {tuple(row['plan']) for row in train_oracle.values()}
    held_out = {tuple(row['plan']) for row in dev_oracle.values()} - previous
    additions = {tuple(plan) for plan, _ in FAMILIES}
    if len(additions) != len(FAMILIES) or additions & (previous | held_out):
        raise ValueError('new train triples must differ from old train and held-out dev triples')
    tasks = copy.deepcopy(old_tasks)
    by_source = {}
    for task in old_tasks:
        if task['split'] == 'train':
            by_source.setdefault(task['source_id'], task)
    next_family = max(task['pair_family'] for task in old_tasks if task['split'] == 'train') + 1
    for source_id, base in sorted(by_source.items()):
        params = base['params']
        names = {'value': params['column'], 'category': params['category_column'],
                 'date': params['date_column'], 'metric': params['other_column']}
        for offset, (plan, wording) in enumerate(FAMILIES):
            task = copy.deepcopy(base)
            task_id = hashlib.sha256(f'{VERSION}/{source_id}/{offset}'.encode()).hexdigest()[:16]
            task.update(schema_version=VERSION, task_id=task_id,
                        pair_family=next_family + offset,
                        composition_novelty='train_added_triple',
                        prompt=wording.format(**names) +
                        ' 严格按顺序完成；成功后选择 stop，不做额外操作。')
            tasks.append(task)
            train_oracle[task_id] = {'plan': list(plan)}
    train = [task for task in tasks if task['split'] == 'train']
    dev = [task for task in tasks if task['split'] == 'dev']
    if len({task['task_id'] for task in tasks}) != len(tasks):
        raise ValueError('duplicate task id')
    if {task['task_id'] for task in train} != set(train_oracle):
        raise ValueError('train oracle mismatch')
    if {task['task_id'] for task in dev} != set(dev_oracle):
        raise ValueError('dev oracle mismatch')
    if {tuple(row['plan']) for row in train_oracle.values()} & held_out:
        raise ValueError('held-out dev triple leaked into train')
    if {task['source_id'] for task in train} & {task['source_id'] for task in dev}:
        raise ValueError('train/dev source overlap')
    out.mkdir(parents=True)
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', train_oracle)
    write_json(out / 'dev_oracle.json', dev_oracle)
    manifest = {'version': VERSION, 'parent_version': parent_manifest['version'],
                'parent_manifest_sha256': digest(parent / 'manifest.json'),
                'synthetic': True, 'external_test': False,
                'train_sources': sorted(by_source),
                'dev_sources': sorted({task['source_id'] for task in dev}),
                'train_tasks': len(train), 'dev_tasks': len(dev),
                'added_train_families': [list(plan) for plan, _ in FAMILIES],
                'held_out_dev_families': [list(plan) for plan in sorted(held_out)],
                'dev_oracle_sha256': digest(out / 'dev_oracle.json'),
                'parent_dev_oracle_sha256': digest(parent / 'dev_oracle.json'),
                'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
