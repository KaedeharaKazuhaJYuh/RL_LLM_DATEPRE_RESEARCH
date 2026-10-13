"""Executable offline transport rehearsal; never create a provider client."""
import argparse
import copy
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from . import VERSION
from ..qualify330.suite import protocol as prior_protocol, prepare
from ..qualify330.environment import observation
from ..qualify330.policy import choose
from ..semantics305.core import diagnostic_body, diagnostic_score, action_body
from ..feedback315.core import public_input
from ..rowdiag.suite import decoded
from ..formatdiag.core import classify
from ..semantic.oracle import evaluate
from ..semantic.tasks import REPO, sha
from ..clarity.tasks import write_json
from ..multistep.suite import require, same

DESIGN = REPO/'faultda_bench/protocols/qualify_v28_design.json'


def protocol():
    old = prior_protocol(); design = json.loads(DESIGN.read_text(encoding='utf-8'))
    states = [{'view': v, 'profile': p, 'checks': design['checks']} for v in design['views'] for p in design['profiles']]
    names = set(old['code_sha256']) | {'faultda_bench/runtime335/'+n for n in ('__init__.py', 'suite.py')}
    return {'version': VERSION, 'revision': 'runtime_v28', 'design_sha256': sha(DESIGN), 'states': states,
            'views': old['views'], 'arms': ['direct', 'shared_model_record'], 'action_horizon': 8,
            'max_record_requests': 8, 'max_action_requests': 128, 'max_transport_requests': 136,
            'code_sha256': {n: sha(REPO/n) for n in sorted(names)}, 'scientific_gate': 'HOLD',
            'transport': 'scripted_offline_only', 'provider_client_created': False,
            'scope': 'Eight record-generation envelopes, sixteen action trajectories, matched initial public state. Script fixtures are public rules, not model responses. No live CLI or independent scientific acceptance.'}


def action_request(obs, record=None):
    body = action_body(obs, record, {'analysis': True, 'idempotency': True, 'carry': True})
    body['messages'][0]['content'] += (
        ' The reliability_contract in the supplied observation includes repeated precommit failures '
        'and commit acknowledgement loss. No numerical executor guard or private oracle is provided. '
        'An optional model-family working record can be wrong; use the latest public state.')
    return body


def scripted_receipt(value):
    return {'category': 'scripted_fixture', 'request_sent': False, 'response': {
        'model': 'offline-public-rule-fixture', 'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(value, allow_nan=False)}}]}}


def fixture(body, probe):
    obs = json.loads(body['messages'][1]['content'])
    if probe == 'action': return scripted_receipt(choose(obs, 'retry_once_reconcile'))
    _, totals, public = public_input(obs)
    start, end = datetime.fromisoformat(public['start']), datetime.fromisoformat(public['end'])
    utc = lambda text: datetime.fromisoformat(text).astimezone(timezone.utc).isoformat()
    rows = []
    for raw in public['rows']:
        instant = datetime.fromisoformat(raw['time']); ge, lt = instant >= start, instant < end
        rows.append({'id': raw['id'], 'value': None if raw['value'] == '' else float(raw['value']),
                     'time_utc': utc(raw['time']), 'ge_start': ge, 'lt_end': lt, 'included': ge and lt})
    return scripted_receipt({'version': public['version'], 'start_utc': utc(public['start']), 'end_utc': utc(public['end']), 'rows': rows, 'total': float(totals['total'])})


def checked_send(send, body, probe, requests):
    require(len(requests) < 136, 'global transport request cap')
    receipt = send(body, probe)
    require(receipt.get('category') == 'scripted_fixture' and receipt.get('request_sent') is False, 'offline-only transport boundary')
    requests.append({'probe': probe, 'body': body, 'receipt': receipt})
    return receipt


def execute(plan, send):
    require(same(plan, protocol()), 'frozen executable plan'); rows = []; generated = []; requests = []
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        for index, cell in enumerate(plan['states']):
            task = plan['views'][cell['view']]
            env = prepare(task, root/('record-'+str(index)), cell['profile'], cell['checks'])
            initial = observation(env); body = diagnostic_body(initial, 'normalized')
            receipt = checked_send(send, body, 'record', requests); record = decoded(receipt)
            generated.append({'state': index, 'request_index': len(requests)-1, 'record': record,
                              'score': diagnostic_score(record, task, 'normalized')})
            for arm in plan['arms']:
                env = prepare(task, root/(str(index)+'-'+arm), cell['profile'], cell['checks'])
                require(same(observation(env), initial), 'matched public initial state')
                evidence = (record if record is not None else {'model_record_unavailable': True}) if arm == 'shared_model_record' else None
                result = {**cell, 'state': index, 'arm': arm, 'record_source': index if arm == 'shared_model_record' else None,
                          'action_record': copy.deepcopy(evidence), 'request_indices': [], 'classifications': []}
                for step in range(8):
                    if env.terminal is not None: break
                    obs = observation(env); obs['experiment_action_horizon_remaining'] = 8-step
                    body = action_request(obs, evidence); receipt = checked_send(send, body, 'action', requests)
                    result['request_indices'].append(len(requests)-1)
                    classification = classify(receipt.get('response')); result['classifications'].append(classification)
                    if classification['category'] != 'valid_action': break
                    decision = classification['decision']; env.step(decision['action'], decision['params'])
                result['evaluation'] = evaluate(env)
                result['end_kind'] = 'terminal' if env.terminal is not None else 'nonterminal'
                rows.append(result)
    return {'version': VERSION, 'protocol': plan, 'record_generations': generated, 'requests': requests, 'rows': rows,
            'summary': {'scripted_record_envelopes': len(generated), 'scripted_trajectories': len(rows),
                        'scripted_transport_envelopes': len(requests), 'actual_provider_requests': 0,
                        'scripted_safe_complete': sum(r['evaluation']['safe_complete'] for r in rows),
                        'new_model_results': 0, 'scientific_gate': 'HOLD', 'independent_review': 'pending',
                        'scope': 'Dry transport rehearsal; fixture rules ignore treatment record, so equal outcomes are not model or treatment-effect evidence.'}}


def verify(output):
    saved = json.loads(Path(output).read_text(encoding='utf-8')); iterator = iter(saved['requests'])
    def replay(body, probe):
        request = next(iterator); require(request['probe'] == probe and same(request['body'], body), 'exact prompt/record replay')
        return request['receipt']
    rebuilt = execute(saved['protocol'], replay)
    require(next(iterator, None) is None and same(rebuilt, saved), 'classifications/records/actions/state/accounting')
    return {'status': 'verified', 'scripted_trajectories': 16, 'actual_provider_requests': 0, 'new_model_results': 0, 'scientific_gate': 'HOLD'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--freeze'); p.add_argument('--dry-run'); p.add_argument('--output'); p.add_argument('--verify'); a = p.parse_args()
    if a.freeze and not any((a.dry_run, a.output, a.verify)): write_json(Path(a.freeze), protocol())
    elif a.dry_run and a.output and not any((a.freeze, a.verify)):
        plan = json.loads(Path(a.dry_run).read_text(encoding='utf-8')); write_json(Path(a.output), execute(plan, fixture)); print(json.dumps(verify(a.output)))
    elif a.verify and not any((a.freeze, a.dry_run, a.output)): print(json.dumps(verify(a.verify)))
    else: p.error('choose freeze, dry-run/output, or verify; no live API option')
