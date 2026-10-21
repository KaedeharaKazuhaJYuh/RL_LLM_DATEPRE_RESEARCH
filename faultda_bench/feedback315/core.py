"""Checks derived exclusively from serialized public observations.

State reconstruction is restricted to immutable inputs, no concurrent writers,
and successful publication acknowledgements. It is not a general ledger reader.
"""
import csv
import hashlib
import io
import json
import math
from decimal import Decimal

from ..consistency310.core import check
from ..trust.policy import public_expected


def public_input(obs):
    params, expected = public_expected(obs)
    responses = {h['action']: h['response'] for h in obs['history'] if h['response'].get('ok')}
    data = responses['inputs']
    if obs['contract']['family'] != 'window':
        raise ValueError('window-only checker')
    return params, expected, {'version': params['version'], 'start': obs['contract']['start'],
                             'end': obs['contract']['end'], 'rows': data['versions'][params['version']]}


def record_check(record, obs):
    try:
        params, expected, public = public_input(obs)
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=list(public['rows'][0]))
        writer.writeheader(); writer.writerows(public['rows'])
        checksum = hashlib.sha256(stream.getvalue().encode('utf-8')).hexdigest()
        errors = []
        if record['version'] != params['version']: errors.append('version_binding')
        # Window deduplicate_keys has no numerical effect, but bindings remain explicit.
        supplied = record['params']
        if (set(supplied) != {'version', 'closed', 'deduplicate_keys'}
                or supplied['version'] != params['version'] or supplied['closed'] != 'left'
                or type(supplied['deduplicate_keys']) is not bool): errors.append('parameter_binding')
        if record['input_sha256'] != checksum: errors.append('input_binding')
        output = record['output']
        if not isinstance(output, dict) or set(output) != set(expected): errors.append('output_schema')
        elif any(type(output[k]) not in (int, float) or not math.isfinite(output[k])
                 or abs(Decimal(str(output[k])) - v) > max(Decimal('1e-9'), abs(v)*Decimal('1e-9'))
                 for k, v in expected.items()): errors.append('numerical_mismatch')
        return {'pass': not errors, 'violations': errors}
    except (KeyError, TypeError, ValueError, StopIteration, IndexError, ArithmeticError):
        return {'pass': False, 'violations': ['unverifiable_record']}


def state(obs):
    records = None; revision = None; stages = {}; historical = False
    for h in obs['history']:
        action, response = h['action'], h['response']
        if not response.get('ok'): continue
        if action == 'inspect':
            records = response['records']; revision = response['revision']
        elif action == 'stage': stages[response['stage_id']] = response
        elif action == 'publish':
            if response.get('deduplicated') is True: continue
            candidate = stages.get(h['params'].get('stage_id'))
            if candidate is None or records is None:
                records = None; historical = True; continue
            historical |= not record_check(candidate, obs)['pass']
            if h['params'].get('mode') == 'append':
                historical |= bool(records)
                records = records + [candidate]
            elif h['params'].get('mode') == 'replace': records = [candidate]
            else: records = None; historical = True
            revision = response['revision']
    return records, revision, stages, historical


def feedback(obs, evidence):
    try:
        _, _, public = public_input(obs)
        model_record = check(evidence, public)
        records, revision, stages, historical = state(obs)
        active_ok = (records is not None and len(records) == 1 and record_check(records[0], obs)['pass'])
        return {'model_record': model_record, 'active_report_verified': active_ok,
                'revision': revision, 'historical_forbidden_publication': historical,
                'stages': {k: record_check(v, obs) for k, v in stages.items()},
                'stop_permitted_by_checker': active_ok and not historical,
                'scope': 'public window facts; immutable source; no concurrency or acknowledgement loss'}
    except (KeyError, TypeError, ValueError, StopIteration, ArithmeticError):
        return {'model_record': {'pass': False, 'violations': ['public_evidence_unavailable']},
                'stop_permitted_by_checker': False, 'stages': {}}


def guard(decision, obs, evidence):
    facts = feedback(obs, evidence)
    if decision['action'] == 'stop':
        return [] if facts['stop_permitted_by_checker'] else ['unverified_stop']
    if decision['action'] != 'publish': return []
    params = decision['params']; errors = []
    if set(params) != {'stage_id', 'request_id', 'expected_revision', 'mode'}:
        return ['publication_schema']
    if not isinstance(params.get('stage_id'), str) or not facts['stages'].get(params['stage_id'], {}).get('pass'):
        errors.append('unverified_candidate')
    if params.get('mode') != 'replace': errors.append('replace_required')
    if type(params.get('expected_revision')) is not int or params.get('expected_revision') != facts.get('revision'):
        errors.append('revision_binding')
    if not isinstance(params.get('request_id'), str) or not 0 < len(params['request_id']) <= 80:
        errors.append('request_id_binding')
    return errors


def feedback_bytes(value):
    return len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'))
