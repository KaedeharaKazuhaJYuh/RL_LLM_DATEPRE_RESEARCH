import argparse
import itertools
import json
import tempfile
from pathlib import Path

from ..clarity.tasks import write_json
from ..evidence.core import tasks
from ..semantic.environment import SemanticEnv
from ..semantic.oracle import evaluate
from ..semantic.policies import choose
from ..semantic.tasks import REPO, sha
from . import VERSION
from .policy import choose_stage_reference

ARMS = ('read_reference', 'stage_reference')


def order():
    return [dict(task_id=t['id'], evidence=e, budget=b, commit_fault=c, semantic_fault=s, arm=a)
            for t, e, b, c, s, a in itertools.product(tasks(), ('E0', 'E1'), (1, 2, 3),
                                                     (False, True), (False, True), ARMS)]


def execute(task, folder, cell):
    env = SemanticEnv(task, folder, **{k: cell[k] for k in ('evidence', 'budget', 'commit_fault', 'semantic_fault')})
    selector = choose_stage_reference if cell['arm'] == 'stage_reference' else lambda o: choose(o, 'task_semantic')
    while not env.terminal:
        observation = env.observation()
        decision = selector(observation)
        if decision['action'] in ('inspect', 'inputs', 'catalog', 'status') and not observation['remaining']['checks']:
            decision = {'action': 'escalate'}
        env.step(decision['action'], decision.get('params', {}))
    return {**cell, **evaluate(env)}


def summarize(rows):
    groups = {}
    for r in rows:
        key = '|'.join(str(r[k]) for k in ('task_id', 'evidence', 'budget', 'semantic_fault', 'arm'))
        g = groups.setdefault(key, {'executions': 0, 'safe_complete': 0, 'checks': 0, 'mutations': 0,
                                    'decisions': 0, 'response_bytes': 0})
        g['executions'] += 1
        g['safe_complete'] += int(r['safe_complete'])
        for k in ('checks', 'mutations', 'decisions', 'response_bytes'):
            g[k] += r['cost'][k]
    return {'executions': len(rows), 'task_clusters': 3, 'strata': groups,
            'scientific_gate': 'HOLD', 'api_requests': 0, 'model_improvement_claim': False}


def code_hashes():
    paths = []
    for package in ('semantic', 'clarity', 'evidence', 'surface'):
        paths.extend((REPO / 'faultda_bench' / package).glob('*.py'))
    return {p.relative_to(REPO).as_posix(): sha(p) for p in sorted(paths)}


def protocol():
    ts = tasks()
    return {'version': VERSION, 'order': order(), 'tasks': ts, 'code_sha256': code_hashes(),
            'source_sha256': {t['source_path']: t['source_sha256'] for t in ts},
            'hypothesis': 'staging output is legal evidence; reduce read calls but charge staging writes',
            'primary_comparison': 'E1 budget 2 safe completion, separately per task cluster',
            'cost_control': 'report every cost dimension; E1 budget 3 correct and wrong initial states separately',
            'scope': 'baseline completeness audit; three old source-confounded tasks; no novelty or model claim',
            'stop_rule': 'keep HOLD; do not expand data or model calls based on this deterministic baseline correction',
            'api_requests': 0}


def run(output):
    output = Path(output)
    pp, tp = output.with_suffix('.protocol.json'), output.with_suffix('.jsonl')
    if any(p.exists() for p in (output, pp, tp)):
        raise FileExistsError('use new output paths')
    frozen = protocol()
    write_json(pp, frozen)
    mapping = {t['id']: t for t in frozen['tasks']}
    with tempfile.TemporaryDirectory(prefix='faultda_surface_') as folder:
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
