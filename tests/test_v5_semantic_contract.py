"""Executable metamorphic contracts; deliberately excluded from frozen training."""
import tempfile
import unittest
from pathlib import Path

from agent.tools import execute_tool
from research.io import write_table, digest
from research.oracle import expected
from verifier.score import verify


class SemanticContracts(unittest.TestCase):
    def test_consistent_wrong_answers_do_not_satisfy_correctness_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            wrong = {'count': 2, 'min': 1, 'max': 3, 'mean': 0}
            for name, column in [('original', 'x'), ('renamed', 'value')]:
                path = Path(folder)/f'{name}.csv'
                write_table(path, [column], [{column: '1'}, {column: '3'}])
                params = {'column': column}
                result = {'answer': wrong, 'evidence': {'input_sha256': digest(path), 'rows_read': 2}}
                checked = verify(result, expected(path, 'describe_numeric', params),
                                 [{'tool': 'describe_numeric', 'ok': True}],
                                 {'input_sha256': digest(path), 'allowed_tools': ['describe_numeric']})
                self.assertFalse(checked['passed'])
                self.assertFalse(checked['checks']['answer'])

    def answer(self, folder, name, columns, rows, action, column='x'):
        path = Path(folder)/f'{name}.csv'
        write_table(path, columns, rows)
        return execute_tool(action, {'uri': str(path), 'params': {'column': column, 'window': 2}})['answer']

    def test_column_rename_requires_synchronized_parameter(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = [{'x': '1'}, {'x': '3'}, {'x': ''}]
            original = self.answer(folder, 'original', ['x'], rows, 'describe_numeric')
            renamed = [{'value': r['x']} for r in rows]
            self.assertEqual(original, self.answer(folder, 'renamed', ['value'], renamed,
                                                  'describe_numeric', 'value'))
            with self.assertRaises(ValueError):
                self.answer(folder, 'unsynchronized', ['value'], renamed, 'describe_numeric')

    def test_irrelevant_column_and_row_permutation_have_limited_scope(self):
        with tempfile.TemporaryDirectory() as folder:
            rows = [{'x': '1'}, {'x': '3'}, {'x': '8'}]
            decorated = [{**r, 'note': str(i)} for i, r in enumerate(rows)]
            original = self.answer(folder, 'original', ['x'], rows, 'describe_numeric')
            self.assertEqual(original, self.answer(folder, 'decorated', ['x', 'note'], decorated,
                                                  'describe_numeric'))
            self.assertEqual(original, self.answer(folder, 'permuted', ['x'], list(reversed(rows)),
                                                  'describe_numeric'))
            # Order is semantic for rolling windows, and extra columns change schema answers.
            self.assertNotEqual(self.answer(folder, 'rolling', ['x'], rows, 'rolling_mean'),
                                self.answer(folder, 'reverse', ['x'], list(reversed(rows)), 'rolling_mean'))
            self.assertNotEqual(self.answer(folder, 'schema', ['x'], rows, 'profile_schema'),
                                self.answer(folder, 'schema_extra', ['x', 'note'], decorated, 'profile_schema'))
