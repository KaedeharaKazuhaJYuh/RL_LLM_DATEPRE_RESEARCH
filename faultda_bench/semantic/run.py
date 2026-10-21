"""Reproducible offline matrix. No API calls; each policy sees a JSON copy only."""
import argparse
import gzip
import hashlib
import itertools
import json
import tempfile
import time
from collections import defaultdict
from pathlib import Path

from . import VERSION
from .environment import SemanticEnv
from .oracle import evaluate
from .policies import POLICIES, choose
from .tasks import load, ROOT, MANIFEST, sha


def episode(task, folder, policy, **config):
    env = SemanticEnv(task, folder, **config)
    started = time.perf_counter()
    while not env.terminal:
        observation = json.loads(json.dumps(env.observation()))
        choice = choose(observation, policy)
        env.step(choice['action'], choice.get('params'))
    return {'task_id': task['id'], 'source_id': task['source_id'],
            'family': task['contract']['family'], 'policy': policy, **config,
            **evaluate(env), 'wall_seconds': time.perf_counter() - started}


def ratio(n, d):
    return {'numerator': n, 'denominator': d, 'value': n / d if d else None}


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row['policy'], row['evidence'], row['budget'], row['deduplicate'])].append(row)
    summaries = []
    for key, group in sorted(groups.items()):
        policy, evidence, budget, deduplicate = key
        success = sum(r['contract_complete'] for r in group)
        claims = sum(r['terminal'] == 'stop' for r in group)
        false = sum(r['false_completion'] for r in group)
        cells = {}
        for c, s in itertools.product((False, True), repeat=2):
            cell = [r for r in group if r['commit_fault'] == c and r['semantic_fault'] == s]
            cells[f'{int(c)}{int(s)}'] = ratio(sum(not r['contract_complete'] for r in cell), len(cell))
        pair_index = {(r['task_id'], r['commit_fault'], r['semantic_fault']): r for r in group}
        capable = [r for r in group if not r['commit_fault'] and not r['semantic_fault'] and r['contract_complete']]
        conditional = ratio(sum(pair_index[(r['task_id'], True, True)]['contract_complete'] for r in capable), len(capable))
        summaries.append({'policy': policy, 'evidence': evidence, 'budget': budget,
                          'deduplicate': deduplicate, 'episodes': len(group),
                          'contract_completion': ratio(success, len(group)),
                          'safe_completion': ratio(sum(r['safe_complete'] for r in group), len(group)),
                          'forbidden_effect_rate': ratio(sum(r['forbidden_effect'] for r in group), len(group)),
                          'false_completion_among_claims': ratio(false, claims),
                          'false_completion_among_all': ratio(false, len(group)),
                          'safe_escalation_E2': ratio(sum(r['safe_escalation'] for r in group) if evidence == 'E2' else 0,
                                                      len(group) if evidence == 'E2' else 0),
                          'over_escalation_observable': ratio(sum(r['terminal'] == 'escalate' for r in group) if evidence != 'E2' else 0,
                                                              len(group) if evidence != 'E2' else 0),
                          'cost_per_success': {k: sum(r['cost'][k] for r in group) / success if success else None
                                               for k in ('checks', 'mutations', 'decisions', 'response_bytes')},
                          'cells_failure': cells, 'conditional_joint_completion': conditional,
                          'interaction': None if evidence == 'E2' else cells['11']['value'] - cells['10']['value'] - cells['01']['value'] + cells['00']['value']})
    return summaries


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'reports/semantic_v1_results.json')
    args = parser.parse_args()
    rows = []
    tasks = load()
    with tempfile.TemporaryDirectory(prefix='faultda_semantic_') as temporary:
        for task, policy, evidence, budget, dedup, c, s in itertools.product(
                tasks, POLICIES, ('E0', 'E1', 'E2'), (2, 4, 6), (False, True), (False, True), (False, True)):
            rows.append(episode(task, Path(temporary) / str(len(rows)), policy, evidence=evidence, budget=budget,
                                deduplicate=dedup, commit_fault=c, semantic_fault=s))
    result = {'version': VERSION, 'track': 'controlled_binding_program_baselines',
              'manifest_sha256': sha(MANIFEST), 'code_sha256': {p.name: sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
              'source_clusters': len({t['source_id'] for t in tasks}),
              'limitations': ['historical development only', 'no LLM scores', 'no human review yet',
                              'one intent family per source: source and intent are confounded',
                              'three clusters insufficient for confirmatory inference'],
              'summary': summarize(rows)}
    audit = args.output.with_suffix('.jsonl.gz')
    packed = gzip.compress(('\n'.join(json.dumps(r, ensure_ascii=False, allow_nan=False) for r in rows) + '\n').encode(), mtime=0)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    audit.write_bytes(packed)
    result['audit'] = {'file': audit.name, 'sha256': sha(audit), 'episodes': len(rows)}
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps({'episodes': len(rows), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
