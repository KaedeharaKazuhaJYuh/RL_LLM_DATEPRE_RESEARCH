import hashlib
import json
import unittest

from faultda_bench.semantic.tasks import REPO
from faultda_bench import vericost566 as v566

CHANGELOG = REPO / 'CHANGELOG.md'
README = REPO / 'README.md'
PACKAGE_README = REPO / 'faultda_bench/README.md'
ASSESSMENT = REPO / 'faultda_bench/docs/CROSS_BRANCH_ASSESSMENT_2026_10_27.md'
NOVELTY = REPO / 'faultda_bench/docs/NOVELTY_AUDIT_2026_10_27.md'


class EvidenceTests(unittest.TestCase):
    """The 0.5.66 claims must be readable off the committed artifacts, not just the prose."""

    @classmethod
    def setUpClass(cls):
        cls.data = v566.load()
        cls.table = v566.regret(cls.data)

    def test_the_summary_is_the_frozen_dev_seen_run_and_spent_nothing(self):
        self.assertEqual(self.data['version'], v566.VERSION)
        self.assertEqual(self.data['instance_set'], 'dev_seen')
        self.assertEqual(self.data['profiles'], 24)
        self.assertEqual(self.data['regimes'], 8)
        self.assertEqual(self.data['arms'], 13)
        self.assertEqual(self.data['api_calls'], 0)
        self.assertEqual(self.data['cny_spent'], 0.0)

    def test_the_summary_matches_the_full_run_row_for_row(self):
        detail = v566.detail()
        self.assertEqual(len(detail['expected']), self.data['certificate_c4_assertions'])
        self.assertEqual(len(detail['expected']), 2496)
        self.assertEqual(len(detail['optimum']), 192)
        self.assertEqual(len(detail['realized']), 7488)

    def test_the_best_fixed_rule_regret_grows_by_two_orders_across_the_price_ladder(self):
        ladder = dict(v566.ladder(self.data))
        self.assertAlmostEqual(ladder['k0.03_L3'], 0.0006, places=3)
        self.assertAlmostEqual(ladder['k0.10_L3'], 0.0022, places=3)
        self.assertAlmostEqual(ladder['k0.30_L3'], 0.0100, places=3)
        self.assertAlmostEqual(ladder['k1.00_L3'], 0.1801, places=3)
        ordered = [ladder[regime] for regime in
                   ('k0.03_L1', 'k0.10_L1', 'k0.30_L1', 'k1.00_L1')]
        self.assertEqual(ordered, sorted(ordered))
        self.assertGreater(v566.headroom_ratio(self.data), 250)

    def test_no_learned_arm_closes_the_gap_at_the_only_regime_with_headroom(self):
        block = self.table['k1.00_L3']
        for arm in v566.LEARNED_ARMS:
            self.assertGreaterEqual(block[arm], block['bf'] - 1e-9, arm)
        self.assertAlmostEqual(block['thompson'], block['bf'], places=6)

    def test_the_richer_fixed_family_is_never_worse_than_the_reported_minimum(self):
        for regime, block in self.table.items():
            self.assertLessEqual(block['F_hist_plus'], block['bf'] + 1e-9, regime)

    def test_the_learned_arm_is_four_times_more_price_elastic_without_gaining_utility(self):
        for loss in (1, 3):
            best = v566.elasticity('bf', loss, data=self.data)
            learned = v566.elasticity('q_only', loss, data=self.data)
            self.assertLess(learned, 3 * best, loss)
            self.assertLess(learned, -1.0, loss)
            self.assertGreater(best, -0.5, loss)
        low = self.table['k0.10_L3']['q_only']
        high = self.table['k1.00_L3']['q_only']
        self.assertLess(abs(high - low), 0.01)


class RecordTests(unittest.TestCase):
    """The release record must stay reachable, and must not claim more than the evidence."""

    def test_the_report_is_committed_and_states_its_own_limits(self):
        text = v566.RELEASE.read_text(encoding='utf-8')
        self.assertIn('0.5.66-dev', text)
        self.assertIn('0.1801', text)
        self.assertIn('0.1636', text)
        self.assertIn('外部基准', text)
        self.assertIn('作废', text)

    def test_the_changelog_entry_keeps_its_bullets_and_the_zero_spend(self):
        lines = CHANGELOG.read_text(encoding='utf-8').splitlines()
        starts = [index for index, line in enumerate(lines)
                  if line.startswith('# FaultDA-Bench %s — ' % v566.VERSION)]
        self.assertEqual(len(starts), 1, starts)
        head = starts[0]
        bullets = [line for line in lines[head:head + 10] if line.startswith('- ')]
        self.assertEqual(len(bullets), 6)
        self.assertTrue(any('0 API calls, ¥0' in line for line in bullets))

    def test_the_readmes_point_at_this_release_and_keep_the_inherited_line(self):
        root = README.read_text(encoding='utf-8').splitlines()
        self.assertEqual(root[0], '# FaultDA-Bench')
        self.assertIn(v566.VERSION, root[6])
        self.assertEqual(root[7], '<!-- inherited-release: V5.0.15-beta.2 -->')
        self.assertIn('faultda_bench/reports/RELEASE_0566.md', README.read_text(encoding='utf-8'))
        package = PACKAGE_README.read_text(encoding='utf-8')
        self.assertIn(v566.VERSION, package)
        self.assertIn('RELEASE_0566.md', package)

    def test_the_two_documents_that_justify_closing_the_line_are_committed(self):
        assessment = ASSESSMENT.read_text(encoding='utf-8')
        self.assertIn('2,100', assessment)
        self.assertIn('跑在别人维护的基准上的次数是 0', assessment)
        novelty = NOVELTY.read_text(encoding='utf-8')
        for identifier in ('2610.06191', '2610.07753', '2609.17848', '2606.26027',
                           '2610.32555'):
            self.assertIn(identifier, novelty)

    def test_every_regime_row_carries_all_thirteen_arms_and_points_at_its_source(self):
        data = v566.load()
        self.assertEqual(data['source'], 'dev_seen_all_regimes.json')
        for row in v566.rows(data):
            self.assertEqual(len(row['arms']), 13, row['regime_id'])
            for name, block in row['arms'].items():
                self.assertGreaterEqual(block['regret_norm'], 0.0, (row['regime_id'], name))
                self.assertLess(block['regret_norm'], 10.0, (row['regime_id'], name))
        self.assertTrue(v566.DETAIL.exists())


class FrozenCatalogTests(unittest.TestCase):
    """A release bump edits one pinned file, so the drift table has to record it."""

    PINNED = 'tests/test_faultda_vericost565_release.py'

    def test_the_registry_lists_this_release_test_module(self):
        path = REPO / 'faultda_bench/protocols/current_evidence_v1.json'
        registry = json.loads(path.read_text(encoding='utf-8'))
        self.assertIn('tests.test_faultda_vericost566_release', registry['test_modules'])

    def test_the_pinned_release_test_carries_a_current_superseded_entry(self):
        from faultda_bench import ci565
        record = ci565.migration()['superseded'][self.PINNED]
        actual = hashlib.sha256((REPO / self.PINNED).read_bytes()).hexdigest()
        self.assertEqual(record['corrected_sha256'], actual)
        catalog = json.loads((REPO / 'faultda_bench/protocols/acceptance_v48.json')
                             .read_text(encoding='utf-8'))
        # The archived original still has to be the frozen one, so the drift stays provable.
        self.assertEqual(record['original_sha256'], catalog['files'][self.PINNED])


if __name__ == '__main__':
    unittest.main()
