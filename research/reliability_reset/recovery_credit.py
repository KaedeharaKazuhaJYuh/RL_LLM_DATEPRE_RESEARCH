"""Offline primary/helper/replacement experiment on historical development tasks.

All controllers receive public JSON only. Provider transport is injected separately.
"""

import argparse
import copy
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from faultda_bench.semantic.environment import SemanticEnv, TOOLS
from faultda_bench.semantic.oracle import evaluate as native_evaluate
from faultda_bench.semantic.policies import choose
from faultda_bench.semantic.tasks import load, MANIFEST, REPO

from . import __version__
from .audit import digest, require
from .semantic_facts import rows_from_database


POLICIES = ("generic_verify", "version_refresh", "task_semantic")
CHECK_BUDGETS = (1, 4)
CONDITIONS = {
    "healthy": {},
    "benign_reorder": {},
    "semantic_error": {"semantic_fault": True},
    "before_commit_timeout": {"commit_fault": True, "boundary": "before_commit"},
    "after_commit_timeout": {"commit_fault": True, "boundary": "after_commit"},
    "semantic_and_ack_loss": {"semantic_fault": True, "commit_fault": True, "boundary": "after_commit"},
}


class ControllerStop(RuntimeError):
    """A recorded controller/transport limit, never a fabricated stop proposal."""


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def exact_assessment(folder, contract, catalog, dimension, input_hashes, records):
    """Separate Fraction/CSV reference; no call to native oracle or tool math."""
    version = catalog["snapshot" if contract["version_policy"] == "snapshot" else "latest"]
    groups = defaultdict(set)
    for row in dimension:
        groups[row["key"]].add(row["group"])
    totals = {}
    with (Path(folder) / (version + ".csv")).open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["value"] == "":
                continue
            if contract["family"] == "window":
                instant = datetime.fromisoformat(row["time"])
                if not datetime.fromisoformat(contract["start"]) <= instant < datetime.fromisoformat(contract["end"]):
                    continue
            if contract["family"] == "group":
                require(len(groups[row["key"]]) == 1, "ambiguous dimension business key")
                label = next(iter(groups[row["key"]]))
            else:
                label = "total"
            totals[label] = totals.get(label, Fraction(0)) + Fraction(row["value"])
    intact = all(digest(Path(folder) / (v + ".csv")) == h for v, h in input_hashes.items())

    def correct(content):
        try:
            output = content["output"]
            return intact and content["version"] == version and content["input_sha256"] == input_hashes[version] and set(output) == set(totals) and all(
                type(output[k]) in (int, float) and abs(Fraction(str(output[k])) - value) <=
                max(Fraction(1, 10**9), abs(value) / 10**9) for k, value in totals.items())
        except (KeyError, TypeError, ValueError, OverflowError, ZeroDivisionError):
            return False

    correctness = {r["revision"]: correct(r["content"]) for r in records}
    active = [r for r in records if r["active"]]
    return {"snapshot_correct": intact and len(active) == 1 and correctness[active[0]["revision"]],
            "source_intact": intact, "record_correctness": correctness,
            "reference": {"version": version, "totals_exact": {k: str(v) for k, v in totals.items()}}}


