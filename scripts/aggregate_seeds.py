import argparse
import json
import re
import statistics
from pathlib import Path

from experiments.aggregate import read, summarize


def method_and_seed(path):
    stem = Path(path).stem
    match = re.match(r"(.+)_seed(\d+)(.*)$", stem)
    if not match:
        return stem, None
    method, seed, suffix = match.groups()
    variant = suffix.strip("_")
    label = f"{method}_{variant}" if variant else method
    return label, int(seed)


def mean_std(values):
    if not values:
        return 0.0, 0.0
    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0
    return round(mean, 4), round(std, 4)


def summarize_seeds(files):
    grouped = {}
    for file in files:
        method, seed = method_and_seed(file)
        rows = read(file)
        item = summarize(rows, method)
        item["seed"] = seed
        grouped.setdefault(method, []).append(item)

    output = []
    for method, seed_rows in sorted(grouped.items()):
        seed_rows.sort(key=lambda item: item["seed"] if item["seed"] is not None else -1)
        pass_mean, pass_std = mean_std([item["pass_rate"] for item in seed_rows])
        score_mean, score_std = mean_std([item["mean_score"] for item in seed_rows])
        calls_mean, calls_std = mean_std([item["mean_tool_calls"] for item in seed_rows])
        output.append({
            "method": method,
            "seeds": len(seed_rows),
            "tasks_per_seed": sorted({item["tasks"] for item in seed_rows}),
            "pass_rate_mean": pass_mean,
            "pass_rate_std": pass_std,
            "mean_score_mean": score_mean,
            "mean_score_std": score_std,
            "mean_tool_calls_mean": calls_mean,
            "mean_tool_calls_std": calls_std,
            "seed_summaries": seed_rows,
        })
    return output


def main():
    parser = argparse.ArgumentParser(description="Aggregate per-seed JSONL experiment results.")
    parser.add_argument("files", nargs="+", help="Per-seed result JSONL files")
    parser.add_argument("--out", default="reports/seed_summary.json")
    args = parser.parse_args()
    summaries = summarize_seeds(args.files)
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

