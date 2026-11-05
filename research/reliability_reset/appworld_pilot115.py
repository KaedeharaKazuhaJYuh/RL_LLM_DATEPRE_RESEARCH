"""Run a fresh AppWorld pilot while preserving the SDK's response status.

All task data, requests and responses remain in the caller's local work area.
This adapter does not alter AppWorld's scorer or repair model proposals.
"""

from __future__ import annotations

import argparse
from datetime import timezone
import json
from pathlib import Path

from research.reliability_reset import appworld_pilot195 as pilot


def run(root: Path, experiment: str, task_id: str, provider: str,
        local_python: Path | None = None, local_model: Path | None = None,
        max_steps: int = 16, max_output_tokens: int = 512, max_prompt_bytes: int = 48000,
        preload_public_docs: bool = False, local_max_input_tokens: int | None = None) -> dict:
    root = root.resolve()
    if not experiment.replace("-", "").isalnum():
        raise ValueError("Experiment must be a simple name")
    if min(max_steps, max_output_tokens, max_prompt_bytes) <= 0:
        raise ValueError("Run limits must be positive")
    if local_max_input_tokens is not None and (provider != "local" or local_max_input_tokens <= 0):
        raise ValueError("A positive local input token limit requires the local provider")
    if task_id not in (root / "data/datasets/train.txt").read_text(encoding="utf-8").split():
        raise ValueError("This pilot adapter only supports official train tasks")
    from appworld.requester import Requester
    from freezegun import api as clock

    status_dir = root.parent / "response-status"
    status_dir.mkdir(parents=True, exist_ok=True)
    original = Requester._request
    previous = pilot.MAX_STEPS, pilot.MAX_OUTPUT_TOKENS, pilot.MAX_PROMPT_BYTES, pilot.SYSTEM
    system = pilot.SYSTEM
    if preload_public_docs:
        docs_dir = root / "data/api_docs/standard"
        onboarding = {}
        for app in ("api_docs", "supervisor"):
            docs = json.loads((docs_dir / f"{app}.json").read_text(encoding="utf-8"))
            onboarding[app] = {name: {"description": doc["description"], "parameters": doc["parameters"]}
                               for name, doc in docs.items()}
        system += "\nPublic discovery and supervisor API documentation:\n" + json.dumps(onboarding, ensure_ascii=False)
    with (status_dir / f"{experiment}.jsonl").open("x", encoding="utf-8", newline="\n") as status_log:
        def request_with_status(requester, *args, **kwargs):
            started = clock.real_perf_counter()
            event = {
                "app": kwargs.get("_app_name"), "api": kwargs.get("_api_name"),
                "sdk_track": kwargs.get("track", True),
                "timestamp_utc": clock.real_datetime.now(timezone.utc).isoformat(),
            }
            try:
                response = original(requester, *args, **kwargs)
            except Exception as error:
                event.update({"status_code": None, "exception_type": type(error).__name__})
                raise
            else:
                event.update({"status_code": response.status_code, "response_text": response.text})
                return response
            finally:
                event["seconds"] = clock.real_perf_counter() - started
                status_log.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
                status_log.flush()

        pilot.MAX_STEPS, pilot.MAX_OUTPUT_TOKENS, pilot.MAX_PROMPT_BYTES = max_steps, max_output_tokens, max_prompt_bytes
        pilot.SYSTEM = system
        Requester._request = request_with_status
        try:
            if local_max_input_tokens is not None:
                return pilot.run(root, experiment, task_id, provider, local_python, local_model,
                                 local_max_input_tokens=local_max_input_tokens)
            return pilot.run(root, experiment, task_id, provider, local_python, local_model)
        finally:
            Requester._request = original
            pilot.MAX_STEPS, pilot.MAX_OUTPUT_TOKENS, pilot.MAX_PROMPT_BYTES, pilot.SYSTEM = previous


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--experiment", required=True)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--provider", choices=("deepseek", "local", "noop"), required=True)
    parser.add_argument("--local-python", type=Path)
    parser.add_argument("--local-model", type=Path)
    parser.add_argument("--max-steps", type=int, default=16)
    parser.add_argument("--max-output-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-bytes", type=int, default=48000)
    parser.add_argument("--preload-public-docs", action="store_true")
    parser.add_argument("--local-max-input-tokens", type=int)
    args = parser.parse_args()
    if args.provider == "local" and (args.local_python is None or args.local_model is None):
        parser.error("local provider requires --local-python and --local-model")
    print(json.dumps(run(args.root, args.experiment, args.task_id, args.provider,
                         args.local_python, args.local_model, args.max_steps,
                         args.max_output_tokens, args.max_prompt_bytes, args.preload_public_docs,
                         args.local_max_input_tokens)))


if __name__ == "__main__":
    main()
