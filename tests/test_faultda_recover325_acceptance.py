import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from faultda_bench.recover325 import VERSION
from faultda_bench.recover325.audit import check_inventory


class InventoryTests(unittest.TestCase):
    def fixture(self, root):
        folder = root/'faultda_bench/protocols'; folder.mkdir(parents=True)
        (root/'evidence.txt').write_bytes(b'original')
        files = {'evidence.txt': hashlib.sha256(b'original').hexdigest()}
        (folder/'acceptance_v23.json').write_text(json.dumps({'files': files}), encoding='utf-8')
        c = {'version': VERSION, 'scientific_gate': 'HOLD', 'new_experiments': ['recover_v26'], 'new_experiments_human_reviewed': False, 'files': files}
        p = folder/'acceptance_v24.json'; p.write_text(json.dumps(c), encoding='utf-8'); return p, c

    def test_changed_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as f:
            root = Path(f); p, _ = self.fixture(root); self.assertEqual(check_inventory(root, p)['files_verified'], 1)
            (root/'evidence.txt').write_bytes(b'changed')
            with self.assertRaises(ValueError): check_inventory(root, p)

    def test_previous_scope_must_be_preserved(self):
        with tempfile.TemporaryDirectory() as f:
            root = Path(f); p, c = self.fixture(root); c['files'] = {}; p.write_text(json.dumps(c), encoding='utf-8')
            with self.assertRaises(ValueError): check_inventory(root, p)

    def test_new_review_cannot_be_forged(self):
        with tempfile.TemporaryDirectory() as f:
            root = Path(f); p, c = self.fixture(root); c['new_experiments_human_reviewed'] = True; p.write_text(json.dumps(c), encoding='utf-8')
            with self.assertRaises(ValueError): check_inventory(root, p)

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as f:
            root = Path(f); p, c = self.fixture(root); c['files']['../outside'] = 'fake'; p.write_text(json.dumps(c), encoding='utf-8')
            with self.assertRaises(ValueError): check_inventory(root, p)
