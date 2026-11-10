# LossSight MCM source-level replay: terminal report loss

Date: 2026-11-07

## Scope

This is a paper-pseudocode analysis, not a runtime experiment and not a result from the released LossSight system. It checks whether the described MCM localization distinguishes a packet lost on the terminal leaf-to-service egress before the sink report is generated from the same packet reaching the service-facing egress and its sink report being lost before the collector.

## Source facts

- LossSight says the INT sink extracts metadata and sends a report to the Telemetry Server. It counts a missing expected server report as an INT packet-loss event and includes sink-to-server transmission/processing delay in its detection-latency model.
- The paper's operational target is therefore broader than only loss between INT switches: a report absent at the server is detected as loss. Its stated localization output, however, is indexed by INT nodes from source through sink; the paper does not define a separate sink-to-server report-channel root-cause label or report a controlled comparison of that cause against loss on the terminal business-packet egress.
- Its localization design maintains marking counters at INT nodes from source through sink. Algorithm 1 scans node indices from `m` down to `2` and marks the first index whose observed marking delta is unexpected.
- The printed MCM predicate is `(delta != 1) || (delta != -2^l + 1)`. For `l=2`, expected deltas are `+1` and wraparound `-3`; the printed disjunction is true for both expected values, so it is tautologically true. A faithful execution of the printed predicate therefore cannot be treated as a valid localization implementation. The intended operator may be `&&`, but that is an interpretation, not a confirmed correction.
- The released `FindINT-MCM(L=2)/receive.py` is a simplified H2 packet receiver. It compares one received packet's mark with a local expected mark; it is not an implementation of the paper's full per-hop Algorithm 1 or sink-to-server report pipeline.
- The paper also proposes source/sink flow-match counter comparison for persistent blackhole diagnosis after a report timeout. This may identify large sustained source-to-sink loss, but the paper does not state that the comparison attributes each individual missing report or the terminal one-packet pair considered here. Treat this as a strong related mechanism, not proof that LossSight either fully solves or cannot solve the exact pair.

## Follow-up baseline boundary: LB-LossSight

The 2023 LB-LossSight paper studies LossSight localization under ECMP and packet-level random packet spraying. It says one received marking pattern can leave several path-loss locations compatible, then adds per-flow/per-output-port marking counters and a pending-update mechanism. Its reported evaluation uses Mininet and P4/BMv2 on a 4-ary Fat-Tree, averages 100 runs of 1,500 INT packets, and obtains ground-truth loss counts from switch logs. This is a strong prior method for path packet-loss localization; generic “Agent reasons over ambiguous INT loss” or “marking fixes multipath ambiguity” would overlap.

The inspected full text evaluates losses along the forwarding paths and does not report a controlled pair where the business packet reaches the sink but only the resulting UDP telemetry report is lost before collection. NIKA's current Agent-facing API also does not expose LB-LossSight's per-output-port loss-bit counters. Therefore, LB-LossSight belongs in related work and can be an instrumented comparator only if both it and the Agent receive the same added marking data. It is not an equal-information baseline on the unmodified NIKA interface. The fair primary rule remains limited to NIKA-visible `read`/`counters`, INT rows, and equal-budget probes. This narrows the open candidate but does not establish novelty.

## Conditional hand replay

Assumptions for the replay: four ordered INT nodes, including sink as node 4; 2-bit per-flow counters increment once whenever a packet reaches a node; stable path and in-order delivery; one lost packet/report; no counter wrap ambiguity beyond modulo 4. These assumptions make the expected per-node mark increment `+1 mod 4` for consecutive observed packets.

| Event between two collector-visible reports | Delta at nodes 1–4 (mod 4) | Result if Algorithm 1 uses the likely intended `&&` predicate |
|---|---|---|
| No loss | `[1, 1, 1, 1]` | No node is marked lost |
| Business packet lost after node 2, before node 3 | `[2, 2, 1, 1]` | Descending scan first encounters node 2 as unexpected; labels the loss at the data-plane boundary around node 2 |
| Packet reaches sink (node 4), but its report is lost after sink processing | `[2, 2, 2, 2]` | Descending scan first encounters node 4; labels the terminal telemetry node |

The conditional replay indicates a terminal-boundary ambiguity: the paper's node-level localization can place a post-sink report loss at the sink, but does not name a separate sink-to-server/report-channel location. Its broad loss detector covers the missing report; the described output does not establish the requested causal distinction as a distinct root-cause label. Algorithm 2's source/sink flow-counter comparison is described for sustained blackhole detection; the paper does not specify that it is applied per missing report to identify post-sink channel loss. Because the paper explicitly models sink-to-server delay and defines missing-at-server reports as losses, the defensible statement is only that the exact *causal pair and label* are not demonstrated in the publication—not that LossSight cannot detect report-channel loss.

