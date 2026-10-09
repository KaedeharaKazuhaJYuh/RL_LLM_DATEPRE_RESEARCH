"""Integrity checks shared by matrix resume and frozen result analysis (no torch)."""
import json
from pathlib import Path

from research.io import ROOT, digest
from research.v5_recovery_protocol import PROTOCOL, load
from research.v5_recovery_env import ACTIONS


def require(condition, message):
    if not condition:
        raise ValueError(message)


def training(target, arm, seed, model=None):
    target = Path(target)
    tasks, _, manifest = load()
    report = json.loads((target/'summary.json').read_text(encoding='utf-8'))
    require(report['schema_version'] == 'v5-recovery-train-1', 'training schema')
    require((report['arm'], report['seed']) == (arm, seed), 'training identity')
    require(report['protocol_sha256'] == digest(PROTOCOL/'manifest.json'), 'protocol changed')
    if model is not None:
        require(report['model_sha256'] == digest(Path(model)/'model.safetensors'), 'model changed')
    initial = ROOT/f'work/v5_0_05_sft_control_seed{seed}/adapter/adapter_model.safetensors'
    require(report['initial_adapter_sha256'] == digest(initial), 'initial adapter changed')
    require(report['adapter_sha256'] == digest(target/'adapter/adapter_model.safetensors'), 'adapter changed')
    rows = report['records']
    from experiments.v5_recovery_train import schedule
    planned = schedule(tasks, seed)
    require(len(rows) == 16 and [r['group'] for r in rows] == list(range(16)), 'incomplete groups')
    train_ids = {t['task_id'] for t in tasks if t['split'] == 'train'}
    for group, row in enumerate(rows):
        require(row['task_id'] == planned[group][0]['task_id'], 'task schedule mismatch')
        pair = group//2
        mode = 'none' if pair in (0, 4) else ('before_commit' if group % 2 == 0 else 'after_commit')
        require(row['task_id'] in train_ids, 'training source leak')
        require((row['pair'], row['mode'], row['reset_after_inspection']) ==
                (pair, mode, bool(pair % 2)), 'schedule mismatch')
        require(len(row['scores']) == len(row['actions']) == 4, 'incomplete branches')
        if group % 2:
            require(row['task_id'] == rows[group-1]['task_id'], 'broken task pairing')
    require(report['budget']['terminal_branches'] == 64, 'branch budget mismatch')
    counters = dict(tool_calls=0, inspections=0, decisions=0)
    for row in rows:
        reset = int(row['reset_after_inspection'] and row['mode'] != 'none')
        root = {'tool_calls': int(row['mode'] in ('none', 'after_commit')),
                'inspections': reset, 'decisions': reset}
        for key in counters:
            counters[key] += sum(s[key] for s in row['scores']) - 3*root[key]
    require(all(report['budget'][k] == v for k, v in counters.items()), 'counter ledger mismatch')
    require(report['optimizer_steps'] == manifest['ppo_epochs']*sum(r['updated'] for r in rows),
            'optimizer count mismatch')
    return report


def evaluation(path, adapter_sha256, model_sha256):
    tasks, _, manifest = load()
    report = json.loads(Path(path).read_text(encoding='utf-8'))
    require(report['schema_version'] == 'v5-recovery-eval-1', 'evaluation schema')
    require(report['protocol_sha256'] == digest(PROTOCOL/'manifest.json'), 'evaluation protocol changed')
    require(report['adapter_sha256'] == adapter_sha256, 'evaluation adapter mismatch')
    require(report['model_sha256'] == model_sha256, 'evaluation model mismatch')
    expected = {(t['task_id'], m) for t in tasks if t['split'] == 'dev' for m in manifest['modes']}
    rows = report['records']
    keys = [(r['task_id'], r['mode']) for r in rows]
    require(len(keys) == len(set(keys)) and set(keys) == expected, 'missing/duplicate evaluation cases')
    metadata = {t['task_id']: t for t in tasks if t['split'] == 'dev'}
    for row in rows:
        task = metadata[row['task_id']]
        require((row['source_id'], row['family'], row['language']) ==
                (task['source_id'], task['pair_family'], task['language']), 'evaluation metadata mismatch')
        actions = row['actions']
        require(1 <= len(actions) <= 3 and all(a in ACTIONS for a in actions), 'invalid evaluation actions')
        initial_commit = int(row['mode'] in ('none', 'after_commit'))
        require(row['decisions'] == len(actions) and row['inspections'] == actions.count('inspect_commit') and
                row['commits'] == initial_commit + actions.count('retry') and
                row['tool_calls'] == initial_commit + actions.count('retry') + actions.count('continue'),
                'evaluation counter ledger mismatch')
        require(type(row['passed']) is bool and row['reward'] == float(row['passed']) and
                row['duplicate_commit'] == (row['commits'] > 1) and
                (not row['passed'] or (row['commits'] == 1 and 'continue' in actions)),
                'inconsistent terminal result')
    require(report['episodes'] == len(rows) and report['passed'] == sum(r['passed'] for r in rows),
            'evaluation totals mismatch')
    return report
