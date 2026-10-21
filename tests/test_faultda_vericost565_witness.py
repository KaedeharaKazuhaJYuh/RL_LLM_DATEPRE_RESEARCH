from unittest.mock import patch
import json
import tempfile
import unittest
from pathlib import Path

from faultda_bench.vericost565 import certificate, costs, policies, witness
from faultda_bench.vericost565.canon import dumps

FIXTURE = witness.FIXTURE
PREREG = json.loads(witness.PREREG.read_text(encoding='utf-8'))
LEARNED_KEYS = ('q_only', 'thompson', 'linucb', 'q', 'learned', 'bf')


def rows(hard_stop, admissible_primary):
    """Eight synthetic regime rows exercising one (hard_stop, primary admissible) combination."""
    out = []
    for item in costs.REGIMES:
        primary = item['primary']
        u_star = 0.05 if primary and not admissible_primary else 0.70
        out.append({'regime_id': item['regime_id'], 'primary': primary, 'profiles': 6,
                    'expected_u_star': u_star,
                    'admissible': costs.admissible(u_star, PREREG),
                    'min_fixed_r': 0.02 if hard_stop else 0.40})
    return out


class Gate0DecisionTests(unittest.TestCase):
    def test_the_live_round_rule_is_decided_for_all_four_combinations(self):
        expected = {(True, True): (True, False, True, 'measurement'),
                    (True, False): (True, True, True, 'measurement'),
                    (False, True): (False, False, False, 'mechanism'),
                    (False, False): (False, True, True, 'measurement')}
        for (hard_stop, admissible), want in expected.items():
            block = witness.decision(rows(hard_stop, admissible), PREREG, 'rev1')
            self.assertEqual((block['hard_stop'], block['primary_inadmissible'], block['trigger'],
                              block['scope']), want, (hard_stop, admissible))
            # rev-1 selects D1 exactly when it triggers; the D1 map then carries the verdict.
            if block['trigger']:
                self.assertEqual((block['model_used'], block['live_round_verdict']),
                                 ('d1', 'pending_d1'))
            else:
                self.assertEqual((block['model_used'], block['live_round_verdict']),
                                 ('rev1', 'PASS'))

    def test_the_d1_branch_carries_the_verdict_of_the_selected_model(self):
        for hard_stop, admissible in ((True, True), (True, False), (False, True), (False, False)):
            block = witness.decision(rows(hard_stop, admissible), PREREG, 'd1', rev1_trigger=True)
            self.assertEqual(block['model_used'], 'd1')
            self.assertEqual(block['live_round_verdict'],
                             'FAIL_NEGATIVE' if block['trigger'] else 'PASS')
            unselected = witness.decision(rows(hard_stop, admissible), PREREG, 'd1',
                                          rev1_trigger=False)
            self.assertEqual((unselected['model_used'], unselected['live_round_verdict']),
                             ('rev1', 'PASS'))
        unresolved = witness.decision(rows(True, True), PREREG, 'd1')
        self.assertEqual((unresolved['model_used'], unresolved['live_round_verdict']),
                         ('unresolved', 'unresolved'))

    def test_a_vacuous_admissible_set_still_triggers_through_inadmissibility(self):
        inadmissible = [dict(row, expected_u_star=0.01, admissible=False, min_fixed_r=0.9)
                        for row in rows(False, True)]
        block = witness.decision(inadmissible, PREREG, 'rev1')
        self.assertTrue(block['hard_stop'])  # vacuously: no admissible regime remains
        self.assertTrue(block['primary_inadmissible'])
        self.assertEqual(block['admissible_regimes'], 0)
        self.assertEqual(block['scope'], 'measurement')


