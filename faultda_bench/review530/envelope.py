"""Bind the actual public packet and helper; no declarations become live approval."""
import copy
import hashlib
from pathlib import Path
from ..review525 import preflight as old

CASE_KEYS = {'case_id', 'public_observation', 'query_event_id'}
ARM_KEYS = {'name', 'public_observation_sha256', 'effective_input_sha256',
            'allowed_tools', 'tool_budgets', 'preprocessing', 'private_truth_access'}
SCHEMA = 'public-comparison-packet-v1'


def helper():
    return {'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'view_schema': SCHEMA, 'charged': True}


def packet(case):
    if not isinstance(case, dict) or set(case) != CASE_KEYS:
        raise ValueError('exact public case fields required')
    if not isinstance(case['case_id'], str) or not case['case_id'].strip():
        raise ValueError('case identifier required')
    # No fixture id, reference, provenance-registry match or private truth enters
    # the effective input. Public source claims are retained as claims, not certified.
    return {'schema': SCHEMA, 'observation': copy.deepcopy(case['public_observation']),
            'request_binding': old.resolve(case['public_observation'], case['query_event_id'])}


def check(cases, arms):
    if not isinstance(cases, list) or not cases or not isinstance(arms, list) or len(arms) != 2:
        raise ValueError('nonempty cases and two arms required')
    packets = [packet(c) for c in cases]
    hashes = {c['case_id']: old.digest(p) for c,p in zip(cases,packets)}
    if len(hashes) != len(cases): raise ValueError('duplicate case identifier')
    for a in arms:
        if not isinstance(a, dict) or set(a) != ARM_KEYS:
            raise ValueError('unknown arm fields may hide unequal context')
        if a['preprocessing'] != helper():
            raise ValueError('helper must match the actual bound packet generator')
        if a['effective_input_sha256'] != hashes:
            raise ValueError('effective public packets differ or cases are missing')
    baseline = old.compare_setup(cases,arms)
    for c in cases:
        remaining = c['public_observation']['remaining']
        for key in ('checks','mutations','decisions'):
            available = remaining.get(key)
            if type(available) is not int or available < 0:
                raise ValueError('invalid public remaining budget')
            if any(a['tool_budgets'][key] > available for a in arms):
                raise ValueError('declared tool cap exceeds the supplied snapshot')
    return {'status': 'strict_public_packet_binding_verified_not_execution',
            'scheduled_per_arm': baseline['scheduled_per_arm'],
            'effective_input_sha256': hashes, 'preprocessing': helper(),
            'resolver_source_sha256': hashlib.sha256(Path(old.__file__).read_bytes()).hexdigest(),
            'execution_compliance_verified': False, 'actual_total_costs_equal': None,
            'independent_task_eligibility_verified': False, 'ability_gap_measured': False,
            'scientific_gate': 'HOLD', 'approved_transport_requests': 0}
