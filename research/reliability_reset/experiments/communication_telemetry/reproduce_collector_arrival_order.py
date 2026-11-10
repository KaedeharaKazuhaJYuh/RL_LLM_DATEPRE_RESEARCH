"""Exercise the pinned NIKA collector with deliberately reordered UDP reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("collector", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).with_name(
            "NIKA_COLLECTOR_ORDER_SEMANTICS_2026_11_07.json"
        ),
    )
    args = parser.parse_args()
    collector_source = args.collector.read_bytes()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]

    with tempfile.TemporaryDirectory(prefix="faultda-nika-collector-order-") as tmp:
        output = Path(tmp) / "collector.jsonl"
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(
            [
                sys.executable,
                str(args.collector),
                "--listen",
                "127.0.0.1",
                "--port",
                str(port),
                "--output",
                str(output),
            ],
            cwd=args.collector.parent,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
        try:
            time.sleep(0.2)
            expected_path = [2, 101, 201]
            sent_order = [101, 2, 201]
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
                for switch_id in sent_order:
                    report = {
                        "flow_id": "collector-order-probe",
                        "packet_id": "1",
                        "switch_id": switch_id,
                        "packet_timestamp": 1_794_028_000_000_000_000,
                        "sink": switch_id >= 200,
                    }
                    sender.sendto(
                        json.dumps(report, separators=(",", ":")).encode(),
                        ("127.0.0.1", port),
                    )
                    time.sleep(0.03)

            deadline = time.monotonic() + 3
            rows = []
            while time.monotonic() < deadline:
                if output.exists():
                    rows = [
                        json.loads(line)
                        for line in output.read_text(encoding="utf-8").splitlines()
                    ]
                    if len(rows) == len(sent_order):
                        break
                if process.poll() is not None:
                    raise RuntimeError(
                        "NIKA collector exited early: " + (process.stderr.read() or "")
                    )
                time.sleep(0.02)
            if len(rows) != len(sent_order):
                raise TimeoutError(
                    f"collector wrote {len(rows)} of {len(sent_order)} UDP records"
                )

            observed_order = [
                int(hop["switch_id"]) for hop in rows[-1]["hop_sequence"]
            ]
            result = {
                "schema_version": 1,
                "scope": "local UDP component reproduction; not a NIKA network run or Agent evaluation",
                "collector_source_sha256": hashlib.sha256(
                    collector_source
                ).hexdigest(),
                "collector_source": "nika/src/nika/net_env/p4_dc_gateway/collector.py",
                "collector_port": port,
                "sent_switch_id_order": sent_order,
                "expected_topology_role_order": expected_path,
                "collector_hop_sequence_order": observed_order,
                "arrival_order_preserved": observed_order == sent_order,
                "collector_row_count": len(rows),
                "final_trace_complete": rows[-1]["trace_complete"],
                "interpretation_limit": (
                    "This verifies collector behavior for a controlled UDP arrival sequence only. "
                    "It does not prove the collector order in the archived NIKA runtime run or any Agent effect."
                ),
            }
            args.output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


if __name__ == "__main__":
    main()
