"""Register historical task sources as seen; never promote prior tests to final tests."""
import json
from pathlib import Path

from research.io import ROOT, write_json


def build():
    sources = {}
    for path in sorted((ROOT/'tasks').rglob('tasks.json')) + sorted((ROOT/'tasks').rglob('tasks.jsonl')):
        if path.suffix == '.jsonl':
            tasks = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        else:
            tasks = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(tasks, list):
            continue
        for task in tasks:
            if not isinstance(task, dict) or 'source_id' not in task:
                continue
            sid = task['source_id']
            row = sources.setdefault(sid, {'source_id': sid, 'used_in_prior_v1_v5': True,
                                          'faultda_split': 'seen_development', 'prior_splits': [],
                                          'usage_files': [], 'datasets': [], 'source_metadata': []})
            for key, value in [('prior_splits', task.get('split', 'unspecified')),
                               ('usage_files', path.relative_to(ROOT).as_posix())]:
                if value not in row[key]:
                    row[key].append(value)
            data = task.get('dataset')
            if isinstance(data, dict) and data not in row['datasets']:
                row['datasets'].append(data)
    for path in sorted((ROOT/'tasks').rglob('manifest.json')):
        manifest = json.loads(path.read_text(encoding='utf-8'))
        for field in ('sources', 'source_licenses'):
            entries = manifest.get(field, {})
            if not isinstance(entries, dict):
                continue
            for key, value in entries.items():
                if not isinstance(value, dict):
                    continue
                sid = value.get('source_id', key if key in sources else 'uci_'+key)
                if sid in sources:
                    sources[sid]['source_metadata'].append({'manifest': path.relative_to(ROOT).as_posix(), **value})
    return {'schema_version': 'faultda-historical-sources-1', 'final_test_sources': [],
            'final_test_policy': 'New sources must not have been used in V1-V5 training, diagnosis, or selection; freeze before model evaluation.',
            'registry_scope': 'source_id values found in historical task JSON/JSONL; source aliases and raw-archive duplication still need manual review',
            'sources': [sources[sid] for sid in sorted(sources)]}


if __name__ == '__main__':
    registry = build()
    write_json(ROOT/'faultda_bench/protocols/historical_sources.json', registry)
    print('historical source IDs', len(registry['sources']), 'final test sources', 0)
