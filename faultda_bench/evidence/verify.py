"""Audit frozen coverage, public facts, costs and replayed effects without API calls."""
import argparse
import itertools
import json
from pathlib import Path
import tempfile

from ..semantic.tasks import REPO, sha
from ..semantic.oracle import evaluate
from .core import STATES, prepare, present, observed_facts, fact_score
from .run import summary


def verify(path):
    path = Path(path)
    result = json.loads(path.read_text(encoding='utf-8'))
    protocol_path = path.parent / result['protocol']
    journal = path.parent / result['journal']
    assert sha(protocol_path) == result['protocol_sha256'], 'protocol checksum'
    assert sha(journal) == result['journal_sha256'], 'journal checksum'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    for name, digest in protocol['code_sha256'].items():
        assert sha(REPO / name) == digest, name
    rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]
    taskmap = {t['id']: t for t in protocol['task_snapshot']}
    policies = ('deepseek',) if protocol['api'] else ('task_semantic', 'stop_all', 'escalate_all')
    expected = set(itertools.product(taskmap, STATES, ('raw', 'indexed'), policies))
    keys = [(r['task_id'], r['state'], r['presentation'], r['policy']) for r in rows]
    assert set(keys) == expected and len(keys) == len(expected), 'coverage'
    assert len(rows) == result['episodes'] == len(protocol['order'])
    assert summary(rows) == result['summary'], 'aggregation'
    assert sum(len(r['api_calls']) for r in rows) == result['action_requests'] <= protocol['max_action_calls']
    assert result['fact_requests'] == (len(rows) if protocol['api'] else 0) <= protocol['max_fact_calls']
    with tempfile.TemporaryDirectory(prefix='faultda_evidence_replay_') as temporary:
        for i, (row, job) in enumerate(zip(rows, protocol['order'])):
            assert all(row[k] == v for k, v in job.items()), 'order'
            assert len(row['api_calls']) <= protocol['per_episode_action_calls']
            env = prepare(taskmap[row['task_id']], Path(temporary) / str(i), row['state'])
            initial = env.observation()
            assert present(initial, row['presentation']) == row['initial_observation'], 'public snapshot'
            assert env.cost == row['prefix_cost'] and len(env.history) == row['prefix_length']
            if protocol['api']:
                reference = observed_facts(initial)
                assert row['fact_reference'] == reference
                assert row['fact_score'] == fact_score(row['fact_answer'], reference)
            for event in row['trace'][row['prefix_length']:]:
                env.step(event['action'], event['params'])
                assert env.history[-1] == event, 'tool replay'
            if row['terminal'] in ('provider_error', 'api_budget_exceeded'):
                env.terminal = row['terminal']
            for key, value in evaluate(env).items():
                assert row[key] == value, f'episode {i}: {key}'
            assert row['continuation_cost'] == {k: env.cost[k] - row['prefix_cost'][k] for k in env.cost}
    return {'episodes': len(rows), 'status': 'verified', 'replayed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    print(json.dumps(verify(parser.parse_args().report)))
