"""Explicit source-to-tool bindings; no changes to frozen v1 artifacts."""
import copy
import csv
import json
from decimal import Decimal
from pathlib import Path

from ..semantic.tasks import ROOT, REPO, sha, load as load_v1
from . import VERSION

MANIFEST = ROOT / 'protocols/cross_source_v2.json'


def write_json(path, data):
    """Byte-stable LF serialization; fail rather than overwrite earlier evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write((json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode())


def clarify(task, key_column=None):
    task = copy.deepcopy(task)
    c = task['contract']
    c['input_binding'] = {
        'value': f'Normalized tool field for original measurement column {c["column"]}. Use value as the numeric measure.',
        'id': 'Unique row identifier within this task slice.',
        'key': (f'Normalized tool field for source column {key_column}; join to dimension.key.' if key_column else
                'Generated business key; join to dimension.key. It is not the numeric measure.'),
    }
    if c['family'] == 'window':
        c['input_binding']['time'] = 'Timezone-aware normalized tool timestamp; compare instants to start/end.'
    c['output'] = ('JSON object mapping each dimension.group to the sum of value for that group.'
                   if c['family'] == 'group' else 'JSON object with exactly one key total containing sum(value).')
    return task


def build():
    v1 = json.loads((ROOT / 'protocols/semantic_tasks_v1.json').read_text(encoding='utf-8'))
    specs = [
        ('uci_auto_mpg', 'tasks/v5/recovery_beta1/data/auto_mpg.csv', 'cylinders', ('mpg', 'weight')),
        ('uci_glass', 'tasks/v5/recovery_beta1/data/glass.csv', 'type', ('Na', 'Si')),
        ('uci_occupancy', 'tasks/v5/beta_holdout_v1/data/occupancy.csv', 'Occupancy', ('Temperature', 'CO2')),
    ]
    templates = {t['contract']['family']: t for t in load_v1()}
    tasks = []
    for source, relative, key_column, columns in specs:
        with (REPO / relative).open(encoding='utf-8', newline='') as stream:
            original = list(csv.DictReader(stream))
        for variant in range(4):
            column = columns[variant % 2]
            indices = [i * len(original) // 8 + variant for i in range(8)]
            rows = [{'id': str(index), 'key': original[index][key_column], 'value': original[index][column]}
                    for index in indices]
            if any(not row['value'] or not Decimal(row['value']).is_finite() for row in rows):
                raise ValueError('fixed development slice must have finite values')
            labels = sorted({r['key'] for r in rows})
            dimension = [{'key': k, 'group': k} for k in labels]
            dimension.append(dict(dimension[0]))
            for family in ('group', 'version'):
                contract = copy.deepcopy(templates[family]['contract'])
                contract.update(column=column, version_policy='snapshot' if family == 'group' or variant < 2 else 'latest')
                versions = {'v1': copy.deepcopy(rows), 'v2': copy.deepcopy(rows)}
                versions['v2'][0]['value'] = str(Decimal(rows[0]['value']) + Decimal(variant + 1))
                task = {'id': f'{source}-{family}-{variant + 1:02d}', 'source_id': source,
                        'family_source_cell': f'{source}/{family}', 'split': 'historical_development',
                        'source_path': relative, 'source_sha256': sha(REPO / relative),
                        'selection_indices': indices, 'contract': contract,
                        'versions': versions, 'dimension': dimension,
                        'catalog': {'snapshot': 'v1', 'latest': 'v2'}}
                tasks.append(clarify(task, key_column))
    return {'version': VERSION, 'tasks': tasks, 'source_clusters': 3,
            'design': 'three sources x two intents x four variants; shared slices are correlated',
            'attribution': v1['attribution'], 'human_review': 'pending; generated review sheet is not human approval',
            'transformations': 'Eight evenly spaced rows shifted by variant; natural source categories as business keys; one duplicated dimension mapping; synthetic one-value v2 revision. Windows excluded from crossed design because two sources lack real timestamps.',
            'limitations': ['historical development only', 'controlled binding', 'no held-out source',
                            'three sources do not support confirmatory inference']}


def load():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))['tasks']


def code_hashes():
    paths = list((ROOT / 'semantic').glob('*.py')) + list(Path(__file__).parent.glob('*.py'))
    paths.append(REPO / 'agent/deepseek_config.py')
    return {p.relative_to(REPO).as_posix(): sha(p) for p in sorted(paths)}


if __name__ == '__main__':
    write_json(MANIFEST, build())
