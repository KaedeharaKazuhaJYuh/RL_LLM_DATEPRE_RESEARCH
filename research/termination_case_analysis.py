"""Public-only arithmetic and legacy proof replay at stored decision inputs."""
import copy
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from faultda_bench.stop360.binding import binding
from faultda_bench.stop360.suite import evidence_verdict
from faultda_bench.lineage375.semantics import public_evidence

ROOT = Path(__file__).resolve().parents[1]


def numeric(observation):
    """Independent half-open window arithmetic, not the project oracle."""
    c = observation['contract']
    if c['family'] != 'window' or c['closed'] != 'left' or c['version_policy'] != 'snapshot':
        raise ValueError('outside audited snapshot-window semantics')
    versions = next(h['response']['versions'] for h in reversed(observation['history'])
                    if h['action'] == 'inputs' and h['response'].get('ok') is True)
    start, end = datetime.fromisoformat(c['start']), datetime.fromisoformat(c['end'])
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError('timezone required')
    chosen = []
    for r in versions[c['snapshot_version']]:
        t = datetime.fromisoformat(r['time'])
        if t.tzinfo is None:
            raise ValueError('timezone required')
        if start <= t < end and r['value'] not in ('', None):
            chosen.append(r)
    return {'selected_ids': sorted(r['id'] for r in chosen),
            'selected_values': {r['id']: r['value'] for r in chosen},
            'total': str(sum((Decimal(r['value']) for r in chosen), Decimal(0))),
            'scope': 'public raw values, no dimension join for this window contract'}


def load(name):
    p = ROOT / 'faultda_bench/reports' / name
    raw = p.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def stored_observation(request):
    messages = request['body']['messages']
    users = [m for m in messages if m['role'] == 'user']
    if len(users) != 1:
        raise ValueError('expected one complete serialized public observation')
    return json.loads(users[0]['content'])


def analyze():
    findings = []
    for name in ('stop_v31_deepseek.json', 'receipt_v35_deepseek.json'):
        d, source_hash = load(name)
        for i, row in enumerate(d['rows']):
            if name.startswith('stop'):
                if not row['predecision_evidence']['evidence_supported_stop']:
                    continue
                request_index = row['request_index']
                decision = row['classification']['decision']
            else:
                request_index = row['decisions'][-1]['request_index']
                decision = row['decisions'][-1]['classification']['decision']
            q = d['requests'][request_index]
            obs = stored_observation(q)
            original = copy.deepcopy(obs)
            arithmetic = numeric(obs)
            if name.startswith('stop'):
                proof = evidence_verdict(obs)
                assert proof == row['predecision_evidence']
                responsibility = {'status': 'no_explicit_responsibility_contract_in_request',
                                  'old_scoring_scope_retained': True}
                current = binding(obs)['active_record_evidence']
            else:
                proof = public_evidence(obs)
                assert proof == row['grade']['public_final']
                responsibility = {'contract': obs['responsibility_contract'],
                                  'context': obs['responsibility_context'],
                                  'origin_authentication': 'not_provided_by_responsibility_labels'}
                current = next(h['response']['records'] for h in reversed(obs['history'])
                               if h['action'] == 'inspect' and h['response'].get('ok') is True)
            assert obs == original
            totals = [str(r['output']['total']) for r in current]
            findings.append({'source': name, 'source_sha256': source_hash,
                             'row_index': i, 'request_index': request_index,
                             'public_observation': obs, 'independent_arithmetic': arithmetic,
                             'current_report_totals': totals,
                             'current_numeric_matches': len(totals) == 1 and
                             abs(Decimal(totals[0]) - Decimal(arithmetic['total'])) <= Decimal('0.000000001'),
                             'replayed_public_proof': proof, 'responsibility': responsibility,
                             'remaining': obs['remaining'],
                             'experiment_horizon_remaining': obs.get('experiment_action_horizon_remaining'),
                             'model_decision': decision,
                             'response_choices': q['receipt']['response']['choices'],
                             'stop_legal_by_legacy_public_proof': proof['evidence_supported_stop'],
                             'causal_explanation': 'unknown; no model knowledge or motive inferred'})
    return {'scope': '12 ready single-step inputs plus 4 final recovery decisions',
            'findings': findings, 'new_api_calls': 0, 'scientific_gate': 'HOLD',
            'new_mechanism_identified': False}


if __name__ == '__main__':
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
