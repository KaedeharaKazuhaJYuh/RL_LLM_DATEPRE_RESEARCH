# NIKA Runtime Preflight — 2026-11-07, Run 2

**Status: baseline and report-only relay worked; packet-ID binding at the service interface failed. No data-plane loss arm or Agent ran. Research gate remains HOLD.**

## Setup and baseline

The run used pinned NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` with `p4_dc_gateway`, topology size `s`, and target `leaf_1` / `service_1_1`. The direct TCP observation probes produced `2` packets on the target service egress port; VIP HTTP checks were `True, True`. The corrected runner had `iproute2` and teardown completed (`lab_closed=True`).

## Report-only arm evidence

- The fixed-seed UDP burst had four flows. The evaluator-owned service UDP sockets received `376` datagrams: `{"f6e760d978c438b2":94,"28a4463f718872b0":94,"fde41913c03f2870":94,"5560a874d0f2acfe":94}`.
- The collector relay recorded `1128` report datagrams, forwarded `752`, and intentionally dropped `376` leaf sink reports. Each pre-registered flow/sink target matched 94 reports.
- Collector summaries retained upstream reports but no targeted sink report. Per-flow summaries:
- `28a4463f718872b0`: 188 collector rows, 94 packet IDs, sink row missing after relay filtering.
- `5560a874d0f2acfe`: 188 collector rows, 94 packet IDs, sink row missing after relay filtering.
- `f6e760d978c438b2`: 188 collector rows, 94 packet IDs, sink row missing after relay filtering.
- `fde41913c03f2870`: 188 collector rows, 94 packet IDs, sink row missing after relay filtering.
- Leaf egress counter delta on the service port during the burst was `376` packets, matching the 4 × 94 service-socket receipt count at aggregate level. This is not a packet-ID join.
- The AF_PACKET collector bound only to `eth0` produced zero matching rows. Since application sockets received the datagrams, this capture result is not evidence that the service received no traffic. It leaves the packet IDs at the service-interface boundary unbound.

The complete machine record and relay event ledger are [NIKA_LEAF_SERVICE_LOSS_PREFLIGHT_2026_11_07_RUN2.json](NIKA_LEAF_SERVICE_LOSS_PREFLIGHT_2026_11_07_RUN2.json) and [NIKA_LEAF_SERVICE_LOSS_RELAY_EVENTS_2026_11_07_RUN2.jsonl](NIKA_LEAF_SERVICE_LOSS_RELAY_EVENTS_2026_11_07_RUN2.jsonl).

## Decision

The report-only relay and application-level business traffic are now exercised together at runtime, but the evidence is still insufficient for a per-packet causal ledger. The next diagnostic captures the service's UDP target ports from all AF_PACKET interfaces and records raw destination tuples before flow-key filtering. Only after a stable packet-ID join exists should the matched leaf-egress-loss arm be built. This remains engineering feasibility evidence, not Agent performance or an independent paper contribution.
