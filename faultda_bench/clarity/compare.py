"""Paired contract-clarity diagnostic; identical tools, data, oracle and system prompt."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import tempfile

from ..semantic.deepseek import Client, SYSTEM
from ..semantic.environment import SemanticEnv
from ..semantic.oracle import evaluate
from ..semantic.tasks import MANIFEST as V1_MANIFEST, REPO, load as load_v1, sha
from . import VERSION
from .tasks import clarify, code_hashes, write_json


def summaries(rows):
    arms = {}
    for arm in ('original', 'explicit'):
        group = [r for r in rows if r['arm'] == arm]
        arms[arm] = {'episodes': len(group), 'complete': sum(r['contract_complete'] for r in group),
                     'terminal_correct': sum(r['terminal_correct'] for r in group),
                     'safe_complete': sum(r['safe_complete'] for r in group),
                     'escalate': sum(r['terminal'] == 'escalate' for r in group),
                     'false_completion': sum(r['false_completion'] for r in group),
                     'provider_error': sum(r['terminal'] == 'provider_error' for r in group),
                     'api_budget_exceeded': sum(r['terminal'] == 'api_budget_exceeded' for r in group),
                     'requests': sum(len(r['api_calls']) for r in group),
                     'parse_errors': sum(c.get('parse_error', False) for r in group for c in r['api_calls']),
                     'tokens': sum(c.get('usage', {}).get('total_tokens', 0) for r in group for c in r['api_calls']),
                     'models': sorted({c['model'] for r in group for c in r['api_calls'] if c.get('model')}),
                     'by_task': {t: {'complete': sum(r['contract_complete'] for r in group if r['task_id'] == t),
                                    'episodes': sum(r['task_id'] == t for r in group)} for t in sorted({r['task_id'] for r in group})}}
    pairs = {}
    for row in rows:
        key = (row['task_id'], row['commit_fault'], row['semantic_fault'])
        if row['arm'] in pairs.setdefault(key, {}):
            raise ValueError('duplicate paired episode')
        pairs[key][row['arm']] = row
    discordant = {'explicit_only': 0, 'original_only': 0, 'both': 0, 'neither': 0}
    for pair in pairs.values():
        if set(pair) != {'original', 'explicit'}:
            raise ValueError('incomplete pair')
        a, b = pair['original']['contract_complete'], pair['explicit']['contract_complete']
        discordant['both' if a and b else 'explicit_only' if b else 'original_only' if a else 'neither'] += 1
    return {'arms': arms, 'paired_completion': discordant, 'pairs': len(pairs),
            'completion_difference': ((arms['explicit']['complete'] - arms['original']['complete']) / len(pairs)
                                      if pairs else None)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=REPO / 'work/clarity_v2_comparison.json')
    args = parser.parse_args()
    protocol_path = args.output.with_suffix('.protocol.json')
    journal_path = args.output.with_suffix('.journal.jsonl')
    if any(p.exists() for p in (args.output, protocol_path, journal_path)):
        parser.error('output already exists; use a new path, do not overwrite a prior run')
    tasks = {t['id']: t for t in load_v1() if t['id'].endswith('-01')}
    rng = random.Random(20261010)
    pairs = [(t, c, s) for t in tasks for c in (False, True) for s in (False, True)]
    rng.shuffle(pairs)
    jobs = []
    for task_id, c, s in pairs:
        arms = ['original', 'explicit']
        rng.shuffle(arms)
        jobs.extend({'task_id': task_id, 'commit_fault': c, 'semantic_fault': s, 'arm': arm} for arm in arms)
    client = Client(max_calls=192)
    protocol = {'version': VERSION, 'created_utc': datetime.now(timezone.utc).isoformat(),
                'scope': 'exploratory paired contract-clarity diagnostic, not new model or RL',
                'hypothesis': 'Explicit field aliases and output schema may reduce avoidable escalation. Bundle effect only.',
                'intervention_fields': ['contract.input_binding', 'contract.output'],
                'primary': 'paired difference in contract completion, all 12 pairs retained',
                'source_clusters': 3, 'independent_instances': 3, 'confirmation': False,
                'model': client.model, 'temperature': 0, 'max_tokens': 800, 'system': SYSTEM,
                'evidence': 'E0', 'budget': 6, 'deduplicate': False, 'per_episode_call_cap': 8,
                'global_call_cap': 192, 'automatic_retries': 0, 'concurrency': 2,
                'original_manifest_sha256': sha(V1_MANIFEST), 'code_sha256': code_hashes(),
                'order': jobs, 'limitations': ['post-v1 diagnostic', 'single model', 'extra explanation changes input token count',
                                             'no model RNG coupling guarantee', 'no independent human review']}
    write_json(protocol_path, protocol)
    with tempfile.TemporaryDirectory(prefix='faultda_clarity_') as temporary:
        def run(index_job):
            index, job = index_job
            task = tasks[job['task_id']]
            if job['arm'] == 'explicit':
                task = clarify(task)
            env = SemanticEnv(task, Path(temporary) / str(index), commit_fault=job['commit_fault'],
                              semantic_fault=job['semantic_fault'], evidence='E0', budget=6)
            started = datetime.now(timezone.utc).isoformat()
            calls = []
            while not env.terminal:
                if len(calls) >= 8:
                    env.terminal = 'api_budget_exceeded'
                    break
                choice, metadata = client.choose(env.observation())
                calls.append(metadata)
                if choice is None:
                    env.terminal = 'provider_error'
                else:
                    env.step(choice['action'], choice.get('params'))
            result = {**job, 'order_index': index, 'source_id': task['source_id'], 'started_utc': started,
                      'ended_utc': datetime.now(timezone.utc).isoformat(), **evaluate(env), 'api_calls': calls}
            print(json.dumps({'index': index, **job, 'terminal': env.terminal,
                              'complete': result['contract_complete'], 'calls': len(calls)}), flush=True)
            return result
        rows = []
        with journal_path.open('xb') as journal, ThreadPoolExecutor(max_workers=2) as pool:
            for row in pool.map(run, enumerate(jobs)):
                journal.write((json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n').encode())
                journal.flush()
                rows.append(row)
    write_json(args.output, {'version': VERSION, 'protocol': protocol_path.name, 'protocol_sha256': sha(protocol_path),
                             'journal': journal_path.name, 'journal_sha256': sha(journal_path),
                             'requests': client.calls, 'summary': summaries(rows), 'episodes': rows})


if __name__ == '__main__':
    main()
