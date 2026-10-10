"""Replay effects, public advice inputs, judgement scores and coverage offline."""
import argparse
import itertools
import json
from pathlib import Path
import tempfile

from ..semantic.tasks import REPO, sha
from ..semantic.oracle import evaluate
from .core import STATES, ARMS, prepare, public_input, judgement_reference, score_judgement, transition
from .run import summary


def require(condition, message):
    if not condition:
        raise ValueError(message)


def verify(path):
    path = Path(path)
    result = json.loads(path.read_text(encoding='utf-8'))
    protocol_path, journal = path.parent / result['protocol'], path.parent / result['journal']
    require(sha(protocol_path) == result['protocol_sha256'], 'protocol checksum')
    require(sha(journal) == result['journal_sha256'], 'journal checksum')
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    for name, digest in protocol['code_sha256'].items():
        require(sha(REPO / name) == digest, 'code changed: ' + name)
    rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]
    taskmap = {t['id']: t for t in protocol['task_snapshot']}
    policies = ('deepseek',) if protocol['api'] else ('task_semantic', 'stop_all', 'escalate_all')
    expected = set(itertools.product(taskmap, STATES, ARMS, policies))
    keys = [(r['task_id'], r['state'], r['arm'], r['policy']) for r in rows]
    require(set(keys) == expected and len(keys) == len(expected), 'coverage')
    require(len(rows) == result['episodes'] == len(protocol['order']), 'episode count')
    require(summary(rows) == result['summary'], 'summary')
    require(sum(len(r['api_calls']) for r in rows) == result['action_requests'] <= protocol['max_action_calls'], 'action budget')
    require(result['judge_requests'] == (len(rows) if protocol['api'] else 0) <= protocol['max_judge_calls'], 'judge budget')
    with tempfile.TemporaryDirectory(prefix='faultda_decision_replay_') as directory:
        for index, (row, job) in enumerate(zip(rows, protocol['order'])):
            require(all(row[k] == v for k, v in job.items()), 'order')
            require(len(row['api_calls']) <= protocol['per_episode_action_calls'], 'episode budget')
            env = prepare(taskmap[row['task_id']], Path(directory) / str(index), row['state'])
            require(env.observation() == row['initial_observation'], 'initial observation')
            require(env.cost == row['prefix_cost'] and len(env.history) == row['prefix_length'], 'prefix')
            if protocol['api']:
                reference = judgement_reference(env)
                require(reference == row['judgement_reference'], 'reference')
                require(score_judgement(row['judgement_answer'], reference) == row['judgement_score'], 'judgement score')
            events = row['trace'][row['prefix_length']:]
            require(len(events) == len(row['transitions']), 'transition count')
            require(len(row['action_inputs']) == len(events) + (row['terminal'] == 'provider_error'), 'input count')
            if protocol['api']:
                require(len(row['action_inputs']) == len(row['api_calls']), 'request input count')
            for i, event in enumerate(events):
                require(public_input(env.observation(), row['arm']) == row['action_inputs'][i], 'public input/advice')
                step = transition(env, {'action': event['action'], 'params': event['params']})
                require(step == row['transitions'][i] and env.history[-1] == event, 'transition replay')
            if row['terminal'] == 'provider_error':
                require(public_input(env.observation(), row['arm']) == row['action_inputs'][-1], 'failed request input')
            if row['terminal'] in ('provider_error', 'api_budget_exceeded'):
                env.terminal = row['terminal']
            for key, value in evaluate(env).items():
                require(row[key] == value, f'episode {index}: {key}')
            require(row['continuation_cost'] == {k: env.cost[k] - row['prefix_cost'][k] for k in env.cost}, 'cost')
    return {'episodes': len(rows), 'replayed': True, 'status': 'verified'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    print(json.dumps(verify(parser.parse_args().report)))
