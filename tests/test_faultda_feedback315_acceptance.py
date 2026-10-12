import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from faultda_bench.feedback315 import VERSION
from faultda_bench.feedback315.audit import check_inventory


class InventoryTests(unittest.TestCase):
    def fixture(self, root):
        folder = root/'faultda_bench/protocols'; folder.mkdir(parents=True)
        (root/'evidence.txt').write_bytes(b'original')
        files = {'evidence.txt': hashlib.sha256(b'original').hexdigest()}
        (folder/'acceptance_v21.json').write_text(json.dumps({'files': files}), encoding='utf-8')
        catalog = {'version': VERSION, 'scientific_gate': 'HOLD', 'new_experiments': ['feedback_v24'],
                   'new_experiments_human_reviewed': False, 'files': files}
        path = folder/'acceptance_v22.json'; path.write_text(json.dumps(catalog), encoding='utf-8')
        return path, catalog

    def test_byte_change_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path, _ = self.fixture(root)
            self.assertEqual(check_inventory(root, path)['files_verified'], 1)
            (root/'evidence.txt').write_bytes(b'changed')
            with self.assertRaises(ValueError): check_inventory(root, path)

    def test_old_scope_cannot_be_dropped(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path, catalog = self.fixture(root)
            catalog['files'] = {}; path.write_text(json.dumps(catalog), encoding='utf-8')
            with self.assertRaises(ValueError): check_inventory(root, path)

    def test_cannot_borrow_human_signature(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path, catalog = self.fixture(root)
            catalog['new_experiments_human_reviewed'] = True; path.write_text(json.dumps(catalog), encoding='utf-8')
            with self.assertRaises(ValueError): check_inventory(root, path)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); path, catalog = self.fixture(root)
            catalog['files']['../outside.txt'] = 'fake'; path.write_text(json.dumps(catalog), encoding='utf-8')
            with self.assertRaises(ValueError): check_inventory(root, path)
