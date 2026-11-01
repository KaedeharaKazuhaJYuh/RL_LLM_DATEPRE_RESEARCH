import json
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from research.reliability_reset import appworld_pilot115 as adapter


class StatusCaptureTests(unittest.TestCase):
    def test_records_native_response_without_changing_it_and_restores_requester(self):
        responses = [SimpleNamespace(status_code=200, text='{"ok":true}'),
                     SimpleNamespace(status_code=422, text='{"detail":"invalid"}')]

        class Requester:
            def _request(self, **kwargs):
                return responses.pop(0)

        appworld = ModuleType("appworld")
        requester_module = ModuleType("appworld.requester")
        requester_module.Requester = Requester
        clock = SimpleNamespace(real_perf_counter=lambda: 1.0,
                                real_datetime=__import__('datetime').datetime)
        original = Requester._request
        previous = (adapter.pilot.MAX_STEPS, adapter.pilot.MAX_OUTPUT_TOKENS, adapter.pilot.MAX_PROMPT_BYTES)

        def fake_run(*args):
            requester = Requester()
            first = requester._request(_app_name="a", _api_name="read", track=True)
            second = requester._request(_app_name="a", _api_name="write", track=False)
            self.assertEqual((first.status_code, second.status_code), (200, 422))
            return {"ok": True}

        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(sys.modules, {"appworld": appworld, "appworld.requester": requester_module,
                                      "freezegun": SimpleNamespace(api=clock)}), \
             patch.object(adapter.pilot, "run", side_effect=fake_run):
            dataset = Path(directory) / "root/data/datasets"
            dataset.mkdir(parents=True)
            (dataset / "train.txt").write_text("task\n", encoding="utf-8")
            result = adapter.run(Path(directory) / "root", "case-1", "task", "noop")
            records = [json.loads(line) for line in
                       (Path(directory) / "response-status/case-1.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(result, {"ok": True})
        self.assertEqual([(r["sdk_track"], r["status_code"]) for r in records], [(True, 200), (False, 422)])
        self.assertEqual(records[1]["response_text"], '{"detail":"invalid"}')
        self.assertIs(Requester._request, original)
        self.assertEqual((adapter.pilot.MAX_STEPS, adapter.pilot.MAX_OUTPUT_TOKENS,
                          adapter.pilot.MAX_PROMPT_BYTES), previous)

    def test_invalid_experiment_name_is_rejected_before_file_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                adapter.run(Path(directory) / "root", "../outside", "task", "noop")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_dev_task_cannot_be_mislabeled_as_train(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "root"
            dataset = root / "data/datasets"
            dataset.mkdir(parents=True)
            (dataset / "train.txt").write_text("train-task\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "only supports official train"):
                adapter.run(root, "case-2", "dev-task", "noop")
            self.assertFalse((Path(directory) / "response-status").exists())

    def test_local_token_limit_is_forwarded_only_for_local_runs(self):
        appworld = ModuleType("appworld")
        requester_module = ModuleType("appworld.requester")
        requester_module.Requester = type("Requester", (), {"_request": lambda self: None})
        clock = SimpleNamespace(real_perf_counter=lambda: 1.0,
                                real_datetime=__import__('datetime').datetime)
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(sys.modules, {"appworld": appworld, "appworld.requester": requester_module,
                                      "freezegun": SimpleNamespace(api=clock)}), \
             patch.object(adapter.pilot, "run", return_value={"ok": True}) as run:
            root = Path(directory) / "root"
            dataset = root / "data/datasets"
            dataset.mkdir(parents=True)
            (dataset / "train.txt").write_text("task\n", encoding="utf-8")
            adapter.run(root, "local-cap", "task", "local", Path("python"), Path("model"),
                        local_max_input_tokens=2000)
            self.assertEqual(run.call_args.kwargs, {"local_max_input_tokens": 2000})
            with self.assertRaisesRegex(ValueError, "requires the local provider"):
                adapter.run(root, "bad-cap", "task", "deepseek", local_max_input_tokens=2000)

    def test_worker_refuses_large_prompt_before_transferring_inputs_to_cuda(self):
        class Inputs(dict):
            def to(self, device):
                raise AssertionError("oversized inputs must stay on CPU")

        class Tokenizer:
            eos_token_id = 0

            def apply_chat_template(self, *args, **kwargs):
                return "prompt"

            def __call__(self, *args, **kwargs):
                return Inputs(input_ids=SimpleNamespace(shape=(1, 2001)))

        class Model:
            def to(self, device):
                return self

            def eval(self):
                return self

            def parameters(self):
                return iter([SimpleNamespace(device="cuda:0")])

            def generate(self, **kwargs):
                raise AssertionError("oversized inputs must not generate")

        torch = ModuleType("torch")
        torch.float16 = object()
        transformers = ModuleType("transformers")
        transformers.AutoTokenizer = SimpleNamespace(from_pretrained=lambda *a, **k: Tokenizer())
        transformers.AutoModelForCausalLM = SimpleNamespace(from_pretrained=lambda *a, **k: Model())
        transformers.logging = SimpleNamespace(set_verbosity_error=lambda: None, disable_progress_bar=lambda: None)
        source = Path(adapter.__file__).with_name("local_worker195.py")
        spec = importlib.util.spec_from_file_location("local_worker_guard_test", source)
        worker = importlib.util.module_from_spec(spec)
        output = io.StringIO()
        with patch.dict(sys.modules, {"torch": torch, "transformers": transformers}), \
             patch.object(sys, "argv", [str(source), "model", "2000"]), \
             patch.object(sys, "stdin", io.StringIO('{"messages": [], "max_tokens": 512}\n')), \
             patch.object(sys, "stdout", output):
            spec.loader.exec_module(worker)
            worker.main()
        ready, blocked = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertTrue(ready["ready"])
        self.assertEqual((blocked["status"], blocked["input_tokens"], blocked["input_token_limit"]),
                         ("input_token_limit", 2001, 2000))

    def test_controller_records_cap_without_counting_a_model_call(self):
        class Client:
            def __init__(self, *args):
                pass

            def request(self, messages):
                return {"status": "input_token_limit", "error_type": "input_token_limit",
                        "input_tokens": 2001, "input_token_limit": 2000}

            def close(self):
                pass

        class World:
            def __init__(self, **kwargs):
                self.task = SimpleNamespace(supervisor=SimpleNamespace(first_name="A", last_name="B",
                                                                       email="a@example.test", phone_number="0"),
                                            instruction="task", app_descriptions={})
                self.requester = SimpleNamespace(request_tracker=SimpleNamespace(requests=[]))

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def save(self):
                pass

            def task_completed(self):
                return False

            def evaluate(self, **kwargs):
                return SimpleNamespace(success=False, pass_count=0, fail_count=1, num_tests=1)

        appworld = ModuleType("appworld")
        appworld.AppWorld = World
        appworld.update_root = lambda root: None
        clock = SimpleNamespace(real_datetime=__import__('datetime').datetime)
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(sys.modules, {"appworld": appworld, "freezegun": SimpleNamespace(api=clock)}), \
             patch.object(adapter.pilot, "LocalModel", Client):
            root = Path(directory) / "root"
            (root / "data/api_docs/standard").mkdir(parents=True)
            result = adapter.pilot.run(root, "guarded", "task", "local", Path("python"), Path("model"), 2000)
            events = [json.loads(line) for line in
                      (Path(directory) / "journals/guarded/events.jsonl").read_text(encoding="utf8").splitlines()]
        self.assertEqual((result["termination"], result["model_calls"]), ("input_token_limit", 0))
        self.assertEqual([event["kind"] for event in events], ["model_request", "controller_stop", "final"])
        self.assertEqual(events[1]["input_tokens"], 2001)


if __name__ == "__main__":
    unittest.main()
