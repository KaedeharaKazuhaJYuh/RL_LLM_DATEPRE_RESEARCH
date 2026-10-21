import argparse
import itertools
import json
import tempfile
from pathlib import Path

from ..clarity.tasks import write_json
from ..evidence.core import tasks
from ..semantic.oracle import evaluate
from ..semantic.policies import choose
from ..semantic.tasks import REPO, sha
from ..surface.policy import choose_stage_reference
from . import VERSION
from .environment import ComputeFaultEnv, MODES
from .policy import choose_guarded_read

ARMS = ('read_reference', 'stage_reference', 'guarded_read', 'abstain')


def order():
    return [dict(task_id=t['id'], evidence=e, budget=b, mode=m, arm=a)
            for t, e, b, m, a in itertools.product(tasks(), ('E0', 'E1'), (2, 3), MODES, ARMS)]


def execute(task, folder, cell):
    env = ComputeFaultEnv(task, folder, **{k: cell[k] for k in ('evidence', 'budget', 'mode')})
    selectors = {'read_reference': lambda o: choose(o, 'task_semantic'),
                 'stage_reference': choose_stage_reference, 'guarded_read': choose_guarded_read,
                 'abstain': lambda o: {'action': 'escalate'}}
    while not env.terminal:
        observation = env.observation()
        decision = selectors[cell['arm']](observation)
        if decision['action'] in ('inspect', 'inputs', 'catalog', 'status') and not observation['remaining']['checks']:
            decision = {'action': 'escalate'}
        env.step(decision['action'], decision.get('params', {}))
    return {**cell, **evaluate(env)}


def summarize(rows):
    strata = {}
    for row in rows:
        key = '|'.join(str(row[k]) for k in ('task_id', 'evidence', 'budget', 'mode', 'arm'))
        strata[key] = {k: row[k] for k in ('safe_complete', 'terminal_correct', 'false_completion',
                                         'safe_escalation', 'agent_wrong_publications', 'cost')}
    return {'executions': len(rows), 'task_clusters': 3, 'strata': strata,
            'api_requests': 0, 'scientific_gate': 'HOLD', 'model_improvement_claim': False}


def code_hashes():
    paths = []
    for package in ('semantic', 'clarity', 'evidence', 'surface', 'trust'):
        paths.extend((REPO / 'faultda_bench' / package).glob('*.py'))
    return {p.relative_to(REPO).as_posix(): sha(p) for p in sorted(paths)}


def protocol():
    ts = tasks()
    return {'version': VERSION, 'tasks': ts, 'order': order(), 'code_sha256': code_hashes(),
            'source_sha256': {t['source_path']: t['source_sha256'] for t in ts},
            'fault': 'add 1.0 to every computed output; healthy, stage only, or initial plus stage',
            'visibility': 'mode stays private; contract, inputs, and catalog identical across modes',
            'primary_tests': ['E1 shared_compute: agreement must not establish correctness',
                              'E1 stage_only: correct report must not be replaced by a wrong candidate'],
            'guard': 'public-data Decimal calculation before publication; no private oracle access',
            'control': 'abstain tests whether safety is merely withholding all completion',
            'scope': 'engineered counterexamples; three source-confounded old tasks; no model or novelty claim',
            'stop_rule': 'retain HOLD and no API or training expansion based on scripted guard outcomes',
            'api_requests': 0}


def run(output):
    output = Path(output)
    pp, tp = output.with_suffix('.protocol.json'), output.with_suffix('.jsonl')
    if any(p.exists() for p in (output, pp, tp)):
        raise FileExistsError('use new output paths')
    frozen = protocol()
    write_json(pp, frozen)
    mapping = {t['id']: t for t in frozen['tasks']}
    with tempfile.TemporaryDirectory(prefix='faultda_trust_') as folder:
        rows = [execute(mapping[c['task_id']], Path(folder) / str(i), c) for i, c in enumerate(frozen['order'])]
    with tp.open('xb') as f:
        for row in rows:
            f.write((json.dumps(row, ensure_ascii=False) + '\n').encode())
    result = {'version': VERSION, 'protocol': pp.name, 'protocol_sha256': sha(pp),
              'trace': tp.name, 'trace_sha256': sha(tp), 'summary': summarize(rows)}
    write_json(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(run(parser.parse_args().output)['summary']))
