"""Fresh synthetic source/pair splits for the first trainable V4 LLM pilot."""
import hashlib
import json
import random
from pathlib import Path

from agent.tools import ACTIONS
from research.io import ROOT, digest, write_json, write_table
from research.v4_sequence_env import SPECS
from experiments.v4_sequence_composition import PROBES

VERSION = 'v4-llm-pilot-1'
SEED = 20260917
TRAIN_FAMILIES = tuple(SPECS) + tuple(PROBES[:2])
NOVEL_DEV_FAMILIES = tuple(PROBES[2:])
SCHEMAS = (
    ('period', 'region', 'amount', 'segment', 'signal'),
    ('日期', '地区', '销售额', '客群', '观测值'),
    ('when', 'zone', 'net_value', 'class_name', 'measure'),
    ('月份', '区域', '收入', '渠道', '指标'),
)


def _source(index, out):
    rng = random.Random(SEED + index * 101)
    date, region, value, category, metric = SCHEMAS[index % len(SCHEMAS)]
    columns = [date, region, value, category, metric]
    rows = []
    for i in range(15 + index % 6):
        amount = round(rng.uniform(10, 90), 2)
        rows.append({date: f'2026-{i % 6 + 1:02d}', region: ('N' if i % 2 else 'S'),
                     value: str(amount), category: (' a ' if i % 3 == 0 else 'B'),
                     metric: str(round(amount * .6 + rng.uniform(-4, 4), 2))})
    rows[2][value] = ''
    rows[4][date] = 'bad-date'
    rows[8][value] = str(180 + index)
    rows.append(dict(rows[0]))
    path = out / 'data' / f'source_{index:02d}.csv'
    write_table(path, columns, rows)
    uri = path.relative_to(ROOT).as_posix()
    params = {'column': value, 'category_column': category, 'date_column': date,
              'other_column': metric, 'lower': 0, 'upper': 100, 'window': 3}
    return {'uri': uri, 'columns': columns, 'sha256': digest(path)}, params


def build(out=None):
    out = Path(out or ROOT / 'tasks/v4/llm_pilot_v1').resolve()
    if out.exists():
        raise FileExistsError('new output directory required')
    if not out.is_relative_to(ROOT):
        raise ValueError('dataset output must be inside repository for stable URIs')
    out.mkdir(parents=True)
    tasks, train_oracle, dev_oracle = [], {}, {}
    for index in range(20):
        source_id = f'v4pilot_source_{index:02d}'
        split = 'train' if index < 16 else 'dev'
        dataset, params = _source(index, out)
        names = {'value': params['column'], 'category': params['category_column'],
                 'date': params['date_column'], 'metric': params['other_column']}
        families = list(TRAIN_FAMILIES)
        if split == 'dev':
            families += list(NOVEL_DEV_FAMILIES)
        for family_index, (plan, wording) in enumerate(families):
            novelty = 'seen_pair' if family_index < len(TRAIN_FAMILIES) else 'unseen_pair'
            task_id = hashlib.sha256(f'{VERSION}/{source_id}/{family_index}'.encode()).hexdigest()[:16]
            prompt = wording.format(**names) + ' 完成后必须选择 stop，不进行额外清理。'
            task = {'schema_version': VERSION, 'task_id': task_id, 'source_id': source_id,
                    'split': split, 'pair_family': family_index, 'composition_novelty': novelty,
                    'prompt': prompt, 'dataset': dataset, 'params': params,
                    'allowed_tools': ACTIONS, 'constraints': {'max_steps': 4,
                    'max_tool_calls': 3, 'max_seconds': 120}}
            tasks.append(task)
            (train_oracle if split == 'train' else dev_oracle)[task_id] = {'plan': list(plan)}
    train_sources = {t['source_id'] for t in tasks if t['split'] == 'train'}
    dev_sources = {t['source_id'] for t in tasks if t['split'] == 'dev'}
    train_pairs = {tuple(x['plan']) for x in train_oracle.values()}
    novel_pairs = {tuple(dev_oracle[t['task_id']]['plan']) for t in tasks if t['composition_novelty'] == 'unseen_pair'}
    assert not train_sources & dev_sources
    assert not train_pairs & novel_pairs
    assert len({t['dataset']['sha256'] for t in tasks}) == 20
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', train_oracle)
    write_json(out / 'dev_oracle.json', dev_oracle)
    manifest = {'version': VERSION, 'seed': SEED, 'synthetic': True, 'external_test': False,
                'training_sources': sorted(train_sources), 'dev_sources': sorted(dev_sources),
                'train_task_count': len(train_oracle), 'dev_seen_pair_tasks': 4 * len(TRAIN_FAMILIES),
                'dev_unseen_pair_tasks': 4 * len(NOVEL_DEV_FAMILIES),
                'train_pair_families': [list(p) for p in sorted(train_pairs)],
                'unseen_dev_pair_families': [list(p) for p in sorted(novel_pairs)],
                'max_decisions': 4, 'max_tool_calls': 3,
                'success': 'explicit stop + independent oracle answer/table + unchanged input',
                'reward': 'success - 0.05*tool_calls - 0.01*decisions',
                'fault': 'first tool call transient read failure; retry allowed',
                'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return tasks, train_oracle, dev_oracle


if __name__ == '__main__':
    tasks, train, dev = build()
    print(json.dumps({'tasks': len(tasks), 'train': len(train), 'dev': len(dev)}, indent=2))
