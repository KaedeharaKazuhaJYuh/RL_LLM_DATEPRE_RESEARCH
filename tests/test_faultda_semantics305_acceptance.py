import json
import shutil
import tempfile
import unittest
from pathlib import Path
from faultda_bench.semantics305.audit import CATALOG, REPO, check_inventory


class Semantics305AcceptanceTests(unittest.TestCase):
    def fixture(self,folder):
        root=Path(folder); catalog=json.loads(CATALOG.read_text(encoding='utf-8'))
        for name in set(catalog['files']) | {'faultda_bench/protocols/acceptance_v19.json'}:
            target=root/name; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(REPO/name,target)
        path=root/'catalog.json'; path.write_text(json.dumps(catalog),encoding='utf-8')
        return root,path,catalog

    def test_current_inventory_does_not_certify_science(self):
        result=check_inventory(); self.assertFalse(result['provider_authenticity_verified']); self.assertFalse(result['external_publication_confirmed'])

    def test_modified_response_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            root,path,catalog=self.fixture(folder); target=root/'faultda_bench/reports/semantics_v22_deepseek.jsonl'
            target.write_bytes(target.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'changed evidence'): check_inventory(root,path)

    def test_new_scope_cannot_borrow_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root,path,catalog=self.fixture(folder); catalog['new_experiments_human_reviewed']=True; path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError,'borrow'): check_inventory(root,path)

    def test_old_inventory_cannot_be_dropped(self):
        with tempfile.TemporaryDirectory() as folder:
            root,path,catalog=self.fixture(folder); del catalog['files']['faultda_bench/reports/boundary_v21_deepseek.jsonl']; path.write_text(json.dumps(catalog))
            with self.assertRaisesRegex(ValueError,'historical'): check_inventory(root,path)
