"""Reproduce the bounded WorkBench Revisited outcome-composition audit."""

from __future__ import annotations

import argparse
import ast
import csv
import gzip
import hashlib
import json
import math
import random
from collections import Counter
from pathlib import Path


EXPECTED_SHA256 = "6035FB112BBB4FB48CD56D643898CAC43C42C2D11BC6D2BB0E595D8D31EA2216"


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in order[start:end]:
            result[index] = rank
        start = end
    return result


def spearman(left: list[float], right: list[float]) -> float:
    left_rank, right_rank = ranks(left), ranks(right)
    left_mean = sum(left_rank) / len(left_rank)
    right_mean = sum(right_rank) / len(right_rank)
    covariance = sum((x - left_mean) * (y - right_mean) for x, y in zip(left_rank, right_rank))
    left_ss = sum((x - left_mean) ** 2 for x in left_rank)
    right_ss = sum((y - right_mean) ** 2 for y in right_rank)
    return covariance / math.sqrt(left_ss * right_ss)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("item_level_csv_gz", type=Path)
    parser.add_argument("--bootstraps", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=20261106)
    args = parser.parse_args()

    digest = hashlib.sha256(args.item_level_csv_gz.read_bytes()).hexdigest().upper()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"unexpected item-level artifact SHA-256: {digest}")

    selected: list[dict[str, str]] = []
    with gzip.open(args.item_level_csv_gz, "rt", newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["run_group"] == "revisited_2026":
                selected.append(row)

    models = sorted({row["model"] for row in selected})
    templates = sorted({row["base_template"] for row in selected})
    model_index = {model: index for index, model in enumerate(models)}
    template_index = {template: index for index, template in enumerate(templates)}
    # Per template/model sums: n, correct, side effects, valid n/correct/side effects.
    cells = [[[0, 0, 0, 0, 0, 0] for _ in models] for _ in templates]
    compensation_cells = [[0 for _ in models] for _ in templates]
    no_write_compensations: list[dict[str, str]] = []
    error_and_side_effect_count = 0

    for row in selected:
        model = model_index[row["model"]]
        template = template_index[row["base_template"]]
        cell = cells[template][model]
        cell[0] += 1
        cell[1] += row["correct"] == "True"
        cell[2] += row["unwanted_side_effects"] == "True"
        if not row["error"]:
            cell[3] += 1
            cell[4] += row["correct"] == "True"
            cell[5] += row["unwanted_side_effects"] == "True"
        if row["error"] and row["unwanted_side_effects"] == "True":
            error_and_side_effect_count += 1

        if (
            row["correct"] != "True"
            or row["unwanted_side_effects"] != "False"
            or row["exact_match"] != "False"
            or ast.literal_eval(row["ground_truth_actions"])
        ):
            continue
        actions = ast.literal_eval(row["predicted_actions"])
        compensated = any(
            (
                action.startswith("calendar.create_event.func(")
                and any('calendar.delete_event.func(event_id="00000300"' in later for later in actions[index + 1 :])
            )
            or (
                action.startswith("project_management.create_task.func(")
                and any('project_management.delete_task.func(task_id="00000300"' in later for later in actions[index + 1 :])
            )
            for index, action in enumerate(actions)
        )
        if compensated:
            no_write_compensations.append(row)
            compensation_cells[template][model] += 1

    totals = [[sum(cells[t][m][field] for t in range(len(templates))) for field in range(6)] for m in range(len(models))]
    compensation_totals = [sum(compensation_cells[t][m] for t in range(len(templates))) for m in range(len(models))]
    completion = [cell[1] / cell[0] for cell in totals]
    side_effect = [cell[2] / cell[0] for cell in totals]
    conditional = [cell[2] / (cell[0] - cell[1]) for cell in totals]
    valid_conditional = [cell[5] / (cell[3] - cell[4]) for cell in totals]
    rho_completion_side_effect = spearman(completion, side_effect)
    rho_completion_conditional = spearman(completion, conditional)

    randomizer = random.Random(args.seed)
    delta_samples: list[float] = []
    completion_side_effect_samples: list[float] = []
    completion_conditional_samples: list[float] = []
    pair_baseline_samples: list[float] = []
    pair_adjusted_samples: list[float] = []
    pair_left, pair_right = model_index["gemini-3.1-pro"], model_index["gemini-3.5-flash"]
    for _ in range(args.bootstraps):
        sampled = [randomizer.randrange(len(templates)) for _ in templates]
        sampled_totals = [[0, 0, 0] for _ in models]
        pair_totals = [[0, 0, 0] for _ in range(2)]
        for template in sampled:
            for model in range(len(models)):
                for field in range(3):
                    sampled_totals[model][field] += cells[template][model][field]
            for side, model in enumerate((pair_left, pair_right)):
                pair_totals[side][0] += cells[template][model][0]
                pair_totals[side][1] += cells[template][model][2]
                pair_totals[side][2] += compensation_cells[template][model]
        sampled_completion = [cell[1] / cell[0] for cell in sampled_totals]
        sampled_side_effect = [cell[2] / cell[0] for cell in sampled_totals]
        if any(cell[0] == cell[1] for cell in sampled_totals):
            continue
        sampled_conditional = [cell[2] / (cell[0] - cell[1]) for cell in sampled_totals]
        rho_h = spearman(sampled_completion, sampled_side_effect)
        rho_q = spearman(sampled_completion, sampled_conditional)
        completion_side_effect_samples.append(rho_h)
        completion_conditional_samples.append(rho_q)
        delta_samples.append(rho_q - rho_h)
        pair_baseline_samples.append(pair_totals[0][1] / pair_totals[0][0] - pair_totals[1][1] / pair_totals[1][0])
        pair_adjusted_samples.append(
            (pair_totals[0][1] + pair_totals[0][2]) / pair_totals[0][0]
            - (pair_totals[1][1] + pair_totals[1][2]) / pair_totals[1][0]
        )

    def interval(samples: list[float]) -> list[float]:
        return [percentile(samples, 0.025), percentile(samples, 0.975)]

    print(json.dumps({
        "artifact_sha256": digest,
        "rows": len(selected),
        "task_ids": len({row["task_id"] for row in selected}),
        "models": len(models),
        "base_templates": len(templates),
        "correct_count": sum(cell[1] for cell in totals),
        "unwanted_side_effect_count": sum(cell[2] for cell in totals),
        "error_and_side_effect_count": error_and_side_effect_count,
        "rho_completion_vs_unconditional_side_effect": rho_completion_side_effect,
        "rho_completion_vs_failure_conditional_side_effect": rho_completion_conditional,
        "rho_completion_vs_valid_record_conditional_side_effect": spearman(completion, valid_conditional),
        "rho_difference_conditional_minus_unconditional": rho_completion_conditional - rho_completion_side_effect,
        "paired_template_bootstrap": {
            "resamples": args.bootstraps,
            "finite_resamples": len(delta_samples),
            "seed": args.seed,
            "rho_completion_unconditional_ci95": interval(completion_side_effect_samples),
            "rho_completion_conditional_ci95": interval(completion_conditional_samples),
            "rho_difference_ci95": interval(delta_samples),
        },
        "correct_no_write_gold_compensating_write_rows": len(no_write_compensations),
        "compensation_task_ids": sorted({row["task_id"] for row in no_write_compensations}),
        "compensation_models": sorted({row["model"] for row in no_write_compensations}),
        "compensation_rows_by_model": dict(sorted(Counter(row["model"] for row in no_write_compensations).items())),
        "posthoc_closest_harm_rate_pair": {
            "left_model": models[pair_left],
            "right_model": models[pair_right],
            "left_minus_right_percentage_points_before": 100 * (totals[pair_left][2] / totals[pair_left][0] - totals[pair_right][2] / totals[pair_right][0]),
            "left_minus_right_percentage_points_after": 100 * ((totals[pair_left][2] + compensation_totals[pair_left]) / totals[pair_left][0] - (totals[pair_right][2] + compensation_totals[pair_right]) / totals[pair_right][0]),
            "bootstrap_ci95_percentage_points_before": [100 * x for x in interval(pair_baseline_samples)],
            "bootstrap_ci95_percentage_points_after": [100 * x for x in interval(pair_adjusted_samples)],
        },
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
