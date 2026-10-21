"""Synthetic design falsifier, not a benchmark, trusted verifier, or model run.

Run from repository root: python research/binding_probe.py
All public certificates are assumed authentic in this toy. No concurrent writer.
"""
import copy
import hashlib
import json
from decimal import Decimal


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def analyze(rows, contract):
    # Deliberately narrow executable semantics; no claim of general analysis.
    if contract != {'operation': 'sum', 'field': 'amount'}:
        raise ValueError('unsupported contract')
    return str(sum((Decimal(r['amount']) for r in rows), Decimal(0)))


def make_case(name):
    rows = [{'id': 1, 'amount': '2.10'}, {'id': 2, 'amount': '3.20'}]
    contract = {'operation': 'sum', 'field': 'amount'}
    report = {'data': digest(rows), 'contract': digest(contract),
              'answer': analyze(rows, contract)}
    public = {'rows': rows, 'contract': contract, 'report': report,
              'validation': {'report': digest(report), 'passed': True},
              'receipt': {'request': 'publish-1', 'report': digest(report),
                          'committed': True},
              'target_request': 'publish-1', 'revision': 1,
              'validation_revision': 1, 'confirmed_active_violation': False,
              'budget': {'checks': 1, 'writes': 1, 'decisions': 1}}
    if name == 'analysis_wrong':
        report['answer'] = '6.30'
        public['validation'] = {'report': digest(report), 'passed': False}
        public['receipt']['report'] = digest(report)
    elif name == 'commit_unknown':
        public['receipt']['committed'] = None
    elif name == 'cross_report':
        # Validation remains a true certificate of old report A. Receipt
        # truthfully acknowledges B; independently true does not imply bound.
        report['answer'] = '6.30'
        public['receipt']['report'] = digest(report)
    elif name == 'benign_revision':
        public['revision'] = 2  # only revision metadata changes, rows unchanged
    elif name == 'repaired_history':
        public['confirmed_active_violation'] = True
    elif name != 'healthy':
        raise ValueError(name)
    return public


def weak(public):
    return ('stop' if public['validation']['passed'] is True and
            public['receipt']['committed'] is True else 'escalate')


def joint(public):
    r, v, ack = public['report'], public['validation'], public['receipt']
    supported = (r['data'] == digest(public['rows']) and
                 r['contract'] == digest(public['contract']) and
                 v['passed'] is True and v['report'] == digest(r) and
                 ack['request'] == public['target_request'] and
                 ack['report'] == digest(r) and ack['committed'] is True)
    return ('stop' if supported and not public['confirmed_active_violation']
            else 'escalate')


def recompute(public):
    """Execute allowed full replacement; costs are operation counts, not time.

    Replacement is a legal idempotent overwrite in this toy, not an append or
    external notification. Repair never erases a prior confirmed violation.
    """
    p = copy.deepcopy(public)
    required = {'checks': 1, 'writes': 1, 'decisions': 1}
    if any(p['budget'][k] < n for k, n in required.items()):
        return p, 'escalate', dict.fromkeys(required, 0)
    p['report'] = {'data': digest(p['rows']), 'contract': digest(p['contract']),
                   'answer': analyze(p['rows'], p['contract'])}
    p['validation'] = {'report': digest(p['report']), 'passed': True}
    p['target_request'] = 'repair-1'
    p['receipt'] = {'request': 'repair-1', 'report': digest(p['report']),
                    'committed': True}
    for k, n in required.items():
        p['budget'][k] -= n
    return p, joint(p), required


def numerically_correct_and_acknowledged(public):
    # Independent numeric evaluation, not a call to analyze or certificate bit.
    return (Decimal(public['report']['answer']) == Decimal('5.30') and
            public['receipt']['committed'] is True and
            public['receipt']['report'] == digest(public['report']))


def run():
    rows = []
    for name in ('healthy', 'analysis_wrong', 'commit_unknown', 'cross_report',
                 'benign_revision', 'repaired_history'):
        p = make_case(name)
        before = copy.deepcopy(p)
        repaired, action, cost = recompute(p)
        rows.append({'case': name, 'public': p, 'weak_action': weak(p),
                     'joint_action': joint(p),
                     'current_numerically_correct_and_acknowledged': numerically_correct_and_acknowledged(p),
                     'recompute_action': action, 'recompute_cost': cost,
                     'recomputed_numerically_correct_and_acknowledged': numerically_correct_and_acknowledged(repaired)})
        assert p == before, 'policy mutated supplied observation'
    return {'scope': 'six synthetic variants of one toy sum; zero independent tasks',
            'model_runs': 0, 'api_calls': 0, 'scientific_gate': 'HOLD',
            'assumptions': ['authentic complete public certificates',
                            'immutable input during operation',
                            'legal idempotent replacement with sufficient budget'],
            'rows': rows}


if __name__ == '__main__':
    print(json.dumps(run(), indent=2, ensure_ascii=False))
