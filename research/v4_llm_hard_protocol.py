"""Build three-step V4 tasks intended to expose non-zero GRPO reward variance."""
import hashlib
import json
import random
from pathlib import Path

from agent.tools import ACTIONS
from research.io import ROOT, digest, write_json, write_table


VERSION = 'v4-llm-hard-1'
SEED = 20260921
SCHEMAS = (
    ('period', 'region', 'amount', 'segment', 'signal'),
    ('日期', '地区', '销售额', '客群', '观测值'),
    ('when', 'zone', 'net_value', 'class_name', 'measure'),
    ('月份', '区域', '收入', '渠道', '指标'),
)

# Every family is order-sensitive under final-table and final-answer verification.
TRAIN_FAMILIES = (
    (('deduplicate', 'fill_missing', 'describe_numeric'),
     '先删除完全重复记录，再用中位数补齐 {value}，最后报告处理后该列的描述统计。'),
    (('normalize_categories', 'deduplicate', 'count_categories'),
     '先规范 {category} 的空格和大小写，再删除规范化后形成的重复记录，最后统计类别频数。'),
    (('normalize_dates', 'fill_missing', 'aggregate'),
     '依次规范 {date}、用中位数补齐 {value}，再按规范后的日期汇总该数值列。'),
    (('fill_missing', 'clip_outliers', 'correlate'),
     '先补齐 {value} 的缺失值，再将其截断至 [0,100]，最后计算它与 {metric} 的相关系数。'),
    (('deduplicate', 'normalize_dates', 'profile_missingness'),
     '删除重复行后规范 {date}，然后报告最终表所有列的缺失率。'),
    (('normalize_dates', 'deduplicate', 'rolling_mean'),
     '先规范 {date}，再删除由规范化产生的重复行，最后计算 {metric} 的三期完整窗口移动平均。'),
    (('normalize_categories', 'fill_missing', 'aggregate'),
     '先规范 {category}，再补齐 {value}，最后按 {date} 汇总处理后的数值。'),
    (('clip_outliers', 'deduplicate', 'describe_numeric'),
     '先截断 {value} 到 [0,100]，再删除完全重复记录，最后给出处理后数值列的描述统计。'),
)

UNSEEN_DEV_FAMILIES = (
    (('deduplicate', 'clip_outliers', 'correlate'),
     '删除重复记录，随后截断 {value} 到 [0,100]，最后计算它与 {metric} 的相关系数。'),
    (('fill_missing', 'normalize_dates', 'aggregate'),
     '补齐 {value} 后规范 {date}，最后按规范日期汇总数值。'),
    (('normalize_categories', 'normalize_dates', 'count_categories'),
     '规范 {category}，再规范 {date}，最后统计处理后类别频数。'),
    (('deduplicate', 'fill_missing', 'rolling_mean'),
     '删除重复行并补齐 {value}，最后按当前行序计算 {metric} 的三期移动平均。'),
)


def _source(index, out):
    rng = random.Random(SEED + index * 137)
    date, region, value, category, metric = SCHEMAS[index % len(SCHEMAS)]
    columns = [date, region, value, category, metric]
    rows = []
    for i in range(20 + index % 5):
        amount = round(rng.uniform(8, 94), 2)
        rows.append({date: f'2026-{i % 7 + 1:02d}', region: ('E' if i % 2 else 'W'),
                     value: str(amount), category: (' a ' if i % 4 == 0 else ('A' if i % 4 == 1 else 'B')),
                     metric: str(round(amount * .55 + rng.uniform(-7, 7), 2))})
    rows[2][value] = ''
    rows[5][date] = 'invalid-date'
    rows[9][value] = str(165 + index)
    # One exact duplicate and one pair that only becomes duplicate after normalization.
    rows.append(dict(rows[0]))
    normalized_duplicate = dict(rows[1])
    normalized_duplicate[category] = f' {rows[1][category].lower()} '
    rows.append(normalized_duplicate)
    path = out / 'data' / f'source_{index:02d}.csv'
    write_table(path, columns, rows)
    return ({'uri': path.relative_to(ROOT).as_posix(), 'columns': columns, 'sha256': digest(path)},
            {'column': value, 'category_column': category, 'date_column': date,
             'other_column': metric, 'lower': 0, 'upper': 100, 'window': 3})


