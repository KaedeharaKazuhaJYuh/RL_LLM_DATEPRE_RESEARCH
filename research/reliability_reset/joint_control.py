"""Live joint evidence/action/termination planning with receipt-loss controls."""

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
from .evidence_planner import INTERFACES, E0_CARDS, public_view
from .evidence_state import COMPLETION_CONTRACT, evidence_state, supported_completion
from .planning_mechanism import CODE as PREVIOUS_CODE, Dispatcher, PROMPTS, system_prompt as read_prompt
from .recovery_credit import fingerprint, run, save


ARMS = ("combined", "read_plan", "joint_plan")
VARIANTS = {"healthy": ("healthy", {}), "semantic_error": ("semantic_error", {}),
            "lost_repair_receipt": ("semantic_error", {"repair_ack_loss": True})}
TASK_IDS = ("group-03", "window-03", "version-03")
MAX_REQUESTS = 432
CODE = tuple(dict.fromkeys((*PREVIOUS_CODE, "research/reliability_reset/evidence_state.py",
                           "research/reliability_reset/joint_control.py")))
JOINT_INSTRUCTION = (
    "\nUse the public decision support below to choose a cost-feasible action. "
    "Do not request a read when no checks remain. Verify analysis semantics from observed data and actual outputs. "
    "A bound successful CAS replace receipt confirms the cited candidate was published, not that its values are correct. "
    "If you verified that candidate, completion does not require another status or inspect. "
    "If publication remains unresolved and cannot be reconciled within budget, escalate instead of guessing. "
    "You still choose every action and parameter; decision support never executes a tool."
)


def effective_task(task):
    task = copy.deepcopy(task)
    task["contract"]["completion_evidence_v150"] = COMPLETION_CONTRACT
    return task


def design_cells():
    pairs = [(task, variant, interface) for task in TASK_IDS for variant in VARIANTS for interface in INTERFACES]
    random.Random(2026102450).shuffle(pairs)
    cells = []
    for i, (task, variant, interface) in enumerate(pairs):
        for arm in ARMS[i % 3:] + ARMS[:i % 3]:
            cells.append({"phase": "joint", "task_id": task, "variant": variant,
                          "condition": VARIANTS[variant][0], "interface": interface, "arm": arm})
    return cells


class JointDispatcher(Dispatcher):
    def presentation(self, observation):
        view = public_view(observation, self.cell["interface"], structured=True)
        arm = self.cell["arm"]
        if arm == "combined":
            # Keep the same information relation when names change; only prompt references are translated.
            prompt = PROMPTS["combined"]
            mapping = INTERFACES[self.cell["interface"]]
            for canonical in ("status", "inspect"):
                prompt = prompt.replace(canonical, mapping[canonical])
        elif arm == "read_plan":
            prompt = read_prompt({"phase": "transfer", "arm": "auto_plan"}, view)
        else:
            require(arm == "joint_plan", "unknown joint arm")
            view["decision_support"] = evidence_state(view, self.cell["interface"])
            prompt = SYSTEM + JOINT_INSTRUCTION
        return view, prompt


def prepare(output):
    output = Path(output).resolve()
    require(not output.exists(), "joint study destination must be new")
    tasks = [t for t in load() if t["id"] in TASK_IDS]
    protocol = {"version": __version__, "date": "2026-10-24", "kind": "joint_evidence_action_termination",
                "model_requested": MODEL, "temperature": 0, "thinking": "disabled", "cells": design_cells(),
                "arms": ARMS, "variants": VARIANTS, "interfaces": INTERFACES,
                "completion_contract": COMPLETION_CONTRACT, "joint_instruction": JOINT_INSTRUCTION,
                "score_migration": "Original native and independent scores retained. Add protocol_complete = original safe completion AND public current-report support under the explicit additive v150 contract, shared by every arm.",
                "negative_control": "Repair publish commits but its receipt is timeout; private commit truth never enters decision support. Unsupported stop is separately counted even if actual state is correct.",
                "action_policy": "Advisory cost-feasible list; all original tools/permissions remain. No forced stop, action substitution, retry or constrained-decoding rescue.",
                "model_trajectories": 54, "shared_backend_rules": 9, "max_requests": MAX_REQUESTS,
                "max_primary_calls": MAX_PRIMARY, "shared_caps": {"checks": 1, "mutations": 6, "decisions": 16},
                "peak_cost_estimate_ceiling_usd": 0.60, "peak_usd_per_million_tokens": {"input_uncached": 0.30, "output": 1.20},
                "pricing_source": "https://api-docs.deepseek.com/quick_start/pricing/", "pricing_checked_date": "2026-10-24",
                "tasks": [{"task_id": t["id"], "base_task_sha256": fingerprint(t), "effective_task_sha256": fingerprint(effective_task(t)),
                           "source_id": t["source_id"], "source_sha256": t["source_sha256"]} for t in tasks],
                "task_manifest_sha256": digest(MANIFEST), "code_sha256": {p: digest(REPO / p) for p in CODE},
                "primary_metrics": ["protocol_complete", "unsupported_stop under lost receipt", "rejected read after successful publication"],
                "other_metrics": ["original safe_complete", "final snapshot correctness", "forbidden effects", "tokens", "response bytes", "latency"],
                "split": "Three historical 03 instances in one environment; normal and receipt-loss controls are not independent task families.",
                "api_policy": "No retry or fallback. First provider failure stops further requests; planned cells remain missing."}
    save(output / "protocol.json", protocol)
    return protocol


