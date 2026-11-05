"""Network-free intervention isolation, accounting and replay checks."""

import json
import tempfile
import unittest
import urllib.error
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from faultda_bench.semantic.policies import choose
from research.reliability_reset.credit_live import Client, MODEL, SYSTEM
from research.reliability_reset.tool_planning import (ARMS, MAX_REQUESTS, PROMPTS, TASK_IDS,
                                                      execute, preflight, prepare, verify)


class ToolPlanningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.study = self.root / "study"
        self.config = {"DEEPSEEK_API_KEY": "unit-test-planning-secret"}

    def client(self, transport):
        return Client(self.study / "requests.jsonl", config=self.config, transport=transport, max_calls=MAX_REQUESTS)

    @staticmethod
    def transport(request):
        body = json.loads(request.data)
        observation = json.loads(body["messages"][1]["content"])
        # Test fixture chooses a rule from the prompt; this is not model evidence.
        policy = "task_semantic" if body["messages"][0]["content"] == PROMPTS["budget_guidance"] else "generic_verify"
        proposal = choose(observation, policy)
        proposal.setdefault("params", {})
        return {"model": "unit-test-not-a-live-model", "usage": {"prompt_tokens": 123, "completion_tokens": 9, "total_tokens": 132},
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal)}}]}

    def test_freeze_balances_order_and_preserves_three_arm_inputs(self):
        p = prepare(self.study)
        self.assertEqual(p["model_trajectories"], 36)
        self.assertEqual(p["shared_rule_controls"], 12)
        self.assertEqual({c["task_id"] for c in p["cells"]}, set(TASK_IDS))
        orders = Counter(tuple(c["arm"] for c in p["cells"][i:i + 3]) for i in range(0, 36, 3))
        self.assertEqual(len(orders), 6)
        self.assertEqual(set(orders.values()), {2})
        self.assertEqual(PROMPTS["original"], SYSTEM)
        self.assertEqual(len(PROMPTS["budget_guidance"].encode()), len(PROMPTS["placebo"].encode()))
        for prompt in PROMPTS.values():
            self.assertTrue(prompt.startswith(SYSTEM))
        with self.assertRaisesRegex(ValueError, "destination must be new"):
            prepare(self.study)

    def test_claimed_information_inclusion_is_observed_in_every_state(self):
        checks = preflight(self.root / "preflight")
        self.assertEqual(len(checks), 12)
        for row in checks:
            self.assertTrue(row["status_subset_of_inspect"])
            self.assertGreater(row["inspect_bytes"], row["status_bytes"])
            self.assertEqual(row["model_calls"], 0)

    def test_complete_fake_study_has_no_hidden_help_and_replays_without_network(self):
        prepare(self.study)
        client = self.client(self.transport)
        summary = execute(self.study, client=client)
        self.assertEqual(summary["model_executions"], 36)
        self.assertEqual(summary["rule_executions"], 12)
        self.assertEqual(summary["native_exact_agree"], 48)
        self.assertEqual(summary["parse_failures"], 0)
        rows = json.loads((self.study / "runs.json").read_text())
        for task in TASK_IDS:
            for condition in ("healthy", "semantic_error"):
                paired = [r for r in rows if r["task_id"] == task and r["condition"] == condition]
                self.assertEqual(len({r["public_input_sha256"] for r in paired}), 1)
                self.assertEqual({r["arm"] for r in paired}, {*ARMS, "rule_only"})
        for row in rows:
            execution = json.loads((self.study / row["evidence"]).read_text())
            self.assertEqual(execution["cost"]["handoff_decisions"], 0)
            self.assertLessEqual(execution["cost"]["checks"], 1)
            if row["arm"] != "rule_only":
                self.assertTrue(all(d["actor_kind"] == "model_api" for d in execution["decisions"]))
        with patch("urllib.request.urlopen", side_effect=AssertionError("verification must not send requests")):
            result = verify(self.study, self.root / "replay")
        self.assertEqual(result["model_replays"], 36)
        self.assertEqual(result["response_classifications"], summary["received_responses"])
        self.assertEqual(result["new_api_calls"], 0)

    def test_prompt_tampering_in_journal_cannot_pass_binding_verification(self):
        prepare(self.study)
        execute(self.study, client=self.client(self.transport))
        journal = self.study / "requests.jsonl"
        records = [json.loads(s) for s in journal.read_text().splitlines()]
        records[0]["request_body"]["messages"][0]["content"] = "tampered prompt"
        journal.write_text("\n".join(json.dumps(r) for r in records) + "\n")
        with self.assertRaisesRegex(ValueError, "response binding mismatch"):
            verify(self.study, self.root / "replay")

    def test_external_failure_retains_all_arms_and_separate_rule_controls(self):
        prepare(self.study)
        def outage(request):
            raise urllib.error.URLError("simulated outage")
        summary = execute(self.study, client=self.client(outage))
        self.assertEqual(summary["requests_sent"], 1)
        self.assertEqual(summary["provider_errors"], 1)
        self.assertEqual(summary["model_executions"], 36)
        self.assertTrue(all(s["resolved"] == 0 for s in summary["strata"] if s["arm"] != "rule_only"))
        self.assertTrue(all(s["safe_complete"] == 6 for s in summary["strata"] if s["arm"] == "rule_only"))
        result = verify(self.study, self.root / "replay")
        self.assertEqual(result["model_replays"], 36)

    def test_runtime_code_change_is_rejected_before_transport(self):
        prepare(self.study)
        client = self.client(lambda request: self.fail("must not send"))
        with patch("research.reliability_reset.tool_planning.digest", return_value="0" * 64):
            with self.assertRaisesRegex(ValueError, "code changed"):
                execute(self.study, client=client)
        self.assertEqual(client.calls, 0)


if __name__ == "__main__":
    unittest.main()
