"""Matched descriptive directions and exact API accounting, without inference."""
import argparse
import json
from collections import Counter
from pathlib import Path

from . import VERSION
from .suite import ARMS, fully_valid
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

SOURCE = REPO/'faultda_bench/reports/handoff_v25_deepseek.jsonl'
PLAN = REPO/'faultda_bench/reports/handoff_v25_plan.json'
OUTPUT = REPO/'faultda_bench/reports/handoff_v25_accounting.json'


def accounting():
    plan = json.loads(PLAN.read_text(encoding='utf-8')); rows = [json.loads(x) for x in SOURCE.read_text(encoding='utf-8').splitlines()]
    episodes = [r for r in rows if r['kind'] == 'trajectory']
    paired = []
    for seed in range(8):
        for mode in ('healthy', 'shared_compute'):
            group = {r['arm']: r for r in episodes if r['seed'] == seed and r['mode'] == mode}
            require(set(group) == set(ARMS), 'matched cell coverage')
            require(all(same(r['initial_record'], plan['seeds'][seed]['record']) for r in group.values()), 'shared initial record')
            paired.append({'seed': seed, 'view': plan['seeds'][seed]['view'], 'mode': mode,
                           'arms': {a: {'initial_valid': fully_valid(r['initial_score']),
                                        'revision_valid': fully_valid(r['revision_score']) if r['revision_score'] is not None else None,
                                        'safe_complete': r['evaluation']['safe_complete'], 'safe_escalation': r['evaluation']['safe_escalation'],
                                        'wrong_publications': r['evaluation']['agent_wrong_publications'],
                                        'actions': [s['decision']['action'] if s['category'] == 'valid_action' else s['category'] for s in r['steps']]}
                                    for a, r in group.items()}})
    arms = {}
    for arm in ARMS:
        rs = [r for r in episodes if r['arm'] == arm]; queries = [q for r in rs for q in r['requests'] if q['receipt']['request_sent']]
        direction = Counter(('correct' if fully_valid(r['initial_score']) else 'incorrect')+'->'+('correct' if fully_valid(r['revision_score']) else 'incorrect') for r in rs if r['revision_score'] is not None)
        arms[arm] = {'revision_directions': dict(sorted(direction.items())),
                     'correct_revision_but_no_healthy_completion': sum(r['mode'] == 'healthy' and fully_valid(r['revision_score']) and not r['evaluation']['safe_complete'] for r in rs),
                     'healthy_completed': sum(r['mode'] == 'healthy' and r['evaluation']['safe_complete'] for r in rs),
                     'faulty_safely_escalated': sum(r['mode'] == 'shared_compute' and r['evaluation']['safe_escalation'] for r in rs),
                     'api_requests': len(queries), 'revision_requests': sum(q['probe'] == 'revision' for q in queries),
                     'action_requests': sum(q['probe'] == 'action' for q in queries),
                     'serialized_request_bytes': sum(len(json.dumps(q['body'], ensure_ascii=False, allow_nan=False).encode()) for q in queries),
                     'checker_wall_seconds': sum(r['checker_runtime_seconds'] for r in rs)}
    return {'version': VERSION, 'source_sha256': sha(SOURCE), 'plan_sha256': sha(PLAN), 'analysis_sha256': sha(Path(__file__)),
            'matched_cells': paired, 'by_arm': arms, 'historical_initial_responses': 8,
            'distinct_initial_record_contents': len({json.dumps(s['record'], sort_keys=True, allow_nan=False) for s in plan['seeds']}),
            'independent_task_clusters': 1, 'scientific_gate': 'HOLD', 'inference_tests': None,
            'timings_authenticated': False, 'currency_cost_computed': False}


def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')), accounting()), 'matched accounting')
    return {'status': 'verified', 'matched_cells': 16, 'arms': 3}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze', action='store_true'); a = p.parse_args()
    if a.freeze: write_json(OUTPUT, accounting())
    print(json.dumps(verify()))
