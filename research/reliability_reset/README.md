# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint and pauses the previous VeriCost/mechanism line. It tests a single question: whether outcome-only agent evaluation makes consequential, independently verifiable mistakes about real operational reliability, and whether any such mistakes recur across independent task families.

**Current release: Reliability Reset 1.0.10 (2026-10-23), engineering review corrections.**

The received 1.0.05 review explicitly identifies its author as an agent. It is preserved as external-agent technical feedback; independent human/scientific review remains pending. [Response](REVIEW_RESPONSE_110.md), [current release](RELEASE_110.md) and [database/distributed-systems context](SYSTEMS_CONTEXT_110.md) document the corrections and limits.

Current reproduction:

```powershell
python -m research.reliability_reset.semantic_adapter work/reset110-development
python -m research.reliability_reset.audit work/reset110-development/bundle.json --output work/reset110-audit --review-output work/reset110-phase-two
python -m research.reliability_reset.review_views work/reset110-development/bundle.json --output work/reset110-first-pass --mapping work/reset110-audit/private-first-pass-map.json
```

First-pass normalized sources exclude machine-derived state/reference labels and explicit condition/arm names. Phase-two material retains original bytes plus derived checks and is unblinded. Do not give the private mapping or phase-two labels to the initial reviewer. This is a preparation workflow, not an independent certification of blinding.

The current controls are an explicit derivative of one historical group task: v2 first value +1, plus declared missing-value and publication interventions. There are twelve conditions, two programmatic arms and repeated behaviors; no independent empirical sample size is inferred. `snapshot_correct` is separate from evidence-qualified `terminal_correct`, and incomplete termination capture propagates null. Original 1.0.05 files remain frozen.

The [current go/no-go record](GO_NO_GO_110.md) permits engineering verification only; model calls and scientific expansion remain NO-GO. The external-agent memo is preserved without promoting it to human approval.
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
- [Current release](RELEASE_110.md): engineering review corrections and two-phase review preparation.
- `audit.py`: offline importer, reliability classification, missingness bounds, matched comparison and review export.
- `controls.py`: reproducible synthetic controls, zero network/provider activity.
- `tests/test_reliability_reset.py`: mutation, budget, actor and provenance rejection checks.

The generic importer trusts supplied adapter facts after structural checks. The new adapter additionally reconstructs one supported task from original CSV/SQLite/capture artifacts. Neither establishes evidence authenticity or scientific independence. The runner and original environment share development ancestry, and separate algorithms cannot replace source review. This release leaves the inherited `VERSION` and historical FaultDA evidence untouched; subsystem releases follow `1.0.0`, `1.0.05`, `1.0.10`, and so on.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The scientific status remains **HOLD**. A positive development pilot would only justify designing a separate held-out study; a negative or non-distinct result means keeping FaultDA-Bench as engineering infrastructure and stopping expansion of the current research claim.
