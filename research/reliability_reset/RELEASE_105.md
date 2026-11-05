# Reliability Reset 1.0.05 — one real workflow adapter

Date: 2026-10-23. Branch: `agent-eval-reliability-reset`.

## Delivered

- Checked the previous push at commit `6d7e6e7`: V5 verification and current evidence acceptance both completed successfully.
- Connected the existing historical `group-01` task to actual CSV/SQLite execution. Eight conditions × two explicitly programmatic arms produce sixteen engineering validation records.
- Kept the original outcome score and full oracle result, and implemented a separate Fraction/SQLite/capture fact extractor with source-chain checks.
- Added original source attachments to hash verification and review export, including CSVs, SQLite snapshot and native action capture.
- Distinguished safe escalation from declared completion and preserved unknown responsibility when evidence is missing or source changes lack action provenance.

Run commands are in the current README. The supported adapter covers one group analysis only. Time-window/version analyses and new task families require their own design and review.

## Finding and practical implication

The extractor can reproduce a known repaired-history violation: the active final report is correct, while an earlier invalid subject publication remains in the ledger. The old oracle already flags this with its safety metric. This is an engineering agreement check and provides no incremental scientific finding over the original full metric set.

Existing rule and deliberate stress controls are not model comparisons. Incomplete capture is a declared control, not an observed data-loss frequency. This release produces no RL/model improvement result or cross-task validity claim.

## Validation and decision

Final validation: 61 relevant tests passed with zero skips in 15.267 seconds, covering reset core/adapter, the existing semantic environment and release documentation. Release metadata, compilation and whitespace checks passed. The prior base commit's two CI workflows passed; a fresh full-repository run was not performed for this increment.

On the sixteen programmatic controls, terminal correctness agreed with the original oracle in all sixteen. Fourteen had settled violation status and agreed in all fourteen; two capture-loss controls remained unknown. No confirmed violation was newly detected beyond the old oracle's safety metric. These counts describe agreement on engineered controls, not independent truth or model performance.

Commands, counts and hashes are recorded in `VALIDATION_105.json`. Local output is `work/reliability-reset-1.0.05/`, including `review-sources-1.0.05.zip`. Review records remain pending. See `ADAPTER_105.md` for source/contract/actor boundaries and `GO_NO_GO_105.md` for the decision.

Engineering proceeds to independent review and candidate-design screening. Paid/live experiments remain NO-GO, scientific status HOLD. The historical FaultDA checkpoint, inherited V5 release metadata and earlier validation records remain frozen.
