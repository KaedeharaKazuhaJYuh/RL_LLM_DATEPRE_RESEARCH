"""Freeze a small, attributed public-CSV diagnostic for the V4 LLM agent."""
import hashlib
import json
import shutil
from pathlib import Path

from agent.tools import ACTIONS
from research.io import ROOT, digest, read_table, write_json

VERSION = 'v4-real-csv-1'
PARENT = ROOT / 'tasks/v3_real'
SOURCES = ('wine', 'abalone', 'wholesale')
PLANS = (
    ('deduplicate', 'rolling_mean'),
    ('normalize_categories', 'count_categories'),
    ('clip_outliers', 'describe_numeric'),
)
PROMPTS = (
    (
        '先删除完全重复的记录，再按当前行序计算 {metric} 列的三期完整窗口移动平均。最后选择 stop。',
        'Remove exact duplicate rows, then report the three-observation rolling mean of {metric} in row order. Stop when done.',
    ),
    (
        '先把 {category} 列去除首尾空格并统一为大写，再统计该列每个取值的频数。最后选择 stop。',
        'Canonicalize {category} by trimming and uppercasing it, then count each category. Stop when done.',
    ),
    (
        '先把 {value} 列数值截断到 [0,100] 并保存，再给出该列的数值描述统计。最后选择 stop。',
        'Clip {value} to the inclusive range [0,100], persist it, and describe that numeric column. Stop when done.',
    ),
)


def build(out=None):
    out = Path(out or ROOT / 'tasks/v4/real_csv_v1').resolve()
    if out.exists():
        raise FileExistsError('new output directory required')
    if not out.is_relative_to(ROOT):
        raise ValueError('output must be inside repository for stable URIs')
    parent = json.loads((PARENT / 'manifest.json').read_text(encoding='utf-8'))
    out.mkdir(parents=True)
    tasks, oracle, sources = [], {}, {}
    for name in SOURCES:
        source = parent['sources'][name]
        if source['license'] != 'CC BY 4.0':
            raise ValueError('source license is not approved')
        original = PARENT / 'data' / f'{name}.csv'
        if digest(original) != source['derived_sha256']:
            raise ValueError(f'{name} source hash mismatch')
        target = out / 'data' / f'{name}.csv'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, target)
        columns, rows = read_table(target)
        if not rows or columns != source['columns']:
            raise ValueError(f'{name} source schema mismatch')
        source_id = f'uci_{name}'
        dataset = {'uri': target.relative_to(ROOT).as_posix(), 'columns': columns,
                   'sha256': digest(target)}
        params = {'column': source['value'], 'category_column': source['category'],
                  'date_column': source['category'],
                  'other_column': source['metric'], 'lower': 0, 'upper': 100,
                  'window': 3}
        sources[name] = {'source_id': source_id, 'rows': len(rows), 'sha256': dataset['sha256'],
                         'archive_sha256': source['sha256'], 'upstream_url': source['url'],
                         'doi': source['doi'], 'license': source['license'],
                         'derived_from': original.relative_to(ROOT).as_posix(),
                         'personal_data_columns': []}
        for family, plan in enumerate(PLANS):
            for paraphrase, template in enumerate(PROMPTS[family]):
                task_id = hashlib.sha256(
                    f'{VERSION}/{name}/{family}/{paraphrase}'.encode()).hexdigest()[:16]
                prompt = template.format(value=params['column'],
                                         metric=params['other_column'],
                                         category=params['category_column'])
                task = {'schema_version': VERSION, 'task_id': task_id,
                        'source_id': source_id, 'split': 'dev',
                        'pair_family': family, 'paraphrase_id': paraphrase,
                        'composition_novelty': 'public_real_source',
                        'prompt': prompt, 'dataset': dataset, 'params': params,
                        'allowed_tools': ACTIONS, 'constraints': {'max_steps': 4,
                        'max_tool_calls': 3, 'max_seconds': 120, 'isolated_tools': True,
                        'tool_timeout_seconds': 10}}
                tasks.append(task)
                oracle[task_id] = {'plan': list(plan)}
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', {})
    write_json(out / 'dev_oracle.json', oracle)
    manifest = {'version': VERSION, 'synthetic': False, 'external_test': False,
                'frozen_public_diagnostic': True, 'source_reuse_from_v3': True,
                'train_task_count': 0, 'dev_task_count': len(tasks),
                'paraphrase_count_per_family': 2, 'fault_conditions':
                ['none', 'transient_read', 'timeout', 'partial_write'],
                'sources': sources, 'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
