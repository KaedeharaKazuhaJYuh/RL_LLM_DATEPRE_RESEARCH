"""Run a local synthetic check of relay flow-scoped packet-ID matching."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)

    relay_path = Path(__file__).with_name("telemetry_report_relay.py")
    plan_path = args.output_dir / "drop-plan.jsonl"
    event_path = args.output_dir / "relay-events.jsonl"
    result_path = args.output_dir / "result.json"
    plan_bytes = (
        json.dumps(
            {"flow_id": "target-flow", "packet_id": "*", "switch_id": 3}
        )
        + "\n"
    ).encode()
    plan_path.write_bytes(plan_bytes)

    port_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port_socket.bind(("127.0.0.1", 0))
    relay_port = port_socket.getsockname()[1]
    port_socket.close()
    port_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    port_socket.bind(("127.0.0.1", 0))
    collector_port = port_socket.getsockname()[1]
    port_socket.close()

    collector = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    collector.bind(("127.0.0.1", collector_port))
    collector.settimeout(0.5)
    relay = subprocess.Popen(
        [
            sys.executable,
            str(relay_path),
            "--listen",
            "127.0.0.1",
            "--listen-port",
            str(relay_port),
            "--collector",
            "127.0.0.1",
            "--collector-port",
            str(collector_port),
            "--drop-plan",
            str(plan_path),
            "--events",
            str(event_path),
            "--run-id",
            "flow-scope-smoke",
            "--max-reports",
            "4",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    reports = [
        {"flow_id": "target-flow", "packet_id": "101", "switch_id": 3},
        {"flow_id": "target-flow", "packet_id": "102", "switch_id": 3},
        {"flow_id": "target-flow", "packet_id": "103", "switch_id": 4},
        {"flow_id": "other-flow", "packet_id": "104", "switch_id": 3},
    ]
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if event_path.exists() and '"event":"run_started"' in event_path.read_text(
                encoding="utf-8"
            ):
                break
            if relay.poll() is not None:
                raise RuntimeError("Relay exited before receiving reports")
            time.sleep(0.02)
        else:
            raise TimeoutError("Relay did not start before the deadline")

        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        for report in reports:
            sender.sendto(
                json.dumps(report).encode(), ("127.0.0.1", relay_port)
            )
        relay.communicate(timeout=10)

        rows = [
            json.loads(line)
            for line in event_path.read_text(encoding="utf-8").splitlines()
        ]
        started = next(row for row in rows if row["event"] == "run_started")
        finished = next(row for row in rows if row["event"] == "run_finished")
        dropped = [row for row in rows if row["event"] == "report_dropped"]
        forwarded = [row for row in rows if row["event"] == "report_forwarded"]
        collector_rows = []
        while len(collector_rows) < len(forwarded):
            try:
                collector_rows.append(json.loads(collector.recv(65535)))
            except socket.timeout:
                break

        dropped_keys = [tuple(row["key"]) for row in dropped]
        forwarded_keys = {tuple(row["key"]) for row in forwarded}
        collector_keys = {
            (row["flow_id"], row["packet_id"], str(row["switch_id"]))
            for row in collector_rows
        }
        expected_dropped = [("target-flow", "101", "3"), ("target-flow", "102", "3")]
        if (
            dropped_keys != expected_dropped
            or forwarded_keys != collector_keys
            or finished["intentionally_dropped_count"] != 2
            or finished["forwarded_count"] != 2
        ):
            raise AssertionError(
                {
                    "dropped": dropped_keys,
                    "forwarded_events": sorted(forwarded_keys),
                    "collector_received": sorted(collector_keys),
                    "run_finished": finished,
                }
            )

        result = {
            "schema": "nika-relay-flow-scope-smoke-v1",
            "synthetic_inputs": reports,
            "drop_plan": {
                "flow_id": "target-flow",
                "packet_id": "*",
                "switch_id": 3,
            },
            "observed": {
                "dropped": [list(key) for key in dropped_keys],
                "forwarded": [list(key) for key in sorted(forwarded_keys)],
                "collector_received": [list(key) for key in sorted(collector_keys)],
                "run_finished": finished,
            },
            "relay_code_sha256": started["relay_code_sha256"],
            "drop_plan_sha256": started["drop_plan_sha256"],
            "event_log_sha256": hashlib.sha256(event_path.read_bytes()).hexdigest(),
            "result": "PASS",
            "scope_limit": (
                "Synthetic localhost relay behavior only; not NIKA runtime or "
                "scientific evidence."
            ),
        }
        result_path.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2))
    finally:
        if relay.poll() is None:
            relay.terminate()
            relay.wait(timeout=5)
        collector.close()


if __name__ == "__main__":
    main()
