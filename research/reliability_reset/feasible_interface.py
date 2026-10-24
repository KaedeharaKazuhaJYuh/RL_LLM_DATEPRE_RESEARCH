"""Matched-text, advisory-state and budget-projected tool-interface experiment.

Projection changes advertised choices, never physical permissions or proposals.
Parsing retains the full namespace so an excluded action remains observable.
"""

import argparse
import copy
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from faultda_bench.semantic.tasks import load, MANIFEST, REPO
from . import __version__
from .audit import digest, require
from .credit_live import Client, EXTERNAL_STOPS, MAX_PRIMARY, MODEL, SYSTEM, parse_action
from .evidence_planner import E0_CARDS, INTERFACES, public_view
from .evidence_state import COMPLETION_CONTRACT, evidence_state
from .joint_control import (CODE as PREVIOUS_CODE, JOINT_INSTRUCTION, TASK_IDS, VARIANTS,
                            assess, effective_task)
from .planning_mechanism import Dispatcher
from .recovery_credit import fingerprint, run, save


ARMS = ("matched_text", "soft_joint", "feasible_tools")
MAX_REQUESTS = 54 * MAX_PRIMARY
CODE = (*PREVIOUS_CODE, "research/reliability_reset/feasible_interface.py")
INSTRUCTION = JOINT_INSTRUCTION.replace(
    "Use the public decision support below to choose a cost-feasible action.",
    "Choose a cost-feasible action using the public contract, history and any structured decision support provided.")
PROMPT = SYSTEM + INSTRUCTION


def action_schema(names):
    return {"type": "object", "required": ["action", "params"], "additionalProperties": False,
            "properties": {"action": {"type": "string", "enum": list(names)}, "params": {"type": "object"}}}


def presentation(observation, interface, arm):
    require(arm in ARMS, "unknown feasible-interface arm")
    view = public_view(observation, interface, structured=True)
    if arm != "matched_text":
        state = evidence_state(view, interface)
        view["decision_support"] = state
        if arm == "feasible_tools":
            allowed = set(state["cost_feasible_actions"])
            view["tools"] = {name: description for name, description in view["tools"].items() if name in allowed}
    # All arms get the same output-schema format; only the projected arm's enum
    # tracks remaining budgets. This is visible JSON metadata, not constrained decoding.
    view["action_schema"] = action_schema(view["tools"])
    return view, PROMPT


class FeasibleDispatcher(Dispatcher):
    def presentation(self, observation):
        return presentation(observation, self.cell["interface"], self.cell["arm"])


def design_cells():
    blocks = [(task, variant, interface) for task in TASK_IDS for variant in VARIANTS for interface in INTERFACES]
    random.Random(2026102455).shuffle(blocks)
    cells = []
    for i, (task, variant, interface) in enumerate(blocks):
        for arm in ARMS[i % len(ARMS):] + ARMS[:i % len(ARMS)]:
            cells.append({"phase": "feasible_interface", "task_id": task, "variant": variant,
                          "condition": VARIANTS[variant][0], "interface": interface, "arm": arm})
    return cells


def protocol_definition():
    tasks = [t for t in load() if t["id"] in TASK_IDS]
    require({t["id"] for t in tasks} == set(TASK_IDS), "missing interface task")
    return {"version": __version__, "date": "2026-10-24", "kind": "budget_projected_tool_interface",
            "cells": design_cells(), "arms": ARMS, "variants": VARIANTS, "interfaces": INTERFACES,
            "prompt": PROMPT, "completion_contract": COMPLETION_CONTRACT,
            "model_requested": MODEL, "temperature": 0, "thinking": "disabled",
            "model_trajectories": 54, "shared_backend_rules": 9, "max_requests": MAX_REQUESTS,
            "max_primary_calls": MAX_PRIMARY, "shared_caps": {"checks": 1, "mutations": 6, "decisions": 16},
            "peak_cost_estimate_ceiling_usd": 0.60,
            "peak_usd_per_million_tokens": {"input_uncached": 0.30, "output": 1.20},
            "pricing_source": "https://api-docs.deepseek.com/quick_start/pricing/", "pricing_checked_date": "2026-10-24",
            "intervention": {"matched_text": "Full tool registry, raw history and identical conditional completion text.",
                             "soft_joint": "Same text, full registry and public evidence-state decision support.",
                             "feasible_tools": "Same text and state; registry and advertised action enum omit unaffordable reads/writes."},
            "identical": "Contracts, raw history, budgets, static read capability metadata, permissions and completion scoring. No numeric oracle in any view.",
            "excluded_proposals": "Parse the full original alias namespace and forward unchanged after bijective translation; original runner rejects unaffordable proposals. No forced stop, retry or rescue.",
            "scope": "Three historical 03 instances, three analysis intents, one environment lineage; not independent or held out.",
            "primary_metrics": ["normal-receipt protocol completion", "lost-receipt budget rejection", "activated-fault escalation and unsupported stop"],
            "secondary_metrics": ["excluded action attempts", "fault activation", "native safe completion", "forbidden effects", "calls", "tokens", "bytes", "latency"],
            "interpretation": "Escalation is not completion. Fault activation and pre-fault escalation are reported separately. Projection is interface engineering, not weight learning or a hard safety guarantee.",
            "api_policy": "No retry or fallback; first provider failure stops further network calls; missing cells remain missing.",
            "task_manifest_sha256": digest(MANIFEST),
            "tasks": [{"task_id": t["id"], "base_task_sha256": fingerprint(t), "effective_task_sha256": fingerprint(effective_task(t)),
                       "source_id": t["source_id"], "source_sha256": t["source_sha256"]} for t in tasks],
            "code_sha256": {p: digest(REPO / p) for p in CODE}}


