"""Crossed source x log evaluation with independently executed recovery baselines.

Recovery parameters are the original public request, never verifier answers.
Timeout observations in this suite are simulated; process isolation is a separate suite.
"""
import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path
from agent.tools import execute_tool
from research.io import ROOT, digest, write_json
from research.oracle import expected
from research.v3_recovery import examples, inject, repair_args, heuristic_predict
from research.v3_leave_one_source_out import STYLES, restyle, bootstrap
from research.v3_selective import SelectiveRecoveryPolicy, metrics
from verifier.score import verify


def execute_repair(item, prediction, folder):
    if prediction == 'escalate':
        return False, 'escalated_without_execution'
    uri = ROOT / f"tasks/v3_real/data/{item['source']}.csv"
    faulty, _ = inject(item['fault'], item['action'], item['params'], uri, folder)
    input_hash = digest(uri)
    started = time.perf_counter()
    try:
        if item['fault'] == 'timeout' and prediction != 'retry_deadline':
            raise TimeoutError('simulated deadline remains exceeded')
        args = repair_args(prediction, faulty, item['params'], uri, folder)
        result = execute_tool(item['action'], args)
        checked = verify(result, expected(uri, item['action'], item['params']),
                         [{'tool': item['action'], 'ok': True}],
                         {'allowed_tools': [item['action']], 'max_tool_calls': 1, 'max_steps': 1,
                          'max_seconds': 10, 'elapsed_seconds': time.perf_counter()-started, 'input_sha256': input_hash})
        passed = checked['passed'] and digest(uri) == input_hash
        return passed, 'verified' if passed else 'verification_failed'
    except (ValueError, KeyError, OSError) as exc:
        return False, type(exc).__name__


def evaluate(out='reports/v3_final.json'):
    meta = json.loads((ROOT/'tasks/v3_real/manifest.json').read_text(encoding='utf-8'))['sources']
    sources = sorted(meta)
    for source in sources:
        if digest(ROOT/f'tasks/v3_real/data/{source}.csv') != meta[source]['derived_sha256']:
            raise ValueError('source hash mismatch: '+source)
    pool = {}
    for source in sources:
        pool[source] = [{**row, 'style': style, 'message': restyle(row['message'], style)}
                        for row in examples(source, meta[source]) for style in STYLES]
    records, folds = [], []
    with tempfile.TemporaryDirectory(prefix='v3_final_') as folder:
        for index, heldout in enumerate(sources):
            calibration = sources[(index+1) % len(sources)]
            fit = [s for s in sources if s not in {heldout, calibration}]
            training = [r for s in fit for r in pool[s]]
            cal = pool[calibration]
            policy = SelectiveRecoveryPolicy()
            policy.fit([r['message'] for r in training], [r['label'] for r in training])
            policy.calibrate([r['message'] for r in cal], [r['label'] for r in cal])
            before = hashlib.sha256(policy.weights.tobytes()).hexdigest()
            threshold = policy.confidence_threshold
            for i, item in enumerate(pool[heldout]):
                for mode in ('none', 'rule', 'selective'):
                    prediction = ('no_repair' if mode == 'none' else heuristic_predict(item['message'])
                                  if mode == 'rule' else policy.predict(item['message']))
                    passed, status = execute_repair(item, prediction, Path(folder)/heldout/str(i)/mode)
                    records.append({'source': heldout, 'style': item['style'], 'action': item['action'],
                                    'fault': item['fault'], 'mode': mode, 'prediction': prediction,
                                    'classification_correct': prediction == item['label'],
                                    'execution_passed': passed, 'status': status})
            assert before == hashlib.sha256(policy.weights.tobytes()).hexdigest()
            assert threshold == policy.confidence_threshold
            folds.append({'heldout': heldout, 'calibration': calibration, 'fit': fit,
                          'policy_sha256': before, 'threshold': threshold if threshold != float('inf') else None,
                          'reject_all': threshold == float('inf')})
    groups = {mode: metrics([r for r in records if r['mode'] == mode]) for mode in ('none','rule','selective')}
    selected = [r for r in records if r['mode'] == 'selective']
    by_source = {s: metrics([r for r in selected if r['source'] == s]) for s in sources}
    result = {'version': '3.6-final', 'protocol': 'crossed source x log style; leave one source out',
              'scope': 'known injected faults; public original request supplied; timeout observation simulated',
              'threshold_rule': 'maximum calibration coverage with zero observed calibration errors',
              'test_updates': False, 'folds': folds, 'baselines': groups, 'by_source': by_source,
              'by_style': {s: metrics([r for r in selected if r['style'] == s]) for s in STYLES},
              'source_bootstrap_execution_95': bootstrap([v['execution_rate'] for v in by_source.values()]),
              'records': records}
    write_json(ROOT/out, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='reports/v3_final.json')
    result = evaluate(parser.parse_args().out)
    print(json.dumps({k:v for k,v in result.items() if k != 'records'}, indent=2))
