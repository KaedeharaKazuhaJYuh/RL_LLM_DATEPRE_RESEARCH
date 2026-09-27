"""Build the preregistered, source-held-out V4 closing evaluation."""
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path

from agent.tools import ACTIONS
from research.io import ROOT, digest, read_table, write_json, write_table
from research.v4_real_protocol import PLANS, PROMPTS
from research.v3_real_data import SOURCES as V3_SOURCES

VERSION = 'v4-source-holdout-1'
CACHE = ROOT / 'work/v4_final_sources'
SOURCES = {
    'forest': {'url': 'https://archive.ics.uci.edu/static/public/162/forest+fires.zip',
               'archive_sha256': 'abd40d6142b5e30fea73ff7292f91dcdd8b64bf3b3f36e20f96c37f5d14f06fb',
               'doi': '10.24432/C5D88D', 'citation': 'Cortez, P. & Morais, A. (2007). Forest Fires. UCI Machine Learning Repository.',
               'archive_name': 'forest.zip', 'member': 'forestfires.csv',
               'category': 'month', 'value': 'DMC', 'metric': 'temp'},
    'rice': {'url': 'https://archive.ics.uci.edu/static/public/545/rice+cammeo+and+osmancik.zip',
             'archive_sha256': 'fe94e42046b829de21b92b0ffb6a22774fde021328cae799faa802a14e8dbed9',
             'doi': '10.24432/C5MW4Z', 'citation': 'Rice (Cammeo and Osmancik) (2019). UCI Machine Learning Repository.',
             'archive_name': 'rice.zip', 'member': 'Rice_Cammeo_Osmancik.arff',
             'category': 'Class', 'value': 'Minor_Axis_Length', 'metric': 'Major_Axis_Length'},
}
RICE_COLUMNS = ('Area', 'Perimeter', 'Major_Axis_Length', 'Minor_Axis_Length',
                'Eccentricity', 'Convex_Area', 'Extent', 'Class')
MODEL_SHA256 = '58858233513d76b8703e72eed6ce16807b523328188e13329257fb9594462945'
ADAPTER_SHA256 = '867a6c91b74a1c4a8b233de6511977e7876008c17ace9df8bab12a877696c9ff'


