# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint. The active research prototype asks whether a system's recovery success comes from its primary controller, an external repair helper, or their interaction. It keeps the earlier evidence-audit infrastructure and the broader evaluation-reliability question.

**Current release: Reliability Reset 1.0.25 (2026-10-24), live DeepSeek recovery credit.**

The [live study](LIVE_CREDIT_125.md) generated 12 real DeepSeek primary trajectories, then ran 12 exact-prefix helper continuations and 12 helper-only replacements. All 41 API requests returned; no response failed parsing. At one available check, primary and paired-helper systems completed 0/6 cells while the public helper completed 6/6. At four checks, all three completed 6/6. The low-budget primary always spent its first check on status and then requested inspect; budget termination occurred before a voluntary helper handoff. See [results](RELEASE_125.md).

```powershell
python -m research.reliability_reset.credit_live work/reset125-live --prepare
python -m research.reliability_reset.credit_live work/reset125-live --execute
```

Preparation is offline; execution uses the configured DeepSeek credential under a frozen request/cost envelope. Raw model response bodies and decision bindings are retained. The helper continuation reuses the same actual primary prefix, not a second independent model sample. The next experiment isolates budget-aware tool-selection guidance while measuring information and token costs.

## Previous recovery-credit controls (1.0.20)

[Research design](RECOVERY_CREDIT_120.md) and [results/release](RELEASE_120.md) describe the primary-alone / primary-plus-helper / helper-alone comparison. All three share public tools and total budgets; handoff consumes a decision. The offline prototype covers 12 historical task instances, six conditions, two check budgets and seven system configurations. These are programmatic controls across three analysis intents in one environment.

```powershell
python -m research.reliability_reset.recovery_credit work/reset120-credit
python -m unittest tests.test_reliability_reset_credit -v
```

The 1.0.20 controls did not call a provider; the current 1.0.25 release adds the live development pilot. Earlier broad paper claims retain their previous status without blocking local exploratory experiments. No new dataset was downloaded.

## Evidence-audit infrastructure (1.0.15)

The received 1.0.05 review explicitly identifies its author as an agent. It is preserved as external-agent technical feedback; independent human/scientific review remains pending. The [1.0.15 release](RELEASE_115.md) fixed two follow-up defects in 1.0.10; the earlier [review response](REVIEW_RESPONSE_110.md) and [systems context](SYSTEMS_CONTEXT_110.md) remain available.

Audit reproduction (fresh outputs use the current implementation version):

```powershell
python -m research.reliability_reset.semantic_adapter work/reset115-development
python -m research.reliability_reset.audit work/reset115-development/bundle.json --output work/reset115-audit --review-output work/reset115-phase-two
python -m research.reliability_reset.review_views work/reset115-development/bundle.json --output work/reset115-first-pass --mapping work/reset115-audit/private-first-pass-map.json
python -m research.reliability_reset.review_views work/reset115-development/bundle.json --output work/reset115-first-pass --mapping work/reset115-audit/private-first-pass-map.json --verify
```

First-pass sources exclude machine-derived state/reference labels. Only native capture-envelope identities are aliased; nested business fields are preserved, and other source files retain exact bytes. A separate verifier reverses permitted substitutions and checks the view against the bound originals, even if its inventory was regenerated. Verification allows filled review annotations and checks case/file coverage. It establishes local consistency, not authenticity or independent certification of blinding. Phase-two material retains original bytes plus derived checks and is unblinded; keep it and the private mapping out of initial review. Old 1.0.10 views/maps remain frozen and must be regenerated into a new directory for this workflow.

The audit-adapter controls are an explicit derivative of one historical group task: v2 first value +1, plus declared missing-value and publication interventions. There are twelve conditions, two programmatic arms and repeated behaviors; no independent empirical sample size is inferred. `snapshot_correct` is separate from evidence-qualified `terminal_correct`, and incomplete termination capture propagates null. Original 1.0.05 files remain frozen.

Partial capture is supported only as a contiguous prefix beginning at step zero. A broken prefix, rewritten publication history, or ledger change during a read action is rejected before attribution. Valid missing suffixes keep termination unknown while retaining any already-proven harm. The [1.0.15 decision record](GO_NO_GO_115.md) remains a historical checkpoint; the new [1.0.20 exploration](RECOVERY_CREDIT_120.md) adds the offline recovery-credit study under the user's updated scope. The external-agent memo is preserved without promoting it to human approval.
No new model runs, API calls, downloads, fine-tuning, or held-out task construction have occurred. The offline audit foundation now has a real CSV/SQLite adapter for one historical development task, plus a separate Fraction-based state/trace extractor. All executions are programmatic engineering controls. They validate the adapter, not the research hypothesis.

