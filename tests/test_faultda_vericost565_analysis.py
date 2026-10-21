import json
import unittest
from pathlib import Path

from faultda_bench.semantic.tasks import ROOT
from faultda_bench.vericost565 import analysis, costs, suite
from faultda_bench.vericost565.canon import canon, compact

PREREG = json.loads((ROOT / 'protocols/vericost_v1_prereg.json').read_text(encoding='utf-8'))
RULES = PREREG['verdict_rules']
# Reproduced during planning from `git show faultda-0.5.60-dev:faultda_bench/stats560/core.py`
# at a63d381; stats560 lives only on the other branch and is never imported here.
STATS560 = {'wilson_8_12': (0.39062208887279953, 0.8618799089087867),
            'wilson_0_16_upper': 0.19360768053443644,
            'wilson_18_18_lower': 0.8241207763533425,
            'holm_a': [0.03, 0.06, 0.06], 'holm_b': [0.003, 0.2, 0.08],
            'mcnemar_2_8': 0.109375}
ARBITRARY = {'kind': 'ratio', 'draws': 1, 'seed': 0, 'level': 0.95, 'point': -42.0,
             'lo': -99.0, 'hi': 99.0, 'clusters': 1, 'degenerate': False, 'role': 'arbitrary'}


def fake_totals(deltas, safe=0.1, cost=-0.2):
    """Four clusters with chosen per-cluster delta U, the shape _totals produces."""
    regime = costs.PRIMARY
    clusters, arms = {}, {}
    for name in ('bf', 'q_only'):
        arms[name] = {'expected_u': 0.0, 'expected_safe': 0.0, 'expected_cost_units': 0.0,
                      'expected_decisions': 0.0, 'fallback_rule_rate': 0.0,
                      'dominated_reads': 0.0, 'profiles': 4}
    for index, delta in enumerate(deltas):
        clusters[(regime, 'c%d' % index)] = {
            'u_star': 4.0, 'profiles': 1,
            'arms': {'bf': {'expected_u': 2.0, 'expected_safe': 0.9,
                            'expected_cost_units': 0.5},
                     'q_only': {'expected_u': 2.0 + delta, 'expected_safe': 0.9 + safe,
                                'expected_cost_units': 0.5 + cost}}}
        arms['bf']['expected_u'] += 2.0
        arms['bf']['expected_safe'] += 0.9
        arms['bf']['expected_cost_units'] += 0.5
        arms['q_only']['expected_u'] += 2.0 + delta
        arms['q_only']['expected_safe'] += 0.9 + safe
        arms['q_only']['expected_cost_units'] += 0.5 + cost
    return {'u_star': {regime: 4.0 * len(deltas)}, 'regimes': {regime: arms},
            'clusters': clusters, 'profiles': {regime: len(deltas)}}


class SignFlipTests(unittest.TestCase):
    def test_the_design_hand_values(self):
        self.assertEqual(analysis.signflip_p([1, 2, 3, 4]), 1 / 16)
        self.assertEqual(analysis.signflip_p([3, -1, 2]), 0.25)
        self.assertEqual(analysis.signflip_p([0, 0]), 1.0)
        self.assertEqual(analysis.signflip_p([-1, -2, -3]), 1.0)

    def test_pooled_with_denominator_n_equals_the_macro_statistic(self):
        for diffs in ([0.3, -0.1], [2.0, 2.0], [-0.5, 0.5]):
            self.assertEqual(analysis.signflip_p(diffs, 'pooled', len(diffs)),
                             analysis.signflip_p(diffs, 'mean'), diffs)
        self.assertEqual(analysis.signflip_p([0.3, -0.1], 'pooled', 7),
                         analysis.signflip_p([0.3, -0.1], 'mean'))

    def test_the_h3_k_at_least_six_correction(self):
        self.assertEqual(analysis.signflip_p([1] * 5 + [0] * 10), 0.03125)
        self.assertFalse(analysis.signflip_gt([1] * 5 + [0] * 10, 0.0, 0.025))
        self.assertEqual(analysis.signflip_p([0.2] * 6 + [0] * 9), 0.015625)
        self.assertTrue(analysis.signflip_gt([0.2] * 6 + [0] * 9, 0.0, 0.025))

    def test_the_test_inversion_helpers(self):
        self.assertEqual(analysis.signflip_p([0.5 - 0.25, 0.4 - 0.25, 0.3 - 0.25]), 1 / 8)
        self.assertFalse(analysis.signflip_gt([0.5, 0.4, 0.3], 0.25, 0.025))
        self.assertEqual(analysis.signflip_p([0.25 - 0.1] * 6), 1 / 64)
        self.assertTrue(analysis.signflip_lt([0.1] * 6, 0.25, 0.025))

    def test_more_than_twenty_clusters_is_refused_and_an_empty_vector_too(self):
        with self.assertRaises(ValueError) as refused:
            analysis.signflip_p([0.1] * 21)
        self.assertIn('limited to 20 clusters', str(refused.exception))
        with self.assertRaises(ValueError):
            analysis.signflip_p([])
        self.assertEqual(analysis.signflip_p([0.1] * 20), 2 ** -20)


