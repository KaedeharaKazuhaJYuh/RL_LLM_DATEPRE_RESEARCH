"""Summarize the public NIKA P4 trace subset without extracting the archive."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import zipfile


parser = argparse.ArgumentParser()
parser.add_argument("archive", type=pathlib.Path)
parser.add_argument("--output", type=pathlib.Path)
args = parser.parse_args()

archive_hash = hashlib.sha256()
archive_md5 = hashlib.md5()
with args.archive.open("rb") as archive_file:
    for block in iter(lambda: archive_file.read(1024 * 1024), b""):
        archive_hash.update(block)
        archive_md5.update(block)

with zipfile.ZipFile(args.archive) as archive:
    names = set(archive.namelist())
    ground_truth_paths = sorted(
        name for name in names if name.endswith("/ground_truth.json")
    )
    p4_rows = []
    tool_calls = collections.Counter()
    model_summary = collections.defaultdict(collections.Counter)
    non_json_log_lines = 0
    missing_logs = 0
    missing_metadata = []

    for ground_truth_path in ground_truth_paths:
        directory = ground_truth_path.rsplit("/", 1)[0]
        metadata_path = f"{directory}/session_meta.json"
        if metadata_path not in names:
            missing_metadata.append(ground_truth_path)
            continue
        metadata = json.loads(archive.read(metadata_path))
        scenario = metadata["scenario_name"]
        if not scenario.lower().startswith("p4_"):
            continue
        issue = metadata["problem_names"][0]
        model = metadata["backend_model"]
        log_path = f"{directory}/conversation_diagnosis_agent.log"
        trace_counter_calls = 0
        if log_path in names:
            for line in archive.read(log_path).decode("utf-8", "replace").splitlines():
                if not line.strip():
                    continue
                if not line.lstrip().startswith("{"):
                    non_json_log_lines += 1
                    continue
                event = json.loads(line)
                if event.get("event") == "tool_start":
                    tool_name = event.get("tool", {}).get("name", "<missing>")
                    tool_calls[tool_name] += 1
                    if "counter" in tool_name.lower():
                        trace_counter_calls += 1
        else:
            missing_logs += 1
        submission_path = f"{directory}/submission.json"
        if submission_path in names:
            submission = json.loads(archive.read(submission_path))
            truth = json.loads(archive.read(ground_truth_path))
            exact_fields = {}
            for field in ("is_anomaly", "faulty_devices", "root_cause_name"):
                predicted = submission.get(field)
                expected = truth.get(field)
                if isinstance(predicted, list) and isinstance(expected, list):
                    predicted = sorted(predicted)
                    expected = sorted(expected)
                exact_fields[field] = predicted == expected
                model_summary[model][f"{field}_exact"] += int(exact_fields[field])
            model_summary[model]["submission_count"] += 1
        else:
            exact_fields = None
            model_summary[model]["missing_submission_count"] += 1
        model_summary[model]["trace_count"] += 1
        model_summary[model]["counter_trace_count"] += int(trace_counter_calls > 0)
        model_summary[model]["counter_tool_call_count"] += trace_counter_calls
        p4_rows.append(
            {
                "issue": issue,
                "model": model,
                "scenario": scenario,
                "session_id": metadata["session_id"],
                "counter_tool_calls": trace_counter_calls,
                "has_submission": exact_fields is not None,
                "literal_field_exact_matches": exact_fields,
            }
        )

issue_model_counts = collections.defaultdict(collections.Counter)
for row in p4_rows:
    issue_model_counts[row["issue"]][row["model"]] += 1

result = {
    "source": {
        "record": "https://zenodo.org/records/17971675",
        "archive_name": "NIKA Traces.zip",
        "archive_sha256": archive_hash.hexdigest(),
        "archive_md5": archive_md5.hexdigest(),
        "zenodo_md5_expected": "cc940a7fadd29677d5ef942847a5c45c",
        "archive_md5_matches_zenodo": archive_md5.hexdigest()
        == "cc940a7fadd29677d5ef942847a5c45c",
        "license": None,
        "license_status": (
            "unverified: Zenodo record API returned a null license field on "
            "2026-11-08; the archive contains no license/readme file; the "
            "GitHub software license is not assumed to cover trace data"
        ),
    },
    "archive_trace_count": len(ground_truth_paths),
    "archive_session_metadata_count": len(ground_truth_paths) - len(missing_metadata),
    "archive_missing_session_metadata": missing_metadata,
    "p4_trace_count": len(p4_rows),
    "p4_explicit_issue_name_trace_count": sum(
        1 for row in p4_rows if row["issue"].lower().startswith("p4_")
    ),
    "p4_scenarios": sorted({row["scenario"] for row in p4_rows}),
    "p4_models": sorted({row["model"] for row in p4_rows}),
    "p4_issue_clusters": {
        issue: dict(sorted(counts.items()))
        for issue, counts in sorted(issue_model_counts.items())
    },
    "p4_issue_cluster_count": len(issue_model_counts),
    "p4_tool_start_counts": dict(sorted(tool_calls.items())),
    "p4_agent_observation_summary": {
        "traces_with_counter_tool_calls": sum(
            summary["counter_trace_count"] for summary in model_summary.values()
        ),
        "counter_tool_call_count": sum(
            summary["counter_tool_call_count"] for summary in model_summary.values()
        ),
        "missing_submission_count": sum(
            summary["missing_submission_count"] for summary in model_summary.values()
        ),
        "by_model": {
            model: dict(sorted(summary.items()))
            for model, summary in sorted(model_summary.items())
        },
        "field_match_semantics": "literal field equality after sorting list values; descriptive only, not an official scorer replay",
        "trace_rows": p4_rows,
    },
    "p4_int_or_telemetry_tool_calls": sum(
        count
        for name, count in tool_calls.items()
        if name.lower().startswith("int_") or "telemetry" in name.lower()
    ),
    "p4_non_json_diagnostic_lines": non_json_log_lines,
    "p4_logs_missing": missing_logs,
    "interpretation_limits": [
        "Trace rows are clustered within P4 issue types and two P4 scenarios; they are not independent task families.",
        "The P4 scenarios do not contain the proposed terminal packet-loss versus sink-report-loss paired intervention.",
        "This census counts logged tool starts only; it does not rerun NIKA scoring or estimate causal Agent effects.",
    ],
}

serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
if args.output:
    args.output.write_text(serialized, encoding="utf-8", newline="\n")
else:
    print(serialized, end="")
