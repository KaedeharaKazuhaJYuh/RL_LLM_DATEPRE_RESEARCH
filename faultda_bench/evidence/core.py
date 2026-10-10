import copy

from ..clarity.tasks import clarify
from ..semantic.compute import parameters
from ..semantic.environment import SemanticEnv
from ..semantic.tasks import load

STATES = ('ready', 'candidate', 'opaque', 'conflict')
FACTS = ('observed_revision', 'observed_active_count', 'stage_id', 'stage_version', 'access_unavailable')


def tasks():
    return [clarify(t) for t in load() if t['id'].endswith('-01')]


def prepare(task, folder, state):
    if state not in STATES:
        raise ValueError('unknown snapshot state')
    env = SemanticEnv(task, folder, commit_fault=True, semantic_fault=state != 'ready',
                      evidence='E2' if state == 'opaque' else 'E0', budget=6)
    env.step('inspect')
    if state != 'opaque':
        env.step('stage', parameters(task['contract'], task['catalog']))
    if state == 'conflict':
        # A concurrent actor commits after the observation. The model does not
        # receive this private fact; CAS or a new inspection can reveal it.
        record = env.history[-1]['response']
        record = {k: v for k, v in record.items() if k not in ('ok', 'stage_id')}
        env._commit(record, 'concurrent-writer', 1, 'replace', 'environment')
    return env


def present(observation, mode):
    observation = copy.deepcopy(observation)
    if mode == 'raw':
        return observation
    if mode != 'indexed':
        raise ValueError('unknown presentation')
    groups = {}
    for position, event in enumerate(observation.pop('history')):
        groups.setdefault(event['action'], []).append({'position': position, 'event': event})
    observation['events_by_action'] = groups
    return observation


def restore(observation):
    observation = copy.deepcopy(observation)
    if 'events_by_action' in observation:
        events = [e for group in observation.pop('events_by_action').values() for e in group]
        positions = [e['position'] for e in events]
        if sorted(positions) != list(range(len(events))):
            raise ValueError('invalid event index')
        observation['history'] = [e['event'] for e in sorted(events, key=lambda x: x['position'])]
    return observation


def observed_facts(observation):
    """Reference is derived from legal observations, never hidden ledger state."""
    result = dict.fromkeys(FACTS)
    result['access_unavailable'] = False
    for event in restore(observation)['history']:
        response = event['response']
        if response.get('ok') and event['action'] in ('inspect', 'status'):
            result['observed_revision'] = response['revision']
            result['observed_active_count'] = response['active_count']
        if response.get('ok') and event['action'] == 'stage':
            result['stage_id'] = response['stage_id']
            result['stage_version'] = response['version']
        if 'storage access unavailable' in response.get('error', ''):
            result['access_unavailable'] = True
    return result


def fact_score(answer, expected):
    if not isinstance(answer, dict):
        return {'correct_fields': 0, 'fields': len(FACTS), 'exact': False}
    correct = sum(k in answer and type(answer[k]) is type(expected[k]) and answer[k] == expected[k] for k in FACTS)
    return {'correct_fields': correct, 'fields': len(FACTS),
            'exact': correct == len(FACTS) and set(answer) == set(FACTS)}