class ExactTestTests(unittest.TestCase):
    def test_mcnemar_hand_values(self):
        self.assertEqual(analysis.mcnemar_exact(2, 8), 0.109375)
        self.assertEqual(analysis.mcnemar_exact(0, 6), 0.03125)
        self.assertEqual(analysis.mcnemar_exact(5, 5), 1.0)
        self.assertEqual(analysis.mcnemar_exact(1, 12), 0.00341796875)
        self.assertEqual(analysis.mcnemar_exact(0, 0), 1.0)

    def test_icc_hand_values(self):
        self.assertEqual(analysis.icc_anova([[1, 1, 1, 1], [0, 0, 0, 0]]), 1.0)
        self.assertEqual(analysis.icc_anova([[1, 0, 1, 0], [1, 0, 1, 0]]), 0)

    def test_the_exact_cluster_binomial_tail(self):
        self.assertEqual(analysis.cluster_binomial_p(0, 4), 1.0)
        self.assertEqual(analysis.cluster_binomial_p(4, 4), 0.0625)
        self.assertEqual(analysis.cluster_binomial_p(3, 4), 0.3125)

    def test_the_logistic_slope_is_zero_on_a_balanced_design(self):
        fit = analysis.logistic_slope([-1, -1, 1, 1], [0, 1, 0, 1])
        self.assertEqual((fit['intercept'], fit['slope']), (0.0, 0.0))
        self.assertTrue(fit['converged'])
        rising = analysis.logistic_slope([0, 1, 2, 3, 4, 5], [0, 0, 0, 1, 1, 1])
        self.assertGreater(rising['slope'], 0.0)
        flat = analysis.logistic_slope([0, 1, 2], [1, 1, 1])
        self.assertTrue(flat['degenerate'])
        self.assertIsNone(flat['slope'])

    def test_the_minimum_detectable_effect_reproduces_the_amendment(self):
        power = analysis.dz_mde(4, RULES['alpha_O2'], 0.8, 0.595368090067,
                                RULES['power']['dz_formula'])
        self.assertEqual(canon(power['t_quantiles']), [2.3533634348, 0.978472312363])
        self.assertEqual(canon(power['dz']), 1.66591787358)
        self.assertEqual(canon(power['mde']), 0.991834342603)
        with self.assertRaises(ValueError):
            analysis.dz_mde(4, 0.05, 0.8, None, 'a different formula')


class Stats560CrossCheckTests(unittest.TestCase):
    """Cross-check against the 0.5.60 stats560 constants, compared after canon().

    The cluster bootstrap is deliberately NOT cross-checked: stats560 resamples with the numpy
    random generator, while this module must stay stdlib-only (plan R12) and uses
    random.Random index resampling, so the two draw different samples by construction.
    """

    def test_wilson_matches_stats560(self):
        self.assertEqual(canon(list(analysis.wilson(8, 12))), canon(list(STATS560['wilson_8_12'])))
        self.assertEqual(canon(analysis.wilson(0, 16)[1]), canon(STATS560['wilson_0_16_upper']))
        self.assertEqual(canon(analysis.wilson(18, 18)[0]),
                         canon(STATS560['wilson_18_18_lower']))
        self.assertEqual(analysis.wilson(0, 16)[0], 0.0)
        self.assertEqual(analysis.wilson(18, 18)[1], 1.0)

    def test_holm_matches_stats560(self):
        self.assertEqual(canon(analysis.holm([0.01, 0.04, 0.03])), canon(STATS560['holm_a']))
        self.assertEqual(canon(analysis.holm([0.001, 0.2, 0.04])), canon(STATS560['holm_b']))
        self.assertEqual(analysis.holm([]), [])

    def test_mcnemar_matches_stats560(self):
        self.assertEqual(canon(analysis.mcnemar_exact(2, 8)), canon(STATS560['mcnemar_2_8']))


