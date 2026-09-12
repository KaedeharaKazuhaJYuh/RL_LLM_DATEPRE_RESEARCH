"""Read-only, deterministic dataset features for a data-aware policy state."""

import csv
import math
from pathlib import Path


DIFFICULTY = {"easy": 0.0, "medium": 0.5, "hard": 1.0}
TARGET_COLUMNS = {"score", "churned"}


def _is_numeric(values):
    try:
        [float(value) for value in values if value not in (None, "")]
    except (TypeError, ValueError):
        return False
    return bool([value for value in values if value not in (None, "")])


def extract_dataset_features(uri, difficulty="medium"):
    """Return a stable 10-dimensional state vector from a CSV without mutation.

    The final two values encode aggregate numeric content. They deliberately make a
    value-perturbed dataset observable to the policy while avoiding row-level data.
    """
    with Path(uri).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    columns = list(rows[0]) if rows else []
    values_by_column = {column: [row.get(column, "") for row in rows] for column in columns}
    numeric_columns = [column for column, values in values_by_column.items() if _is_numeric(values)]
    missing = sum(value in (None, "") for values in values_by_column.values() for value in values)
    cells = max(len(rows) * max(len(columns), 1), 1)
    numeric_values = [float(value) for column in numeric_columns for value in values_by_column[column] if value not in (None, "")]
    mean_abs = sum(abs(value) for value in numeric_values) / max(len(numeric_values), 1)
    spread = (max(numeric_values) - min(numeric_values)) if numeric_values else 0.0
    categorical_count = len(columns) - len(numeric_columns)
    return [
        DIFFICULTY[difficulty],
        min(len(rows) / 100.0, 1.0),
        missing / cells,
        float(len(numeric_columns)),
        float(categorical_count),
        float("month" in columns),
        float(bool(TARGET_COLUMNS.intersection(columns))),
        min(math.log1p(mean_abs) / 10.0, 1.0),
        min(math.log1p(spread) / 10.0, 1.0),
        0.0,
    ]

