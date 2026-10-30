"""Bounded DeepSeek primary trajectories with exact-prefix helper counterfactuals."""

import argparse
import copy
import json
import random
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from agent.deepseek_config import credential_present, settings
from faultda_bench.semantic.environment import TOOLS
from faultda_bench.semantic.tasks import load, MANIFEST, REPO

from . import __version__
from .audit import digest, require
from .recovery_credit import ControllerStop, fingerprint, run, save


SYSTEM = (
    "You operate the report service described by the public contract and tools in the observation. "
    "Choose exactly one next tool. Return only JSON with exactly two fields: action (a tool name) "
    "and params (an object; empty for reads/stop/escalate). Stop declares completion of the contract; "
    "escalate ends without claiming completion. Respect the remaining budgets. "
    "Use only observed data and tool responses; do not invent stage IDs, revisions or results. "
    "No filesystem access, code execution or private evaluator is available."
)
MODEL = "deepseek-flash"
MAX_CALLS, MAX_PRIMARY, MAX_TOKENS, MAX_PROMPT_BYTES = 96, 8, 512, 12000
PEAK_INPUT, PEAK_OUTPUT, MAX_COST_USD = 0.30, 1.20, 0.60
EXTERNAL_STOPS = {"provider_error", "input_limit", "request_limit", "cost_limit", "provider_unavailable"}


def parse_action(answer, action_names=None):
    try:
        choice = answer["choices"][0]
        require(choice.get("finish_reason") == "stop", "unfinished model response")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                require(key not in result, "duplicate model JSON key")
                result[key] = value
            return result
        def reject_constant(value):
            raise ValueError("non-finite JSON value")
        value = json.loads(choice["message"]["content"], object_pairs_hook=unique, parse_constant=reject_constant)
        require(isinstance(value, dict) and set(value) == {"action", "params"}
                and isinstance(value["action"], str) and value["action"] in (TOOLS if action_names is None else action_names)
                and isinstance(value["params"], dict), "invalid action schema")
        return value, None
    except (ValueError, KeyError, TypeError, IndexError):
        return {"action": "invalid_model_output", "params": {}}, "invalid_model_output"


class Client:
    """Uses existing local credentials; journals public requests and received bodies.

    No SDK retry, JSON repair or automatic model fallback. Cost accounting uses
    peak uncached token rates, not the provider's eventual invoice/discounts.
    """
    def __init__(self, journal, *, config=None, transport=None, system_prompt=SYSTEM, max_calls=MAX_CALLS,
                 action_names=None):
        config = settings() if config is None else config
        key = config.get("DEEPSEEK_API_KEY", "").strip()
        require(key and key not in ("replace_with_your_key", "your_key", "YOUR_API_KEY"), "DeepSeek credential not configured")
        self.key, self.journal = key, Path(journal)
        require(not self.journal.exists(), "request journal must be new")
        self.journal.parent.mkdir(parents=True, exist_ok=True)
        self.transport = transport or self.send
        require(isinstance(system_prompt, str) and system_prompt and type(max_calls) is int and max_calls > 0,
                "invalid client prompt/request cap")
        self.system_prompt, self.max_calls = system_prompt, max_calls
        self.action_names = tuple(TOOLS if action_names is None else action_names)
        require(self.action_names and all(isinstance(n, str) and n for n in self.action_names)
                and len(set(self.action_names)) == len(self.action_names), "invalid action namespace")
        self.calls, self.peak_cost, self.fatal = 0, 0.0, False
        self.records = []

    @staticmethod
    def send(request):
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)

    def scrub(self, value):
        if isinstance(value, str):
            return value.replace(self.key, "[REDACTED_CREDENTIAL]")
        if isinstance(value, list):
            return [self.scrub(x) for x in value]
        if isinstance(value, dict):
            return {self.scrub(k): self.scrub(v) for k, v in value.items()}
        return value

    def record(self, value):
        clean = self.scrub(value)
        self.records.append(clean)
        with self.journal.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(clean, ensure_ascii=False, allow_nan=False) + "\n")

    def __call__(self, observation, controller):
        require(controller == MODEL, "unexpected model controller")
        messages = [{"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": json.dumps(observation, ensure_ascii=False, allow_nan=False)}]
        prompt_bytes = len(json.dumps(messages, ensure_ascii=False).encode("utf-8"))
        reservation = ((prompt_bytes + 1024) * PEAK_INPUT + MAX_TOKENS * PEAK_OUTPUT) / 1_000_000
        reason = ("provider_unavailable" if self.fatal else "input_limit" if prompt_bytes > MAX_PROMPT_BYTES else
                  "request_limit" if self.calls >= self.max_calls else "cost_limit" if self.peak_cost + reservation > MAX_COST_USD else None)
        base = {"observation_sha256": fingerprint(observation), "prompt_bytes": prompt_bytes,
                "timestamp_utc": datetime.now(timezone.utc).isoformat()}
        if reason:
            self.record({**base, "request_sent": False, "category": reason})
            raise ControllerStop(reason)
        body = {"model": MODEL, "temperature": 0, "thinking": {"type": "disabled"}, "max_tokens": MAX_TOKENS,
                "response_format": {"type": "json_object"}, "messages": messages}
        self.calls += 1
        request = urllib.request.Request("https://api.deepseek.com/chat/completions", data=json.dumps(body).encode(),
                                        headers={"Content-Type": "application/json", "Authorization": "Bearer " + self.key}, method="POST")
        started = time.perf_counter()
        try:
            answer = self.transport(request)
        except Exception as error:
            self.peak_cost += reservation  # response absent: do not assume zero charge
            self.fatal = True
            error_body = None
            if isinstance(error, urllib.error.HTTPError):
                try:
                    error_body = error.read(8192).decode("utf-8", errors="replace")
                except OSError:
                    pass
            self.record({**base, "request_sent": True, "request_index": self.calls - 1,
                         "request_body": body, "category": "provider_error", "error_type": type(error).__name__,
                         "http_status": getattr(error, "code", None), "error_body": error_body,
                         "seconds": time.perf_counter() - started, "peak_cost_estimate_usd": reservation})
            raise ControllerStop("provider_error") from None
        usage = answer.get("usage", {}) if isinstance(answer, dict) else {}
        prompt, completion = usage.get("prompt_tokens"), usage.get("completion_tokens")
        valid_usage = type(prompt) is int and prompt >= 0 and type(completion) is int and completion >= 0
        charge = (prompt * PEAK_INPUT + completion * PEAK_OUTPUT) / 1_000_000 if valid_usage else reservation
        self.peak_cost += charge
        response_redacted = self.key in json.dumps(answer)
        clean_answer = self.scrub(answer)
        proposal, parse_error = parse_action(clean_answer, self.action_names)
        if response_redacted:
            proposal, parse_error = {"action": "invalid_model_output", "params": {}}, "credential_echo_redacted"
        self.record({**base, "request_sent": True, "request_index": self.calls - 1, "request_body": body,
                     "category": "received", "raw_response": clean_answer, "response_redacted": response_redacted,
                     "parsed_action": proposal, "parse_error": parse_error,
                     "seconds": time.perf_counter() - started, "peak_cost_estimate_usd": charge,
                     "usage_available": valid_usage})
        return proposal


