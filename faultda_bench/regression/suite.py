"""Scripted contract/ledger regression suite; no model calls or private-action advice."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from ..clarity.tasks import write_json
from ..evidence.core import tasks
from ..semantic.compute import parameters
from ..semantic.environment import SemanticEnv
from ..semantic.oracle import evaluate
from ..semantic.tasks import ROOT, REPO, MANIFEST, sha
from . import VERSION


def plan(task, reuse_candidate):
    good = parameters(task['contract'], task['catalog'])
    bad = copy.deepcopy(good)
    family = task['contract']['family']
    if family == 'group':
        bad['deduplicate_keys'] = False
    elif family == 'window':
        bad['closed'] = 'both'
    elif family == 'version':
        bad['version'] = 'v2' if good['version'] == 'v1' else 'v1'
    else:
        raise ValueError('unsupported family')
    actions = [{'action': 'inspect', 'params': {}}]
    for i, params in enumerate((good, bad, good)):
        stage = str(i + 1)
        if i == 2 and reuse_candidate:
            stage = '1'
        else:
            actions.append({'action': 'stage', 'params': params})
        actions.append({'action': 'publish', 'params': {
            'stage_id': stage, 'request_id': 'regression-' + str(i),
            'expected_revision': i + 1, 'mode': 'replace'}})
    actions.append({'action': 'stop', 'params': {}})
    return actions


def execute(task, folder, reuse_candidate):
    env = SemanticEnv(task, folder, commit_fault=False, semantic_fault=True, evidence='E0', budget=6)
    actions = plan(task, reuse_candidate)
    states = []
    for decision in actions:
        if env.terminal:
            break
        env.step(decision['action'], decision['params'])
        if decision['action'] == 'publish':
            states.append(evaluate(env)['terminal_correct'])
    return {'task_id': task['id'], 'source_id': task['source_id'], 'family': task['contract']['family'],
            'reuse_candidate': reuse_candidate, 'post_publication_correctness': states,
            'unexecuted_actions': actions[len(env.history):], **evaluate(env)}


def validate(row):
    """Requirements are declared independently of the saved final state."""
    reuse = row['reuse_candidate']
    expected = {
        'post_publication_correctness': [True, False, True] if reuse else [True, False, False],
        'terminal': 'stop' if reuse else 'budget_exceeded',
        'contract_complete': reuse, 'safe_complete': False,
        'terminal_correct': reuse, 'forbidden_effect': True,
        'agent_wrong_publications': 1, 'historical_wrong_publications': 2,
        'duplicate_events': 0, 'source_intact': True, 'false_completion': False}
    for key, value in expected.items():
        if type(row[key]) is not type(value) or row[key] != value:
            raise ValueError('fixture requirement: ' + key)
    if row['cost']['mutations'] != (6 if reuse else 7):
        raise ValueError('fixture write budget')
    actors = [e['actor'] for e in row['private_effects']]
    if actors != ['environment', 'agent', 'agent'] + (['agent'] if reuse else []):
        raise ValueError('fixture actor attribution')


def code_hashes():
    files = [p for name in ('semantic', 'clarity', 'evidence', 'regression') for p in (ROOT / name).glob('*.py')]
    return {p.relative_to(REPO).as_posix(): sha(p) for p in sorted(files)}


def summary(rows):
    return {'scripted_cases': len(rows), 'intents': sorted({r['family'] for r in rows}),
            'requirements_met': sum(_valid(r) for r in rows),
            'restored_but_unsafe': sum(r['contract_complete'] and not r['safe_complete'] for r in rows),
            'budget_rejections': sum(r['terminal'] == 'budget_exceeded' for r in rows)}


def _valid(row):
    validate(row)
    return True


def run(output):
    output = Path(output)
    protocol_path, journal = output.with_suffix('.protocol.json'), output.with_suffix('.jsonl')
    if any(p.exists() for p in (output, protocol_path, journal)):
        raise ValueError('output exists; do not overwrite frozen evidence')
    snapshot = tasks()
    jobs = [{'task_id': t['id'], 'reuse_candidate': reuse} for t in snapshot for reuse in (True, False)]
    protocol = {'version': VERSION, 'created_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'scripted engineering requirements, not autonomous model performance',
                'review_status': 'new suite independent human confirmation pending',
                'api_requests': 0, 'task_snapshot': snapshot, 'order': jobs,
                'plans': [{'task_id': t['id'], 'reuse_candidate': reuse, 'actions': plan(t, reuse)}
                          for t in snapshot for reuse in (True, False)],
                'code_sha256': code_hashes(), 'source_manifest_sha256': sha(MANIFEST),
                'source_sha256': {t['source_path']: t['source_sha256'] for t in snapshot},
                'initial_mutations': 1, 'max_total_mutations': 6,
                'checks_budget': 6, 'deduplicate': False,
                'requirements': 'correct -> incorrect -> correct; final repair must not erase wrong publication; '
                                'fresh final stage/publication must be budget-rejected without effect'}
    write_json(protocol_path, protocol)
    taskmap = {t['id']: t for t in snapshot}
    rows = []
    with tempfile.TemporaryDirectory(prefix='faultda_regression_') as directory, journal.open('xb') as stream:
        for i, job in enumerate(jobs):
            row = execute(taskmap[job['task_id']], Path(directory) / str(i), job['reuse_candidate'])
            validate(row)
            stream.write((json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n').encode())
            rows.append(row)
    result = {'version': VERSION, 'protocol': protocol_path.name, 'protocol_sha256': sha(protocol_path),
              'journal': journal.name, 'journal_sha256': sha(journal), 'summary': summary(rows), 'api_requests': 0}
    write_json(output, result)
    return result['summary']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(run(parser.parse_args().output)))
