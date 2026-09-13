"""Generate the v3 planner benchmark with source and template-family holdouts."""
import csv, hashlib, json, random
from pathlib import Path

from agent.tools import ACTIONS
from research.io import ROOT, digest, write_json, write_table

SEED = 20260913
SINGLE = [
    ("profile_schema", "列出字段类型和表的尺寸", "Tell me the table shape and infer each field type without changing the file."),
    ("profile_missingness", "计算各列缺失率", "Which field has the worst null-data problem? Include every column's rate."),
    ("count_categories", "统计类别列频数", "Build a frequency table for the labels in {category}."),
    ("deduplicate", "删除重复记录", "Keep one copy of identical observations and persist the cleaned table."),
    ("describe_numeric", "给出数值列描述统计", "I need count, mean, spread and range for {value}."),
    ("normalize_dates", "统一日期列格式", "Make {date} machine-readable; malformed calendar values may become empty."),
    ("clip_outliers", "按给定上下界截断异常值", "Winsorize {value} to the supplied floor and ceiling and save the result."),
    ("fill_missing", "使用中位数填补空值", "Patch numeric gaps in {value} with a robust central value."),
    ("normalize_categories", "清理类别拼写", "Canonicalize {category}: trim surrounding whitespace and ignore letter case."),
    ("aggregate", "按日期分组汇总金额", "Produce period-level totals of {value}, grouped by {date}."),
    ("correlate", "计算两个数值字段相关性", "Quantify the linear association between {value} and {metric}."),
    ("rolling_mean", "计算三期移动平均", "Smooth {metric} over a trailing window of three complete observations."),
]

COMPOSITIONS = [
    (("deduplicate", "profile_missingness"), "先删除重复记录，再检查各列缺失情况", "Remove repeated observations before auditing null rates."),
    (("fill_missing", "describe_numeric"), "填补金额空值后再汇总描述统计", "Repair numeric gaps in {value}, then summarize its distribution."),
    (("normalize_categories", "count_categories"), "规范类别后再统计频数", "Canonicalize {category} before building its frequency table."),
    (("normalize_dates", "aggregate"), "清理日期后按期汇总金额", "Parse {date} first, then total {value} by the cleaned period."),
    (("clip_outliers", "correlate"), "截断金额异常值后计算相关性", "Cap extreme {value} values before measuring association with {metric}."),
    (("deduplicate", "rolling_mean"), "去重后计算三期移动平均", "Drop identical rows, then smooth {metric} using three complete observations."),
]

CLARIFY = [
    ("清理这份表，做得合理一些", "Clean this dataset appropriately."),
    ("看看金额有没有问题并处理", "Fix whatever is wrong with the numeric field."),
]


def _task_id(source, track, index):
    return hashlib.sha256(f"v3/{source}/{track}/{index}".encode()).hexdigest()[:16]


def _render(text, names):
    return text.format(**names)


def build(out_dir=None, sources=24):
    out = Path(out_dir or ROOT / "tasks/v3")
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    tasks, oracle, datasets = [], {}, {}
    for source in range(sources):
        split = "train" if source < sources // 2 else "test"
        columns = (["period", "area", "amount", "segment", "signal"] if source % 3 == 0 else
                   ["日期", "地区", "销售额", "客群", "观测值"] if source % 3 == 1 else
                   ["when", "zone", "net_value", "class_name", "measure"])
        date, region, value, category, metric = columns
        names = {"date": date, "region": region, "value": value, "category": category, "metric": metric}
        rows = []
        for i in range(15):
            amount = round(rng.uniform(5, 95), 2)
            rows.append(dict(zip(columns, [f"2026-{i % 5 + 1:02d}", "N" if i % 2 else "S", str(amount), [" a ", "B", "A", " b "][i % 4], str(round(amount * .7 + rng.uniform(-5, 5), 2))])))
        rows[2][value] = ""; rows[8][value] = "280"; rows[4][date] = "bad-date"; rows.append(dict(rows[0]))
        data_path = out / "data" / f"source_{source:02d}.csv"
        write_table(data_path, columns, rows)
        uri = data_path.relative_to(ROOT).as_posix() if data_path.is_relative_to(ROOT) else data_path.as_posix()
        datasets[uri] = {"sha256": digest(data_path), "source_id": f"v3_source_{source:02d}", "split": split}

        for i, (action, train_text, test_text) in enumerate(SINGLE):
            prompt = _render(train_text if split == "train" else test_text, names)
            tid = _task_id(source, "single", i)
            tasks.append(_public(tid, source, split, "single", prompt, uri, columns, names))
            oracle[tid] = {"plan": [action], "decision": "execute"}
        for i, (plan, train_text, test_text) in enumerate(COMPOSITIONS):
            prompt = _render(train_text if split == "train" else test_text, names)
            tid = _task_id(source, "composition", i)
            tasks.append(_public(tid, source, split, "composition", prompt, uri, columns, names, max_steps=len(plan)))
            oracle[tid] = {"plan": list(plan), "decision": "execute"}
        for i, (train_text, test_text) in enumerate(CLARIFY):
            prompt = train_text if split == "train" else test_text
            tid = _task_id(source, "clarification", i)
            tasks.append(_public(tid, source, split, "clarification", prompt, uri, columns, names, max_steps=0))
            oracle[tid] = {"plan": [], "decision": "clarify"}

    rng.shuffle(tasks)
    tasks_path = out / "tasks.jsonl"
    tasks_path.write_text("".join(json.dumps(t, ensure_ascii=False, separators=(",", ":")) + "\n" for t in tasks), encoding="utf-8", newline="\n")
    write_json(out / "oracle.json", oracle)
    prompt_sets = {s: {t["prompt"] for t in tasks if t["split"] == s} for s in ("train", "test")}
    write_json(out / "manifest.json", {
        "version": 3, "seed": SEED, "tasks_sha256": digest(tasks_path), "oracle_sha256": digest(out / "oracle.json"),
        "counts": {s: sum(t["split"] == s for t in tasks) for s in ("train", "test")},
        "tracks": {k: sum(t["track"] == k for t in tasks) for k in ("single", "composition", "clarification")},
        "source_overlap": False, "exact_prompt_overlap": bool(prompt_sets["train"] & prompt_sets["test"]), "datasets": datasets,
        "scope": "synthetic planner diagnostic; source and wording-family holdout; plans are scored but not yet executed end to end"
    })
    return tasks, oracle


def _public(tid, source, split, track, prompt, uri, columns, names, max_steps=1):
    return {"schema_version": 3, "task_id": tid, "source_id": f"v3_source_{source:02d}", "split": split,
            "track": track, "prompt": prompt, "dataset": {"uri": uri, "columns": columns},
            "params": {"column": names["value"], "category_column": names["category"], "date_column": names["date"],
                       "other_column": names["metric"], "lower": 0, "upper": 100, "window": 3},
            "allowed_tools": ACTIONS, "constraints": {"max_steps": max_steps, "max_tool_calls": max_steps}}


if __name__ == "__main__":
    generated, _ = build()
    print(f"generated {len(generated)} v3 tasks")
