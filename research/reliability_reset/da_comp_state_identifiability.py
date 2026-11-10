"""Audit how many state-cluster contrasts survive app-by-task-type controls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np


ROOT = Path(__file__).parent
CROSSWALK = ROOT / "DAComp_APP_STATE_CROSSWALK_2026_11_06.csv"
OUTPUT = ROOT / "DAComp_STATE_IDENTIFIABILITY_2026_11_06.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crosswalk", type=Path, default=CROSSWALK)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    with args.crosswalk.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    state_counts = Counter(row["state_cluster"] for row in rows)
    repeated_states = sorted(state for state, count in state_counts.items() if count > 1)
    all_states = sorted(state_counts)
    cells = sorted({f"{row['application_family']}|{row['task_type']}" for row in rows})
    base = np.array(
        [[int(f"{row['application_family']}|{row['task_type']}" == cell) for cell in cells] for row in rows],
        dtype=float,
    )
    state_terms = np.array(
        [[int(row["state_cluster"] == state) for state in repeated_states] for row in rows],
        dtype=float,
    )
    all_state_terms = np.array(
        [[int(row["state_cluster"] == state) for state in all_states] for row in rows],
        dtype=float,
    )
    baseline_rank = int(np.linalg.matrix_rank(base))
    augmented_rank = int(np.linalg.matrix_rank(np.column_stack((base, state_terms))))
    all_states_rank = int(np.linalg.matrix_rank(np.column_stack((base, all_state_terms))))

    family_gains = {}
    for family in sorted({row["application_family"] for row in rows}):
        subset = [row for row in rows if row["application_family"] == family]
        family_cells = sorted({row["task_type"] for row in subset})
        family_states = sorted(
            state
            for state, count in Counter(row["state_cluster"] for row in subset).items()
            if count > 1
        )
        family_base = np.array(
            [[int(row["task_type"] == cell) for cell in family_cells] for row in subset],
            dtype=float,
        )
        family_terms = np.array(
            [[int(row["state_cluster"] == state) for state in family_states] for row in subset],
            dtype=float,
        )
        gain = int(
            np.linalg.matrix_rank(np.column_stack((family_base, family_terms)))
            - np.linalg.matrix_rank(family_base)
        )
        if gain:
            family_gains[family] = gain

    record = {
        "tasks": len(rows),
        "crosswalk_sha256": hashlib.sha256(args.crosswalk.read_bytes()).hexdigest(),
        "application_by_task_type_cells": len(cells),
        "all_state_clusters": len(all_states),
        "repeated_state_clusters": len(repeated_states),
        "baseline_design_rank": baseline_rank,
        "rank_after_repeated_state_indicators": augmented_rank,
        "incremental_state_degrees_of_freedom": augmented_rank - baseline_rank,
        "rank_after_all_state_indicators": all_states_rank,
        "incremental_all_state_degrees_of_freedom": all_states_rank - baseline_rank,
        "families_with_incremental_state_degrees_of_freedom": family_gains,
        "numpy_version": np.__version__,
        "interpretation": (
            "Fixed state indicators add only the reported rank beyond application-by-task-type cells; "
            "this is a design identifiability result, not an outcome or variance estimate."
        ),
    }
    args.output.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