class BootstrapTests(unittest.TestCase):
    def setUp(self):
        self.draws = RULES['bootstrap']['draws']
        self.seed = RULES['bootstrap']['seed']

    def test_identical_clusters_give_a_degenerate_interval(self):
        result = analysis.cluster_bootstrap([(1.0, 2.0)] * 4, 'ratio', self.draws, self.seed)
        self.assertEqual((result['lo'], result['point'], result['hi']), (0.5, 0.5, 0.5))
        self.assertIs(result['degenerate'], True)

    def test_the_fixed_seed_repeats_and_a_different_seed_draws_differently(self):
        rows = [(value / 10, 1.0 + value) for value in range(1, 9)]
        first = analysis.cluster_bootstrap(rows, 'ratio', 1000, self.seed)
        again = analysis.cluster_bootstrap(rows, 'ratio', 1000, self.seed)
        self.assertEqual(compact(first), compact(again))
        self.assertLessEqual(first['lo'], first['point'])
        self.assertLessEqual(first['point'], first['hi'])
        other = analysis.cluster_bootstrap(rows, 'ratio', 1000, self.seed + 1)
        self.assertEqual(other['point'], first['point'])
        self.assertNotEqual((other['lo'], other['hi']), (first['lo'], first['hi']))

    def test_the_macro_and_ratio_statistics_are_distinct_and_fixed_inside_resamples(self):
        """level 0 reads the median draw, which is the mixed resample of the two clusters."""
        rows = [(1.0, 1.0), (1.0, 9.0)]
        ratio = analysis.cluster_bootstrap(rows, 'ratio', 500, self.seed)
        macro = analysis.cluster_bootstrap(rows, 'macro', 500, self.seed)
        self.assertEqual(ratio['point'], 0.2)
        self.assertEqual(macro['point'], (1.0 + 1 / 9) / 2)
        self.assertEqual(analysis.cluster_bootstrap(rows, 'ratio', 500, self.seed, 0.0)['lo'], 0.2)
        self.assertEqual(analysis.cluster_bootstrap(rows, 'macro', 500, self.seed, 0.0)['lo'],
                         (1.0 + 1 / 9) / 2)
        self.assertEqual(ratio['kind'], 'ratio')
        self.assertEqual(macro['kind'], 'macro')
        # Every resample of a one-cluster set is that cluster, so the bounds equal the point.
        for kind in ('ratio', 'macro'):
            single = analysis.cluster_bootstrap([(0.4, 2.0)], kind, 50, self.seed)
            self.assertEqual((single['lo'], single['hi']), (0.2, 0.2))
        with self.assertRaises(ValueError):
            analysis.cluster_bootstrap(rows, 'median', 10, self.seed)

    def test_the_percentile_helper_interpolates_linearly(self):
        self.assertEqual(analysis.percentile([0.0, 1.0], 0.5), 0.5)
        self.assertAlmostEqual(analysis.percentile([0.0, 1.0, 2.0, 3.0], 0.025), 0.075, places=15)
        self.assertEqual(analysis.percentile([5.0], 0.975), 5.0)


class VerdictTests(unittest.TestCase):
    def test_the_pre_registered_o2_rule(self):
        base = {'delta_u': 0.4, 'dominated': False, 'signflip_p': 0.01}
        self.assertEqual(analysis.o2_verdict(base, RULES, False, '')['verdict'], 'SUPPORTED')
        self.assertEqual(analysis.o2_verdict(dict(base, signflip_p=0.0625), RULES, True,
                                             '')['verdict'], 'INCONCLUSIVE')
        self.assertEqual(analysis.o2_verdict(dict(base, delta_u=-0.1), RULES, True,
                                             '')['verdict'], 'FALSIFIED')
        self.assertEqual(analysis.o2_verdict(dict(base, delta_u=0.0), RULES, True,
                                             '')['verdict'], 'FALSIFIED')
        self.assertEqual(analysis.o2_verdict(dict(base, dominated=True), RULES, True,
                                             '')['verdict'], 'FALSIFIED')

    def test_dominance_is_decided_at_twelve_digits(self):
        better = {'expected_safe': 0.9, 'expected_cost_units': 0.4}
        worse = {'expected_safe': 0.8, 'expected_cost_units': 0.4}
        self.assertTrue(analysis.dominated(worse, better))
        self.assertFalse(analysis.dominated(better, worse))
        self.assertFalse(analysis.dominated(better, dict(better)))
        tiny = {'expected_safe': 0.9 + 1e-15, 'expected_cost_units': 0.4}
        self.assertFalse(analysis.dominated(better, tiny))

    def test_a_falsified_point_estimate_is_reported_with_the_under_power_reason(self):
        block = analysis.o2_block(fake_totals([-0.5, -0.2, -0.3, -0.4]), costs.PRIMARY, 'q_only',
                                  RULES, 0.0625)
        self.assertEqual(block['verdict'], 'FALSIFIED')
        self.assertEqual(block['signflip_p'], 1.0)
        self.assertIs(block['under_powered'], True)
        self.assertEqual(block['clusters_with_positive_delta'], 0)
        self.assertIn('0.0625', block['reason'])
        self.assertIn('no p value can clear alpha', block['reason'])

    def test_replacing_every_bootstrap_bound_leaves_the_verdicts_unchanged(self):
        """Plan D9: no verdict condition may read a bootstrap bound."""
        totals = fake_totals([0.5, -0.2, 0.3, 0.4])
        honest = analysis.o2_block(totals, costs.PRIMARY, 'q_only', RULES, 0.0625)
        original = analysis.cluster_bootstrap
        analysis.cluster_bootstrap = lambda *args, **extra: dict(ARBITRARY)
        try:
            patched = analysis.o2_block(totals, costs.PRIMARY, 'q_only', RULES, 0.0625)
        finally:
            analysis.cluster_bootstrap = original
        self.assertNotEqual(honest['bootstrap_ci'], patched['bootstrap_ci'])
        for key in sorted(honest):
            if key != 'bootstrap_ci':
                self.assertEqual(honest[key], patched[key], key)
        self.assertEqual(honest['verdict'], 'INCONCLUSIVE')