def prepare(output):
    output = Path(output).resolve()
    require(not output.exists(), "interface destination must be new")
    protocol = protocol_definition()
    save(output / "protocol.json", protocol)
    return protocol


def diagnostics(execution, records):
    extra = assess(execution)
    activated = any(s["action"] == "publish" and s["response"].get("error") == "timeout" for s in execution["steps"])
    excluded = []
    for record in records:
        if record["category"] != "received":
            continue
        view = json.loads(record["request_body"]["messages"][1]["content"])
        proposal = record["parsed_action"]
        if not record["parse_error"] and proposal["action"] not in view["action_schema"]["properties"]["action"]["enum"]:
            excluded.append({"request_index": record["request_index"], "proposal": proposal})
    last = execution["decisions"][-1] if execution["decisions"] else {}
    extra.update(fault_activated=activated, escalated=execution["terminal"] == "escalate",
                 activated_escalation=activated and execution["terminal"] == "escalate",
                 pre_fault_escalation=not activated and execution["terminal"] == "escalate",
                 budget_rejection=last.get("kind") == "budget_rejection",
                 rejected_read=last.get("kind") == "budget_rejection" and last.get("proposal", {}).get("action") in E0_CARDS,
                 excluded_action_attempts=excluded)
    return extra


COUNT_FIELDS = ("protocol_complete", "native_safe_complete", "snapshot_correct", "unsupported_stop",
                "post_publish_read_rejection", "forbidden_effect", "fault_activated", "escalated",
                "activated_escalation", "pre_fault_escalation", "budget_rejection", "rejected_read")


