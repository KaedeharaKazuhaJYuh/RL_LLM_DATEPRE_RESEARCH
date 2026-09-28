"""Build the preregistered V5 beta source-and-paraphrase holdout."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from agent.tools import ACTIONS
from research.io import ROOT, digest, read_table, write_json, write_table

VERSION = 'v5-beta-holdout-1'
CACHE = ROOT / 'work/v5_beta_sources'
SOURCES = {
    'banknote': {
        'url': 'https://archive.ics.uci.edu/static/public/267/banknote+authentication.zip',
        'archive': 'banknote.zip',
        'archive_sha256': '1e2acd9a2085fadf3d8145c12d3d22af853320d52294a6590c2eaf75fdc05227',
        'member': 'data_banknote_authentication.txt', 'upstream_rows': 1372,
        'columns': ['variance', 'skewness', 'curtosis', 'entropy', 'class'],
        'value': 'variance', 'metric': 'entropy', 'category': 'class',
        'doi': '10.24432/C55P57',
        'citation': 'Lohweg, V. (2012). Banknote Authentication. UCI Machine Learning Repository.'},
    'occupancy': {
        'url': 'https://archive.ics.uci.edu/static/public/357/occupancy+detection.zip',
        'archive': 'occupancy.zip',
        'archive_sha256': '4ae3f46aa98eedff564a9f6924d1635173e2fd2c816004342a9be93076d3a81a',
        'member': 'datatest.txt', 'upstream_rows': 2665,
        'columns': ['id', 'date', 'Temperature', 'Humidity', 'Light', 'CO2',
                    'HumidityRatio', 'Occupancy'],
        'value': 'Light', 'metric': 'CO2', 'category': 'Occupancy',
        'doi': '10.24432/C5X01N',
        'citation': 'Candanedo, L. (2016). Occupancy Detection. UCI Machine Learning Repository.'},
}
PLANS = (
    ('deduplicate', 'rolling_mean'),
    ('normalize_categories', 'count_categories'),
    ('clip_outliers', 'describe_numeric'),
)
PROMPTS = (
    ('检查重复行并只保留一份。然后依数据现有顺序，给出 {metric} 每连续三行的平均值；完成后结束。',
     'Keep one copy of each duplicate row. Next compute full three-row moving averages for {metric} in the existing order, then finish.'),
    ('请先清理 {category} 的首尾空白并转成大写，再汇总清理后各类别出现的次数，然后结束。',
     'First trim and uppercase entries in {category}; then tally the cleaned categories and finish.'),
    ('把 {value} 中低于 0 的值设为 0、高于 100 的值设为 100 并保存，随后报告该列的数量、最小值、最大值与均值；完成后结束。',
     'Save {value} after bounding it to 0 through 100, then report its count, minimum, maximum and mean. Finish after that.'),
)


def read_source(name, spec):
    archive = CACHE / spec['archive']
    if digest(archive) != spec['archive_sha256']:
        raise ValueError(f'{name} upstream archive hash mismatch')
    with zipfile.ZipFile(archive) as bundle:
        payload = bundle.read(spec['member']).decode('utf-8-sig')
    if name == 'banknote':
        parsed = list(csv.reader(io.StringIO(payload)))
        columns = spec['columns']
    else:
        parsed_rows = list(csv.reader(io.StringIO(payload)))
        columns = ['id', *parsed_rows[0]]  # The upstream CSV omits the row-id header.
        parsed = parsed_rows[1:]
    if columns != spec['columns'] or len(parsed) != spec['upstream_rows'] or any(
            len(row) != len(columns) for row in parsed):
        raise ValueError(f'{name} upstream schema or count changed')
    indices = [(i * len(parsed)) // 240 for i in range(240)]
    return columns, [dict(zip(columns, parsed[index])) for index in indices]


def build(out=ROOT / 'tasks/v5/beta_holdout_v1'):
    out = Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('new output directory inside repository required')
    staged = [(name, spec, *read_source(name, spec)) for name, spec in SOURCES.items()]
    out.mkdir(parents=True)
    tasks, oracle, sources = [], {}, {}
    for name, spec, columns, rows in staged:
        target = out / 'data' / f'{name}.csv'
        write_table(target, columns, rows)
        if read_table(target) != (columns, rows):
            raise AssertionError('CSV round-trip mismatch')
        source_hash = digest(target)
        dataset = {'uri': target.relative_to(ROOT).as_posix(), 'columns': columns,
                   'sha256': source_hash}
        params = {'column': spec['value'], 'category_column': spec['category'],
                  'date_column': spec['category'], 'other_column': spec['metric'],
                  'lower': 0, 'upper': 100, 'window': 3}
        sources[name] = {'source_id': f'uci_{name}', 'rows': 240,
                         'upstream_rows': spec['upstream_rows'],
                         'selection': '240 evenly spaced source-order rows, index floor(i*N/240)',
                         'sha256': source_hash, 'archive_sha256': spec['archive_sha256'],
                         'upstream_url': spec['url'], 'doi': spec['doi'],
                         'citation': spec['citation'], 'license': 'CC BY 4.0',
                         'personal_data_columns': []}
        for family, plan in enumerate(PLANS):
            for paraphrase, template in enumerate(PROMPTS[family]):
                task_id = hashlib.sha256(
                    f'{VERSION}/{name}/{family}/{paraphrase}'.encode()).hexdigest()[:16]
                tasks.append({'schema_version': VERSION, 'task_id': task_id,
                              'source_id': f'uci_{name}', 'split': 'dev',
                              'pair_family': family, 'paraphrase_id': paraphrase,
                              'composition_novelty': 'new_public_source_and_prompt',
                              'prompt': template.format(value=spec['value'], metric=spec['metric'],
                                                        category=spec['category']),
                              'dataset': dataset, 'params': params, 'allowed_tools': ACTIONS,
                              'constraints': {'max_steps': 4, 'max_tool_calls': 3,
                                              'max_seconds': 120, 'isolated_tools': True,
                                              'tool_timeout_seconds': 10}})
                oracle[task_id] = {'plan': list(plan)}
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', {})
    write_json(out / 'dev_oracle.json', oracle)
    manifest = {'version': VERSION, 'synthetic': False, 'external_test': True,
                'external_test_scope': 'new data sources and prompt paraphrases; action pairs reused',
                'one_time_evaluation': True, 'train_task_count': 0, 'dev_task_count': 12,
                'fault_conditions': ['none', 'transient_read', 'timeout', 'partial_write'],
                'planned_primary_metric': 'paired terminal success over 48 executions, RL vs SFT',
                'planned_secondary_metric': 'paired terminal success over 12 clean executions',
                'sources': sources, 'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
