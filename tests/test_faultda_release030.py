import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from faultda_bench.release030.audit import CATALOG, REPO, check_inventory


class Release030Tests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder); catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
        for name in set(catalog['files']) | {'faultda_bench/protocols/acceptance_v18.json'}:
            target=root/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(REPO/name,target)
        path=root/'catalog.json'; path.write_text(json.dumps(catalog),encoding='utf-8')
        return root,path,catalog

    def test_current_scope_stays_pending(self):
        result=check_inventory()
        self.assertEqual(set(result['new_experiments_review'].values()),{'pending'})
        self.assertFalse(result['provider_authenticity_verified'])
        self.assertFalse(result['external_publication_confirmed'])

    def test_tampered_new_response_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root,path,catalog=self.fixture(folder)
            target=root/'faultda_bench/reports/boundary_v21_deepseek.jsonl'
            target.write_bytes(target.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'changed evidence'): check_inventory(root,path)

    def test_new_review_cannot_borrow_old_signature(self):
        with tempfile.TemporaryDirectory() as folder:
            root,path,catalog=self.fixture(folder); catalog['new_experiments_human_reviewed']=True
            path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError,'old human'): check_inventory(root,path)

    def test_historical_hash_cannot_be_replaced_even_with_rehashed_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            root,path,catalog=self.fixture(folder)
            name='faultda_bench/reports/stopping_v18_deepseek.jsonl'
            target=root/name; target.write_bytes(target.read_bytes()+b'\n')
            catalog['files'][name]=hashlib.sha256(target.read_bytes()).hexdigest()
            path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError,'historical scope'): check_inventory(root,path)
