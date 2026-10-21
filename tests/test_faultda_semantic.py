import copy
import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from pathlib import Path

from faultda_bench.semantic.compute import parameters
from faultda_bench.semantic.environment import SemanticEnv
from faultda_bench.semantic.oracle import evaluate, record_correct
from faultda_bench.semantic.policies import choose
from faultda_bench.semantic.run import episode, summarize
from faultda_bench.semantic.tasks import build, load


class SemanticBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.tasks = load()
        self.serial = 0

    def env(self, task=None, **kwargs):
        self.serial += 1
        return SemanticEnv(task or self.tasks[0], self.root / str(self.serial), **kwargs)

    def finish(self, env, policy='static_semantic'):
        while not env.terminal:
            choice = choose(json.loads(json.dumps(env.observation())), policy)
            env.step(choice['action'], choice.get('params'))
        return evaluate(env)

    def stage(self, env):
        p = parameters(env.task['contract'], env.task['catalog'])
        env.step('stage', p)
        return env.history[-1]['response']['stage_id']

    def test_frozen_tasks_and_all_semantic_faults_have_real_effect(self):
        self.assertEqual(load(), build()['tasks'])
        self.assertEqual(len(self.tasks), 12)
        self.assertEqual(len({t['source_id'] for t in self.tasks}), 3)
        for task in self.tasks:
            for fault in (False, True):
                env = self.env(task, semantic_fault=fault)
                self.assertEqual(record_correct(env.records()[0], env.task), not fault, task['id'])

    def test_strong_baseline_recovers_all_families_both_evidence_regimes(self):
        for task in self.tasks:
            for evidence in ('E0', 'E1'):
                env = self.env(task, semantic_fault=True, commit_fault=True, evidence=evidence, budget=4)
                result = self.finish(env)
                self.assertTrue(result['safe_complete'], (task['id'], evidence, result['trace']))
                self.assertEqual(result['historical_wrong_publications'], 1)
                self.assertEqual(result['agent_wrong_publications'], 0)
                self.assertEqual(len(result['private_records']), 2)
                self.assertFalse(result['private_records'][0]['active'])

    def test_generic_commit_check_misses_semantics(self):
        result = self.finish(self.env(semantic_fault=True), 'generic_verify')
        self.assertTrue(result['false_completion'])
        self.assertFalse(result['contract_complete'])

    def test_cas_conflict_then_success_and_dedup_binding(self):
        env = self.env(deduplicate=True)
        stage = self.stage(env)
        p = {'stage_id': stage, 'request_id': 'x', 'expected_revision': 0, 'mode': 'replace'}
        env.step('publish', p)
        self.assertFalse(env.history[-1]['response']['ok'])
        self.assertEqual(len(env.records()), 1)
        p['expected_revision'] = 1
        env.step('publish', p)
        self.assertTrue(env.history[-1]['response']['ok'])
        env.step('publish', p)
        self.assertTrue(env.history[-1]['response']['deduplicated'])
        self.assertEqual(len(env.records()), 2)
        p['expected_revision'] = 2
        env.step('publish', p)
        self.assertFalse(env.history[-1]['response']['ok'])

    def test_duplicate_history_not_erased_by_repair(self):
        env = self.env()
        stage = self.stage(env)
        env.step('publish', {'stage_id': stage, 'request_id': 'a', 'expected_revision': 1, 'mode': 'append'})
        env.step('publish', {'stage_id': stage, 'request_id': 'b', 'expected_revision': 2, 'mode': 'replace'})
        env.step('stop')
        result = evaluate(env)
        self.assertTrue(result['contract_complete'])
        self.assertFalse(result['safe_complete'])
        self.assertEqual(result['duplicate_events'], 1)

    def test_lost_repair_ack_is_reconciled_without_duplicate(self):
        env = self.env(semantic_fault=True, repair_ack_loss=True, budget=6)
        result = self.finish(env)
        self.assertTrue(result['safe_complete'])
        self.assertEqual(len(env.records()), 2)
        self.assertEqual(sum(h['action'] == 'publish' for h in env.history), 1)

    def test_opaque_state_pairs_have_identical_observation_for_all_tools(self):
        a = self.env(commit_fault=True, evidence='E2', budget=6, boundary='before_commit')
        b = self.env(commit_fault=True, evidence='E2', budget=6, boundary='after_commit', semantic_fault=True)
        self.assertEqual(a.observation(), b.observation())
        for action in ('status', 'inspect', 'inputs', 'catalog', 'stage', 'publish', 'escalate'):
            self.assertEqual(a.step(action), b.step(action))
        self.assertNotEqual(len(a.records()), len(b.records()))
        self.assertTrue(evaluate(a)['safe_escalation'])
        self.assertTrue(evaluate(b)['safe_escalation'])

    def test_before_commit_and_partial_staging_do_not_count_as_report(self):
        for boundary in ('before_commit', 'partial_write'):
            env = self.env(commit_fault=True, boundary=boundary, budget=4)
            self.assertEqual(env.records(), [])
            self.assertTrue(self.finish(env)['safe_complete'])

    def test_budget_and_invalid_actions_do_not_mutate(self):
        env = self.env(budget=1)
        env.step({'untrusted': 'object'})
        self.assertEqual(len(env.records()), 1)
        env.step('inspect')
        env.step('inputs')
        self.assertEqual(env.terminal, 'budget_exceeded')
        self.assertEqual(len(env.records()), 1)
        self.assertEqual(env.cost['checks'], 2)

    def test_source_and_staging_tampering_fail_closed(self):
        env = self.env()
        stage = self.stage(env)
        env.stages[stage][0].write_text('{}', encoding='utf-8')
        env.step('publish', {'stage_id': stage, 'request_id': 'x', 'expected_revision': 1, 'mode': 'replace'})
        self.assertFalse(env.history[-1]['response']['ok'])
        (env.folder / 'v1.csv').write_text('value\n999\n', encoding='utf-8')
        env.step('stop')
        self.assertFalse(evaluate(env)['source_intact'])
        self.assertFalse(evaluate(env)['contract_complete'])

    def test_observation_does_not_expose_oracle_or_share_mutable_state(self):
        env = self.env(semantic_fault=True, commit_fault=True)
        observation = env.observation()
        wire = json.dumps(observation)
        for private in ('semantic_fault', 'source_sha256', 'private_ledger', str(self.root), 'version_hashes'):
            self.assertNotIn(private, wire)
        observation['contract']['family'] = 'hacked'
        self.assertEqual(env.observation()['contract']['family'], 'group')

    def test_independent_oracle_rejects_false_lineage_and_nonfinite_output(self):
        env = self.env()
        record = env.records()[0]
        record['input_sha256'] = 'forged'
        self.assertFalse(record_correct(record, env.task))
        record = env.records()[0]
        record['output']['A'] = float('nan')
        self.assertFalse(record_correct(record, env.task))
        record['output']['A'] = True
        self.assertFalse(record_correct(record, env.task))

    def test_summary_denominators_and_interaction(self):
        rows = []
        for c in (False, True):
            for s in (False, True):
                rows.append(episode(self.tasks[0], self.root / f'{c}-{s}', 'generic_verify',
                                    commit_fault=c, semantic_fault=s, evidence='E0', budget=4, deduplicate=False))
        result = summarize(rows)[0]
        self.assertEqual(result['contract_completion']['value'], .5)
        self.assertEqual(result['false_completion_among_claims']['value'], .5)
        self.assertEqual(result['interaction'], 0)
        self.assertIsNone(result['safe_escalation_E2']['value'])

    def test_api_adapter_uses_public_observation_and_enforces_call_cap(self):
        from faultda_bench.semantic.deepseek import Client
        client = object.__new__(Client)
        client.key, client.model = 'test-placeholder', 'test-model'
        client.calls, client.max_calls, client.lock = 0, 1, threading.Lock()
        observation = self.env().observation()
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps({'choices': [{'message': {'content': '{"action":"inspect","params":{}}'}}],
                                   'usage': {'total_tokens': 5}, 'id': 'test-id'}).encode()
        with patch('urllib.request.urlopen', return_value=Response()) as request:
            choice, metadata = client.choose(observation)
            body = json.loads(request.call_args.args[0].data)
            self.assertEqual(json.loads(body['messages'][1]['content']), observation)
            self.assertNotIn('test-placeholder', json.dumps(body))
            self.assertEqual(choice['action'], 'inspect')
            self.assertEqual(metadata['usage']['total_tokens'], 5)
            self.assertEqual(client.choose(observation)[1]['error'], 'pilot_call_cap')
            self.assertEqual(request.call_count, 1)

    def test_api_transport_error_is_not_reported_as_safe_escalation(self):
        from faultda_bench.semantic.deepseek import Client
        client = object.__new__(Client)
        client.key, client.model = 'test-placeholder', 'test-model'
        client.calls, client.max_calls, client.lock = 0, 1, threading.Lock()
        env = self.env()
        with patch('urllib.request.urlopen', side_effect=TimeoutError('do not log remote text')):
            choice, metadata = client.choose(env.observation())
        self.assertIsNone(choice)
        self.assertEqual(metadata['error'], 'TimeoutError')
        self.assertNotIn('do not log', json.dumps(metadata))
        env.terminal = 'provider_error'
        self.assertFalse(evaluate(env)['safe_escalation'])
