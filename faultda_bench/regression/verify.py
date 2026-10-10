"""Verify coverage and replay all effects even when an altered journal is rehashed."""
import argparse
import itertools
import json
from pathlib import Path
import tempfile

from ..evidence.core import tasks
from ..semantic.environment import SemanticEnv
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, MANIFEST, sha
from . import VERSION
from .suite import plan, summary, validate


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def same(left, right):
    # Python equality treats True == 1; frozen JSON evidence must preserve types.
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def sibling(path, name):
    require(isinstance(name, str) and Path(name).name == name, 'invalid artifact path')
    return path.parent / name


def verify(report):
    report = Path(report)
    result = read(report)
    protocol_path, journal = sibling(report, result['protocol']), sibling(report, result['journal'])
    require(sha(protocol_path) == result['protocol_sha256'], 'protocol checksum')
    require(sha(journal) == result['journal_sha256'], 'journal checksum')
    protocol = read(protocol_path)
    require(protocol['version'] == result['version'] == VERSION, 'version')
    require(protocol['api_requests'] == result['api_requests'] == 0, 'API scope')
    require(protocol['initial_mutations'] == 1 and protocol['max_total_mutations'] == 6 and
            protocol['checks_budget'] == 6 and protocol['deduplicate'] is False, 'environment configuration')
    require(sha(MANIFEST) == protocol['source_manifest_sha256'], 'task source manifest')
    for name, digest in protocol['code_sha256'].items():
        target = (REPO / name).resolve()
        require(target.is_relative_to(REPO.resolve()), 'invalid code path')
        require(sha(target) == digest, 'code changed: ' + name)
    require(protocol['task_snapshot'] == tasks(), 'frozen task snapshot')
    taskmap = {t['id']: t for t in protocol['task_snapshot']}
    require(len(taskmap) == 3 and {t['contract']['family'] for t in taskmap.values()} ==
            {'group', 'window', 'version'}, 'intent coverage')
    expected_sources = {t['source_path']: t['source_sha256'] for t in taskmap.values()}
    require(protocol['source_sha256'] == expected_sources, 'source coverage')
    for name, digest in expected_sources.items():
        require(sha(REPO / name) == digest, 'source changed: ' + name)
    rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]
    keys = [(r['task_id'], r['reuse_candidate']) for r in rows]
    require(len(keys) == 6 and set(keys) == set(itertools.product(taskmap, (True, False))), 'case coverage')
    require(len(protocol['order']) == len(protocol['plans']) == len(rows), 'plan coverage')
    require(result['summary'] == summary(rows), 'summary')
    with tempfile.TemporaryDirectory(prefix='faultda_regression_replay_') as directory:
        for i, (row, job, frozen_plan) in enumerate(zip(rows, protocol['order'], protocol['plans'])):
            require(type(row['reuse_candidate']) is bool, 'case type')
            task = taskmap[row['task_id']]
            require(row['source_id'] == task['source_id'] and row['family'] == task['contract']['family'],
                    'case source attribution')
            require(job == {'task_id': row['task_id'], 'reuse_candidate': row['reuse_candidate']}, 'order')
            actions = plan(taskmap[row['task_id']], row['reuse_candidate'])
            require(frozen_plan == {**job, 'actions': actions}, 'frozen plan')
            env = SemanticEnv(taskmap[row['task_id']], Path(directory) / str(i),
                              commit_fault=False, semantic_fault=True, evidence='E0', budget=6)
            states = []
            for event in row['trace']:
                require(not env.terminal, 'actions after termination')
                index = len(env.history)
                require(index < len(actions) and {'action': event['action'], 'params': event['params']} ==
                        actions[index], 'planned action')
                env.step(event['action'], event['params'])
                require(same(env.history[-1], event), 'tool response replay')
                if event['action'] == 'publish':
                    states.append(evaluate(env)['terminal_correct'])
            require(env.terminal is not None, 'incomplete trace')
            require(same(states, row['post_publication_correctness']), 'state transitions')
            require(actions[len(env.history):] == row['unexecuted_actions'], 'unexecuted plan')
            for key, value in evaluate(env).items():
                require(same(row[key], value), f'effect replay: {key}')
            validate(row)
    return {'version': VERSION, 'cases': len(rows), 'status': 'verified', 'replayed': True, 'api_requests': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('report', type=Path)
    print(json.dumps(verify(parser.parse_args().report)))
