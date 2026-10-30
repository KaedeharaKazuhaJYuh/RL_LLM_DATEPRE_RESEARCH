"""Bounded, structured API pilot on a local AppWorld train task.

Raw task data, simulated credentials and model/tool responses belong in work/.
Neither model is allowed to execute generated Python.
"""

from __future__ import annotations

import argparse
from datetime import timezone
from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import subprocess
import urllib.error
import urllib.request

SYSTEM = """You are an assistant solving a user's task using AppWorld APIs.
At every turn return only one JSON object. To call an API, return
{"type":"call","app":"app_name","api":"api_name","arguments":{...}}.
To end without claiming completion return {"type":"stop"} or {"type":"escalate"}.
App names and descriptions are supplied. Use api_docs.show_api_descriptions
and api_docs.show_api_doc to discover exact API names and parameters; the
supervisor app can provide account information. Use only observed values.
To complete the task use supervisor.complete_task, supplying an answer if needed.
Every proposal consumes one turn; API errors and rejected proposals remain visible.
Do not output Python code or extra text."""
MAX_STEPS = 8
MAX_OUTPUT_TOKENS = 256
MAX_PROMPT_BYTES = 24000
PEAK_PRICE = {"cache_hit": 0.006, "cache_miss": 0.30, "output": 1.20}
MODEL = "deepseek-flash"


def parse_proposal(content: str) -> dict:
    """Parse the model's proposal without filling fields or repairing JSON."""
    if not isinstance(content, str):
        raise ValueError("Model response is not text")
    content = content.strip()
    if content.startswith("<think>") and "</think>" in content:
        content = content.split("</think>", 1)[1].strip()
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key")
            result[key] = value
        return result
    value = json.loads(content, object_pairs_hook=unique)
    if not isinstance(value, dict) or value.get("type") not in ("call", "stop", "escalate"):
        raise ValueError("Expected a call, stop or escalate object")
    if value["type"] in ("stop", "escalate"):
        if set(value) != {"type"}:
            raise ValueError("Terminal proposal has extra fields")
    elif set(value) != {"type", "app", "api", "arguments"} or not all(
        isinstance(value[k], str) for k in ("app", "api")
    ) or not isinstance(value["arguments"], dict):
        raise ValueError("Call proposal does not match the interface")
    return value


def check_call(proposal: dict, docs: dict) -> str | None:
    """Validate the API boundary; never add missing arguments."""
    app, api, args = proposal["app"], proposal["api"], proposal["arguments"]
    if app not in docs or api not in docs[app]:
        return "unknown_api"
    parameters = docs[app][api].get("parameters", [])
    allowed = {p["name"] for p in parameters}
    required = {p["name"] for p in parameters if p.get("required")}
    if set(args) - allowed:
        return "unknown_argument"
    if required - set(args):
        return "missing_required_argument"
    return None


def peak_cost(usage: dict) -> float | None:
    """Peak-rate estimate from provider-reported token usage, not an invoice."""
    hit = usage.get("prompt_cache_hit_tokens")
    miss = usage.get("prompt_cache_miss_tokens")
    output = usage.get("completion_tokens")
    if any(type(value) is not int or value < 0 for value in (hit, miss, output)):
        return None
    if usage.get("prompt_tokens") != hit + miss or usage.get("total_tokens") != hit + miss + output:
        return None
    return (hit * PEAK_PRICE["cache_hit"] + miss * PEAK_PRICE["cache_miss"] +
            output * PEAK_PRICE["output"]) / 1_000_000


