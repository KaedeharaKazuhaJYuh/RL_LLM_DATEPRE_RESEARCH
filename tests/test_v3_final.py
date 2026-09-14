import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from research.io import ROOT, load_jsonl
from research.v3_runtime import run_plan
from research.v3_selective import SelectiveRecoveryPolicy, metrics
from research.v3_final import evaluate, execute_repair
from research.v3_subprocess_faults import run_case


class FinalTests(unittest.TestCase):
    def test_stale_process_artifact_is_not_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/'timeout.json').write_text('{"status":"complete"}')
            result = run_case('timeout', deadline=.1, sleep=.4, folder=d)
            self.assertTrue(result['passed'])
            self.assertFalse(result['artifact_valid'])

    def task(self):
        gold = json.loads((ROOT/'tasks/v3/oracle.json').read_text(encoding='utf-8'))
        task = next(t for t in load_jsonl('tasks/v3/tasks.jsonl') if gold[t['task_id']]['plan'] == ['fill_missing'])
        return copy.deepcopy(task), gold[task['task_id']]

    def test_preflight_prevents_side_effects(self):
        for change in ('forbidden', 'zero_calls', 'zero_steps', 'hash', 'missing', 'deadline'):
            task, gold = self.task()
            if change == 'forbidden': task['allowed_tools'] = []
            if change == 'zero_calls': task['constraints']['max_tool_calls'] = 0
            if change == 'zero_steps': task['constraints']['max_steps'] = 0
            if change == 'hash': task['dataset']['sha256'] = 'bad'
            if change == 'missing': task['dataset']['uri'] = 'absent.csv'
            if change == 'deadline': task['constraints']['max_seconds'] = 0
            with tempfile.TemporaryDirectory() as d, patch('research.v3_runtime.execute_tool') as tool:
                result = run_plan(task, gold['plan'], gold, d)
                tool.assert_not_called()
                self.assertFalse(result['passed'], change)

    def test_retry_consumes_total_budget(self):
        task, gold = self.task()
        task['constraints']['max_tool_calls'] = 1
        with tempfile.TemporaryDirectory() as d:
            result = run_plan(task, gold['plan'], gold, d, recover=True, inject_error=True)
        self.assertFalse(result['passed'])
        self.assertEqual(1, result['tool_calls'])

    def test_calibration_errors_and_empty_calibration_reject(self):
        policy = SelectiveRecoveryPolicy()
        policy.fit(['unknown/missing column'], ['repair_column'])
        policy.calibrate(['unknown/missing column'], ['swap_bounds'])
        self.assertEqual('escalate', policy.predict('unknown/missing column'))
        policy.calibrate([], [])
        self.assertEqual('escalate', policy.predict('anything'))
        for text in ('ValueError', ' ValueError: ', '', 'TimeoutError'):
            self.assertEqual('escalate', policy.predict(text))
        self.assertIsNone(metrics([])['selective_risk'])

    def test_escalation_never_executes(self):
        with patch('research.v3_final.execute_tool') as tool:
            self.assertFalse(execute_repair({}, 'escalate', None)[0])
            tool.assert_not_called()

    def test_crossed_evaluation_and_accounting(self):
        with tempfile.TemporaryDirectory() as d:
            result = evaluate(str(Path(d)/'result.json'))
        for fold in result['folds']:
            self.assertNotIn(fold['heldout'], fold['fit'])
            self.assertNotIn(fold['calibration'], fold['fit'])
            self.assertNotEqual(fold['heldout'], fold['calibration'])
        for mode, summary in result['baselines'].items():
            self.assertEqual(480, summary['tasks'])
            self.assertEqual(summary['tasks'], summary['accepted']+summary['escalated'])
            rows = [r for r in result['records'] if r['mode'] == mode]
            self.assertEqual(summary['execution_passed'], sum(r['execution_passed'] for r in rows))
        self.assertEqual(0, result['by_style']['terse']['accepted'])
        self.assertIsNone(result['by_style']['terse']['selective_risk'])
        self.assertEqual(0, result['baselines']['none']['execution_passed'])
