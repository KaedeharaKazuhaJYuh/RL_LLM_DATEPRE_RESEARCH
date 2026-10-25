# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint. The active question is whether a benchmark's unmodified native full scorer can make consequential, verifiable errors about execution reliability. Earlier controller/helper attribution and interface experiments remain development records; the current implementation has not established an original recovery algorithm.

**Current release: Reliability Reset 1.0.70 (2026-10-26), AppWorld native-contract and scoring-chain review.**

The [native-contract audit](APPWORLD_AUDIT_170.md) pins AppWorld commit `42b5bcf3cd334fee33f0c37c02070a9f5807add5` and verifies 19 plaintext files (522,076 bytes) against SHA-256 digests and the official Git tree. Native scoring already supports collateral-state checks and separates the completion flag from task-test success. Task and scenario aggregation are explicitly different. These facts close several generic explanations for apparent mismeasurement.

One hash-set/record-identity question remains unresolved. Hash-generation semantics, legal model/API reachability, all native task tests and original run artifacts have not been obtained; conditional examples were not executed and are not confirmed defects. This is a generic scoring-chain review, **not a full task-scorer reproduction**. See [release findings](RELEASE_170.md), [fixed source manifest](evidence/1.0.70/SOURCE_MANIFEST_170.json) and [machine-readable review](evidence/1.0.70/APPWORLD_AUDIT_170.json).

No AppWorld installation, protected bundle, task data, output bundle or native execution was added. The audit report includes an offline digest-verification command for the source cache; a fresh checkout can retrieve the 19 fixed plaintext URLs without installing the benchmark. No model API call, trajectory or independent task family was added.

The prior [public-prefix/rule screen](RESEARCH_SCREEN_165.md) retains local state/cost benefits without a recovery-completion gain. The recovery-algorithm claim remains NO-GO and the broader scientific question HOLD. Next is one bounded source check of record-hash identity semantics, with an explicit close condition, before separately designing any native train/dev case. New data collection, cross-model or paid evaluation does not follow automatically.

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
| 1.0.70 | Pinned AppWorld contract, scoring-chain and unresolved source-question audit | [Current release](RELEASE_170.md) |

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
- [Current native-contract audit](RELEASE_170.md): source-bound scoring definitions, candidate closures and an unresolved identity question; no task reproduction.
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
- `tests/test_reliability_reset.py`: mutation, budget, actor and provenance rejection checks.

The generic importer trusts supplied adapter facts after structural checks. The new adapter additionally reconstructs one supported task from original CSV/SQLite/capture artifacts. Neither establishes evidence authenticity or scientific independence. The runner and original environment share development ancestry, and separate algorithms cannot replace source review. This release leaves the inherited `VERSION` and historical FaultDA evidence untouched; subsystem releases follow `1.0.0`, `1.0.05`, `1.0.10`, and so on.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The independent-family scientific claim remains **HOLD**. Current interface/planning methods are engineering controls with direct prior work. A local effect that a frozen public rule already supplies is not sufficient scientific increment. The next check targets native benchmark measurement validity without changing success definitions or silently introducing a new task family.
