"""Replay a counter-only rule on the recorded NIKA terminal-loss pair."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=Path(__file__).with_name("NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source_path = args.input.resolve()
    raw = source_path.read_bytes()
    record = json.loads(raw)
    snapshots = record["leaf_counter_snapshots"]

    conditions = (
        {
            "condition_id": "report_only_burst",
            "before": "before_background_burst",
            "after": "after_background_burst",
        },
        {
            "condition_id": "leaf_loss_burst",
            "before": "before_matched_leaf_loss_burst",
            "after": "after_matched_leaf_loss_burst",
        },
    )

    output_episodes = []
    for condition in conditions:
        before = snapshots[condition["before"]]
        after = snapshots[condition["after"]]
        ingress_delta = sum(
            int(item["packets"]) for item in after["ingress"].values()
        ) - sum(int(item["packets"]) for item in before["ingress"].values())
        egress_delta = sum(
            int(item["packets"]) for item in after["egress"].values()
        ) - sum(int(item["packets"]) for item in before["egress"].values())

        if ingress_delta <= 0 or egress_delta < 0 or egress_delta > ingress_delta:
            prediction = "underdetermined"
        elif egress_delta == 0:
            prediction = "terminal_data_plane_loss"
        elif egress_delta == ingress_delta:
            prediction = "packet_reached_egress_report_loss"
        else:
            prediction = "underdetermined"

        if condition["condition_id"] == "report_only_burst":
            service_received = int(record["service_udp_packet_capture"]["packets"])
            sink_reports_dropped = int(record["report_only_relay_summary"]["report_dropped_count"])
            truth = (
                "packet_reached_egress_report_loss"
                if service_received > 0 and sink_reports_dropped > 0
                else "truth_not_supported"
            )
        else:
            service_received = int(
                record["matched_leaf_loss_service_observations"]["udp_socket_receipts"]
            )
            service_capture = int(
                record["matched_leaf_loss_service_observations"]["af_packet_packets"]
            )
            truth = (
                "terminal_data_plane_loss"
                if service_received == 0 and service_capture == 0
                else "truth_not_supported"
            )

        output_episodes.append(
            {
                "condition_id": condition["condition_id"],
                "visible_counter_input": {
                    "target_switch": record["target_switch"],
                    "ingress_packets": ingress_delta,
                    "egress_packets": egress_delta,
                },
                "prediction": prediction,
                "evaluator_only_truth": truth,
                "correct": prediction == truth,
            }
        )

    correct_count = sum(item["correct"] for item in output_episodes)
    result = {
        "protocol": "nika-counter-rule-replay-v1",
        "rule": "sum target-leaf ingress and egress packet deltas; classify only exact conservation or zero-egress cases",
        "source_file": source_path.name,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "nika_commit": record["nika_commit"],
        "rule_inputs": "Recorded per-port counter snapshots only; no packet-capture, relay, fault-table, or ground-truth fields are supplied to the rule.",
        "episodes": output_episodes,
        "summary": {
            "episode_count": len(output_episodes),
            "correct_count": correct_count,
            "descriptive_accuracy": correct_count / len(output_episodes),
            "independent_task_clusters": 1,
        },
        "limits": [
            "Both conditions are one paired small-topology workload, not independent task clusters.",
            "The rule uses the recorded target switch as its scope; the archived run does not retain the exact raw MCP read output used to establish that scope from Agent-visible evidence.",
            "This is an offline replay of recorded counters, not a live Agent comparison or a frozen blind test.",
            "The closed-world rule does not establish performance under unrelated traffic, other concurrent faults, route changes, or counter resets.",
        ],
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
