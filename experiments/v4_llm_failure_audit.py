"""Describe frozen-dev failures without feeding them into train-task selection."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from research.io import ROOT, digest, write_json


def failure_kind(record, plan):
    if record['passed']:
        return 'passed'
    expected = [plan[0], *([plan[0]] if record['fault'] else []), *plan[1:], 'stop']
    steps = record['steps']
    actual = [step.get('action') for step in steps]
    for index, (got, wanted) in enumerate(zip(actual, expected)):
        if steps[index].get('parse_error') or got is None:
            return 'parse_error'
        if got != wanted:
            if got == 'stop':
                return 'early_stop'
            if record['fault'] and index == 1:
                return 'retry_missing'
            if index == 0:
                return 'wrong_first_tool'
            if index in (2, 3) or (not record['fault'] and index in (1, 2)):
                return 'wrong_later_tool'
            return 'wrong_action'
    if len(actual) < len(expected):
        return 'missing_stop' if actual == expected[:len(actual)] and len(actual) == len(expected)-1 else 'incomplete'
    if len(actual) > len(expected):
        return 'extra_action'
    return 'verification_or_timeout'


def run(protocol, evaluations, out):
    oracle = json.loads((protocol / 'dev_oracle.json').read_text(encoding='utf-8'))
    runs = []
    failures_by_key = defaultdict(list)
    for name, path in evaluations:
        report = json.loads(path.read_text(encoding='utf-8'))
        if report['protocol_sha256'] != digest(protocol / 'manifest.json'):
            raise ValueError('evaluation protocol does not match')
        tally = Counter()
        by_slice = defaultdict(Counter)
        for record in report['records']:
            kind = failure_kind(record, oracle[record['task_id']]['plan'])
            tally[kind] += 1
            by_slice[f"{record['novelty']}:{'fault' if record['fault'] else 'clean'}"][kind] += 1
            if kind != 'passed':
                failures_by_key[(record['task_id'], bool(record['fault']))].append(name)
        runs.append({'name': name, 'evaluation_sha256': digest(path),
                     'passed': tally['passed'], 'failures': sum(tally.values()) - tally['passed'],
                     'failure_kinds': dict(sorted(tally.items())),
                     'by_slice': {key: dict(sorted(value.items()))
                                  for key, value in sorted(by_slice.items())}})
    common = [{'task_id': task_id, 'fault': fault, 'failed_seeds': names}
              for (task_id, fault), names in sorted(failures_by_key.items())
              if len(names) == len(evaluations)]
    summary = {'schema_version': 'v4-llm-failure-audit-1', 'runs': runs,
               'common_failures': common, 'common_failure_count': len(common),
               'external_test': False}
    write_json(out, summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=ROOT / 'tasks/v4/llm_hard_v1')
    parser.add_argument('--evaluation', nargs=2, metavar=('NAME', 'PATH'),
                        action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.protocol,
                         [(name, Path(path)) for name, path in args.evaluation], args.out),
                     ensure_ascii=False, indent=2))
