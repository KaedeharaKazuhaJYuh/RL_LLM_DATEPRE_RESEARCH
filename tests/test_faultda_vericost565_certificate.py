import json
import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from faultda_bench.vericost565 import certificate, costs, dp, instances, simulator
from faultda_bench.vericost565.canon import dumps

COUNTS = instances.VALIDATION_COUNTS
PAGE = instances.Materialized.page
BILLED = costs.billed_bytes


class _ClassSpecific(instances.Materialized):
    """Mutation (i): the removed x1.01 + 1 global signature, so magnitudes carry the class."""

    def __init__(self, profile, latent):
        super().__init__(profile, latent)
        if latent[0] != 'global':
            return
        faults = {item['part']: item for item in profile['fault_rows']}
        signature = {part: Decimal(faults[part]['v']) * Decimal('1.01') + 1
                     for part in sorted(self.affected)}
        self.override = {(part, faults[part]['row_id']): value
                         for part, value in signature.items()}
        totals = []
        for part in range(self.parts):
            total = self.report_totals[part]
            if part in self.affected:
                total = total - Decimal(faults[part]['v']) + signature[part]
            totals.append(total)
        self.source_totals = tuple(totals)
        self.source_strings = tuple(str(total) for total in totals)


class _LeakyReport(instances.Materialized):
    """Mutation (iv): a displayed report total that depends on the latent."""

    def __init__(self, profile, latent):
        super().__init__(profile, latent)
        if self.affected:
            self.report_strings = (str(self.report_totals[0] + 1),) + self.report_strings[1:]


def _spanning_page(self, part, offset, limit):
    """Mutation (ii): a read that spans two parts instead of the requested one."""
    following = (part + 1) % self.parts
    return PAGE(self, part, offset, limit) + PAGE(self, following, 0, 1)


