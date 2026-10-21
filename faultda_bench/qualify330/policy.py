"""Recovery strategies differ; this is not a check-selection-only ablation."""
import copy
from ..recover325.policy import choose as inspect_first
from ..feedback315.core import state, record_check

POLICIES = ('inspect_first', 'retry_once_reconcile', 'retry_then_stop')


def choose(observation, policy):
    if policy not in POLICIES: raise ValueError('policy')
    if policy == 'inspect_first': return inspect_first(observation, 'verified')
    history = observation['history']
    last_inspect = max((i for i, h in enumerate(history) if h['action'] == 'inspect' and h['response'].get('ok')), default=-1)
    attempts = [h for h in history[last_inspect+1:] if h['action'] == 'publish']
    if attempts and not attempts[-1]['response'].get('ok'):
        if len(attempts) == 1:
            candidate = state(observation)[2].get(attempts[-1]['params'].get('stage_id'), {})
            if record_check(candidate, observation)['pass']:
                return {'action': 'publish', 'params': copy.deepcopy(attempts[-1]['params'])}
        if policy == 'retry_then_stop' and len(attempts) >= 2:
            # Deliberately unsafe assumption: one retry guarantees convergence.
            return {'action': 'stop', 'params': {}}
    return inspect_first(observation, 'verified')
