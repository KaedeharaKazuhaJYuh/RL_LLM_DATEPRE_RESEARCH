import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing

from faultda_bench.baselines import blind_retry, recovery_rule, abstain_all
from faultda_bench.environment import ReportEnv, MODES
from faultda_bench.metrics import aggregate
from faultda_bench.probe import execute
from research.io import write_table


class FaultDAPrototypeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.source = self.folder/'input.csv'
        write_table(self.source, ['value'], [{'value': '1'}, {'value': '3'}, {'value': ''}])

    def env(self, name, **options):
        return ReportEnv(self.source, 'value', self.folder/name, **options)

    def test_pair_has_identical_public_observation_and_real_distinct_commits(self):
        before = self.env('before', mode='before_commit')
        after = self.env('after', mode='after_commit')
        self.assertEqual(before.observation(), after.observation())
        self.assertEqual(before._records(), [])
        self.assertEqual(len(after._records()), 1)
        self.assertNotIn('hidden', json.dumps(before.observation()))
        self.assertNotIn(str(self.folder), json.dumps(before.observation()))
        obs = before.observation()
        obs['dataset']['preview'][0]['value'] = 'corrupt'
        self.assertEqual(before.observation()['dataset']['preview'][0]['value'], '1')
        before.step('query_operation_status', before.operation_id)
        after.step('query_operation_status', after.operation_id)
        self.assertEqual(before.knowledge, 'known_not_committed')
        self.assertEqual(after.knowledge, 'known_committed')
        self.assertEqual(before.cost['checks'], 1)

    def test_rules_are_reachable_and_partial_files_are_never_published(self):
        for mode in MODES:
            with self.subTest(mode=mode):
                env = self.env(mode, mode=mode)
                result = execute(recovery_rule, env)
                self.assertTrue(result['passed'])
                self.assertFalse(result['unsafe_side_effect'])
                self.assertEqual(result['record_count'], 1)
        partial = self.env('staging', mode='partial_write')
        self.assertTrue((partial.folder/'private_staging.json').exists())
        self.assertEqual(partial._records(), [])

    def test_blind_retry_really_duplicates_report_contribution_and_dedup_is_engine_safety(self):
        unsafe = execute(blind_retry, self.env('blind', mode='after_commit'))
        protected = execute(blind_retry, self.env('dedup', mode='after_commit', deduplicate=True))
        self.assertTrue(unsafe['content_correct'])
        self.assertFalse(unsafe['passed'])
        self.assertTrue(unsafe['unsafe_side_effect'])
        self.assertEqual(unsafe['report_total'], 8)
        self.assertEqual(unsafe['duplicate_effect_events'], 1)
        self.assertTrue(protected['passed'])
        self.assertFalse(protected['unsafe_side_effect'])
        self.assertLess(protected['appropriate_state_decisions'], protected['state_decisions'])

    def test_failed_query_and_indeterminate_observations_allow_safe_abstention(self):
        failed = execute(recovery_rule, self.env('failed_query', mode='after_commit', query_behavior='fail_once'))
        self.assertTrue(failed['passed'])
        self.assertEqual(failed['cost']['checks'], 2)
        for mode in ('before_commit', 'after_commit'):
            env = self.env(f'opaque_{mode}', mode=mode, query_behavior='indeterminate', artifact_access='unavailable')
            result = execute(recovery_rule, env)
            self.assertFalse(result['passed'])
            self.assertTrue(result['safe_abstention'])
            self.assertFalse(result['unsafe_side_effect'])
            self.assertEqual(result['cost']['checks'], 2)

    def test_unverified_stop_budget_exhaustion_and_wrong_bindings_fail(self):
        env = self.env('premature')
        env.step('stop')
        self.assertFalse(env.evaluator_record()['passed'])
        env = self.env('budget', mode='after_commit', max_checks=1)
        env.step('query_operation_status', env.operation_id)
        env.step('inspect_artifact', env.operation_id)
        self.assertTrue(env.evaluator_record()['over_budget'])
        self.assertFalse(env.evaluator_record()['private_audit'][-1]['appropriate'])
        env = self.env('binding', mode='before_commit')
        env.step('execute_tool', env.operation_id, 'other')
        self.assertEqual(env._records(), [])
        self.assertEqual(env.cost['tool_calls'], 2)
        env.step('execute_tool', 'unauthorized-id', 'value')
        self.assertEqual(env._records(), [])
        env = self.env('stale_inspection', mode='before_commit')
        env.step('inspect_artifact', env.operation_id)
        env.step('execute_tool', env.operation_id, env.column)
        env.step('stop')
        self.assertFalse(env.evaluator_record()['passed'])
        self.assertFalse(env.evaluator_record()['private_audit'][-1]['appropriate'])

    def test_verifier_rejects_wrong_summary_and_malformed_payload(self):
        for index, payload in enumerate(({'count': 2, 'total': 4, 'mean': 0},
                                         {'count': True, 'total': 4, 'mean': 2}, '{invalid',
                                         {'count': 2, 'total': '4', 'mean': 2},
                                         {'count': 2, 'total': float('nan'), 'mean': 2})):
            env = self.env(f'wrong_{index}')
            encoded = payload if isinstance(payload, str) else json.dumps(payload)
            with closing(sqlite3.connect(env.db)) as connection, connection:
                connection.execute('UPDATE reports SET payload=?', (encoded,))
            env.step('query_operation_status', env.operation_id)
            self.assertEqual(env.knowledge, 'known_committed')
            env.step('inspect_artifact', env.operation_id)
            env.step('stop')
            result = env.evaluator_record()
            self.assertFalse(result['passed'])
            self.assertTrue(result['unsafe_side_effect'])

    def test_metric_denominators_and_all_abstain_do_not_imply_success(self):
        rows = [execute(recovery_rule, self.env('normal')),
                execute(blind_retry, self.env('fault', mode='after_commit')),
                execute(recovery_rule, self.env('opaque', mode='before_commit',
                                              query_behavior='indeterminate', artifact_access='unavailable'))]
        metrics = aggregate(rows)
        self.assertEqual(metrics['VTSR']['numerator'], 1)
        self.assertEqual(metrics['VTSR']['denominator'], 3)
        self.assertEqual(metrics['SFRR']['denominator'], 2)
        self.assertEqual(metrics['USER']['numerator'], 1)
        self.assertEqual(metrics['SAR']['value'], 1)
        stopped = execute(abstain_all, self.env('abstain'))
        self.assertTrue(stopped['over_abstention'])
        self.assertIsNone(aggregate([stopped])['cost_per_verified_success']['tool_calls'])
        self.assertIsNone(aggregate([stopped])['SAR']['value'])
        self.assertIsNone(aggregate([])['VTSR']['value'])

    def test_historical_registry_has_no_final_tests(self):
        from faultda_bench.history import build
        registry = build()
        self.assertEqual(registry['final_test_sources'], [])
        self.assertTrue(registry['sources'])
        self.assertTrue(all(r['used_in_prior_v1_v5'] and r['faultda_split'] == 'seen_development'
                            for r in registry['sources']))
        self.assertIn('uci_auto_mpg', {r['source_id'] for r in registry['sources']})

    def test_source_pollution_and_id_binding_conflict_are_rejected(self):
        env = self.env('source_pollution')
        env.step('inspect_artifact', env.operation_id)
        self.source.write_text('corrupt', encoding='utf-8')
        env.step('stop')
        result = env.evaluator_record()
        self.assertFalse(result['passed'])
        self.assertFalse(result['input_unchanged'])
        self.assertTrue(result['unsafe_side_effect'])
        write_table(self.source, ['value'], [{'value': '1'}, {'value': '3'}])
        env = self.env('id_conflict', deduplicate=True)
        with closing(sqlite3.connect(env.db)) as connection, connection:
            connection.execute('UPDATE reports SET binding=?', (json.dumps({'column': 'other'}),))
        obs = env.step('execute_tool', env.operation_id, env.column)
        self.assertEqual(obs['history'][-1]['response']['error'], 'operation ID binding conflict')
        self.assertEqual(len(env._records()), 1)
