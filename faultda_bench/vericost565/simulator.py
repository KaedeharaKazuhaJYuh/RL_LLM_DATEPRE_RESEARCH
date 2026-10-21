"""Episode draws, the public observation function and the abstract training transition."""
import hashlib
import math
import random

from . import costs
from .canon import argmax_first, fsum_

TYPES = ('A', 'B', 'C')
RATES = {'A': (0.90, 0.08, 0.02), 'B': (0.45, 0.50, 0.05), 'C': (0.45, 0.05, 0.50)}
CLASSES = ('none', 'local', 'global')
COUNT_KEYS = ('clean', 'single_part_discrepancy', 'multi_part_discrepancy')
HISTORY_JOBS = 10
P_CC = 0.5
Q_G = 0.5
HORIZON = 6
TRAINING_SEED = 565001
CC_STATES = ('none', 'ok', 'flag_unchecked', 'flag_checked_match', 'flag_checked_mismatch')
GATE_ACTIONS = ('escalate', 'stop', 'publish_patch', 'publish_c1', 'cc',
                'spot_flagged', 'spot_small', 'spot_large', 'full')


def latents(model, parts):
    """The latent alphabet: none, global (one mask in rev-1, every non-empty mask under D1), local."""
    if model not in ('rev1', 'd1'):
        raise ValueError('unknown latent model: ' + str(model))
    out = [('none',)]
    if model == 'rev1':
        out.append(('global', (1 << parts) - 1))
    else:
        out.extend(('global', mask) for mask in range(1, 1 << parts))
    for part in range(parts):
        out.append(('local', part, True))
        out.append(('local', part, False))
    return tuple(out)


LATENTS_REV1 = latents('rev1', 8)


def latent_id(latent):
    if latent[0] == 'none':
        return 'none'
    if latent[0] == 'global':
        return f'global:{latent[1]}'
    return f'local:{latent[1]}:{int(latent[2])}'


def affected_parts(latent, parts):
    if latent[0] == 'none':
        return frozenset()
    if latent[0] == 'global':
        return frozenset(j for j in range(parts) if (latent[1] >> j) & 1)
    return frozenset({latent[1]})


def cc_flagged(latent):
    """The consistency check flags the engine's extra row: visible local faults only, never global."""
    return (latent[1],) if latent[0] == 'local' and latent[2] else ()


def patch_covers(latent, checked, parts):
    """A patch replaces every spot-checked part, so it is correct iff it covers the affected set."""
    return affected_parts(latent, parts) <= frozenset(checked)


def type_posterior(counts):
    """Posterior over deployment types given the public history class counts (prior 1/3 each)."""
    observed = tuple(counts[key] for key in COUNT_KEYS)
    weights = {}
    for name in TYPES:
        rates = RATES[name]
        product = 1.0
        for rate, count in zip(rates, observed):
            product *= rate ** count
        weights[name] = product / 3
    total = fsum_(weights.values())
    if total <= 0:
        raise ValueError('history counts have zero likelihood under every type')
    return {name: weights[name] / total for name in TYPES}


def predictive(counts):
    """The history-predictive class distribution (none, local, global)."""
    posterior = type_posterior(counts)
    return tuple(fsum_([posterior[name] * RATES[name][index] for name in TYPES]) for index in range(3))


def map_type(counts):
    """MAP deployment type of the public history; ties go to the lower letter."""
    posterior = type_posterior(counts)
    return argmax_first([(name, posterior[name]) for name in TYPES])


def latent_prior(profile, counts, model):
    """The prior over latents given the public history: predictive class x part share x cc visibility."""
    parts = len(profile['parts'])
    none, local, glob = predictive(counts)
    prior = {('none',): none}
    if model == 'rev1':
        prior[('global', (1 << parts) - 1)] = glob
    else:
        normalizer = 1 - (1 - Q_G) ** parts
        for mask in range(1, 1 << parts):
            hits = bin(mask).count('1')
            prior[('global', mask)] = glob * Q_G ** hits * (1 - Q_G) ** (parts - hits) / normalizer
    for part in range(parts):
        share = profile['parts'][part]['share']
        prior[('local', part, True)] = local * share * P_CC
        prior[('local', part, False)] = local * share * (1 - P_CC)
    return prior


def _draw_class(rng, rates):
    sample = rng.random()
    total = 0.0
    for index, rate in enumerate(rates):
        total += rate
        if sample < total:
            return CLASSES[index]
    return CLASSES[2]


def _draw_part(rng, profile):
    sample = rng.random()
    total = 0.0
    for part in profile['parts']:
        total += part['share']
        if sample < total:
            return part['part']
    return profile['parts'][-1]['part']


def _draw_mask(rng, parts):
    """Drawn in both models so rev-1 and D1 episodes share steps 1-3 of the design draw order."""
    while True:
        mask = 0
        for part in range(parts):
            if rng.random() < Q_G:
                mask |= 1 << part
        if mask:
            return mask


