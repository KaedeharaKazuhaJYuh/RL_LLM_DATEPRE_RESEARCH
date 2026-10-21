import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from faultda_bench.review515 import lineage


class LocalLineageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seen = lineage.seen_sources()
        cls.occupancy = next(s for s in cls.seen if s['source_id'] == 'uci_occupancy')
        cls.metadata = cls.occupancy['source_metadata'][0]

    def assess(self, candidate):
        return lineage.assess_candidate(candidate, seen=self.seen)

    def test_trace_eight_rows_and_preserve_historical_scope(self):
        report = lineage.audit()
        self.assertEqual(report, lineage.audit())
        self.assertEqual(len(report['eight_row_trace']), 8)
        self.assertEqual([r['original_source_id'] for r in report['eight_row_trace']],
                         ['140', '151', '162', '173', '184', '195', '206', '217'])
        self.assertEqual(report['observed_reuse']['prompt_pairs'], 12)
        self.assertEqual(report['observed_reuse']['coherent_task_views'], 6)
        self.assertEqual(report['observed_reuse']['independent_task_clusters'], 1)
        self.assertTrue(report['source_lineage']['original_manifest_external_test'])
        self.assertTrue(report['source_lineage']['original_manifest_one_time_evaluation'])
        self.assertFalse(report['source_lineage']['future_unseen_external_test_eligible'])
        self.assertTrue(report['historical_usage']['later_development_reuse_confirmed'])
        self.assertFalse(report['historical_usage']['earlier_training_leakage_proved'])
        self.assertEqual(report['new_provider_requests'], 0)

    def test_source_identity_is_case_insensitive_and_path_cannot_wash_it(self):
        result = self.assess({'source_id': ' UCI_OCCUPANCY ', 'path': 'new/test.csv'})
        self.assertEqual(result['decision'], 'REJECT_SEEN_LINEAGE')
        self.assertFalse(result['path_is_independence_evidence'])

    def test_same_content_with_new_name_is_rejected(self):
        result = self.assess({'source_id': 'renamed-independent-source',
                              'content_sha256': self.metadata['sha256'].upper()})
        self.assertEqual(result['decision'], 'REJECT_SEEN_LINEAGE')
        self.assertEqual(result['matches'][0]['seen_source_id'], 'uci_occupancy')

    def test_same_raw_archive_or_doi_is_rejected(self):
        for field, value in [('archive_sha256', self.metadata['archive_sha256']),
                             ('doi', 'https://doi.org/' + self.metadata['doi'])]:
            with self.subTest(field=field):
                self.assertEqual(self.assess({field: value})['decision'], 'REJECT_SEEN_LINEAGE')

    def test_nested_ancestor_rejects_disjoint_slice_and_transformed_hash(self):
        candidate = {'source_id': 'new-slice', 'sha256': 'a' * 64,
                     'ancestors': [{'source_id': 'renamed-parent',
                                    'ancestors': [{'upstream_url': self.metadata['upstream_url']}]}]}
        frozen = copy.deepcopy(candidate)
        result = self.assess(candidate)
        self.assertEqual(result['decision'], 'REJECT_SEEN_LINEAGE')
        self.assertEqual(result['matches'][0]['location'], 'candidate.ancestors[0].ancestors[0]')
        self.assertEqual(candidate, frozen)

    def test_whole_registry_not_only_occupancy_is_quarantined(self):
        for name in ('uci_banknote', 'uci_auto_mpg', 'uci_glass', 'source_00'):
            with self.subTest(name=name):
                self.assertEqual(self.assess({'source_id': name})['decision'], 'REJECT_SEEN_LINEAGE')

    def test_unknown_identity_and_path_only_never_auto_admit(self):
        for candidate in ({'source_id': 'unseen-declaration', 'sha256': 'f' * 64},
                          {'path': 'new/test.csv'}, {}, {'sha256': 'malformed'}):
            with self.subTest(candidate=candidate):
                result = self.assess(candidate)
                self.assertEqual(result['decision'], 'PENDING_LINEAGE_REVIEW')
                self.assertFalse(result['eligible_as_unseen_test'])
                self.assertEqual(result['approved_transport_requests'], 0)

    def test_malformed_or_cyclic_ancestry_fails_closed(self):
        cyclic = {'source_id': 'x'}
        cyclic['ancestors'] = [cyclic]
        for candidate in ([], {'ancestors': {}}, {'ancestors': ['occupancy']}, cyclic):
            with self.assertRaises(ValueError):
                self.assess(candidate)

    def test_altered_raw_bytes_and_derived_rows_are_not_quarantined_as_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            for relative in lineage.INPUTS:
                dest = target / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(lineage.REPO / relative, dest)
            raw = target / lineage.CSV
            original = raw.read_bytes()
            raw.write_bytes(original + b'\n')
            with self.assertRaisesRegex(ValueError, 'historical manifest'):
                lineage.audit(target)
            raw.write_bytes(original)
            derived_path = target / lineage.SEMANTIC
            derived = json.loads(derived_path.read_text(encoding='utf-8'))
            task = next(t for t in derived['tasks'] if t['id'] == 'window-01')
            task['versions']['v1'][0]['value'] = '999'
            derived_path.write_text(json.dumps(derived), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'values/timestamps'):
                lineage.audit(target)


if __name__ == '__main__':
    unittest.main()
