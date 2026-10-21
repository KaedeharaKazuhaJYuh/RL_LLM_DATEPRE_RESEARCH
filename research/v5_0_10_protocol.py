"""Freeze train-only rewrites and a source/wording held-out V5.0.10 protocol."""
import copy
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from agent.tools import ACTIONS
from research.io import ROOT, digest, read_table, write_json, write_table
from research.v4_real_protocol import PLANS

VERSION = 'v5-0-10-rewrite-1'
PARENT = ROOT / 'tasks/v5/beta_curriculum_v1'
ARCHIVE = ROOT / 'work/v5_0_10_sources/online_shoppers.zip'
ARCHIVE_SHA256 = '2972e6184d3ad7beaaa831d9fc2b059dc3ee29df69d1ec593c466a5cd8485d14'
ARCHIVE_MEMBER = 'online_shoppers_intention.csv'
UPSTREAM_ROWS = 12330
SOURCE_ID = 'uci_online_shoppers'
SOURCE_URL = 'https://archive.ics.uci.edu/static/public/468/online+shoppers+purchasing+intention+dataset.zip'

TRAIN_PROMPTS = (
    (
        '把一模一样的整行记录合并到只剩一份；之后按原来的行序算 {metric} 的三行完整滑动均值，工作完成就停止。',
        'Collapse identical whole rows to one copy. Then calculate complete three-row moving averages of {metric} in original order and finish.',
    ),
    (
        '先修整 {category} 的标签：删掉两端空格并转换成大写；再给出修整后的各标签条数，完成就停止。',
        'Tidy labels in {category} by stripping outer whitespace and converting to capitals; tally each resulting label and finish.',
    ),
    (
        '把 {value} 的值限制在零到一百（含端点），写回结果；然后汇报这一列的描述性数值统计，完成就停止。',
        'Bound {value} inclusively between zero and one hundred and save; report descriptive numeric statistics for that column, then finish.',
    ),
)

# Kept distinct from TRAIN_PROMPTS and all previously published prompt families.
EVAL_PROMPTS = (
    (
        '表里重复的完整记录只留一条。接着按照现有行顺序，求 {metric} 每三个相邻值的完整窗口平均；两项都办妥后结束。',
        'Retain a single instance of each fully repeated record. Next return full-window averages over adjacent triples of {metric} in table order; end after both operations.',
    ),
    (
        '将 {category} 的类别名统一为去掉首尾留白后的大写形式。基于变更后的表列出每种类别的出现次数，然后结束。',
        'Standardize category names in {category} to uppercase after removing surrounding space. Count frequencies in the updated table and then end.',
    ),
    (
        '将 {value} 的每个数压到闭区间 [0,100] 并保存；随后给出此列的条数、最小值、最大值和平均值，结束。',
        'Persist {value} with every number confined to the closed interval [0,100]; then provide its count, minimum, maximum and mean, and end.',
    ),
)


def _task_id(kind, source, family, paraphrase):
    return hashlib.sha256(f'{VERSION}/{kind}/{source}/{family}/{paraphrase}'.encode()).hexdigest()[:16]


