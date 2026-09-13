"""Stateful V3 executor with artifact chaining and one bounded parameter-recovery retry."""
import argparse, json, time
from pathlib import Path

from agent.tools import MUTATING, execute_tool
from research.io import ROOT, digest, load_jsonl, resolve, write_json
from research.oracle import expected
from verifier.score import verify


def params_for(action, task, corrupt=False):
    source = task["params"]
    column = source["column"]
    if action in {"count_categories", "normalize_categories"}: column = source["category_column"]
    elif action == "normalize_dates": column = source["date_column"]
    elif action == "rolling_mean": column = source["other_column"]
    params = {"column": "__missing__" if corrupt else column, "group_by": source["date_column"],
              "other_column": source["other_column"], "lower": source["lower"], "upper": source["upper"], "window": source["window"]}
    return params


def run_plan(task, plan, gold, artifact_dir, recover=False, inject_error=False):
    if gold["decision"] == "clarify":
        passed = not plan
        return {"task_id": task["task_id"], "track": task["track"], "slice": task["slice"], "decision": "clarify" if not plan else "execute",
                "proposed_plan": plan, "gold_plan": gold["plan"], "steps": [], "recoveries": 0, "recovered": False,
                "planning_passed": passed, "execution_passed": passed, "passed": passed}
    current = resolve(task["dataset"]["uri"]); steps = []; recoveries = 0; execution_ok = True
    for index, action in enumerate(plan):
        step_ok = False
        for attempt in range(2 if recover else 1):
            corrupt = inject_error and index == 0 and attempt == 0
            params = params_for(action, task, corrupt=corrupt)
            before_hash = digest(current); started = time.perf_counter()
            try:
                result = execute_tool(action, {"uri": str(current), "params": params,
                                               "artifact_dir": Path(artifact_dir)/f"step_{index}"/f"attempt_{attempt}"})
                reference = expected(current, action, params)
                checked = verify(result, reference, [{"tool": action, "ok": True}],
                                 {"allowed_tools": task["allowed_tools"], "max_tool_calls": 1, "max_steps": 1,
                                  "max_seconds": 10, "elapsed_seconds": time.perf_counter()-started, "input_sha256": before_hash})
                step = {"index": index, "attempt": attempt, "action": action, "input_sha256": before_hash,
                        "result": result, "checks": checked["checks"], "passed": checked["passed"]}
                steps.append(step)
                if checked["passed"]:
                    if action in MUTATING: current = resolve(result["artifact"]["path"])
                    step_ok = True; break
            except Exception as exc:
                steps.append({"index": index, "attempt": attempt, "action": action, "input_sha256": before_hash,
                              "error": type(exc).__name__ + ": " + str(exc), "passed": False})
            if recover and attempt == 0: recoveries += 1
        if not step_ok:
            execution_ok = False; break
    planning_ok = plan == gold["plan"]
    recovered = bool(recoveries and execution_ok)
    return {"task_id": task["task_id"], "track": task["track"], "slice": task["slice"], "decision": "execute",
            "proposed_plan": plan, "gold_plan": gold["plan"], "steps": steps, "recoveries": recoveries, "recovered": recovered,
            "planning_passed": planning_ok, "execution_passed": execution_ok, "passed": planning_ok and execution_ok,
            "final_artifact_sha256": digest(current) if current.exists() else None}


def evaluate(mode="oracle", recover=False, inject_error=False, out=None):
    from research.v3_baselines import keyword_plan
    tasks = load_jsonl("tasks/v3/tasks.jsonl"); oracle = json.loads((ROOT/"tasks/v3/oracle.json").read_text(encoding="utf-8"))
    test = [t for t in tasks if t["split"] == "test"]
    records = []
    root = ROOT/"artifacts/v3_runtime"/(Path(out).stem if out else f"{mode}_{int(recover)}_{int(inject_error)}")
    for task in test:
        gold = oracle[task["task_id"]]
        if mode == "oracle": plan = list(gold["plan"])
        elif mode == "keyword": plan = keyword_plan(task["prompt"]) or ["profile_schema"]
        else: plan = []
        records.append(run_plan(task, plan, gold, root/task["task_id"], recover=recover, inject_error=inject_error))
    def stats(rows):
        return {"tasks": len(rows), "planning_passed": sum(r["planning_passed"] for r in rows),
                "execution_passed": sum(r["execution_passed"] for r in rows), "passed": sum(r["passed"] for r in rows),
                "recovered": sum(r["recovered"] for r in rows)}
    result = {"version": 3, "mode": mode, "recover": recover, "inject_error": inject_error, **stats(records),
              "by_slice": {s: stats([r for r in records if r["slice"] == s]) for s in sorted({r["slice"] for r in records})},
              "records": records}
    if out: write_json(ROOT/out, result)
    return result


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("--mode",choices=["oracle","keyword","empty"],default="oracle");p.add_argument("--recover",action="store_true");p.add_argument("--inject-error",action="store_true");p.add_argument("--out");a=p.parse_args()
    result=evaluate(mode=a.mode,recover=a.recover,inject_error=a.inject_error,out=a.out)
    print(json.dumps({k:v for k,v in result.items() if k!="records"},ensure_ascii=False,indent=2))
