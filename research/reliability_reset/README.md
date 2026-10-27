# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint. It examined whether an unmodified native full scorer makes consequential, verifiable errors about execution reliability. Earlier controller/helper attribution and interface experiments remain development records; the current implementation has not established an original recovery algorithm.

**Closeout, 2026-10-27:** The [AppWorld audit](APPWORLD_AUDIT_CLOSEOUT_2026_10_27.md) and [paper-claim review](PAPER_CLAIM_REVIEW_2026_10_27.md) found no current claim meeting the original-contract, reachability, full-scorer and consequential-novelty requirements. Current paper claims are NO-GO; the broader scientific status is HOLD. Stop random scoring-defect searches. If a concrete new candidate arises, first complete the [one-page design gate](ONE_PAGE_RESEARCH_DESIGN_GATE.md).

**Terminal taxonomy, 2026-10-27 (no version bump):** adding up the failure column of all 60 committed 1.0.35 executions changes the reading of the line. All 27 failures are terminations — 24 at the one-check cap, 3 escalations — with 0 false completions, 0 wrong publications and 0 forbidden effects; 22 of the 27 had already produced a correct record. The same 48 model runs read 89.6% on record correctness and 43.8% on safe completion. The check cap is 1 in all 60 runs and was used in all 60, so this packet measures budget arithmetic, not verification reliability. See the [record](TERMINAL_TAXONOMY.md).

**Current release: Reliability Reset 1.0.85 (2026-10-26), native tools, complete scoring and isolated-process replay.**

The [native control study](NATIVE_CONTROL_185.md) runs the original reference program and a legal title-exchange prefix followed by that same reference on the single train task already selected in 1.0.80. The reference passes both original tests; the variant passes the answer test but fails the collateral-state test. Both native completion signals are true, while only the reference receives full task success.

The title multiset, record count and IDs are preserved, but complete record hashes differ because other fields retain their own identity. The original full scorer detects the change. This closes this particular legal-operation candidate; it does not invalidate the [1.0.75 synthetic helper miss](HASH_AUDIT_175.md), prove all identity permutations unreachable or establish a benchmark-wide result. Two program controls are not model evidence.

Pinned compatible dependencies make the unchanged upstream source run on this Windows host. Three bootstrap failures and one incorrect same-process score replay are retained. The low-level evaluator deliberately retains task caches; the [replay utility](native_replay185.py) uses a new native process per arm and verifies original inputs plus key scoring source. Replayed scores match both live controls. See [results](evidence/1.0.85/NATIVE_EXECUTION_185.json), [runtime lock](evidence/1.0.85/RUNTIME_LOCK_185.json), [replay receipt](evidence/1.0.85/NATIVE_BOUND_REPLAY_185.json) and [release report](RELEASE_185.md).

An [encrypted original packet](evidence/1.0.85/native-controls-1.0.85.bundle) retains protected task/tests, terminal deltas, environment IO, API request logs and failure records; base DBs are referenced rather than duplicated. Per-call raw API response bodies were not captured. Upstream public encryption parameters satisfy distribution format, not confidentiality or independent authenticity.

```powershell
python -m research.reliability_reset.terminal_binding185 work/reliability-reset-1.0.85/native-root work/terminal-check-fresh.json
python -m research.reliability_reset.terminal_binding185 work/reliability-reset-1.0.85/native-root work/terminal-replay-fresh.json --native-python work/reliability-reset-1.0.85/venv/Scripts/python.exe
python -m unittest tests.test_reliability_reset_terminal_binding185 tests.test_reliability_reset_native_replay185 -v
```

The first command only checks the 38 recorded task-output files against the [terminal binding](evidence/closeout-2026-10-27/TERMINAL_BINDING.json); it does not call a scorer. The second optionally replays the two recorded terminal states and requires the original protected local inputs and pinned separate native runtime. Use a fresh extracted copy, since any changed, missing or extra output file fails the binding check. The tests use software controls without AppWorld. The 2026-10-27 closeout did not run the second command, a new task or a model; local digests do not independently authenticate history.

## Research milestones

| Releases | Contribution | Record |
| --- | --- | --- |
| 1.0.0–1.0.15 | Offline evidence audit, independent CSV/SQLite reconstruction, source-preserving review export | [Audit checkpoint](RELEASE_115.md) |
| 1.0.20 | Primary/helper/replacement attribution under shared budgets | [Programmatic controls](RELEASE_120.md) |
| 1.0.25 | First live DeepSeek prefixes; one-check query-planning failure | [Live recovery credit](RELEASE_125.md) |
| 1.0.30 | Budget/information guidance completed 12/12 versus original 0/12 | [Prompt intervention](RELEASE_130.md) |
| 1.0.35 | Prompt components, public query planner, and 16 post-publication budget failures | [Mechanism study](RELEASE_135.md) |
| 1.0.50 | Joint evidence validity and termination; ordinary-receipt completion 12/12 | [Joint study](RELEASE_150.md) |
| 1.0.55 | Matched text, state tracking and tool projection; retained parameter and fault-activation failure | [Interface study](RELEASE_155.md) |
| 1.0.60 | Direct-neighbor comparison, offline parameter contracts and orthogonal outcome audit | [Contract/audit release](RELEASE_160.md) |
| 1.0.65 | Exact public-prefix, fault-exposure and frozen-rule claim screen | [Claim screen](RELEASE_165.md) |
| 1.0.70 | Pinned AppWorld contract, scoring-chain and unresolved source-question audit | [Native-contract audit](RELEASE_170.md) |
| 1.0.75 | Source-bound public helper reproduction and a content-multiplicity blind spot | [Helper diagnostic](RELEASE_175.md) |
| 1.0.80 | One native start-state preflight; multiplicity candidate closed at this start | [Start-state preflight](RELEASE_180.md) |
| 1.0.85 | Original native tools, complete score controls and isolated-process replay | [Current release](RELEASE_185.md) |

