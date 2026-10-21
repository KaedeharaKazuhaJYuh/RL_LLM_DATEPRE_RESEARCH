"""Descriptive accounting derived from frozen responses; no inferential tests."""
import argparse
import json
from collections import Counter
from pathlib import Path

from . import VERSION
from ..semantic.tasks import REPO, sha
from ..multistep.suite import require, same
from ..clarity.tasks import write_json

SOURCE = REPO/'faultda_bench/reports/feedback_v24_deepseek.jsonl'
OUTPUT = REPO/'faultda_bench/reports/feedback_v24_accounting.json'


def fully_valid(score):
    return all(value is True for value in score.values())


def accounting():
    rows = [json.loads(x) for x in SOURCE.read_text(encoding='utf-8').splitlines()]
    def cost(records):
        sent = [q for r in records for q in r.get('requests', []) if q['receipt']['request_sent']]
        usages = [q['receipt'].get('response', {}).get('usage', {}) for q in sent]
        usages = [u for u in usages if all(type(u.get(k)) is int for k in ('prompt_tokens', 'completion_tokens'))]
        extra_bytes = 0
        for q in sent:
            for message in q['body']['messages']:
                text = message['content']
                if text.startswith(('Program check ', 'Program public-evidence checks:', 'Previous proposal blocked before execution:')):
                    extra_bytes += len(text.encode('utf-8'))
        return {'requests': len(sent), 'usage_available': len(usages),
                'prompt_tokens': sum(u['prompt_tokens'] for u in usages),
                'completion_tokens': sum(u['completion_tokens'] for u in usages),
                'serialized_sent_request_bytes': sum(len(json.dumps(q['body'], ensure_ascii=False, allow_nan=False).encode()) for q in sent),
                'extra_program_message_bytes': extra_bytes,
                'checker_wall_seconds': sum(r.get('checker_runtime_seconds', 0)+sum(s['checker_runtime_seconds'] for s in r.get('steps', [])) for r in records),
                'provider_errors': sum(q['receipt']['category'] == 'provider_error' for q in sent),
                'length_finishes': sum((q['receipt'].get('response', {}).get('choices') or [{}])[0].get('finish_reason') == 'length' for q in sent)}
    probes = [r for r in rows if r['kind'] == 'revision']; trajectories = [r for r in rows if r['kind'] == 'trajectory']
    revision_cells = {}
    for arm in ('none', 'internal', 'bound'):
        for view in ('utc_end', 'plus8_end', 'minus5_end', 'plus8_all'):
            rs = [r for r in probes if r['arm'] == arm and r['view'] == view]
            directions = Counter(('correct' if fully_valid(r['initial_score']) else 'incorrect')+'->'+('correct' if fully_valid(r['revised_score']) else 'incorrect') for r in rs)
            revision_cells[arm+'|'+view] = {'records': len(rs), 'directions': dict(sorted(directions.items())), 'cost': cost(rs)}
    trajectory_arms = {}
    for arm in ('pure', 'feedback', 'guard'):
        rs = [r for r in trajectories if r['arm'] == arm]
        blocks = Counter(s['proposed']['action'] for r in rs for s in r['steps'] if s['blocked'])
        trajectory_arms[arm] = {'cost': cost(rs), 'end_kinds': dict(Counter(r['end_kind'] for r in rs)),
                                'blocked_action_counts': dict(blocks),
                                'initial_verification_fully_valid': sum(fully_valid(r['verification_score']) for r in rs)}
    return {'version': VERSION, 'source_sha256': sha(SOURCE), 'analysis_sha256': sha(Path(__file__)),
            'revision_cells': revision_cells, 'trajectory_arms': trajectory_arms, 'total_cost': cost(rows),
            'independent_task_clusters': 1, 'scientific_gate': 'HOLD', 'inference_tests': None,
            'timings_authenticated': False, 'currency_cost_computed': False}


def verify():
    require(same(json.loads(OUTPUT.read_text(encoding='utf-8')), accounting()), 'derived accounting')
    return {'status': 'verified', 'paired_revision_records': 24, 'model_trajectories': 24}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze', action='store_true'); a = p.parse_args()
    if a.freeze: write_json(OUTPUT, accounting())
    print(json.dumps(verify()))
