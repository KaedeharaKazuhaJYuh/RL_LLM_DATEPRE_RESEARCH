"""Deterministic baselines receive only public JSON, never an environment object."""
import math

from .compute import calculate, parameters

POLICIES = ('abstain', 'blind_retry', 'generic_verify', 'version_refresh', 'static_semantic', 'task_semantic')


def choose(observation, policy):
    if policy not in POLICIES:
        raise ValueError('unknown policy')
    history = observation['history']
    responses = {h['action']: h['response'] for h in history}
    if policy == 'abstain':
        return {'action': 'escalate'}
    if any('storage access unavailable' in h['response'].get('error', '') for h in history):
        return {'action': 'escalate'}
    published = responses.get('publish')
    if published and published.get('ok'):
        return {'action': 'stop'}
    # A lost repair acknowledgement must be reconciled, not blindly republished.
    last_publish = max((i for i, h in enumerate(history) if h['action'] == 'publish'), default=-1)
    last_inspect = max((i for i, h in enumerate(history) if h['action'] == 'inspect'), default=-1)
    if last_publish > last_inspect and not (published or {}).get('ok'):
        return {'action': 'inspect'} if observation['remaining']['checks'] else {'action': 'escalate'}
    if policy in ('generic_verify', 'static_semantic', 'version_refresh') and 'status' not in responses:
        return {'action': 'status'}
    if policy == 'generic_verify' and responses.get('status', {}).get('active_count', 0) == 1:
        return {'action': 'stop'}
    if policy == 'blind_retry' and observation['initial_feedback'].get('ok'):
        return {'action': 'stop'}
    inspected = responses.get('inspect', {})
    if policy != 'blind_retry' and not inspected.get('ok'):
        return {'action': 'inspect'} if observation['remaining']['checks'] else {'action': 'escalate'}
    data = inspected if 'versions' in inspected else responses.get('inputs', {})
    catalog = inspected.get('catalog') or responses.get('catalog', {}).get('catalog')
    if catalog is None:
        return {'action': 'catalog'} if observation['remaining']['checks'] else {'action': 'escalate'}
    c = observation['contract']
    params = parameters(c, catalog)
    records = inspected.get('records', [])
    if policy == 'version_refresh' and len(records) == 1 and records[0]['version'] == params['version']:
        return {'action': 'stop'}
    if policy in ('static_semantic', 'task_semantic'):
        if not data.get('versions'):
            return {'action': 'inputs'} if observation['remaining']['checks'] else {'action': 'escalate'}
        expected = calculate(data['versions'][params['version']], data['dimension'], c, params)
        if len(records) == 1 and records[0]['version'] == params['version']:
            actual = records[0]['output']
            if set(actual) == set(expected) and all(math.isclose(actual[k], v, rel_tol=1e-9, abs_tol=1e-9)
                                                   for k, v in expected.items()):
                return {'action': 'stop'}
    staged = responses.get('stage', {})
    if not staged.get('ok'):
        return {'action': 'stage', 'params': params}
    # If a prior publish failed but current report is still wrong, stop rather
    # than guessing new operation identifiers or silently spending extra writes.
    if last_publish >= 0:
        return {'action': 'escalate'}
    return {'action': 'publish', 'params': {'stage_id': staged['stage_id'], 'request_id': 'repair-1',
                                           'expected_revision': inspected.get('revision', 0),
                                           'mode': 'append' if policy == 'blind_retry' else 'replace'}}
