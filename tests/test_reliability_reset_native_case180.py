"""Preflight controls; no protected AppWorld inputs or native task scores."""
from collections import Counter
from contextlib import closing
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from research.reliability_reset import native_case180 as native
from research.reliability_reset.hash_probe175 import probe


class NativeStartPreflightTests(unittest.TestCase):
    def test_unique_start_lemma_against_all_small_content_bags(self):
        # Independent Counter oracle, all three-label sequences of length 0..4.
        # These are mathematical software controls, never task observations.
        checked = 0
        for size in range(5):
            sequences = list(itertools.product('abc', repeat=size))
            for start in sequences:
                if len(set(start)) != size:
                    continue
                for end in sequences:
                    if set(start) == set(end):
                        self.assertEqual(Counter(start), Counter(end))
                        checked += 1
        self.assertEqual(checked, 52)

    def test_duplicate_start_is_a_real_missing_premise_in_the_old_helper(self):
        row = next(row for row in probe()['cases']
                   if row['case'] == 'duplicate_multiplicity_redistributed')
        self.assertTrue(row['helper_misses_content_multiset_change'])
        self.assertNotEqual(Counter(v for _, v in row['start']),
                            Counter(v for _, v in row['end']))

    def test_original_sql_replay_applies_both_single_and_many_operations(self):
        with tempfile.TemporaryDirectory() as tmp, closing(sqlite3.connect(':memory:')) as conn:
            conn.execute('CREATE TABLE items(id INTEGER PRIMARY KEY, record_hash TEXT)')
            operations = [('INSERT INTO items VALUES (?, ?)', [1, 'a'], False),
                          ('INSERT INTO items VALUES (?, ?)', [[2, 'a'], [3, 'b']], True)]
            path = Path(tmp) / 'delta.jsonl'
            path.write_text(''.join(json.dumps(row) + '\n' for row in operations))
            native.load_apply_changes()(conn, str(path))
            self.assertEqual(native.inspect_hashes(conn),
                             {'hash_tables': 1, 'rows': 3, 'duplicate_groups': 1,
                              'invalid_hash_rows': 0})

    def test_invalid_hashes_cannot_certify_uniqueness(self):
        with closing(sqlite3.connect(':memory:')) as conn:
            conn.execute('CREATE TABLE items(record_hash)')
            conn.executemany('INSERT INTO items VALUES (?)', [(None,), ('',), (42,), ('a',)])
            self.assertEqual(native.inspect_hashes(conn)['invalid_hash_rows'], 3)

    def test_empty_hash_table_is_valid_but_absent_hash_schema_is_not(self):
        with closing(sqlite3.connect(':memory:')) as conn:
            conn.execute('CREATE TABLE bookkeeping(id INTEGER)')
            with self.assertRaisesRegex(ValueError, 'No record_hash'):
                native.inspect_hashes(conn)
            conn.execute('CREATE TABLE "quoted""name"(record_hash TEXT)')
            stats = native.inspect_hashes(conn)
            self.assertEqual(stats['hash_tables'], 1)
            self.assertEqual(stats['rows'], 0)

    def test_public_fixture_tampering_is_rejected_before_compiling(self):
        with self.assertRaisesRegex(ValueError, 'digest'):
            native.load_apply_changes(b'raise RuntimeError("must not execute")')

    def test_native_input_tampering_is_rejected_before_sql_or_zip_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'wrong.zip'
            p.write_bytes(b'not a native package')
            with self.assertRaisesRegex(ValueError, 'package digest'):
                native.preflight(p, Path(tmp))

    def test_missing_task_delta_is_not_silently_treated_as_an_empty_delta(self):
        with tempfile.TemporaryDirectory() as tmp, closing(sqlite3.connect(':memory:')) as conn:
            conn.execute('CREATE TABLE items(record_hash TEXT)')
            p = Path(tmp) / 'software-control.zip'
            with zipfile.ZipFile(p, 'w') as archive:
                archive.writestr('data/version.txt', '0.2.0')
                archive.writestr('data/datasets/train.txt', '82e2fac_1\n')
                archive.writestr('data/base_dbs/admin.db', conn.serialize())
                archive.writestr('data/tasks/82e2fac_1/dbs/admin.jsonl', '')
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            with patch.object(native, 'ZIP_SHA256', digest), patch.object(native, 'APPS', ('admin',)):
                with self.assertRaises(FileNotFoundError):
                    native.preflight(p, Path(tmp) / 'missing-originals')


if __name__ == '__main__':
    unittest.main()
