import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from faultda_bench.formatdiag.core import Client, body, classify
from faultda_bench.formatdiag.suite import protocol
from faultda_bench.formatdiag.verify import verify


def response(content, finish='stop'):
    return {'model': 'offline_fake', 'choices': [{'finish_reason': finish,
            'message': {'content': content, 'reasoning_content': 'not persisted'}}]}


class FormatDiagnosticTests(unittest.TestCase):
    def test_failure_categories_and_length_are_separate(self):
        cases = [(None, 'empty_content'), ('  ', 'empty_content'), ('{', 'json_error'),
                 ('{"action":"stop"}', 'schema_error'),
                 ('{"action":"unknown","params":{}}', 'schema_error'),
                 ('{"action":"stop","params":{}}', 'valid_action'),
                 ('{"action":"stop","action":"inspect","params":{}}', 'json_error'),
                 ('{"action":"stop","params":{"x":NaN}}', 'json_error'),
                 ('{"action":"stop","params":{"x":1e999}}', 'json_error')]
        for content, category in cases:
            with self.subTest(content=content):
                result = classify(response(content, 'length'))
                self.assertEqual(result['category'], category)
                self.assertTrue(result['length_finish'])
                self.assertNotIn('reasoning_content', result)
                self.assertNotIn('not persisted', json.dumps(result))
        self.assertEqual(classify({})['category'], 'response_shape')
        self.assertEqual(classify([])['category'], 'response_shape')

    def test_exact_body_modes_cap_and_sanitized_exception(self):
        captured = []
        def transport(request):
            captured.append(json.loads(request.data))
            raise RuntimeError('private-key-and-provider-message')
        client = Client('deepseek-flash', 1, transport=transport, config={'DEEPSEEK_API_KEY': 'fake'})
        cell = {'thinking': 'disabled', 'max_tokens': 800}
        result = client.request_once({}, cell)
        self.assertEqual(captured[0], body({}, cell))
        self.assertNotIn('reasoning_effort', captured[0])
        self.assertEqual(result['category'], 'provider_error')
        self.assertNotIn('private-key', json.dumps(result))
        self.assertEqual(client.request_once({}, cell)['category'], 'request_cap')
        self.assertEqual(len(captured), 1)
        self.assertEqual(body({}, {'thinking': 'enabled', 'max_tokens': 2048})['reasoning_effort'], 'low')

    def test_frozen_balanced_snapshots_without_network(self):
        with patch('urllib.request.urlopen', side_effect=AssertionError('unexpected network')):
            plan = protocol()
        self.assertEqual(len(plan['order']), 24)
        self.assertEqual(len(plan['observations']), 3)
        cells = {(r['task_id'], r['thinking'], r['max_tokens'], r['repeat']) for r in plan['order']}
        self.assertEqual(len(cells), 24)
        for obs in plan['observations'].values():
            self.assertNotIn('mode', obs)
            self.assertNotIn('private_records', obs)

    def test_receipt_request_rebuild_rejects_rehashed_forgery(self):
        from faultda_bench.formatdiag import suite
        from faultda_bench.semantic.tasks import sha
        from faultda_bench.clarity.tasks import write_json
        from contextlib import redirect_stdout
        import io
        fake = Client('deepseek-flash', 24, transport=lambda r: response('{"action":"inspect","params":{}}'),
                      config={'DEEPSEEK_API_KEY': 'fake'})
        with tempfile.TemporaryDirectory() as folder:
            plan, output = Path(folder)/'plan.json', Path(folder)/'fake.json'
            write_json(plan, protocol())
            with patch.object(suite, 'Client', return_value=fake), redirect_stdout(io.StringIO()):
                suite.live(plan, output)
            self.assertEqual(verify(output)['status'], 'verified')
            trace = output.with_suffix('.jsonl')
            rows = [json.loads(x) for x in trace.read_text().splitlines()]
            rows[0]['request_sha256'] = '0'*64
            trace.write_text('\n'.join(json.dumps(r) for r in rows)+'\n', encoding='utf-8')
            result = json.loads(output.read_text())
            result['trace_sha256'] = sha(trace)
            output.write_text(json.dumps(result), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'request rebuild'):
                verify(output)


if __name__ == '__main__':
    unittest.main()
