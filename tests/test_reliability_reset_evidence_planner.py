"""Public evidence coverage, alias fidelity, client namespace and full study replay."""

import copy
import json
import tempfile
import unittest
import urllib.error
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from faultda_bench.semantic.environment import SemanticEnv
from faultda_bench.semantic.policies import choose
from faultda_bench.semantic.tasks import load
from research.reliability_reset.credit_live import Client, MODEL, parse_action
from research.reliability_reset.evidence_planner import (E0_CARDS, INTERFACES, OPAQUE, evidence_plan,
                                                        observed_evidence, plan_reads, public_view)
from research.reliability_reset.planning_mechanism import (Dispatcher, FACTORS, MAX_REQUESTS, PROMPTS,
                                                         RELATION, execute, prepare, preflight, verify)


def response(proposal):
    return {"model": "unit-test-not-a-live-model", "usage": {"prompt_tokens": 100, "completion_tokens": 10, "total_tokens": 110},
            "choices": [{"finish_reason": "stop", "message": {"content": json.dumps(proposal)}}]}


class EvidencePlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.study = self.root / "study"
        self.config = {"DEEPSEEK_API_KEY": "unit-test-mechanism-not-a-real-secret"}
        self.task = next(t for t in load() if t["id"] == "group-03")

    def client(self, transport):
        return Client(self.study / "requests.jsonl", config=self.config, transport=transport, max_calls=MAX_REQUESTS)

    @staticmethod
    def transport(request):
        body = json.loads(request.data)
        view = json.loads(body["messages"][1]["content"])
        mapping = OPAQUE if "query_b" in view["tools"] else INTERFACES["canonical"]
        reverse = {v: k for k, v in mapping.items()}
        canonical = copy.deepcopy(view)
        for event in canonical["history"]:
            event["action"] = reverse[event["action"]]
        policy = "task_semantic" if RELATION in body["messages"][0]["content"] or "read_tool_contracts" in view else "generic_verify"
        proposal = choose(canonical, policy)
        proposal.setdefault("params", {})
        proposal["action"] = mapping[proposal["action"]]
        return response(proposal)

    def test_exact_cover_prefers_lower_byte_plan_and_handles_missing_budget(self):
        cards = {"bundle": {"provides": ["a", "b"], "checks": 2, "estimated_response_bytes": 80},
                 "small_a": {"provides": ["a"], "checks": 1, "estimated_response_bytes": 12},
                 "small_b": {"provides": ["b"], "checks": 1, "estimated_response_bytes": 12}}
        plan = plan_reads(cards, {"a", "b"}, set(), 2)
        self.assertEqual(plan["read_plan"], ["small_a", "small_b"])
        self.assertFalse(plan_reads(cards, {"a", "b"}, set(), 1)["feasible"])
        self.assertEqual(plan_reads(cards, {"a", "b"}, {"a"}, 1)["read_plan"], ["small_b"])
        self.assertEqual(plan_reads(cards, {"a", "b"}, {"a", "b"}, 0)["read_plan"], [])

    def test_planning_depends_on_capabilities_not_names_or_insertion_order(self):
        for replacement in ("opaque_19", "anything", "catalog_is_just_a_name"):
            cards = {replacement if n == "inspect" else "x_" + n: copy.deepcopy(c) for n, c in reversed(list(E0_CARDS.items()))}
            plan = plan_reads(cards, {"active_reports", "input_rows", "version_catalog"}, set(), 1)
            self.assertEqual(plan["read_plan"], [replacement])
        with self.assertRaisesRegex(ValueError, "invalid public tool cost"):
            plan_reads({"bad": {"provides": ["a"], "checks": -1, "estimated_response_bytes": 1}}, {"a"}, set(), 1)

    def test_aliasing_does_not_rewrite_business_payloads(self):
        env = SemanticEnv(self.task, self.root / "env", budget=1)
        obs = env.observation()
        business = {"status": "inspect", "run_id": "catalog", "nested": {"action": "inputs"}}
        obs["history"] = [{"action": "inspect", "params": business, "response": {"ok": True, "records": [business]}}]
        view = public_view(obs, "opaque", structured=True)
        self.assertEqual(view["history"][0]["action"], "query_b")
        self.assertEqual(view["history"][0]["params"], business)
        self.assertEqual(view["history"][0]["response"]["records"], [business])
        self.assertEqual(view["contract"], obs["contract"])
        self.assertEqual(obs["history"][0]["action"], "inspect")
        self.assertEqual(evidence_plan(view)["read_plan"], ["query_b"])

    def test_evidence_is_not_inferred_from_failed_or_write_responses(self):
        data = {"ok": True, "revision": 1, "active_count": 1, "records": [], "versions": {}, "catalog": {}}
        for action, response_data in (("stage", data), ("publish", data), ("inspect", {**data, "ok": False})):
            self.assertEqual(observed_evidence([{"action": action, "response": response_data}], E0_CARDS), set())
        env = SemanticEnv(self.task, self.root / "env", budget=1)
        env.step("inspect")
        view = public_view(env.observation(), "opaque", structured=True)
        self.assertEqual(evidence_plan(view)["read_plan"], [])

    def test_client_strictly_uses_the_advertised_action_namespace(self):
        proposal = {"action": "query_b", "params": {}}
        self.assertIsNone(parse_action(response(proposal), OPAQUE.values())[1])
        self.assertEqual(parse_action(response(proposal))[1], "invalid_model_output")
        self.assertEqual(parse_action(response({"action": "inspect", "params": {}}), OPAQUE.values())[1], "invalid_model_output")

    def test_factorial_and_transfer_design_are_fixed_and_byte_matched(self):
        p = prepare(self.study)
        self.assertEqual(len(p["cells"]), 48)
        self.assertEqual(Counter(c["phase"] for c in p["cells"]), {"factorial": 24, "transfer": 24})
        self.assertEqual(len({len(s.encode()) for s in PROMPTS.values()}), 1)
        self.assertEqual(set(PROMPTS), set(FACTORS))
        self.assertEqual(len(preflight(self.root / "preflight")), 48)

    def test_full_fake_experiment_preserves_namespace_decisions_and_replays(self):
        prepare(self.study)
        summary = execute(self.study, client=self.client(self.transport))
        self.assertEqual(summary["model_executions"], 48)
        self.assertEqual(summary["rule_executions"], 12)
        self.assertEqual(summary["native_exact_agree"], 60)
        self.assertEqual(summary["parse_failures"], 0)
        rows = json.loads((self.study / "runs.json").read_text())
        opaque = next(r for r in rows if r["interface"] == "opaque" and r["arm"] == "auto_plan")
        execution = json.loads((self.study / opaque["evidence"]).read_text())
        self.assertEqual(execution["dispatch"][0]["advertised_proposal"]["action"], "query_b")
        self.assertEqual(execution["decisions"][0]["proposal"]["action"], "inspect")
        self.assertEqual(execution["cost"]["handoff_decisions"], 0)
        with patch("urllib.request.urlopen", side_effect=AssertionError("must not call provider")):
            checks = verify(self.study, self.root / "replay")
        self.assertEqual(checks["model_replays"], 48)
        self.assertEqual(checks["response_classifications"], summary["received_responses"])
        self.assertEqual(checks["new_api_calls"], 0)

    def test_planner_does_not_override_an_unhelpful_model_proposal(self):
        prepare(self.study)
        cell = {"phase": "transfer", "interface": "opaque", "arm": "auto_plan"}
        env = SemanticEnv(self.task, self.root / "env", budget=1)
        client = self.client(lambda request: response({"action": "query_d", "params": {}}))
        dispatcher = Dispatcher(cell, client=client)
        actual = dispatcher(env.observation(), MODEL)
        self.assertEqual(actual, {"action": "status", "params": {}})
        self.assertIn('"query_b"', client.records[0]["request_body"]["messages"][0]["content"])

    def test_provider_outage_retains_planned_cells_as_missing_without_retry(self):
        prepare(self.study)
        def outage(request):
            raise urllib.error.URLError("unit test outage")
        summary = execute(self.study, client=self.client(outage))
        self.assertEqual(summary["requests_sent"], 1)
        self.assertEqual(summary["provider_errors"], 1)
        self.assertEqual(summary["model_executions"], 48)
        self.assertTrue(all(s["resolved"] == 0 for s in summary["strata"] if s["arm"] != "rule_only"))
        self.assertEqual(verify(self.study, self.root / "replay")["model_replays"], 48)


if __name__ == "__main__":
    unittest.main()