Full historical commands, review-export procedures and checkpoint limitations are in [the historical/review guide](HISTORY_AND_REVIEW_GUIDE.md); release details are in [CHANGELOG.md](CHANGELOG.md). Experiments use different protocols and correlated development cases, so the table is a history rather than a combined leaderboard.

## Implementation and boundaries

- [Data contract](SCHEMA_V1.md): frozen artifacts, binding and scoring semantics.
- [First engineering release](RELEASE_100.md): frozen 1.0.0 scope and validation.
- [Previous adapter release](RELEASE_105.md): frozen 1.0.05 validation.
- [Previous review corrections](RELEASE_110.md): engineering corrections and two-phase preparation, with follow-up defects disclosed.
- [Previous audit release](RELEASE_115.md): partial-capture consistency and verified source-preserving review export.
- [Programmatic experiment](RELEASE_120.md): recovery credit, replacement control and shared-budget handoff.
- [Previous live experiment](RELEASE_125.md): actual DeepSeek prefixes, role isolation and budget-conditioned behavior.
- [Previous prompt intervention](RELEASE_130.md): real three-arm tool planning, full completion and information costs.
- [Previous mechanism/method study](RELEASE_135.md): factorial prompts, public evidence planning and post-publication stopping failures.
- [Previous joint-control study](RELEASE_150.md): evidence validity, receipt binding, admissible-action advice and receipt-loss controls.
- [Previous interface study](RELEASE_155.md): matched completion text, cost-feasible tool registry, retained proposals and actual fault activation.
- [Previous offline release](RELEASE_160.md): AFT/INTENT/HyperAgent comparison, parameter validation and separate safety/completion outcomes.
- [Previous claim screen](RELEASE_165.md): retained local effects, unmatched-prefix reasons and strong-rule falsification.
- [Previous native-contract audit](RELEASE_170.md): source-bound scoring definitions, candidate closures and an unresolved identity question; no task reproduction.
- [Earlier hash audit](RELEASE_175.md): unchanged-helper reproduction, ordinary/benign controls and a bounded native-case decision.
- `audit.py`: offline importer, reliability classification, missingness bounds, matched comparison and review export.
- `controls.py`: reproducible synthetic controls, zero network/provider activity.
- `review_views.py` / `review_fidelity.py`: scoped first-pass export and source comparison; no blinding or authenticity certification.
- `recovery_credit.py`: local primary/helper/replacement intervention runner and per-intent reports.
- `credit_live.py`: bounded DeepSeek transport, raw response ledger and exact-prefix paired live study.
- `tool_planning.py`: frozen prompt intervention, information-inclusion preflight and network-free model replay.
- `evidence_planner.py` / `planning_mechanism.py`: public evidence cover, lossless tool aliases, factorial/transfer experiments and response-bound replay.
- `evidence_state.py` / `joint_control.py`: public evidence validity, receipt-aware state, optional lost-repair-ack control and joint planning experiment.
- `feasible_interface.py`: matched-text/state/interface intervention, excluded-action accounting and full model/rule replay.
- `tool_contracts.py`: explicit per-tool parameters and opt-in offline rejection preserving unmodified proposals.
- `outcomes.py` / `offline160.py`: orthogonal world/evidence/termination/rejection labels and source-bound audit of the 1.0.55 archive.
- `claim_screen.py`: post-fault public-prefix reconstruction and descriptive exposure/rule screening; no new environment execution.
- `hash_probe175.py`: synthetic software boundary diagnostic of pinned public functions; not an AppWorld task evaluator or new recovery policy.
- `native_case180.py`: digest-bound original start-state SQL reconstruction and aggregate multiplicity preflight; no native task score or API execution.
- `native_replay185.py`: source/input-bound original score replay in a fresh native process for each recorded control; no model or new tool trajectory.
- `terminal_binding185.py`: check the recorded terminal file set and digests before optional native score replay.
- `tests/test_reliability_reset.py`: mutation, budget, actor and provenance rejection checks.

The generic importer trusts supplied adapter facts after structural checks. The new adapter additionally reconstructs one supported task from original CSV/SQLite/capture artifacts. Neither establishes evidence authenticity or scientific independence. The runner and original environment share development ancestry, and separate algorithms cannot replace source review. This release leaves the inherited `VERSION` and historical FaultDA evidence untouched; subsystem releases follow `1.0.0`, `1.0.05`, `1.0.10`, and so on.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The independent-family scientific claim remains **HOLD**. Current interface/planning methods are engineering controls with direct prior work. A local effect that a frozen public rule already supplies is not sufficient scientific increment. The existing native-scoring audit is closed; future research follows the design gate above rather than an automatic search for another example.