def build(out=None):
    out = Path(out or ROOT / 'tasks/v4/llm_hard_v1').resolve()
    if out.exists():
        raise FileExistsError('new output directory required')
    if not out.is_relative_to(ROOT):
        raise ValueError('dataset output must be inside repository for stable URIs')
    out.mkdir(parents=True)
    tasks, train_oracle, dev_oracle = [], {}, {}
    for index in range(20):
        source_id = f'v4hard_source_{index:02d}'
        split = 'train' if index < 16 else 'dev'
        dataset, params = _source(index, out)
        names = {'value': params['column'], 'category': params['category_column'],
                 'date': params['date_column'], 'metric': params['other_column']}
        families = list(TRAIN_FAMILIES)
        if split == 'dev':
            families += list(UNSEEN_DEV_FAMILIES)
        for family_index, (plan, wording) in enumerate(families):
            novelty = 'seen_triple' if family_index < len(TRAIN_FAMILIES) else 'unseen_triple'
            task_id = hashlib.sha256(f'{VERSION}/{source_id}/{family_index}'.encode()).hexdigest()[:16]
            task = {'schema_version': VERSION, 'task_id': task_id, 'source_id': source_id,
                    'split': split, 'pair_family': family_index, 'composition_novelty': novelty,
                    'prompt': wording.format(**names) + ' 严格按顺序完成；成功后选择 stop，不做额外操作。',
                    'dataset': dataset, 'params': params, 'allowed_tools': ACTIONS,
                    'reward': {'success': 1.0, 'progress': 0.3,
                               'tool_call_cost': 0.05, 'decision_cost': 0.01},
                    'constraints': {'max_steps': 5, 'max_tool_calls': 4, 'max_seconds': 120}}
            tasks.append(task)
            (train_oracle if split == 'train' else dev_oracle)[task_id] = {'plan': list(plan)}
    train_sources = {t['source_id'] for t in tasks if t['split'] == 'train'}
    dev_sources = {t['source_id'] for t in tasks if t['split'] == 'dev'}
    train_triples = {tuple(v['plan']) for v in train_oracle.values()}
    unseen_triples = {tuple(dev_oracle[t['task_id']]['plan']) for t in tasks
                      if t['composition_novelty'] == 'unseen_triple'}
    assert not train_sources & dev_sources
    assert not train_triples & unseen_triples
    assert len({t['dataset']['sha256'] for t in tasks}) == 20
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', train_oracle)
    write_json(out / 'dev_oracle.json', dev_oracle)
    manifest = {'version': VERSION, 'seed': SEED, 'synthetic': True, 'external_test': False,
                'purpose': 'development protocol for non-zero online-RL reward variance',
                'training_sources': sorted(train_sources), 'dev_sources': sorted(dev_sources),
                'train_task_count': len(train_oracle),
                'dev_seen_triple_tasks': 4 * len(TRAIN_FAMILIES),
                'dev_unseen_triple_tasks': 4 * len(UNSEEN_DEV_FAMILIES),
                'train_triple_families': [list(p) for p in sorted(train_triples)],
                'unseen_dev_triple_families': [list(p) for p in sorted(unseen_triples)],
                'max_decisions': 5, 'max_tool_calls': 4,
                'success': 'ordered three-tool completion + explicit stop + independent final verification',
                'reward': 'success + 0.3*correct_prefix_fraction - 0.05*tool_calls - 0.01*decisions',
                'fault': 'first tool call transient read failure; one retry fits the budget',
                'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return tasks, train_oracle, dev_oracle


if __name__ == '__main__':
    tasks, train, dev = build()
    print(json.dumps({'tasks': len(tasks), 'train': len(train), 'dev': len(dev)}, indent=2))
