"""Offline adversarial qualification and explicit independent-review status."""
import argparse
import json
import tempfile
from pathlib import Path

from . import VERSION
from .environment import QualificationEnv, observation
from .policy import choose, POLICIES
from ..recover325.suite import protocol as previous_protocol
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

OUTPUT = REPO/'faultda_bench/reports/qualify_v27_results.json'
DESIGN = REPO/'faultda_bench/protocols/recover_v27_design.json'
PROFILES = {'normal': (0, False), 'before_once': (1, False), 'after_once': (0, True), 'before_twice': (2, False)}


def protocol():
    previous = previous_protocol(); views = {v: previous['views'][v] for v in ('utc_end', 'plus8_end')}
    names = set(previous['code_sha256']) | {'faultda_bench/qualify330/'+n for n in ('__init__.py', 'environment.py', 'policy.py', 'suite.py')}
    return {'version': VERSION, 'revision': 'qualify_v27', 'views': views, 'profiles': PROFILES,
            'order': [{'view': v, 'profile': p, 'checks': b, 'policy': a} for v in views for p in PROFILES for b in (3, 4, 5) for a in POLICIES],
            'source_design_sha256': sha(DESIGN), 'code_sha256': {n: sha(REPO/n) for n in sorted(names)},
            'action_horizon': 8, 'new_api_calls': 0, 'independent_task_clusters': 1, 'scientific_gate': 'HOLD',
            'scope': '72 program executions; compare full recovery strategies and blind retry assumption. Independent human/scientific review remains pending. No model score, RL or equal-actual-cost claim.'}


def prepare(task, folder, profile, checks):
    before, after = PROFILES[profile]
    env = QualificationEnv(task, folder, before_failures=before, after_loss=after, check_budget=checks)
    for action in ('inspect', 'inputs', 'catalog'): env.step(action)
    return env


def episode(task, folder, cell):
    env = prepare(task, folder, cell['profile'], cell['checks']); decisions = []
    for _ in range(8):
        if env.terminal is not None: break
        decision = choose(observation(env), cell['policy']); decisions.append(decision)
        env.step(decision['action'], decision['params'])
    return {**cell, 'decisions': decisions, 'evaluation': evaluate(env)}


def ambiguous_pair(task, folder):
    observations = []; ledgers = []; post_read = []
    for profile in ('before_once', 'after_once'):
        env = prepare(task, folder/profile, profile, 4)
        for _ in range(2):
            decision = choose(observation(env), 'inspect_first'); env.step(decision['action'], decision['params'])
        observations.append(observation(env)); ledgers.append(env.records())
        env.step('inspect'); post_read.append(observation(env))
    require(same(observations[0], observations[1]), 'same public history before reconciliation')
    require(not same(ledgers[0], ledgers[1]), 'different actual commitment')
    decisions = [choose(v, 'inspect_first') for v in post_read]
    require([d['action'] for d in decisions] == ['publish', 'stop'], 'legally different resolved next steps')
    return {'public_histories_equal_before_inspect': True, 'actual_ledgers': ledgers,
            'public_observation_before_inspect': observations[0], 'public_observations_after_inspect': post_read,
            'resolved_decisions': decisions, 'scope': 'Immediate stop cannot distinguish these two states; this does not prove inspect is the only or cheapest possible recovery strategy.'}


def run():
    p = protocol(); rows = []; pairs = {}
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for i, cell in enumerate(p['order']): rows.append(episode(p['views'][cell['view']], root/str(i), cell))
        for view, task in p['views'].items(): pairs[view] = ambiguous_pair(task, root/('pair-'+view))
    def totals(rs):
        return {'executions': len(rs), **{k: sum(int(r['evaluation'][k]) for r in rs) for k in ('safe_complete', 'safe_escalation', 'false_completion', 'agent_wrong_publications', 'duplicate_events')},
                'cost': {k: sum(r['evaluation']['cost'][k] for r in rs) for k in ('checks', 'mutations', 'decisions', 'response_bytes')}}
    return {'version': VERSION, 'protocol': p, 'rows': rows, 'ambiguous_pairs': pairs,
            'summary': {'by_policy': {a: totals([r for r in rows if r['policy'] == a]) for a in POLICIES},
                        'by_budget_policy': {str(b)+'|'+a: totals([r for r in rows if r['checks'] == b and r['policy'] == a]) for b in (3, 4, 5) for a in POLICIES},
                        'new_api_calls': 0, 'scientific_gate': 'HOLD', 'rl_improvement_claim': False},
            'model_execution_decision': {'status': 'not_ready', 'model_run_performed': False,
                'independent_human_review': 'pending', 'independent_scientific_review': 'pending',
                'reasons': ['New fault/trust declaration has not received independent review.',
                            'Original design lacks repeated precommit failures and a retry-once-reconcile strong strategy.',
                            'Local program qualification cannot establish novelty or model/RL improvement.']}}


def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')), run()), 'qualification replay')
    return {'status': 'verified', 'program_executions': 72, 'ambiguous_pairs': 2, 'new_api_calls': 0, 'model_execution_ready': False, 'scientific_gate': 'HOLD'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze', action='store_true'); a = p.parse_args()
    if a.freeze: write_json(OUTPUT, run())
    print(json.dumps(verify()))