class Gate0MapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.committed = json.loads(FIXTURE.read_text(encoding='utf-8'))

    def test_worker_count_does_not_change_a_single_byte(self):
        """Measured CPU time aside, the map is merged in task order and is worker-independent."""
        single = witness.fixture(1)
        # Spawned workers do not inherit the parent test's temporary profile registry.
        # Seed the fixture explicitly in each real child; do not change the producer.
        real_pool = witness.multiprocessing.Pool
        def fixture_pool(workers):
            return real_pool(workers, initializer=policies.set_worker_profiles,
                             initargs=(certificate.fixtures()[:2],))
        with patch.object(witness.multiprocessing, 'Pool', side_effect=fixture_pool):
            parallel = witness.fixture(3)
        self.assertEqual(dumps(single), dumps(parallel))
        self.assertEqual(dumps(single), FIXTURE.read_text(encoding='utf-8'))

    def test_the_emitted_families_are_exactly_the_pre_registered_gate0_families(self):
        for label, item in self.committed['sets'].items():
            for row in item['regimes']:
                self.assertEqual(sorted(row['families']), sorted(PREREG['gate0']['families']),
                                 (label, row['regime_id']))

    def test_f_hist_always_carries_a_non_null_member_so_no_family_can_be_omitted(self):
        for label, item in self.committed['sets'].items():
            for row in item['regimes']:
                member = row['families']['F_hist']['best_member']
                self.assertTrue(member, (label, row['regime_id']))
                self.assertEqual(len(member), row['cells']['F_hist'])
                for cell, rule in member.items():
                    self.assertIn(rule, policies.F_RULES, cell)
                self.assertIsNotNone(row['families']['F_size']['best_member'])
                self.assertIn(row['families']['F']['best_member'], policies.F_RULES)

    def test_min_fixed_r_is_the_minimum_over_f_f_size_and_f_hist(self):
        for item in self.committed['sets'].values():
            for row in item['regimes']:
                families = ('F', 'F_size', 'F_hist')
                self.assertAlmostEqual(row['min_fixed_r'],
                                       min(row['families'][name]['regret'] for name in families),
                                       places=12)
                self.assertIn(row['argmin']['family'], families)
                self.assertLessEqual(row['families']['F_hist']['regret'],
                                     row['families']['F']['regret'] + 1e-12)

    def test_static_semantic_is_an_alias_and_guarded_read_pays_a_read(self):
        for item in self.committed['sets'].values():
            for row in item['regimes']:
                families = row['families']
                self.assertEqual(families['static_semantic']['alias_of'], 'always_full_recompute')
                self.assertAlmostEqual(families['static_semantic']['regret'],
                                       families['always_full_recompute']['regret'], places=12)
                self.assertGreater(families['guarded_read']['dominated_reads'], 0.0)
                self.assertGreater(families['guarded_read']['regret'],
                                   families['always_full_recompute']['regret'])

    def test_no_learned_policy_value_appears_in_a_gate0_body(self):
        text = dumps(self.committed)
        for key in LEARNED_KEYS:
            self.assertNotIn(f'"{key}"', text, key)
        self.assertEqual(self.committed['model'], 'rev1')


class Gate0RefusalTests(unittest.TestCase):
    def test_witness_refuses_without_a_passing_certificate(self):
        with tempfile.TemporaryDirectory(prefix='vericost565_gate0_') as folder:
            missing = Path(folder) / 'absent.json'
            with self.assertRaises(RuntimeError) as absent:
                witness.run('rev1', 1, Path(folder) / 'out.json', certificate_path=missing)
            self.assertIn('certificate missing', str(absent.exception))
            failing = Path(folder) / 'failing.json'
            failing.write_text(dumps({'status': 'fail', 'parts': {'C1': {'status': 'fail'}}}),
                               encoding='utf-8')
            with self.assertRaises(RuntimeError) as refused:
                witness.run('rev1', 1, Path(folder) / 'out.json', certificate_path=failing)
            self.assertIn('did not pass', str(refused.exception))
            self.assertFalse((Path(folder) / 'out.json').exists())

    def test_the_committed_maps_embed_the_certificate_and_refuse_learned_values(self):
        for model, path in sorted(witness.OUTPUT.items()):
            data = json.loads(Path(path).read_text(encoding='utf-8'))
            self.assertEqual(data['schema'], witness.SCHEMA)
            self.assertEqual(data['model'], model)
            self.assertEqual(data['certificate_status'], 'pass')
            self.assertEqual(len(data['certificate_sha256']), 64)
            self.assertEqual(sorted(data['sets']), ['all', 'dev_seen', 'dev_syn'])
            self.assertEqual(data['sets']['dev_syn']['size_buckets_present'],
                             ['n500', 'n5000', 'n50000'])
            self.assertEqual(data['sets']['all']['size_buckets_present'],
                             ['n500', 'n5000', 'n50000', 'seen8'])
            self.assertEqual(data['sets']['dev_seen']['size_buckets_present'], ['seen8'])
            self.assertEqual(data['sets']['dev_syn']['regimes'][0]['cells']['F_hist'], 9)
            for row in data['sets']['all']['regimes']:
                self.assertEqual(sorted(row['families']), sorted(PREREG['gate0']['families']))
                self.assertTrue(row['families']['F_hist']['best_member'])
            text = dumps(data['sets'])
            for key in LEARNED_KEYS:
                self.assertNotIn(f'"{key}"', text, (model, key))


if __name__ == '__main__':
    unittest.main()
