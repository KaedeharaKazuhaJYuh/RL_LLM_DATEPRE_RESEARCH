# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint. The active research prototype asks whether a system's recovery success comes from its primary controller, an external repair helper, or their interaction. It keeps the earlier evidence-audit infrastructure and the broader evaluation-reliability question.

**Current release: Reliability Reset 1.0.55 (2026-10-24), budget-projected tool interfaces and matched completion text.**

The [matched-interface study](FEASIBLE_INTERFACE_155.md) ran 54 actual DeepSeek trajectories and 9 shared backend controls, receiving all **207** API responses without parse/provider errors. Ordinary-receipt completion was **12/12 in every arm**. Under planned receipt loss, matched text, soft state and projected tools had **6 / 1 / 0 rejected reads**. Projection triggered only five faults: another publication omitted a required parameter and failed before commit. All five realized faults escalated; escalation is not recovery completion. See [results, retained failure and costs](RELEASE_155.md).

Public state tracking invalidates stale report evidence and binds known candidates to successful CAS receipts. The new projection removes unaffordable tools from the advertised registry/action enum. It never repairs a model proposal or imports private numerical truth. Every arm receives identical conditional completion text and the same additive evidence contract. State tracking reduced invalid reads locally; projection did not dominate soft state in completion or ordinary-case costs.

```powershell
python -m research.reliability_reset.feasible_interface work/reset155-new --prepare
python -m research.reliability_reset.feasible_interface work/reset155-new --execute
python -m research.reliability_reset.feasible_interface work/reset155-new --verify work/reset155-replay
```

All 54 model traces, 9 rule traces and 207 response classifications replayed offline. The full suite completed with **1010 passes and 3 conditional skips**. Next **1.0.60** tests per-tool parameter schemas and source-linked evidence compaction against frozen decision prefixes. Tasks remain historical development examples in one environment; no weight training was performed.

## Research milestones

| Releases | Contribution | Record |
| --- | --- | --- |
| 1.0.0–1.0.15 | Offline evidence audit, independent CSV/SQLite reconstruction, source-preserving review export | [Audit checkpoint](RELEASE_115.md) |
| 1.0.20 | Primary/helper/replacement attribution under shared budgets | [Programmatic controls](RELEASE_120.md) |
| 1.0.25 | First live DeepSeek prefixes; one-check query-planning failure | [Live recovery credit](RELEASE_125.md) |
| 1.0.30 | Budget/information guidance completed 12/12 versus original 0/12 | [Prompt intervention](RELEASE_130.md) |
| 1.0.35 | Prompt components, public query planner, and 16 post-publication budget failures | [Mechanism study](RELEASE_135.md) |
| 1.0.50 | Joint evidence validity and termination; ordinary-receipt completion 12/12 | [Joint study](RELEASE_150.md) |
| 1.0.55 | Matched text, state tracking and tool projection; retained parameter and fault-activation failure | [Current study](RELEASE_155.md) |

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
- [Current interface study](RELEASE_155.md): matched completion text, cost-feasible tool registry, retained proposals and actual fault activation.
- `audit.py`: offline importer, reliability classification, missingness bounds, matched comparison and review export.
- `controls.py`: reproducible synthetic controls, zero network/provider activity.
- `review_views.py` / `review_fidelity.py`: scoped first-pass export and source comparison; no blinding or authenticity certification.
- `recovery_credit.py`: local primary/helper/replacement intervention runner and per-intent reports.
- `credit_live.py`: bounded DeepSeek transport, raw response ledger and exact-prefix paired live study.
- `tool_planning.py`: frozen prompt intervention, information-inclusion preflight and network-free model replay.
- `evidence_planner.py` / `planning_mechanism.py`: public evidence cover, lossless tool aliases, factorial/transfer experiments and response-bound replay.
- `evidence_state.py` / `joint_control.py`: public evidence validity, receipt-aware state, optional lost-repair-ack control and joint planning experiment.
- `feasible_interface.py`: matched-text/state/interface intervention, excluded-action accounting and full model/rule replay.
- `tests/test_reliability_reset.py`: mutation, budget, actor and provenance rejection checks.

The generic importer trusts supplied adapter facts after structural checks. The new adapter additionally reconstructs one supported task from original CSV/SQLite/capture artifacts. Neither establishes evidence authenticity or scientific independence. The runner and original environment share development ancestry, and separate algorithms cannot replace source review. This release leaves the inherited `VERSION` and historical FaultDA evidence untouched; subsystem releases follow `1.0.0`, `1.0.05`, `1.0.10`, and so on.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The broad independent-family measurement claim remains **HOLD**; exploratory research is active. Matching completion text closed the ordinary-receipt gap, while public state tracking improved uncertainty handling locally. The next method addresses parameter completeness and context costs, retaining task completion and fault activation as separate outcomes.
