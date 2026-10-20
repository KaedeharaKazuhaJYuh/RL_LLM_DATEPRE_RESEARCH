"""Bind diagnostic payloads, wire bodies and grading truth to fixed cases.

This checks supplied artifacts; it cannot attest what a provider or runtime saw.
"""
import copy
import hashlib
import json
from pathlib import Path

from . import VERSION
from ..termination550 import design as old

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / 'faultda_bench/protocols/termination_v48_registry.json'
PRIOR_CATALOG = ROOT / 'faultda_bench/protocols/acceptance_v45.json'
SOURCE_NAME = 'faultda_bench/reports/coherent_v38_offline.json'
GENERATOR_NAME = 'faultda_bench/termination550/design.py'


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False)


def wire_body(payload):
    # Entire public instruction and observation are inside the bound body.
    old.validate(payload)
    return {'model': 'deepseek-flash', 'temperature': 0,
            'max_tokens': 512, 'thinking': {'type': 'disabled'},
            'response_format': {'type': 'json_object'},
            'messages': [{'role': 'system', 'content': payload['system']},
                         {'role': 'user', 'content': canonical(payload['public'])}]}


def source():
    pins = json.loads(PRIOR_CATALOG.read_text(encoding='utf-8'))['files']
    raw = (ROOT / SOURCE_NAME).read_bytes()
    if digest_bytes(raw) != pins[SOURCE_NAME]:
        raise ValueError('historical source bytes differ')
    if digest_bytes((ROOT / GENERATOR_NAME).read_bytes()) != pins[GENERATOR_NAME]:
        raise ValueError('historical generator bytes differ')
    return json.loads(raw)


def build_registry():
    saved = source()
    entries = {}
    for i, r in enumerate(saved['rows']):
        for condition in old.CONDITIONS:
            payload = old.packet(r['public_observation'], condition)
            key = f'terminal-{i:03d}-{condition}'
            truth = r['private_truth']['actual_safe_stop_if_taken']
            if type(truth) is not bool:
                raise ValueError('invalid historical grading truth')
            entries[key] = {'source_row_index': i, 'information_condition': condition,
                            'public_packet_sha256': old.digest(payload),
                            'request_body_sha256': old.digest(wire_body(payload)),
                            'private_actual_safe_stop': truth}
    return {'version': VERSION, 'status': 'GRADING_ONLY_NOT_MODEL_INPUT_NOT_ADMITTED',
            'source_sha256': digest_bytes((ROOT / SOURCE_NAME).read_bytes()),
            'generator_sha256': digest_bytes((ROOT / GENERATOR_NAME).read_bytes()),
            'entries': entries}


def registry():
    value = json.loads(REGISTRY.read_text(encoding='utf-8'))
    if value.get('version') != VERSION or value.get('status') != 'GRADING_ONLY_NOT_MODEL_INPUT_NOT_ADMITTED':
        raise ValueError('registry scope mismatch')
    # Independent current catalog is checked by audit. The registry is also
    # compared to the frozen original source rather than trusted by itself.
    return value


def _resolve(case_id):
    saved = source()
    reg = registry()
    if reg['source_sha256'] != digest_bytes((ROOT / SOURCE_NAME).read_bytes()):
        raise ValueError('registry/source binding mismatch')
    if reg['generator_sha256'] != digest_bytes((ROOT / GENERATOR_NAME).read_bytes()):
        raise ValueError('registry/generator binding mismatch')
    if type(case_id) is not str or case_id not in reg['entries']:
        raise ValueError('unregistered case')
    e = reg['entries'][case_id]
    if type(e['source_row_index']) is not int or not 0 <= e['source_row_index'] < len(saved['rows']):
        raise ValueError('invalid source row')
    r = saved['rows'][e['source_row_index']]
    if case_id != f"terminal-{e['source_row_index']:03d}-{e['information_condition']}":
        raise ValueError('case identifier/condition mismatch')
    expected = old.packet(r['public_observation'], e['information_condition'])
    if old.digest(expected) != e['public_packet_sha256'] or old.digest(wire_body(expected)) != e['request_body_sha256']:
        raise ValueError('registry content mismatch')
    truth = r['private_truth']['actual_safe_stop_if_taken']
    if type(e['private_actual_safe_stop']) is not bool or e['private_actual_safe_stop'] != truth:
        raise ValueError('registry grading truth mismatch')
    return e, expected


