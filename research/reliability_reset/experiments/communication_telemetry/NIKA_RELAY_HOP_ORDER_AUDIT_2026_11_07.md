# NIKA relay hop-order audit — 2026-11-07

## Question

Does the saved low-rate report-only run preserve physical hop order in the UDP relay's receive/forward sequence, and could this affect the path evidence used by the planned R1 baseline?

## Reproducible result

Input: `NIKA_PAIRED_REPORT_ONLY_RELAY_EVENTS_2026_11_07.jsonl`, SHA-256 `126f9a4a9a52f156b53904387ac5ce62439d95835c8fb4140ec32093361e5643`. The analysis is reproduced with:

```powershell
py -3 research/reliability_reset/experiments/communication_telemetry/audit_relay_hop_order.py
```

The pinned NIKA topology encodes switch IDs with role bases: gateway IDs below 100, spine IDs from 100 to 199, and leaf IDs from 200 upward. For the 376 packets with three reports received by the relay, physical role order is gateway → spine → leaf.

- Relay received 1,128 reports: 376 gateway, 376 spine, and 376 leaf reports.
- Across all 752 adjacent role transitions, 10 were reversed; 10 of 376 packet groups (2.66%) had at least one role-order inversion. This is a count from one run, not an estimated population rate.
- The relay intentionally dropped the leaf reports. Among the 376 packets with both upstream reports forwarded, one had the spine report forwarded before its gateway report: packet `(flow_id=f6e760d978c438b2, packet_id=63915)`, switch IDs `[101, 2]`.

The replay input was a single small topology and four fixed low-rate UDP flows, without added background traffic. The finding establishes a relay-order observation in that run; it does not establish a model error or a stable rate under other loads.

## Source interpretation and limits

In the pinned NIKA source, `hop_exporter.py` emits each report independently over UDP; `collector.py` appends each received report to `traces[key]` and serializes that list as `hop_sequence`. `int_query_telemetry()` reads collector JSONL rows and preserves file order after filtering; it does not sort hop records. This makes it possible for receive order to appear as `hop_sequence` order. However, raw collector rows for this run were not retained, so the exact collector sequence and any Agent-facing effect are not directly confirmed.

The reports contain per-hop ingress/egress timestamps, but there is no collector receive timestamp in the record. Therefore this audit cannot measure report-arrival latency or distinguish event-time ordering from collector-ingest ordering in the archived run.

## Controlled collector reproduction

The pinned NIKA `collector.py` was launched locally on loopback, and three UDP reports for one packet were sent in switch-ID order `[101, 2, 201]` (spine, gateway, leaf), while the topology role order is `[2, 101, 201]`. The final collector row retained `[101, 2, 201]` in `hop_sequence`. Collector source SHA-256: `7e2adc718a0153ebf17a81ad58c95c66b434725749568f6e675713726986b992`. This verifies the component's append-on-arrival behavior under a controlled datagram sequence. It still does not establish that the archived full NIKA run's collector received the anomalous pair in that exact order, because its raw collector file was not retained. Reproduce with `reproduce_collector_arrival_order.py`; output is `NIKA_COLLECTOR_ORDER_SEMANTICS_2026_11_07.json`.

## Consequence for the current study

The candidate remains **HOLD**. The result does not create a new contribution and does not justify running an Agent. It does require R1 to reconstruct path order from the pinned topology and per-hop timestamps instead of treating collector append order as physical path order. Agent and rule arms must receive the same normalized evidence. A future end-to-end run should preserve raw collector rows and compare relay receive order, collector append order, and event-time order before interpreting any RCA difference.

Machine output: `NIKA_RELAY_HOP_ORDER_AUDIT_2026_11_07.json`; analyzer: `audit_relay_hop_order.py`.