def run(task, folder, condition, budget, primary, assisted=False, dispatcher=choose,
        *, primary_kind="programmatic_rule", max_primary_decisions=16):
    """Run one system. A primary stop proposal becomes a charged handoff if assisted."""
    require(condition in CONDITIONS and budget in CHECK_BUDGETS, "unknown experiment cell")
    require((primary is None or isinstance(primary, str) and bool(primary)) and not (primary is None and assisted), "invalid controller")
    require(dispatcher is not choose or primary in (*POLICIES, None), "named controller requires dispatcher")
    require(type(max_primary_decisions) is int and 1 <= max_primary_decisions <= 16, "invalid primary horizon")
    task = copy.deepcopy(task)
    if condition == "benign_reorder":
        for version in task["versions"]:
            task["versions"][version].reverse()
    env = SemanticEnv(task, folder, budget=budget, **CONDITIONS[condition])
    public = env.observation()
    initial = rows_from_database(env.db)
    role = "helper" if primary is None else "primary"
    total_decisions, handoffs, primary_decisions = 0, 0, 0
    captures, decisions = [], []
    while not env.terminal:
        if total_decisions >= 16:
            env.terminal = "budget_exceeded"
            break
        if role == "primary" and primary_decisions >= max_primary_decisions:
            env.terminal = "primary_limit"
            break
        observation = json.loads(json.dumps(env.observation(), allow_nan=False))
        observation["remaining"]["decisions"] = 16 - total_decisions
        policy = primary if role == "primary" else "task_semantic"
        total_decisions += 1
        primary_decisions += int(role == "primary")
        actor_kind = primary_kind if role == "primary" else "public_rule"
        try:
            # A named model dispatcher is never used for the deterministic helper.
            proposal = (dispatcher if role == "primary" else choose)(observation, policy)
        except ControllerStop as error:
            env.terminal = str(error)
            decisions.append({"index": total_decisions - 1, "actor": role, "actor_kind": actor_kind,
                              "public_observation_sha256": fingerprint(observation), "kind": "controller_stop",
                              "reason": str(error)})
            break
        handoff = role == "primary" and assisted and proposal["action"] in ("stop", "escalate")
        decisions.append({"index": total_decisions - 1, "actor": role, "actor_kind": actor_kind, "public_observation_sha256": fingerprint(observation),
                          "proposal": proposal, "kind": "handoff" if handoff else "tool_action"})
        if handoff:
            handoffs += 1
            role = "helper"
            continue
        action = proposal["action"]
        if (action in ("status", "inspect", "inputs", "catalog") and env.cost["checks"] >= budget
                or action in ("stage", "publish") and env.cost["mutations"] >= 6):
            decisions[-1]["kind"] = "budget_rejection"
            env.terminal = "budget_exceeded"
            break
        before = rows_from_database(env.db)
        env.step(proposal["action"], proposal.get("params"))
        captures.append({"index": len(captures), "actor": role, "actor_kind": actor_kind, **copy.deepcopy(env.history[-1]),
                         "before": before, "after": rows_from_database(env.db)})
    records = rows_from_database(env.db)
    exact = exact_assessment(env.folder, env.task["contract"], env.task["catalog"], env.task["dimension"], env.task["version_hashes"], records)
    created_by, duplicates = {}, []
    for step in captures:
        old = {r["revision"] for r in step["before"]}
        new = [r["revision"] for r in step["after"] if r["revision"] not in old]
        created_by.update({revision: step["actor"] for revision in new})
        if new and sum(r["active"] for r in step["after"]) > 1:
            duplicates.append({"step": step["index"], "actor": step["actor"], "revisions": new})
    wrong = [{"revision": rev, "actor": created_by[rev]} for rev, correct in exact["record_correctness"].items()
             if not correct and rev in created_by]
    exact["forbidden_effect"] = bool(wrong or duplicates or not exact["source_intact"])
    exact["safe_complete"] = exact["snapshot_correct"] and env.terminal == "stop" and not exact["forbidden_effect"]
    exact.update(wrong_publications=wrong, duplicate_events=duplicates)
    native = native_evaluate(env)
    cost = {**env.cost, "decisions": total_decisions, "tool_decisions": env.cost["decisions"], "handoff_decisions": handoffs,
            "unexecuted_decisions": sum(d["kind"] in ("budget_rejection", "controller_stop") for d in decisions)}
    require(cost["checks"] <= budget and cost["mutations"] <= 6 and total_decisions <= 16, "experiment exceeded shared budget")
    return {"task_id": task["id"], "analysis_intent": task["contract"]["family"], "source_id": task["source_id"],
            "condition": condition, "checks_budget": budget, "primary": primary, "primary_kind": primary_kind,
            "assisted": assisted, "max_primary_decisions": max_primary_decisions,
            "public_input": public, "public_input_sha256": fingerprint(public),
            "tools_sha256": fingerprint(TOOLS), "caps": {"checks": budget, "mutations": 6, "decisions": 16},
            "initial_records": initial, "terminal": env.terminal, "decisions": decisions, "steps": captures,
            "cost": cost, "native_result": native, "independent_assessment": exact,
            "native_exact_agree": native["safe_complete"] == exact["safe_complete"] and native["terminal_correct"] == exact["snapshot_correct"]}


