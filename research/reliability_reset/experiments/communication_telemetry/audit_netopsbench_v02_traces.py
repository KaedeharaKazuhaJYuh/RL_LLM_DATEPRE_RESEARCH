"""Recompute a zero-tool anomaly-flag baseline on public NetOpsBench v0.2 traces."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path


ANOMALY_FLAG = re.compile(r'"anomalies_detected"\s*:\s*(true|false)')
CLEAN_CURRENT_CUE = re.compile(
    r"current ping|0% loss|normal latency|resolved|no actionable fault|no active fault",
    re.IGNORECASE,
)
NETOPSBENCH_CODE_COMMIT = "d121e55b51f317b9f6bc684be0745184457740b8"
HF_DATASET_REVISION = "f7ef8e5ecde5eba030c9b4cd9ec4cda7703edc42"
MESSAGE_CAP_CHARS = 200_000


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--extracted-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ping-output", type=Path)
    args = parser.parse_args()

    release_archives = [
        row
        for row in csv.DictReader(args.manifest.open(encoding="utf-8", newline=""))
        if "netopsbench-0.2" in row["archive_path"]
    ]
    records: list[dict[str, object]] = []
    ping_audit_events: list[dict[str, object]] = []
    for archive in release_archives:
        run_dir = args.extracted_root / archive["run_id"]
        results_path = run_dir / "traces" / "results.jsonl"
        archive_records = [
            json.loads(line)
            for line in results_path.open(encoding="utf-8")
            if line.strip()
        ]
        if len(archive_records) != int(archive["result_count"]):
            raise ValueError(f"Unexpected result count in {results_path}")

        for result in archive_records:
            trace_path = run_dir / Path(result["atif_path"])
            trajectory = json.loads(trace_path.read_text(encoding="utf-8"))
            initial = trajectory["steps"][0]
            if initial["extra"].get("is_initial_context") is not True:
                raise ValueError(f"First step is not initial context: {trace_path}")
            if initial["source"] != "user":
                raise ValueError(f"Initial context is not user-visible: {trace_path}")

            message = initial["message"]
            flag_match = ANOMALY_FLAG.search(message)
            if flag_match is None:
                raise ValueError(f"Missing anomaly flag in {trace_path}")
            anomaly_detected = flag_match.group(1) == "true"

            details = result["details"]
            agent_output = details["agent_output"]
            healthy = details["healthy"]
            if not isinstance(healthy, bool):
                raise ValueError(f"Missing binary ground truth in {trace_path}")
            if not isinstance(result["correct_verdict"], bool):
                raise ValueError(f"Missing boolean scorer output in {results_path}")

            rule_verdict = "fault_detected" if anomaly_detected else "network_healthy"
            summary_text = " ".join(
                [*agent_output.get("evidence", []), agent_output.get("reasoning", "")]
            )
            packet_loss = result["scenario_id"].startswith("generated_packet_loss_")
            initial_context = json.loads(message) if packet_loss else {}
            anomaly_pairs = {
                (
                    anomaly.get("src_name"),
                    anomaly.get("dst_ip"),
                    anomaly.get("dst_name"),
                    anomaly.get("src_ip"),
                )
                for anomaly in (
                    initial_context.get("symptoms", {})
                    .get("observations", {})
                    .get("pingmesh_metrics", {})
                    .get("anomalies", [])
                )
            }
            ping_calls = [
                call.get("args", {})
                for call in agent_output.get("tool_calls", [])
                if call.get("tool") == "ping_test"
            ]
            exact_endpoint_pairs = set()
            exact_endpoint_ping_calls = 0
            for call in ping_calls:
                for src_name, dst_ip, dst_name, src_ip in anomaly_pairs:
                    if (call.get("src") == src_name and call.get("dst_ip") == dst_ip) or (
                        call.get("src") == dst_name and call.get("dst_ip") == src_ip
                    ):
                        exact_endpoint_pairs.add((src_name, dst_ip, dst_name, src_ip))
                        exact_endpoint_ping_calls += 1
                        break
            matching_ping_results: list[tuple[int, int]] = []
            seen_ping_result_ids: set[str] = set()
            if packet_loss:
                for step_index, step in enumerate(trajectory["steps"]):
                    messages = (step.get("extra") or {}).get("llm_request", {}).get(
                        "messages", []
                    )
                    for tool_message in messages:
                        tool_call_id = tool_message.get("tool_call_id")
                        if (
                            tool_message.get("role") != "tool"
                            or tool_message.get("name") != "ping_test"
                            or not isinstance(tool_call_id, str)
                            or tool_call_id in seen_ping_result_ids
                        ):
                            continue
                        seen_ping_result_ids.add(tool_call_id)
                        contents = tool_message.get("content", [])
                        if not isinstance(contents, list):
                            continue
                        for content in contents:
                            try:
                                ping_result = json.loads(content.get("text", ""))
                            except (AttributeError, json.JSONDecodeError):
                                continue
                            if not isinstance(ping_result, dict) or not all(
                                key in ping_result
                                for key in ("source", "destination", "output")
                            ):
                                continue
                            matches_anomaly_endpoints = any(
                                (
                                    ping_result["source"] == src_name
                                    and ping_result["destination"] == dst_ip
                                )
                                or (
                                    ping_result["source"] == dst_name
                                    and ping_result["destination"] == src_ip
                                )
                                for src_name, dst_ip, dst_name, src_ip in anomaly_pairs
                            )
                            if matches_anomaly_endpoints:
                                ping_summary = re.search(
                                    r"(\d+) packets transmitted,\s*(\d+) (?:packets )?received",
                                    ping_result["output"],
                                )
                                if ping_summary is None:
                                    raise ValueError(
                                        f"Unparseable ping result in {trace_path}: {tool_call_id}"
                                    )
                                matching_ping_results.append(
                                    (int(ping_summary.group(1)), int(ping_summary.group(2)))
                                )
                                transmitted, received = map(int, ping_summary.groups())
                                ping_audit_events.append(
                                    {
                                        "netopsbench_code_commit": NETOPSBENCH_CODE_COMMIT,
                                        "hf_dataset_revision": HF_DATASET_REVISION,
                                        "provider": archive["provider"],
                                        "model": archive["model"],
                                        "scale": archive["scale"],
                                        "run_id": archive["run_id"],
                                        "scenario_id": result["scenario_id"],
                                        "case_id": result["case_id"],
                                        "step_index": step_index,
                                        "step_id": step.get("step_id"),
                                        "timestamp": step.get("timestamp"),
                                        "tool_call_id": tool_call_id,
                                        "source": ping_result["source"],
                                        "destination": ping_result["destination"],
                                        "count": ping_result.get("count"),
                                        "payload_size": ping_result.get("payload_size"),
                                        "dont_fragment": ping_result.get("dont_fragment"),
                                        "packets_transmitted": transmitted,
                                        "packets_received": received,
                                        "packets_lost": transmitted - received,
                                    }
                                )
                            break
            matching_pings_all_clean = bool(matching_ping_results) and all(
                transmitted == received
                for transmitted, received in matching_ping_results
            )
            matching_pings_any_loss = any(
                transmitted > received
                for transmitted, received in matching_ping_results
            )
            records.append(
                {
                    "netopsbench_code_commit": NETOPSBENCH_CODE_COMMIT,
                    "hf_dataset_revision": HF_DATASET_REVISION,
                    "provider": archive["provider"],
                    "model": archive["model"],
                    "scale": archive["scale"],
                    "run_id": archive["run_id"],
                    "scenario_id": result["scenario_id"],
                    "case_id": result["case_id"],
                    "ground_truth_healthy": healthy,
                    "initial_anomalies_detected": anomaly_detected,
                    "rule_verdict": rule_verdict,
                    "agent_verdict": agent_output["verdict"],
                    "agent_correct_verdict": bool(result["correct_verdict"]),
                    "rule_correct_verdict": rule_verdict
                    == ("network_healthy" if healthy else "fault_detected"),
                    "packet_loss_case": packet_loss,
                    "packet_loss_anomaly_endpoint_pairs": len(anomaly_pairs)
                    if packet_loss
                    else 0,
                    "live_ping_calls": len(ping_calls),
                    "live_ping_matching_anomaly_endpoint_calls": exact_endpoint_ping_calls,
                    "live_ping_covers_anomaly_endpoint_pair": bool(exact_endpoint_pairs),
                    "packet_loss_matching_endpoint_ping_results": len(matching_ping_results),
                    "packet_loss_matching_endpoint_ping_packets_transmitted": sum(
                        transmitted for transmitted, _ in matching_ping_results
                    ),
                    "packet_loss_matching_endpoint_ping_packets_received": sum(
                        received for _, received in matching_ping_results
                    ),
                    "packet_loss_matching_endpoint_ping_loss_free_results": sum(
                        transmitted == received
                        for transmitted, received in matching_ping_results
                    ),
                    "packet_loss_matching_endpoint_ping_results_with_loss": sum(
                        transmitted > received
                        for transmitted, received in matching_ping_results
                    ),
                    "packet_loss_matching_endpoint_pings_all_clean": matching_pings_all_clean,
                    "packet_loss_matching_endpoint_pings_any_loss": matching_pings_any_loss,
                    "agent_wrong_with_exact_anomaly_endpoint_ping": packet_loss
                    and not bool(result["correct_verdict"])
                    and bool(exact_endpoint_pairs),
                    "incorrect_packet_loss_has_clean_current_cue": packet_loss
                    and not bool(result["correct_verdict"])
                    and bool(CLEAN_CURRENT_CUE.search(summary_text)),
                    "initial_context_chars": len(message),
                    "initial_context_at_or_over_200k_chars": len(message)
                    >= MESSAGE_CAP_CHARS,
                }
            )

    if len(records) != 319:
        raise ValueError(f"Expected the 319-case v0.2 release, found {len(records)}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    columns = list(records[0])
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)
    if args.ping_output is not None:
        args.ping_output.parent.mkdir(parents=True, exist_ok=True)
        with args.ping_output.open("w", encoding="utf-8", newline="") as stream:
            columns = list(ping_audit_events[0]) if ping_audit_events else []
            writer = csv.DictWriter(stream, fieldnames=columns)
            writer.writeheader()
            writer.writerows(ping_audit_events)

    packet_loss_records = [row for row in records if row["packet_loss_case"]]
    verdict_counts = Counter(str(row["agent_verdict"]) for row in records)
    packet_loss_verdict_counts = Counter(
        str(row["agent_verdict"]) for row in packet_loss_records
    )
    by_scale: dict[str, dict[str, int]] = {}
    for scale in sorted({str(row["scale"]) for row in records}):
        scale_records = [row for row in records if row["scale"] == scale]
        scale_packet_loss = [row for row in scale_records if row["packet_loss_case"]]
        by_scale[scale] = {
            "cases": len(scale_records),
            "agent_correct": sum(bool(row["agent_correct_verdict"]) for row in scale_records),
            "rule_correct": sum(bool(row["rule_correct_verdict"]) for row in scale_records),
            "packet_loss_cases": len(scale_packet_loss),
            "packet_loss_agent_correct": sum(
                bool(row["agent_correct_verdict"]) for row in scale_packet_loss
            ),
            "packet_loss_rule_correct": sum(
                bool(row["rule_correct_verdict"]) for row in scale_packet_loss
            ),
            "packet_loss_cases_with_matching_endpoint_ping": sum(
                bool(row["live_ping_covers_anomaly_endpoint_pair"])
                for row in scale_packet_loss
            ),
        }
    rule_only = sum(
        bool(row["rule_correct_verdict"]) and not bool(row["agent_correct_verdict"])
        for row in records
    )
    agent_only = sum(
        bool(row["agent_correct_verdict"]) and not bool(row["rule_correct_verdict"])
        for row in records
    )
    summary = {
        "netopsbench_code_commit": NETOPSBENCH_CODE_COMMIT,
        "hf_dataset_revision": HF_DATASET_REVISION,
        "cases": len(records),
        "initial_flag_cases": len(records),
        "initial_messages_at_or_over_200k_chars": sum(
            bool(row["initial_context_at_or_over_200k_chars"]) for row in records
        ),
        "agent_correct_verdict": sum(
            bool(row["agent_correct_verdict"]) for row in records
        ),
        "rule_correct_verdict": sum(bool(row["rule_correct_verdict"]) for row in records),
        "rule_true_positive": sum(
            bool(row["initial_anomalies_detected"])
            and not bool(row["ground_truth_healthy"])
            for row in records
        ),
        "rule_false_positive": sum(
            bool(row["initial_anomalies_detected"])
            and bool(row["ground_truth_healthy"])
            for row in records
        ),
        "rule_false_negative": sum(
            not bool(row["initial_anomalies_detected"])
            and not bool(row["ground_truth_healthy"])
            for row in records
        ),
        "rule_true_negative": sum(
            not bool(row["initial_anomalies_detected"])
            and bool(row["ground_truth_healthy"])
            for row in records
        ),
        "paired_rule_only_correct": rule_only,
        "paired_agent_only_correct": agent_only,
        "paired_both_correct": sum(
            bool(row["rule_correct_verdict"]) and bool(row["agent_correct_verdict"])
            for row in records
        ),
        "paired_both_wrong": sum(
            not bool(row["rule_correct_verdict"]) and not bool(row["agent_correct_verdict"])
            for row in records
        ),
        "agent_verdict_counts": dict(sorted(verdict_counts.items())),
        "by_scale": by_scale,
        "packet_loss_cases": len(packet_loss_records),
        "packet_loss_agent_correct": sum(
            bool(row["agent_correct_verdict"]) for row in packet_loss_records
        ),
        "packet_loss_rule_correct": sum(
            bool(row["rule_correct_verdict"]) for row in packet_loss_records
        ),
        "packet_loss_incorrect_agent_with_clean_current_cue": sum(
            bool(row["incorrect_packet_loss_has_clean_current_cue"])
            for row in packet_loss_records
        ),
        "packet_loss_cases_with_matching_anomaly_endpoint_ping": sum(
            bool(row["live_ping_covers_anomaly_endpoint_pair"])
            for row in packet_loss_records
        ),
        "packet_loss_agent_wrong_despite_exact_anomaly_endpoint_ping": sum(
            bool(row["agent_wrong_with_exact_anomaly_endpoint_ping"])
            for row in packet_loss_records
        ),
        "packet_loss_cases_with_all_matching_endpoint_pings_clean": sum(
            bool(row["packet_loss_matching_endpoint_pings_all_clean"])
            for row in packet_loss_records
        ),
        "packet_loss_cases_with_any_matching_endpoint_ping_loss": sum(
            bool(row["packet_loss_matching_endpoint_pings_any_loss"])
            for row in packet_loss_records
        ),
        "packet_loss_agent_wrong_with_all_matching_endpoint_pings_clean": sum(
            bool(row["packet_loss_matching_endpoint_pings_all_clean"])
            and not bool(row["agent_correct_verdict"])
            for row in packet_loss_records
        ),
        "packet_loss_agent_wrong_with_matching_endpoint_ping_loss": sum(
            bool(row["packet_loss_matching_endpoint_pings_any_loss"])
            and not bool(row["agent_correct_verdict"])
            for row in packet_loss_records
        ),
        "packet_loss_matching_endpoint_ping_calls": sum(
            int(row["packet_loss_matching_endpoint_ping_results"])
            for row in packet_loss_records
        ),
        "packet_loss_matching_endpoint_ping_packets_transmitted": sum(
            int(row["packet_loss_matching_endpoint_ping_packets_transmitted"])
            for row in packet_loss_records
        ),
        "packet_loss_matching_endpoint_ping_packets_received": sum(
            int(row["packet_loss_matching_endpoint_ping_packets_received"])
            for row in packet_loss_records
        ),
        "packet_loss_agent_verdict_counts": dict(
            sorted(packet_loss_verdict_counts.items())
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
