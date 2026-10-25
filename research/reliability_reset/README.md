# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint. The active research prototype asks whether a system's recovery success comes from its primary controller, an external repair helper, or their interaction. It keeps the earlier evidence-audit infrastructure and the broader evaluation-reliability question.

**Current release: Reliability Reset 1.0.60 (2026-10-25), direct-neighbor review and offline input contracts.**

The [primary-paper comparison](DIRECT_COMPARISON_160.md) identifies direct overlap with AFT-Bench, INTENT and HyperAgent. Current tool exposure, budget planning, receipt/effect tracking and safe termination implementations are retained as engineering; they do not establish an original algorithm. AFT is compared section by section, with versions, sources and unresolved coverage limits recorded.

This release adds per-tool required fields/types and a proposal-preserving offline validation gate. Reclassification of **207 frozen model responses** found exactly one missing publish.mode; **all 63 historical completion labels remain unchanged**. The new outcome vector separates actual state, public evidence, safe escalation, tool rejection, budget rejection and realized fault activation. See [contracts and outcome definitions](OUTCOME_CONTRACT_160.md) and [release results](RELEASE_160.md).

```powershell
python -m research.reliability_reset.offline160 work/reset160-audit.json
python -m unittest tests.test_reliability_reset_contracts160 -v
```

**No new API calls, models or task families were added.** The full suite completed with **1020 passes and 3 conditional skips**. Next work is a differentiated, falsifiable claim and task/metric design review; cross-task expansion and paid runs are conditional on that review. Safe escalation is not task completion, and zero completion alone is not proof of model incapacity.

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
| 1.0.60 | Direct-neighbor comparison, offline parameter contracts and orthogonal outcome audit | [Current release](RELEASE_160.md) |

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
- [Current offline release](RELEASE_160.md): AFT/INTENT/HyperAgent comparison, parameter validation and separate safety/completion outcomes.
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
- `tests/test_reliability_reset.py`: mutation, budget, actor and provenance rejection checks.

The generic importer trusts supplied adapter facts after structural checks. The new adapter additionally reconstructs one supported task from original CSV/SQLite/capture artifacts. Neither establishes evidence authenticity or scientific independence. The runner and original environment share development ancestry, and separate algorithms cannot replace source review. This release leaves the inherited `VERSION` and historical FaultDA evidence untouched; subsystem releases follow `1.0.0`, `1.0.05`, `1.0.10`, and so on.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The independent-family scientific claim remains **HOLD**. Current interface/planning methods are engineering controls with direct prior work. The next research decision must identify a falsifiable difference beyond that work before new task families, models or paid experiments are introduced.
