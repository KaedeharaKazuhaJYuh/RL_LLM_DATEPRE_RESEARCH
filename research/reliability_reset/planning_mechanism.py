"""Factorial prompt mechanism and automatic evidence planning across tool names."""

import argparse
import copy
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from faultda_bench.semantic.environment import SemanticEnv
from faultda_bench.semantic.tasks import load, MANIFEST, REPO
from . import __version__
from .audit import digest, require
from .credit_live import Client, EXTERNAL_STOPS, MAX_PRIMARY, MODEL, SYSTEM, parse_action
from .evidence_planner import INTERFACES, E0_CARDS, evidence_plan, observed_evidence, public_view
from .recovery_credit import ControllerStop, fingerprint, run, save
from .tool_planning import CODE as PREVIOUS_CODE


BUDGET = "Read budget note: Each read consumes one check. With only one check remaining, choose a read that can support the full contract before spending that check."
BUDGET_CONTROL = "Service context note: The report service keeps durable records with revision identifiers. A staged candidate is distinct from a published report in storage."
RELATION = "Information note: In E0, inspect returns every status field plus active reports, all input tables and catalog. It can return more bytes than status."
RELATION_CONTROL = "Record context note: A report identifies an input version and stores its computed output. The request contract specifies which analysis is requested."
SLOTS = (max(len(BUDGET), len(BUDGET_CONTROL)), max(len(RELATION), len(RELATION_CONTROL)))
FACTORS = {"context": (False, False), "budget_only": (True, False),
           "relation_only": (False, True), "combined": (True, True)}
PROMPTS = {arm: SYSTEM + "\n" + (BUDGET if b else BUDGET_CONTROL).ljust(SLOTS[0]) + "\n" +
           (RELATION if i else RELATION_CONTROL).ljust(SLOTS[1]) for arm, (b, i) in FACTORS.items()}
MAX_REQUESTS = 384
TASK_IDS = tuple(f"{family}-{n:02d}" for family in ("group", "window", "version") for n in (1, 3))
CODE = tuple(dict.fromkeys((*PREVIOUS_CODE, "research/reliability_reset/evidence_planner.py",
                           "research/reliability_reset/planning_mechanism.py")))


def system_prompt(cell, view):
    if cell["phase"] == "factorial":
        return PROMPTS[cell["arm"]]
    if cell["arm"] == "schema_only":
        return SYSTEM
    require(cell["arm"] == "auto_plan", "unknown planning arm")
    return SYSTEM + ("\nA public-contract query planner suggests the following evidence plan. "
                     "It does not check numerical correctness, choose publication parameters, or execute tools for you. "
                     "After obtaining evidence, evaluate the report against the analysis contract and complete the task.\n" +
                     json.dumps(evidence_plan(view), sort_keys=True))


class Dispatcher:
    """Lossless interface view plus suggestions; never overrides a model tool choice."""
    def __init__(self, cell, client=None, recorded=None):
        self.cell, self.client, self.recorded = cell, client, recorded
        self.events = []

    def __call__(self, observation, controller):
        require(controller == MODEL, "unexpected mechanism controller")
        mapping = INTERFACES[self.cell["interface"]]
        view = public_view(observation, self.cell["interface"], self.cell["phase"] == "transfer")
        prompt = system_prompt(self.cell, view)
        event = {"canonical_observation_sha256": fingerprint(observation), "view_sha256": fingerprint(view),
                 "system_prompt_sha256": fingerprint(prompt)}
        index = len(self.events)
        if self.recorded is not None:
            require(index < len(self.recorded), "planning replay prefix exhausted")
            original = self.recorded[index]
            require(all(original[k] == v for k, v in event.items()), "planning replay input/prompt changed")
            self.events.append(copy.deepcopy(original))
            if original.get("controller_stop"):
                raise ControllerStop(original["controller_stop"])
            return copy.deepcopy(original["canonical_proposal"])
        self.client.system_prompt = prompt
        self.client.action_names = tuple(mapping.values())
        before = len(self.client.records)
        try:
            advertised = self.client(view, MODEL)
        except ControllerStop as error:
            event.update(controller_stop=str(error), journal_index=before)
            self.events.append(event)
            raise
        reverse = {v: k for k, v in mapping.items()}
        canonical = {**advertised, "action": reverse.get(advertised["action"], advertised["action"])}
        event.update(advertised_proposal=advertised, canonical_proposal=canonical, journal_index=before)
        self.events.append(event)
        return canonical


