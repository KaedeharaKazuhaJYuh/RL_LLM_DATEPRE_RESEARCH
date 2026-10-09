"""Independent result aggregation, exact coverage and optional effect replay."""
import argparse
import gzip
import itertools
import json
from pathlib import Path
import tempfile

from ..semantic.environment import SemanticEnv
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, ROOT, MANIFEST as V1_MANIFEST, load as load_v1, sha
from .tasks import MANIFEST, load, clarify
from .offline import summaries as offline_summaries
from .compare import summaries as paired_summaries


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify(report, replay=False):
    report = Path(report)
    result = read(report)
    protocol_path = report.parent / result['protocol']
    if sha(protocol_path) != result['protocol_sha256']:
        raise ValueError('protocol checksum mismatch')
    protocol = read(protocol_path)
    for relative, checksum in protocol['code_sha256'].items():
        if sha(REPO / relative) != checksum:
            raise ValueError('implementation changed: ' + relative)
    paired = 'journal' in result
    if paired:
        journal = report.parent / result['journal']
        if sha(journal) != result['journal_sha256'] or sha(V1_MANIFEST) != protocol['original_manifest_sha256']:
            raise ValueError('paired source checksum mismatch')
        rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]
        if rows != result['episodes'] or paired_summaries(rows) != result['summary']:
            raise ValueError('paired summary mismatch')
        if len(rows) != len(protocol['order']):
            raise ValueError('missing paired episode')
        for row, planned in zip(rows, protocol['order']):
            if any(row[key] != value for key, value in planned.items()):
                raise ValueError('paired order or condition mismatch')
            if len(row['api_calls']) > protocol['per_episode_call_cap']:
                raise ValueError('episode request budget exceeded')
        if sum(len(r['api_calls']) for r in rows) != result['requests'] or result['requests'] > protocol['global_call_cap']:
            raise ValueError('global request accounting mismatch')
        tasks = {t['id']: t for t in load_v1()}
    else:
        audit = report.parent / result['audit']['file']
        if sha(audit) != result['audit']['sha256'] or sha(MANIFEST) != protocol['manifest_sha256']:
            raise ValueError('offline source checksum mismatch')
        rows = [json.loads(line) for line in gzip.decompress(audit.read_bytes()).decode().splitlines()]
        if len(rows) != result['audit']['episodes'] or offline_summaries(rows) != result['summaries']:
            raise ValueError('offline summary mismatch')
        keys = [(r['task_id'], r['policy'], r['evidence'], r['budget'], r['commit_fault'], r['semantic_fault']) for r in rows]
        expected = set(itertools.product(protocol['task_ids'], protocol['policies'], protocol['evidence'], protocol['budgets'], (False, True), (False, True)))
        if set(keys) != expected or len(keys) != len(expected):
            raise ValueError('missing or duplicated factorial cell')
        if any(r['deduplicate'] != protocol['deduplicate'] for r in rows):
            raise ValueError('deduplication condition changed')
        tasks = {t['id']: t for t in load()}
    if replay:
        with tempfile.TemporaryDirectory(prefix='faultda_clarity_replay_') as temporary:
            for i, row in enumerate(rows):
                task = tasks[row['task_id']]
                if paired and row['arm'] == 'explicit':
                    task = clarify(task)
                env = SemanticEnv(task, Path(temporary) / str(i),
                                  commit_fault=row['commit_fault'], semantic_fault=row['semantic_fault'],
                                  evidence=protocol['evidence'] if paired else row['evidence'],
                                  budget=protocol['budget'] if paired else row['budget'], deduplicate=False)
                for step in row['trace']:
                    env.step(step['action'], step['params'])
                    if env.history[-1]['response'] != step['response']:
                        raise ValueError(f'tool response changed: episode {i}')
                if row['terminal'] in ('provider_error', 'api_budget_exceeded'):
                    env.terminal = row['terminal']
                for key, value in evaluate(env).items():
                    if row[key] != value:
                        raise ValueError(f'oracle result changed: episode {i}, {key}')
    return {'episodes': len(rows), 'replayed': replay, 'status': 'verified'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    parser.add_argument('--replay', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.report, args.replay)))
