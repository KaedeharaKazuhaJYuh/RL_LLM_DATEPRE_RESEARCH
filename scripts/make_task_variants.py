"""Create prompt-only task variants while preserving IDs, contracts, and gold answers.

The first robustness split intentionally changes task wording only. It does not alter
CSV values, so the existing independent gold and reference artifacts remain valid.
"""

import argparse
import json
from pathlib import Path


WRAPPERS = (
    "请基于当前 CSV 数据集完成以下分析，并给出可核验的结果：{prompt}。",
    "你的数据分析目标如下。请执行它，并清楚汇报结论：{prompt}。",
    "请把下面的需求作为一次独立的数据任务处理：{prompt}。",
    "请检查给定数据后完成这项工作；结果应当能够被复核：{prompt}。",
    "请围绕当前表格完成下列目标，并返回明确的分析结果：{prompt}。",
)


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def make_wording_variant(tasks):
    rows = []
    for index, task in enumerate(tasks):
        row = dict(task)
        row["prompt"] = WRAPPERS[index % len(WRAPPERS)].format(prompt=task["prompt"])
        row["variant"] = {
            "name": "wording_v1",
            "source_task_id": task["task_id"],
            "transform": "instruction wrapper only; dataset, contract, gold, and budget unchanged",
        }
        rows.append(row)
    return rows


def write_jsonl(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate robust prompt-only task variants.")
    parser.add_argument("--source", default="tasks/tasks.jsonl")
    parser.add_argument("--out", default="tasks/variants/wording_v1.jsonl")
    args = parser.parse_args()
    source = load_jsonl(args.source)
    variant = make_wording_variant(source)
    if [row["task_id"] for row in variant] != [row["task_id"] for row in source]:
        raise ValueError("Task IDs must be preserved so independent gold artifacts remain aligned.")
    if [row["contract"] for row in variant] != [row["contract"] for row in source]:
        raise ValueError("Contracts must be preserved in a wording-only variant.")
    write_jsonl(variant, Path(args.out))
    print(f"wrote {len(variant)} wording variants to {args.out}")


if __name__ == "__main__":
    main()

