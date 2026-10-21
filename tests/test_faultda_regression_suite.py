import json
from pathlib import Path
import tempfile
import unittest

from faultda_bench.regression.suite import run, summary
from faultda_bench.regression.verify import verify
from faultda_bench.semantic.tasks import sha


class RegressionSuiteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'suite.json'
        run(self.path)

    def alter_journal(self, change):
        result = json.loads(self.path.read_text(encoding='utf-8'))
        journal = self.path.parent / result['journal']
        rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]
        change(rows)
        journal.write_bytes(('\n'.join(json.dumps(r) for r in rows) + '\n').encode())
        result['journal_sha256'] = sha(journal)
        result['summary'] = summary(rows)
        self.path.write_bytes(json.dumps(result).encode())

    def test_all_six_cases_replay_without_api(self):
        result = verify(self.path)
        self.assertEqual(result['cases'], 6)
        self.assertEqual(result['api_requests'], 0)
        data = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(data['summary']['restored_but_unsafe'], 3)
        self.assertEqual(data['summary']['budget_rejections'], 3)

    def test_rehashed_private_ledger_corruption_is_rejected(self):
        def change(rows):
            rows[0]['private_records'][-1]['output']['A'] += 1
        self.alter_journal(change)
        with self.assertRaisesRegex(ValueError, 'effect replay: private_records'):
            verify(self.path)

    def test_rehashed_tool_feedback_corruption_is_rejected(self):
        def change(rows):
            rows[0]['trace'][2]['response']['revision'] = 999
        self.alter_journal(change)
        with self.assertRaisesRegex(ValueError, 'tool response replay'):
            verify(self.path)

    def test_removed_case_is_rejected_even_with_updated_summary(self):
        self.alter_journal(lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, 'case coverage'):
            verify(self.path)

    def test_boolean_cost_cannot_impersonate_integer(self):
        def change(rows):
            rows[0]['cost']['checks'] = True
        self.alter_journal(change)
        with self.assertRaisesRegex(ValueError, 'effect replay: cost'):
            verify(self.path)

    def test_source_cannot_be_relabelled_after_rehashing(self):
        def change(rows):
            rows[0]['source_id'] = 'unseen-source'
        self.alter_journal(change)
        with self.assertRaisesRegex(ValueError, 'case source attribution'):
            verify(self.path)

    def test_rehashed_contract_mutation_is_rejected(self):
        result = json.loads(self.path.read_text(encoding='utf-8'))
        path = self.path.parent / result['protocol']
        protocol = json.loads(path.read_text(encoding='utf-8'))
        protocol['task_snapshot'][0]['contract']['analysis'] = 'unreviewed replacement contract'
        path.write_bytes(json.dumps(protocol).encode())
        result['protocol_sha256'] = sha(path)
        self.path.write_bytes(json.dumps(result).encode())
        with self.assertRaisesRegex(ValueError, 'frozen task snapshot'):
            verify(self.path)

    def test_rerun_does_not_overwrite_frozen_protocol(self):
        before = self.path.with_suffix('.protocol.json').read_bytes()
        with self.assertRaisesRegex(ValueError, 'output exists'):
            run(self.path)
        self.assertEqual(before, self.path.with_suffix('.protocol.json').read_bytes())