def without_bootstrap(value):
    if isinstance(value, dict):
        return {key: without_bootstrap(item) for key, item in value.items()
                if 'bootstrap' not in key}
    if isinstance(value, list):
        return [without_bootstrap(item) for item in value]
    return value


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not suite.OFFLINE.exists():
            raise unittest.SkipTest('offline_eval.json is produced by plan item 17')
        cls.data = analysis.report()

    def test_the_report_carries_the_under_power_record_and_the_zero_cost_scope(self):
        self.assertEqual(self.data['schema'], analysis.SCHEMA)
        self.assertEqual(self.data['n_clusters'], 4)
        self.assertEqual(self.data['min_attainable_signflip_p'], 0.0625)
        self.assertEqual(self.data['split'], 'development')
        self.assertIs(self.data['seen_cluster'], True)
        self.assertIs(self.data['independent_test'], False)
        self.assertEqual(self.data['generalization_claim'], 'none')
        self.assertEqual(self.data['api_calls'], 0)
        self.assertEqual(self.data['cny_spent'], '0.000000')
        for name in ('H1', 'H2', 'H3'):
            self.assertEqual(self.data['hypotheses_live'][name]['status'], 'pending_live')
        for key in ('new_sources', 'heldout_split', 'pilot', 'a', 'b', 'p1', 'p2',
                    'provider_path', 'direction_b', 'hybrid_arm', 'hypotheses_live'):
            self.assertIn(key, self.data['not_run'])

    def test_o1_o2_and_o3_are_complete(self):
        for model in ('rev1', 'd1'):
            sets = self.data['O1']['models'][model]['sets']
            self.assertEqual(sorted(sets), ['all', 'dev_seen', 'dev_syn'])
            for item in sets.values():
                self.assertEqual(len(item['regimes']), 8)
        self.assertEqual(self.data['O2']['arm'], 'q_only')
        self.assertEqual(sorted(self.data['O2_exploratory']), ['linucb', 'thompson'])
        for arm, block in self.data['O2_exploratory'].items():
            self.assertEqual(block['label'], 'exploratory')
        self.assertEqual(sorted(self.data['O3']['regret_by_arm']), sorted(costs.REGIME_IDS))
        self.assertEqual(len(self.data['O3']['frontier']), 8 * len(suite.ARMS))
        self.assertEqual(sorted(self.data['counts_by_arm']), sorted(suite.ARMS))

    def test_the_cluster_sign_flip_input_agrees_with_the_independent_learned_evaluation(self):
        measured = self.data['O2']['delta_u_by_cluster']
        cross = self.data['O2']['cross_check_learned_eval']['delta_u_by_cluster']
        for cluster, value in measured.items():
            self.assertAlmostEqual(value, cross[cluster], places=9, msg=cluster)

    def test_every_verdict_survives_arbitrary_bootstrap_bounds(self):
        original = analysis.cluster_bootstrap
        analysis.cluster_bootstrap = lambda *args, **extra: dict(ARBITRARY)
        try:
            patched = analysis.report()
        finally:
            analysis.cluster_bootstrap = original
        self.assertEqual(compact(without_bootstrap(self.data)),
                         compact(without_bootstrap(patched)))

    def test_the_committed_analysis_matches_a_rebuild(self):
        if not analysis.OUTPUT.exists():
            self.skipTest('analysis.json is produced by plan item 19')
        committed = json.loads(analysis.OUTPUT.read_text(encoding='utf-8'))
        self.assertEqual(compact(committed), compact(canon(self.data)))


if __name__ == '__main__':
    unittest.main()
