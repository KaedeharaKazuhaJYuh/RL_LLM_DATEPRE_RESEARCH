"""Evidence freshness, receipt support, advisory actions and study replay."""

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
from research.reliability_reset.evidence_planner import INTERFACES, OPAQUE, public_view
from research.reliability_reset.evidence_state import evidence_state, supported_completion
from research.reliability_reset.joint_control import (JointDispatcher, MAX_REQUESTS, assess, effective_task,
                                                     execute, prepare, verify)
from research.reliability_reset.recovery_credit import run


class JointControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.study = self.root / "study"
        self.task = effective_task(next(t for t in load() if t["id"] == "group-03"))
        self.config = {"DEEPSEEK_API_KEY": "unit-test-joint-not-a-real-secret"}

    def env(self, **options):
        return SemanticEnv(self.task, self.root / "env", budget=1, semantic_fault=True, **options)

    def stage_publish(self, env):
        env.step("inspect")
        env.step("stage", {"version": "v1", "deduplicate_keys": True, "closed": "left"})
        env.step("publish", {"stage_id": "1", "request_id": "test-repair", "expected_revision": 1, "mode": "replace"})

    def test_successful_bound_receipt_refreshes_report_and_preserves_input_evidence(self):
        env = self.env()
        self.stage_publish(env)
        state = evidence_state(env.observation())
        self.assertTrue(state["supported_current_report"])
        self.assertFalse(state["unresolved_publication"])
        self.assertEqual(state["current_report_evidence"]["revision"], 2)
        self.assertEqual(state["current_report_evidence"]["source"], "bound_cas_receipt")
        self.assertEqual(state["read_plan"]["read_plan"], [])
        self.assertNotIn("status", state["cost_feasible_actions"])
        self.assertIn("stop", state["cost_feasible_actions"])
        self.assertEqual(state["numerical_correctness"], "not_checked_by_planner")

    def test_receipt_loss_invalidates_report_without_importing_actual_commit_truth(self):
        env = self.env(repair_ack_loss=True)
        self.stage_publish(env)
        state = evidence_state(env.observation())
        self.assertFalse(state["supported_current_report"])
        self.assertTrue(state["unresolved_publication"])
        self.assertIsNone(state["current_report_evidence"])
        self.assertEqual(env.records()[-1]["revision"], 2)  # private truth used in test only
        self.assertFalse(state["read_plan"]["feasible"])
        self.assertIn("input_rows", state["immutable_evidence_fields"])

    def test_unbound_or_revision_mismatched_ack_is_not_a_completion_certificate(self):
        env = self.env()
        self.stage_publish(env)
        for change in ("unknown_stage", "bad_revision"):
            obs = env.observation()
            if change == "unknown_stage":
                obs["history"][-1]["params"]["stage_id"] = "unknown"
            else:
                obs["history"][-1]["response"]["revision"] = 99
            self.assertFalse(evidence_state(obs)["supported_current_report"])

    def test_write_evidence_does_not_assert_semantic_correctness(self):
        # A wrong candidate can be durably published. Original oracle must still reject it.
        def wrong_policy(obs, controller):
            history = obs["history"]
            if not history:return {"action": "inspect", "params": {}}
            if len(history) == 1:return {"action": "stage", "params": {"version": "v1", "deduplicate_keys": False, "closed": "left"}}
            if len(history) == 2:return {"action": "publish", "params": {"stage_id": "1", "request_id": "wrong", "expected_revision": 1, "mode": "replace"}}
            return {"action": "stop", "params": {}}
        e = run(self.task, self.root / "run", "semantic_error", 1, MODEL, dispatcher=wrong_policy)
        self.assertTrue(supported_completion(e)["public_state_supported"])
        self.assertFalse(supported_completion(e)["protocol_complete"])
        self.assertTrue(e["independent_assessment"]["forbidden_effect"])

    def test_unsupported_stop_is_separate_from_original_actual_state_score(self):
        def blind_stop(obs, controller):
            if any(s["action"] == "publish" for s in obs["history"]):return {"action": "stop", "params": {}}
            return choose(obs, "task_semantic")
        e = run(self.task, self.root / "run", "semantic_error", 1, MODEL, dispatcher=blind_stop,
                environment_options={"repair_ack_loss": True})
        self.assertTrue(e["native_result"]["safe_complete"])
        self.assertTrue(e["independent_assessment"]["safe_complete"])
        self.assertTrue(assess(e)["unsupported_stop"])
        self.assertFalse(assess(e)["protocol_complete"])

    def test_alias_support_and_budget_actions_preserve_business_data(self):
        env = self.env()
        self.stage_publish(env)
        view = public_view(env.observation(), "opaque", structured=True)
        state = evidence_state(view, "opaque")
        self.assertEqual(state["current_report_evidence"], evidence_state(env.observation())["current_report_evidence"])
        self.assertNotIn("query_b", state["cost_feasible_actions"])
        self.assertNotIn("query_d", state["cost_feasible_actions"])
        self.assertIn("publish", state["cost_feasible_actions"])

    def test_reconciliation_and_later_revision_change_refresh_and_invalidate_cache(self):
        env = self.env(repair_ack_loss=True)
        self.stage_publish(env)
        obs = env.observation()
        # Synthetic public reconciliation response, not an extra real budgeted read.
        receipt = {"action": "inspect", "params": {}, "response": {"ok": True, "revision": 2, "active_count": 1, "records": env.records()}}
        obs["history"].append(receipt)
        self.assertTrue(evidence_state(obs)["supported_current_report"])
        obs["history"].append({"action": "status", "params": {}, "response": {"ok": True, "revision": 3, "active_count": 1}})
        self.assertFalse(evidence_state(obs)["supported_current_report"])

    @staticmethod
    def transport(request):
        body = json.loads(request.data)
        view = json.loads(body["messages"][1]["content"])
        mapping = OPAQUE if "query_b" in view["tools"] else INTERFACES["canonical"]
        reverse = {v: k for k, v in mapping.items()}
        obs = copy.deepcopy(view)
        for step in obs["history"]:step["action"] = reverse[step["action"]]
        proposal = choose(obs, "task_semantic")
        proposal.setdefault("params", {})
        proposal["action"] = mapping[proposal["action"]]
        return {"model": "unit-test-not-live", "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
                "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal)}}]}

    def test_full_fake_design_uses_same_effective_contract_and_replays(self):
        p = prepare(self.study)
        self.assertEqual(len(p["cells"]), 54)
        client = Client(self.study / "requests.jsonl", config=self.config, transport=self.transport, max_calls=MAX_REQUESTS)
        summary = execute(self.study, client=client)
        self.assertEqual(summary["model_executions"], 54)
        self.assertEqual(summary["backend_rule_controls"], 9)
        self.assertEqual(summary["native_exact_agree"], 63)
        self.assertEqual(summary["parse_failures"], 0)
        self.assertTrue(all(s["unsupported_stop"] == 0 for s in summary["strata"]))
        rows = json.loads((self.study / "runs.json").read_text())
        hashes = {}
        for r in rows:hashes.setdefault((r["task_id"],r["variant"]),set()).add(r["public_input_sha256"])
        self.assertTrue(all(len(v) == 1 for v in hashes.values()))
        with patch("urllib.request.urlopen", side_effect=AssertionError("must not send")):
            checked = verify(self.study, self.root / "replay")
        self.assertEqual(checked["model_replays"], 54)
        self.assertEqual(checked["response_classifications"], summary["received_responses"])

    def test_joint_suggestions_do_not_replace_model_choice_or_force_stop(self):
        env = self.env()
        self.stage_publish(env)
        cell = {"phase": "joint", "interface": "canonical", "arm": "joint_plan"}
        def transport(request):
            return {"choices": [{"finish_reason": "stop", "message": {"content": '{"action":"status","params":{}}'}}]}
        client = Client(self.root / "requests.jsonl", config=self.config, transport=transport)
        actual = JointDispatcher(cell, client=client)(env.observation(), MODEL)
        self.assertEqual(actual["action"], "status")
        self.assertNotIn("status", json.loads(client.records[0]["request_body"]["messages"][1]["content"])["decision_support"]["cost_feasible_actions"])


if __name__ == "__main__":
    unittest.main()