## Research consequence

This narrows the possible difference to **terminal-report attribution under the exact evidence exposed to the Agent**, not missing-report detection and not a new marking mechanism. In NIKA, per-hop reports are keyed by `(flow_id, packet_id)` and include a sink flag. A missing intermediate report may be inferable when a later-hop report for the same packet exists. The report-only equivalence holds only when the data-plane loss occurs at the last reporting egress: all earlier-hop rows are then shared, while the leaf/sink row is absent in both histories. An earlier data-plane loss, such as official dev-066's `gateway_1:eth1`, removes later spine/leaf rows and is therefore distinguishable from losing only the final sink report. Source/sink or port-counter evidence and probe budget remain decisive for the terminal pair. Aggregated counters may support a strong rule under low background traffic and become ambiguous under concurrent traffic; this remains to be measured.

The pinned NIKA collector appends a partial trace when each report arrives. Its `trace_complete` value is derived from whether any collected row has `sink=true`. Therefore, for a packet that has upstream reports but no collected sink report, these two hidden histories have the same report-only observation:

| Evidence available to the Agent | Packet dropped at final leaf-to-service egress | Packet forwarded to service; leaf/sink report lost before collector |
|---|---|---|
| Upstream per-hop reports for this packet | Present | Present |
| Sink report in collector | Absent | Absent |
| `sink_seen` / `trace_complete` | `false` / `false` | `false` / `false` |
| Relay evaluator log | No sink datagram received | Sink datagram received, then dropped |
| Switch counters | Sink-side delta absent for that packet, but only aggregate counts are exposed | Sink-side delta includes the packet, but mixed with other traffic |

The relay log is oracle/evaluator evidence and must not be given to the Agent. The last row is based on the counter collection path and packet-processing order in the pinned source; its per-packet attribution is an inference, not something the NIKA tool returns. NIKA's published dev-066 fault is earlier, at gateway1→spine, and is not the terminal pair in this table. A new versioned study task must configure the loss on the final leaf egress and separately drop only that leaf's UDP report. The pinned manager's `gateway-config --kind loss --switch ... --port ...` path accepts a switch name from the configured switch map, and the shared P4 ingress applies the loss table regardless of gateway/spine/leaf role; this is source-level reachability only. It motivates the exact next check: can a same-information counter rule recover the terminal distinction as background load and probe budget change?

## Frozen same-information rule to challenge first

The pinned NIKA `gateway.p4` increments `ingress_port_counter` at the beginning of ingress, applies the private loss hook later in ingress, and increments `egress_port_counter` in the egress control. The Agent-facing `p4rt_exec counters` returns nonzero counts by switch and port. Its `p4rt_exec read` command, when called without a switch, reads all configured switches and returns forwarding members (including BMv2 egress port IDs), groups, IPv4 LPM entries, counters and selected runtime configuration. The API sanitizer removes keys containing `internal_fault`, so this output does not intentionally expose the private fault table; exact mapping from egress port IDs to interface names still needs to be verified as Agent-visible rather than taken from the evaluator's topology model. NIKA release 0.2.0 identifies this environment as BMv2. BMv2 `simple_switch` documents that a packet marked to drop at the end of ingress is dropped before packet-buffering and egress processing; this supports (but does not replace runtime verification of) the inference that such a packet increments ingress and not egress counters. For an isolated, known route and a measurement window containing only a controlled probe batch, a deterministic rule can compare the relevant ingress/egress deltas:

1. Take a counter snapshot and preserve the report-trace snapshot.
2. Send the already budgeted, uniquely identified probe batch along a known path.
3. Take a second counter/report snapshot.
4. If the target path's data-plane egress count is short while upstream reports exist, classify forwarding loss. If the forwarding counters account for the probe but the sink report is absent, classify report-channel loss. If multiple paths or background packets make the aggregate deltas non-unique, return `underdetermined` rather than guessing.

