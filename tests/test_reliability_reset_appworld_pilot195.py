import io
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from research.reliability_reset.appworld_pilot195 import DeepSeek, check_call, parse_proposal, peak_cost


class ProposalTests(unittest.TestCase):
    def test_valid_and_thinking_prefix_are_kept_separate(self):
        proposal = parse_proposal('<think>reasoning</think>{"type":"call","app":"a","api":"b","arguments":{}}')
        self.assertEqual(proposal, {"type": "call", "app": "a", "api": "b", "arguments": {}})

    def test_duplicate_keys_and_malformed_text_are_rejected(self):
        for raw in ('{"type":"stop","type":"call"}', '{"type":"call"}', '```json\n{}\n```', None):
            with self.subTest(raw=raw), self.assertRaises((ValueError, TypeError)):
                parse_proposal(raw)

    def test_missing_parameters_are_not_repaired(self):
        docs = {"a": {"b": {"parameters": [{"name": "needed", "required": True}]}}}
        proposal = {"type": "call", "app": "a", "api": "b", "arguments": {}}
        self.assertEqual(check_call(proposal, docs), "missing_required_argument")
        self.assertEqual(proposal["arguments"], {})
        proposal["arguments"] = {"needed": 4, "unexpected": 1}
        self.assertEqual(check_call(proposal, docs), "unknown_argument")
        proposal["arguments"] = {"needed": 4}
        self.assertIsNone(check_call(proposal, docs))


class UsageTests(unittest.TestCase):
    def test_peak_rate_uses_reported_hit_miss_and_output(self):
        usage = {"prompt_cache_hit_tokens": 1000, "prompt_cache_miss_tokens": 2000,
                 "prompt_tokens": 3000, "completion_tokens": 400, "total_tokens": 3400}
        self.assertAlmostEqual(peak_cost(usage), (1000 * .006 + 2000 * .30 + 400 * 1.20) / 1_000_000)

    def test_missing_or_inconsistent_usage_is_unknown(self):
        self.assertIsNone(peak_cost({"prompt_tokens": 10, "completion_tokens": 2}))
        self.assertIsNone(peak_cost({"prompt_tokens": 10, "prompt_cache_hit_tokens": 2,
                                     "prompt_cache_miss_tokens": 3, "completion_tokens": 2}))

    def test_remote_uses_unfrozen_clock_and_retains_provider_body(self):
        clock = SimpleNamespace(real_perf_counter=Mock(side_effect=[10.0, 12.5]))
        response = {"id": "r1", "model": "m", "choices": [{"finish_reason": "stop", "message": {"content": '{"type":"stop"}'}}],
                    "usage": {"prompt_tokens": 10, "prompt_cache_hit_tokens": 2,
                              "prompt_cache_miss_tokens": 8, "completion_tokens": 2, "total_tokens": 12}}
        client = DeepSeek.__new__(DeepSeek)
        client.key = "unit-test-only"
        with patch.dict(sys.modules, {"freezegun": SimpleNamespace(api=clock)}), \
             patch("urllib.request.urlopen", return_value=io.BytesIO(json.dumps(response).encode())):
            result = client.request([{"role": "user", "content": "test"}])
        self.assertEqual(result["seconds"], 2.5)
        self.assertEqual(result["provider_response"], response)
        self.assertEqual(result["response_id"], "r1")

    def test_provider_error_redacts_local_credential(self):
        clock = SimpleNamespace(real_perf_counter=Mock(side_effect=[10.0, 12.0]))
        client = DeepSeek.__new__(DeepSeek)
        client.key = "unit-test-only"
        error = HTTPError("https://example.invalid", 401, "unauthorized", {}, io.BytesIO(b"unit-test-only"))
        with patch.dict(sys.modules, {"freezegun": SimpleNamespace(api=clock)}), \
             patch("urllib.request.urlopen", side_effect=error):
            result = client.request([])
        self.assertEqual(result["http_status"], 401)
        self.assertEqual(result["error_body"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
