"""Verify local Ollama tool-call formatting without executing the returned tool."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:11435")
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument("--seed", type=int, default=231)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    version = json.load(opener.open(f"{base_url}/api/version", timeout=10))
    tags = json.load(opener.open(f"{base_url}/api/tags", timeout=10))
    model = next(model for model in tags["models"] if model["name"] == args.model)

    payload = {
        "model": args.model,
        "think": False,
        "messages": [
            {"role": "system", "content": "Use the available function now. Return no prose."},
            {"role": "user", "content": "Call report_probe exactly once with status ready and count 3."},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "report_probe",
                    "description": "Harmless interface probe. Do not perform external actions.",
                    "parameters": {
                        "type": "object",
                        "properties": {"status": {"type": "string"}, "count": {"type": "integer"}},
                        "required": ["status", "count"],
                    },
                },
            }
        ],
        "stream": False,
        "options": {"temperature": 0, "seed": args.seed, "num_predict": 256, "num_ctx": 2048},
    }

    started = time.perf_counter()
    request = urllib.request.Request(
        f"{base_url}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    response = json.load(opener.open(request, timeout=180))
    elapsed_seconds = time.perf_counter() - started
    calls = response["message"].get("tool_calls", [])
    if len(calls) != 1:
        raise RuntimeError(f"expected one tool call, received {len(calls)}")

    call = calls[0]["function"]
    arguments = call["arguments"]
    if call["name"] != "report_probe" or arguments != {"count": 3, "status": "ready"}:
        raise RuntimeError(f"unexpected tool-call payload: {call!r}")

    running = json.load(opener.open(f"{base_url}/api/ps", timeout=10))["models"]
    loaded = next((item for item in running if item["name"] == args.model), None)
    record = {
        "server_version": version["version"],
        "model": model["name"],
        "model_digest": model["digest"],
        "model_size_bytes": model["size"],
        "tool_call": {"name": call["name"], "arguments": arguments},
        "returned_tool_executed": False,
        "generated_tokens": response["eval_count"],
        "elapsed_seconds": round(elapsed_seconds, 3),
        "gpu_vram_bytes_after_call": loaded["size_vram"] if loaded else None,
        "result": "PASS",
    }
    output = json.dumps(record, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
