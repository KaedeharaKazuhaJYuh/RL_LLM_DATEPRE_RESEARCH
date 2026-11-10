# Communication telemetry report-loss relay

This isolated experiment utility receives NIKA hop-exporter UDP reports, records their arrival at the relay, and either forwards them to the collector or drops report keys selected by a frozen JSONL plan. A key is `(flow_id, packet_id, switch_id)`, so the same packet can be retained at one hop and dropped at another. A plan may use `"*"` only for `packet_id` to drop every report from one preregistered flow at one switch; this is intended for sink-report loss when packet IDs cannot be known in advance.

It models **post-exporter, pre-collector report loss**. It does not modify NIKA's P4 forwarding path or replace the native NIKA scorer. The relay event log is evaluator-only evidence and must never be exposed to the Agent.

## Input files

The drop plan has one JSON object per line:

```json
{"flow_id":"flow-17","packet_id":"packet-0042","switch_id":3}
```

Flow-scoped sink-report loss:

```json
{"flow_id":"flow-17","packet_id":"*","switch_id":3}
```

Exact and wildcard targets for the same `(flow_id, switch_id)` are rejected as overlapping. The event log records the actual packet ID for every received and dropped report, and the run summary counts matches against the planned target.

The relay writes separate `report_received` and `report_forwarded`/`report_dropped` events, then a `run_finished` summary. It records the drop-plan SHA-256, its own source SHA-256, report key, source endpoint, payload SHA-256, receive/action timestamps, and matched-target counts. `sendto_accepted_bytes` only means the local UDP socket accepted the datagram; collector JSONL is the independent receipt evidence. The relay does not store raw telemetry payloads. Each run requires a new event-log path; existing logs are not overwritten. Matching keys are dropped every time they arrive, and the final summary reports targets that were never observed.

## NIKA wiring

Run the relay on the collector node at the address already passed to each `hop_exporter.py`, listening on UDP/32766. Start NIKA's `collector.py` on UDP/32767. Configure the relay to forward accepted datagrams to `127.0.0.1:32767`. This keeps exporters pointed at the relay while preserving the collector's report parser and JSONL output.

At pinned NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81`, this wiring is **not a runtime setting**: `lab.py` starts exporters with the fixed collector IP, and starts the collector on its default UDP/32766. The hosted preflight applies a process-level overlay without editing the NIKA checkout: it stops that collector, restarts the same `collector.py` on UDP/32767, copies the relay and frozen drop plan into the collector node, and starts the relay on UDP/32766. Starting the relay without moving the collector creates a bind conflict. Each preflight result records the pinned NIKA/Kathara versions, relay hash and drop-plan hash; it does not create a source diff because the overlay changes only processes and temporary files in the runner's lab.

NIKA derives `packet_id` from the IPv4 identification field, while its `flow_id` is stable for a fixed source/destination/protocol/port tuple. The flow-scoped wildcard supports that case without matching other flows or switches. It is a control-plane convenience, not proof of a live pair: a runtime run must verify the expected reports arrived, the intended sink reports matched, and the collector retained the non-target reports.

For the preflight's report-only arm, evaluator-owned UDP sockets bind the planned service ports before `BurstTrafficGenerator` starts. This replaces its stock UDP sink with a non-responding receiver that records each received datagram; the stock sink's bind attempts then fail on those occupied ports, but the sender still runs. The preflight labels these PID values as bind attempts, not live sink processes. It also records service `eth0` AF_PACKET observations to map IPv4 identification to the flow key. Both records are evaluator-only, and this first arm alone does not establish a matched data-plane-loss comparison.

Example command on the collector node:

```text
python3 telemetry_report_relay.py --listen 0.0.0.0 --listen-port 32766 --collector 127.0.0.1 --collector-port 32767 --drop-plan /var/lib/nika/drop-plan.jsonl --events /var/lib/nika/relay-events.jsonl --run-id dev-001
```

For a bounded run, add `--max-reports N` to stop after N datagrams, or `--duration-seconds T` to close after a fixed observation window and write `run_finished`. Without either option it runs until interrupted. If both are set, whichever limit is reached first closes the run. The current preflight uses a fixed-duration relay and retains the raw event log as a separate workflow artifact.

The relay passed two local UDP loopback checks: the original exact-key case dropped one selected report, and the flow-scoped case dropped two changing packet IDs only for the selected `(flow_id, switch_id)` while forwarding a different flow and the same flow at another switch. The latest replayable record and runner are [flow-scope result](artifacts/relay_flow_scope_smoke_retry1/result.json) and [smoke script](relay_flow_scope_smoke.py); the earlier exact-match record is [RELAY_LOOPBACK_SMOKE_2026_11_07.json](RELAY_LOOPBACK_SMOKE_2026_11_07.json). These checks do not validate a live NIKA collector, network namespace, permissions, or forwarding behavior in Kathara. Before any NIKA experiment, verify that the relay binds in the collector namespace, the collector listens on 32767, and every planned key appears; compare relay records with collector JSONL and preserve the untouched NIKA release/score. Freeze the drop plan, tool allowlist, node allowlist, probe budget, task seed, and model configuration before any Agent run.

No Docker/WSL startup, model call, or API call was part of the local check.

The related paper-level limitation audit is [LOSSSIGHT_MCM_SOURCE_REPLAY_2026_11_07.md](LOSSSIGHT_MCM_SOURCE_REPLAY_2026_11_07.md). It is a conditional hand replay, not a runtime reproduction; it records a logical-operator ambiguity in the published MCM pseudocode and explains why the remaining research question is terminal-report attribution under matched, Agent-visible evidence.

## Paired runtime result (2026-11-07)

The fourth pinned NIKA run completed one matched fixed-flow workload under (a) sink-report-only relay drops and (b) verified leaf-to-service packet loss. Per flow, the first arm delivered 94 UDP packets to the service and dropped the matching 94 sink reports; the second delivered none. Collector output retained 188 upstream rows per flow and no sink rows in both arms. Public target-port egress counters separated them (376 vs 0), so the observed clean low-background pair is directly separable by a same-information deterministic rule; this is not yet a frozen baseline evaluation on independent clusters. This is a negative result for an Agent-advantage claim, not a paper contribution or generalization result. See [analysis](NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.md), [raw run](NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.json), and relay ledgers.

## Hop-order audit (2026-11-07)

Replaying the report-only relay ledger found 10 of 376 packets whose relay receive order had at least one gateway/spine/leaf role inversion; one of 376 forwarded upstream report pairs had the spine report before the gateway report. A local UDP reproduction with the pinned NIKA collector source confirmed that its `hop_sequence` preserves supplied datagram arrival order and does not reorder by topology. The archived full NIKA run did not retain the collector JSONL, so an Agent-facing effect is unverified. R1 must normalize path order using topology and per-hop timestamps. The runtime preflight runner now saves target-flow collector rows, in their original order, for each arm and records their SHA-256. This is a data-pipeline constraint, not a paper result. See [relay-order audit](NIKA_RELAY_HOP_ORDER_AUDIT_2026_11_07.md), [reproduction result](NIKA_COLLECTOR_ORDER_SEMANTICS_2026_11_07.json), and [reproduction runner](reproduce_collector_arrival_order.py).