def assess(execution):
    support = supported_completion(execution)
    published = any(s["action"] == "publish" and s["response"].get("ok") is True for s in execution["steps"])
    last = execution["decisions"][-1] if execution["decisions"] else {}
    support["post_publish_read_rejection"] = bool(published and last.get("kind") == "budget_rejection"
                                                  and last.get("proposal", {}).get("action") in E0_CARDS)
    return support


def summarize(rows, records):
    strata = defaultdict(Counter)
    indexed = defaultdict(dict)
    for r in rows:
        key = (r["variant"], r["interface"], r["arm"])
        strata[key].update(executions=1, resolved=int(r["assessed_success"] is not None),
                            protocol_complete=int(r["assessed_success"] is True), native_safe_complete=int(r["native_safe_complete"]),
                            snapshot_correct=int(r["snapshot_correct"]), unsupported_stop=int(r["unsupported_stop"]),
                            post_publish_read_rejection=int(r["post_publish_read_rejection"]), forbidden_effect=int(r["forbidden_effect"]),
                            requests=r["requests"], response_bytes=r["cost"]["response_bytes"], **r["usage"])
        if r["arm"] != "rule_only":
            indexed[(r["task_id"], r["variant"], r["interface"])][r["arm"]] = r
    contrasts = []
    for control in ("combined", "read_plan"):
        for variant in VARIANTS:
            counts = Counter(gains=0, losses=0, ties=0, missing=0)
            for key, group in indexed.items():
                if key[1] != variant:
                    continue
                a, b = group[control]["assessed_success"], group["joint_plan"]["assessed_success"]
                counts["missing" if a is None or b is None else "gains" if b and not a else "losses" if a and not b else "ties"] += 1
            contrasts.append({"comparison": "joint_plan_vs_" + control, "variant": variant, **counts})
    return {"version": __version__, "model_executions": sum(r["arm"] != "rule_only" for r in rows),
            "backend_rule_controls": sum(r["arm"] == "rule_only" for r in rows), "environment_families": 1,
            "requests_sent": sum(r["request_sent"] for r in records), "received_responses": sum(r["category"] == "received" for r in records),
            "parse_failures": sum(bool(r.get("parse_error")) for r in records), "provider_errors": sum(r["category"] == "provider_error" for r in records),
            "models_returned": sorted({r["raw_response"].get("model", "unknown") for r in records if r["category"] == "received"}),
            "known_usage": {k: sum(r.get("raw_response", {}).get("usage", {}).get(k, 0) or 0 for r in records)
                            for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
            "peak_cost_estimate_usd": sum(r.get("peak_cost_estimate_usd", 0) for r in records),
            "native_exact_agree": sum(r["native_exact_agree"] for r in rows),
            "strata": [{"variant": k[0], "interface": k[1], "arm": k[2], **v} for k, v in sorted(strata.items())], "contrasts": contrasts}


def execute(output, client=None, progress=None):
    output = Path(output).resolve()
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    require(protocol["version"] == __version__ and protocol["cells"] == design_cells()
            and protocol["completion_contract"] == COMPLETION_CONTRACT and protocol["joint_instruction"] == JOINT_INSTRUCTION,
            "joint protocol mismatch")
    for name, sha in protocol["code_sha256"].items():
        require(digest(REPO / name) == sha, "joint code changed since freeze")
    require(digest(MANIFEST) == protocol["task_manifest_sha256"] and not (output / "executions").exists(), "joint input/results changed")
    tasks = {t["id"]: effective_task(t) for t in load() if t["id"] in TASK_IDS}
    require(all(fingerprint(tasks[t["task_id"]]) == t["effective_task_sha256"] for t in protocol["tasks"]), "joint task changed")
    client = Client(output / "requests.jsonl", max_calls=MAX_REQUESTS) if client is None else client
    require(not client.records and client.calls == 0 and client.max_calls == MAX_REQUESTS, "joint client must be fresh")
    rows, controls = [], set()
    protocol_hash = digest(output / "protocol.json")
    for i, cell in enumerate(protocol["cells"]):
        task = tasks[cell["task_id"]]
        condition, options = VARIANTS[cell["variant"]]
        key = "--".join(cell[k] for k in ("task_id", "variant", "interface", "arm"))
        dispatcher = JointDispatcher(cell, client=client)
        start = len(client.records)
        result = run(task, output / "executions" / key, condition, 1, MODEL, dispatcher=dispatcher,
                     primary_kind="model_api", max_primary_decisions=MAX_PRIMARY, environment_options=options)
        records = client.records[start:]
        require(len(records) == len(dispatcher.events) == len(result["decisions"]), "joint journal length mismatch")
        result["dispatch"] = dispatcher.events
        for event, record, decision in zip(dispatcher.events, records, result["decisions"]):
            require(event["view_sha256"] == record["observation_sha256"] and event["canonical_observation_sha256"] == decision["public_observation_sha256"], "joint observation binding mismatch")
            event["record_sha256"] = fingerprint(record)
        pending = [(cell["arm"], key, result, records)]
        pair = (cell["task_id"], cell["variant"])
        if pair not in controls:
            controls.add(pair)
            rule = run(task, output / "executions" / (key + "--rule"), condition, 1, None, environment_options=options)
            require(rule["public_input_sha256"] == result["public_input_sha256"], "joint rule input mismatch")
            pending.append(("rule_only", key + "--rule", rule, []))
        for arm, run_id, execution, selected in pending:
            execution.update(cell={**cell, "arm": arm}, protocol_sha256=protocol_hash, public_support=assess(execution))
            path = output / "executions" / run_id / "execution.json"
            save(path, execution)
            value = None if execution["terminal"] in EXTERNAL_STOPS else execution["public_support"]["protocol_complete"]
            rows.append({**cell, "arm": arm, "interface": "backend" if arm == "rule_only" else cell["interface"],
                         "run_id": run_id, "public_input_sha256": execution["public_input_sha256"], "assessed_success": value,
                         **execution["public_support"], "native_safe_complete": execution["independent_assessment"]["safe_complete"],
                         "snapshot_correct": execution["independent_assessment"]["snapshot_correct"], "forbidden_effect": execution["independent_assessment"]["forbidden_effect"],
                         "terminal": execution["terminal"], "cost": execution["cost"], "requests": sum(r["request_sent"] for r in selected),
                         "usage": {k: sum(r.get("raw_response", {}).get("usage", {}).get(k, 0) or 0 for r in selected)
                                   for k in ("prompt_tokens", "completion_tokens", "total_tokens")},
                         "native_exact_agree": execution["native_exact_agree"], "evidence": path.relative_to(output).as_posix(), "evidence_sha256": digest(path)})
        if progress:
            progress({"completed": i + 1, **cell, **assess(result), "terminal": result["terminal"], "requests": client.calls})
    require(digest(output / "protocol.json") == protocol_hash, "joint protocol changed during execution")
    summary = summarize(rows, client.records)
    save(output / "runs.json", rows)
    save(output / "summary.json", summary)
    lines = ["# 1.0.50：证据、动作与终止联合规划", "", "| 条件 | 接口 | 系统 | 协议完成/解析单元 | 原生完成 | 无证据停止 | 发布后多读失败 |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: |"]
    for s in summary["strata"]:
        lines.append(f"| {s['variant']} | {s['interface']} | {s['arm']} | {s['protocol_complete']}/{s['resolved']} | {s['native_safe_complete']} | {s['unsupported_stop']} | {s['post_publish_read_rejection']} |")
    lines += ["", "原生评分保持原样。协议完成新增公开证据要求，各臂任务说明相同；不能与旧版本分数直接合并。",
              "回执丢失条件下，实际提交成功不等于模型拥有成功确认。规划器不强制停止，也不替换任何模型提案。"]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return summary


def verify(output, replay_output):
    output, replay_output = Path(output).resolve(), Path(replay_output).resolve()
    require(not replay_output.exists(), "joint replay destination must be new")
    protocol = json.loads((output / "protocol.json").read_text(encoding="utf-8"))
    for name, sha in protocol["code_sha256"].items():
        require(digest(REPO / name) == sha, "joint replay source mismatch")
    rows = json.loads((output / "runs.json").read_text(encoding="utf-8"))
    records = [json.loads(s) for s in (output / "requests.jsonl").read_text(encoding="utf-8").splitlines()]
    tasks = {t["id"]: effective_task(t) for t in load()}
    used, count, responses = [], 0, 0
    for row in rows:
        require(digest(output / row["evidence"]) == row["evidence_sha256"], "joint execution hash mismatch")
        execution = json.loads((output / row["evidence"]).read_text(encoding="utf-8"))
        support = assess(execution)
        require(support == execution["public_support"] and all(row[k] == v for k, v in support.items()), "joint support classification mismatch")
        require(row["assessed_success"] == (None if execution["terminal"] in EXTERNAL_STOPS else support["protocol_complete"]), "joint outcome index mismatch")
        if row["arm"] == "rule_only":
            continue
        mapping = INTERFACES[row["interface"]]
        reverse = {v: k for k, v in mapping.items()}
        for event, decision in zip(execution["dispatch"], execution["decisions"], strict=True):
            record = records[event["journal_index"]]
            used.append(event["journal_index"])
            require(fingerprint(record) == event["record_sha256"] and event["view_sha256"] == record["observation_sha256"]
                    and event["canonical_observation_sha256"] == decision["public_observation_sha256"], "joint response binding mismatch")
            if record["category"] == "received":
                require(not record["response_redacted"], "joint credential echo requires separate review")
                proposal, error = parse_action(record["raw_response"], tuple(mapping.values()))
                canonical = {**proposal, "action": reverse.get(proposal["action"], proposal["action"])}
                require(proposal == event["advertised_proposal"] and canonical == decision["proposal"] and error == record["parse_error"], "joint response classification mismatch")
                messages = record["request_body"]["messages"]
                require(fingerprint(json.loads(messages[1]["content"])) == event["view_sha256"]
                        and fingerprint(messages[0]["content"]) == event["system_prompt_sha256"], "joint request prompt mismatch")
                responses += 1
        dispatcher = JointDispatcher(row, recorded=execution["dispatch"])
        result = run(tasks[row["task_id"]], replay_output / row["run_id"], row["condition"], 1, MODEL,
                     dispatcher=dispatcher, primary_kind="recorded_model_prefix", max_primary_decisions=MAX_PRIMARY,
                     environment_options=VARIANTS[row["variant"]][1])
        for field in ("cost", "terminal", "native_result", "independent_assessment"):
            require(json.loads(json.dumps(result[field])) == execution[field], "joint replay differs: " + field)
        require(assess(result) == support and len(dispatcher.events) == len(execution["dispatch"]), "joint replay support/prefix mismatch")
        count += 1
    require(sorted(used) == list(range(len(records))), "joint unbound/duplicate request")
    require(summarize(rows, records) == json.loads((output / "summary.json").read_text(encoding="utf-8")), "joint summary mismatch")
    result = {"model_replays": count, "response_classifications": responses, "journal_records_bound": len(used), "new_api_calls": 0}
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
        protocol = prepare(args.output)
        print(json.dumps({"model_trajectories": protocol["model_trajectories"], "max_requests": MAX_REQUESTS}))
    elif args.execute:
        result = execute(args.output, progress=lambda x: print(json.dumps(x), flush=True))
        print(json.dumps({k: result[k] for k in ("requests_sent", "parse_failures", "contrasts", "peak_cost_estimate_usd")}, indent=2))
    else:
        print(json.dumps(verify(args.output, args.verify), indent=2))


if __name__ == "__main__":
    main()
