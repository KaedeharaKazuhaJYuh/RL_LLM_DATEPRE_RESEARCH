"""Create a deterministic value-perturbed benchmark with rebuilt verifier artifacts.

Unlike a wording-only split, changing CSV values invalidates old gold answers and
reference outputs. This generator writes the transformed datasets, aligned tasks,
and new independent verifier artifacts as one reproducible bundle.
"""

import argparse
import copy
import csv
import json
from pathlib import Path

from agent.analysis import analyze_task
from agent.tools import execute_tool


ROOT = Path(__file__).parents[1]
VALUE_TRANSFORMS = {
    "sample.csv": {"revenue": lambda value: f"{float(value) * 1.15 + 7:.2f}"},
    "churn.csv": {
        "tenure_months": lambda value: str(int(float(value)) + 1),
        "monthly_fee": lambda value: f"{float(value) * 1.10 + 3:.2f}",
    },
    "students.csv": {
        "study_hours": lambda value: f"{float(value) + 0.5:.2f}",
        "score": lambda value: f"{float(value) + 2:.2f}",
    },
}
FIRST_STAGE_ACTIONS = {
    "T01": "profile_schema", "T02": "profile_missingness", "T03": "count_categories",
    "T04": "deduplicate", "T05": "describe_numeric", "T06": "deduplicate",
    "T07": "normalize_dates", "T08": "clip_outliers", "T09": "fill_missing",
    "T10": "normalize_categories", "T11": "aggregate",
}


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def transform_csv(source, destination):
    with Path(source).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    for row in rows:
        for column, transform in VALUE_TRANSFORMS[Path(source).name].items():
            row[column] = transform(row[column])
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def expected_answer(task):
    action = FIRST_STAGE_ACTIONS[task["task_id"]]
    observation = execute_tool(action if action != "profile_schema" else "load_table", {
        "uri": task["dataset"]["uri"], "task_id": task["task_id"], "prompt": task["prompt"],
    })
    if action == "profile_schema":
        return observation["columns"]
    if action == "aggregate":
        return observation["totals"]
    return observation


def build_variant(source_tasks, source_gold, variant_root):
    data_root = variant_root / "data"
    source_files = {"data/sample.csv", "data/churn.csv", "data/students.csv"}
    uri_map = {}
    for uri in sorted(source_files):
        destination = data_root / Path(uri).name
        transform_csv(ROOT / uri, destination)
        uri_map[uri] = destination.as_posix()

    tasks = []
    for source in source_tasks:
        task = copy.deepcopy(source)
        task["dataset"]["uri"] = uri_map[task["dataset"]["uri"]]
        task["variant"] = {
            "name": "value_v1",
            "source_task_id": source["task_id"],
            "transform": "deterministic numeric value changes; schema, row order, contracts, prompts, and budgets unchanged",
        }
        tasks.append(task)

    gold = {}
    references = {}
    for task in tasks:
        task_id = task["task_id"]
        if task_id in FIRST_STAGE_ACTIONS:
            gold[task_id] = {
                "answer_type": source_gold[task_id]["answer_type"],
                "expected": expected_answer(task),
            }
        else:
            references[task_id] = analyze_task(task["dataset"]["uri"], task_id, task["prompt"])
    return tasks, gold, references


def main():
    parser = argparse.ArgumentParser(description="Generate a value-perturbed task bundle with new verifier artifacts.")
    parser.add_argument("--tasks", default="tasks/tasks.jsonl")
    parser.add_argument("--gold", default="tasks/gold_answers.json")
    parser.add_argument("--out-dir", default="tasks/variants/value_v1")
    args = parser.parse_args()
    source_tasks = read_jsonl(args.tasks)
    source_gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    out_dir = Path(args.out_dir)
    tasks, gold, references = build_variant(source_tasks, source_gold, out_dir)
    if [task["task_id"] for task in tasks] != [task["task_id"] for task in source_tasks]:
        raise ValueError("Task IDs must remain aligned with evaluation artifacts.")
    if [task["contract"] for task in tasks] != [task["contract"] for task in source_tasks]:
        raise ValueError("Contracts must not change in a value-only split.")
    write_jsonl(tasks, out_dir / "tasks.jsonl")
    (out_dir / "gold_answers.json").write_text(json.dumps(gold, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "reference_outputs.json").write_text(json.dumps(references, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(tasks)} value variants and {len(gold)} gold / {len(references)} reference artifacts to {out_dir}")


if __name__ == "__main__":
    main()

