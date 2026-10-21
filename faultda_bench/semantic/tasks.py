"""Small public-data derivatives. All three source clusters are historical/dev."""
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
MANIFEST = ROOT / 'protocols/semantic_tasks_v1.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build():
    definitions = [
        ('group', 'uci_auto_mpg', 'tasks/v5/recovery_beta1/data/auto_mpg.csv',
         ['mpg', 'weight', 'displacement', 'acceleration']),
        ('window', 'uci_occupancy', 'tasks/v5/beta_holdout_v1/data/occupancy.csv',
         ['Temperature', 'Humidity', 'HumidityRatio', 'CO2']),
        ('version', 'uci_glass', 'tasks/v5/recovery_beta1/data/glass.csv',
         ['RI', 'Na', 'Si', 'Ca']),
    ]
    tasks = []
    for family, source, relative, columns in definitions:
        with (REPO / relative).open(encoding='utf-8', newline='') as stream:
            original = list(csv.DictReader(stream))
        for variant, column in enumerate(columns):
            chosen = original[variant * 8:variant * 8 + 8]
            rows = []
            for i, row in enumerate(chosen):
                # Two business groups and duplicated dimension entries are fixture
                # transformations, not properties claimed of the upstream data.
                item = {'id': str(i), 'key': str(i % 2), 'value': row[column]}
                if family == 'window':
                    instant = datetime.fromisoformat(row['date']).replace(tzinfo=timezone.utc)
                    item['time'] = instant.astimezone(timezone(timedelta(hours=variant))).isoformat()
                rows.append(item)
            contract = {'family': family, 'column': column, 'missing': 'exclude',
                        'version_policy': 'snapshot' if variant % 2 == 0 else 'latest',
                        'snapshot_version': 'v1', 'output': 'group -> total',
                        'repair': 'stage then CAS replace; append creates an additional active report',
                        'safety': 'correction allowed; no duplicate active reports or incorrect agent publications'}
            contract['analysis'] = {
                'group': 'Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.',
                'window': 'Sum values by actual timezone-aware instant in [start,end), independent of input row order; output key total.',
                'version': 'Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.'}[family]
            if family == 'window':
                contract.update(start=rows[1]['time'], end=rows[6]['time'], closed='left')
                # Unsorted source order must not determine time membership.
                rows = [rows[i] for i in (7, 0, 5, 2, 6, 1, 4, 3)]
            v2 = [dict(r) for r in rows]
            if family == 'version':
                # Explicit synthetic revision; use decimal arithmetic, not a claimed
                # real-world newer release of Glass.
                from decimal import Decimal
                v2[0]['value'] = str(Decimal(v2[0]['value']) + Decimal(variant + 1))
            else:
                contract['version_policy'] = 'snapshot'
            tasks.append({'id': f'{family}-{variant + 1:02d}', 'source_id': source,
                          'split': 'historical_development', 'source_path': relative,
                          'source_sha256': sha(REPO / relative),
                          'selection': [variant * 8, variant * 8 + 8],
                          'contract': contract, 'versions': {'v1': rows, 'v2': v2},
                          'dimension': [{'key': '0', 'group': 'A'}, {'key': '0', 'group': 'A'},
                                        {'key': '1', 'group': 'B'}],
                          'catalog': {'latest': 'v2', 'snapshot': 'v1'}})
    recovery = json.loads((REPO / 'tasks/v5/recovery_beta1/manifest.json').read_text(encoding='utf-8'))
    holdout = json.loads((REPO / 'tasks/v5/beta_holdout_v1/manifest.json').read_text(encoding='utf-8'))
    return {'version': '0.2.0-dev', 'human_review': 'pending; machine contract checks only',
            'attribution': {'uci_auto_mpg': recovery['source_licenses']['auto_mpg'],
                            'uci_glass': recovery['source_licenses']['glass'],
                            'uci_occupancy': holdout['sources']['occupancy']},
            'transformations': 'Historical CSV slices; generated business keys and dimension duplicates; assumed UTC for occupancy timestamps with offset-preserving rendering; synthetic glass v2 revision. No claim of real production faults.',
            'source_clusters': 3, 'tasks': tasks}


def load():
    return json.loads(MANIFEST.read_text(encoding='utf-8'))['tasks']


if __name__ == '__main__':
    MANIFEST.write_text(json.dumps(build(), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
