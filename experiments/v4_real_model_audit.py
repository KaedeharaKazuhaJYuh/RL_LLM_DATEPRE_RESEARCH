"""Audit frozen DeepSeek results on the attributed public-CSV diagnostic."""
import argparse
import collections
import json
from pathlib import Path

from research.io import ROOT, digest, write_json


def _first_divergence(actual, expected, steps):
    if any(step.get('parse_error') for step in steps):
        return 'parse_error'
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            if got == 'stop':
                return 'early_stop'
            if got in actual[:index]:
                return 'repeated_action'
            return 'wrong_action'
    if len(actual) < len(expected):
        return 'missing_action_or_stop'
    if len(actual) > len(expected):
        return 'extra_action'
    return 'actions_match_but_execution_failed'


def run(protocol, evaluation, out):
    protocol, evaluation, out = Path(protocol), Path(evaluation), Path(out)
    if out.exists():
        raise FileExistsError('new output file required')
    tasks = json.loads((protocol / 'tasks.json').read_text(encoding='utf-8'))
    by_id = {task['task_id']: task for task in tasks}
    oracle = json.loads((protocol / 'dev_oracle.json').read_text(encoding='utf-8'))
    result = json.loads(evaluation.read_text(encoding='utf-8'))
    manifest = json.loads((protocol / 'manifest.json').read_text(encoding='utf-8'))
    protocol_hash = digest(protocol / 'manifest.json')
    if result['protocol_sha256'] != protocol_hash or not result['greedy']:
        raise ValueError('evaluation is not the frozen protocol/greedy mode')
    records = result['records']
    modes = result.get('fault_modes', ['none'])
    expected_keys = {(task_id, mode) for task_id in by_id for mode in modes}
    actual_keys = [(row['task_id'], row.get('fault_kind', 'none')) for row in records]
    if len(actual_keys) != len(expected_keys) or set(actual_keys) != expected_keys:
        raise ValueError('evaluation does not cover every task exactly once')
    rows = []
    for record in records:
        task = by_id[record['task_id']]
        mode = record.get('fault_kind', 'none')
        plan = oracle[record['task_id']]['plan']
        expected = ([plan[0]] if mode != 'none' else []) + [*plan, 'stop']
        actual = [step['action'] for step in record['steps']]
        failures = [entry for entry in record.get('tool_history', []) if not entry['ok']]
        unexpected_failures = failures[1:] if mode != 'none' and failures else failures
        rows.append({'task_id': record['task_id'], 'source_id': task['source_id'],
                     'pair_family': task['pair_family'],
                     'paraphrase_id': task['paraphrase_id'],
                     'fault_kind': mode, 'injection_applied': record.get('injection_applied', False),
                     'passed': bool(record['passed']), 'actions': actual,
                     'expected': expected,
                     'tool_failures': [entry['error'].split(':', 1)[0] for entry in failures],
                     'first_divergence': None if record['passed'] else
                     ('tool_execution_failure' if unexpected_failures else
                      _first_divergence(actual, expected, record['steps']))})
    def summary(key):
        values = sorted({row[key] for row in rows})
        return {str(value): {'n': sum(row[key] == value for row in rows),
                             'passed': sum(row[key] == value and row['passed'] for row in rows)}
                for value in values}
    pairs = collections.defaultdict(dict)
    for row in rows:
        pairs[(row['source_id'], row['pair_family'], row['fault_kind'])][row['paraphrase_id']] = row['passed']
    if any(set(pair) != {0, 1} for pair in pairs.values()):
        raise ValueError('missing paired paraphrase')
    paired = collections.Counter(('both' if pair[0] and pair[1] else
                                  'zh_only' if pair[0] else 'en_only' if pair[1] else 'neither')
                                 for pair in pairs.values())
    errors = collections.Counter(row['first_divergence'] for row in rows if not row['passed'])
    audit = {'version': 'v4-real-model-audit-1', 'protocol_sha256': protocol_hash,
             'evaluation_sha256': digest(evaluation), 'episodes': len(rows),
             'passed': sum(row['passed'] for row in rows),
             'model_weights_sha256': digest(ROOT / result['model'] / 'model.safetensors'),
             'adapter_weights_sha256': digest(ROOT / result['adapter'] / 'adapter_model.safetensors'),
             'by_source': summary('source_id'), 'by_family': summary('pair_family'),
             'by_paraphrase': summary('paraphrase_id'), 'by_fault': summary('fault_kind'),
             'paired_paraphrases': {key: paired[key] for key in ('both', 'zh_only', 'en_only', 'neither')},
             'first_divergence': dict(sorted(errors.items())), 'records': rows}
    for field, actual in [('frozen_model_weights_sha256', audit['model_weights_sha256']),
                          ('frozen_adapter_weights_sha256', audit['adapter_weights_sha256'])]:
        if manifest.get(field) and manifest[field] != actual:
            raise ValueError(f'{field} mismatch')
    write_json(out, audit)
    return {key: value for key, value in audit.items() if key != 'records'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', default=str(ROOT / 'tasks/v4/real_csv_v1'))
    parser.add_argument('--evaluation', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.protocol, args.evaluation, args.out), indent=2))
