import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from faultda_bench.stats560 import VERSION
from faultda_bench.stats560 import audit, core

ROOT = audit.ROOT
COMMITTED = ROOT / 'faultda_bench/reports/stats560/summary.json'


class StatisticsTests(unittest.TestCase):
    def test_wilson_reference_values(self):
        cases = {(6, 12): (0.2537815976337061, 0.7462184023662939),
                 (0, 12): (0.0, 0.2424940066552408),
                 (12, 12): (0.7575059933447593, 1.0),
                 (4, 12): (0.1381200910912132, 0.6093779111272004),
                 (48, 144): (0.26155286452605253, 0.41377501452162635)}
        for (k, n), (lo, hi) in cases.items():
            got = core.wilson_interval(k, n)
            self.assertAlmostEqual(lo, got[0], places=12)
            self.assertAlmostEqual(hi, got[1], places=12)
        self.assertAlmostEqual(1.9599639845400536, core.Z95, places=12)

    def test_wilson_matches_closed_form(self):
        k, n, z = 6, 12, core.Z95
        p = k / n
        centre = (p + z * z / (2 * n)) / (1 + z * z / n)
        half = z / (1 + z * z / n) * (p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5
        self.assertAlmostEqual(centre - half, core.wilson_interval(k, n)[0], places=12)

    def test_wilson_rejects_invalid_input(self):
        for args in ((1, 0), (13, 12), (-1, 12), (True, 12), (1.0, 12)):
            with self.assertRaises(ValueError):
                core.wilson_interval(*args)

    def test_exact_sign_and_mcnemar_reference_values(self):
        cases = {(6, 0): 0.03125, (5, 0): 0.0625, (1, 5): 0.21875, (2, 8): 0.109375,
                 (10, 3): 0.09228515625, (0, 0): 1.0, (48, 0): 7.105427357601002e-15,
                 (24, 0): 1.1920928955078125e-07}
        for (b, c), p in cases.items():
            self.assertAlmostEqual(p, core.exact_sign_test(b, c), places=15)
            self.assertEqual(core.exact_sign_test(b, c), core.exact_sign_test(c, b))
        a = [True] * 6 + [False] * 6
        b = [False] * 12
        result = core.mcnemar_exact(a, b)
        self.assertEqual((6, 0, 0, 6, 6), (result['a_only'], result['b_only'], result['both'],
                                           result['neither'], result['discordant']))
        self.assertEqual(0.03125, result['p_value'])
        with self.assertRaises(ValueError):
            core.mcnemar_exact([True], [True, False])
        with self.assertRaises(ValueError):
            core.mcnemar_exact([1], [0])

    def test_holm_reference_and_ordering(self):
        raw = [0.01, 0.04, 0.03, 0.005]
        adjusted = core.holm_bonferroni(raw)
        for want, got in zip([0.03, 0.06, 0.06, 0.02], adjusted):
            self.assertAlmostEqual(want, got, places=15)
        self.assertTrue(all(a >= r for a, r in zip(adjusted, raw)))
        ordered = [adjusted[i] for i in sorted(range(len(raw)), key=raw.__getitem__)]
        self.assertEqual(sorted(ordered), ordered)
        self.assertEqual([1.0, 1.0], core.holm_bonferroni([0.6, 0.9]))
        self.assertEqual([], core.holm_bonferroni([]))

    def test_power_and_minimum_detectable_effect(self):
        self.assertEqual(6, core.min_discordant_for_significance(0.05))
        self.assertEqual(1.0, core.sign_test_power(6, 1.0))
        self.assertEqual(0.0, core.sign_test_power(5, 1.0))
        self.assertEqual(0.0, core.sign_test_power(0, 0.8))
        self.assertAlmostEqual(0.571871187941724, core.mde_two_proportions(12), places=9)
        self.assertAlmostEqual(0.23346543484274732, core.mde_two_proportions(72), places=9)

    def test_bootstrap_is_deterministic_given_seed(self):
        values = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1]
        first = core.bootstrap_replicates(values, n_resamples=500, seed=7)
        self.assertTrue(np.array_equal(first, core.bootstrap_replicates(values, n_resamples=500, seed=7)))
        self.assertFalse(np.array_equal(first, core.bootstrap_replicates(values, n_resamples=500, seed=8)))
        ci = core.bootstrap_ci(values, n_resamples=500, seed=7)
        self.assertEqual(ci, core.bootstrap_ci(values, n_resamples=500, seed=7))
        self.assertLessEqual(ci['low'], ci['estimate'])
        self.assertLessEqual(ci['estimate'], ci['high'])
        self.assertEqual('percentile_bootstrap', ci['method'])

    def test_cluster_bootstrap_resamples_whole_clusters(self):
        values = [1, 1, 1, 1, 0, 0, 0, 0]
        clusters = ['a'] * 4 + ['b'] * 4
        reps = core.cluster_bootstrap_replicates(values, clusters, n_resamples=500, seed=1)
        self.assertTrue(set(np.unique(reps)) <= {0.0, 0.5, 1.0})
        self.assertGreaterEqual(len(np.unique(reps)), 2)
        iid = core.bootstrap_replicates(values, n_resamples=500, seed=1)
        self.assertTrue(set(np.unique(iid)) - {0.0, 0.5, 1.0})
        order = [7, 0, 5, 2, 4, 1, 6, 3]
        shuffled = core.cluster_bootstrap_replicates(
            [values[i] for i in order], [clusters[i] for i in order], n_resamples=500, seed=1)
        self.assertTrue(np.array_equal(reps, shuffled))
        ci = core.cluster_bootstrap_ci(values, clusters, n_resamples=500, seed=1)
        self.assertEqual(2, ci['n_clusters'])
        self.assertEqual('cluster_percentile_bootstrap', ci['method'])

    def test_cluster_bootstrap_rejects_single_cluster_and_mismatch(self):
        with self.assertRaises(ValueError):
            core.cluster_bootstrap_ci([1, 0], ['a', 'a'])
        with self.assertRaises(ValueError):
            core.cluster_bootstrap_ci([1, 0], ['a'])