def build_train(out=ROOT / 'tasks/v5/rewrite_train_v1'):
    out = Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('new repository output directory required')
    parent_tasks = json.loads((PARENT / 'tasks.json').read_text(encoding='utf-8'))
    parent_oracle = json.loads((PARENT / 'train_oracle.json').read_text(encoding='utf-8'))
    bases = {}
    for task in parent_tasks:
        if task['split'] != 'train' or parent_oracle[task['task_id']]['plan'] != list(PLANS[task['pair_family']]):
            raise ValueError('unexpected parent train task')
        bases.setdefault(task['source_id'], task)
    if len(bases) != 16 or SOURCE_ID in bases:
        raise ValueError('train source isolation failed')
    tasks, oracle = [], {}
    for source, base in sorted(bases.items()):
        params = base['params']
        values = {'value': params['column'], 'metric': params['other_column'],
                  'category': params['category_column']}
        for family, plan in enumerate(PLANS):
            for paraphrase, template in enumerate(TRAIN_PROMPTS[family]):
                task = copy.deepcopy(base)
                task_id = _task_id('train', source, family, paraphrase)
                task.update(schema_version=VERSION, task_id=task_id,
                            pair_family=family, paraphrase_id=paraphrase,
                            composition_novelty='train_rewrite_only',
                            prompt=template.format(**values))
                tasks.append(task)
                oracle[task_id] = {'plan': list(plan)}
    out.mkdir(parents=True)
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', oracle)
    write_json(out / 'dev_oracle.json', {})
    manifest = {'version': VERSION, 'train_only': True, 'synthetic': True,
                'parent_manifest_sha256': digest(PARENT / 'manifest.json'),
                'train_sources': sorted(bases), 'train_task_count': len(tasks),
                'prompt_templates': TRAIN_PROMPTS,
                'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return manifest


def build_eval(out=ROOT / 'tasks/v5/rewrite_holdout_v1'):
    out = Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('new repository output directory required')
    if digest(ARCHIVE) != ARCHIVE_SHA256:
        raise ValueError('UCI archive hash mismatch')
    with zipfile.ZipFile(ARCHIVE) as bundle:
        rows = list(csv.reader(io.StringIO(bundle.read(ARCHIVE_MEMBER).decode('utf-8-sig'))))
    columns, values = rows[0], rows[1:]
    if len(values) != UPSTREAM_ROWS or any(len(row) != len(columns) for row in values):
        raise ValueError('UCI source schema or row count changed')
    for field in ('VisitorType', 'ProductRelated_Duration', 'PageValues'):
        if field not in columns:
            raise ValueError(f'missing expected column {field}')
    sampled = [dict(zip(columns, values[(i * UPSTREAM_ROWS) // 240])) for i in range(240)]
    out.mkdir(parents=True)
    csv_path = out / 'data/online_shoppers.csv'
    write_table(csv_path, columns, sampled)
    if read_table(csv_path) != (columns, sampled):
        raise AssertionError('source CSV round-trip mismatch')
    dataset = {'uri': csv_path.relative_to(ROOT).as_posix(), 'columns': columns,
               'sha256': digest(csv_path)}
    params = {'column': 'ProductRelated_Duration', 'category_column': 'VisitorType',
              'date_column': 'Month', 'other_column': 'PageValues',
              'lower': 0, 'upper': 100, 'window': 3}
    values = {'value': params['column'], 'category': params['category_column'],
              'metric': params['other_column']}
    tasks, oracle = [], {}
    for family, plan in enumerate(PLANS):
        for paraphrase, template in enumerate(EVAL_PROMPTS[family]):
            task_id = _task_id('eval', SOURCE_ID, family, paraphrase)
            tasks.append({'schema_version': VERSION, 'task_id': task_id,
                          'source_id': SOURCE_ID, 'split': 'dev',
                          'pair_family': family, 'paraphrase_id': paraphrase,
                          'composition_novelty': 'new_source_and_prompt',
                          'prompt': template.format(**values), 'dataset': dataset,
                          'params': params, 'allowed_tools': ACTIONS,
                          'constraints': {'max_steps': 4, 'max_tool_calls': 3,
                                          'max_seconds': 120, 'isolated_tools': True,
                                          'tool_timeout_seconds': 10}})
            oracle[task_id] = {'plan': list(plan)}
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', {})
    write_json(out / 'dev_oracle.json', oracle)
    manifest = {'version': VERSION, 'synthetic': False, 'external_test': True,
                'external_test_scope': 'new UCI source and unseen prompt templates',
                'one_time_evaluation': True, 'train_task_count': 0,
                'dev_task_count': len(tasks), 'fault_conditions':
                ['none', 'transient_read', 'timeout', 'partial_write'],
                'source': {'source_id': SOURCE_ID, 'rows': len(sampled),
                           'upstream_rows': UPSTREAM_ROWS,
                           'selection': '240 evenly spaced source-order rows, index floor(i*N/240)',
                           'sha256': dataset['sha256'], 'archive_sha256': ARCHIVE_SHA256,
                           'upstream_url': SOURCE_URL, 'doi': '10.24432/C5F88Q',
                           'citation': 'Sakar, C. & Kastro, Y. (2018). Online Shoppers Purchasing Intention Dataset. UCI Machine Learning Repository.',
                           'license': 'CC BY 4.0', 'personal_data_columns': []},
                'prompt_templates': EVAL_PROMPTS,
                'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    print(json.dumps({'train': build_train(), 'eval': build_eval()}, ensure_ascii=False, indent=2))
