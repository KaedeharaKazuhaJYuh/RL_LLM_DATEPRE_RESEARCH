import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from faultda_bench.acceptance.audit import CATALOG, REPO, check_inventory, pinned_path


class AcceptanceTests(unittest.TestCase):
    def test_real_inventory_separates_review_from_science(self):
        result = check_inventory()
        self.assertEqual(result['human_review']['development_tasks']['tasks'], 24)
        self.assertEqual(result['human_review']['new_regression_cases']['status'], 'passed')
        self.assertEqual(result['scientific_gate'], 'HOLD')
        self.assertIs(result['scientific_release_ready'], False)

    def test_historical_snapshot_still_pending(self):
        result = check_inventory(catalog_path=REPO / 'faultda_bench/protocols/acceptance_v6.json')
        self.assertEqual(result['human_review']['new_regression_cases']['status'], 'pending')

    def test_missing_new_review_cannot_use_old_signature(self):
        with tempfile.TemporaryDirectory() as folder:
            root, path, catalog = self.fixture(folder)
            name = 'faultda_bench/reports/regression_review_2026_10_11/receipt.json'
            del catalog['files'][name]
            path.write_text(json.dumps(catalog), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'new review provenance'):
                check_inventory(root, path)

    def fixture(self, folder):
        root = Path(folder)
        catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
        for name in catalog['files']:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO / name, target)
        path = root / 'catalog.json'
        path.write_text(json.dumps(catalog), encoding='utf-8')
        return root, path, catalog

    def test_changed_or_missing_trace_is_rejected(self):
        for mode in ('changed', 'missing'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                root, path, _ = self.fixture(folder)
                target = root / 'faultda_bench/reports/regression_v5_results.jsonl'
                if mode == 'changed':
                    target.write_bytes(target.read_bytes() + b'\n')
                else:
                    target.unlink()
                with self.assertRaises(ValueError):
                    check_inventory(root, path)

    def test_rehashed_receipt_cannot_extend_old_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root, path, catalog = self.fixture(folder)
            name = 'faultda_bench/reports/human_review_round2_2026_10_11/receipt.json'
            receipt = json.loads((root / name).read_text(encoding='utf-8'))
            receipt['new_regression_fixtures_human_reviewed'] = True
            data = json.dumps(receipt).encode()
            (root / name).write_bytes(data)
            catalog['files'][name] = hashlib.sha256(data).hexdigest()
            path.write_text(json.dumps(catalog), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'old review'):
                check_inventory(root, path)

    def test_original_review_checked_even_if_archive_rehashed(self):
        import zipfile
        with tempfile.TemporaryDirectory() as folder:
            root, path, catalog = self.fixture(folder)
            name = 'faultda_bench/reports/human_review_round2_2026_10_11/submitted_records.zip'
            with zipfile.ZipFile(root / name, 'w') as archive:
                archive.writestr('HUMAN_REVIEW_2026-10-11.md', 'altered conclusion')
            catalog['files'][name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
            path.write_text(json.dumps(catalog), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'original human review'):
                check_inventory(root, path)

    def test_path_escape_rejected(self):
        for name in ('../outside', '/absolute', 'a/../../outside', 'a\\outside'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                pinned_path(REPO, name)


if __name__ == '__main__':
    unittest.main()
