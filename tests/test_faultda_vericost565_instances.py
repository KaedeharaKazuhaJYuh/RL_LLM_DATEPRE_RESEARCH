import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from faultda_bench.semantic.tasks import REPO, sha
from faultda_bench.vericost565 import costs, instances, simulator
from faultda_bench.vericost565.canon import compact, dumps, sha_json
from faultda_bench.vericost565.environment import VeriCostEnv, leaked_labels

COUNTS = instances.VALIDATION_COUNTS


class InstanceIndexTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = instances.load()
        cls.profiles = instances.build_profiles(cls.index)
        cls.by_id = {profile['profile_id']: profile for profile in cls.profiles}

    def test_committed_index_declares_the_development_scope(self):
        self.assertEqual(self.index['schema'], instances.SCHEMA)
        self.assertEqual(self.index['split'], 'development')
        self.assertIs(self.index['seen_cluster'], True)
        self.assertIs(self.index['independent_test'], False)
        self.assertEqual(self.index['generalization_claim'], 'none')
        self.assertEqual(len(self.index['clusters']), 4)
        self.assertEqual(sorted(item['cluster_id'] for item in self.index['clusters']),
                         ['synthetic', 'uci_auto_mpg', 'uci_glass', 'uci_occupancy'])
        self.assertEqual(self.index['validation']['c2_status'], 'pass')

    def test_every_kept_profile_carries_parts_bytes_and_costs_at_all_eight_regimes(self):
        self.assertEqual(len(self.index['profiles']), 30)
        for profile in self.index['profiles']:
            self.assertGreaterEqual(len(profile['parts']), instances.MIN_PARTS)
            self.assertEqual(len(profile['fault_rows']), len(profile['parts']))
            self.assertEqual(list(profile['costs']), list(costs.REGIME_IDS))
            self.assertEqual(profile['split'], 'development')
            for part in profile['parts']:
                self.assertGreater(part['bytes'], 0)
                self.assertGreater(part['rows'], 0)
            for regime in profile['costs'].values():
                self.assertEqual(len(regime['spot_check']), len(profile['parts']))
                self.assertEqual(len(regime['read_rows']), len(profile['parts']))

    def test_excluded_profiles_carry_a_reason(self):
        for item in self.index['excluded']:
            self.assertEqual(set(item), {'profile_id', 'reason'})
            self.assertIn(item['reason'], ('fault_unrealizable', 'too_few_parts'))

    def test_the_seen_tasks_map_to_profiles_with_the_expected_part_structure(self):
        seen = [p for p in self.index['profiles'] if p['kind'] == 'seen_development']
        self.assertEqual(len(seen) + len(self.index['excluded']), 24)
        for profile in seen:
            self.assertEqual(profile['n'], 8)
            self.assertEqual(profile['size_bucket'], 'seen8')
            if profile['family'] == 'version':
                self.assertEqual([part['rows'] for part in profile['parts']], [1] * 8)
            else:
                self.assertIn(len(profile['parts']), range(2, 9))
                self.assertEqual(sum(part['rows'] for part in profile['parts']), 8)

    def test_seen_sources_are_reverified_against_the_repo_csv(self):
        for profile in self.index['profiles']:
            if profile['kind'] != 'seen_development':
                continue
            self.assertEqual(sha(REPO / profile['source']['path']), profile['source']['sha256'])

    def test_the_fault_construction_keeps_the_discrepancy_at_nine_tenths_of_the_value(self):
        for profile in self.index['profiles']:
            for fault in profile['fault_rows']:
                value, carried = Decimal(fault['v']), Decimal(fault['w'])
                self.assertNotEqual(value, 0)
                self.assertEqual(carried, value / 10)
                self.assertEqual(Decimal(fault['discrepancy']), 9 * carried)
                self.assertEqual(value - carried, Decimal(fault['discrepancy']))

    def test_materialize_shares_the_rows_and_derives_totals_from_the_override_map(self):
        profile = self.by_id['syn-skewed-n5000']
        parts = len(profile['parts'])
        for latent in simulator.latents('rev1', parts):
            mat = instances.materialize(profile, latent)
            self.assertIs(mat.rows, profile['rows'])
            self.assertLessEqual(len(mat.override), parts)
            self.assertEqual(mat.affected, simulator.affected_parts(latent, parts))
            for part in range(parts):
                expected = mat.report_totals[part]
                if part in mat.affected:
                    fault = profile['fault_rows'][part]
                    expected = expected - Decimal(fault['v']) + Decimal(fault['w'])
                    self.assertEqual(mat.report_totals[part] - mat.source_totals[part],
                                     Decimal(fault['discrepancy']))
                self.assertEqual(mat.source_totals[part], expected)

    def test_the_visible_local_story_adds_exactly_one_engine_row(self):
        profile = self.by_id['syn-equal-n500']
        rows = [part['rows'] for part in profile['parts']]
        self.assertEqual(list(instances.materialize(profile, ('local', 2, True)).engine_row_counts),
                         [count + (1 if index == 2 else 0) for index, count in enumerate(rows)])
        self.assertEqual(list(instances.materialize(profile, ('local', 2, False)).engine_row_counts),
                         rows)
        self.assertEqual(list(instances.materialize(profile, ('global', 255)).engine_row_counts), rows)

    def test_the_static_observation_is_byte_identical_under_every_latent(self):
        for profile in self.profiles:
            parts = len(profile['parts'])
            signatures = set()
            for latent in simulator.latents('rev1', parts):
                env = VeriCostEnv(instances.materialize(profile, latent), counts=COUNTS,
                                  regime=costs.PRIMARY)
                signatures.add(instances._static_signature(env.observation()))
                self.assertEqual(leaked_labels(env.observation()), [])
                env.close()
            self.assertEqual(len(signatures), 1, profile['profile_id'])

    def test_contract_text_is_vericost_owned_and_never_the_seen_task_text(self):
        from faultda_bench.clarity.tasks import load as load_cross_source
        texts = {task['id']: task['contract']['analysis'] for task in load_cross_source()}
        for profile in self.index['profiles']:
            self.assertEqual(profile['contract'], instances.CONTRACTS[profile['family']])
            if profile['profile_id'] in texts:
                self.assertNotEqual(profile['contract'], texts[profile['profile_id']])

    def test_check_passes_at_head_and_fails_on_a_perturbed_index(self):
        self.assertEqual(instances.check()['status'], 'ok')
        with tempfile.TemporaryDirectory(prefix='vericost565_index_') as folder:
            copy = Path(folder) / 'vericost_v1_instances.json'
            shutil.copy(instances.INDEX, copy)
            data = json.loads(copy.read_text(encoding='utf-8'))
            data['profiles'][0]['rows_sha256'] = '0' * 64
            copy.write_text(compact(data), encoding='utf-8')
            done = subprocess.run([sys.executable, '-m', 'faultda_bench.vericost565.instances',
                                   '--check', '--path', str(copy)], cwd=REPO, capture_output=True,
                                  text=True)
            self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
            self.assertIn('does not match a rebuild', done.stderr)

    def test_the_index_is_write_once(self):
        with self.assertRaises(FileExistsError):
            instances.index()

    def test_golden_fixture_reproduces_byte_for_byte(self):
        committed = instances.GOLDEN.read_text(encoding='utf-8')
        fixture = instances.golden()
        self.assertEqual(committed, dumps(fixture))
        self.assertEqual(sha_json(fixture), sha(instances.GOLDEN))
        self.assertEqual(len(fixture['training_draws']), instances.GOLDEN_DRAWS)
        self.assertEqual(len(fixture['episodes']), 3 * len(self.index['profiles']))
        self.assertEqual(list(fixture['utility']), list(costs.REGIME_IDS))
        self.assertEqual(fixture['utility'][costs.PRIMARY],
                         {'safe_complete': 1.0, 'false_completion': -3, 'forbidden_effect': -3,
                          'escalate': 0.0, 'response_failure': 0.0})

    def test_validate_rejects_an_unrealizable_profile(self):
        broken = dict(self.by_id['syn-equal-n500'])
        broken['fault_rows'] = broken['fault_rows'][:-1]
        with self.assertRaisesRegex(ValueError, 'unrealizable profile'):
            instances.validate(broken)


if __name__ == '__main__':
    unittest.main()
