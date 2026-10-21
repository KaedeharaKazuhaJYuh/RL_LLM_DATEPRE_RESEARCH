import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from ..acceptance.audit import pinned_path, require
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, sha
from ..trust.environment import ComputeFaultEnv
from . import VERSION
from .contract import MAX_PROMPT_BYTES, prompt_bytes, public_observation
from .suite import execute, protocol, summarize


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def replay_live(task, folder, row, cell):
    env = ComputeFaultEnv(task, folder, **{k: cell[k] for k in ('mode', 'evidence', 'budget')})
    prompts = []
    def capture():
        encoded = prompt_bytes(public_observation(env))
        prompts.append({'sha256': hashlib.sha256(encoded).hexdigest(), 'bytes': len(encoded)})
    for event in row['trace']:
        capture()
        require(prompts[-1]['bytes'] <= MAX_PROMPT_BYTES, 'overlimit action was executed')
        env.step(event['action'], event['params'])
        require(same(env.history[-1], event), 'model tool feedback replay')
    error_terminals = ('provider_error', 'api_budget_exceeded', 'input_limit')
    if row['terminal'] in error_terminals:
        require(env.terminal is None, 'provider error overwrites tool termination')
        capture()
        if row['terminal'] == 'input_limit':
            require(prompts[-1]['bytes'] > MAX_PROMPT_BYTES, 'unjustified prompt limit')
        else:
            last = row['api_calls'][-1]
            require(isinstance(last.get('error'), str), 'missing provider error provenance')
            require((last.get('error') == 'pilot_call_cap') == (row['terminal'] == 'api_budget_exceeded'), 'cap reason')
        env.terminal = row['terminal']
    expected_calls = len(row['trace']) + int(row['terminal'] in ('provider_error', 'api_budget_exceeded'))
    require(len(row['api_calls']) == expected_calls, 'request/action accounting')
    require(same(prompts, row['prompt_audit']), 'model public prompt replay')
    for k, value in evaluate(env).items():
        require(same(row[k], value), 'model effect replay: ' + k)


def verify(report):
    report = Path(report).resolve()
    result = json.loads(report.read_text(encoding='utf-8'))
    pp, tp = (pinned_path(report.parent, result[k]) for k in ('protocol', 'trace'))
    require(result['version'] == VERSION, 'version')
    require(sha(pp) == result['protocol_sha256'] and sha(tp) == result['trace_sha256'], 'artifact hash')
    frozen = json.loads(pp.read_text(encoding='utf-8'))
    require(same(frozen, protocol(frozen['requested_model'])), 'complete frozen protocol')
    for name, checksum in frozen['source_sha256'].items():
        require(sha(pinned_path(REPO, name)) == checksum, 'source hash')
    backend = result['backend']
    require(backend in ('offline_rules', 'deepseek_live'), 'backend provenance')
    cells = frozen['offline_order'] if backend == 'offline_rules' else [{**c, 'arm': 'deepseek'} for c in frozen['pilot_order']]
    rows = [json.loads(line) for line in tp.read_text(encoding='utf-8').splitlines()]
    require(len(rows) == len(cells), 'coverage')
    mapping = {t['id']: t for t in frozen['tasks']}
    with tempfile.TemporaryDirectory(prefix='faultda_pilot_replay_') as folder:
        for i, (row, cell) in enumerate(zip(rows, cells)):
            require(same({k: row[k] for k in cell}, cell), 'condition identity')
            if backend == 'offline_rules':
                require(same(row, execute(mapping[cell['task_id']], Path(folder) / str(i), cell)), 'offline prompt and effect replay')
            else:
                replay_live(mapping[cell['task_id']], Path(folder) / str(i), row, cell)
    require(same(result['summary'], summarize(rows)), 'summary')
    require(result['summary']['request_attempts'] <= frozen['max_calls'], 'request cap')
    return {'version': VERSION, 'backend': backend, 'executions': len(rows), 'replayed': True,
            'request_attempts': result['summary']['request_attempts'], 'status': 'verified',
            'provider_authenticity_verified': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    print(json.dumps(verify(parser.parse_args().report)))
