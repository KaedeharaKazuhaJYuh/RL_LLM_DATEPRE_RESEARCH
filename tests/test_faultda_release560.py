import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from faultda_bench.release560 import VERSION, audit
from faultda_bench.stats560.core import round_floats

ROOT = audit.ROOT
COMMITTED = ROOT / audit.MANIFEST
EXPECTED_FILES = 690
EXPECTED_ADDITIONS = 30
EXPECTED_BASE_FILES = 660


def _leaves(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from _leaves(item)
    else:
        yield value


class Release560Tests(unittest.TestCase):
    """Pin the additive v47 freeze and the guards that make it worth having."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(COMMITTED.read_text(encoding='utf-8'))
        cls.base = json.loads(
            (ROOT / audit.BASE_CATALOG).read_text(encoding='utf-8'))['files']

    def _hashes(self, names):
        return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in sorted(names)}

    def test_manifest_verifies_on_clean_tree(self):
        result = audit.audit()
        self.assertEqual(EXPECTED_FILES, result['files_verified'])
        self.assertEqual(EXPECTED_ADDITIONS, result['additions_verified'])
        self.assertEqual(EXPECTED_ADDITIONS, len(audit.ADDITIONS))
        self.assertEqual(EXPECTED_BASE_FILES, result['base_catalog_files'])
        self.assertEqual(EXPECTED_FILES, len(self.manifest['files']))
        self.assertIs(True, result['v46_preserved'])
        self.assertEqual('offline_freeze_verified', result['status'])
        self.assertEqual(VERSION, result['version'])
        self.assertEqual('HOLD', result['scientific_gate'])
        self.assertEqual(0, result['new_model_executions'])
        self.assertEqual(0, result['new_provider_requests'])
        self.assertEqual(0, result['files_modified'])
        self.assertIs(False, result['rescored'])
        self.assertEqual(hashlib.sha256(COMMITTED.read_bytes()).hexdigest(),
                         result['catalog_sha256'])

    def test_tampered_copy_fails(self):
        names = audit.ADDITIONS[:3]
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder)
            for name in names:
                target = tmp / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
            reduced = {'files': {name: self.manifest['files'][name] for name in names}}
            self.assertEqual(3, audit.verify_files(tmp, reduced))
            victim = tmp / names[2]
            data = bytearray(victim.read_bytes())
            data[10] ^= 1
            victim.write_bytes(bytes(data))
            with self.assertRaisesRegex(ValueError, 'frozen bytes changed'):
                audit.verify_files(tmp, reduced)
        victim = 'faultda_bench/reports/stats560/summary.json'
        tampered = json.loads(COMMITTED.read_text(encoding='utf-8'))
        tampered['files'][victim] = '0' * 64
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'acceptance_v47_tampered.json'
            path.write_text(json.dumps(tampered, ensure_ascii=False, indent=2) + '\n',
                            encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'frozen bytes changed: ' + victim):
                audit.check_inventory(root=ROOT, catalog_path=path)

    def test_audit_refuses_frozen_output_locations(self):
        result = audit.audit()
        for name in (audit.MANIFEST, 'faultda_bench/reports/stats560/summary.json',
                     'faultda_bench/protocols/anything.json', 'docs/x.json'):
            with self.subTest(name=name):
                target = ROOT / name
                existed = target.exists()
                with self.assertRaises(ValueError):
                    audit.write_result(result, target)
                self.assertEqual(existed, target.exists())
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'work/v47.json'
            self.assertEqual(result, json.loads(
                audit.write_result(result, out).read_text(encoding='utf-8')))
            with self.assertRaises(FileExistsError):
                audit.write_result(result, out)

    def test_audit_does_not_modify_any_file(self):
        before = self._hashes(self.manifest['files'])
        self.assertEqual(EXPECTED_FILES, len(before))
        with tempfile.TemporaryDirectory() as folder:
            audit.write_result(audit.audit(), Path(folder) / 'result.json')
        self.assertEqual(before, self._hashes(self.manifest['files']))

    def test_committed_manifest_matches_emitter(self):
        fresh = audit.emit_manifest()
        self.assertEqual(self.manifest, fresh)
        self.assertEqual(list(self.manifest), list(fresh))
        self.assertEqual(list(self.manifest['files']), list(fresh['files']))
        self.assertEqual(COMMITTED.read_bytes(),
                         (json.dumps(fresh, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))

    def test_v46_preserved_and_living_documents_excluded(self):
        files = self.manifest['files']
        self.assertEqual(EXPECTED_BASE_FILES, len(self.base))
        for name, checksum in self.base.items():
            with self.subTest(name=name):
                self.assertEqual(checksum, files.get(name))
        self.assertEqual(list(self.base) + list(audit.ADDITIONS), list(files))
        self.assertNotIn(audit.MANIFEST, files)
        self.assertEqual(audit.BASE_CATALOG_SHA256, self.manifest['base_catalog_sha256'])
        excluded = self.manifest['excluded_living_documents']
        for name, reason in excluded.items():
            with self.subTest(name=name):
                self.assertTrue((ROOT / name).exists(), 'excluded document is missing: ' + name)
                self.assertNotIn(name, files)
                self.assertGreaterEqual(len(reason), 20)
        for name in ('README.md', 'faultda_bench/README.md', 'CHANGELOG.md',
                     'docs/PROJECT_HISTORY.md', 'docs/REPRODUCIBILITY.md', 'VERSION',
                     '.github/workflows/faultda-current.yml',
                     'faultda_bench/protocols/current_evidence_v1.json',
                     'tests/test_faultda_current_evidence.py'):
            with self.subTest(name=name):
                self.assertIn(name, excluded)
        for name in ('.github/workflows/tests.yml', 'pyproject.toml'):
            with self.subTest(name=name):
                self.assertIn(name, files)

    def test_result_has_no_float_and_is_quantization_fixed_point(self):
        result = audit.audit()
        self.assertEqual([], [v for v in _leaves(result) if isinstance(v, float)])
        self.assertEqual(result, round_floats(result))


if __name__ == '__main__':
    unittest.main()