class PrefixReplay:
    """Reuse actual primary decisions only if the complete public observation matches."""
    def __init__(self, execution):
        self.events = [d for d in execution["decisions"] if d["actor"] == "primary"]
        self.index = 0

    def __call__(self, observation, controller):
        require(controller == MODEL and self.index < len(self.events), "replay prefix exhausted")
        event = self.events[self.index]
        require(event["public_observation_sha256"] == fingerprint(observation), "replay public prefix mismatch")
        self.index += 1
        if event["kind"] == "controller_stop":
            raise ControllerStop(event["reason"])
        return copy.deepcopy(event["proposal"])


def prepare(output):
    output = Path(output).resolve()
    require(not output.exists(), "live experiment destination must be new")
    tasks = [t for t in load() if t["id"].endswith("-01")]
    cells = [{"task_id": t["id"], "condition": c, "checks_budget": b} for t in tasks
             for c in ("healthy", "semantic_error") for b in (1, 4)]
    random.Random(20261024).shuffle(cells)
    code = [Path(__file__), Path(__file__).with_name("recovery_credit.py"),
            REPO / "faultda_bench/semantic/environment.py", REPO / "faultda_bench/semantic/policies.py",
            REPO / "faultda_bench/semantic/compute.py", REPO / "faultda_bench/semantic/oracle.py"]
    protocol = {"version": __version__, "date": "2026-10-24", "kind": "exploratory_live_prefix_counterfactual",
                "model_requested": MODEL, "model_version_documented": "DeepSeek-V4.1-Flash-1017",
                "model_version_limit": "Provider alias and response labels recorded; immutable weights are not established.",
                "temperature": 0, "thinking": "disabled", "system_prompt": SYSTEM, "conditions": ["healthy", "semantic_error"],
                "cells": cells, "systems": ["live_primary", "same_prefix_plus_helper", "helper_only"],
                "primary_trajectories": len(cells), "paired_replays": len(cells), "helper_only_executions": len(cells),
                "max_calls": MAX_CALLS, "max_primary_calls_per_trajectory": MAX_PRIMARY, "max_tokens": MAX_TOKENS,
                "max_prompt_bytes": MAX_PROMPT_BYTES, "peak_cost_ceiling_estimate_usd": MAX_COST_USD,
                "peak_usd_per_million_tokens": {"input_uncached": PEAK_INPUT, "output": PEAK_OUTPUT},
                "cost_reservation": "UTF-8 prompt bytes + 1024 input tokens, plus maximum output; actual usage uses peak uncached rates. Not an invoice guarantee.",
                "pricing_source": "https://api-docs.deepseek.com/quick_start/pricing/", "pricing_checked_date": "2026-10-24",
                "shared_caps": {"checks": [1, 4], "mutations": 6, "decisions": 16},
                "pairing": "Same recorded real model prefix, verified at every public observation; helper acts only after a stop/escalate proposal. No new model calls in the helper arm.",
                "external_stops": sorted(EXTERNAL_STOPS), "missingness": "Provider/input/request/cost stops remain missing in the three-way outcome; bounded model failures remain failures.",
                "task_manifest_sha256": digest(MANIFEST),
                "tasks": [{"task_id": t["id"], "task_sha256": fingerprint(t), "source_id": t["source_id"],
                           "source_sha256": t["source_sha256"], "split": "historical_development"} for t in tasks],
                "code_sha256": {p.relative_to(REPO).as_posix(): digest(p) for p in code},
                "primary_metrics": ["A/AH/H safe-completion triplet", "AH-A", "AH-H", "per-intent costs and stop behavior"],
                "sampling": "Three historical instances, one per analysis intent in one environment; no independent cross-task estimate.",
                "api_retry_policy": "none; first provider failure prevents further network calls in this pilot"}
    save(output / "protocol.json", protocol)
    return protocol