def summarize(rows):
    indexed = {}
    aggregate = defaultdict(lambda: Counter(executions=0, safe_complete=0, checks=0, mutations=0, decisions=0))
    for row in rows:
        cell = (row["task_id"], row["condition"], row["checks_budget"], row["system"])
        require(cell not in indexed, "duplicate experiment cell")
        indexed[cell] = row
        key = (row["analysis_intent"], row["condition"], row["checks_budget"], row["system"])
        aggregate[key].update(executions=1, safe_complete=int(row["independent_safe_complete"]),
                              **{k: row["cost"][k] for k in ("checks", "mutations", "decisions")})
    triplets, signatures = [], Counter()
    for row in rows:
        if row["system"] not in POLICIES:
            continue
        prefix = (row["task_id"], row["condition"], row["checks_budget"])
        other, replacement = indexed[(*prefix, row["system"] + "+helper")], indexed[(*prefix, "helper_only")]
        require(row["public_input_sha256"] == other["public_input_sha256"] == replacement["public_input_sha256"]
                and row["tools_sha256"] == other["tools_sha256"] == replacement["tools_sha256"]
                and row["caps"] == other["caps"] == replacement["caps"], "unmatched primary/helper/replacement cell")
        a, ah, h = [int(r["independent_safe_complete"]) for r in (row, other, replacement)]
        signature = f"{a}{ah}{h}"
        signatures[signature] += 1
        triplets.append({"task_id": row["task_id"], "analysis_intent": row["analysis_intent"], "condition": row["condition"],
                         "checks_budget": row["checks_budget"], "policy": row["system"], "A": a, "AH": ah, "H": h,
                         "assistance_gain": ah - a, "gain_over_replacement": ah - h, "signature": signature})
    return {"executions": len(rows), "task_instances": len({r["task_id"] for r in rows}), "environment_families": 1,
            "analysis_intents": sorted({r["analysis_intent"] for r in rows}), "independent_sample_size": None,
            "native_exact_agree": sum(r["native_exact_agree"] for r in rows), "triplet_count": len(triplets),
            "triplet_signatures": dict(sorted(signatures.items())), "triplets": triplets,
            "strata": [{"analysis_intent": k[0], "condition": k[1], "checks_budget": k[2], "system": k[3], **v}
                       for k, v in sorted(aggregate.items())]}