class Stats560AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary = audit.build_summary(n_resamples=200)

    def _copy_root(self, folder):
        tmp = Path(folder)
        for name in (audit.CATALOG_NAME, audit.MANIFEST_NAME, audit.PERFORMANCE_NAME) + audit.INPUTS:
            target = tmp / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        return tmp

    def _frozen_hashes(self):
        names = sorted(audit._frozen_names(ROOT))
        return {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in names}

    def test_summary_is_offline_deterministic_and_bounded(self):
        s = self.summary
        self.assertEqual(s, audit.build_summary(n_resamples=200))
        self.assertEqual((VERSION, 'HOLD', 0, 0, False),
                         (s['version'], s['scientific_gate'], s['new_model_executions'],
                          s['new_provider_requests'], s['rescored']))
        self.assertEqual(['C1', 'C2', 'C3', 'C4', 'C5'], [c['id'] for c in s['comparisons']])
        for c in s['comparisons']:
            self.assertIs(False, c['evidence_boundary']['independent_test'])
            self.assertIs(True, c['evidence_boundary']['seen_cluster'])
        self.assertEqual(['U1', 'U2', 'U3', 'U4', 'U5'], [u['id'] for u in s['unavailable']])

    def test_paired_tests_match_frozen_counts(self):
        tests = self.summary['paired_tests']
        self.assertEqual(15, self.summary['holm_family_size'])
        self.assertEqual(15, len(tests))
        c1, c2 = tests[0], tests[1]
        self.assertEqual((6, 0, 0.03125), (c1['a_only'], c1['b_only'], c1['p_value']))
        self.assertEqual((0, 0, 1.0), (c2['a_only'], c2['b_only'], c2['p_value']))
        for t in tests:
            self.assertGreaterEqual(t['holm_adjusted_p'], t['p_value'])
        c4 = [t for t in tests if t['comparison'] == 'C4'
              and t['metric'] == 'supported_correct_termination']
        self.assertEqual({(48, 0), (24, 0)}, {(t['a_only'], t['b_only']) for t in c4})
        c5 = self.summary['comparisons'][4]['arms']
        self.assertEqual([(144, 144), (48, 144)], [(a['successes'], a['n']) for a in c5])

    def test_refuses_changed_frozen_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp = self._copy_root(folder)
            audit.verified_inputs(tmp)
            target = tmp / audit.ACCOUNTING
            data = bytearray(target.read_bytes())
            data[10] ^= 1
            target.write_bytes(bytes(data))
            with self.assertRaisesRegex(ValueError, 'frozen bytes changed'):
                audit.verified_inputs(tmp)

    def test_refuses_manifest_and_catalog_changes(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp = self._copy_root(folder)
            path = tmp / audit.MANIFEST_NAME
            manifest = json.loads(path.read_text(encoding='utf-8'))
            manifest['inputs'][audit.CLARITY] = '0' * 64
            path.write_text(json.dumps(manifest), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'manifest/catalog hash mismatch'):
                audit.verified_inputs(tmp)
        with tempfile.TemporaryDirectory() as folder:
            tmp = self._copy_root(folder)
            with (tmp / audit.CATALOG_NAME).open('ab') as stream:
                stream.write(b' ')
            with self.assertRaisesRegex(ValueError, 'base catalog'):
                audit.verified_inputs(tmp)

    def test_writer_does_not_touch_frozen_files(self):
        before = self._frozen_hashes()
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'out.json'
            json_path, md_path = audit.write_outputs(self.summary, out)
            self.assertEqual(self.summary, json.loads(json_path.read_text(encoding='utf-8')))
            self.assertTrue(md_path.read_text(encoding='utf-8').startswith('# 0.5.60'))
            with self.assertRaises(FileExistsError):
                audit.write_outputs(self.summary, out)
        for target in (ROOT / audit.TERM555, ROOT / 'faultda_bench/protocols/x.json',
                       ROOT / 'docs/x.json'):
            existed = target.exists()
            with self.assertRaises(ValueError):
                audit.write_outputs(self.summary, target)
            self.assertEqual(existed, target.exists())
            self.assertFalse(target.with_suffix('.md').exists())
        self.assertEqual(before, self._frozen_hashes())

    def test_committed_summary_matches_fresh_run(self):
        if not COMMITTED.exists():
            self.skipTest('committed stats560 summary not generated yet')
        summary = audit.build_summary()
        self.assertEqual(json.loads(COMMITTED.read_text(encoding='utf-8')), summary)
        self.assertEqual(COMMITTED.with_suffix('.md').read_text(encoding='utf-8'),
                         audit.render_markdown(summary))


if __name__ == '__main__':
    unittest.main()
