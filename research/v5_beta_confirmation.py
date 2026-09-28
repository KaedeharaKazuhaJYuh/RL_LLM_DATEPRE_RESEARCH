"""Build a second, source-held-out V5 beta confirmation protocol."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from agent.tools import ACTIONS
from research.io import ROOT, digest, read_table, write_json, write_table
from research.v4_real_protocol import PLANS, PROMPTS

VERSION = 'v5-beta-confirmation-1'
CACHE = ROOT / 'work/v5_beta2_sources'
SOURCES = {
    'drybean': {'url': 'https://archive.ics.uci.edu/static/public/602/dry+bean+dataset.zip',
                'archive': 'drybean.zip', 'archive_sha256':
                '0a64eff5be87f48c3dbbfc0a12a56c5d5b5167ef8e61cd45d69b3e7c7130c06f',
                'member': 'DryBeanDataset/Dry_Bean_Dataset.arff', 'upstream_rows': 13611,
                'category': 'Class', 'value': 'Area', 'metric': 'Perimeter',
                'doi': '10.24432/C50S4B',
                'citation': 'Dry Bean (2020). UCI Machine Learning Repository.'},
    'letter': {'url': 'https://archive.ics.uci.edu/static/public/59/letter+recognition.zip',
               'archive': 'letter.zip', 'archive_sha256':
               '3b5f07a334697b6cace4fbae22940393a18fee596e73f68d97ce5973d52dc60f',
               'member': 'letter-recognition.data', 'upstream_rows': 20000,
               'category': 'lettr', 'value': 'x-box', 'metric': 'y-box',
               'doi': '10.24432/C5ZP40',
               'citation': 'Slate, D. (1991). Letter Recognition. UCI Machine Learning Repository.'},
}
LETTER_COLUMNS = ['lettr', 'x-box', 'y-box', 'width', 'high', 'onpix', 'x-bar', 'y-bar',
                  'x2bar', 'y2bar', 'xybar', 'x2ybr', 'xy2br', 'x-ege', 'xegvy', 'y-ege', 'yegvx']


def read_source(name, spec):
    archive = CACHE / spec['archive']
    if digest(archive) != spec['archive_sha256']:
        raise ValueError(f'{name} archive hash mismatch')
    with zipfile.ZipFile(archive) as bundle:
        payload = bundle.read(spec['member']).decode('utf-8-sig')
    if name == 'drybean':
        columns = [line.split()[1] for line in payload.splitlines()
                   if line.upper().startswith('@ATTRIBUTE ')]
        rows = [line for line in payload.splitlines()
                if line and not line.startswith(('%', '@'))]
        parsed = list(csv.reader(rows))
    else:
        columns = LETTER_COLUMNS
        parsed = list(csv.reader(io.StringIO(payload)))
    if len(parsed) != spec['upstream_rows'] or any(len(row) != len(columns) for row in parsed):
        raise ValueError(f'{name} schema or row count changed')
    indices = [(i * len(parsed)) // 240 for i in range(240)]
    return columns, [dict(zip(columns, parsed[index])) for index in indices]


def build(out=ROOT / 'tasks/v5/beta_confirmation_v1'):
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
        dataset = {'uri': target.relative_to(ROOT).as_posix(), 'columns': columns,
                   'sha256': digest(target)}
        params = {'column': spec['value'], 'category_column': spec['category'],
                  'date_column': spec['category'], 'other_column': spec['metric'],
                  'lower': 0, 'upper': 100, 'window': 3}
        sources[name] = {'source_id': f'uci_{name}', 'rows': 240,
                         'upstream_rows': spec['upstream_rows'],
                         'selection': '240 evenly spaced source-order rows, index floor(i*N/240)',
                         'sha256': dataset['sha256'], 'archive_sha256': spec['archive_sha256'],
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
                              'composition_novelty': 'source_held_out_prompt_seen',
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
                'external_test_scope': 'new data sources only; prompts/action pairs used in train curriculum',
                'one_time_evaluation': True, 'train_task_count': 0, 'dev_task_count': 12,
                'fault_conditions': ['none', 'transient_read', 'timeout', 'partial_write'],
                'sources': sources, 'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