def design_cells():
    pairs = [(family + "-01", condition) for family in ("group", "window", "version")
             for condition in ("healthy", "semantic_error")]
    random.Random(2026102435).shuffle(pairs)
    cells = []
    # Balanced Latin order gives each factorial arm every position within the first four blocks.
    arms = tuple(FACTORS)
    for i, (task, condition) in enumerate(pairs):
        for arm in arms[i % 4:] + arms[:i % 4]:
            cells.append({"phase": "factorial", "task_id": task, "condition": condition,
                          "interface": "canonical", "arm": arm})
    transfer = [(family + "-03", condition, interface) for family in ("group", "window", "version")
                for condition in ("healthy", "semantic_error") for interface in INTERFACES]
    random.Random(2026102436).shuffle(transfer)
    for i, (task, condition, interface) in enumerate(transfer):
        for arm in (("schema_only", "auto_plan") if i % 2 == 0 else ("auto_plan", "schema_only")):
            cells.append({"phase": "transfer", "task_id": task, "condition": condition,
                          "interface": interface, "arm": arm})
    return cells


def prepare(output):
    output = Path(output).resolve()
    require(not output.exists(), "mechanism destination must be new")
    tasks = [t for t in load() if t["id"] in TASK_IDS]
    require({t["id"] for t in tasks} == set(TASK_IDS), "missing mechanism task")
    protocol = {"version": __version__, "date": "2026-10-24", "kind": "factorial_and_public_evidence_planning",
                "model_requested": MODEL, "temperature": 0, "thinking": "disabled", "cells": design_cells(),
                "factor_prompts": PROMPTS, "factors": FACTORS, "interfaces": INTERFACES,
                "read_tool_contracts": E0_CARDS, "byte_estimates": "Fixed interface metadata, not private-state measurements or trained costs.",
                "factorial_metrics": "2x2 budget salience / information inclusion completion contrasts and interaction; all four notes byte-matched, not token-matched.",
                "transfer_metrics": "Schema-only vs automatically planned, each under canonical and opaque read names; both see identical structured public metadata.",
                "shared_caps": {"checks": 1, "mutations": 6, "decisions": 16},
                "model_trajectories": 48, "shared_rule_controls": 12, "max_primary_calls": MAX_PRIMARY,
                "max_requests": MAX_REQUESTS, "peak_cost_estimate_ceiling_usd": 0.60,
                "peak_usd_per_million_tokens": {"input_uncached": 0.30, "output": 1.20},
                "pricing_source": "https://api-docs.deepseek.com/quick_start/pricing/", "pricing_checked_date": "2026-10-24",
                "task_manifest_sha256": digest(MANIFEST),
                "tasks": [{"task_id": t["id"], "task_sha256": fingerprint(t), "source_id": t["source_id"],
                           "source_sha256": t["source_sha256"]} for t in tasks],
                "code_sha256": {p: digest(REPO / p) for p in CODE},
                "split": "01 previously live; 03 additional historically offline development instances. One environment, no independent held-out set.",
                "model_role": "Every model action is executed as proposed after bijective namespace translation. Planner only supplies read suggestions; no action substitution or hidden repair.",
                "order": "Rotated factorial blocks; shuffled transfer blocks with alternating arm order. One provider sample per model cell.",
                "stopping": "No retry/fallback; first provider error prevents further network requests. Missing cells retained; no additional paid experiment selected from results."}
    save(output / "protocol.json", protocol)
    return protocol


def preflight(output):
    output = Path(output).resolve()
    tasks = {t["id"]: t for t in load()}
    rows = []
    for task_id in TASK_IDS:
        for condition in ("healthy", "semantic_error"):
            env = SemanticEnv(tasks[task_id], output / (task_id + "--" + condition), budget=4,
                              semantic_fault=condition == "semantic_error")
            for name, card in E0_CARDS.items():
                env.step(name)
                event = env.history[-1]
                actual = observed_evidence([event], E0_CARDS)
                require(set(card["provides"]) <= actual, "public card overstates returned evidence")
                rows.append({"task_id": task_id, "condition": condition, "tool": name,
                             "public_response": event["response"], "advertised_fields_verified": card["provides"]})
    save(output / "checks.json", rows)
    return rows


