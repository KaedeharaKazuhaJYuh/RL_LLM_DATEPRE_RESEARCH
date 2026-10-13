"""Matched public rules; only numerical validation differs."""
from ..feedback315.core import public_input, record_check, state


def metadata_check(record, observation):
    # Same binding validation as the numerical rule, but explicitly omit numbers.
    verdict = record_check(record, observation)
    remaining = [v for v in verdict['violations'] if v != 'numerical_mismatch']
    return {'pass': not remaining, 'violations': remaining}


def choose(observation, policy):
    if policy not in ('verified', 'metadata_only'): raise ValueError('policy')
    history = observation['history']
    publish = max((i for i, h in enumerate(history) if h['action'] == 'publish'), default=-1)
    inspect = max((i for i, h in enumerate(history) if h['action'] == 'inspect' and h['response'].get('ok')), default=-1)
    if publish > inspect and not history[publish]['response'].get('ok'):
        return {'action': 'inspect' if observation['remaining']['checks'] else 'escalate', 'params': {}}
    records, revision, stages, _ = state(observation)
    verify = record_check if policy == 'verified' else metadata_check
    # Do not borrow the stronger helper's numerical history verdict for the
    # metadata ablation. Both policies use their own acceptance predicate.
    historical = any(h['action'] == 'publish' and h['response'].get('ok')
                     and not h['response'].get('deduplicated')
                     and (h['params'].get('mode') != 'replace'
                          or not verify(stages.get(h['params'].get('stage_id'), {}), observation)['pass'])
                     for h in history)
    if historical: return {'action': 'escalate', 'params': {}}
    if records is not None and len(records) == 1 and verify(records[0], observation)['pass']:
        return {'action': 'stop', 'params': {}}
    if stages:
        stage_id = next(reversed(stages)); candidate = stages[stage_id]
        if not verify(candidate, observation)['pass']:
            return {'action': 'escalate', 'params': {}}
        return {'action': 'publish', 'params': {'stage_id': stage_id, 'request_id': 'public-repair',
                                               'expected_revision': revision, 'mode': 'replace'}}
    return {'action': 'stage', 'params': public_input(observation)[0]}
