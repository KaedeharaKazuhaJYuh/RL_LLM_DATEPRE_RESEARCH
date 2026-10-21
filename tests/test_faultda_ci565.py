"""Regression checks for clean-checkout CI and the explicit v48 migration."""
import base64
import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from faultda_bench import ci565
from faultda_bench.current_evidence import runner
from tests import test_faultda_vericost565_determinism as determinism


class CIIntegrationTests(unittest.TestCase):
    def test_archived_bytes_and_current_corrections_are_all_verified(self):
        result = ci565.audit()
        self.assertEqual(result['explicit_ci_corrections'], 7)
        self.assertEqual(result['v47_files_unchanged'], 690)
        self.assertTrue(result['historical_v48_catalog_unchanged'])
        self.assertFalse(result['experiment_outputs_changed'])

    def test_a_current_correction_tamper_is_rejected(self):
        real = ci565.digest
        target = 'tests/test_faultda_vericost565_prereg.py'
        def altered(path):
            return '0' * 64 if str(path).replace('\\', '/').endswith(target) else real(path)
        with patch.object(ci565, 'digest', side_effect=altered):
            with self.assertRaisesRegex(ValueError, 'current evidence mismatch'):
                ci565.audit()

    def test_historical_catalog_and_original_archive_tampering_are_rejected(self):
        real = ci565.digest
        for filename, message in [('acceptance_v48.json', 'historical v48 catalog changed'),
                                  ('ci565_original_bytes.json', 'historical CI source archive changed')]:
            with self.subTest(filename=filename):
                with patch.object(ci565, 'digest', side_effect=lambda p: '0' * 64 if str(p).endswith(filename) else real(p)):
                    with self.assertRaisesRegex(ValueError, message):
                        ci565.migration()

    def test_missing_or_inaccessible_second_interpreter_is_optional_locally(self):
        with patch.dict(determinism.os.environ, {}, clear=True):
            self.assertIsNone(determinism.other_python())
        with patch.dict(determinism.os.environ, {'VERICOST_PY312': '/root/private/python'}):
            with patch.object(determinism.Path, 'is_file', side_effect=PermissionError):
                self.assertIsNone(determinism.other_python())

    def test_no_vericost_module_is_silently_excluded(self):
        registry = runner.load_registry()
        modules = {'tests.' + p.stem for p in (runner.ROOT / 'tests').glob('test_faultda_vericost565*.py')}
        self.assertTrue(modules.issubset(registry['test_modules']))
        self.assertEqual(len(modules), 15)

    def test_shallow_history_requires_explicit_skip_and_full_current_ci(self):
        text = (runner.ROOT / '.github/workflows/faultda-current.yml').read_text(encoding='utf-8')
        self.assertIn('fetch-depth: 0', text)
        self.assertIn('Require complete audit history', text)
        self.assertIn('VERICOST_PY312:', text)
        from tests import test_faultda_vericost565_audit as audit_tests
        self.assertIn('mandatory in current-evidence CI', audit_tests.FULL_HISTORY_REASON)