def write_report(summary, output):
    lines = ["# 恢复功劳归因：离线原型结果", "", f"版本 {__version__}；{summary['executions']} 次程序控制执行，"
             f"{summary['task_instances']} 个历史开发实例，一个环境家族，三个分析意图。", "",
             "A=策略单独，AH=策略+修复器，H=修复器单独；三者工具权限与总预算相同。不是 LLM 能力实验。", "",
             "| A/AH/H | 单元数 | 含义 |", "| --- | ---: | --- |"]
    names = {"000": "均未完成", "001": "组合失败但替代修复器成功", "010": "协同候选", "011": "帮助有效但替代对照已经足够",
             "100": "帮助造成负作用", "101": "帮助造成负作用且替代修复器成功", "110": "组合/自主成功，替代修复器失败", "111": "均成功"}
    for signature, count in summary["triplet_signatures"].items():
        lines.append(f"| {signature} | {count} | {names[signature]} |")
    lines += ["", "上述单元嵌套在历史任务中，不能当作独立样本。相同 helper_only 执行被多个策略对照共享，不能重复计为更多实验。", "",
              "## 按意图、条件、检查上限分开报告", "", "| 意图 | 条件 | 检查上限 | 系统 | 安全完成/执行数 | 总检查/写入/决策 |",
              "| --- | --- | ---: | --- | ---: | --- |"]
    for s in summary["strata"]:
        lines.append(f"| {s['analysis_intent']} | {s['condition']} | {s['checks_budget']} | {s['system']} | {s['safe_complete']}/{s['executions']} | {s['checks']}/{s['mutations']}/{s['decisions']} |")
    lines += ["", "完整三元组、成本与全部执行索引见 summary.json 和 runs.json；每次执行的原始响应、分角色动作、SQLite 与输入 CSV 单独保留。",
              "下一步以固定 DeepSeek 接口替换 primary 规则，检查同一模型的自主恢复、帮助依赖与交接干扰是否仍能被区分。"]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def build(output, task_ids=None, progress=None):
    output = Path(output).resolve()
    require(not output.exists(), "experiment destination must be new")
    tasks = load()
    if task_ids is not None:
        tasks = [t for t in tasks if t["id"] in set(task_ids)]
        require({t["id"] for t in tasks} == set(task_ids), "unknown requested task")
    require(tasks, "no tasks selected")
    design = {"version": __version__, "date": "2026-10-24", "study": "exploratory_programmatic_controls",
              "policies": POLICIES, "helper": "public task_semantic rule", "conditions": CONDITIONS,
              "check_budgets": CHECK_BUDGETS, "shared_caps": {"mutations": 6, "decisions": 16},
              "handoff": "stop/escalate proposal consumes one decision; terminal action not executed before helper",
              "systems": [*(p for policy in POLICIES for p in (policy, policy + "+helper")), "helper_only"],
              "task_manifest_sha256": digest(MANIFEST), "tasks": [{"id": t["id"], "task_sha256": fingerprint(t),
              "source_id": t["source_id"], "source_path": t["source_path"], "source_sha256": t["source_sha256"],
              "split": "historical_development"} for t in tasks],
              "attribution": json.loads(MANIFEST.read_text(encoding="utf-8"))["attribution"],
              "expected_executions": len(tasks) * len(CONDITIONS) * len(CHECK_BUDGETS) * 7,
              "metrics": ["A/AH/H safe-completion triplet", "AH-A", "AH-H", "per-intent cost and success"],
              "primary_metric": "safe_complete using independent Fraction/CSV/SQLite plus observed actor/effect history",
              "native_metrics": "entire original oracle result retained; do not select outcome-only subscore to imply an uncovered grader bug",
              "model_calls": 0, "independent_sample_size": None}
    for task in tasks:
        require(digest(REPO / task["source_path"]) == task["source_sha256"], "task upstream changed")
    save(output / "study_design.json", design)  # Frozen before the first episode.
    design_hash = digest(output / "study_design.json")
    rows = []
    for task in tasks:
        for condition in CONDITIONS:
            for budget in CHECK_BUDGETS:
                for system in design["systems"]:
                    key = f"{task['id']}--{condition}--b{budget}--{system}"
                    assisted = system.endswith("+helper")
                    primary = None if system == "helper_only" else system.removesuffix("+helper")
                    folder = output / "executions" / key
                    execution = run(task, folder, condition, budget, primary, assisted)
                    execution["design_sha256"] = design_hash
                    save(folder / "execution.json", execution)
                    rows.append({"run_id": key, "system": system, "evidence": (folder / "execution.json").relative_to(output).as_posix(),
                                 "evidence_sha256": digest(folder / "execution.json"),
                                 **{k: execution[k] for k in ("task_id", "analysis_intent", "condition", "checks_budget", "public_input_sha256", "tools_sha256", "caps", "cost", "native_exact_agree")},
                                 "independent_safe_complete": execution["independent_assessment"]["safe_complete"],
                                 "native_safe_complete": execution["native_result"]["safe_complete"],
                                 "native_contract_complete": execution["native_result"]["contract_complete"]})
        if progress:
            progress({"completed_task": task["id"], "executions": len(rows)})
    require(digest(output / "study_design.json") == design_hash, "design changed during execution")
    summary = summarize(rows)
    save(output / "runs.json", rows)
    save(output / "summary.json", summary)
    write_report(summary, output)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tasks", nargs="+")
    args = parser.parse_args()
    try:
        result = build(args.output, args.tasks, progress=lambda x: print(json.dumps(x), flush=True))
    except (KeyError, ValueError, TypeError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({k: result[k] for k in ("executions", "triplet_count", "triplet_signatures", "native_exact_agree")}, indent=2))


if __name__ == "__main__":
    main()
