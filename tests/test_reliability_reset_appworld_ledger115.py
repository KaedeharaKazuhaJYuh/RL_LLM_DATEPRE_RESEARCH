import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from research.reliability_reset.appworld_ledger115 import export
from research.reliability_reset.appworld_replay115 import replay


class LedgerTests(unittest.TestCase):
    def test_export_keeps_costs_censoring_and_incomplete_calls_without_payloads(self):
        manifest = {"version": "1.1.05", "attempts": [
            {"arm": "test", "task": 1, "attempt": "one", "role": "primary"},
            {"arm": "test", "task": 2, "attempt": "two", "role": "primary"},
        ]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("one", "two"):
                (root / "journals" / name).mkdir(parents=True)
            (root / "response-status").mkdir()
            events = [
                {"kind": "model_request", "step": 1, "prompt_bytes": 20, "messages": "private-prompt"},
                {"kind": "model", "step": 1, "status": "received", "content": "private-response",
                 "usage": {"prompt_tokens": 10, "completion_tokens": 5},
                 "peak_estimate_usd": 0.00001, "seconds": 1.5},
                {"kind": "tool", "step": 1, "observation": {"returned": "private-tool"}, "seconds": 0.1},
                {"kind": "model_request", "step": 2, "prompt_bytes": 40},
                {"kind": "controller_stop", "step": 2, "reason": "input_token_limit",
                 "input_tokens": 2001, "input_token_limit": 2000},
                {"kind": "final", "termination": "input_token_limit", "native_success": False,
                 "native_tests_passed": 0, "native_tests_total": 1, "safety_judgment": "unknown"},
            ]
            (root / "journals/one/events.jsonl").write_text(
                "\n".join(json.dumps(row) for row in events) + "\n{truncated", encoding="utf8")
            (root / "journals/two/events.jsonl").write_text(
                json.dumps({"kind": "model_request", "step": 1}) + "\n", encoding="utf8")
            status = {"app": "supervisor", "api": "show_active_task", "sdk_track": False,
                      "status_code": 200, "seconds": 0.2,
                      "response_text": json.dumps({"status": "success", "secret": "private-status"})}
            (root / "response-status/one.jsonl").write_text(json.dumps(status) + "\n", encoding="utf8")
            summary, ledger = export(root, manifest)
        first, second = summary["cases"]
        self.assertEqual(first["model_statuses"], {"received": 1, "input_token_limit": 1})
        self.assertEqual((first["known_peak_estimate_usd"], first["malformed_journal_lines"]), (0.00001, 1))
        self.assertEqual(first["supervisor_status"], "success")
        self.assertEqual((second["termination"], second["model_statuses"]), ("interrupted", {"unresolved": 1}))
        self.assertEqual(summary["arms"]["test"]["primary_resource_censored"], 1)
        serialized = json.dumps([summary, ledger])
        for secret in ("private-prompt", "private-response", "private-tool", "private-status"):
            self.assertNotIn(secret, serialized)
        guard = next(row for row in ledger if row["channel"] == "model" and row["status"] == "input_token_limit")
        self.assertEqual((guard["input_tokens"], guard["input_token_limit"]), (2001, 2000))

    def test_native_replay_compares_recorded_score_and_hides_child_output(self):
        manifest = {"attempts": [{"attempt": "one", "task": 1}]}
        native = {"attempt": "one", "source_files_checked": 5, "success": False,
                  "passed": 4, "failed": 1, "total": 5}
        child = SimpleNamespace(returncode=0, stdout="private output\nREPLAY115=" + json.dumps(native) + "\n")
        with tempfile.TemporaryDirectory() as directory, \
             patch("research.reliability_reset.appworld_replay115.subprocess.run", return_value=child) as run:
            root = Path(directory)
            (root / "journals/one").mkdir(parents=True)
            final = {"kind": "final", "native_success": False, "native_tests_passed": 4,
                     "native_tests_failed": 1, "native_tests_total": 5}
            (root / "journals/one/events.jsonl").write_text(json.dumps(final) + "\n", encoding="utf8")
            report = replay(root, Path("python"), manifest, ["one"])
        self.assertTrue(report["results"][0]["matches_recorded"])
        self.assertTrue(report["separate_process_per_attempt"])
        self.assertNotIn("private output", json.dumps(report))
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
