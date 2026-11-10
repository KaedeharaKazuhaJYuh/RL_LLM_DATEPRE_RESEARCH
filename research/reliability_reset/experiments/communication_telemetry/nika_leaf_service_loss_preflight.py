"""Bounded runtime preflight for the custom NIKA leaf-to-service loss path.

This compares a report-only relay-drop UDP burst against a matched UDP burst
under leaf-to-service packet loss. It records service-side packet IDs, socket
receipts, relay and collector reports, and aggregate P4 port counters. It is a
single small-topology mechanism check, not an Agent or generalization result.
Run from the pinned NIKA checkout after its lab dependencies are installed.
"""

from __future__ import annotations

import base64
import hashlib
import json
from importlib.metadata import version
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from nika.net_env.verify import http_ok
from nika.problems.registry import get_problem_class
from nika.traffic.burst import (
    BurstTrafficGenerator,
    build_burst_flows,
    flow_id_for_five_tuple,
)
from nika.utils.session_store import SessionStore
from nika.workflows.env.start import start_net_env
from nika.workflows.failure.inject import inject_failure
from nika.workflows.session.close import close_session


def main() -> None:
    scenario = "p4_dc_gateway"
    topo_size = "s"
    switch = "leaf_1"
    service_name = "service_1_1"
    problem_name = "silent_egress_packet_loss"
    result = {
        "protocol": "nika-leaf-service-loss-preflight-v0.9-paired-mechanism-check",
        "nika_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "runner_python_version": sys.version.split()[0],
        "kathara_version": version("kathara"),
        "scenario": scenario,
        "topo_size": topo_size,
        "target_switch": switch,
        "target_service": service_name,
        "phase": "starting_environment",
        "passed": False,
        "scope_limit": (
            "Leaf service-port injection, direct-service TCP probe forwarding, VIP HTTP, and one controlled "
            "matched report-only relay-drop and leaf packet-loss UDP bursts with "
            "service packet capture, collector relay ledgers, and aggregate counters; "
            "no Agent result or independent task cluster is included."
        ),
        "counter_delta_interpretation": (
            "Per-port packet deltas cover each controlled probe window, not individual "
            "flow attribution. The paired run compares the same fixed flow profile in "
            "report-only and leaf-loss arms; raw snapshots are retained for reset/wrap inspection."
        ),
        "background_burst_profile": None,
        "background_telemetry_summary": None,
        "service_udp_packet_capture": None,
        "service_collector_packet_join": None,
        "report_only_relay_summary": None,
        "source_packet_captures": {},
        "collector_raw_artifacts": {},
        "leaf_counter_snapshots": {},
        "leaf_counter_packet_deltas": {},
        "service_egress_counter_packet_deltas": {},
        "fault_table_checks": [],
    }
    session_id: str | None = None
    output_path = Path(os.environ["FAULTDA_PREFLIGHT_RESULT"])

    try:
        session_id = start_net_env(
            scenario,
            topo_size,
            backend="kathara",
            session_tag="faultda-preflight",
        )
        row = SessionStore().get_session(session_id)
        scenario_kwargs = dict(row.get("scenario_params") or {})
        scenario_kwargs["lab_name"] = row["lab_name"]
        scenario_kwargs["topo_size"] = row.get("scenario_topo_size") or topo_size

        problem_cls = get_problem_class(problem_name, scenario)
        if problem_cls is None:
            raise RuntimeError(f"Pinned NIKA does not register {problem_name!r}")
        problem = problem_cls(scenario_name=scenario, **scenario_kwargs)

        model = problem.net_env.model
        services = model.services_on_leaf(switch)
        service_ports = []
        for item in services:
            item_port = model.port_to_peer(switch, item.name)
            if item_port is None or item_port.role != "service":
                raise RuntimeError(f"No leaf-to-service port for {item.name}")
            service_ports.append((item, item_port))
        service = next(item for item, _ in service_ports if item.name == service_name)
        port = next(item_port for item, item_port in service_ports if item.name == service_name)
        result["expected_static_mapping"] = {
            "interface": "eth2",
            "bmv2_port": 3,
        }
        if port.name != "eth2" or port.bmv2_port != 3:
            raise RuntimeError(
                f"Pinned topology mapping changed: {port.name}/{port.bmv2_port}"
            )
        result["target_service_ports"] = [
            {
                "service": item.name,
                "service_ip": item.ip,
                "interface": item_port.name,
                "bmv2_port": item_port.bmv2_port,
            }
            for item, item_port in service_ports
        ]
        vip_backends = list(model.backend_pool)
        if not vip_backends or any(
            not any(backend.name == item.name for item, _ in service_ports)
            for backend in vip_backends
        ):
            raise RuntimeError(
                "The VIP backend pool is not covered by the selected leaf loss ports"
            )
        result["vip_backends"] = [backend.name for backend in vip_backends]

        runtime = problem.runtime
        vip_url = model.vip_url

        def send_service_tcp_probe() -> None:
            runtime.exec(
                "client_1",
                f"nc -z -w 1 {service.ip} 80 || true",
                timeout=5,
            )

        def snapshot_leaf_counters(label: str) -> None:
            raw = runtime.exec(
                "fabric_mgr",
                f"python3 /opt/nika/p4rt_manager.py counters --switch {switch}",
                timeout=30,
            )
            snapshot = json.loads(raw)
            if not snapshot.get("ok") or switch not in snapshot.get("counters", {}):
                raise RuntimeError(f"Could not read {switch} P4 port counters")
            result["leaf_counter_snapshots"][label] = snapshot["counters"][switch]

        def record_packet_counter_delta(label: str, before: str, after: str) -> None:
            before_counters = result["leaf_counter_snapshots"][before]
            after_counters = result["leaf_counter_snapshots"][after]
            result["leaf_counter_packet_deltas"][label] = {
                direction: {
                    port_id: (
                        after_counters.get(direction, {})
                        .get(port_id, {})
                        .get("packets", 0)
                        - before_counters.get(direction, {})
                        .get(port_id, {})
                        .get("packets", 0)
                    )
                    for port_id in sorted(
                        set(before_counters.get(direction, {}))
                        | set(after_counters.get(direction, {}))
                    )
                }
                for direction in ("ingress", "egress")
            }

        def start_source_packet_captures(
            arm: str, flow_filters_by_source: dict[str, list[dict]]
        ) -> dict[str, dict[str, str]]:
            capture_code = r'''import hashlib,json,select,socket,struct,sys,time
filters=json.loads(sys.argv[1])
duration=float(sys.argv[2])
out_path,ready_path,done_path=sys.argv[3:]
flow_by_tuple={(item['source_ip'],item['destination_ip'],17,item['source_port'],item['destination_port']):item['flow_id'] for item in filters}
with open(out_path,'w',encoding='utf-8') as ledger:
    sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3))
    open(ready_path,'w').close()
    deadline=time.monotonic()+duration
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:
            break
        readable,_,_=select.select([sock],[],[],min(remaining,0.5))
        if not readable:
            continue
        frame,address=sock.recvfrom(65535)
        if len(frame)<34:
            continue
        ethertype=struct.unpack('!H',frame[12:14])[0]
        offset=14
        while ethertype in (0x8100,0x88a8) and len(frame)>=offset+4:
            ethertype=struct.unpack('!H',frame[offset+2:offset+4])[0]
            offset+=4
        if ethertype!=0x0800 or len(frame)<offset+20:
            continue
        header=frame[offset:]
        if header[0]>>4!=4 or header[9]!=17:
            continue
        header_len=(header[0]&15)*4
        if header_len<20 or len(header)<header_len+8:
            continue
        src=socket.inet_ntoa(header[12:16])
        dst=socket.inet_ntoa(header[16:20])
        src_port,dst_port,udp_len,_=struct.unpack('!HHHH',header[header_len:header_len+8])
        key=(src,dst,17,src_port,dst_port)
        flow_id=flow_by_tuple.get(key)
        if flow_id is None:
            continue
        packet_id=struct.unpack('!H',header[4:6])[0]
        row={'observed_unix_ns':time.time_ns(),'interface':address[0],'packet_type':address[2] if len(address)>2 else None,'source_ip':src,'destination_ip':dst,'protocol':17,'source_port':src_port,'destination_port':dst_port,'flow_id':flow_id,'packet_id':packet_id,'udp_length':udp_len}
        ledger.write(json.dumps(row,separators=(',',':'))+'\n')
        ledger.flush()
    sock.close()
open(done_path,'w').close()
'''
            captures = {}
            for source, flow_filters in flow_filters_by_source.items():
                remote_path = f"/tmp/faultda-source-{arm}-{capture_key}-{source}.jsonl"
                ready_path = remote_path + ".ready"
                done_path = remote_path + ".done"
                command = (
                    f"python3 -c {shlex.quote(capture_code)} "
                    f"{shlex.quote(json.dumps(flow_filters, separators=(',', ':')))} "
                    f"12 {shlex.quote(remote_path)} {shlex.quote(ready_path)} "
                    f"{shlex.quote(done_path)} >/tmp/faultda-source-{arm}-{source}.log 2>&1 & "
                    "capture_pid=$!; i=0; "
                    f"while [ ! -f {shlex.quote(ready_path)} ] && [ \"$i\" -lt 40 ]; "
                    "do sleep 0.1; i=$((i+1)); done; "
                    f"if [ ! -f {shlex.quote(ready_path)} ]; then "
                    f"cat /tmp/faultda-source-{arm}-{source}.log; exit 1; fi; "
                    "printf 'SOURCE_CAPTURE_READY:%s\\n' \"$capture_pid\""
                )
                started = runtime.exec(source, command, timeout=10).strip()
                if not started.startswith("SOURCE_CAPTURE_READY:"):
                    raise RuntimeError(
                        f"Source packet capture did not start on {source}: {started}"
                    )
                captures[source] = {
                    "remote_path": remote_path,
                    "done_path": done_path,
                }
            return captures

        def finish_source_packet_captures(
            arm: str, captures: dict[str, dict[str, str]]
        ) -> dict[str, set[str]]:
            rows_by_flow: dict[str, set[str]] = {}
            counts_by_flow: dict[str, int] = {}
            all_rows = []
            for source, capture in captures.items():
                output = runtime.exec(
                    source,
                    "i=0; "
                    f"while [ ! -f {shlex.quote(capture['done_path'])} ] "
                    "&& [ \"$i\" -lt 180 ]; do sleep 0.1; i=$((i+1)); done; "
                    f"if [ ! -f {shlex.quote(capture['done_path'])} ]; then "
                    f"printf 'FAULTDA_SOURCE_CAPTURE_TIMEOUT\\n'; exit 124; fi; "
                    f"cat {shlex.quote(capture['remote_path'])}",
                    timeout=25,
                )
                if "FAULTDA_SOURCE_CAPTURE_TIMEOUT" in output:
                    raise RuntimeError(f"Source packet capture timed out on {source}")
                for line in output.splitlines():
                    if not line.strip():
                        continue
                    row = json.loads(line)
                    all_rows.append(row)
                    counts_by_flow[row["flow_id"]] = (
                        counts_by_flow.get(row["flow_id"], 0) + 1
                    )
                    rows_by_flow.setdefault(row["flow_id"], set()).add(
                        str(row["packet_id"])
                    )
            if not all_rows:
                raise RuntimeError(f"Source packet ledger is empty for the {arm} arm")
            if any(
                counts_by_flow[flow_id] != len(packet_ids)
                for flow_id, packet_ids in rows_by_flow.items()
            ):
                raise RuntimeError(
                    f"Source packet IDs are not unique within the {arm} arm"
                )
            artifact_path = output_path.with_name(
                f"NIKA_SOURCE_{arm.upper()}_PACKET_LEDGER.jsonl"
            )
            artifact_path.write_text(
                "\n".join(
                    json.dumps(row, sort_keys=True, separators=(",", ":"))
                    for row in all_rows
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )
            artifact_bytes = artifact_path.read_bytes()
            result["source_packet_captures"][arm] = {
                "observation_point": "source client AF_PACKET egress",
                "packets": len(all_rows),
                "packets_by_flow": dict(sorted(counts_by_flow.items())),
                "unique_packet_ids_by_flow": {
                    flow_id: sorted(packet_ids)
                    for flow_id, packet_ids in sorted(rows_by_flow.items())
                },
                "artifact": artifact_path.name,
                "sha256": hashlib.sha256(artifact_bytes).hexdigest(),
            }
            return rows_by_flow

        snapshot_leaf_counters("before_baseline_probes")
        result["phase"] = "baseline_service_probe"
        for _ in range(2):
            send_service_tcp_probe()
        result["baseline_direct_service_tcp_probe_count"] = 2
        snapshot_leaf_counters("after_baseline_direct_tcp")
        record_packet_counter_delta(
            "baseline_direct_service_tcp",
            "before_baseline_probes",
            "after_baseline_direct_tcp",
        )
        vip_before = [http_ok(runtime, "client_1", vip_url) for _ in range(2)]
        result["baseline_vip_http_ok"] = vip_before
        result["vip_url"] = vip_url
        snapshot_leaf_counters("after_vip_control")
        record_packet_counter_delta(
            "baseline_vip_control",
            "after_baseline_direct_tcp",
            "after_vip_control",
        )
        result["service_egress_counter_packet_deltas"]["baseline_direct_service_tcp"] = {
            item.name: (
                result["leaf_counter_snapshots"]["after_baseline_direct_tcp"]
                .get("egress", {})
                .get(str(item_port.bmv2_port), {})
                .get("packets", 0)
                - result["leaf_counter_snapshots"]["before_baseline_probes"]
                .get("egress", {})
                .get(str(item_port.bmv2_port), {})
                .get("packets", 0)
            )
            for item, item_port in service_ports
        }
        target_baseline_egress = result[
            "service_egress_counter_packet_deltas"
        ]["baseline_direct_service_tcp"][service.name]
        result["baseline_direct_service_tcp_target_egress_packets"] = (
            target_baseline_egress
        )
        result["service_egress_counter_packet_deltas"]["vip_control"] = {
            item.name: (
                result["leaf_counter_snapshots"]["after_vip_control"]
                .get("egress", {})
                .get(str(item_port.bmv2_port), {})
                .get("packets", 0)
                - result["leaf_counter_snapshots"]["after_baseline_direct_tcp"]
                .get("egress", {})
                .get(str(item_port.bmv2_port), {})
                .get("packets", 0)
            )
            for item, item_port in service_ports
        }
        if not all(vip_before):
            raise RuntimeError("VIP HTTP control path is not healthy before injection")
        if target_baseline_egress <= 0:
            raise RuntimeError(
                "Direct watched-service TCP probes produced no target-port egress; "
                "leaf INT-MX decapsulation and service forwarding are not validated"
            )

        result["phase"] = "report_only_telemetry_burst"
        capture_key = hashlib.sha256(session_id.encode()).hexdigest()[:12]
        client_names = [item.name for item in model.clients]
        flow_specs = build_burst_flows(
            client_names,
            service.name,
            "udp",
            seed=20261107,
            flows_per_source=2,
        )
        destination_ip = runtime.get_data_plane_host_ip(service.name)
        if destination_ip != service.ip:
            raise RuntimeError(
                "NIKA service model IP and runtime data-plane IP disagree: "
                f"{service.ip} != {destination_ip}"
            )
        result["service_data_plane_ip"] = destination_ip
        expected_flow_ids = set()
        flow_filters_by_source = {source: [] for source in client_names}
        for flow in flow_specs:
            source_ip = runtime.get_data_plane_host_ip(flow.source)
            flow_id = flow_id_for_five_tuple(
                source_ip,
                destination_ip,
                "udp",
                flow.source_port,
                flow.destination_port,
            )
            expected_flow_ids.add(flow_id)
            flow_filters_by_source[flow.source].append(
                {
                    "source_ip": source_ip,
                    "destination_ip": destination_ip,
                    "source_port": flow.source_port,
                    "destination_port": flow.destination_port,
                    "flow_id": flow_id,
                }
            )
        sink_switch_id = str(model.switch_info[switch].device_id)
        drop_plan_bytes = (
            "".join(
                json.dumps(
                    {
                        "flow_id": flow_id,
                        "packet_id": "*",
                        "switch_id": sink_switch_id,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
                for flow_id in sorted(expected_flow_ids)
            )
        ).encode("utf-8")
        relay_source_bytes = Path(__file__).with_name(
            "telemetry_report_relay.py"
        ).read_bytes()
        relay_remote_path = f"/tmp/faultda-report-relay-{capture_key}.py"
        relay_plan_path = f"/var/lib/nika/faultda-drop-plan-{capture_key}.jsonl"
        relay_events_path = f"/var/lib/nika/faultda-relay-events-{capture_key}.jsonl"
        relay_log_path = output_path.with_name(
            "NIKA_LEAF_SERVICE_LOSS_RELAY_EVENTS.jsonl"
        )
        relay_files = {
            relay_remote_path: base64.b64encode(relay_source_bytes).decode("ascii"),
            relay_plan_path: base64.b64encode(drop_plan_bytes).decode("ascii"),
        }
        write_remote_files_code = "import base64,pathlib; " + "; ".join(
            f"pathlib.Path({path!r}).write_bytes(base64.b64decode({encoded!r}))"
            for path, encoded in relay_files.items()
        )
        runtime.exec(
            "collector",
            f"python3 -c {shlex.quote(write_remote_files_code)}",
            timeout=10,
        )
        collector_setup_command = (
            "collector_pid=$(ps -eo pid=,args= | awk '$2 == \"python3\" "
            "&& $3 == \"collector.py\" && $4 == \"--output\" "
            "&& $5 == \"/var/lib/nika/int_reports.jsonl\" {print $1; exit}'); "
            "if [ -z \"$collector_pid\" ]; then printf 'NO_ORIGINAL_COLLECTOR\\n'; exit 1; fi; "
            "kill \"$collector_pid\"; sleep 0.2; "
            "python3 collector.py --port 32767 --output /var/lib/nika/int_reports.jsonl "
            ">/tmp/faultda-collector-32767.log 2>&1 & new_pid=$!; sleep 0.2; "
            "if ! kill -0 \"$new_pid\" 2>/dev/null; then "
            "cat /tmp/faultda-collector-32767.log; exit 1; fi; "
            "printf 'COLLECTOR_READY:%s\\n' \"$new_pid\""
        )
        collector_setup = runtime.exec(
            "collector", collector_setup_command, timeout=10
        ).strip()
        if not collector_setup.startswith("COLLECTOR_READY:"):
            raise RuntimeError(f"Could not move NIKA collector to UDP/32767: {collector_setup}")
        relay_run_id = f"nika-report-only-{capture_key}"
        relay_start_command = (
            f"python3 {shlex.quote(relay_remote_path)} "
            f"--listen-port 32766 --collector 127.0.0.1 --collector-port 32767 "
            f"--drop-plan {shlex.quote(relay_plan_path)} "
            f"--events {shlex.quote(relay_events_path)} "
            f"--run-id {shlex.quote(relay_run_id)} --duration-seconds 16 "
            f">/tmp/faultda-relay-{capture_key}.log 2>&1 & relay_pid=$!; i=0; "
            f"while ! grep -q '\"event\":\"run_started\"' {shlex.quote(relay_events_path)} "
            "2>/dev/null && [ \"$i\" -lt 40 ]; do sleep 0.1; i=$((i+1)); done; "
            f"if ! grep -q '\"event\":\"run_started\"' {shlex.quote(relay_events_path)} "
            f"2>/dev/null; then cat /tmp/faultda-relay-{capture_key}.log; exit 1; fi; "
            "printf 'RELAY_READY:%s\\n' \"$relay_pid\""
        )
        relay_setup = runtime.exec(
            "collector", relay_start_command, timeout=10
        ).strip()
        if not relay_setup.startswith("RELAY_READY:"):
            raise RuntimeError(f"Report relay did not become ready: {relay_setup}")
        result["report_only_relay_summary"] = {
            "run_id": relay_run_id,
            "target_sink_switch_id": sink_switch_id,
            "target_flow_count": len(expected_flow_ids),
            "drop_plan_sha256": hashlib.sha256(drop_plan_bytes).hexdigest(),
            "relay_code_sha256": hashlib.sha256(relay_source_bytes).hexdigest(),
            "duration_seconds": 16,
        }
        sink_capture_path = f"/tmp/faultda-service-sink-{capture_key}.jsonl"
        sink_ready_path = f"/tmp/faultda-service-sink-{capture_key}.ready"
        sink_done_path = f"/tmp/faultda-service-sink-{capture_key}.done"
        sink_ports_json = json.dumps(sorted({flow.destination_port for flow in flow_specs}))
        sink_capture_code = r'''import json,select,socket,sys,time
ports=json.loads(sys.argv[1])
service_ip=sys.argv[2]
duration=float(sys.argv[3])
out_path,ready_path,done_path=sys.argv[4:]
with open(out_path,"w",encoding="utf-8") as ledger:
    sockets=[]
    for port in ports:
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        sock.bind(("0.0.0.0",port))
        sockets.append(sock)
    open(ready_path,"w").close()
    deadline=time.monotonic()+duration
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:
            break
        readable,_,_=select.select(sockets,[],[],min(remaining,0.5))
        for sock in readable:
            payload,source=sock.recvfrom(65535)
            destination_port=sock.getsockname()[1]
            row={"received_unix_ns":time.time_ns(),"source_ip":source[0],"destination_ip":service_ip,"protocol":17,"source_port":source[1],"destination_port":destination_port,"payload_bytes":len(payload)}
            ledger.write(json.dumps(row,separators=(",",":"))+"\n")
            ledger.flush()
    for sock in sockets:
        sock.close()
open(done_path,"w").close()
'''
        sink_command = (
            f"python3 -c {shlex.quote(sink_capture_code)} "
            f"{shlex.quote(sink_ports_json)} {shlex.quote(service.ip)} 12 {shlex.quote(sink_capture_path)} "
            f"{shlex.quote(sink_ready_path)} {shlex.quote(sink_done_path)} "
            f">/tmp/faultda-service-sink-{capture_key}.log 2>&1 & sink_pid=$!; i=0; "
            f"while [ ! -f {shlex.quote(sink_ready_path)} ] && [ \"$i\" -lt 40 ]; "
            "do sleep 0.1; i=$((i+1)); done; "
            f"if [ ! -f {shlex.quote(sink_ready_path)} ]; then "
            f"cat /tmp/faultda-service-sink-{capture_key}.log; exit 1; fi; "
            "printf '%s\\n' \"$sink_pid\""
        )
        sink_pid_text = runtime.exec(service.name, sink_command, timeout=10).strip()
        if not sink_pid_text.isdigit():
            raise RuntimeError("Evaluator UDP receiver did not bind the planned service ports")
        capture_path = f"/tmp/faultda-service-udp-{capture_key}.jsonl"
        ready_path = f"/tmp/faultda-service-udp-{capture_key}.ready"
        done_path = f"/tmp/faultda-service-udp-{capture_key}.done"
        capture_code = r'''import hashlib,json,select,socket,struct,sys,time
ports=set(json.loads(sys.argv[1]))
duration,out_path,ready_path,done_path=float(sys.argv[2]),sys.argv[3],sys.argv[4],sys.argv[5]
with open(out_path,"w",encoding="utf-8") as ledger:
    sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3))
    open(ready_path,"w").close()
    deadline=time.monotonic()+duration
    while True:
        remaining=deadline-time.monotonic()
        if remaining<=0:
            break
        readable,_,_=select.select([sock],[],[],min(remaining,0.5))
        if not readable:
            continue
        frame,address=sock.recvfrom(65535)
        if len(frame)<34:
            continue
        ethertype=struct.unpack("!H",frame[12:14])[0]
        offset=14
        while ethertype in (0x8100,0x88a8) and len(frame)>=offset+4:
            ethertype=struct.unpack("!H",frame[offset+2:offset+4])[0]
            offset+=4
        if ethertype!=0x0800 or len(frame)<offset+20:
            continue
        header=frame[offset:]
        if header[0]>>4!=4 or header[9]!=17:
            continue
        header_len=(header[0]&15)*4
        if header_len<20 or len(header)<header_len+8:
            continue
        src=socket.inet_ntoa(header[12:16])
        dst=socket.inet_ntoa(header[16:20])
        src_port,dst_port,udp_len,_=struct.unpack("!HHHH",header[header_len:header_len+8])
        if dst_port not in ports:
            continue
        packet_id=struct.unpack("!H",header[4:6])[0]
        identity=(f"{src}|{dst}|17|{src_port}|{dst_port}").encode()
        row={"observed_unix_ns":time.time_ns(),"interface":address[0],"source_ip":src,"destination_ip":dst,"protocol":17,"source_port":src_port,"destination_port":dst_port,"flow_id":hashlib.blake2b(identity,digest_size=8).hexdigest(),"packet_id":packet_id,"udp_length":udp_len}
        ledger.write(json.dumps(row,separators=(",",":"))+"\n")
        ledger.flush()
sock.close()
open(done_path,"w").close()
'''
        capture_command = (
            f"python3 -c {shlex.quote(capture_code)} {shlex.quote(sink_ports_json)} "
            f"12 {shlex.quote(capture_path)} {shlex.quote(ready_path)} {shlex.quote(done_path)} "
            f">/tmp/faultda-service-udp-{capture_key}.log 2>&1 & "
            "capture_pid=$!; i=0; "
            f"while [ ! -f {shlex.quote(ready_path)} ] && [ \"$i\" -lt 40 ]; "
            "do sleep 0.1; i=$((i+1)); done; "
            f"if [ ! -f {shlex.quote(ready_path)} ]; then "
            f"cat /tmp/faultda-service-udp-{capture_key}.log; exit 1; fi; "
            "printf '%s\\n' \"$capture_pid\""
        )
        capture_pid_text = runtime.exec(
            service.name, capture_command, timeout=10
        ).strip()
        if not capture_pid_text.isdigit():
            raise RuntimeError("Service packet capture did not return a process ID")
        capture_pid = int(capture_pid_text)
        report_source_captures = start_source_packet_captures(
            "report_only", flow_filters_by_source
        )
        snapshot_leaf_counters("before_background_burst")
        burst_profile = BurstTrafficGenerator(runtime).run(
            sources=client_names,
            destination=service.name,
            protocol="udp",
            rate="32K",
            packet_size=128,
            duration=3,
            synchronized_start=time.time() + 2.0,
            seed=20261107,
            flows_per_source=2,
            raw_udp=True,
        )
        result["background_burst_profile"] = burst_profile
        flow_ids = [flow["flow_id"] for flow in burst_profile["flows"]]
        if set(flow_ids) != expected_flow_ids:
            raise RuntimeError("Precomputed relay flow keys do not match the burst profile")
        result["background_burst_profile"]["default_sink_bind_attempt_pids"] = (
            result["background_burst_profile"].pop("sink_pids", [])
        )
        result["background_burst_profile"]["service_sink_instrumentation"] = (
            "Evaluator UDP sockets pre-bind the flow ports and replace NIKA's "
            "non-logging sink for this preflight; built-in sink attempts cannot bind."
        )
        time.sleep(6)
        sink_result = runtime.exec(
            service.name,
            "i=0; "
            f"while [ ! -f {shlex.quote(sink_done_path)} ] && [ \"$i\" -lt 160 ]; "
            "do sleep 0.1; i=$((i+1)); done; "
            f"if [ ! -f {shlex.quote(sink_done_path)} ]; then "
            f"printf 'FAULTDA_SINK_TIMEOUT\\n'; cat /tmp/faultda-service-sink-{capture_key}.log; exit 124; fi; "
            f"cat {shlex.quote(sink_capture_path)}",
            timeout=25,
        )
        if "FAULTDA_SINK_TIMEOUT" in sink_result:
            raise RuntimeError(sink_result.strip())
        sink_rows = [
            json.loads(line) for line in sink_result.splitlines() if line.strip()
        ]
        sink_rows = [
            row
            for row in sink_rows
            if row["source_port"]
            and flow_id_for_five_tuple(
                row["source_ip"],
                service.ip,
                "udp",
                row["source_port"],
                row["destination_port"],
            )
            in expected_flow_ids
        ]
        sink_receipts_by_flow: dict[str, int] = {}
        for row in sink_rows:
            flow_id = flow_id_for_five_tuple(
                row["source_ip"],
                service.ip,
                "udp",
                row["source_port"],
                row["destination_port"],
            )
            row["flow_id"] = flow_id
            sink_receipts_by_flow[flow_id] = sink_receipts_by_flow.get(flow_id, 0) + 1
        result["service_udp_socket_receipt"] = {
            "observation_point": "evaluator-owned UDP sockets on service ports",
            "datagrams_received": len(sink_rows),
            "received_by_flow": sink_receipts_by_flow,
            "packet_observations": sink_rows,
            "scope": "report-only fault arm; application socket receipt, without payload modification",
        }
        capture_result = runtime.exec(
            service.name,
            "i=0; "
            f"while [ ! -f {shlex.quote(done_path)} ] && [ \"$i\" -lt 160 ]; "
            "do sleep 0.1; i=$((i+1)); done; "
            f"if [ ! -f {shlex.quote(done_path)} ]; then "
            f"kill {capture_pid} 2>/dev/null; printf 'FAULTDA_CAPTURE_TIMEOUT\\n'; "
            f"cat /tmp/faultda-service-udp-{capture_key}.log; exit 124; fi; "
            f"cat {shlex.quote(capture_path)}",
            timeout=25,
        )
        if "FAULTDA_CAPTURE_TIMEOUT" in capture_result:
            raise RuntimeError(capture_result.strip())
        captured_rows = [
            json.loads(line) for line in capture_result.splitlines() if line.strip()
        ]
        matched_capture_rows = []
        captured_by_flow: dict[str, set[str]] = {}
        for packet in captured_rows:
            if packet["flow_id"] not in expected_flow_ids:
                continue
            matched_capture_rows.append(packet)
            captured_by_flow.setdefault(packet["flow_id"], set()).add(
                str(packet["packet_id"])
            )
        report_source_ids_by_flow = finish_source_packet_captures(
            "report_only", report_source_captures
        )
        for flow_id in sorted(expected_flow_ids):
            if report_source_ids_by_flow.get(flow_id, set()) != captured_by_flow.get(
                flow_id, set()
            ):
                raise RuntimeError(
                    f"Source-egress and service-ingress packet IDs differ for {flow_id}"
                )
        result["service_udp_packet_capture"] = {
            "observation_point": "service_1_1 all-interface AF_PACKET ingress",
            "window_seconds": 12,
            "packets": len(matched_capture_rows),
            "raw_target_port_packets": len(captured_rows),
            "raw_target_port_flow_ids": {
                flow_id: sum(packet["flow_id"] == flow_id for packet in captured_rows)
                for flow_id in sorted({packet["flow_id"] for packet in captured_rows})
            },
            "raw_target_port_sample": captured_rows[:8],
            "unique_packets_by_flow": {
                flow_id: sorted(packet_ids)
                for flow_id, packet_ids in sorted(captured_by_flow.items())
            },
            "packet_observations": matched_capture_rows,
            "scope": "report-only fault arm; business path remains healthy; interface arrival only",
        }
        report_source_counts = result["source_packet_captures"]["report_only"][
            "packets_by_flow"
        ]
        report_service_counts = result["service_udp_packet_capture"][
            "raw_target_port_flow_ids"
        ]
        for flow_id in sorted(expected_flow_ids):
            if report_source_counts.get(flow_id, 0) != report_service_counts.get(
                flow_id, 0
            ):
                raise RuntimeError(
                    f"Source-egress and service-ingress packet counts differ for {flow_id}"
                )
        snapshot_leaf_counters("after_background_burst")
        record_packet_counter_delta(
            "background_burst", "before_background_burst", "after_background_burst"
        )
        flow_ids_json = json.dumps(flow_ids)
        summarize_code = (
            "import json\n"
            f"flow_ids = set(json.loads({flow_ids_json!r}))\n"
            "summary = {flow: {'rows': 0, 'packet_ids': set(), 'sink_packet_ids': set(), 'sink_seen': False} "
            "for flow in flow_ids}\n"
            "with open('/var/lib/nika/int_reports.jsonl', encoding='utf-8') as reports:\n"
            "    for line in reports:\n"
            "        row = json.loads(line)\n"
            "        flow_id = row.get('flow_id')\n"
            "        if flow_id in summary:\n"
            "            item = summary[flow_id]\n"
            "            item['rows'] += 1\n"
            "            item['packet_ids'].add(str(row.get('packet_id')))\n"
            "            item['sink_seen'] = item['sink_seen'] or bool(row.get('sink_seen'))\n"
            "            if row.get('sink_seen'):\n"
            "                item['sink_packet_ids'].add(str(row.get('packet_id')))\n"
            "print(json.dumps({'flows': {flow: {'rows': item['rows'], "
            "'packet_ids': sorted(item['packet_ids']), 'sink_packet_ids': sorted(item['sink_packet_ids']), 'sink_seen': item['sink_seen']} "
            "for flow, item in summary.items()}, 'total_rows': sum(item['rows'] "
            "for item in summary.values())}, sort_keys=True))\n"
        )
        raw_summary = runtime.exec(
            "collector", f"python3 -c {shlex.quote(summarize_code)}", timeout=30
        )
        result["background_telemetry_summary"] = json.loads(raw_summary)
        for flow_id in sorted(expected_flow_ids):
            source_ids = report_source_ids_by_flow.get(flow_id, set())
            collector_ids = set(
                result["background_telemetry_summary"]["flows"][flow_id][
                    "packet_ids"
                ]
            )
            if source_ids != collector_ids:
                raise RuntimeError(
                    f"Source-egress and collector packet IDs differ for {flow_id}"
                )
        collector_output = runtime.exec(
            "collector", "cat /var/lib/nika/int_reports.jsonl", timeout=30
        )
        report_only_rows = [
            line
            for line in collector_output.splitlines()
            if line.strip() and json.loads(line).get("flow_id") in expected_flow_ids
        ]
        if not report_only_rows:
            raise RuntimeError("No raw report-only collector rows were retained")
        report_only_collector_path = output_path.with_name(
            "NIKA_COLLECTOR_REPORT_ONLY_ROWS.jsonl"
        )
        report_only_collector_path.write_text(
            "\n".join(report_only_rows) + "\n", encoding="utf-8", newline="\n"
        )
        report_only_collector_bytes = report_only_collector_path.read_bytes()
        result["collector_raw_artifacts"]["report_only"] = {
            "file": report_only_collector_path.name,
            "rows": len(report_only_rows),
            "sha256": hashlib.sha256(report_only_collector_bytes).hexdigest(),
            "filter": "target flow IDs only; original collector JSONL row order preserved",
        }
        relay_output = runtime.exec(
            "collector",
            "i=0; "
            f"while ! grep -q '\"event\":\"run_finished\"' {shlex.quote(relay_events_path)} "
            "2>/dev/null && [ \"$i\" -lt 90 ]; do sleep 0.1; i=$((i+1)); done; "
            f"cat {shlex.quote(relay_events_path)}",
            timeout=15,
        )
        relay_events = [
            json.loads(line) for line in relay_output.splitlines() if line.strip()
        ]
        relay_finished = next(
            (event for event in reversed(relay_events) if event.get("event") == "run_finished"),
            None,
        )
        relay_log_path.parent.mkdir(parents=True, exist_ok=True)
        relay_log_path.write_text(relay_output, encoding="utf-8", newline="\n")
        result["report_only_relay_summary"].update(
            {
                "events_artifact": relay_log_path.name,
                "run_started": any(
                    event.get("event") == "run_started" for event in relay_events
                ),
                "report_received_count": sum(
                    event.get("event") == "report_received" for event in relay_events
                ),
                "report_forwarded_count": sum(
                    event.get("event") == "report_forwarded" for event in relay_events
                ),
                "report_dropped_count": sum(
                    event.get("event") == "report_dropped" for event in relay_events
                ),
                "run_finished": relay_finished is not None,
                "stop_reason": relay_finished.get("stop_reason") if relay_finished else None,
                "drop_targets": relay_finished.get("drop_targets", []) if relay_finished else [],
            }
        )
        if relay_finished is None:
            raise RuntimeError("Report relay did not write a bounded run_finished record")
        if relay_finished.get("intentionally_dropped_count", 0) < 1:
            raise RuntimeError("Report relay observed no targeted sink reports to drop")
        if any(target.get("matched_count", 0) < 1 for target in relay_finished.get("drop_targets", [])):
            raise RuntimeError("At least one planned flow/sink report target was never observed")
        collector_sink_by_flow = {
            flow_id: set(item["sink_packet_ids"])
            for flow_id, item in result["background_telemetry_summary"]["flows"].items()
        }
        relay_dropped_sink_by_flow: dict[str, set[str]] = {}
        for event in relay_events:
            if event.get("event") == "report_dropped" and str(event["key"][2]) == sink_switch_id:
                flow_id = event["key"][0]
                relay_dropped_sink_by_flow.setdefault(flow_id, set()).add(
                    str(event["key"][1])
                )
        for flow_id in sorted(expected_flow_ids):
            item = result["background_telemetry_summary"]["flows"].get(flow_id)
            if not sink_receipts_by_flow.get(flow_id):
                raise RuntimeError(f"No service UDP socket receipt was observed for {flow_id}")
            service_ids = captured_by_flow.get(flow_id, set())
            dropped_sink_ids = relay_dropped_sink_by_flow.get(flow_id, set())
            if service_ids != dropped_sink_ids:
                raise RuntimeError(
                    f"Service packet IDs do not exactly match relay-dropped sink IDs "
                    f"for {flow_id}: {len(service_ids)} vs {len(dropped_sink_ids)}"
                )
            if item is None or item["rows"] < 1:
                raise RuntimeError(f"Collector received no upstream INT row for {flow_id}")
            if item["sink_seen"] or item["sink_packet_ids"]:
                raise RuntimeError(f"Collector still observed a targeted sink report for {flow_id}")
        flow_join = {}
        for flow_id in sorted(expected_flow_ids):
            service_ids = captured_by_flow.get(flow_id, set())
            collector_sink_ids = collector_sink_by_flow.get(flow_id, set())
            dropped_sink_ids = relay_dropped_sink_by_flow.get(flow_id, set())
            flow_join[flow_id] = {
                "service_packet_observations": sum(
                    packet["flow_id"] == flow_id for packet in matched_capture_rows
                ),
                "service_interface_packets": len(service_ids),
                "service_udp_socket_receipts": sink_receipts_by_flow.get(flow_id, 0),
                "collector_sink_report_packets": len(collector_sink_ids),
                "collector_sink_packet_id_overlap": len(service_ids & collector_sink_ids),
                "relay_dropped_sink_report_packets": len(dropped_sink_ids),
                "service_to_relay_drop_packet_id_overlap": len(service_ids & dropped_sink_ids),
                "service_only_vs_relay_drop_packet_ids": sorted(service_ids - dropped_sink_ids),
                "relay_drop_only_packet_ids": sorted(dropped_sink_ids - service_ids),
            }
        result["service_collector_packet_join"] = {
            "flows": flow_join,
            "interpretation": (
                "IPv4 identification is compared within the exporter flow key. "
                "The service-side packet IDs exactly match relay-dropped leaf sink "
                "report IDs; no corresponding sink report reaches the collector, while "
                "upstream reports remain visible. The matched leaf-loss arm is recorded "
                "separately after fault injection; no Agent result is included."
            ),
        }

        result["phase"] = "install_leaf_loss"
        for item, item_port in service_ports:
            overrides = {
                "host_name": switch,
                "intf_name": item_port.name,
                "bmv2_port": str(item_port.bmv2_port),
                "loss_basis_points": "10000",
                "seed": "42",
            }
            inject_failure(
                [problem_name],
                session_id=session_id,
                param_overrides=overrides,
            )
            parsed = problem.parse_params(overrides)
            verification = problem.verify_fault(parsed)
            check = {
                "service": item.name,
                "interface": item_port.name,
                "bmv2_port": item_port.bmv2_port,
                "verified": bool(verification.get("verified")),
                "observed_threshold": (verification.get("details") or {}).get(
                    "observed_threshold"
                ),
            }
            result["fault_table_checks"].append(check)
            if not check["verified"]:
                raise RuntimeError(
                    f"Installed P4 loss table entry did not verify for {item.name}"
                )
        result["fault_table_verified"] = all(
            check["verified"] for check in result["fault_table_checks"]
        )
        snapshot_leaf_counters("after_loss_injection_before_probe")

        result["phase"] = "post_injection_service_probe"
        send_service_tcp_probe()
        result["post_injection_direct_service_tcp_probe_count"] = 1
        snapshot_leaf_counters("after_post_injection_direct_service_tcp")
        record_packet_counter_delta(
            "loss_probe_direct",
            "after_loss_injection_before_probe",
            "after_post_injection_direct_service_tcp",
        )
        vip_after = [http_ok(runtime, "client_1", vip_url) for _ in range(3)]
        result["post_injection_vip_http_ok"] = vip_after
        snapshot_leaf_counters("after_post_injection_vip_http")
        record_packet_counter_delta(
            "loss_probe_vip",
            "after_post_injection_direct_service_tcp",
            "after_post_injection_vip_http",
        )
        result["service_egress_counter_packet_deltas"]["loss_probe_direct"] = {
            item.name: (
                result["leaf_counter_snapshots"]["after_post_injection_direct_service_tcp"]
                .get("egress", {})
                .get(str(item_port.bmv2_port), {})
                .get("packets", 0)
                - result["leaf_counter_snapshots"]["after_loss_injection_before_probe"]
                .get("egress", {})
                .get(str(item_port.bmv2_port), {})
                .get("packets", 0)
            )
            for item, item_port in service_ports
        }
        result["service_egress_counter_packet_deltas"]["loss_probe_vip"] = {
            item.name: (
                result["leaf_counter_snapshots"]["after_post_injection_vip_http"]
                .get("egress", {})
                .get(str(item_port.bmv2_port), {})
                .get("packets", 0)
                - result["leaf_counter_snapshots"]["after_post_injection_direct_service_tcp"]
                .get("egress", {})
                .get(str(item_port.bmv2_port), {})
                .get("packets", 0)
            )
            for item, item_port in service_ports
        }
        target_post_injection_egress = result[
            "service_egress_counter_packet_deltas"
        ]["loss_probe_direct"][service.name]
        result["post_injection_direct_service_tcp_target_egress_packets"] = (
            target_post_injection_egress
        )
        if target_post_injection_egress > 0:
            raise RuntimeError(
                "Direct TCP probe still reached the target service egress after "
                "near-total leaf loss injection"
            )
        if any(vip_after):
            raise RuntimeError(
                "VIP service still answered after near-total leaf egress loss injection"
            )

        # Reuse the exact same fixed-seed flows for the data-plane-loss arm. The
        # evaluator-side receiver and packet capture remain private ground truth.
        result["phase"] = "matched_leaf_loss_telemetry_burst"
        result["matched_flow_ids"] = sorted(expected_flow_ids)
        pass_plan_path = f"/var/lib/nika/faultda-pass-plan-{capture_key}.jsonl"
        pass_events_path = f"/var/lib/nika/faultda-pass-events-{capture_key}.jsonl"
        pass_plan_bytes = b""
        runtime.exec(
            "collector",
            "python3 -c " + shlex.quote(
                "from pathlib import Path; Path('/var/lib/nika/int_reports.jsonl').write_text(''); "
                f"Path({pass_plan_path!r}).write_bytes(b'')"
            ),
            timeout=10,
        )
        pass_relay_id = f"nika-leaf-loss-pass-{capture_key}"
        pass_relay_command = (
            f"python3 {shlex.quote(relay_remote_path)} "
            f"--listen-port 32766 --collector 127.0.0.1 --collector-port 32767 "
            f"--drop-plan {shlex.quote(pass_plan_path)} "
            f"--events {shlex.quote(pass_events_path)} "
            f"--run-id {shlex.quote(pass_relay_id)} --duration-seconds 16 "
            f">/tmp/faultda-relay-pass-{capture_key}.log 2>&1 & relay_pid=$!; i=0; "
            f"while ! grep -q '\"event\":\"run_started\"' {shlex.quote(pass_events_path)} "
            "2>/dev/null && [ \"$i\" -lt 40 ]; do sleep 0.1; i=$((i+1)); done; "
            f"if ! grep -q '\"event\":\"run_started\"' {shlex.quote(pass_events_path)} "
            f"2>/dev/null; then cat /tmp/faultda-relay-pass-{capture_key}.log; exit 1; fi; "
            "printf 'RELAY_READY:%s\\n' \"$relay_pid\""
        )
        pass_relay_setup = runtime.exec(
            "collector", pass_relay_command, timeout=10
        ).strip()
        if not pass_relay_setup.startswith("RELAY_READY:"):
            raise RuntimeError(f"Pass-through report relay did not become ready: {pass_relay_setup}")

        loss_sink_path = f"/tmp/faultda-loss-sink-{capture_key}.jsonl"
        loss_sink_ready = f"/tmp/faultda-loss-sink-{capture_key}.ready"
        loss_sink_done = f"/tmp/faultda-loss-sink-{capture_key}.done"
        loss_sink_command = (
            f"python3 -c {shlex.quote(sink_capture_code)} "
            f"{shlex.quote(sink_ports_json)} {shlex.quote(service.ip)} 12 "
            f"{shlex.quote(loss_sink_path)} {shlex.quote(loss_sink_ready)} "
            f"{shlex.quote(loss_sink_done)} >/tmp/faultda-loss-sink-{capture_key}.log 2>&1 & sink_pid=$!; i=0; "
            f"while [ ! -f {shlex.quote(loss_sink_ready)} ] && [ \"$i\" -lt 40 ]; "
            "do sleep 0.1; i=$((i+1)); done; "
            f"if [ ! -f {shlex.quote(loss_sink_ready)} ]; then cat /tmp/faultda-loss-sink-{capture_key}.log; exit 1; fi; "
            "printf '%s\\n' \"$sink_pid\""
        )
        loss_sink_pid = runtime.exec(
            service.name, loss_sink_command, timeout=10
        ).strip()
        if not loss_sink_pid.isdigit():
            raise RuntimeError("Loss-arm evaluator UDP receiver did not bind")
        loss_capture_path = f"/tmp/faultda-loss-packets-{capture_key}.jsonl"
        loss_capture_ready = f"/tmp/faultda-loss-packets-{capture_key}.ready"
        loss_capture_done = f"/tmp/faultda-loss-packets-{capture_key}.done"
        loss_capture_command = (
            f"python3 -c {shlex.quote(capture_code)} {shlex.quote(sink_ports_json)} "
            f"12 {shlex.quote(loss_capture_path)} {shlex.quote(loss_capture_ready)} "
            f"{shlex.quote(loss_capture_done)} >/tmp/faultda-loss-packets-{capture_key}.log 2>&1 & capture_pid=$!; i=0; "
            f"while [ ! -f {shlex.quote(loss_capture_ready)} ] && [ \"$i\" -lt 40 ]; "
            "do sleep 0.1; i=$((i+1)); done; "
            f"if [ ! -f {shlex.quote(loss_capture_ready)} ]; then cat /tmp/faultda-loss-packets-{capture_key}.log; exit 1; fi; "
            "printf '%s\\n' \"$capture_pid\""
        )
        loss_capture_pid = runtime.exec(
            service.name, loss_capture_command, timeout=10
        ).strip()
        if not loss_capture_pid.isdigit():
            raise RuntimeError("Loss-arm AF_PACKET capture did not start")
        loss_source_captures = start_source_packet_captures(
            "leaf_loss", flow_filters_by_source
        )
        snapshot_leaf_counters("before_matched_leaf_loss_burst")
        loss_burst = BurstTrafficGenerator(runtime).run(
            sources=client_names,
            destination=service.name,
            protocol="udp",
            rate="32K",
            packet_size=128,
            duration=3,
            synchronized_start=time.time() + 2.0,
            seed=20261107,
            flows_per_source=2,
            raw_udp=True,
        )
        if {flow["flow_id"] for flow in loss_burst["flows"]} != expected_flow_ids:
            raise RuntimeError("Matched loss-arm flow IDs differ from report-only arm")
        result["matched_leaf_loss_burst_profile"] = loss_burst
        report_profile = result["background_burst_profile"]
        profile_fields = (
            "protocol",
            "rate",
            "packet_size",
            "duration",
            "seed",
            "flows_per_source",
            "destination",
        )
        if any(loss_burst.get(field) != report_profile.get(field) for field in profile_fields):
            raise RuntimeError("Paired arms do not share the same traffic profile")
        flow_fields = (
            "flow_id",
            "source",
            "destination",
            "protocol",
            "source_port",
            "destination_port",
            "source_ip",
        )
        report_flow_signature = sorted(
            tuple(flow.get(field) for field in flow_fields)
            for flow in report_profile["flows"]
        )
        loss_flow_signature = sorted(
            tuple(flow.get(field) for field in flow_fields)
            for flow in loss_burst["flows"]
        )
        if loss_flow_signature != report_flow_signature:
            raise RuntimeError("Paired arms do not share the same flow tuples")
        time.sleep(6)
        loss_sink_output = runtime.exec(
            service.name,
            "i=0; "
            f"while [ ! -f {shlex.quote(loss_sink_done)} ] && [ \"$i\" -lt 160 ]; "
            "do sleep 0.1; i=$((i+1)); done; "
            f"if [ ! -f {shlex.quote(loss_sink_done)} ]; then printf 'FAULTDA_SINK_TIMEOUT\\n'; exit 124; fi; "
            f"cat {shlex.quote(loss_sink_path)}",
            timeout=25,
        )
        loss_capture_output = runtime.exec(
            service.name,
            "i=0; "
            f"while [ ! -f {shlex.quote(loss_capture_done)} ] && [ \"$i\" -lt 160 ]; "
            "do sleep 0.1; i=$((i+1)); done; "
            f"if [ ! -f {shlex.quote(loss_capture_done)} ]; then kill {loss_capture_pid} 2>/dev/null; printf 'FAULTDA_CAPTURE_TIMEOUT\\n'; exit 124; fi; "
            f"cat {shlex.quote(loss_capture_path)}",
            timeout=25,
        )
        if "FAULTDA_SINK_TIMEOUT" in loss_sink_output or "FAULTDA_CAPTURE_TIMEOUT" in loss_capture_output:
            raise RuntimeError("Loss-arm evaluator observation timed out")
        loss_socket_rows = [
            json.loads(line) for line in loss_sink_output.splitlines() if line.strip()
        ]
        loss_capture_rows = [
            json.loads(line) for line in loss_capture_output.splitlines() if line.strip()
        ]
        loss_source_ids_by_flow = finish_source_packet_captures(
            "leaf_loss", loss_source_captures
        )
        for flow_id in sorted(expected_flow_ids):
            if not loss_source_ids_by_flow.get(flow_id):
                raise RuntimeError(f"Source ledger captured no packets for {flow_id}")
        loss_capture_by_flow: dict[str, set[str]] = {}
        for packet in loss_capture_rows:
            if packet["flow_id"] in expected_flow_ids:
                loss_capture_by_flow.setdefault(packet["flow_id"], set()).add(
                    str(packet["packet_id"])
                )
        result["matched_leaf_loss_service_observations"] = {
            "af_packet_packets": sum(len(ids) for ids in loss_capture_by_flow.values()),
            "af_packet_packet_ids_by_flow": {
                flow_id: sorted(loss_capture_by_flow.get(flow_id, set()))
                for flow_id in sorted(expected_flow_ids)
            },
            "udp_socket_receipts": len(loss_socket_rows),
            "scope": "evaluator-only service-side ground truth under verified leaf loss entries",
        }
        if loss_socket_rows or any(loss_capture_by_flow.values()):
            raise RuntimeError("Target UDP packets reached the service in the 100% leaf-loss arm")
        snapshot_leaf_counters("after_matched_leaf_loss_burst")
        record_packet_counter_delta(
            "matched_leaf_loss_burst",
            "before_matched_leaf_loss_burst",
            "after_matched_leaf_loss_burst",
        )
        for snapshot_name in (
            "before_matched_leaf_loss_burst",
            "after_matched_leaf_loss_burst",
        ):
            target_counter = (
                result["leaf_counter_snapshots"][snapshot_name]
                .get("egress", {})
                .get(str(port.bmv2_port))
            )
            if target_counter is None or "packets" not in target_counter:
                raise RuntimeError(
                    f"Target service egress counter is missing in {snapshot_name}"
                )
        loss_report_summary_code = (
            "import json\n"
            f"flow_ids = set(json.loads({json.dumps(sorted(expected_flow_ids))!r}))\n"
            "summary = {flow: {'rows': 0, 'packet_ids': set(), 'sink_packet_ids': set(), 'sink_seen': False} for flow in flow_ids}\n"
            "with open('/var/lib/nika/int_reports.jsonl', encoding='utf-8') as reports:\n"
            "    for line in reports:\n"
            "        row = json.loads(line); flow_id = row.get('flow_id')\n"
            "        if flow_id in summary:\n"
            "            item = summary[flow_id]; item['rows'] += 1; item['packet_ids'].add(str(row.get('packet_id')))\n"
            "            item['sink_seen'] = item['sink_seen'] or bool(row.get('sink_seen'))\n"
            "            if row.get('sink_seen'): item['sink_packet_ids'].add(str(row.get('packet_id')))\n"
            "print(json.dumps({'flows': {flow: {'rows': item['rows'], 'packet_ids': sorted(item['packet_ids']), 'sink_packet_ids': sorted(item['sink_packet_ids']), 'sink_seen': item['sink_seen']} for flow,item in summary.items()}, 'total_rows': sum(item['rows'] for item in summary.values())}, sort_keys=True))\n"
        )
        result["matched_leaf_loss_collector_reports"] = json.loads(
            runtime.exec(
                "collector",
                f"python3 -c {shlex.quote(loss_report_summary_code)}",
                timeout=30,
            )
        )
        for flow_id, summary in result["matched_leaf_loss_collector_reports"]["flows"].items():
            if summary["rows"] == 0 or summary["sink_packet_ids"]:
                raise RuntimeError(
                    f"Leaf-loss arm lacks upstream-only collector evidence for {flow_id}"
                )
            if loss_source_ids_by_flow.get(flow_id, set()) != set(
                summary["packet_ids"]
            ):
                raise RuntimeError(
                    f"Source-egress and collector packet IDs differ for {flow_id}"
                )
        loss_egress_delta = result["leaf_counter_packet_deltas"][
            "matched_leaf_loss_burst"
        ]["egress"].get(str(port.bmv2_port), 0)
        loss_ingress_delta = sum(
            result["leaf_counter_packet_deltas"]["matched_leaf_loss_burst"][
                "ingress"
            ].values()
        )
        if loss_ingress_delta <= 0:
            raise RuntimeError("No target traffic entered the leaf during the loss arm")
        if loss_egress_delta != 0:
            raise RuntimeError(
                "Leaf-loss arm recorded packets on the target service egress counter"
            )
        result["matched_leaf_loss_counter_check"] = {
            "leaf_ingress_packets": loss_ingress_delta,
            "target_service_egress_packets": loss_egress_delta,
            "passed": True,
        }
        leaf_loss_collector_output = runtime.exec(
            "collector", "cat /var/lib/nika/int_reports.jsonl", timeout=30
        )
        leaf_loss_rows = [
            line
            for line in leaf_loss_collector_output.splitlines()
            if line.strip() and json.loads(line).get("flow_id") in expected_flow_ids
        ]
        if not leaf_loss_rows:
            raise RuntimeError("No raw leaf-loss collector rows were retained")
        leaf_loss_collector_path = output_path.with_name(
            "NIKA_COLLECTOR_LEAF_LOSS_ROWS.jsonl"
        )
        leaf_loss_collector_path.write_text(
            "\n".join(leaf_loss_rows) + "\n", encoding="utf-8", newline="\n"
        )
        leaf_loss_collector_bytes = leaf_loss_collector_path.read_bytes()
        result["collector_raw_artifacts"]["leaf_loss"] = {
            "file": leaf_loss_collector_path.name,
            "rows": len(leaf_loss_rows),
            "sha256": hashlib.sha256(leaf_loss_collector_bytes).hexdigest(),
            "filter": "target flow IDs only; original collector JSONL row order preserved",
        }
        pass_relay_output = runtime.exec(
            "collector",
            "i=0; "
            f"while ! grep -q '\"event\":\"run_finished\"' {shlex.quote(pass_events_path)} "
            "2>/dev/null && [ \"$i\" -lt 90 ]; do sleep 0.1; i=$((i+1)); done; "
            f"cat {shlex.quote(pass_events_path)}",
            timeout=15,
        )
        pass_events = [
            json.loads(line) for line in pass_relay_output.splitlines() if line.strip()
        ]
        pass_finished = next(
            (event for event in reversed(pass_events) if event.get("event") == "run_finished"),
            None,
        )
        pass_log_path = output_path.with_name(
            "NIKA_LEAF_SERVICE_LOSS_RELAY_EVENTS_LOSS_ARM.jsonl"
        )
        pass_log_path.write_text(pass_relay_output, encoding="utf-8", newline="\n")
        if pass_finished is None:
            raise RuntimeError("Pass-through relay did not finish its bounded run")
        result["matched_leaf_loss_relay_summary"] = {
            "run_id": pass_relay_id,
            "events_artifact": pass_log_path.name,
            "run_started": any(event.get("event") == "run_started" for event in pass_events),
            "report_received_count": sum(event.get("event") == "report_received" for event in pass_events),
            "report_forwarded_count": sum(event.get("event") == "report_forwarded" for event in pass_events),
            "report_dropped_count": sum(event.get("event") == "report_dropped" for event in pass_events),
            "run_finished": True,
            "drop_plan_sha256": hashlib.sha256(pass_plan_bytes).hexdigest(),
            "stop_reason": pass_finished.get("stop_reason"),
        }
        pass_received = result["matched_leaf_loss_relay_summary"]["report_received_count"]
        if (
            not result["matched_leaf_loss_relay_summary"]["run_started"]
            or pass_received == 0
            or result["matched_leaf_loss_relay_summary"]["report_forwarded_count"]
            != pass_received
            or result["matched_leaf_loss_relay_summary"]["report_dropped_count"] != 0
        ):
            raise RuntimeError("Leaf-loss arm report relay did not pass through all observed reports")
        result["paired_packet_observation_summary"] = {
            "report_only_service_packets_by_flow": {
                flow_id: result["service_collector_packet_join"]["flows"][flow_id]["service_interface_packets"]
                for flow_id in sorted(expected_flow_ids)
            },
            "leaf_loss_service_packets_by_flow": {
                flow_id: len(loss_capture_by_flow.get(flow_id, set()))
                for flow_id in sorted(expected_flow_ids)
            },
            "report_only_collector_sink_packets_by_flow": {
                flow_id: result["service_collector_packet_join"]["flows"][flow_id]["collector_sink_report_packets"]
                for flow_id in sorted(expected_flow_ids)
            },
            "leaf_loss_collector_sink_packets_by_flow": {
                flow_id: len(
                    result["matched_leaf_loss_collector_reports"]["flows"][flow_id]["sink_packet_ids"]
                )
                for flow_id in sorted(expected_flow_ids)
            },
            "interpretation_limit": "One paired small-topology mechanism check; not an independent replication, Agent comparison, or paper contribution.",
        }
        result["paired_runtime_observations_complete"] = True
        result["phase"] = "complete"
    finally:
        exception = sys.exc_info()[1]
        if exception is not None:
            result["error_type"] = type(exception).__name__
            result["error"] = str(exception)
        result["pre_cleanup_recorded_utc"] = datetime.now(timezone.utc).isoformat()
        if session_id is not None:
            session_status = (
                "finished" if result["phase"] == "complete" else "error"
            )
            result["nika_session_status"] = session_status
            result["lab_closed"] = False
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if session_id is not None:
            close_session(session_id=session_id, status=session_status)
            result["lab_closed"] = True
            result["passed"] = result["phase"] == "complete" and bool(
                result.get("paired_runtime_observations_complete")
            )
        result["finished_utc"] = datetime.now(timezone.utc).isoformat()
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
