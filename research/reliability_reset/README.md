# Outcome-based Agent Evaluation Reliability Reset

This branch starts from the `0.5.65-dev` infrastructure checkpoint and pauses the previous VeriCost/mechanism line. It tests a single question: whether outcome-only agent evaluation makes consequential, independently verifiable mistakes about real operational reliability, and whether any such mistakes recur across independent task families.

**Current release: Reliability Reset 1.0.0 (2026-10-22), offline audit foundation.**
No new model runs, API calls, downloads, fine-tuning, or held-out task construction have occurred. The implementation now supports separately frozen outcome scores, imported reliability facts, family-level descriptive summaries, exact matched-arm comparisons, and a label-withheld source review package. Its synthetic controls test the software, not the research hypothesis.

## Reproduce the first release

From the repository root, with Python 3.11 or later (standard library only):

```powershell
python -m research.reliability_reset.controls work/reset100-controls
python -m research.reliability_reset.audit work/reset100-controls/bundle.json --output work/reset100-audit --review-output work/reset100-review
python -m unittest tests.test_reliability_reset -v
```

Use new output directory names on reruns; existing evidence/results are not overwritten. `audit.json` contains all run-level labels, denominators, unresolved cases and paired comparisons. `REPORT.md` is the concise summary. The separate review directory contains original contract/input/trace/state files and a blank review form; outcome scores and fact-adapter outputs are withheld. Raw source metadata remains visible, so this is not a fully blinded scientific study.

The two scripted arms and ten cases belong to **one synthetic control family**. They are not independent tasks, a capable model, a strong rule baseline, or a pilot supporting GO.

## Implementation and boundaries

- [Data contract](SCHEMA_V1.md): frozen artifacts, binding and scoring semantics.
- [Release and next gate](RELEASE_100.md): scope, validation and concrete next work.
- `audit.py`: offline importer, reliability classification, missingness bounds, matched comparison and review export.
- `controls.py`: reproducible synthetic controls, zero network/provider activity.
- `tests/test_reliability_reset.py`: mutation, budget, actor and provenance rejection checks.

The importer trusts supplied adapter facts only after structural checks; it does not independently reconstruct arbitrary application state or establish evidence authenticity. Different implementation IDs or hashes cannot prove scientific independence. A real task adapter and its sources still need review. This release leaves the inherited `VERSION` and historical FaultDA evidence untouched; `1.0.0` names this research subsystem's first engineering release.

- [Research draft](PAPER_DRAFT.md): proposed measurement question and carefully bounded retrospective development audit.
- [Reset protocol](RESET_PROTOCOL.md): operational definitions, independence gates, controls, three-week decision rule, and resource limits.

The scientific status remains **HOLD**. A positive development pilot would only justify designing a separate held-out study; a negative or non-distinct result means keeping FaultDA-Bench as engineering infrastructure and stopping expansion of the current research claim.