class DeepSeek:
    def __init__(self):
        # Load the shared config without importing agent/__init__, which requires NumPy.
        config_path = Path(__file__).resolve().parents[2] / "agent" / "deepseek_config.py"
        spec = spec_from_file_location("project_deepseek_config", config_path)
        config = module_from_spec(spec)
        spec.loader.exec_module(config)
        self.key = config.settings().get("DEEPSEEK_API_KEY", "").strip()
        if not self.key or self.key in ("replace_with_your_key", "your_key", "YOUR_API_KEY"):
            raise ValueError("DeepSeek credential is not configured")

    def request(self, messages):
        from freezegun import api as clock

        body = {"model": MODEL, "temperature": 0, "thinking": {"type": "disabled"},
                "max_tokens": MAX_OUTPUT_TOKENS, "response_format": {"type": "json_object"},
                "messages": messages}
        request = urllib.request.Request(
            "https://api.deepseek.com/chat/completions", data=json.dumps(body, ensure_ascii=False).encode("utf8"),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key}, method="POST")
        started = clock.real_perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                answer = json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            detail = None
            if isinstance(error, urllib.error.HTTPError):
                detail = error.read(8192).decode("utf8", errors="replace").replace(self.key, "[REDACTED]")
            return {"status": "provider_error", "error_type": type(error).__name__,
                    "http_status": getattr(error, "code", None), "error_body": detail,
                    "seconds": clock.real_perf_counter() - started}
        usage = answer.get("usage", {})
        choices = answer.get("choices", [])
        return {"status": "received", "content": choices[0].get("message", {}).get("content") if choices else None,
                "finish_reason": choices[0].get("finish_reason") if choices else None,
                "response_id": answer.get("id"), "reported_model": answer.get("model"),
                "system_fingerprint": answer.get("system_fingerprint"), "usage": usage,
                "provider_response": answer, "peak_estimate_usd": peak_cost(usage),
                "seconds": clock.real_perf_counter() - started}