def execute(output, client=None, progress=None):
    output = Path(output).resolve()
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    require(protocol["version"] == __version__ and protocol["model_requested"] == MODEL, "live protocol mismatch")
    for path, expected in protocol["code_sha256"].items():
        require(digest(REPO / path) == expected, "live code changed since protocol freeze")
    require(not (output / "runs.json").exists() and not (output / "executions").exists(), "live results must be new")
    client = Client(output / "requests.jsonl") if client is None else client
    tasks = {t["id"]: t for t in load()}
    rows, triplets = [], []
    protocol_hash = digest(output / "protocol.json")
    for cell_index, cell in enumerate(protocol["cells"]):
        task = tasks[cell["task_id"]]
        require(fingerprint(task) == next(t["task_sha256"] for t in protocol["tasks"] if t["task_id"] == task["id"]), "live task changed")
        prefix = f"{task['id']}--{cell['condition']}--b{cell['checks_budget']}"
        base_args = (task, cell["condition"], cell["checks_budget"])
        before_calls = client.calls
        journal_start = len(client.records)
        live = run(base_args[0], output / "executions" / (prefix + "--live"), *base_args[1:], MODEL,
                   dispatcher=client, primary_kind="model_api", max_primary_decisions=MAX_PRIMARY)
        live["request_record_range"] = [journal_start, len(client.records)]
        primary_records = client.records[journal_start:]
        require(len(primary_records) == len(live["decisions"]) and all(
                r["observation_sha256"] == d["public_observation_sha256"] for r, d in zip(primary_records, live["decisions"])),
                "primary response journal/decision mismatch")
        live["request_record_bindings"] = [{"journal_index": journal_start + i, "record_sha256": fingerprint(r)}
                                           for i, r in enumerate(primary_records)]
        replay = PrefixReplay(live)
        assisted = run(base_args[0], output / "executions" / (prefix + "--assisted"), *base_args[1:], MODEL, True,
                       dispatcher=replay, primary_kind="recorded_model_prefix", max_primary_decisions=MAX_PRIMARY)
        require(replay.index == len(replay.events), "model prefix not fully replayed")
        require(client.calls - before_calls <= MAX_PRIMARY, "episode request cap exceeded")
        helper = run(base_args[0], output / "executions" / (prefix + "--helper"), *base_args[1:], None)
        require(live["public_input_sha256"] == assisted["public_input_sha256"] == helper["public_input_sha256"]
                and live["caps"] == assisted["caps"] == helper["caps"], "live comparison inputs/caps differ")
        assessed = []
        for name, suffix, execution in [("live_primary", "live", live), ("same_prefix_plus_helper", "assisted", assisted), ("helper_only", "helper", helper)]:
            execution["protocol_sha256"] = protocol_hash
            if name == "same_prefix_plus_helper":
                execution["primary_prefix_source"] = prefix + "--live"
                execution["new_model_calls"] = 0
            path = output / "executions" / (prefix + "--" + suffix) / "execution.json"
            save(path, execution)
            value = None if execution["terminal"] in EXTERNAL_STOPS else bool(execution["independent_assessment"]["safe_complete"])
            assessed.append(value)
            rows.append({**cell, "system": name, "terminal": execution["terminal"], "assessed_success": value,
                         "safe_complete": execution["independent_assessment"]["safe_complete"], "snapshot_correct": execution["independent_assessment"]["snapshot_correct"],
                         "forbidden_effect": execution["independent_assessment"]["forbidden_effect"], "cost": execution["cost"],
                         "native_exact_agree": execution["native_exact_agree"], "evidence": path.relative_to(output).as_posix(), "evidence_sha256": digest(path)})
        a, ah, h = assessed
        signature = "".join("?" if v is None else str(int(v)) for v in assessed)
        triplets.append({**cell, "analysis_intent": task["contract"]["family"], "A": a, "AH": ah, "H": h,
                         "signature": signature, "assistance_gain": int(ah) - int(a) if a is not None and ah is not None else None,
                         "gain_over_replacement": int(ah) - int(h) if ah is not None and h is not None else None,
                         "live_requests": client.calls - before_calls,
                         "received_responses": sum(r["category"] == "received" for r in primary_records),
                         "exact_prefix_replayed": True})
        if progress:
            progress({"cell": cell_index + 1, **cell, "signature": signature, "requests": client.calls,
                      "peak_cost_estimate_usd": round(client.peak_cost, 6)})
    require(digest(output / "protocol.json") == protocol_hash, "protocol changed during live run")
    summary = {"version": __version__, "kind": protocol["kind"], "executions": len(rows), "attempted_primary_trajectories": len(triplets),
               "primary_trajectories_with_responses": sum(t["received_responses"] > 0 for t in triplets),
               "paired_model_prefix_replays": len(triplets), "helper_only_executions": len(triplets), "requests_sent": client.calls,
               "received_responses": sum(r["category"] == "received" for r in client.records),
               "parse_failures": sum(bool(r.get("parse_error")) for r in client.records),
               "models_returned": sorted({r["raw_response"].get("model", "unknown") for r in client.records if r["category"] == "received"}),
               "peak_cost_estimate_usd": client.peak_cost, "known_usage": {k: sum(r.get("raw_response", {}).get("usage", {}).get(k, 0) or 0 for r in client.records)
                                                                       for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
               "signatures": dict(Counter(t["signature"] for t in triplets)), "resolved_triplets": sum("?" not in t["signature"] for t in triplets),
               "native_exact_agree": sum(r["native_exact_agree"] for r in rows), "triplets": triplets,
               "limitations": ["One model alias and three historical task instances in one environment.",
                               "Helper arm reuses the actual model prefix; it is not an independent second live trajectory or a helper-aware model policy.",
                               "Peak-rate usage estimate is not an actual invoice; provider errors retain reserved estimated costs."]}
    save(output / "runs.json", rows)
    save(output / "summary.json", summary)
    report = ["# DeepSeek 恢复功劳归因：配对前缀实验", "", f"尝试主策略单元 {len(triplets)} 个；其中 {summary['primary_trajectories_with_responses']} 个收到模型响应；配对重放 {len(triplets)} 个；规则对照 {len(triplets)} 个。",
              f"API 请求 {client.calls} 次；按峰值单价的用量估算 ${client.peak_cost:.6f}。", "",
              "A=真实模型，AH=相同真实前缀接修复器，H=修复器独立；? 表示外部执行原因未能评估。", "",
              "| 任务 | 条件 | 检查上限 | A/AH/H | 主轨迹请求数 |", "| --- | --- | ---: | --- | ---: |"]
    for t in triplets:
        report.append(f"| {t['task_id']} | {t['condition']} | {t['checks_budget']} | {t['signature']} | {t['live_requests']} |")
    report += ["", "每个模型决策的公开观察哈希均经配对重放核对。真实供应商响应正文、解析失败及请求用量保存在 requests.jsonl。",
               "此开发实验检验归因设计能否描述真实模型行为；重复条件和预算不是独立任务家族。"]
    (output / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8", newline="\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prepare", action="store_true", help="freeze the study without network calls")
    parser.add_argument("--execute", action="store_true", help="run a previously frozen study")
    args = parser.parse_args()
    require(args.prepare != args.execute, "choose exactly one of --prepare/--execute")
    try:
        if args.prepare:
            protocol = prepare(args.output)
            print(json.dumps({"protocol": str(args.output / 'protocol.json'), "primary_trajectories": protocol['primary_trajectories'],
                              "max_requests": MAX_CALLS, "peak_cost_ceiling_estimate_usd": MAX_COST_USD}, indent=2))
        else:
            require(credential_present(), "DeepSeek credential not configured")
            result = execute(args.output, progress=lambda x: print(json.dumps(x), flush=True))
            print(json.dumps({k: result[k] for k in ("requests_sent", "signatures", "parse_failures", "peak_cost_estimate_usd")}, indent=2))
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
