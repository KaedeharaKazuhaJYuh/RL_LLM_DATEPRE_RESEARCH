import argparse
import itertools
import json
import random
import tempfile
from pathlib import Path

from ..clarity.tasks import write_json
from ..evidence.core import tasks
from ..semantic.environment import SemanticEnv
from ..semantic.oracle import evaluate
from ..semantic.policies import choose
from ..semantic.tasks import REPO, sha
from . import VERSION

ARMS = ('fixed', 'random', 'conditional', 'strong')
CHECKS = ('inspect', 'inputs', 'catalog')


def order():
    return [dict(task_id=task['id'], evidence=evidence, commit_fault=commit,
                 semantic_fault=semantic, budget=budget, arm=arm, seed=seed)
            for task, evidence, commit, semantic, budget, arm, seed in itertools.product(
                tasks(), ('E0', 'E1'), (False, True), (False, True), (1, 3), ARMS, (0, 1, 2))]


def execute(task, folder, cell):
    env = SemanticEnv(task, folder, **{k: cell[k] for k in
                      ('evidence', 'commit_fault', 'semantic_fault', 'budget')})
    schedule = list(CHECKS)
    if cell['arm'] == 'random':
        random.Random(cell['seed']).shuffle(schedule)
    checked = 0
    while not env.terminal:
        observation = env.observation()
        # Same public-only semantic executor and stopping criterion in every arm.
        decision = choose(observation, 'task_semantic')
        if decision['action'] in CHECKS:
            if not observation['remaining']['checks']:
                decision = {'action': 'escalate'}
            elif cell['arm'] in ('fixed', 'random'):
                if checked >= len(schedule):
                    decision = {'action': 'escalate'}
                else:
                    decision = {'action': schedule[checked]}
                    checked += 1
        env.step(decision['action'], decision.get('params', {}))
    return {**cell, **evaluate(env)}


def summarize(rows):
    strata = {}
    for row in rows:
        key = '|'.join(str(row[k]) for k in ('task_id', 'evidence', 'budget', 'arm'))
        group = strata.setdefault(key, {'executions': 0, 'safe_complete': 0,
                                        'checks': 0, 'mutations': 0, 'decisions': 0, 'response_bytes': 0})
        group['executions'] += 1
        group['safe_complete'] += int(row['safe_complete'])
        for k in ('checks', 'mutations', 'decisions', 'response_bytes'):
            group[k] += row['cost'][k]
    pairs = {}
    for row in rows:
        key = tuple(row[k] for k in ('task_id', 'evidence', 'budget', 'commit_fault', 'semantic_fault', 'seed'))
        pairs.setdefault(key, {})[row['arm']] = row
    gains = sum(int(p['conditional']['safe_complete']) - int(p['strong']['safe_complete']) for p in pairs.values())
    matched = [p for p in pairs.values() if len({r['cost']['checks'] for r in p.values()}) == 1]
    return {'task_clusters': 3, 'executions': len(rows), 'strata': strata,
            'conditional_minus_strong_safe_completions': gains,
            'all_arm_check_cost_matched_cells': len(matched),
            'cost_matching_is_exploratory_not_causal': True,
            'scientific_gate': 'HOLD', 'api_requests': 0}


def code_hashes():
    paths = []
    for package in ('semantic', 'clarity', 'evidence', 'allocation'):
        paths.extend((REPO / 'faultda_bench' / package).glob('*.py'))
    return {p.relative_to(REPO).as_posix(): sha(p) for p in sorted(paths)}


def run(output):
    output = Path(output)
    protocol_path = output.with_suffix('.protocol.json')
    trace_path = output.with_suffix('.jsonl')
    if any(p.exists() for p in (output, protocol_path, trace_path)):
        raise FileExistsError('use new output paths')
    task_list = tasks()
    protocol = {'version': VERSION, 'hypothesis': 'check allocation must exceed strong semantic rule at comparable actual cost',
                'design': 'negative control: conditional and strong intentionally share selector',
                'order': order(), 'tasks': task_list, 'code_sha256': code_hashes(),
                'source_sha256': {t['source_path']: t['source_sha256'] for t in task_list},
                'decision': 'HOLD if conditional does not exceed strong in all three task clusters; no expansion or API',
                'same_seed_repeats_are_not_independent_samples': True, 'api_requests': 0}
    # Freeze before any episode executes.
    write_json(protocol_path, protocol)
    mapping = {t['id']: t for t in task_list}
    with tempfile.TemporaryDirectory(prefix='faultda_allocation_') as folder:
        rows = [execute(mapping[cell['task_id']], Path(folder) / str(i), cell)
                for i, cell in enumerate(protocol['order'])]
    with trace_path.open('xb') as stream:
        for row in rows:
            stream.write((json.dumps(row, ensure_ascii=False) + '\n').encode())
    result = {'version': VERSION, 'protocol': protocol_path.name, 'protocol_sha256': sha(protocol_path),
              'trace': trace_path.name, 'trace_sha256': sha(trace_path), 'summary': summarize(rows)}
    write_json(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    print(json.dumps(run(parser.parse_args().output)['summary'], ensure_ascii=False))
