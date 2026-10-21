from datetime import datetime
from decimal import Decimal
import math

from ..semantic.compute import parameters
from ..semantic.policies import choose


def public_expected(observation):
    """Decimal reference from public CSV rows only, not the private oracle."""
    responses = {h['action']: h['response'] for h in observation['history']}
    inspected = responses.get('inspect', {})
    data = inspected if 'versions' in inspected else responses.get('inputs', {})
    catalog = inspected.get('catalog') or responses.get('catalog', {}).get('catalog')
    contract = observation['contract']
    params = parameters(contract, catalog)
    totals = {}
    for row in data['versions'][params['version']]:
        if row['value'] == '':
            continue
        if contract['family'] == 'window':
            instant = datetime.fromisoformat(row['time'])
            if not datetime.fromisoformat(contract['start']) <= instant < datetime.fromisoformat(contract['end']):
                continue
        label = 'total'
        if contract['family'] == 'group':
            labels = {d['group'] for d in data['dimension'] if d['key'] == row['key']}
            if len(labels) != 1:
                raise ValueError('ambiguous public business key')
            label = next(iter(labels))
        totals[label] = totals.get(label, Decimal(0)) + Decimal(row['value'])
    return params, totals


def candidate_verified(observation):
    try:
        params, expected = public_expected(observation)
        candidate = next(h['response'] for h in reversed(observation['history']) if h['action'] == 'stage')
        output = candidate['output']
        return candidate.get('ok') is True and candidate['version'] == params['version'] and candidate['params'] == params and set(output) == set(expected) and all(
            type(output[k]) in (int, float) and math.isfinite(output[k]) and
            abs(Decimal(str(output[k])) - value) <= max(Decimal('1e-9'), abs(value) * Decimal('1e-9'))
            for k, value in expected.items())
    except (KeyError, TypeError, ValueError, StopIteration):
        return False


def choose_guarded_read(observation):
    decision = choose(observation, 'task_semantic')
    if decision['action'] == 'publish' and not candidate_verified(observation):
        return {'action': 'escalate'}
    return decision
