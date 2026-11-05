"""Budget projection preserves proposals, aliases, uncertainty and replay evidence."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from faultda_bench.semantic.environment import SemanticEnv
from faultda_bench.semantic.policies import choose
from faultda_bench.semantic.tasks import load
from research.reliability_reset.credit_live import Client, MODEL
from research.reliability_reset.evidence_planner import E0_CARDS, INTERFACES
from research.reliability_reset.feasible_interface import (ARMS, MAX_REQUESTS, FeasibleDispatcher, diagnostics,
                                                         effective_task, execute, prepare, presentation, verify)
from research.reliability_reset.recovery_credit import run


class FeasibleInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.task = effective_task(next(t for t in load() if t["id"] == "group-03"))
        self.config = {"DEEPSEEK_API_KEY": "unit-test-feasible-not-a-real-secret"}

    def observation(self):
        env = SemanticEnv(self.task, self.root / "env", budget=1, semantic_fault=True, repair_ack_loss=True)
        env.step("inspect")
        env.step("stage", {"version": "v1", "deduplicate_keys": True, "closed": "left"})
        env.step("publish", {"stage_id": "1", "request_id": "lost", "expected_revision": 1, "mode": "replace"})
        return env.observation()

    def test_identical_text_raw_history_and_state_with_only_registry_enum_projection(self):
        obs = self.observation()
        before = copy.deepcopy(obs)
        text, tp = presentation(obs, "canonical", "matched_text")
        soft, sp = presentation(obs, "canonical", "soft_joint")
        projected, pp = presentation(obs, "canonical", "feasible_tools")
        self.assertEqual(tp, sp)
        self.assertEqual(sp, pp)
        self.assertEqual(obs, before)
        self.assertEqual(text["history"], soft["history"])
        self.assertEqual(soft["history"], projected["history"])
        self.assertEqual(soft["decision_support"], projected["decision_support"])
        self.assertEqual(soft["read_tool_contracts"], projected["read_tool_contracts"])
        self.assertNotIn("decision_support", text)
        self.assertTrue(projected["decision_support"]["unresolved_publication"])
        self.assertFalse(projected["decision_support"]["supported_current_report"])
        self.assertTrue(set(E0_CARDS) <= set(soft["tools"]))
        self.assertFalse(set(E0_CARDS) & set(projected["tools"]))
        self.assertEqual(set(projected["tools"]), {"stage", "publish", "stop", "escalate"})
        self.assertEqual(projected["action_schema"]["properties"]["action"]["enum"], list(projected["tools"]))

    def test_alias_projection_changes_only_tool_envelopes_and_preserves_candidates(self):
        obs = self.observation()
        view, _ = presentation(obs, "opaque", "feasible_tools")
        self.assertEqual(view["history"][0]["action"], "query_b")
        self.assertEqual(view["history"][0]["response"], obs["history"][0]["response"])
        self.assertEqual(view["history"][1]["params"], obs["history"][1]["params"])
        self.assertEqual(view["history"][1]["response"], obs["history"][1]["response"])
        self.assertFalse(any(n.startswith("query_") for n in view["tools"]))

    def test_zero_mutation_budget_removes_writes_but_not_terminal_choice(self):
        obs = self.observation()
        obs["remaining"]["mutations"] = 0
        view, _ = presentation(obs, "canonical", "feasible_tools")
        self.assertEqual(set(view["tools"]), {"stop", "escalate"})

    def test_initial_budget_keeps_every_tool_and_schema_in_all_arms(self):
        env = SemanticEnv(self.task, self.root / "env", budget=1)
        for arm in ARMS:
            view, _ = presentation(env.observation(), "opaque", arm)
            self.assertEqual(set(view["tools"]), set(INTERFACES["opaque"].values()))

    def test_excluded_proposal_is_not_repaired_and_original_budget_rejection_is_retained(self):
        def transport(request):
            view = json.loads(json.loads(request.data)["messages"][1]["content"])
            action = "query_b" if not view["history"] else "query_d"
            return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"action": action, "params": {}})}}]}
        client = Client(self.root / "requests.jsonl", config=self.config, transport=transport)
        dispatcher = FeasibleDispatcher({"arm": "feasible_tools", "interface": "opaque"}, client=client)
        result = run(self.task, self.root / "run", "semantic_error", 1, MODEL, dispatcher=dispatcher)
        self.assertEqual(result["terminal"], "budget_exceeded")
        self.assertEqual(result["decisions"][-1]["proposal"]["action"], "status")
        self.assertEqual(result["cost"]["checks"], 1)
        self.assertEqual(client.calls, 2)
        self.assertEqual(client.records[-1]["parse_error"], None)
        extra = diagnostics(result, client.records)
        self.assertEqual(len(extra["excluded_action_attempts"]), 1)
        self.assertEqual(extra["excluded_action_attempts"][0]["proposal"]["action"], "query_d")
        self.assertTrue(extra["rejected_read"])
        self.assertFalse(extra["protocol_complete"])

    @staticmethod
    def transport(request):
        view = json.loads(json.loads(request.data)["messages"][1]["content"])
        mapping = INTERFACES["opaque"] if "query_b" in view["read_tool_contracts"] else INTERFACES["canonical"]
        reverse = {v: k for k, v in mapping.items()}
        obs = copy.deepcopy(view)
        for event in obs["history"]:
            event["action"] = reverse[event["action"]]
        proposal = choose(obs, "task_semantic")
        proposal.setdefault("params", {})
        proposal["action"] = mapping[proposal["action"]]
        return {"model": "unit-test-not-live", "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal)}}]}

    def test_full_fake_design_replays_all_models_rules_and_request_classifications(self):
        folder = self.root / "study"
        protocol = prepare(folder)
        self.assertEqual(len(protocol["cells"]), 54)
        client = Client(folder / "requests.jsonl", config=self.config, transport=self.transport, max_calls=MAX_REQUESTS)
        summary = execute(folder, client=client)
        self.assertEqual(summary["model_executions"], 54)
        self.assertEqual(summary["backend_rule_controls"], 9)
        self.assertEqual(summary["native_exact_agree"], 63)
        self.assertEqual(summary["parse_failures"], 0)
        self.assertTrue(all(s["rejected_read"] == 0 and s["unsupported_stop"] == 0 for s in summary["strata"]))
        rows = json.loads((folder / "runs.json").read_text())
        hashes = {}
        for r in rows:
            hashes.setdefault((r["task_id"], r["variant"]), set()).add(r["public_input_sha256"])
        self.assertTrue(all(len(v) == 1 for v in hashes.values()))
        with patch("urllib.request.urlopen", side_effect=AssertionError("must not send")):
            checked = verify(folder, self.root / "replay")
        self.assertEqual(checked["model_replays"], 54)
        self.assertEqual(checked["backend_rule_replays"], 9)
        self.assertEqual(checked["response_classifications"], summary["received_responses"])
        self.assertEqual(checked["new_api_calls"], 0)
        # Indexed resource totals must be recomputed from bound provider evidence.
        rows[0]["requests"] += 1
        (folder / "runs.json").write_text(json.dumps(rows))
        with self.assertRaisesRegex(ValueError, "cost index changed"):
            verify(folder, self.root / "tampered")

    def test_protocol_prompt_or_budget_mutation_is_rejected_before_network(self):
        folder = self.root / "study"
        protocol = prepare(folder)
        protocol["shared_caps"]["checks"] = 2
        (folder / "protocol.json").write_text(json.dumps(protocol))
        with patch("urllib.request.urlopen", side_effect=AssertionError("must not send")):
            with self.assertRaisesRegex(ValueError, "protocol/source/input changed"):
                execute(folder)


if __name__ == "__main__":
    unittest.main()
