# NIKA Paired Preflight Code Audit — 2026-11-09

## Scope

This review covers the current local `nika_leaf_service_loss_preflight.py` runner and its GitHub Actions workflow. It is a code and experiment-protocol audit only. No NIKA runtime, Agent, or API run was performed in this review.

## Findings and changes

The runner had a scientific-validity gap: its final `passed` flag was set from `phase == "complete"`. That condition did not itself establish that the report-only and leaf-loss arms were matched, that target packets actually entered the leaf, that the leaf-loss arm delivered no target packets to the service, or that the pass-through report relay forwarded the observed reports.

The runner now requires all of the following before reaching a successful paired record:

- Both arms have the same protocol, rate, packet size, duration, seed, flow count, destination, and flow tuples.
- Source-side AF_PACKET capture records the actual emitted `(flow_id, IPv4 ID)` set for each arm. In the report-only arm, those IDs must match service ingress and collector upstream IDs; in the leaf-loss arm, they must match collector upstream IDs while service receipt/capture remains zero.
- The report-only arm's service packet IDs match the relay-dropped sink-report IDs; this existing check is retained.
- The loss arm records positive leaf ingress, zero target-service egress, zero evaluator-side service packet capture/UDP receipts, and upstream collector rows with no sink rows.
- The loss-arm report relay starts, receives reports, forwards every received report, and drops none.
- The final `passed` flag is true only after the complete paired observation summary is written.

The Actions push trigger now targets the active branch, `comm-telemetry-crossday-load-audit-2026-11-09`, instead of the older reset branch. This makes the prepared runner executable after the user pushes the local workflow and script.

## Current execution state

The existing `NIKA_LEAF_SERVICE_LOSS_PREFLIGHT_2026_11_07_RUN1.json` through `RUN3.json` records use protocol `nika-leaf-service-loss-preflight-v0.7-report-only-arm`. They do **not** contain the matched leaf-loss arm added in v0.9 and cannot be cited as evidence that v0.9 passed.

This source ledger is required because the pinned `BurstTrafficGenerator` raw UDP sender simply calls `sendto` and suppresses `OSError`; its returned profile contains flow tuples and sender PIDs, not per-datagram send records. The new capture independently observes actual source egress frames rather than treating planned rate × duration as a sent-packet denominator. [Pinned sender source](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/traffic/burst.py#L24-L39)

An additional offline check of the old RUN3 record compared the service-side IPv4-ID sets with the collector's unique upstream IDs: all four flows matched exactly, 94/94 IDs per flow (376/376 total). This supports the packet-ID join used by the new source ledger, but it does not validate AF_PACKET capture on the source clients; that still requires a successful v0.9 runtime.

On this Windows machine, the only listed WSL distribution is `docker-desktop`, it is stopped, and `podman`, `kathara`, `mininet`, `containerd`, `nerdctl`, and the GitHub CLI are unavailable. The hosted runner is the prepared execution route; the workflow and v0.9 runner are currently local and unpushed. Therefore no new runtime observation is available yet.

## Scientific status and next decision

This paired preflight only verifies that the two terminal mechanisms can be produced and measured under the small pinned topology. It still does not test the background-load aliasing hypothesis, a deterministic baseline on a held-out workload, an Agent, or independent task clusters. The earlier clean pair remains explainable by the visible per-port counter rule. Keep the paper claim **HOLD**.

After the hosted paired preflight succeeds, the next experiment must freeze a bounded, seed-separated shared-port workload matrix and test whether the same-information counter/probe rules retain target-level attribution under concurrent traffic. If the rules still identify the target cause, there is no Agent experiment to run for this candidate. If a reproducible ambiguity remains, define the exact target-level task labels and rule baselines in the one-page gate before any model run.
