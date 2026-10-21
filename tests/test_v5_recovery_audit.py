import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research.io import write_json
from research.v5_recovery_audit import evaluation, training
from research.v5_recovery_protocol import load


class RecoveryAuditTests(unittest.TestCase):
    def test_evaluation_rejects_missing_duplicate_and_wrong_weights(self):
        tasks, _, manifest = load()
        rows = [{'task_id': t['task_id'], 'source_id': t['source_id'], 'family': t['pair_family'],
                 'language': t['language'], 'mode': mode, 'passed': False, 'reward': 0.0,
                 'actions': ['abort'], 'duplicate_commit': False, 'decisions': 1, 'inspections': 0,
                 'commits': int(mode in ('none', 'after_commit')),
                 'tool_calls': int(mode in ('none', 'after_commit'))}
                for t in tasks if t['split'] == 'dev' for mode in manifest['modes']]
        report = dict(schema_version='v5-recovery-eval-1', protocol_sha256='protocol',
                      model_sha256='model', adapter_sha256='adapter', episodes=len(rows),
                      passed=0, records=rows)
        with tempfile.TemporaryDirectory() as folder, patch('research.v5_recovery_audit.digest', return_value='protocol'):
            path = Path(folder)/'eval.json'
            write_json(path, report)
            evaluation(path, 'adapter', 'model')
            for field, value in [('records', rows[:-1]), ('records', rows[:-1]+rows[:1]),
                                 ('adapter_sha256', 'other'), ('passed', 1)]:
                bad = copy.deepcopy(report)
                bad[field] = value
                write_json(path, bad)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    evaluation(path, 'adapter', 'model')
            bad = copy.deepcopy(report)
            bad['records'][0]['decisions'] = 3
            write_json(path, bad)
            with self.assertRaisesRegex(ValueError, 'ledger'):
                evaluation(path, 'adapter', 'model')

    def test_training_rejects_incomplete_and_altered_schedule_or_ledger(self):
        from experiments.v5_recovery_train import schedule
        tasks, _, manifest = load()
        seed = manifest['seeds'][0]
        rows = []
        counters = dict(tool_calls=0, inspections=0, decisions=0)
        for group, (task, mode, reset, pair) in enumerate(schedule(tasks, seed)):
            check = int(reset and mode != 'none')
            calls = int(mode in ('none', 'after_commit'))
            score = dict(tool_calls=calls, inspections=check, decisions=check+1)
            counters['tool_calls'] += calls
            counters['inspections'] += check
            counters['decisions'] += check+4
            rows.append(dict(group=group, pair=pair, task_id=task['task_id'], mode=mode,
                             reset_after_inspection=reset, scores=[score]*4,
                             actions=[['abort']]*4, updated=False))
        report = dict(schema_version='v5-recovery-train-1', arm='paired', seed=seed,
                      protocol_sha256='hash', model_sha256='hash', initial_adapter_sha256='hash',
                      adapter_sha256='hash', optimizer_steps=0, records=rows,
                      budget={'terminal_branches': 64, **counters})
        with tempfile.TemporaryDirectory() as folder, patch('research.v5_recovery_audit.digest', return_value='hash'):
            path = Path(folder)/'summary.json'
            write_json(path, report)
            training(folder, 'paired', seed)
            for field in ('groups', 'schedule', 'ledger', 'identity'):
                bad = copy.deepcopy(report)
                if field == 'groups':
                    bad['records'].pop()
                elif field == 'schedule':
                    bad['records'][0]['mode'] = 'after_commit'
                elif field == 'ledger':
                    bad['budget']['tool_calls'] += 1
                else:
                    bad['seed'] += 1
                write_json(path, bad)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    training(folder, 'paired', seed)
