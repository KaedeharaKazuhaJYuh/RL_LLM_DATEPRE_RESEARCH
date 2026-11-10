"""Deterministically drop selected NIKA UDP telemetry reports before collection."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import select
import socket
import time
from pathlib import Path


def write_event(stream, event: dict) -> None:
    stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
    stream.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--listen-port", type=int, default=32766)
    parser.add_argument("--collector", default="127.0.0.1")
    parser.add_argument("--collector-port", type=int, default=32767)
    parser.add_argument("--drop-plan", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--max-reports", type=int)
    parser.add_argument("--duration-seconds", type=float)
    args = parser.parse_args()

    if not 1 <= args.listen_port <= 65535 or not 1 <= args.collector_port <= 65535:
        parser.error("UDP ports must be between 1 and 65535")
    if args.drop_plan.resolve() == args.events.resolve():
        parser.error("--events must be a different file from --drop-plan")
    if args.max_reports is not None and args.max_reports < 1:
        parser.error("--max-reports must be positive")
    if args.duration_seconds is not None and (
        not math.isfinite(args.duration_seconds) or args.duration_seconds <= 0
    ):
        parser.error("--duration-seconds must be finite and positive")

    plan_bytes = args.drop_plan.read_bytes()
    drop_plan: set[tuple[str, str, str]] = set()
    exact_scopes: set[tuple[str, str]] = set()
    wildcard_scopes: set[tuple[str, str]] = set()
    for line_number, line in enumerate(plan_bytes.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            parser.error(f"drop-plan line {line_number} is invalid JSON: {error.msg}")
        if not isinstance(item, dict) or not all(
            field in item for field in ("flow_id", "packet_id", "switch_id")
        ):
            parser.error(
                f"drop-plan line {line_number} needs flow_id, packet_id and switch_id"
            )
        key = (str(item["flow_id"]), str(item["packet_id"]), str(item["switch_id"]))
        if not all(key) or key in drop_plan:
            parser.error(f"drop-plan line {line_number} has an empty or duplicate key")
        scope = (key[0], key[2])
        scopes = wildcard_scopes if key[1] == "*" else exact_scopes
        conflicting_scopes = exact_scopes if key[1] == "*" else wildcard_scopes
        if scope in conflicting_scopes:
            parser.error(
                f"drop-plan line {line_number} overlaps an exact and wildcard target"
            )
        scopes.add(scope)
        drop_plan.add(key)

    args.events.parent.mkdir(parents=True, exist_ok=True)
    code_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    plan_sha256 = hashlib.sha256(plan_bytes).hexdigest()
    collector = (args.collector, args.collector_port)
    received_count = 0
    forwarded_count = 0
    dropped_count = 0
    seen_drop_keys: dict[tuple[str, str, str], int] = {}
    deadline = (
        time.monotonic() + args.duration_seconds
        if args.duration_seconds is not None
        else None
    )

    with args.events.open("x", encoding="utf-8", newline="\n") as events:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver, socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM
        ) as sender:
            try:
                receiver.bind((args.listen, args.listen_port))
            except OSError as error:
                write_event(
                    events,
                    {
                        "event": "run_failed",
                        "run_id": args.run_id,
                        "stage": "bind",
                        "error_type": type(error).__name__,
                        "error": str(error),
                        "utc_ns": time.time_ns(),
                    },
                )
                raise

            write_event(
                events,
                {
                    "event": "run_started",
                    "schema_version": 1,
                    "run_id": args.run_id,
                    "listen": [args.listen, args.listen_port],
                    "collector": list(collector),
                    "drop_plan_sha256": plan_sha256,
                    "drop_target_count": len(drop_plan),
                    "relay_code_sha256": code_sha256,
                    "utc_ns": time.time_ns(),
                    "monotonic_ns": time.monotonic_ns(),
                },
            )
            stop_reason = "keyboard_interrupt"
            try:
                while args.max_reports is None or received_count < args.max_reports:
                    if deadline is not None:
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            stop_reason = "duration_limit"
                            break
                        readable, _, _ = select.select(
                            [receiver], [], [], min(remaining, 0.5)
                        )
                        if not readable:
                            continue
                    payload, source = receiver.recvfrom(65535)
                    received_count += 1
                    report = None
                    try:
                        decoded = json.loads(payload)
                        if isinstance(decoded, dict):
                            report = decoded
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        pass

                    key = None
                    drop_target = None
                    if report is not None and all(
                        field in report for field in ("flow_id", "packet_id", "switch_id")
                    ):
                        key = (
                            str(report["flow_id"]),
                            str(report["packet_id"]),
                            str(report["switch_id"]),
                        )
                        wildcard_key = (key[0], "*", key[2])
                        if key in drop_plan:
                            drop_target = key
                        elif wildcard_key in drop_plan:
                            drop_target = wildcard_key

                    event = {
                        "run_id": args.run_id,
                        "received_index": received_count,
                        "source": list(source),
                        "key": list(key) if key is not None else None,
                        "payload_sha256": hashlib.sha256(payload).hexdigest(),
                        "received_utc_ns": time.time_ns(),
                        "received_monotonic_ns": time.monotonic_ns(),
                    }
                    write_event(events, {"event": "report_received", **event})
                    if drop_target is not None:
                        dropped_count += 1
                        seen_drop_keys[drop_target] = (
                            seen_drop_keys.get(drop_target, 0) + 1
                        )
                        write_event(
                            events,
                            {
                                "event": "report_dropped",
                                **event,
                                "drop_target": list(drop_target),
                                "action_utc_ns": time.time_ns(),
                                "action_monotonic_ns": time.monotonic_ns(),
                            },
                        )
                    else:
                        try:
                            accepted_bytes = sender.sendto(payload, collector)
                        except OSError as error:
                            stop_reason = "forward_error"
                            write_event(
                                events,
                                {
                                    "event": "report_forward_error",
                                    **event,
                                    "error_type": type(error).__name__,
                                    "error": str(error),
                                    "action_utc_ns": time.time_ns(),
                                    "action_monotonic_ns": time.monotonic_ns(),
                                },
                            )
                            raise
                        forwarded_count += 1
                        write_event(
                            events,
                            {
                                "event": "report_forwarded",
                                **event,
                                "sendto_accepted_bytes": accepted_bytes,
                                "action_utc_ns": time.time_ns(),
                                "action_monotonic_ns": time.monotonic_ns(),
                            },
                        )
                    if args.max_reports is not None and received_count >= args.max_reports:
                        stop_reason = "report_limit"
            except KeyboardInterrupt:
                pass
            except OSError:
                if stop_reason != "forward_error":
                    stop_reason = "socket_error"
                raise
            finally:
                write_event(
                    events,
                    {
                        "event": "run_finished",
                        "run_id": args.run_id,
                        "stop_reason": stop_reason,
                        "received_count": received_count,
                        "forwarded_count": forwarded_count,
                        "intentionally_dropped_count": dropped_count,
                        "drop_targets": [
                            {"key": list(key), "matched_count": seen_drop_keys.get(key, 0)}
                            for key in sorted(drop_plan)
                        ],
                        "utc_ns": time.time_ns(),
                        "monotonic_ns": time.monotonic_ns(),
                    },
                )


if __name__ == "__main__":
    main()