def _rows(name, archive):
    spec = SOURCES[name]
    with zipfile.ZipFile(archive) as bundle:
        payload = bundle.read(spec['member']).decode('utf-8-sig')
    if name == 'forest':
        reader = csv.DictReader(io.StringIO(payload))
        columns = list(reader.fieldnames)
        rows = list(reader)
        if len(rows) != 517 or 'month' not in columns:
            raise ValueError('unexpected forest schema')
        return columns, rows[:240], len(rows), 'first 240 rows in upstream order'
    data = [line.strip() for line in payload.splitlines()
            if line.strip() and not line.lstrip().startswith('%') and not line.lstrip().startswith('@')]
    parsed = list(csv.reader(data))
    if len(parsed) != 3810 or any(len(row) != len(RICE_COLUMNS) for row in parsed):
        raise ValueError('unexpected rice schema')
    indices = [(i * len(parsed)) // 240 for i in range(240)]
    rows = [dict(zip(RICE_COLUMNS, parsed[index])) for index in indices]
    if {row['Class'] for row in rows} != {'Cammeo', 'Osmancik'}:
        raise ValueError('rice sample is not class-diverse')
    return list(RICE_COLUMNS), rows, len(parsed), '240 evenly spaced source-order rows, index floor(i*N/240)'


def build(out=None, cache=CACHE):
    out = Path(out or ROOT / 'tasks/v4/final_holdout_v1').resolve()
    cache = Path(cache)
    if out.exists():
        raise FileExistsError('new output directory required')
    if not out.is_relative_to(ROOT):
        raise ValueError('output must be inside repository')
    old_urls = {spec['url'] for spec in V3_SOURCES.values()}
    old_real = json.loads((ROOT / 'tasks/v4/real_csv_v1/manifest.json').read_text(encoding='utf-8'))
    old_urls.update(spec['upstream_url'] for spec in old_real['sources'].values())
    if any(spec['url'] in old_urls for spec in SOURCES.values()):
        raise ValueError('holdout source overlaps prior real-data protocol')
    staged = []
    for name, spec in SOURCES.items():
        archive = cache / spec['archive_name']
        if digest(archive) != spec['archive_sha256']:
            raise ValueError(f'{name} archive hash mismatch')
        staged.append((name, *_rows(name, archive)))
    out.mkdir(parents=True)
    tasks, oracle, sources = [], {}, {}
    for name, columns, rows, upstream_rows, selection in staged:
        spec = SOURCES[name]
        target = out / 'data' / f'{name}.csv'
        write_table(target, columns, rows)
        if read_table(target) != (columns, rows):
            raise AssertionError('CSV round-trip mismatch')
        dataset = {'uri': target.relative_to(ROOT).as_posix(), 'columns': columns,
                   'sha256': digest(target)}
        params = {'column': spec['value'], 'category_column': spec['category'],
                  'date_column': spec['category'], 'other_column': spec['metric'],
                  'lower': 0, 'upper': 100, 'window': 3}
        sources[name] = {'source_id': f'uci_{name}', 'rows': len(rows),
                         'upstream_rows': upstream_rows, 'selection': selection,
                         'sha256': dataset['sha256'], 'archive_sha256': spec['archive_sha256'],
                         'upstream_url': spec['url'], 'doi': spec['doi'],
                         'citation': spec['citation'], 'license': 'CC BY 4.0',
                         'personal_data_columns': []}
        for family, plan in enumerate(PLANS):
            for paraphrase, template in enumerate(PROMPTS[family]):
                task_id = hashlib.sha256(f'{VERSION}/{name}/{family}/{paraphrase}'.encode()).hexdigest()[:16]
                task = {'schema_version': VERSION, 'task_id': task_id,
                        'source_id': f'uci_{name}', 'split': 'dev',
                        'pair_family': family, 'paraphrase_id': paraphrase,
                        'composition_novelty': 'held_out_public_source',
                        'prompt': template.format(value=spec['value'], metric=spec['metric'],
                                                  category=spec['category']),
                        'dataset': dataset, 'params': params, 'allowed_tools': ACTIONS,
                        'constraints': {'max_steps': 4, 'max_tool_calls': 3,
                                        'max_seconds': 120, 'isolated_tools': True,
                                        'tool_timeout_seconds': 10}}
                tasks.append(task)
                oracle[task_id] = {'plan': list(plan)}
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'train_oracle.json', {})
    write_json(out / 'dev_oracle.json', oracle)
    manifest = {'version': VERSION, 'synthetic': False, 'external_test': True,
                'external_test_scope': 'new data sources only; task templates and action families reused',
                'one_time_evaluation': True, 'source_reuse_from_v3': False,
                'train_task_count': 0, 'dev_task_count': len(tasks),
                'paraphrase_count_per_family': 2,
                'fault_conditions': ['none', 'transient_read', 'timeout', 'partial_write'],
                'frozen_model_weights_sha256': MODEL_SHA256,
                'frozen_adapter_weights_sha256': ADAPTER_SHA256,
                'frozen_decoding': {'greedy': True, 'max_new_tokens': 48},
                'planned_primary_metric': 'terminal success, 12 clean episodes',
                'planned_secondary_metric': 'terminal success, 48 episodes across 4 fault modes',
                'sources': sources, 'tasks_sha256': digest(out / 'tasks.json'),
                'train_oracle_sha256': digest(out / 'train_oracle.json'),
                'dev_oracle_sha256': digest(out / 'dev_oracle.json')}
    write_json(out / 'manifest.json', manifest)
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
