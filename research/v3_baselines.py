"""Lightweight planning baselines for the v3 diagnostic benchmark."""
import argparse, hashlib, json, math, random
from collections import Counter, defaultdict
from pathlib import Path
from research.io import ROOT, load_jsonl, write_json

# Frozen v2 vocabulary. Do not add v3 test wording to this baseline.
TRAIN_HINTS = {
    "profile_schema": ("字段", "行列数"), "profile_missingness": ("缺失率",), "count_categories": ("频数", "类别计数"),
    "deduplicate": ("重复行",), "describe_numeric": ("基本统计量",), "normalize_dates": ("日期格式",),
    "clip_outliers": ("异常值",), "fill_missing": ("填补", "填充"), "normalize_categories": ("类别拼写",),
    "aggregate": ("总额", "汇总"), "correlate": ("相关系数",), "rolling_mean": ("移动平均",)}


def keyword_plan(prompt):
    found = []
    lower = prompt.lower()
    for action, hints in TRAIN_HINTS.items():
        positions = [lower.find(h.lower()) for h in hints if lower.find(h.lower()) >= 0]
        if positions: found.append((min(positions), action))
    return [a for _, a in sorted(found)]


def _ngrams(text, n=3):
    compact = " ".join(text.lower().split())
    return Counter(compact[i:i+n] for i in range(max(1, len(compact)-n+1)))


def _cos(a, b):
    common = sum(a[k] * b[k] for k in a.keys() & b.keys())
    den = math.sqrt(sum(v*v for v in a.values()) * sum(v*v for v in b.values()))
    return common / den if den else 0


def nearest_plan(task, examples):
    q = _ngrams(task["prompt"])
    best = max(examples, key=lambda x: (_cos(q, x[0]), x[2]))
    return list(best[1])


def evaluate(mode="keyword", tasks_path="tasks/v3/tasks.jsonl", oracle_path="tasks/v3/oracle.json", seed=1):
    tasks = load_jsonl(tasks_path); oracle = json.loads((ROOT/oracle_path).read_text(encoding="utf-8")); rng = random.Random(seed)
    train = [t for t in tasks if t["split"] == "train"]; test = [t for t in tasks if t["split"] == "test"]
    examples = [(_ngrams(t["prompt"]), oracle[t["task_id"]]["plan"], t["task_id"]) for t in train]
    rows = []
    for task in test:
        gold = oracle[task["task_id"]]
        if mode == "keyword":
            plan = keyword_plan(task["prompt"]) or ["profile_schema"]
            decision = "execute"
        elif mode == "nearest": plan = nearest_plan(task, examples); decision = "clarify" if not plan else "execute"
        elif mode == "random":
            candidates = [oracle[t["task_id"]]["plan"] for t in train]; plan = list(rng.choice(candidates)); decision = "clarify" if not plan else "execute"
        else: plan = list(gold["plan"]); decision = gold["decision"]
        rows.append({"task_id": task["task_id"], "track": task["track"], "predicted_plan": plan, "gold_plan": gold["plan"],
                     "decision": decision, "gold_decision": gold["decision"], "passed": plan == gold["plan"] and decision == gold["decision"]})
    by_track = {}
    for track in sorted({r["track"] for r in rows}):
        subset = [r for r in rows if r["track"] == track]; by_track[track] = {"passed": sum(r["passed"] for r in subset), "tasks": len(subset), "pass_rate": sum(r["passed"] for r in subset)/len(subset)}
    return {"benchmark_version": 3, "mode": mode, "seed": seed, "passed": sum(r["passed"] for r in rows), "tasks": len(rows),
            "pass_rate": sum(r["passed"] for r in rows)/len(rows), "by_track": by_track, "records": rows}


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--mode", choices=["keyword", "nearest", "random", "oracle"], default="keyword"); p.add_argument("--seed", type=int, default=1); p.add_argument("--out"); a = p.parse_args()
    result = evaluate(a.mode, seed=a.seed)
    if a.out: write_json(ROOT/a.out, result)
    print(json.dumps({k:v for k,v in result.items() if k != "records"}, ensure_ascii=False, indent=2))
