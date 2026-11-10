# NIKA collector-order paired rerun — 2026-11-07

## Purpose

This is a bounded systems check for the fixed research direction: AI diagnosis over communication-network telemetry. It verifies whether the collector's accumulated `hop_sequence` follows network path order under a controlled paired run. It does not measure an Agent or establish a paper contribution.

## Run integrity

- Pinned NIKA commit: `ac4422d8a4a03be2b905e28edf72993d467e1b81`.
- Kathara: `3.8.3`; runner Python: `3.12.16`.
- Retry result: `phase=complete`, `passed=true`, `lab_closed=true`, runtime observations complete.
- Each collector JSONL contains 752 rows and 376 unique `(flow_id, packet_id)` keys. Raw files and SHA-256 values are recorded in [`NIKA_COLLECTOR_ORDER_AUDIT.json`](artifacts/nika_pair_collector_rerun_20261107_retry1/NIKA_COLLECTOR_ORDER_AUDIT.json).
- The earlier cleanup-failed attempt remains a failed attempt and is not pooled with this run.

## Observations

- Report-only arm: all 376 service-side UDP packets reached the service; the 376 matching sink reports were deliberately dropped at the relay. The collector retained upstream reports. Across the final per-packet collector records, 0/376 had a gateway/spine/leaf role inversion.
- Leaf-loss arm: the injected leaf service-port loss prevented all 376 probe packets from reaching the service; the relay forwarded 752 upstream reports and dropped none. Across final per-packet collector records, 1/376 had a role inversion: switch sequence `[101, 2]` (spine then gateway), while the embedded hop timestamps are numerically gateway-first. Cross-switch clock comparability was not separately calibrated, so timestamps are recorded evidence, not an independently validated chronology.
- The inversion therefore confirms that collector append order can disagree with path order in this run. It does not establish a stable frequency: the earlier run showed a different arm/count pattern, and the sample is one short synthetic burst.
- In both arms, the collector's sink report is absent. That missing sink report alone cannot identify whether the business packet was delivered or lost; independent service-side ground truth separates the arms. We have not yet shown that an Agent-facing evidence bundle exposes enough information for this distinction.

## Agent-visible identifiability check

An offline comparison of the preserved collector JSONL files found 752 rows and 376 flow/packet keys in each arm. Every row in both arms has `sink_seen=false` and `trace_complete=false`. The hop-sequence histograms are identical except for one leaf-loss packet whose accumulated sequence is reversed; this single ordering anomaly is not a stable class signal. In contrast, evaluator-side service capture records 376 delivered packets in report-only and 0 in leaf-loss. That capture is ground truth, not Agent-visible evidence. The paired run therefore establishes delivery-state separation only at the evaluator boundary; it does not establish that the current collector-only view identifies the cause. Exposing service-side egress counters may make the distinction directly solvable by the simple R0 rule, so any future Agent study must freeze the exact tool-visible bundle first and compare an equal-information rule.

The pinned NIKA tool registry resolves the relevant `p4_gateway` tags to both `kathara_bmv2_mcp_server` and `kathara_telemetry_mcp_server`. Their tools are `p4rt_exec(args)` and `int_query_telemetry(...)`; `p4rt_exec` invokes `p4rt_manager.py`, whose CLI includes `counters`. Thus packet-port counters are reachable through the normal Agent tool surface. The current run's evaluator-side service capture separates the arms 376 versus 0 packets; it did not collect matched report-only and leaf-loss counter snapshots for this pair. A prior low-background run recorded a 376-versus-0 target-port counter delta, making the same-information R0 rule a strong expected baseline, but the exact counters still need to be recorded on both arms before a paired rule result is claimed. These are source/API reachability and evaluator-measured findings, not a real-Agent result.

**Decision for this concrete pair: NO-GO for an Agent-capability experiment.** Collector-only evidence does not yield a stable identifying signal; with the normal NIKA tool set, per-port counters are accessible and the existing R0 counter rule has the same distinguishing signal. Keep the pair as a runtime and information-boundary diagnostic, not as evidence of independent Agent value. Broader Agent-vs-rule research in communication-network telemetry remains a field-level direction only; it needs a separate falsifiable task design and gate before another model run.

## Research decision

**HOLD.** Keep the project centered on network telemetry diagnosis. The concrete next question is whether, under identical exposed telemetry and equal tool/budget access, an Agent can distinguish (a) delivered traffic with a lost sink report from (b) actual leaf egress loss—and whether it adds value over a topology/timestamp-aware rule. First freeze precisely what the Agent can observe; do not infer that collector ordering is a useful research mechanism from this single event.

Next evidence gate:

1. Define an Agent-visible evidence bundle separately from evaluator-only service capture and ground truth.
2. Verify whether the two paired states are distinguishable from that bundle. If they are not, report the task as unidentifiable rather than scoring an Agent as wrong.
3. If distinguishable, compare a model and an equal-information topology/timestamp rule on repeated, independently seeded runs; preserve full raw collector rows and packet-level event timestamps.
4. Expand to other traffic/topology conditions only after this controlled diagnostic has a valid answer key and a nontrivial rule baseline.

## Data caveats

`NIKA_PAIR_RESULT.json` is preserved byte-for-byte. Its legacy `telemetry_pair_ready=false` field is stale metadata (the runner never assigns it after initialization), so it must not be treated as the readiness decision. The structured arm data and this audit are authoritative for this run. The source has been changed to omit that stale field from future results.
