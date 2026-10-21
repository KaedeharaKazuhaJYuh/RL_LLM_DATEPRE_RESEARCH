"""Resolve from public history; compare setup declarations, never ability scores."""
import copy
import hashlib
import json
import re
from ..lineage375 import SEMANTICS_VERSION

PUBLIC_KEYS = {'contract', 'tools', 'initial_feedback', 'remaining', 'history', 'terminal',
               'reliability_contract', 'responsibility_contract', 'responsibility_context',
               'trajectory_provenance'}
BUDGETS = {'checks', 'mutations', 'decisions', 'response_bytes', 'wall_seconds'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def resolve(observation, query_event_id):
    """No answer/event target, case id, origin registry or private truth is read.

    This v1 endpoint handles a snapshot ending at its explicitly selected lookup;
    it does not silently use later events. It checks structural references only.
    """
    if not isinstance(observation, dict) or set(observation) != PUBLIC_KEYS:
        raise ValueError('exact supported public observation keys required')
    if (observation['responsibility_contract'].get('semantics_version') != SEMANTICS_VERSION
            or observation['responsibility_context'].get('semantics_version') != SEMANTICS_VERSION):
        raise ValueError('unsupported responsibility semantics')
    history = observation['history']
    if not isinstance(history, list) or not history:
        raise ValueError('nonempty public history required')
    if not isinstance(query_event_id, str) or re.fullmatch(r'history:(0|[1-9][0-9]*)', query_event_id) is None:
        raise ValueError('canonical query event id required')
    index = int(query_event_id.split(':')[1])
    if index != len(history) - 1:
        raise ValueError('snapshot must end at the selected query; no later-event help')
    boundary = observation['responsibility_context'].get('current_model_start_history_index')
    if type(boundary) is not int or not 0 <= boundary <= len(history):
        raise ValueError('invalid responsibility boundary')
    query = history[index]
    if query.get('action') != 'receipt_lookup' or set(query.get('params', {})) != {'request_id'}:
        raise ValueError('explicit receipt_lookup required')
    request = query['params']['request_id']; response = query.get('response', {})
    if not isinstance(response, dict) or set(response) != {'ok', 'request_id', 'committed', 'revision'}:
        raise ValueError('exact public receipt fields required')
    if not isinstance(request, str) or not request.strip() or request == 'initial':
        raise ValueError('nonreserved request id required')
    if response.get('ok') is not True or response.get('request_id') != request:
        raise ValueError('receipt query/response identity mismatch')
    committed, revision = response.get('committed'), response.get('revision')
    if type(committed) is not bool or (committed and (type(revision) is not int or revision <= 0)) or (not committed and revision is not None):
        raise ValueError('invalid receipt scalar types')
    matches = [{'event_id': 'history:'+str(i),
                'responsibility_scope': 'pre_handoff_actor' if i < boundary else 'active_actor'}
               for i, h in enumerate(history[:index])
               if h.get('action') == 'publish' and h.get('params', {}).get('request_id') == request]
    if not matches: raise ValueError('request has no prior public publication attempt')
    unique = len(matches) == 1
    return {'schema': 'public-request-binding-v1', 'query_event_id': query_event_id,
            'request_id': request, 'candidate_attempts': matches,
            'binding_status': 'unique_public_reference' if unique else 'ambiguous_repeated_request',
            'target_publish_event_id': matches[0]['event_id'] if unique else None,
            'receipt_response': copy.deepcopy(response),
            'receipt_authenticity_verified': False,
            'generation_origin_attested': False,
            'safety_or_stop_permission_computed': False}


def compare_setup(cases, arms):
    """Check common inputs/helpers/tool caps before results; no human/runner attestation."""
    if not isinstance(cases, list) or not cases:
        raise ValueError('common scheduled cases required')
    ids = [c['case_id'] for c in cases]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('unique case identifiers required')
    expected = {c['case_id']: digest(c['public_observation']) for c in cases}
    # Resolving each case also refuses accidental reference/private fields.
    for c in cases: resolve(c['public_observation'], c['query_event_id'])
    if not isinstance(arms, list) or len(arms) != 2:
        raise ValueError('exactly two prespecified comparison arms required')
    names = [a['name'] for a in arms]
    if any(not isinstance(n, str) or not n.strip() for n in names) or len(set(names)) != 2:
        raise ValueError('distinct arm names required')
    profiles = []
    for a in arms:
        if a.get('public_observation_sha256') != expected:
            raise ValueError('arm-specific case deletion or input substitution')
        tools = a.get('allowed_tools')
        if not isinstance(tools, list) or not tools or any(not isinstance(t, str) or not t for t in tools) or len(set(tools)) != len(tools):
            raise ValueError('explicit unique public tool permissions required')
        if any(not set(tools) <= set(c['public_observation']['tools']) for c in cases):
            raise ValueError('tool is not declared public for every scheduled case')
        caps = a.get('tool_budgets', {})
        if not isinstance(caps, dict) or set(caps) != BUDGETS or any(type(v) is not int or v < 0 for v in caps.values()):
            raise ValueError('integer nonnegative common tool caps required')
        helper = a.get('preprocessing')
        if not isinstance(helper, dict) or set(helper) != {'code_sha256', 'view_schema', 'charged'}:
            raise ValueError('explicit preprocessing contract required')
        if not isinstance(helper['code_sha256'], str) or re.fullmatch('[0-9a-f]{64}', helper['code_sha256']) is None or not isinstance(helper['view_schema'], str) or not helper['view_schema'].strip() or helper['charged'] is not True:
            raise ValueError('preprocessing must be bound and charged')
        if a.get('private_truth_access') is not False:
            raise ValueError('private truth access forbidden')
        profiles.append({'tools': sorted(tools), 'tool_budgets': caps, 'preprocessing': helper})
    if digest(profiles[0]) != digest(profiles[1]):
        raise ValueError('unequal tool permissions, budgets or preprocessing help')
    return {'status': 'setup_declarations_match_not_authenticated', 'scheduled_per_arm': len(cases),
            'public_input_hashes': expected, 'setup_sha256': digest(profiles[0]),
            'execution_compliance_verified': False, 'actual_total_costs_equal': None,
            'independent_task_eligibility_verified': False, 'ability_gap_measured': False,
            'scientific_gate': 'HOLD', 'approved_transport_requests': 0}
