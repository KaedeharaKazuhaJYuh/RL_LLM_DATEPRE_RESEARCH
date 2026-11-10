"""Census DAComp-DA rubric score ceilings from a pinned public Git tree.

This reports source-level values only. It does not select an authoritative
denominator or infer a score correction.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any


REVISION = "027ccaf20f0d3743d9291fd575d9bc785a5fe3db"
SOURCE_ROOT = (
    "https://raw.githubusercontent.com/ByteDance-Seed/DAComp/"
    f"{REVISION}/dacomp-da/evaluation_suite/src/dacomp-"
)
FIELDS = (
    "task_id",
    "revision",
    "rubric_sha256",
    "metadata_sha256",
    "metadata_total",
    "rubric_title_total",
    "requirement_max_sum",
    "standard_max_sum",
    "path_weight_sum_min",
    "path_weight_sum_max",
    "standards_with_unequal_path_weights",
    "path_weight_parse_complete",
    "path_weights_exceed_standard_cap",
)


def _download(task_number: int, filename: str) -> bytes:
    url = f"{SOURCE_ROOT}{task_number:03d}/{filename}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "FaultDA-DAComp-rubric-census/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def _points(line: str) -> float | None:
    patterns = (
        r"(?:maximum(?:\s+score\s+for\s+this\s+(?:requirement|standard))?"
        r"|max(?:imum)?|up\s+to|worth\s+up\s+to)\s*[:(]?\s*"
        r"(\d+(?:\.\d+)?)\s*points?\b",
        r"\[\s*(\d+(?:\.\d+)?)\s*points?\b",
        r"\((\d+(?:\.\d+)?)\s*points?\s*(?:,|\))",
    )
    for pattern in patterns:
        match = re.search(pattern, line, re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _parse_task(task_number: int, rubric_bytes: bytes, metadata_bytes: bytes) -> dict[str, Any]:
    rubric = rubric_bytes.decode("utf-8")
    metadata = json.loads(metadata_bytes)
    lines = rubric.splitlines()

    title_total = None
    for line in lines:
        match = re.search(
            r"total\s+score\s*\|\s*(\d+(?:\.\d+)?)\s*points?",
            line,
            re.IGNORECASE,
        )
        if match:
            title_total = float(match.group(1))
            break

    requirements: list[float] = []
    standards: list[dict[str, Any]] = []
    current_standard: dict[str, Any] | None = None
    current_path: dict[str, Any] | None = None

    requirement_heading = re.compile(r"^\s*#{2,5}\s*Requirement\b", re.IGNORECASE)
    standard_heading = re.compile(
        r"^\s*#{2,5}\s*(?:Standard|Criterion)\b", re.IGNORECASE
    )
    path_heading = re.compile(r"^\s*#{2,6}\s*Path\b", re.IGNORECASE)
    leaf_heading = re.compile(
        r"^\s*(?:[-*]\s*)?(?:Sub-criterion|Substandard|Sub-standard|"
        r"Rubric item|Item)\b",
        re.IGNORECASE,
    )

    for line in lines:
        if requirement_heading.match(line):
            if current_path is not None and current_standard is not None:
                current_standard["paths"].append(current_path)
                current_path = None
            if current_standard is not None:
                standards.append(current_standard)
                current_standard = None
            value = _points(line)
            if value is not None:
                requirements.append(value)
        elif standard_heading.match(line):
            if current_path is not None and current_standard is not None:
                current_standard["paths"].append(current_path)
                current_path = None
            if current_standard is not None:
                standards.append(current_standard)
            current_standard = {
                "maximum": _points(line),
                "paths": [],
            }
        elif path_heading.match(line) and current_standard is not None:
            if current_path is not None:
                current_standard["paths"].append(current_path)
            current_path = {"maximum": _points(line), "leaves": []}
        elif current_path is not None and leaf_heading.match(line):
            value = _points(line)
            if value is not None:
                current_path["leaves"].append(value)

    if current_path is not None and current_standard is not None:
        current_standard["paths"].append(current_path)
    if current_standard is not None:
        standards.append(current_standard)

    path_minima: list[float] = []
    path_maxima: list[float] = []
    unequal_path_standards = 0
    path_weights_exceed_cap = 0
    unresolved_standards = 0
    standard_maxima = [s["maximum"] for s in standards if s["maximum"] is not None]

    for standard in standards:
        paths = standard["paths"]
        values: list[float | None] = []
        for path in paths:
            value = path["maximum"]
            if value is None and path["leaves"]:
                value = sum(path["leaves"])
            if value is None and len(paths) == 1 and standard["maximum"] is not None:
                value = standard["maximum"]
            values.append(value)
        if not paths and standard["maximum"] is not None:
            values = [standard["maximum"]]

        if not values or any(value is None for value in values):
            unresolved_standards += 1
            continue

        concrete_values = [float(value) for value in values if value is not None]
        path_minima.append(min(concrete_values))
        path_maxima.append(max(concrete_values))
        unequal_path_standards += len(set(concrete_values)) > 1
        if (
            standard["maximum"] is not None
            and max(concrete_values) > standard["maximum"]
        ):
            path_weights_exceed_cap += 1

    all_standard_maxima_known = bool(standards) and len(standard_maxima) == len(standards)
    path_parse_complete = bool(standards) and unresolved_standards == 0
    return {
        "task_id": f"dacomp-{task_number:03d}",
        "revision": REVISION,
        "rubric_sha256": hashlib.sha256(rubric_bytes).hexdigest(),
        "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "metadata_total": metadata.get("Total"),
        "rubric_title_total": title_total,
        "requirement_max_sum": sum(requirements) if requirements else None,
        "standard_max_sum": sum(standard_maxima) if all_standard_maxima_known else None,
        "path_weight_sum_min": sum(path_minima) if path_parse_complete else None,
        "path_weight_sum_max": sum(path_maxima) if path_parse_complete else None,
        "standards_with_unequal_path_weights": unequal_path_standards,
        "path_weight_parse_complete": path_parse_complete,
        "path_weights_exceed_standard_cap": path_weights_exceed_cap,
    }


def run(output: Path) -> list[dict[str, Any]]:
    def fetch_and_parse(task_number: int) -> dict[str, Any]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            rubric = pool.submit(_download, task_number, "rubric.txt")
            metadata = pool.submit(_download, task_number, "metadata.json")
            return _parse_task(task_number, rubric.result(), metadata.result())

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(fetch_and_parse, range(1, 101)))

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(results)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("DACOMP_PATH_WEIGHT_CENSUS_2026_11_07.csv"),
    )
    args = parser.parse_args()
    results = run(args.output)
    complete = [row for row in results if row["path_weight_parse_complete"]]
    outside = [
        row
        for row in complete
        if row["metadata_total"] < row["path_weight_sum_min"]
        or row["metadata_total"] > row["path_weight_sum_max"]
    ]
    variable = [
        row for row in complete if row["standards_with_unequal_path_weights"] > 0
    ]
    print(f"fetched={len(results)} path_parse_complete={len(complete)}")
    print(
        "unequal_alternative_path_tasks="
        f"{len(variable)} metadata_outside_parsed_path_range={len(outside)}"
    )
    print(f"csv={args.output.resolve()}")


if __name__ == "__main__":
    main()
