import math

from ..semantic.compute import parameters
from ..semantic.policies import choose


def matches(record, candidate):
    if record.get('version') != candidate.get('version') or record.get('input_sha256') != candidate.get('input_sha256'):
        return False
    actual, expected = record.get('output', {}), candidate.get('output', {})
    return set(actual) == set(expected) and all(
        type(actual[k]) in (int, float) and math.isfinite(actual[k])
        and math.isclose(actual[k], v, rel_tol=1e-9, abs_tol=1e-9) for k, v in expected.items())


def choose_stage_reference(observation):
    """Only public tool observations; staging is charged as a mutation."""
    history = observation['history']
    if any('storage access unavailable' in h['response'].get('error', '') for h in history):
        return {'action': 'escalate'}
    responses = {h['action']: h['response'] for h in history}
    published = responses.get('publish', {})
    if published.get('ok'):
        return {'action': 'stop'}
    last_publish = max((i for i, h in enumerate(history) if h['action'] == 'publish'), default=-1)
    last_inspect = max((i for i, h in enumerate(history) if h['action'] == 'inspect'), default=-1)
    if last_publish > last_inspect:
        return {'action': 'inspect'} if observation['remaining']['checks'] else {'action': 'escalate'}
    inspected = responses.get('inspect', {})
    if not inspected.get('ok'):
        return {'action': 'inspect'} if observation['remaining']['checks'] else {'action': 'escalate'}
    # Use the bundled data when it is already available; do not pad cost.
    if inspected.get('versions'):
        return choose(observation, 'task_semantic')
    catalog = responses.get('catalog', {}).get('catalog')
    if catalog is None:
        return {'action': 'catalog'} if observation['remaining']['checks'] else {'action': 'escalate'}
    candidate = responses.get('stage', {})
    if not candidate.get('ok'):
        return {'action': 'stage', 'params': parameters(observation['contract'], catalog)}
    records = inspected.get('records', [])
    if len(records) == 1 and matches(records[0], candidate):
        return {'action': 'stop'}
    if last_publish >= 0:
        return {'action': 'escalate'}
    return {'action': 'publish', 'params': {'stage_id': candidate['stage_id'],
            'request_id': 'stage-reference-1', 'expected_revision': inspected['revision'], 'mode': 'replace'}}