def _per_returned_byte(profile, op, part=None):
    """Mutation (iii): reads billed per returned row instead of the full part scan."""
    if op == 'read_rows':
        return max(1, profile['parts'][part]['bytes'] // profile['parts'][part]['rows'])
    return BILLED(profile, op, part)


def _coarse_alive(self, cc, checked, mismatch, full):
    """Mutation (v): the compact state keeps the flag but drops which part was flagged."""
    out = []
    for index in range(len(self.latents)):
        affected, flag = self.affected[index], self.flags[index]
        if affected & checked != mismatch:
            continue
        if cc == dp.CC_OK and flag:
            continue
        if cc >= 0 and not flag:
            continue
        if full == 'match' and affected:
            continue
        if full == 'mismatch' and not affected:
            continue
        out.append(index)
    return tuple(out)


class CertificateTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(prefix='vericost565_certificate_')
        self.path = Path(self.folder.name) / 'dp_certificate_dev.json'
        self.addCleanup(self.folder.cleanup)

    def _run(self):
        return certificate.run('development', 1, certificate.FULL, certificate.UNIT, self.path)

    def _assert_guard_failed(self, case):
        with self.assertRaises(RuntimeError) as caught:
            self._run()
        self.assertIn('INV-DP violated', str(caught.exception), case)
        self.assertRegex(str(caught.exception), r'INV-DP violated: C[1-5]/')
        self.assertFalse(self.path.exists(), 'a failing certificate must write no file')
        with self.assertRaisesRegex(RuntimeError, 'certificate missing'):
            certificate.require(self.path)
        return str(caught.exception)

    # ---- the five mutation tests ---------------------------------------------------------------
    def test_mutation_class_specific_magnitudes_fails_the_certificate(self):
        with mock.patch.object(instances, 'materialize', _ClassSpecific):
            self._assert_guard_failed('class_specific_magnitudes')

    def test_mutation_read_spanning_two_parts_fails_the_certificate(self):
        with mock.patch.object(instances.Materialized, 'page', _spanning_page):
            self._assert_guard_failed('read_spans_two_parts')

    def test_mutation_reads_billed_per_returned_byte_fails_the_certificate(self):
        with mock.patch.object(costs, 'billed_bytes', _per_returned_byte):
            observed = self._assert_guard_failed('reads_billed_per_byte')
        self.assertIn('INV-DP violated: C1/', observed)

    def test_mutation_latent_dependent_report_total_fails_the_certificate(self):
        with mock.patch.object(instances, 'materialize', _LeakyReport):
            self._assert_guard_failed('latent_dependent_report_total')

    def test_mutation_coarsened_compact_state_fails_the_certificate(self):
        with mock.patch.object(dp.Oracle, '_alive_of', _coarse_alive):
            self._assert_guard_failed('compact_state_drops_the_flag')

    # ---- the passing certificate ----------------------------------------------------------------
    def test_the_reduced_certificate_passes_is_write_once_and_keeps_no_per_profile_record(self):
        clock = time.perf_counter()
        data, seconds = self._run()
        self.assertLess(time.perf_counter() - clock, 60.0,
                        'the reduced C1 case must stay under a minute')
        self.assertEqual(data['status'], 'pass')
        self.assertEqual(list(data['parts']), ['C1', 'C2', 'C3', 'C4', 'C5'])
        for name, part in data['parts'].items():
            self.assertEqual(part['status'], 'pass', name)
            self.assertLessEqual(part['max_violation'], dp.TOL, name)
            self.assertGreater(len(part['case_counts']), 0, name)
        self.assertEqual(data['tol'], 1e-09)
        self.assertEqual(data['mi_threshold_bits'], 1e-12)
        self.assertEqual(list(data['code_sha256']), list(certificate.CODE))
        self.assertEqual(data['instances_index_sha256'], certificate.sha(instances.INDEX))
        self.assertEqual(data['parts']['C2']['c2_scope'], certificate.FULL)
        self.assertEqual(data['parts']['C3']['c3_scope'], certificate.FULL)
        self.assertEqual(self.path.read_text(encoding='utf-8'), dumps(data))
        self.assertGreater(seconds['C1'], 0.0)
        self.assertEqual(certificate.require(self.path)[0]['status'], 'pass')
        text = self.path.read_text(encoding='utf-8')
        for profile in instances.load()['profiles']:
            self.assertNotIn(profile['profile_id'], text)
        for word in ('regret', 'expected_u', 'policy', 'spot:', 'publish_patch', 'cert-g3'):
            self.assertNotIn(word, text, word)
        with self.assertRaises(FileExistsError):
            self._run()

    # ---- the parts on their own -----------------------------------------------------------------
    def test_c1_compares_the_full_history_optimum_with_the_compact_root(self):
        profile = certificate.fixtures()[0]
        result = certificate.c1(profile, certificate.UNIT)
        self.assertEqual(result['case_counts']['cases'], 4)
        self.assertEqual(result['case_counts']['alphabet'], 27)
        self.assertLessEqual(result['max_violation'], dp.TOL)
        oracle = dp.Oracle(profile, certificate.C1_HISTORIES[0][1], costs.PRIMARY, 'rev1',
                           certificate.C1_HORIZON)
        references = [certificate.Reference(profile, latent)
                      for latent in simulator.latents('rev1', len(profile['parts']))]
        self.assertAlmostEqual(certificate.c1_full_history(oracle, references),
                               oracle.compact_root(), places=9)

    def test_c2_covers_every_d1_mask_on_two_synthetic_profiles(self):
        for profile in certificate.fixtures()[:2]:
            result = certificate.c2(profile, 'd1', certificate.FULL)
            self.assertEqual(result['case_counts']['latents'], 1 + 7 + 6)
            self.assertEqual(result['case_counts']['sequences'], 12 + 144)
            self.assertGreater(result['case_counts']['alive_exact'], 0)
            self.assertGreater(result['case_counts']['state_sufficiency'], 0)
            self.assertEqual(result['max_violation'], 0.0)

    def test_c3_searches_deviations_on_a_synthetic_four_part_profile(self):
        profile = certificate.unit_profile()
        self.assertEqual(len(profile['parts']), 4)
        result = certificate.c3(profile, 'rev1', certificate.UNIT, certificate.FULL)
        self.assertGreater(result['case_counts']['on_path'], 0)
        self.assertGreater(result['case_counts']['off_path'], 0)
        self.assertGreater(result['case_counts']['deviations'], 0)
        self.assertLessEqual(result['max_violation'], dp.TOL)
        self.assertLessEqual(result['max_state_gap'], dp.TOL)
        self.assertEqual(result['c4']['checks'], len(certificate.PROGRAM_ARMS))

    def test_c4_refuses_an_arm_whose_expected_utility_beats_the_dp(self):
        self.assertTrue(certificate.c4_assert('never_verify', 'syn-equal-n500', costs.PRIMARY,
                                              0.4, 0.4 + dp.TOL / 2))
        with self.assertRaises(RuntimeError) as caught:
            certificate.c4_assert('hand_built', {'profile_id': 'syn-equal-n500'}, costs.PRIMARY,
                                  0.9, 0.5)
        self.assertEqual(str(caught.exception),
                         'INV-DP violated: C4/hand_built|syn-equal-n500|k0.30_L3|0.4')
        self.assertTrue(certificate.c4_self_check())

    def test_c5_measures_zero_mutual_information_between_class_and_signature(self):
        for profile in certificate.fixtures()[:2]:
            result = certificate.c5(profile)
            self.assertEqual(result['max_violation'], 0.0)
            self.assertGreater(result['case_counts']['population'], 0)
        self.assertGreater(certificate.mutual_information(
            [('global', 'a'), ('global', 'a'), ('local_visible', 'b')]), 0.9)
        self.assertEqual(certificate.mutual_information(
            [('global', 'a'), ('local_visible', 'a')]), 0.0)

    def test_the_committed_certificate_has_a_passing_status_for_every_part(self):
        data, digest = certificate.require()
        self.assertEqual(data['schema'], certificate.SCHEMA)
        self.assertEqual(data['split'], 'development')
        self.assertEqual(data['status'], 'pass')
        self.assertEqual(len(digest), 64)
        self.assertEqual(data['instances_index_sha256'], certificate.sha(instances.INDEX))
        self.assertEqual(data['code_sha256'],
                         {name: certificate.sha(certificate.REPO / name)
                          for name in certificate.CODE})
        self.assertEqual(json.loads(certificate.OUTPUT.read_text(encoding='utf-8')), data)

    def test_c2_is_wired_into_the_instance_validation(self):
        profile = certificate.fixtures()[0]
        report = instances.validate(profile)
        self.assertEqual(report['env_steps'],
                         len(simulator.latents('rev1', 3)) * len(instances._single_actions(3)))
        self.assertEqual(report['static_observation_sha256'],
                         certificate.c2(profile, 'rev1', certificate.FREEZE_TIME)['static_sha256'])
        with mock.patch.object(instances, 'materialize', _LeakyReport):
            with self.assertRaisesRegex(RuntimeError, 'INV-DP violated: C2/static'):
                certificate.c2(profile, 'rev1', certificate.FREEZE_TIME)
        probe = RuntimeError('INV-DP violated: C2/probe')
        with mock.patch.object(certificate, 'c2', side_effect=probe) as spy:
            with self.assertRaisesRegex(RuntimeError, 'C2/probe'):
                instances.validate(profile)
        self.assertEqual(spy.call_args[0][2], certificate.FREEZE_TIME)


if __name__ == '__main__':
    unittest.main()
