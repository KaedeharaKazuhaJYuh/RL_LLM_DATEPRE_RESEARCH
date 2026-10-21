"""Tool-side float implementation; evaluator has a separate Decimal reference."""
from datetime import datetime
import math


def calculate(rows, dimension, family, params):
    if set(params) != {'version', 'deduplicate_keys', 'closed'}:
        raise ValueError('expected version, deduplicate_keys, closed')
    if type(params['deduplicate_keys']) is not bool or params['closed'] not in ('left', 'both'):
        raise ValueError('invalid analysis parameters')
    groups = {}
    for row in rows:
        if not row['value']:
            continue
        value = float(row['value'])
        if not math.isfinite(value):
            raise ValueError('non-finite input')
        if family['family'] == 'window':
            stamp, start, end = map(datetime.fromisoformat, (row['time'], family['start'], family['end']))
            if not (start <= stamp and (stamp < end if params['closed'] == 'left' else stamp <= end)):
                continue
        matches = [r['group'] for r in dimension if r['key'] == row['key']]
        if family['family'] != 'group':
            matches = ['total']
        elif params['deduplicate_keys']:
            matches = list(dict.fromkeys(matches))
        for group in matches:
            groups.setdefault(group, []).append(value)
    return {key: math.fsum(values) for key, values in sorted(groups.items())}


def parameters(contract, catalog):
    return {'version': catalog['snapshot' if contract['version_policy'] == 'snapshot' else 'latest'],
            'deduplicate_keys': True, 'closed': 'left'}
