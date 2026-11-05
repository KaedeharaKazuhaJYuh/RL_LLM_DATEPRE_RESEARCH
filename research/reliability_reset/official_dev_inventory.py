"""Inventory official AppWorld train/dev outputs without reading protected test tasks.

The published reports establish the original native result, not an independent
judgment about side effects. All cases start with safety marked unknown.
"""

from __future__ import annotations

import argparse
from collections import Counter
from io import BytesIO
import json
from pathlib import Path
import re
from zipfile import ZipFile


EXPERIMENT = "legacy_react_code_agent/openai/gpt-4o-2024-05-13"
SPLITS = ("train", "dev")
NATIVE_OUTCOMES = ("pass", "fail", "unknown")
SAFETY_OUTCOMES = ("violation", "no_violation", "unknown")


def summarize_judgments(records: list[dict]) -> dict:
    """Count supplied safety judgments, retaining unknowns.

    The interval bounds the fraction of native passes with a violation if every
    unresolved case were eventually classified either way. It is not a
    confidence interval. A reference is required, but its quality and the
    independence of a judgment must be verified outside this function.
    """
    cells = {native: dict.fromkeys(SAFETY_OUTCOMES, 0) for native in NATIVE_OUTCOMES}
    seen = set()
    for record in records:
        case_id = record["case_id"]
        native = record["native"]
        safety = record["safety"]
        if case_id in seen or native not in NATIVE_OUTCOMES or safety not in SAFETY_OUTCOMES:
            raise ValueError("Duplicate case or invalid outcome")
        if safety != "unknown" and not record.get("judgment_reference"):
            raise ValueError("A safety judgment requires its supporting reference")
        seen.add(case_id)
        cells[native][safety] += 1

    native_passes = sum(cells["pass"].values())
    if native_passes:
        lower = cells["pass"]["violation"] / native_passes
        upper = (cells["pass"]["violation"] + cells["pass"]["unknown"]) / native_passes
        bounds = {"lower": lower, "upper": upper}
    else:
        bounds = None
    return {"cases": len(records), "cells": cells, "native_pass_violation_bounds": bounds}


def summarize_official_split(archive: ZipFile, split: str, expected_ids: set[str] | None = None) -> dict:
    """Read one designated split's archived reports and request-log coverage."""
    if split not in SPLITS:
        raise ValueError("Only the official train and dev splits may be inspected")
    prefix = f"{EXPERIMENT}/{split}/"
    members = {name for name in archive.namelist() if name.startswith(prefix)}
    metadata = json.loads(archive.read(prefix + "metadata.json"))
    if metadata["dataset"] != split:
        raise ValueError("Experiment metadata does not match the selected split")
    task_prefix = prefix + "tasks/"
    ids = sorted({name[len(task_prefix):].split("/", 1)[0] for name in members if name.startswith(task_prefix) and name != task_prefix})
    records = []
    counts = Counter()
    scenario_results: dict[str, list[str]] = {}
    versions = {key: Counter() for key in ("code", "data", "evaluation")}
    for task_id in ids:
        root = task_prefix + task_id + "/"
        report = root + "evaluation/report.md"
        outcome = "unknown"
        if report in members:
            text = archive.read(report).decode("utf-8")
            passed = re.search(r"^Num Passed Tests\s*:\s*(\d+)\s*$", text, re.MULTILINE)
            failed = re.search(r"^Num Failed Tests\s*:\s*(\d+)\s*$", text, re.MULTILINE)
            total = re.search(r"^Num Total\s+Tests\s*:\s*(\d+)\s*$", text, re.MULTILINE)
            if passed and failed and total:
                p, f, t = int(passed.group(1)), int(failed.group(1)), int(total.group(1))
                if t > 0 and p + f == t:
                    outcome = "pass" if p == t else "fail"
        records.append({"case_id": task_id, "native": outcome, "safety": "unknown"})
        scenario_results.setdefault(task_id.split("_")[0], []).append(outcome)
        request_log = root + "logs/api_calls.jsonl"
        if request_log in members:
            counts["request_logs"] += 1
            counts["tracked_requests"] += sum(bool(line.strip()) for line in archive.read(request_log).splitlines())
        for name, suffix in (("environment_logs", "logs/environment_io.md"), ("logger_jsonl_files", "logs/logger.jsonl")):
            counts[name] += int(root + suffix in members)
        for name, suffix in (("code", "version/code.txt"), ("data", "version/data.txt"), ("evaluation", "evaluation/version.txt")):
            path = root + suffix
            versions[name][archive.read(path).decode("utf-8").strip() if path in members else "unknown"] += 1

    scenarios = Counter()
    for outcomes in scenario_results.values():
        result = "fail" if "fail" in outcomes else "unknown" if "unknown" in outcomes else "pass"
        scenarios[result] += 1
    coverage = None
    if expected_ids is not None:
        coverage = {
            "dataset_tasks": len(expected_ids),
            "missing_from_outputs": len(expected_ids - set(ids)),
            "unexpected_in_outputs": len(set(ids) - expected_ids),
        }
    complete_split = expected_ids is not None and expected_ids == set(ids)
    return {
        "split": split,
        "model": metadata["llm"]["name"],
        "agent": metadata["method"]["name"],
        "source_date": metadata.get("date"),
        "judgments": summarize_judgments(records),
        "scenario_outcomes": {key: scenarios[key] for key in NATIVE_OUTCOMES} if complete_split else None,
        "dataset_coverage": coverage,
        "log_coverage": {key: counts[key] for key in ("request_logs", "tracked_requests", "environment_logs", "logger_jsonl_files")},
        "versions": {key: dict(value) for key, value in versions.items()},
        "provider_cost": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Official encrypted experiment-outputs bundle")
    parser.add_argument("--data-bundle", type=Path, help="Optional matching official 0.1.0 data bundle")
    parser.add_argument("--split", choices=SPLITS + ("both",), default="both")
    args = parser.parse_args()
    from appworld.common.constants import PASSWORD, SALT
    from appworld.common.crypto import decrypt_bytes

    with ZipFile(BytesIO(decrypt_bytes(args.bundle.read_bytes(), PASSWORD, SALT))) as archive:
        splits = SPLITS if args.split == "both" else (args.split,)
        if args.data_bundle:
            with ZipFile(BytesIO(decrypt_bytes(args.data_bundle.read_bytes(), PASSWORD, SALT))) as data_archive:
                if data_archive.read("data/version.txt").decode("utf-8").strip() != "0.1.0":
                    raise ValueError("Historical model outputs require AppWorld data 0.1.0")
                task_ids = {
                    split: set(data_archive.read(f"data/datasets/{split}.txt").decode("utf-8").split())
                    for split in splits
                }
        else:
            task_ids = {}
        print(json.dumps([summarize_official_split(archive, split, task_ids.get(split)) for split in splits], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
