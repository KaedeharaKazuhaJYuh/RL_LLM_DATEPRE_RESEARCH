"""Software boundary checks are not AppWorld task or model evidence."""
import unittest
from unittest.mock import patch

from research.reliability_reset.hash_probe175 import Snapshot, load_functions, probe


class HashBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = probe()
        cls.rows = {row['case']: row for row in cls.result['cases']}

    def test_unchanged_content_and_benign_recreation_are_retained(self):
        for name in ('unchanged_content', 'same_content_recreated_id'):
            row = self.rows[name]
            self.assertTrue(row['reference_content_multiset_equal'])
            self.assertEqual(row['native_helper_changed_models'], [])
            self.assertEqual(row['native_helper_added_ids'], [])
            self.assertEqual(row['native_helper_removed_ids'], [])
            self.assertFalse(row['helper_misses_content_multiset_change'])

    def test_ordinary_updates_additions_and_removals_are_detected(self):
        expected = {'ordinary_content_update': ('updated', [2]),
                    'ordinary_addition': ('added', [3]),
                    'ordinary_removal': ('removed', [2]),
                    'duplicate_added_changes_size': ('added', [3])}
        for name, (kind, ids) in expected.items():
            with self.subTest(case=name):
                row = self.rows[name]
                self.assertEqual(row['native_helper_changed_models'], ['probe.Item'])
                self.assertEqual(row[f'native_helper_{kind}_ids'], ids)
                self.assertFalse(row['reference_content_multiset_equal'])

    def test_identity_permutation_is_not_mislabeled_as_a_content_miss(self):
        row = self.rows['content_permuted_across_ids']
        self.assertFalse(row['reference_identity_map_equal'])
        self.assertTrue(row['reference_content_multiset_equal'])
        self.assertFalse(row['helper_misses_content_multiset_change'])

    def test_multiplicity_change_is_missed_by_both_unchanged_native_helpers(self):
        row = self.rows['duplicate_multiplicity_redistributed']
        self.assertFalse(row['reference_content_multiset_equal'])
        self.assertEqual(row['native_helper_changed_models'], [])
        for kind in ('added', 'updated', 'removed'):
            self.assertEqual(row[f'native_helper_{kind}_ids'], [])
        self.assertTrue(row['helper_misses_content_multiset_change'])
        self.assertEqual(sum(r['helper_misses_content_multiset_change'] for r in self.result['cases']), 1)

    def test_fixture_tampering_is_rejected_before_execution(self):
        with self.assertRaisesRegex(ValueError, 'digest'):
            load_functions(b'raise RuntimeError("must not execute")')

    def test_duplicate_primary_key_is_not_a_valid_adapter_input(self):
        with self.assertRaisesRegex(ValueError, 'primary key'):
            Snapshot(((1, 'a'), (1, 'b')), 1)

    def test_source_hash_definition_omits_id_and_no_real_task_is_claimed(self):
        self.assertTrue(self.result['hash_omits_id_source_fact'])
        self.assertEqual(self.result['counts']['synthetic_software_cases'], 8)
        for key in ('real_tasks', 'native_task_scorer_runs', 'AppWorld_environment_runs', 'new_model_api_calls'):
            self.assertEqual(self.result['counts'][key], 0)

    def test_probe_needs_neither_network_nor_an_appworld_installation(self):
        import socket
        with patch.object(socket, 'create_connection', side_effect=AssertionError('Network forbidden')):
            self.assertEqual(probe(), self.result)


if __name__ == '__main__':
    unittest.main()