def _draw(rng, profile, kind):
    history = [_draw_class(rng, RATES[kind]) for _ in range(HISTORY_JOBS)]
    latent_class = _draw_class(rng, RATES[kind])
    part = _draw_part(rng, profile) if latent_class == 'local' else None
    visible = rng.random() < P_CC if latent_class == 'local' else None
    mask = _draw_mask(rng, len(profile['parts']))
    counts = {key: history.count(name) for key, name in zip(COUNT_KEYS, CLASSES)}
    if latent_class == 'none':
        rev1 = d1 = ('none',)
    elif latent_class == 'local':
        rev1 = d1 = ('local', part, visible)
    else:
        rev1, d1 = ('global', (1 << len(profile['parts'])) - 1), ('global', mask)
    return {'profile_id': profile['profile_id'], 'type': kind, 'history_classes': history,
            'counts': counts, 'latent_class': latent_class, 'part': part, 'cc_visible': visible,
            'mask': mask, 'latent': {'rev1': latent_id(rev1), 'd1': latent_id(d1)}}


def episode(profile, kind):
    """The frozen (profile, type) cell; the RNG is seeded from the cell identity alone."""
    if kind not in TYPES:
        raise ValueError('unknown deployment type: ' + str(kind))
    key = 'vericost565|' + profile['profile_id'] + '|' + kind
    rng = random.Random(int(hashlib.sha256(key.encode()).hexdigest()[:16], 16))
    return _draw(rng, profile, kind)


def sample_episode(rng, profiles):
    """Training sampler over development profiles only (seed 565001)."""
    for profile in profiles:
        if profile.get('split') != 'development':
            raise ValueError('non-development profile in training')
    profile = profiles[rng.randrange(len(profiles))]
    return _draw(rng, profile, TYPES[rng.randrange(len(TYPES))])


def observe(profile, latent, action):
    """The latent-dependent part of one action's response; everything else is public."""
    parts = len(profile['parts'])
    name = action[0]
    if name == 'consistency_check':
        return tuple(sorted(cc_flagged(latent)))
    if name == 'full_recompute':
        return tuple(sorted(affected_parts(latent, parts)))
    if name in ('spot_check', 'read_rows'):
        return (action[1], action[1] in affected_parts(latent, parts))
    if name in ('publish', 'stop', 'escalate'):
        return ()
    raise ValueError('unknown action: ' + str(name))


def initial_state(profile, counts, regime_id):
    """The training transition state; the profile is shared, never copied."""
    return {'profile': profile, 'counts': dict(counts), 'regime': regime_id, 'rem': HORIZON,
            'cc': 'none', 'flag': None, 'checked': frozenset(), 'mismatch': frozenset(),
            'spots': 0, 'full': 'none', 'published': None, 'spent': 0.0, 'terminal': None,
            'outcome': {'safe_complete': False, 'false_completion': False, 'forbidden_effect': False}}


def _rows_checked_bucket(state):
    profile = state['profile']
    checked = sum(profile['parts'][j]['rows'] for j in state['checked'])  # int-sum
    fraction = checked / profile['n']
    if fraction == 0:
        return 'none'
    if fraction < 0.25:
        return 'lt25'
    return 'lt50' if fraction < 0.5 else 'ge50'


def abstract_state(state):
    """The Q/gate state key: a pure function of the public history (design 2.6)."""
    counts = state['counts']
    return (tuple(counts[key] for key in COUNT_KEYS), state['profile']['size_bucket'], state['cc'],
            state['spots'], len(state['mismatch']), _rows_checked_bucket(state), state['full'],
            state['rem'])


def state_key(state):
    return '|'.join(str(item) for item in abstract_state(state))


def _resolve_part(state, action):
    unchecked = [p for p in state['profile']['parts'] if p['part'] not in state['checked']]
    if not unchecked:
        return None
    if action == 'spot_flagged':
        flag = state['flag']
        return flag if flag is not None and flag not in state['checked'] else None
    if action == 'spot_large':
        return min(unchecked, key=lambda p: (-p['rows'], p['part']))['part']
    return min(unchecked, key=lambda p: (p['rows'], p['part']))['part']


def _report_correct(state, latent):
    parts = len(state['profile']['parts'])
    if state['published'] == 'c1':
        return True
    if state['published'] == 'patch':
        return patch_covers(latent, state['checked'], parts)
    return not affected_parts(latent, parts)