In the isolated case, the rule is expected to separate the two histories without an LLM. This is a **source-derived prediction**, not an observed NIKA result. That low-background condition should be a negative/control arm for Agent value; it cannot support a model-mechanism contribution by itself. It is also not yet clear that the Agent knows the faulted interface: the verifier's mapping from probe flows to egress ports is oracle-only, while `p4rt_exec read` does expose switch route groups and port IDs. The discriminating experiment, if the runtime becomes available, must pair both causes across predeclared background loads and probe budgets, include the `underdetermined` outcome, and compare the Agent with this exact rule using identical observations and actions. Do not give the baseline the relay log, `root_cause_name`, hidden port mapping, or any verifier field. Because `p4rt_exec` accepts raw CLI arguments and its manager has mutating subcommands, use a read-only wrapper that allows only `read`/`counters`; the default NIKA diagnosis policy otherwise permits all tools and node roles.

**Threats to this rule:** port counters aggregate unrelated traffic; ingress and egress ports are not a per-packet join; routes may be ECMP or change during the window; cumulative counters can reset or wrap; ordinary TTL/ACL drops and multiple losses can also create ingress/egress gaps. The NIKA task's true fault interface is hidden from the Agent, so the rule must identify a deficit from public topology and counters rather than receive the target port as an input. These are reasons to measure the rule's ambiguity rate, not reasons to assume it fails.

### Identifiability bound from aggregation (constructed, not measured)

For one target packet, let `y=0` mean it failed before the counted egress and `y=1` mean it was forwarded but its sink report was lost; let `b` be unrelated packets counted on that egress during the same window. The exposed aggregate is `E=b+y`. If `b` is unknown, `E=1` is compatible with both `(b=1,y=0)` and `(b=0,y=1)`. Thus the port counter is not a per-packet witness under unrestricted background traffic. If the exact same background trace is replayed in a paired comparison, the two conditions differ by one egress count. The decisive experiment must therefore report both: a matched-background causal contrast (to estimate the effect cleanly) and a blind classification setting where background is not revealed to the Agent (to measure operational identifiability). These are different estimands; one cannot substitute for the other.

## Decision

Keep the communication-telemetry research direction fixed. Keep this particular candidate **HOLD**. Before any model run, compare (1) report-trace-only evidence, (2) report trace plus the exact NIKA-visible port counters, and (3) the best deterministic rule under the same probe budget, across the paired terminal-loss causes and controlled background traffic. If the equal-information rule resolves the distinction, close the Agent-mechanism claim. No runtime NIKA, Docker/WSL, or model/API experiment was run for this source-level replay.

## References

- LossSight paper, Sections III–IV and Algorithm 1: <https://tanlizhuang.cn/papers/2021-%E8%AE%BA%E6%96%87-TNSM.pdf>
- Manzanares-López et al., “An INT-based packet loss monitoring system for data center networks implementing Fine-Grained Multi-Path routing,” *Internet Technology Letters* 6(6), e393 (2023), DOI: <https://doi.org/10.1002/itl2.393>
- INTCollector, “A High-performance Collector for In-band Network Telemetry”: <https://dl.ifip.org/db/conf/cnsm/cnsm2018/1570470751.pdf>
- Pinned public FindINT implementation README: <https://github.com/lzhtan/LossSight/blob/2b52b174c954aea8f31082aa9425a405044f4e5e/LossSight-FindINT/README.md>
- Pinned public FindINT MCM receiver: <https://github.com/lzhtan/LossSight/blob/2b52b174c954aea8f31082aa9425a405044f4e5e/LossSight-FindINT/FindINT-MCM%28L%3D2%29/receive.py>
- Pinned NIKA `hop_exporter.py` and `collector.py`, commit `ac4422d8a4a03be2b905e28edf72993d467e1b81`: <https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/hop_exporter.py> and <https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/collector.py>.
- Pinned NIKA gateway counter/fault order, same commit: `gateway.p4` ingress counter at line 161, fault hook at lines 233–236, and egress counter at line 262; <https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4>. `p4rt_manager.py` reads nonzero counter entries and returns per-switch/per-port packet and byte values in `cmd_counters`; <https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py>.
- Pinned NIKA P4 read projection and access defaults, same commit: `cmd_read` reads every configured switch unless a switch is specified; `observed_switch` returns forwarding members, groups, LPM entries, counters and selected runtime config; the default `DiagnosisAccessPolicy` allows all tools and node roles. <https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py> · <https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/run_config/schema.py>
- BMv2 `simple_switch` drop semantics: <https://github.com/p4lang/behavioral-model/blob/main/docs/simple_switch.md> (current upstream documentation; NIKA's pinned runtime behavior still needs a direct run-time check).

## Review procedure provenance

The evidence appraisal follows the workflow in Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*, current arXiv version v2, arXiv:2609.00065, https://doi.org/10.48550/arXiv.2609.00065. This is a review-method reference, not a networking related-work claim.