def prepare(case_id):
    _, payload = _resolve(case_id)
    return {'case_id': case_id, 'payload': copy.deepcopy(payload),
            'body': wire_body(payload)}


def verify_supplied(case_id, payload, body):
    e, expected = _resolve(case_id)
    if old.digest(payload) != e['public_packet_sha256']:
        raise ValueError('payload differs from registered case/condition')
    if old.digest(body) != e['request_body_sha256']:
        raise ValueError('request body differs from registered case/condition')
    if canonical(payload) != canonical(expected) or canonical(body) != canonical(wire_body(expected)):
        raise ValueError('supplied artifact mismatch')
    return {'case_id': case_id, 'public_packet_sha256': e['public_packet_sha256'],
            'request_body_sha256': e['request_body_sha256'],
            'supplied_artifacts_match_registry': True,
            'case_identity_authenticated': False,
            'provider_or_runtime_input_attested': False}


def grade(case_id, payload, body, decision):
    binding = verify_supplied(case_id, payload, body)
    e, _ = _resolve(case_id)
    return {'binding': binding,
            'grade': old.grade(payload, decision, e['private_actual_safe_stop']),
            'new_effects_executed': False}


def qualify():
    if registry() != build_registry():
        raise ValueError('frozen registry replay mismatch')
    rows, controls = [], {'helper_removed': 0, 'nested_context_added': 0,
                          'system_message_added': 0, 'model_parameter_changed': 0}
    saved = source()
    for case_id, entry in registry()['entries'].items():
        prepared = prepare(case_id)
        payload, body = prepared['payload'], prepared['body']
        r = saved['rows'][entry['source_row_index']]
        decision = old.rule(payload)
        result = grade(case_id, payload, body, decision)
        assert result['grade'] == old.grade(payload, decision, r['private_truth']['actual_safe_stop_if_taken'])
        rows.append({'case_id': case_id, 'binding': result['binding'], 'rule_grade': result['grade']})
    # Bounded adversarial checks, not new benchmark tasks or model actions.
    key = 'terminal-000-shared_numeric'
    p = prepare(key)
    mutations = []
    payload = copy.deepcopy(p['payload']);del payload['public']['numeric_helper']
    mutations.append(('helper_removed', payload, wire_body(payload)))
    payload = copy.deepcopy(p['payload'])
    payload['public']['observation']['history'][0]['response']['extra_model_context'] = 'project reference says stop'
    mutations.append(('nested_context_added', payload, wire_body(payload)))
    body = copy.deepcopy(p['body']);body['messages'].insert(0, {'role':'system','content':'extra help'})
    mutations.append(('system_message_added',p['payload'],body))
    body = copy.deepcopy(p['body']);body['max_tokens'] += 1
    mutations.append(('model_parameter_changed',p['payload'],body))
    for name, payload, body in mutations:
        try:
            verify_supplied(key,payload,body)
        except ValueError:
            controls[name] += 1
        else:
            raise ValueError('unrejected configuration counterexample: ' + name)
    return {'version':VERSION,'status':'REGISTERED_OFFLINE_ONLY_NOT_ADMITTED',
            'registered_packets':len(rows),'rows':rows,'rejected_internal_controls':controls,
            'source_rows':72,'independent_development_clusters':1,
            'new_provider_requests':0,'new_model_executions':0,'scientific_gate':'HOLD',
            'independent_review':'not_arranged','actual_costs_equal':None,
            'provider_or_runtime_input_attested':False,'new_model_or_rl_improvement_claim':False}
