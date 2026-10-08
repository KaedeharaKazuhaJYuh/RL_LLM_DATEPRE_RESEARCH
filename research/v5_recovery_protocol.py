"""Build a source-disjoint, conditional commit-recovery research protocol."""
import copy
import csv
import hashlib
import io
import json
import shlex
import zipfile
from pathlib import Path

from research.io import ROOT, digest, write_json, write_table

PROTOCOL = ROOT / 'tasks/v5/recovery_beta1'
PLANS = [('clip_outliers', 'describe_numeric'), ('deduplicate', 'rolling_mean'),
         ('normalize_categories', 'count_categories'), ('clip_outliers', 'correlate'),
         ('deduplicate', 'profile_schema')]
SOURCES = {
    'auto_mpg': {'sha256': '5fc1507522b73b8050d3aa45df51eefe1b666ae5f428a5f1347b6483339f1003',
                 'doi': '10.24432/C5859H', 'citation': 'Quinlan, R. (1993). Auto MPG. UCI.',
                 'url': 'https://archive.ics.uci.edu/static/public/9/auto+mpg.zip'},
    'glass': {'sha256': '499c07a17115bf63100bb19cc1fdefad7f464bf5dc2b168930fa2071fd6b6e65',
              'doi': '10.24432/C5WW2P', 'citation': 'German, B. (1987). Glass Identification. UCI.',
              'url': 'https://archive.ics.uci.edu/static/public/42/glass+identification.zip'}}


