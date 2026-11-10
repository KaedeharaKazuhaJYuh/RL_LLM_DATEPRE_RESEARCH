"""Offline replay census for AppWorld 0.1.0 historical train/dev outputs.

This script evaluates saved databases with the released scorer. It never runs an
agent or calls a model API. AppWorld data and outputs must be supplied locally;
they are not included in this repository. The destination must be a new private
directory because the extracted task data and scorer outputs are restricted.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile

from appworld.common.constants import PASSWORD, SALT
from appworld.common.utils import decrypt_bytes


DATA_SHA256 = "fd9f9608c2ec71ed0ac25c3633a738b9129a318a129e31230425b9188e508250"
OUTPUTS_SHA256 = "e5ec6367d32b1883d28aaa25e4fe5026c89a08d5fb7a5742a83bfb65fe6bb2da"
OUTPUT_PREFIX = "legacy_react_code_agent/openai/gpt-4o-2024-05-13"
EXPERIMENT_NAME = "faultda-census147-20261106"


if len(sys.argv) == 3 and sys.argv[1] == "--worker":
    from appworld.evaluator import evaluate_task

    tracker = evaluate_task(sys.argv[2], experiment_name=EXPERIMENT_NAME, save_report=False)
    print("REPLAY_RESULT=" + json.dumps({
        "passed": tracker.pass_count,
        "failed": tracker.fail_count,
        "passed_requirements": [entry["requirement"] for entry in tracker.passes],
        "failed_requirements": [entry["requirement"] for entry in tracker.failures],
        "assertion_failures": sum("AssertionError" in entry["trace"] for entry in tracker.failures),
    }))
    raise SystemExit(0)

if len(sys.argv) not in (4, 5):
    raise SystemExit("Usage: replay_census.py DATA.bundle OUTPUTS.bundle NEW_PRIVATE_DIR [--limit N]")
if importlib.metadata.version("appworld") != "0.1.0":
    raise SystemExit("This census requires AppWorld 0.1.0")

data_path, outputs_path, destination = map(Path, sys.argv[1:4])
limit = None
if len(sys.argv) == 5:
    if not sys.argv[4].startswith("--limit="):
        raise SystemExit("The optional argument must be --limit=N")
    limit = int(sys.argv[4].split("=", 1)[1])
    if limit < 1:
        raise SystemExit("N must be positive")

data_bytes, outputs_bytes = data_path.read_bytes(), outputs_path.read_bytes()
data_sha256 = hashlib.sha256(data_bytes).hexdigest()
outputs_sha256 = hashlib.sha256(outputs_bytes).hexdigest()
if data_sha256 != DATA_SHA256 or outputs_sha256 != OUTPUTS_SHA256:
    raise SystemExit("Input archive hashes do not match the frozen official 0.1.0 inputs")

destination = destination.resolve()
destination.mkdir(parents=True, exist_ok=False)
raw_data = decrypt_bytes(data_bytes, PASSWORD, SALT)
raw_outputs = decrypt_bytes(outputs_bytes, PASSWORD, SALT)
with zipfile.ZipFile(io.BytesIO(raw_data)) as data_archive, zipfile.ZipFile(io.BytesIO(raw_outputs)) as outputs_archive:
    output_names = outputs_archive.namelist()
    selected: dict[str, list[str]] = {}
    saved: dict[tuple[str, str], dict] = {}
    normalize = lambda text: " ".join(text.split())

    for split in ("train", "dev"):
        prefix = f"{OUTPUT_PREFIX}/{split}/tasks/"
        task_ids = sorted({name[len(prefix):].split("/", 1)[0] for name in output_names if name.startswith(prefix) and "/" in name[len(prefix):]})
        if limit is not None:
            task_ids = task_ids[:limit]
        selected[split] = task_ids
        for task_id in task_ids:
            base = prefix + task_id + "/"
            report_path = base + "evaluation/report.md"
            report = outputs_archive.read(report_path).decode("utf-8")
            stats = {key: int(value) for key, value in re.findall(r"Num (Passed|Failed|Total)\s+Tests\s*:\s*(\d+)", report)}
            if not all(key in stats for key in ("Passed", "Failed", "Total")):
                raise ValueError(f"Saved score report is malformed in {split}")
            passed = sorted(normalize(item) for item in re.findall(r">> Passed Requirement\s*\n(.*?)(?=\n>>|\n[^\n]*Fails)", report, re.S))
            failed = sorted(normalize(item) for item in re.findall(r">> Failed Requirement\s*\n(.*?)\n```", report, re.S))
            saved[(split, task_id)] = {"passed": passed, "failed": failed, "stats": stats}

    if len(selected["train"]) != (limit or 90) or len(selected["dev"]) != (limit or 57):
        raise ValueError("The frozen train/dev output archive does not contain the expected task counts")

    for name in data_archive.namelist():
        shared = name.startswith(("data/base_dbs/", "data/api_docs/")) or name in ("data/version.txt", "data/LICENSE")
        selected_task = any(name.startswith("data/tasks/" + task_id + "/") for ids in selected.values() for task_id in ids)
        if name.endswith("/") or not (shared or selected_task):
            continue
        target = destination.joinpath(*name.split("/"))
        if not target.resolve().is_relative_to(destination):
            raise ValueError("Data archive path escaped the private destination")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data_archive.read(name))

    for split, task_ids in selected.items():
        prefix = f"{OUTPUT_PREFIX}/{split}/tasks/"
        for task_id in task_ids:
            archived = prefix + task_id + "/dbs/"
            target_root = destination / "experiments" / "outputs" / EXPERIMENT_NAME / "tasks" / task_id / "dbs"
            for name in output_names:
                if name.startswith(archived) and not name.endswith("/"):
                    target = target_root / name[len(archived):]
                    if not target.resolve().is_relative_to(target_root.resolve()):
                        raise ValueError("Output archive path escaped the private task directory")
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(outputs_archive.read(name))

environment = os.environ.copy()
environment["APPWORLD_ROOT"] = str(destination)
environment["APPWORLD_CACHE"] = str(destination / "cache")
environment["PYTHONIOENCODING"] = "utf-8"
results = []
failures = []
for split, task_ids in selected.items():
    for index, task_id in enumerate(task_ids, start=1):
        try:
            run = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--worker", task_id],
                capture_output=True, text=True, timeout=120, env=environment,
            )
            if run.returncode:
                failures.append({"split": split, "reason": "scorer_exit", "returncode": run.returncode})
                continue
            output = json.loads(next(line[14:] for line in run.stdout.splitlines() if line.startswith("REPLAY_RESULT=")))
            original = saved[(split, task_id)]
            record = {
                "split": split,
                "saved_pass": original["stats"]["Failed"] == 0,
                "replay_pass": output["failed"] == 0,
                "check_labels_match": output["passed_requirements"] == original["passed"] and output["failed_requirements"] == original["failed"],
                "saved_passed": original["stats"]["Passed"],
                "saved_failed": original["stats"]["Failed"],
                "replay_passed": output["passed"],
                "replay_failed": output["failed"],
                "assertion_failures": output["assertion_failures"],
            }
            results.append(record)
        except Exception as error:
            failures.append({"split": split, "reason": type(error).__name__})
        if index % 10 == 0 or index == len(task_ids):
            print(f"{split}: {index}/{len(task_ids)}; completed={len(results)}; errors={len(failures)}", flush=True)

summary = {"source_sha256": {"data": data_sha256, "outputs": outputs_sha256}, "appworld_version": "0.1.0", "model_lineage": "GPT-4o (2024-05-13), ReAct Code Agent", "limit": limit, "completed": len(results), "errors": len(failures), "results": results, "error_records": failures}
for split in ("train", "dev"):
    rows = [row for row in results if row["split"] == split]
    summary[split] = {
        "completed": len(rows),
        "saved_pass_to_replay_pass": sum(row["saved_pass"] and row["replay_pass"] for row in rows),
        "saved_pass_to_replay_fail": sum(row["saved_pass"] and not row["replay_pass"] for row in rows),
        "saved_fail_to_replay_pass": sum(not row["saved_pass"] and row["replay_pass"] for row in rows),
        "saved_fail_to_replay_fail": sum(not row["saved_pass"] and not row["replay_pass"] for row in rows),
        "check_label_exact_matches": sum(row["check_labels_match"] for row in rows),
    }
(destination / "census-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps({key: summary[key] for key in ("completed", "errors", "train", "dev")}, indent=2))
print("Private census artifacts are stored at:", destination)
