# NIKA Runtime Preflight — 2026-11-07, Run 3

**Status: the report-only arm now has an exact service-packet-ID to dropped-sink-report join. The matched data-plane-loss UDP arm, strong-rule comparison, and Agent evaluation remain unrun. Candidate remains HOLD.**

## Runtime outcome

The run used pinned NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` in `p4_dc_gateway`, small topology, targeting `leaf_1` and `service_1_1`. The preflight completed (`phase=complete`, `passed=true`, `lab_closed=true`). This `passed` field applies only to the bounded preflight procedure.

- Before injection, the direct TCP observation probe produced two target-service egress packets and VIP HTTP passed twice.
- In the report-only arm, four fixed-seed UDP flows each sent 94 packets. Evaluator UDP sockets received 94 datagrams per flow; all-interface AF_PACKET recorded the same 94 IPv4 IDs per flow.
- The relay received 1,128 telemetry reports, forwarded 752 upstream reports, and intentionally dropped 376 leaf sink reports (94 per flow). The collector retained 188 upstream rows per flow and no dropped sink rows.
- A post-run set comparison joined the service-side IPv4 IDs against the relay `report_dropped` event keys, restricted to the target leaf switch. All four flows matched exactly: 376/376 IDs overlap, with zero service-only or relay-drop-only IDs. The join audit records hashes for both source artifacts.
- The subsequent leaf/service loss table entries were verified on both service-facing ports. Under this loss injection the direct TCP observation produced zero target-port egress packets and VIP HTTP failed three times. No matched UDP burst was sent under the data-plane loss condition.
- Teardown completed, and no Kathara lab containers remained after the run.

## What this establishes

This is runtime evidence that, in one small NIKA topology and one controlled workload, application packets reached the service while the matching leaf sink reports were dropped before reaching the collector. It validates the report-only arm and the exact packet-ID join. It does **not** establish a paired packet-loss-versus-report-loss experiment: the loss condition only used a TCP probe and VIP HTTP checks. It also contains no Agent, strong-rule comparison, held-out task cluster, or cross-topology result.

## Artifacts

- [Preflight result JSON](NIKA_LEAF_SERVICE_LOSS_PREFLIGHT_2026_11_07_RUN3.json)
- [Raw relay event JSONL](NIKA_LEAF_SERVICE_LOSS_RELAY_EVENTS_2026_11_07_RUN3.jsonl)
- [Deterministic packet-ID join audit with source hashes](NIKA_REPORT_ONLY_PACKET_ID_JOIN_2026_11_07_RUN3.json)

## Next discriminating step

Send the same four-flow workload under the verified leaf-service loss entries while the relay forwards all reports without dropping. Capture the same endpoint socket receipts, AF_PACKET IDs, per-port counters, and collector rows. This determines whether the two arms yield distinct Agent-visible evidence and whether report presence survives a packet dropped after the leaf observes it. Only then freeze a same-information rule baseline. No model call is warranted yet.
