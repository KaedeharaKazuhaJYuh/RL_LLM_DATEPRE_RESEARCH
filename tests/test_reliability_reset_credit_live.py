"""Network-free model-journal, exact-prefix, budget and role-isolation checks."""

import json
import tempfile
import unittest
import urllib.error
from pathlib import Path

from faultda_bench.semantic.policies import choose
from faultda_bench.semantic.tasks import load
from research.reliability_reset.credit_live import Client, MODEL, PrefixReplay, execute, parse_action, prepare
from research.reliability_reset.recovery_credit import ControllerStop, fingerprint, run


def response(proposal):
    return {"id": "unit-test-response", "model": "unit-test-model-not-live",
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal)}}]}


class CreditLiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {"DEEPSEEK_API_KEY": "unit-test-secret-not-a-real-key", "DEEPSEEK_MODEL": "deepseek-chat"}
        self.task = next(t for t in load() if t["id"] == "group-01")

    def client(self, transport):
        return Client(self.root / "requests.jsonl", config=self.config, transport=transport)

    def test_valid_output_and_invalid_length_fence_duplicate_or_nan(self):
        action = {"action": "stop", "params": {}}
        self.assertEqual(parse_action(response(action)), (action, None))
        for text in ('```json\n{"action":"stop","params":{}}\n```',
                     '{"action":"stop","action":"publish","params":{}}',
                     '{"action":"stop","params":{"x":NaN}}',
                     '{"action":"stop","params":{},"rationale":"extra"}'):
            answer = response(action)
            answer["choices"][0]["message"]["content"] = text
            self.assertEqual(parse_action(answer)[1], "invalid_model_output")
        answer = response(action)
        answer["choices"][0]["finish_reason"] = "length"
        self.assertEqual(parse_action(answer)[1], "invalid_model_output")

    def test_named_model_never_dispatches_helper_to_vendor(self):
        policies = []
        def dispatcher(observation, policy):
            policies.append(policy)
            self.assertEqual(policy, MODEL)
            return choose(observation, "generic_verify")
        result = run(self.task, self.root / "run", "semantic_error", 4, MODEL, True,
                     dispatcher=dispatcher, primary_kind="unit_test_model")
        self.assertTrue(result["independent_assessment"]["safe_complete"])
        self.assertEqual(policies, [MODEL, MODEL])
        self.assertEqual({s["actor_kind"] for s in result["steps"]}, {"unit_test_model", "public_rule"})

    def test_input_request_and_cost_limits_prevent_transport(self):
        def no_send(request):
            self.fail("transport must not run")
        client = self.client(no_send)
        with self.assertRaisesRegex(ControllerStop, "input_limit"):
            client({"payload": "a" * 13000}, MODEL)
        client.calls = 96
        with self.assertRaisesRegex(ControllerStop, "request_limit"):
            client({}, MODEL)
        client.calls, client.peak_cost = 0, 0.60
        with self.assertRaisesRegex(ControllerStop, "cost_limit"):
            client({}, MODEL)
        self.assertFalse(any(r["request_sent"] for r in client.records))

    def test_provider_failure_is_not_retried_or_converted_to_stop(self):
        requests = []
        def failure(request):
            requests.append(request)
            raise urllib.error.URLError(self.config["DEEPSEEK_API_KEY"])
        client = self.client(failure)
        with self.assertRaisesRegex(ControllerStop, "provider_error"):
            client({}, MODEL)
        with self.assertRaisesRegex(ControllerStop, "provider_unavailable"):
            client({}, MODEL)
        self.assertEqual(len(requests), 1)
        self.assertGreater(client.peak_cost, 0)
        self.assertNotIn(self.config["DEEPSEEK_API_KEY"], client.journal.read_text(encoding="utf-8"))

    def test_raw_response_preserved_with_only_known_credential_echo_redacted(self):
        def transport(request):
            body = json.loads(request.data)
            self.assertEqual(request.full_url, "https://api.deepseek.com/chat/completions")
            self.assertEqual(body["model"], "deepseek-flash")
            self.assertEqual(body["thinking"], {"type": "disabled"})
            answer = response({"action": "stop", "params": {}})
            answer["provider_debug"] = self.config["DEEPSEEK_API_KEY"]
            return answer
        client = self.client(transport)
        self.assertEqual(client({}, MODEL)["action"], "invalid_model_output")
        text = client.journal.read_text(encoding="utf-8")
        self.assertNotIn(self.config["DEEPSEEK_API_KEY"], text)
        self.assertIn('"raw_response"', text)
        self.assertIn('"prompt_tokens": 100', text)
        self.assertIn('[REDACTED_CREDENTIAL]', text)

    def test_exact_prefix_checks_observation_and_preserves_controller_stop(self):
        execution = {"decisions": [{"actor": "primary", "public_observation_sha256": fingerprint({"x": 1}),
                                   "kind": "controller_stop", "reason": "provider_error"}]}
        with self.assertRaisesRegex(ValueError, "public prefix mismatch"):
            PrefixReplay(execution)({"x": 2}, MODEL)
        with self.assertRaisesRegex(ControllerStop, "provider_error"):
            PrefixReplay(execution)({"x": 1}, MODEL)

    def test_model_over_budget_attempt_is_recorded_without_executing_extra_read(self):
        result = run(self.task, self.root / "run", "healthy", 1, MODEL,
                     dispatcher=lambda o, p: {"action": "status", "params": {}}, primary_kind="unit_test_model")
        self.assertEqual(result["terminal"], "budget_exceeded")
        self.assertEqual(result["cost"]["checks"], 1)
        self.assertEqual(result["decisions"][-1]["kind"], "budget_rejection")
        self.assertEqual(result["cost"]["unexecuted_decisions"], 1)
        self.assertEqual(len(result["steps"]), 1)

    def test_invalid_model_responses_reach_primary_limit_without_becoming_handoff(self):
        answer = response({"action": "not_a_tool", "params": {}})
        client = self.client(lambda request: answer)
        result = run(self.task, self.root / "run", "healthy", 4, MODEL, True,
                     dispatcher=client, primary_kind="model_api", max_primary_decisions=8)
        self.assertEqual(result["terminal"], "primary_limit")
        self.assertEqual(client.calls, 8)
        self.assertEqual(result["cost"]["handoff_decisions"], 0)
        self.assertTrue(all(d["actor"] == "primary" for d in result["decisions"]))

    def test_fake_pilot_keeps_real_response_journal_bound_to_replayed_decisions(self):
        study = self.root / "study"
        prepare(study)
        def transport(request):
            body = json.loads(request.data)
            obs = json.loads(body["messages"][1]["content"])
            proposal = choose(obs, "generic_verify")
            proposal.setdefault("params", {})  # fake vendor obeys the frozen model JSON schema
            return response(proposal)
        client = Client(study / "requests.jsonl", config=self.config, transport=transport)
        result = execute(study, client=client)
        self.assertEqual(result["executions"], 36)
        self.assertEqual(result["requests_sent"], 24)
        self.assertEqual(result["resolved_triplets"], 12)
        self.assertEqual(result["signatures"], {"111": 3, "101": 3, "001": 3, "011": 3})
        self.assertEqual(result["native_exact_agree"], 36)
        rows = json.loads((study / "runs.json").read_text(encoding="utf-8"))
        for row in rows:
            e = json.loads((study / row["evidence"]).read_text(encoding="utf-8"))
            if row["system"] == "same_prefix_plus_helper":
                self.assertEqual(e["new_model_calls"], 0)
            if row["system"] == "live_primary":
                for binding, decision in zip(e["request_record_bindings"], e["decisions"]):
                    record = client.records[binding["journal_index"]]
                    self.assertEqual(fingerprint(record), binding["record_sha256"])
                    self.assertEqual(record["observation_sha256"], decision["public_observation_sha256"])

    def test_external_failure_remains_missing_and_all_cells_are_retained(self):
        study = self.root / "study"
        prepare(study)
        def failure(request):
            raise urllib.error.URLError("unit-test-outage")
        client = Client(study / "requests.jsonl", config=self.config, transport=failure)
        result = execute(study, client=client)
        self.assertEqual(result["requests_sent"], 1)
        self.assertEqual(result["primary_trajectories_with_responses"], 0)
        self.assertEqual(result["resolved_triplets"], 0)
        self.assertEqual(result["signatures"], {"??1": 12})
        self.assertEqual(result["executions"], 36)


if __name__ == "__main__":
    unittest.main()
