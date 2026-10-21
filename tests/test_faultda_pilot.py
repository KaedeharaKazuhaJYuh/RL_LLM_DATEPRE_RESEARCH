import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from faultda_bench.evidence.core import tasks
from faultda_bench.pilot.client import Client
from faultda_bench.pilot.contract import messages, public_observation
from faultda_bench.pilot.suite import execute, offline
from faultda_bench.pilot.verify import replay_live, verify
from faultda_bench.trust.environment import ComputeFaultEnv

CONFIG = {'DEEPSEEK_API_KEY': 'dummy-unit-test-key'}


def answer(choice):
    return {'model': 'mock-offline', 'id': 'unit-test-response',
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1},
            'choices': [{'message': {'content': json.dumps(choice)}}]}


class PilotTests(unittest.TestCase):
    def observation(self, folder, mode='healthy'):
        env = ComputeFaultEnv(tasks()[0], Path(folder) / mode, mode=mode, evidence='E1', budget=3)
        return public_observation(env)

    def test_public_reliability_contract_same_across_hidden_modes(self):
        with tempfile.TemporaryDirectory() as folder:
            obs = [self.observation(folder, mode) for mode in ('healthy', 'stage_only', 'shared_compute')]
            self.assertTrue(all(o == obs[0] for o in obs))
            self.assertIn('reliability_contract', obs[0])
            self.assertFalse({'mode', 'task_id', 'private_records', 'private_effects', 'arm'} & set(obs[0]))

    def test_wire_messages_equal_public_builder_and_invalid_json_not_healed(self):
        with tempfile.TemporaryDirectory() as folder:
            observation = self.observation(folder)
            def transport(request):
                body = json.loads(request.data)
                self.assertEqual(body['messages'], messages(observation))
                self.assertEqual(body['max_tokens'], 800)
                return answer({'action': 'stop', 'params': {}, 'fault_mode': 'hidden'})
            client = Client('deepseek-flash', config=CONFIG, transport=transport)
            choice, metadata = client.choose(observation)
            self.assertEqual(choice['action'], 'invalid_model_output')
            self.assertTrue(metadata['parse_error'])
            self.assertEqual(client.calls, 1)

    def test_call_cap_has_no_implicit_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            observation = self.observation(folder)
            sent = []
            def transport(request):
                sent.append(request)
                return answer({'action': 'stop', 'params': {}})
            client = Client('deepseek-flash', max_calls=1, config=CONFIG, transport=transport)
            client.choose(observation)
            choice, metadata = client.choose(observation)
            self.assertIsNone(choice)
            self.assertEqual(metadata['error'], 'pilot_call_cap')
            self.assertEqual(len(sent), 1)
            self.assertIs(metadata['request_sent'], False)

    def test_provider_exception_message_not_persisted(self):
        with tempfile.TemporaryDirectory() as folder:
            def transport(request):
                raise RuntimeError('private-secret-provider-text')
            client = Client('deepseek-flash', config=CONFIG, transport=transport)
            choice, metadata = client.choose(self.observation(folder))
            self.assertIsNone(choice)
            self.assertNotIn('private-secret', json.dumps(metadata))
            self.assertEqual(client.calls, 1)

    def test_overbudget_model_action_is_not_changed_to_escalation(self):
        with tempfile.TemporaryDirectory() as folder:
            client = Client('deepseek-flash', config=CONFIG,
                            transport=lambda request: answer({'action': 'inspect', 'params': {}}))
            cell = dict(task_id=tasks()[0]['id'], mode='healthy', evidence='E1', budget=3, arm='deepseek')
            row = execute(tasks()[0], Path(folder) / 'run', cell, client)
            self.assertEqual(row['terminal'], 'budget_exceeded')
            self.assertEqual(row['cost']['checks'], 4)
            self.assertEqual(len(row['api_calls']), 4)
            replay_live(tasks()[0], Path(folder) / 'replay', row, cell)

    def test_local_cap_terminal_replays_with_mock_transport(self):
        with tempfile.TemporaryDirectory() as folder:
            client = Client('deepseek-flash', max_calls=1, config=CONFIG,
                            transport=lambda request: answer({'action': 'inspect', 'params': {}}))
            cell = dict(task_id=tasks()[0]['id'], mode='shared_compute', evidence='E1', budget=3, arm='deepseek')
            row = execute(tasks()[0], Path(folder) / 'run', cell, client)
            self.assertEqual(row['terminal'], 'api_budget_exceeded')
            self.assertEqual(client.calls, 1)
            replay_live(tasks()[0], Path(folder) / 'replay', row, cell)

    def test_offline_never_networks_and_rehashed_prompt_tampering_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'result.json'
            with patch('urllib.request.urlopen', side_effect=AssertionError('no live call in offline')):
                result = offline(path)
                self.assertEqual(result['request_attempts'], 0)
            self.assertEqual(verify(path)['executions'], 36)
            result = json.loads(path.read_text())
            tp = path.with_suffix('.jsonl')
            rows = [json.loads(line) for line in tp.read_text().splitlines()]
            rows[0]['prompt_audit'][0]['sha256'] = 'forged'
            data = ('\n'.join(json.dumps(r) for r in rows) + '\n').encode()
            tp.write_bytes(data)
            result['trace_sha256'] = hashlib.sha256(data).hexdigest()
            path.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError, 'offline prompt and effect replay'):
                verify(path)
            with self.assertRaises(FileExistsError):
                offline(path)


if __name__ == '__main__':
    unittest.main()