class LocalModel:
    def __init__(self, executable: Path, model_path: Path, error_path: Path):
        self.errors = error_path.open("x", encoding="utf8")
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.worker = subprocess.Popen(
            [str(executable), "-m", "research.reliability_reset.local_worker195", str(model_path)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.errors, text=True, encoding="utf8",
            creationflags=flags)
        ready = json.loads(self.worker.stdout.readline())
        if not ready.get("ready") or not ready.get("device", "").startswith("cuda"):
            raise RuntimeError("Local CUDA worker did not become ready")

    def request(self, messages):
        self.worker.stdin.write(json.dumps({"messages": messages, "max_tokens": MAX_OUTPUT_TOKENS}) + "\n")
        self.worker.stdin.flush()
        line = self.worker.stdout.readline()
        if not line:
            return {"status": "provider_error", "error_type": "local_worker_stopped"}
        return {"status": "received", **json.loads(line), "peak_estimate_usd": None,
                "provider_charge": None}

    def close(self):
        self.worker.stdin.close()
        self.worker.wait(timeout=30)
        self.errors.close()


def run(root: Path, experiment: str, task_id: str, provider: str, local_python: Path | None = None,
        local_model: Path | None = None) -> dict:
    """Run one fresh task; the original task and evaluator are unchanged."""
    from appworld import AppWorld, update_root
    from freezegun import api as clock

    root = root.resolve()
    output = root / "experiments" / "outputs" / experiment
    if output.exists() or not experiment.replace("-", "").isalnum():
        raise ValueError("Experiment must be a fresh simple name")
    log_dir = root.parent / "journals" / experiment
    log_dir.mkdir(parents=True, exist_ok=False)
    client = DeepSeek() if provider == "deepseek" else (
        LocalModel(local_python.resolve(), local_model.resolve(), log_dir / "worker-stderr.txt")
        if provider == "local" else None)
    docs_dir = root / "data" / "api_docs" / "standard"
    docs = {path.stem: json.loads(path.read_text(encoding="utf8")) for path in docs_dir.glob("*.json")}
    journal = (log_dir / "events.jsonl").open("x", encoding="utf8", newline="\n")

    def record(event):
        journal.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        journal.flush()

    try:
        update_root(str(root))
        with AppWorld(task_id=task_id, experiment_name=experiment, load_ground_truth=True,
                      ground_truth_mode="full", raise_on_failure=False) as world:
            user = world.task.supervisor
            context = {"task": world.task.instruction, "apps": world.task.app_descriptions,
                       "supervisor": {key: getattr(user, key) for key in ("first_name", "last_name", "email", "phone_number")},
                       "max_turns": MAX_STEPS}
            history = []
            termination = "no_action" if provider == "noop" else "step_limit"
            model_calls = 0
            for step in range(MAX_STEPS if client else 0):
                messages = [{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": json.dumps({**context, "turns": history, "turn": step + 1},
                                                                   ensure_ascii=False, default=str)}]
                prompt_bytes = len(json.dumps(messages, ensure_ascii=False).encode("utf8"))
                if prompt_bytes > MAX_PROMPT_BYTES:
                    termination = "prompt_limit"
                    record({"kind": "controller_stop", "reason": termination, "prompt_bytes": prompt_bytes})
                    break
                record({"kind": "model_request", "step": step + 1,
                        "timestamp_utc": clock.real_datetime.now(timezone.utc).isoformat(), "messages": messages,
                        "prompt_bytes": prompt_bytes, "max_output_tokens": MAX_OUTPUT_TOKENS})
                result = client.request(messages)
                model_calls += 1
                record({"kind": "model", "step": step + 1, "timestamp_utc": clock.real_datetime.now(timezone.utc).isoformat(),
                        "prompt_bytes": prompt_bytes, **result})
                if result["status"] != "received":
                    termination = "provider_error"
                    break
                if result.get("finish_reason") != "stop":
                    observation = {"error": "unfinished_model_output"}
                    history.append({"raw_proposal": result.get("content"), "observation": observation})
                    record({"kind": "rejection", "step": step + 1, **observation})
                    continue
                try:
                    proposal = parse_proposal(result.get("content") or "")
                except (ValueError, TypeError):
                    observation = {"error": "invalid_model_output"}
                    history.append({"raw_proposal": result.get("content"), "observation": observation})
                    record({"kind": "rejection", "step": step + 1, **observation})
                    continue
                if proposal["type"] != "call":
                    termination = proposal["type"]
                    record({"kind": "terminal", "step": step + 1, "proposal": proposal})
                    break
                reason = check_call(proposal, docs)
                if reason:
                    observation = {"error": reason}
                    record({"kind": "rejection", "step": step + 1, "proposal": proposal, **observation})
                else:
                    tool_started_utc = clock.real_datetime.now(timezone.utc).isoformat()
                    started = clock.real_perf_counter()
                    try:
                        response = world.apis[proposal["app"]][proposal["api"]](**proposal["arguments"])
                        observation = {"returned": response}
                    except Exception as error:
                        # The external tool can reject an otherwise well-formed proposal.
                        observation = {"error": type(error).__name__, "message": str(error)}
                    record({"kind": "tool", "step": step + 1, "proposal": proposal,
                            "timestamp_utc": tool_started_utc, "observation": observation,
                            "seconds": clock.real_perf_counter() - started})
                    world.save()
                history.append({"proposal": proposal, "observation": observation})
                completed = world.task_completed()
                record({"kind": "completion_probe", "step": step + 1, "task_completed": completed})
                if completed:
                    termination = "task_completed_signal"
                    break
            world.save()
            score = world.evaluate(suppress_errors=True)
            result = {"provider": provider, "task_split": "train", "termination": termination,
                      "model_calls": model_calls, "recorded_tool_requests": len(world.requester.request_tracker.requests),
                      "task_completed_signal": world.task_completed(), "native_success": score.success,
                      "native_tests_passed": score.pass_count, "native_tests_failed": score.fail_count,
                      "native_tests_total": score.num_tests, "safety_judgment": "unknown"}
            record({"kind": "final", **result})
    finally:
        journal.close()
        if isinstance(client, LocalModel):
            client.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--provider", choices=("deepseek", "local", "noop"), required=True)
    parser.add_argument("--local-python", type=Path)
    parser.add_argument("--local-model", type=Path)
    args = parser.parse_args()
    if args.provider == "local" and (args.local_python is None or args.local_model is None):
        parser.error("local provider requires --local-python and --local-model")
    print(json.dumps(run(args.root, args.experiment, args.task_id, args.provider, args.local_python, args.local_model)))


if __name__ == "__main__":
    main()