def summarize(rows, records):
    strata, pairs = defaultdict(Counter), defaultdict(dict)
    for row in rows:
        counts = strata[(row["variant"], row["interface"], row["arm"])]
        counts.update(executions=1, resolved=int(row["assessed_success"] is not None),
                      **{k: int(row[k]) for k in COUNT_FIELDS})
        counts.update(requests=row["requests"], response_bytes=row["cost"]["response_bytes"],
                      excluded_action_attempts=len(row["excluded_action_attempts"]), **row["usage"])
        if row["arm"] != "rule_only":
            pairs[(row["task_id"], row["variant"], row["interface"])][row["arm"]] = row
    contrasts = []
    for a, b in (("matched_text", "soft_joint"), ("soft_joint", "feasible_tools")):
        for variant in VARIANTS:
            for metric in ("assessed_success", "rejected_read", "activated_escalation", "unsupported_stop"):
                counts = Counter(increased=0, decreased=0, tied=0, missing=0)
                for key, arms in pairs.items():
                    if key[1] != variant:
                        continue
                    av, bv = arms[a][metric], arms[b][metric]
                    counts["missing" if av is None or bv is None else "increased" if bv > av else "decreased" if bv < av else "tied"] += 1
                contrasts.append({"comparison": b + "_vs_" + a, "variant": variant, "metric": metric, **counts})
    return {"version": __version__, "model_executions": sum(r["arm"] != "rule_only" for r in rows),
            "backend_rule_controls": sum(r["arm"] == "rule_only" for r in rows), "environment_families": 1,
            "requests_sent": sum(r["request_sent"] for r in records),
            "received_responses": sum(r["category"] == "received" for r in records),
            "parse_failures": sum(bool(r.get("parse_error")) for r in records),
            "provider_errors": sum(r["category"] == "provider_error" for r in records),
            "models_returned": sorted({r["raw_response"].get("model", "unknown") for r in records if r["category"] == "received"}),
            "known_usage": {k: sum(r.get("raw_response", {}).get("usage", {}).get(k, 0) or 0 for r in records)
                            for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "peak_cost_estimate_usd": sum(r.get("peak_cost_estimate_usd", 0) for r in records),
            "native_exact_agree": sum(r["native_exact_agree"] for r in rows),
            "strata": [{"variant": k[0], "interface": k[1], "arm": k[2], **v} for k, v in sorted(strata.items())],
            "contrasts": contrasts}


def execute(output, client=None, progress=None):
    output = Path(output).resolve()
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    require(protocol == json.loads(json.dumps(protocol_definition())), "interface protocol/source/input changed")
    require(not (output / "executions").exists(), "interface results must be new")
    tasks = {t["id"]: effective_task(t) for t in load() if t["id"] in TASK_IDS}
    client = Client(output / "requests.jsonl", max_calls=MAX_REQUESTS) if client is None else client
    require(not client.records and client.calls == 0 and client.max_calls == MAX_REQUESTS, "interface client must be fresh")
    rows, controls = [], set()
    protocol_hash = digest(output / "protocol.json")
    for i, cell in enumerate(protocol["cells"]):
        key = "--".join(cell[k] for k in ("task_id", "variant", "interface", "arm"))
        dispatcher = FeasibleDispatcher(cell, client=client)
        start = len(client.records)
        result = run(tasks[cell["task_id"]], output / "executions" / key, cell["condition"], 1, MODEL,
                     dispatcher=dispatcher, primary_kind="model_api", max_primary_decisions=MAX_PRIMARY,
                     environment_options=VARIANTS[cell["variant"]][1])
        selected = client.records[start:]
        require(len(selected) == len(dispatcher.events) == len(result["decisions"]), "interface journal length mismatch")
        result["dispatch"] = dispatcher.events
        for event, record, decision in zip(dispatcher.events, selected, result["decisions"], strict=True):
            require(event["view_sha256"] == record["observation_sha256"]
                    and event["canonical_observation_sha256"] == decision["public_observation_sha256"], "interface input binding mismatch")
            event["record_sha256"] = fingerprint(record)
        pending = [(cell["arm"], key, result, selected)]
        pair = (cell["task_id"], cell["variant"])
        if pair not in controls:
            controls.add(pair)
            rule = run(tasks[cell["task_id"]], output / "executions" / (key + "--rule"), cell["condition"], 1, None,
                       environment_options=VARIANTS[cell["variant"]][1])
            require(rule["public_input_sha256"] == result["public_input_sha256"], "interface rule input mismatch")
            pending.append(("rule_only", key + "--rule", rule, []))
        for arm, run_id, execution, records in pending:
            extra = diagnostics(execution, records)
            execution.update(cell={**cell, "arm": arm}, protocol_sha256=protocol_hash, interface_diagnostics=extra)
            path = output / "executions" / run_id / "execution.json"
            save(path, execution)
            rows.append({**cell, "arm": arm, "interface": "backend" if arm == "rule_only" else cell["interface"],
                         "run_id": run_id, "public_input_sha256": execution["public_input_sha256"],
                         "assessed_success": None if execution["terminal"] in EXTERNAL_STOPS else extra["protocol_complete"],
                         **extra, "native_safe_complete": execution["independent_assessment"]["safe_complete"],
                         "snapshot_correct": execution["independent_assessment"]["snapshot_correct"],
                         "forbidden_effect": execution["independent_assessment"]["forbidden_effect"],
                         "native_exact_agree": execution["native_exact_agree"], "terminal": execution["terminal"],
                         "cost": execution["cost"], "requests": sum(r["request_sent"] for r in records),
                         "usage": {k: sum(r.get("raw_response", {}).get("usage", {}).get(k, 0) or 0 for r in records)
                                   for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
                         "evidence": path.relative_to(output).as_posix(), "evidence_sha256": digest(path)})
        if progress:
            progress({"completed": i + 1, **cell, **diagnostics(result, selected), "terminal": result["terminal"], "requests": client.calls})
    require(digest(output / "protocol.json") == protocol_hash, "interface protocol changed during execution")
    summary = summarize(rows, client.records)
    save(output / "runs.json", rows)
    save(output / "summary.json", summary)
    return summary


def verify(output, replay_output):
    output, replay_output = Path(output).resolve(), Path(replay_output).resolve()
    require(not replay_output.exists(), "interface replay destination must be new")
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    require(protocol == json.loads(json.dumps(protocol_definition())), "interface replay protocol/source/input mismatch")
    rows = json.loads((output / "runs.json").read_text(encoding="utf-8"))
    records = [json.loads(s) for s in (output / "requests.jsonl").read_text(encoding="utf-8").splitlines()]
    tasks = {t["id"]: effective_task(t) for t in load()}
    used, replays, responses = [], 0, 0
    require(len(rows) == 63 and sum(r["arm"] != "rule_only" for r in rows) == 54, "interface missing execution")
    expected_cells = [json.dumps(c, sort_keys=True) for c in protocol["cells"]]
    actual_cells = [json.dumps({k: r[k] for k in protocol["cells"][0]}, sort_keys=True) for r in rows if r["arm"] != "rule_only"]
    require(actual_cells == expected_cells, "interface cell order/membership changed")
    for row in rows:
        path = output / row["evidence"]
        require(digest(path) == row["evidence_sha256"], "interface execution hash mismatch")
        execution = json.loads(path.read_text(encoding="utf-8"))
        require(execution["protocol_sha256"] == digest(output / "protocol.json"), "interface protocol binding mismatch")
        selected = []
        if row["arm"] != "rule_only":
            mapping = INTERFACES[row["interface"]]
            reverse = {v: k for k, v in mapping.items()}
            for event, decision in zip(execution["dispatch"], execution["decisions"], strict=True):
                record = records[event["journal_index"]]
                used.append(event["journal_index"])
                selected.append(record)
                require(fingerprint(record) == event["record_sha256"] and event["view_sha256"] == record["observation_sha256"]
                        and event["canonical_observation_sha256"] == decision["public_observation_sha256"], "interface response binding mismatch")
                if record["category"] == "received":
                    require(not record["response_redacted"], "interface credential echo requires separate review")
                    proposal, error = parse_action(record["raw_response"], tuple(mapping.values()))
                    require(proposal == record["parsed_action"] == event["advertised_proposal"] and error == record["parse_error"], "interface response classification mismatch")
                    require({**proposal, "action": reverse.get(proposal["action"], proposal["action"])} == decision["proposal"], "interface proposal changed")
                    messages = record["request_body"]["messages"]
                    require(fingerprint(json.loads(messages[1]["content"])) == event["view_sha256"]
                            and fingerprint(messages[0]["content"]) == event["system_prompt_sha256"], "interface prompt changed")
                    responses += 1
            dispatcher = FeasibleDispatcher(row, recorded=execution["dispatch"])
            result = run(tasks[row["task_id"]], replay_output / row["run_id"], row["condition"], 1, MODEL,
                         dispatcher=dispatcher, primary_kind="recorded_model_prefix", max_primary_decisions=MAX_PRIMARY,
                         environment_options=VARIANTS[row["variant"]][1])
            require(len(dispatcher.events) == len(execution["dispatch"]), "interface replay prefix changed")
            replays += 1
        else:
            result = run(tasks[row["task_id"]], replay_output / row["run_id"], row["condition"], 1, None,
                         environment_options=VARIANTS[row["variant"]][1])
        for field in ("cost", "terminal", "native_result", "independent_assessment"):
            require(json.loads(json.dumps(result[field])) == execution[field] == row.get(field, execution[field]), "interface replay differs: " + field)
        extra = diagnostics(execution, selected)
        require(extra == execution["interface_diagnostics"] == diagnostics(result, selected)
                and all(row[k] == v for k, v in extra.items()), "interface diagnostics changed")
        expected = None if execution["terminal"] in EXTERNAL_STOPS else extra["protocol_complete"]
        require(row["assessed_success"] == expected and row["native_safe_complete"] == execution["independent_assessment"]["safe_complete"]
                and row["snapshot_correct"] == execution["independent_assessment"]["snapshot_correct"]
                and row["forbidden_effect"] == execution["independent_assessment"]["forbidden_effect"], "interface outcome index changed")
        require(row["requests"] == sum(r["request_sent"] for r in selected)
                and row["usage"] == {k: sum(r.get("raw_response", {}).get("usage", {}).get(k, 0) or 0 for r in selected) for k in row["usage"]}, "interface cost index changed")
    require(sorted(used) == list(range(len(records))), "interface unbound/duplicate request")
    require(summarize(rows, records) == json.loads((output / "summary.json").read_text(encoding="utf-8")), "interface summary changed")
    result = {"model_replays": replays, "backend_rule_replays": 9, "response_classifications": responses,
              "journal_records_bound": len(used), "new_api_calls": 0}
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
        result = prepare(args.output)
        print(json.dumps({k: result[k] for k in ("model_trajectories", "max_requests")}))
    elif args.execute:
        result = execute(args.output, progress=lambda x: print(json.dumps(x), flush=True))
        print(json.dumps({k: result[k] for k in ("requests_sent", "parse_failures", "peak_cost_estimate_usd")}, indent=2))
    else:
        print(json.dumps(verify(args.output, args.verify), indent=2))


if __name__ == "__main__":
    main()