def build(out=PROTOCOL):
    out = Path(out)
    if out.exists():
        raise FileExistsError(out)
    parent = ROOT / 'tasks/v5/rewrite_train_v1/tasks.json'
    bases = {}
    for task in json.loads(parent.read_text(encoding='utf-8')):
        if task['split'] != 'train':
            raise ValueError('training source contamination')
        bases.setdefault(task['source_id'], task)
    datasets = []
    for source, info in SOURCES.items():
        archive = ROOT / f'work/v5_0_15_sources/{source}.zip'
        if digest(archive) != info['sha256']:
            raise ValueError('upstream archive changed')
        with zipfile.ZipFile(archive) as bundle:
            if source == 'auto_mpg':
                columns = ['mpg', 'cylinders', 'displacement', 'horsepower', 'weight',
                           'acceleration', 'model_year', 'origin', 'car_name']
                values = [shlex.split(line) for line in bundle.read('auto-mpg.data').decode().splitlines() if line.strip()]
                numeric, metric, category = 'mpg', 'weight', 'car_name'
                if len(values) != 398:
                    raise ValueError('Auto MPG row count changed')
            else:
                columns = ['id', 'RI', 'Na', 'Mg', 'Al', 'Si', 'K', 'Ca', 'Ba', 'Fe', 'type']
                values = list(csv.reader(io.StringIO(bundle.read('glass.data').decode())))
                numeric, metric, category = 'Si', 'RI', 'type'
                if len(values) != 214:
                    raise ValueError('Glass row count changed')
        if any(len(row) != len(columns) for row in values):
            raise ValueError('source width mismatch')
        rows = [dict(zip(columns, ['' if v == '?' else v for v in row])) for row in values]
        path = out / 'data' / f'{source}.csv'
        write_table(path, columns, rows)
        params = {'column': numeric, 'other_column': metric, 'category_column': category,
                  'date_column': category, 'lower': 0,
                  'upper': 30 if source == 'auto_mpg' else 72, 'window': 3}
        datasets.append((f'uci_{source}', {'uri': path.relative_to(ROOT).as_posix(),
                        'columns': columns, 'sha256': digest(path)}, params))
    tasks, oracle = [], {}
    rows_to_build = [(source, base['dataset'], base['params'], 'train')
                     for source, base in sorted(bases.items())]
    rows_to_build += [(source, data, params, 'dev') for source, data, params in datasets]
    for source, dataset, params, split in rows_to_build:
        for family, plan in enumerate(PLANS[:3] if split == 'train' else PLANS):
            for language in ('en', 'zh'):
                key = f'recovery-beta1/{source}/{family}/{language}'
                tid = hashlib.sha256(key.encode()).hexdigest()[:16]
                text = (f'Apply {plan[0]} with the supplied bindings, then {plan[1]}; ensure exactly one commit.'
                        if language == 'en' else
                        f'先按绑定参数完成 {plan[0]}，再进行 {plan[1]}；确保首项只提交一次。')
                if split == 'dev':
                    text = (f'Resume this job safely: {plan[0]} precedes {plan[1]}. Do not submit the first operation twice.'
                            if language == 'en' else
                            f'恢复被打断的任务：先 {plan[0]} 再 {plan[1]}。首项操作不得重复提交。')
                tasks.append({'task_id': tid, 'source_id': source, 'pair_family': family,
                              'language': language, 'split': split, 'prompt': text,
                              'dataset': copy.deepcopy(dataset), 'params': copy.deepcopy(params),
                              'timeout_message': ('Timeout: outcome unknown' if split == 'train'
                                                  else 'Response deadline exceeded; acknowledgement unavailable')})
                oracle[tid] = list(plan)
    write_json(out / 'tasks.json', tasks)
    write_json(out / 'oracle.json', oracle)
    manifest = {'version': 'v5-recovery-beta1', 'scope': 'conditional recovery; given prefix and suffix',
                'train_sources': sorted(bases), 'holdout_sources': [x[0] for x in datasets],
                'source_licenses': {k: {**v, 'license': 'CC BY 4.0',
                                      'transformations': 'whitespace source parsed to CSV; ? becomes empty; all rows retained'}
                                    for k, v in SOURCES.items()},
                'tasks_sha256': digest(out / 'tasks.json'), 'oracle_sha256': digest(out / 'oracle.json'),
                'seeds': [20260921, 20260922, 20260923],
                'modes': ['none', 'before_commit', 'after_commit', 'partial_write'],
                'train_task_count': sum(t['split'] == 'train' for t in tasks),
                'eval_task_count': sum(t['split'] == 'dev' for t in tasks),
                'train_modes': ['none', 'before_commit', 'after_commit'],
                'heldout_fault': 'partial_write', 'heldout_families': [3, 4],
                'arms': ['sft', 'grpo', 'branch', 'counterfactual', 'paired'],
                'groups': 16, 'branches_per_group': 4, 'ppo_epochs': 2,
                'learning_rate': 0.000002, 'kl_beta': 0.02,
                'decoding': '4-way categorical next-token policy; greedy at evaluation',
                'counterfactual_estimator': 'enumerate first action; sample continuation with frozen behavior; update root only',
                'gate': 'positive source-family macro gap over SFT, GRPO and branch; >=2 positive seeds; clean no regression; descriptive only with two sources'}
    write_json(out / 'manifest.json', manifest)
    return manifest


def load(protocol=PROTOCOL):
    protocol = Path(protocol)
    manifest = json.loads((protocol / 'manifest.json').read_text(encoding='utf-8'))
    for file in ('tasks', 'oracle'):
        if digest(protocol / f'{file}.json') != manifest[f'{file}_sha256']:
            raise ValueError('protocol content hash mismatch')
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    oracle = json.loads((protocol / 'oracle.json').read_text(encoding='utf-8'))
    train = {t['source_id'] for t in tasks if t['split'] == 'train'}
    dev = {t['source_id'] for t in tasks if t['split'] == 'dev'}
    if train & dev or train != set(manifest['train_sources']) or dev != set(manifest['holdout_sources']):
        raise ValueError('source split mismatch')
    if {t['task_id'] for t in tasks} != set(oracle) or len(tasks) != len(oracle):
        raise ValueError('invalid task identity set')
    return tasks, oracle, manifest


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
