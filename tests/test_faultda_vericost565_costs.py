import statistics
import unittest
from decimal import Decimal

from faultda_bench.vericost565 import costs, instances


class CostModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = instances.synthetic_profiles()
        reference = costs.b_ref(cls.profiles, 'synthetic')
        for profile in cls.profiles:
            profile['b_ref'] = reference
        cls.by_id = {profile['profile_id']: profile for profile in cls.profiles}

    def test_eight_regimes_with_the_fixed_primary(self):
        self.assertEqual(costs.REGIME_IDS,
                         ('k0.03_L1', 'k0.03_L3', 'k0.10_L1', 'k0.10_L3',
                          'k0.30_L1', 'k0.30_L3', 'k1.00_L1', 'k1.00_L3'))
        self.assertEqual(costs.PRIMARY, 'k0.30_L3')
        self.assertEqual([item['regime_id'] for item in costs.REGIMES if item['primary']],
                         ['k0.30_L3'])
        with self.assertRaises(ValueError):
            costs.regime('k0.30_L2')

    def test_row_serialization_counts_missing_values_in_rows_and_bytes(self):
        self.assertEqual(costs.row_bytes(('12', 'abc', Decimal('1.50'))), len('12,abc,1.5\n'))
        self.assertEqual(costs.row_bytes(('7', 'k', None)), len('7,k,\n'))
        rows = (('0', 'a', Decimal('1')), ('1', 'a', None))
        self.assertEqual(costs.part_bytes(rows), len('0,a,1\n') + len('1,a,\n'))

    def test_read_rows_is_billed_the_full_part_scan_at_any_limit(self):
        profile = self.by_id['syn-skewed-n5000']
        for part in range(len(profile['parts'])):
            self.assertEqual(costs.billed_bytes(profile, 'read_rows', part),
                             profile['parts'][part]['bytes'])
            self.assertEqual(costs.cost(profile, 'k0.30_L3', 'read_rows', part),
                             costs.cost(profile, 'k0.30_L3', 'spot_check', part))
        self.assertEqual(costs.billed_bytes(profile, 'consistency_check'),
                         costs.CC_RECORD_BYTES * len(profile['parts']))
        with self.assertRaises(ValueError):
            costs.billed_bytes(profile, 'read_rows', len(profile['parts']))

    def test_full_recompute_cost_scales_with_data_size(self):
        for shape in ('equal', 'skewed'):
            small = costs.cost(self.by_id[f'syn-{shape}-n500'], 'k0.30_L3', 'full_recompute')
            middle = costs.cost(self.by_id[f'syn-{shape}-n5000'], 'k0.30_L3', 'full_recompute')
            large = costs.cost(self.by_id[f'syn-{shape}-n50000'], 'k0.30_L3', 'full_recompute')
            self.assertAlmostEqual(small, 0.03, delta=0.01)
            self.assertAlmostEqual(middle, 0.30, delta=0.05)
            self.assertAlmostEqual(large, 3.00, delta=0.5)
            self.assertAlmostEqual(middle / small, 10, delta=1.5)
            self.assertAlmostEqual(large / middle, 10, delta=1.5)

    def test_cost_is_linear_in_kappa_and_independent_of_the_loss(self):
        profile = self.by_id['syn-equal-n5000']
        base = costs.cost(profile, 'k0.03_L1', 'full_recompute')
        self.assertAlmostEqual(costs.cost(profile, 'k0.30_L1', 'full_recompute'), base * 10, places=9)
        self.assertEqual(costs.cost(profile, 'k0.30_L1', 'full_recompute'),
                         costs.cost(profile, 'k0.30_L3', 'full_recompute'))

    def test_utility_table_at_every_regime(self):
        for item in costs.REGIMES:
            name = item['regime_id']
            self.assertEqual(costs.utility({'safe_complete': True}, 0.0, name), 1.0)
            self.assertEqual(costs.utility({'false_completion': True}, 0.0, name), -item['L'])
            self.assertEqual(costs.utility({'forbidden_effect': True}, 0.0, name), -item['L'])
            self.assertEqual(costs.utility({}, 0.0, name), 0.0)
            self.assertEqual(costs.utility({}, [0.1, 0.2], name), -0.30000000000000004)

    def test_loss_is_applied_at_most_once(self):
        both = {'false_completion': True, 'forbidden_effect': True}
        self.assertEqual(costs.utility(both, 0.0, 'k0.30_L3'), -3)
        self.assertEqual(costs.utility({'safe_complete': True, 'forbidden_effect': True}, 0.0,
                                       'k0.30_L3'), 1.0 - 3)

    def test_admissibility_reads_its_threshold_from_the_prereg(self):
        prereg = {'verdict_rules': {'admissibility': 0.10}}
        self.assertTrue(costs.admissible(0.10, prereg))
        self.assertFalse(costs.admissible(0.0999, prereg))
        self.assertFalse(costs.admissible(0.10, {'verdict_rules': {'admissibility': 0.5}}))

    def test_b_ref_uses_the_documented_rule_per_instance_set(self):
        seen, _ = instances.seen_profiles()
        self.assertAlmostEqual(costs.b_ref(self.profiles, 'synthetic'),
                               costs.REFERENCE_ROWS * 14.0502, delta=0.5)
        self.assertEqual(costs.b_ref(seen, 'seen_development'),
                         statistics.median([costs.profile_bytes(p) for p in seen]))
        with self.assertRaises(ValueError):
            costs.b_ref(seen, 'synthetic')


if __name__ == '__main__':
    unittest.main()