def step_abstract(state, action, latent):
    """One abstract decision; mirrors VeriCostEnv without opening a ledger (plan D7)."""
    if state['terminal']:
        raise RuntimeError('episode ended')
    profile, parts = state['profile'], len(state['profile']['parts'])
    new = dict(state)
    new['rem'] = state['rem'] - 1
    target = action[1] if isinstance(action, tuple) else None
    name = action[0] if isinstance(action, tuple) else action
    charge = 0.0
    if name == 'cc':
        charge = costs.cost(profile, state['regime'], 'consistency_check')
        flagged = cc_flagged(latent)
        new['cc'] = 'ok' if not flagged else 'flag_unchecked'
        new['flag'] = flagged[0] if flagged else None
        if flagged and flagged[0] in state['checked']:
            new['cc'] = 'flag_checked_mismatch' if flagged[0] in state['mismatch'] else 'flag_checked_match'
    elif name in ('spot', 'spot_flagged', 'spot_large', 'spot_small'):
        part = target if name == 'spot' else _resolve_part(state, name)
        if part is not None:  # an unavailable target is a rejected call: one decision, no cost
            charge = costs.cost(profile, state['regime'], 'spot_check', part)
            new['checked'] = state['checked'] | {part}
            if part in affected_parts(latent, parts):
                new['mismatch'] = state['mismatch'] | {part}
            if part not in state['checked']:
                new['spots'] = state['spots'] + 1
            if new['flag'] == part:
                new['cc'] = 'flag_checked_mismatch' if part in new['mismatch'] else 'flag_checked_match'
    elif name == 'full':
        charge = costs.cost(profile, state['regime'], 'full_recompute')
        new['full'] = 'mismatch' if affected_parts(latent, parts) else 'match'
    elif name == 'publish_patch':
        if state['mismatch']:
            new['published'] = 'patch'
            if not patch_covers(latent, state['checked'], parts):
                new['outcome'] = dict(state['outcome'], forbidden_effect=True)
    elif name == 'publish_c1':
        if state['full'] != 'none':
            new['published'] = 'c1'
    elif name in ('stop', 'escalate'):
        new['terminal'] = name
    else:
        raise ValueError('unknown abstract action: ' + str(name))
    new['spent'] = state['spent'] + charge
    if new['terminal'] == 'stop':
        correct = _report_correct(new, latent)
        new['outcome'] = dict(new['outcome'], safe_complete=correct and not new['outcome']['forbidden_effect'],
                              false_completion=not correct)
    elif not new['terminal'] and new['rem'] <= 0:
        new['terminal'] = 'horizon'
    reward = -charge
    if new['terminal']:
        reward += costs.utility(new['outcome'], 0.0, state['regime'])
    return new, reward


def utility_of(state):
    if not state['terminal']:
        raise ValueError('episode is not terminal')
    return costs.utility(state['outcome'], state['spent'], state['regime'])


def state_from_observation(observation, profile, regime_id):
    """Rebuild the abstract state from a public observation, for the env-side evaluation path."""
    counts = {key: observation['reliability'][key] for key in COUNT_KEYS}
    state = initial_state(profile, counts, regime_id)
    for entry in observation['history']:
        action, response = entry['action'], entry['response']
        if not response.get('ok'):
            continue
        if action == 'consistency_check':
            flagged = tuple(response['flagged_parts'])
            state['cc'] = 'ok' if not flagged else 'flag_unchecked'
            state['flag'] = flagged[0] if flagged else None
            if flagged and flagged[0] in state['checked']:
                state['cc'] = ('flag_checked_mismatch' if flagged[0] in state['mismatch']
                               else 'flag_checked_match')
        elif action == 'spot_check':
            part = response['part']
            if part not in state['checked']:
                state['spots'] += 1
            state['checked'] = state['checked'] | {part}
            if not response['match']:
                state['mismatch'] = state['mismatch'] | {part}
            if state['flag'] == part:
                state['cc'] = ('flag_checked_mismatch' if part in state['mismatch']
                               else 'flag_checked_match')
        elif action == 'full_recompute':
            state['full'] = 'match' if response['match'] else 'mismatch'
        elif action == 'publish':
            state['published'] = entry['params'].get('candidate_id')
        elif action in ('stop', 'escalate'):
            state['terminal'] = action
    state['rem'] = observation['remaining_decisions']
    return state


def history_states(jobs=HISTORY_JOBS):
    """Every public history count vector with its unconditional weight and MAP type."""
    out = []
    for clean in range(jobs + 1):
        for single in range(jobs + 1 - clean):
            counts = {'clean': clean, 'single_part_discrepancy': single,
                      'multi_part_discrepancy': jobs - clean - single}
            coefficient = (math.factorial(jobs) / (math.factorial(clean) * math.factorial(single)
                                                   * math.factorial(jobs - clean - single)))
            weight = fsum_([coefficient * _likelihood(RATES[name], counts) / 3 for name in TYPES])
            out.append({'counts': counts, 'weight': weight, 'map_type': map_type(counts)})
    return out


def _likelihood(rates, counts):
    product = 1.0
    for rate, key in zip(rates, COUNT_KEYS):
        product *= rate ** counts[key]
    return product