def summarize(rows, records):
    strata = defaultdict(Counter)
    indexed = defaultdict(dict)
    for row in rows:
        key = (row["phase"], row["interface"], row["arm"])
        strata[key].update(executions=1, resolved=int(row["assessed_success"] is not None),
                           safe_complete=int(row["assessed_success"] is True), inspect_first=int(row["first_canonical"] == "inspect"),
                           forbidden_effect=int(row["forbidden_effect"]), response_bytes=row["cost"]["response_bytes"],
                           requests=row["requests"], **row["usage"])
        if row["arm"] != "rule_only":
            indexed[(row["phase"], row["task_id"], row["condition"], row["interface"])][row["arm"]] = row
    factorial = []
    for key, arms in indexed.items():
        if key[0] != "factorial":
            continue
        values = {k: arms[k]["assessed_success"] for k in FACTORS}
        resolved = all(v is not None for v in values.values())
        c, b, i, bi = [int(values[a]) if resolved else None for a in FACTORS]
        factorial.append({"task_id": key[1], "condition": key[2], **values,
                          "budget_at_no_relation": b - c if resolved else None,
                          "relation_at_no_budget": i - c if resolved else None,
                          "interaction": bi - b - i + c if resolved else None})
    contrasts = []
    for interface in INTERFACES:
        counts = Counter(gains=0, losses=0, ties=0, missing=0)
        for key, arms in indexed.items():
            if key[0] != "transfer" or key[3] != interface:
                continue
            a, b = arms["schema_only"]["assessed_success"], arms["auto_plan"]["assessed_success"]
            if a is None or b is None:
                counts["missing"] += 1
            else:
                counts["gains" if b and not a else "losses" if a and not b else "ties"] += 1
        contrasts.append({"interface": interface, **counts})
    return {"version": __version__, "model_executions": sum(r["arm"] != "rule_only" for r in rows),
            "rule_executions": sum(r["arm"] == "rule_only" for r in rows), "environment_families": 1,
            "requests_sent": sum(r["request_sent"] for r in records), "received_responses": sum(r["category"] == "received" for r in records),
            "parse_failures": sum(bool(r.get("parse_error")) for r in records), "provider_errors": sum(r["category"] == "provider_error" for r in records),
            "known_usage": {k: sum(r.get("raw_response", {}).get("usage", {}).get(k, 0) or 0 for r in records)
                            for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "peak_cost_estimate_usd": sum(r.get("peak_cost_estimate_usd", 0) for r in records),
            "models_returned": sorted({r["raw_response"].get("model", "unknown") for r in records if r["category"] == "received"}),
            "native_exact_agree": sum(r["native_exact_agree"] for r in rows),
            "strata": [{"phase": k[0], "interface": k[1], "arm": k[2], **v} for k, v in sorted(strata.items())],
            "factorial_cells": factorial, "planner_contrasts": contrasts}


def execute(output, client=None, progress=None):
    output = Path(output).resolve()
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    require(protocol["version"] == __version__ and protocol["cells"] == design_cells()
            and protocol["factor_prompts"] == PROMPTS and protocol["interfaces"] == INTERFACES
            and protocol["read_tool_contracts"] == E0_CARDS, "mechanism protocol mismatch")
    for path, expected in protocol["code_sha256"].items():
        require(digest(REPO / path) == expected, "mechanism code changed since freeze")
    require(digest(MANIFEST) == protocol["task_manifest_sha256"], "mechanism manifest changed")
    require(not (output / "executions").exists(), "mechanism results must be new")
    tasks = {t["id"]: t for t in load()}
    for t in protocol["tasks"]:
        require(fingerprint(tasks[t["task_id"]]) == t["task_sha256"], "mechanism task changed")
    client = Client(output / "requests.jsonl", max_calls=MAX_REQUESTS) if client is None else client
    require(not client.records and client.calls == 0 and client.max_calls == MAX_REQUESTS, "mechanism client must be fresh")
    rows, controls = [], set()
    protocol_hash = digest(output / "protocol.json")
    for i, cell in enumerate(protocol["cells"]):
        run_id = "--".join(cell[k] for k in ("phase", "task_id", "condition", "interface", "arm"))
        dispatcher = Dispatcher(cell, client=client)
        start = len(client.records)
        execution = run(tasks[cell["task_id"]], output / "executions" / run_id, cell["condition"], 1, MODEL,
                        dispatcher=dispatcher, primary_kind="model_api", max_primary_decisions=MAX_PRIMARY)
        records = client.records[start:]
        require(len(records) == len(dispatcher.events) == len(execution["decisions"]), "mechanism dispatch length mismatch")
        execution["dispatch"] = dispatcher.events
        for event, decision, record in zip(dispatcher.events, execution["decisions"], records):
            require(event["canonical_observation_sha256"] == decision["public_observation_sha256"]
                    and event["view_sha256"] == record["observation_sha256"], "mechanism observation binding mismatch")
            event["record_sha256"] = fingerprint(record)
        pending = [(cell["arm"], run_id, execution, records)]
        control_key = (cell["phase"], cell["task_id"], cell["condition"])
        if control_key not in controls:
            controls.add(control_key)
            rule = run(tasks[cell["task_id"]], output / "executions" / (run_id + "--rule"), cell["condition"], 1, None)
            require(rule["public_input_sha256"] == execution["public_input_sha256"], "mechanism rule input mismatch")
            pending.append(("rule_only", run_id + "--rule", rule, []))
        for arm, key, result, selected in pending:
            selected_cell = {**cell, "arm": arm, "interface": "backend" if arm == "rule_only" else cell["interface"]}
            result.update(cell=selected_cell, protocol_sha256=protocol_hash)
            path = output / "executions" / key / "execution.json"
            save(path, result)
            usage = {k: sum(r.get("raw_response", {}).get("usage", {}).get(k, 0) or 0 for r in selected)
                     for k in ("prompt_tokens", "completion_tokens", "total_tokens")}
            first = next((d["proposal"]["action"] for d in result["decisions"] if "proposal" in d), None)
            rows.append({**selected_cell, "run_id": key, "public_input_sha256": result["public_input_sha256"],
                         "terminal": result["terminal"], "assessed_success": None if result["terminal"] in EXTERNAL_STOPS else bool(result["independent_assessment"]["safe_complete"]),
                         "forbidden_effect": result["independent_assessment"]["forbidden_effect"], "first_canonical": first,
                         "cost": result["cost"], "usage": usage, "requests": sum(r["request_sent"] for r in selected),
                         "native_exact_agree": result["native_exact_agree"], "evidence": path.relative_to(output).as_posix(), "evidence_sha256": digest(path)})
        if progress:
            progress({"completed": i + 1, **cell, "success": execution["independent_assessment"]["safe_complete"],
                      "first": next((d.get("proposal", {}).get("action") for d in execution["decisions"] if "proposal" in d), None), "requests": client.calls})
    require(digest(output / "protocol.json") == protocol_hash, "mechanism protocol changed")
    summary = summarize(rows, client.records)
    save(output / "runs.json", rows)
    save(output / "summary.json", summary)
    lines = ["# 1.0.35：提示成分与自动证据规划", "", "| 阶段 | 接口 | 提示/系统 | 安全完成/解析单元 | inspect 首选 | 输入/输出 tokens |",
             "| --- | --- | --- | ---: | ---: | --- |"]
    for s in summary["strata"]:
        lines.append(f"| {s['phase']} | {s['interface']} | {s['arm']} | {s['safe_complete']}/{s['resolved']} | {s['inspect_first']}/{s['executions']} | {s['prompt_tokens']}/{s['completion_tokens']} |")
    lines += ["", "所有模型臂均真实采样。rule_only 为每任务/状态共享的后台规则，不是另一批模型采样。",
              "03 实例也曾用于离线开发；这里只有一个环境家族。自动规划建议不会重写模型动作，别名转换不改变工具参数或业务数据。"]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return summary


def verify(output, replay_output):
    output, replay_output = Path(output).resolve(), Path(replay_output).resolve()
    require(not replay_output.exists(), "mechanism replay destination must be new")
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    for path, expected in protocol["code_sha256"].items():
        require(digest(REPO / path) == expected, "mechanism replay code mismatch")
    rows = json.loads((output / "runs.json").read_text(encoding="utf-8"))
    records = [json.loads(s) for s in (output / "requests.jsonl").read_text(encoding="utf-8").splitlines()]
    tasks = {t["id"]: t for t in load()}
    used, responses, replayed = [], 0, 0
    for row in rows:
        require(digest(output / row["evidence"]) == row["evidence_sha256"], "mechanism evidence hash mismatch")
        execution = json.loads((output / row["evidence"]).read_text(encoding="utf-8"))
        require(execution["protocol_sha256"] == digest(output / "protocol.json"), "mechanism protocol binding mismatch")
        require(row["cost"] == execution["cost"] and row["native_exact_agree"] == execution["native_exact_agree"], "mechanism index mismatch")
        if row["arm"] == "rule_only":
            continue
        mapping = INTERFACES[row["interface"]]
        for event, decision in zip(execution["dispatch"], execution["decisions"], strict=True):
            index = event["journal_index"]
            record = records[index]
            used.append(index)
            require(fingerprint(record) == event["record_sha256"] and event["view_sha256"] == record["observation_sha256"]
                    and event["canonical_observation_sha256"] == decision["public_observation_sha256"], "mechanism journal binding mismatch")
            if record["request_sent"]:
                messages = record["request_body"]["messages"]
                view = json.loads(messages[1]["content"])
                require(fingerprint(view) == event["view_sha256"] and fingerprint(messages[0]["content"]) == event["system_prompt_sha256"], "mechanism prompt/view mismatch")
                require(messages[0]["content"] == system_prompt(row, view), "mechanism treatment prompt changed")
            if record["category"] == "received":
                require(not record["response_redacted"], "credential redaction requires separate review")
                proposal, error = parse_action(record["raw_response"], tuple(mapping.values()))
                require(proposal == event["advertised_proposal"] and error == record["parse_error"], "mechanism response classification mismatch")
                reverse = {v: k for k, v in mapping.items()}
                canonical = {**proposal, "action": reverse.get(proposal["action"], proposal["action"])}
                require(canonical == decision["proposal"] == event["canonical_proposal"], "mechanism tool translation mismatch")
                responses += 1
        replay = Dispatcher(row, recorded=execution["dispatch"])
        result = run(tasks[row["task_id"]], replay_output / row["run_id"], row["condition"], 1, MODEL,
                     dispatcher=replay, primary_kind="recorded_model_prefix", max_primary_decisions=MAX_PRIMARY)
        require(len(replay.events) == len(execution["dispatch"]), "mechanism replay prefix mismatch")
        for field in ("native_result", "independent_assessment", "terminal", "cost"):
            require(json.loads(json.dumps(result[field])) == execution[field], "mechanism replay result differs: " + field)
        replayed += 1
    require(sorted(used) == list(range(len(records))), "unbound or duplicate mechanism request")
    require(summarize(rows, records) == json.loads((output / "summary.json").read_text(encoding="utf-8")), "mechanism summary mismatch")
    result = {"model_replays": replayed, "response_classifications": responses, "journal_records_bound": len(used), "new_api_calls": 0}
    save(replay_output / "CHECKS.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare", action="store_true")
    action.add_argument("--execute", action="store_true")
    action.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.prepare:
        p = prepare(args.output)
        checks = preflight(args.output / "tool-preflight")
        print(json.dumps({"model_trajectories": p["model_trajectories"], "max_requests": MAX_REQUESTS, "public_card_checks": len(checks)}))
    elif args.execute:
        result = execute(args.output, progress=lambda v: print(json.dumps(v), flush=True))
        print(json.dumps({k: result[k] for k in ("requests_sent", "parse_failures", "planner_contrasts", "peak_cost_estimate_usd")}, indent=2))
    else:
        print(json.dumps(verify(args.output, args.verify), indent=2))


if __name__ == "__main__":
    main()