## Previous 1.0.05 adapter checkpoint

```powershell
python -m research.reliability_reset.semantic_adapter work/reset105-development
python -m research.reliability_reset.audit work/reset105-development/bundle.json --output work/reset105-audit --review-output work/reset105-review
python -m unittest tests.test_reliability_reset tests.test_reliability_reset_adapter -v
```

The adapter keeps the old `contract_complete` outcome score and full original oracle result unmodified. It separately reads attached CSVs, a read-only SQLite snapshot, and trusted before/after action captures. Its reference code imports neither the old oracle nor tool-side math. Eight workflow/capture conditions and two programmatic arms produce sixteen records from **one** already-seen task. The stress arm is deliberately constructed, not a model; the capture-loss case is a declared missing-evidence control.

The old `safe_complete` metric already detects the planted repaired violation. This validates preservation of that known distinction; it does not establish an overlooked defect in the original benchmark. See [release report](RELEASE_105.md), [go/no-go decision](GO_NO_GO_105.md) and [adapter/review dossier](ADAPTER_105.md). Paid/live model execution remains NO-GO and scientific status HOLD.

The [same-version novelty review](NOVELTY_REVIEW_2026_10_23.md) found additional direct overlap and narrowed the manuscript's claims. [Three candidate designs](CANDIDATE_SCREEN_2026_10_23.md) were screened; none qualifies for live execution. The [focused human review form](FOCUSED_REVIEW_105.md) is pending. Reading documentation and paper sections is not a complete source audit, and this screening adds no model result or new task family.

## Reproduce the first release

From the repository root, with Python 3.11 or later (standard library only):

```powershell
python -m research.reliability_reset.controls work/reset100-controls
python -m research.reliability_reset.audit work/reset100-controls/bundle.json --output work/reset100-audit --review-output work/reset100-review
python -m unittest tests.test_reliability_reset -v
```

Use new output directory names on reruns; existing evidence/results are not overwritten. `audit.json` contains all run-level labels, denominators, unresolved cases and paired comparisons. `REPORT.md` is the concise summary. The separate review directory contains original contract/input/trace/state files and a blank review form; outcome scores and fact-adapter outputs are withheld. Raw source metadata remains visible, so this is not a fully blinded scientific study.

The two scripted arms and ten cases in the first-release controls belong to **one synthetic control family**. They are not independent tasks, a capable model, a strong rule baseline, or a pilot supporting GO.

## Implementation and boundaries

- [Data contract](SCHEMA_V1.md): frozen artifacts, binding and scoring semantics.
- [First engineering release](RELEASE_100.md): frozen 1.0.0 scope and validation.
- [Previous adapter release](RELEASE_105.md): frozen 1.0.05 validation.
- [Previous review corrections](RELEASE_110.md): engineering corrections and two-phase preparation, with follow-up defects disclosed.
- [Previous audit release](RELEASE_115.md): partial-capture consistency and verified source-preserving review export.
- [Programmatic experiment](RELEASE_120.md): recovery credit, replacement control and shared-budget handoff.
- [Current live experiment](RELEASE_125.md): actual DeepSeek prefixes, role isolation and budget-conditioned behavior.
- `audit.py`: offline importer, reliability classification, missingness bounds, matched comparison and review export.
- `controls.py`: reproducible synthetic controls, zero network/provider activity.
- `review_views.py` / `review_fidelity.py`: scoped first-pass export and source comparison; no blinding or authenticity certification.
- `recovery_credit.py`: local primary/helper/replacement intervention runner and per-intent reports.
- `credit_live.py`: bounded DeepSeek transport, raw response ledger and exact-prefix paired live study.
- `tests/test_reliability_reset.py`: mutation, budget, actor and provenance rejection checks.

The generic importer trusts supplied adapter facts after structural checks. The new adapter additionally reconstructs one supported task from original CSV/SQLite/capture artifacts. Neither establishes evidence authenticity or scientific independence. The runner and original environment share development ancestry, and separate algorithms cannot replace source review. This release leaves the inherited `VERSION` and historical FaultDA evidence untouched; subsystem releases follow `1.0.0`, `1.0.05`, `1.0.10`, and so on.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The scientific status remains **HOLD**. A positive development pilot would only justify designing a separate held-out study; a negative or non-distinct result means keeping FaultDA-Bench as engineering infrastructure and stopping expansion of the current research claim.
