"""Explicit actor/receipt references; no score or terminal answer is supplied."""
import copy
import re

from ..lineage375 import SEMANTICS_VERSION as LEGACY_VERSION
from ..validity500.adapter import origin_evidence

VERSION = '0.5.20-dev'
CONTRACT = {
    'schema': 'actor-receipt-v1',
    'responsibility_scope': {
        'environment_setup': 'Initial setup outside the indexed action history.',
        'pre_handoff_actor': 'Publication attempt before the declared actor handoff index.',
        'active_actor': 'Publication attempt at or after the declared actor handoff index.'},
    'origin': 'Generation origin and represented responsibility are separate axes. Only an exact pinned observation match supports scripted_fixture here; all other observations are unknown. This interface has no positive model_api_tool_action evidence.',
    'receipt_target': 'query_event_id identifies a successful receipt_lookup read. target_publish_event_id identifies its earlier publish attempt, never its stage or the query itself. Both request ids and the returned request_id must match. A repeated request id cannot certify one attempt.',
    'execution': 'This is a read-only derived fact view, not a new tool execution or a model fact answer. A model fact answer never establishes tool-action authorship.',
    'boundary': 'The index is inherited from the supplied task responsibility contract. This view does not independently authenticate that it was fixed before real historical actions.',
    'limits': 'No stop permission, violation judgement, model score or human validity acceptance is added. Any future model use needs a separately reviewed equal-help and cost comparison.'}


def _index(event_id, history):
    if type(event_id) is not str or re.fullmatch(r'history:(0|[1-9][0-9]*)', event_id) is None:
        raise ValueError('event id must be history:N with a nonnegative canonical index')
    index = int(event_id.split(':')[1])
    if index >= len(history):
        raise ValueError('event id outside supplied history')
    return index


def _request_id(params):
    request_id = params.get('request_id')
    if type(request_id) is not str or not 0 < len(request_id) <= 80 or request_id == 'initial':
        raise ValueError('publication request id missing, invalid or reserved')
    return request_id


def build_view(obs, query_event_id, target_publish_event_id):
    """Derive structural references without renaming or mutating legacy payloads.

    This parser is not a replacement for the independent public-evidence engine.
    It does not turn an unknown origin into a model-action claim or evaluate the
    safety of supplied history. Repeated ids produce explicit ambiguity instead
    of guessing which physical publication the receipt certifies.
    """
    history = obs['history']
    if not isinstance(history, list):
        raise ValueError('history must be an indexed list')
    contract = obs.get('responsibility_contract', {})
    context = obs.get('responsibility_context', {})
    if contract.get('semantics_version') != LEGACY_VERSION or context.get('semantics_version') != LEGACY_VERSION:
        raise ValueError('unsupported legacy responsibility contract')
    boundary = context.get('current_model_start_history_index')
    if type(boundary) is not int or not 0 <= boundary <= len(history):
        raise ValueError('responsibility boundary must be an in-range integer, not bool')
    query_index = _index(query_event_id, history)
    target_index = _index(target_publish_event_id, history)
    query, target = history[query_index], history[target_index]
    if query['action'] != 'receipt_lookup':
        raise ValueError('query event must be receipt_lookup')
    if target['action'] != 'publish':
        raise ValueError('target event must be publish, never stage or receipt_lookup')
    if target_index >= query_index:
        raise ValueError('target publication must precede the receipt query')
    if set(query['params']) != {'request_id'}:
        raise ValueError('receipt query requires only request_id')
    request_id = _request_id(query['params'])
    if _request_id(target['params']) != request_id:
        raise ValueError('query and target publication request ids differ')
    response = query['response']
    if response.get('ok') is not True or response.get('request_id') != request_id:
        raise ValueError('successful receipt response must bind the query request id')
    committed, revision = response.get('committed'), response.get('revision')
    if type(committed) is not bool or (committed and (type(revision) is not int or revision <= 0)) or (not committed and revision is not None):
        raise ValueError('receipt commit/revision types invalid')
    origin = origin_evidence(obs)
    if origin['history_generation_origin'] not in ('scripted_fixture', 'unknown'):
        raise ValueError('no positive model-tool generation evidence supported')
    attempts = []
    for index, entry in enumerate(history):
        if entry['action'] == 'publish':
            attempts.append({'event_id': 'history:' + str(index), 'history_index': index,
                             'request_id': _request_id(entry['params']),
                             'responsibility_scope': 'pre_handoff_actor' if index < boundary else 'active_actor',
                             'generation_origin': origin['history_generation_origin'],
                             'params': copy.deepcopy(entry['params']),
                             'response': copy.deepcopy(entry['response'])})
    matches = [a for a in attempts if a['history_index'] < query_index and a['request_id'] == request_id]
    ambiguous = len(matches) != 1
    receipt = {'query_event_id': query_event_id, 'query_history_index': query_index,
               'query_action': 'receipt_lookup', 'request_id': request_id,
               'binding_status': 'ambiguous_repeated_request' if ambiguous else 'bound_unique_prior_publish',
               'candidate_publish_event_ids': [a['event_id'] for a in matches],
               'target_publish_event_id': None if ambiguous else target_publish_event_id,
               'target_responsibility_scope': None if ambiguous else matches[0]['responsibility_scope'],
               'response': copy.deepcopy(response),
               'single_attempt_reference_unambiguous': not ambiguous,
               'receipt_authenticity_verified': False}
    return {'version': VERSION, 'schema': CONTRACT['schema'], 'contract': copy.deepcopy(CONTRACT),
            'readonly_derived_view': True, 'legacy_payload_modified': False,
            'source_observation_sha256': origin['observation_sha256'],
            'actor_boundary': {'handoff_history_index': boundary,
                               'evidence_path': 'responsibility_context.current_model_start_history_index',
                               'assurance': 'inherited_task_contract_not_independent_historical_authentication'},
            'environment_setup': {'event_id': 'environment_setup', 'history_index': None,
                                  'responsibility_scope': 'environment_setup',
                                  'initial_feedback': copy.deepcopy(obs.get('initial_feedback')),
                                  'physical_commit_inferred': False},
            'attempts': attempts, 'receipt_read': receipt, 'origin_evidence': copy.deepcopy(origin),
            'execution_context': {'kind': 'read_only_derived_fact_view',
                                  'new_tool_executions': 0, 'new_provider_requests': 0,
                                  'model_fact_answer_proves_tool_authorship': False},
            'human_validity_accepted': False, 'scientific_gate': 'HOLD'}
