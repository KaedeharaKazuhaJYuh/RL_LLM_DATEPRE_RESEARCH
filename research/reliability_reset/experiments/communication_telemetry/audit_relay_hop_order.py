"""Audit NIKA UDP relay order against the pinned P4 hop-role order."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "input",
        nargs="?",
        type=Path,
        default=here / "NIKA_PAIRED_REPORT_ONLY_RELAY_EVENTS_2026_11_07.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=here / "NIKA_RELAY_HOP_ORDER_AUDIT_2026_11_07.json",
    )
    args = parser.parse_args()
    raw = args.input.read_bytes()
    received: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    forwarded: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
    event_counts: dict[str, int] = defaultdict(int)

    for line in raw.decode("utf-8").splitlines():
        event = json.loads(line)
        name = event.get("event")
        event_counts[name] += 1
        if name not in {"report_received", "report_forwarded"}:
            continue
        flow_id, packet_id, switch_id = event["key"]
        key = (str(flow_id), str(packet_id))
        observation = (int(event["received_index"]), int(switch_id))
        (received if name == "report_received" else forwarded)[key].append(
            observation
        )

    all_order_errors = []
    upstream_order_errors = []
    all_adjacent_pairs = 0
    all_adjacent_reversals = 0
    all_inversion_pairs = 0
    for key, observations in received.items():
        observations.sort()
        ranks = [
            0 if switch_id < 100 else 1 if switch_id < 200 else 2
            for _, switch_id in observations
        ]
        adjacent = sum(
            ranks[index] > ranks[index + 1]
            for index in range(len(ranks) - 1)
        )
        inversions = sum(
            ranks[left] > ranks[right]
            for left in range(len(ranks))
            for right in range(left + 1, len(ranks))
        )
        all_adjacent_pairs += max(0, len(ranks) - 1)
        all_adjacent_reversals += adjacent
        all_inversion_pairs += inversions
        if inversions:
            all_order_errors.append(
                {
                    "flow_id": key[0],
                    "packet_id": key[1],
                    "switch_ids_in_relay_receive_order": [
                        switch_id for _, switch_id in observations
                    ],
                    "adjacent_reversals": adjacent,
                    "inversion_pairs": inversions,
                }
            )

    for key, observations in forwarded.items():
        observations.sort()
        roles = [
            0 if switch_id < 100 else 1 if switch_id < 200 else 2
            for _, switch_id in observations
        ]
        if len(roles) >= 2 and any(
            roles[index] > roles[index + 1] for index in range(len(roles) - 1)
        ):
            upstream_order_errors.append(
                {
                    "flow_id": key[0],
                    "packet_id": key[1],
                    "switch_ids_in_relay_forward_order": [
                        switch_id for _, switch_id in observations
                    ],
                }
            )

    result = {
        "schema_version": 1,
        "scope": "single low-rate report-only arm; relay order audit, not Agent impact",
        "input": str(args.input),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "path_role_order": ["gateway", "spine", "leaf"],
        "switch_id_role_mapping": "<100 gateway; 100-199 spine; >=200 leaf (pinned NIKA topology model)",
        "event_counts": dict(sorted(event_counts.items())),
        "packets_with_received_reports": len(received),
        "received_report_order": {
            "adjacent_hop_pairs": all_adjacent_pairs,
            "adjacent_role_reversals": all_adjacent_reversals,
            "packets_with_any_role_inversion": len(all_order_errors),
            "inversion_pairs": all_inversion_pairs,
            "examples": all_order_errors,
        },
        "forwarded_upstream_order": {
            "packets_with_forwarded_reports": len(forwarded),
            "packets_with_gateway_spine_reversal": len(upstream_order_errors),
            "examples": upstream_order_errors,
        },
        "interpretation_limit": (
            "Relay receive/forward order is measured. The raw NIKA collector rows were not retained, "
            "so collector hop_sequence order and any Agent-facing effect are not directly confirmed."
        ),
    }
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
