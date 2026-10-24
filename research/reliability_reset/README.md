# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint. The active research prototype asks whether a system's recovery success comes from its primary controller, an external repair helper, or their interaction. It keeps the earlier evidence-audit infrastructure and the broader evaluation-reliability question.

**Current release: Reliability Reset 1.0.50 (2026-10-24), joint evidence/action/termination control.**

The [joint study](JOINT_CONTROL_150.md) ran 54 actual DeepSeek trajectories and 9 shared backend controls, receiving all 181 API responses without parse/provider errors. With ordinary receipts, joint planning completed **12/12**, strong combined prompting **5/12**, read-only planning **1/12**. Rejected reads after successful publication fell from ten to zero versus read-only planning. Under six realized lost repair receipts, joint planning still exceeded the budget five times and escalated once. See [results, fault activation and costs](RELEASE_150.md).

The method invalidates report evidence after writes, derives a new current report only from a known candidate plus bound CAS receipt, and displays cost-feasible actions. It does not verify numerical correctness or override any model proposal. Every arm gets the same additive completion-evidence contract; original metrics remain intact and the evidence-qualified score is separately reported.

```powershell
python -m research.reliability_reset.joint_control work/reset150-new --prepare
python -m research.reliability_reset.joint_control work/reset150-new --execute
python -m research.reliability_reset.joint_control work/reset150-new --verify work/reset150-replay
```

All 54 model traces and 181 response classifications replayed offline. The next release, **1.0.55**, tests a structured admissible-action interface against the current advisory list, with matched completion text and all rejected attempts retained. Tasks remain historical development examples in one environment.

## Research milestones

| Releases | Contribution | Record |
| --- | --- | --- |
| 1.0.0–1.0.15 | Offline evidence audit, independent CSV/SQLite reconstruction, source-preserving review export | [Audit checkpoint](RELEASE_115.md) |
| 1.0.20 | Primary/helper/replacement attribution under shared budgets | [Programmatic controls](RELEASE_120.md) |
| 1.0.25 | First live DeepSeek prefixes; one-check query-planning failure | [Live recovery credit](RELEASE_125.md) |
| 1.0.30 | Budget/information guidance completed 12/12 versus original 0/12 | [Prompt intervention](RELEASE_130.md) |
| 1.0.35 | Prompt components, public query planner, and 16 post-publication budget failures | [Mechanism study](RELEASE_135.md) |
| 1.0.50 | Joint evidence validity and termination; ordinary-receipt completion 12/12 | [Current study](RELEASE_150.md) |

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
- [Current joint-control study](RELEASE_150.md): evidence validity, receipt binding, admissible-action advice and receipt-loss controls.
- `audit.py`: offline importer, reliability classification, missingness bounds, matched comparison and review export.
- `controls.py`: reproducible synthetic controls, zero network/provider activity.
- `review_views.py` / `review_fidelity.py`: scoped first-pass export and source comparison; no blinding or authenticity certification.
- `recovery_credit.py`: local primary/helper/replacement intervention runner and per-intent reports.
- `credit_live.py`: bounded DeepSeek transport, raw response ledger and exact-prefix paired live study.
- `tool_planning.py`: frozen prompt intervention, information-inclusion preflight and network-free model replay.
- `evidence_planner.py` / `planning_mechanism.py`: public evidence cover, lossless tool aliases, factorial/transfer experiments and response-bound replay.
- `evidence_state.py` / `joint_control.py`: public evidence validity, receipt-aware state, optional lost-repair-ack control and joint planning experiment.
- `tests/test_reliability_reset.py`: mutation, budget, actor and provenance rejection checks.

The generic importer trusts supplied adapter facts after structural checks. The new adapter additionally reconstructs one supported task from original CSV/SQLite/capture artifacts. Neither establishes evidence authenticity or scientific independence. The runner and original environment share development ancestry, and separate algorithms cannot replace source review. This release leaves the inherited `VERSION` and historical FaultDA evidence untouched; subsystem releases follow `1.0.0`, `1.0.05`, `1.0.10`, and so on.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The broad independent-family measurement claim remains **HOLD**; exploratory research is active. Current joint control improves completion after confirmed publication; uncertain-receipt budget control is still unresolved. The next method compares advisory and structured admissible-action interfaces before a separate held-out study.
