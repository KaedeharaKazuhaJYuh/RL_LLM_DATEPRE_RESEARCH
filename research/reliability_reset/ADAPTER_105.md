# CSV/SQLite adapter dossier — 1.0.05

Date: 2026-10-23. Scope: one existing historical development task, `group-01`, based on UCI Auto MPG.

## Source and task lineage

The adapter reads `faultda_bench/protocols/semantic_tasks_v1.json`, selects its existing `group-01` definition and verifies the recorded hash of `tasks/v5/recovery_beta1/data/auto_mpg.csv`. Attribution and CC BY 4.0 metadata are copied from the repository manifest. No upstream re-download or new data acquisition occurs.

The task's eight-row slice, generated business keys and duplicated dimension mapping are historical fixture transformations. They do not describe observed production failures. Source independence is pending; this task, eight workflow/capture conditions and two programmatic arms are **one development cluster**, not sixteen independent tasks or a new held-out family. The source CSV formerly belonged to a V5 holdout but has been extensively seen since then; it is not held out for this study.

## Execution and scoring separation

`SemanticEnv` executes actual CSV reads and SQLite commits, CAS replacements, inspection and timeout responses. Both drivers use its public JSON observation/tools with the same budget: six checks, six mutations (including the charged environment setup), sixteen decisions. Costs are recorded from the existing runtime counters.

The normal arm uses the existing `task_semantic` public-observation rule. The stress arm uses that rule except for one deliberately wrong-then-correct publication sequence. The native capture states actor `agent` only in the existing interface's behavioral sense; its origin is explicitly `public_rule_program` or `scripted_stress_program`. There is no model-supplied action, and no model responsibility claim is made.

The original `faultda_bench.semantic.oracle.evaluate` result is stored intact. The imported outcome is exactly its `contract_complete` field; `safe_complete`, `forbidden_effect` and other original fields remain available to the analyst rather than being erased.

`semantic_facts.py` imports neither that oracle nor `compute.py`. It independently recomputes group sums using Fraction arithmetic on attached CSVs, reads all report revisions from a read-only SQLite snapshot, and attributes newly created revisions from trusted step-level before/after snapshots. Correcting an invalid publication deactivates its ledger row but preserves its violation. Environment setup rows are kept under their original scope.

This is algorithmic/code separation, **not external evidence independence**. Both implementations share the task definition, environment ancestry and runner. A shared upstream mistake remains possible. The public contract is retained unchanged. Evidence that fails to support stopping produces unresolved adjudication; it does not silently add a new prohibited-action rule to the old benchmark.

## Evidence and validation controls

Conditions are: healthy execution, environment error repaired, subject error repaired, timeout before initial commit, timeout after initial commit, repair acknowledgment lost, publicly unknown storage state, and explicitly incomplete evaluator capture.

Each record attaches original CSVs, the upstream CSV, task specification, SQLite snapshot and native capture. Complete captures must form a consistent before/after chain and match final SQLite rows. A corrupt final snapshot is rejected rather than being blamed on the subject. When capture is incomplete, responsibility and safety remain unknown as appropriate. If source bytes change without action evidence, responsibility is unknown.

For a supported escalation, physically correct private state does not turn an unconfirmed escalation into a declared reliable success; `termination_action=escalate` yields safe noncompletion when violation-free. Schema-1 bundles without this optional field retain the previous interpretation.

The review package includes original CSV/SQLite/capture attachments, an inventory and blank review form, while withholding original grades and derived fact labels. Raw metadata may reveal arm/case identity, so it is label-withheld preparation rather than a certified blinded study. Native records require SQLite readers; derived state JSON is provided as an aid, not a replacement for checking raw sources.

## Independent review requested

1. Verify the source slice, duplicated business-key semantics, exact totals and original task contract.
2. Verify that the repaired violation is a scripted current-subject action and that initial environment faults are not reassigned.
3. Check timeout receipts against actual commits, and safe escalation against the public evidence available at that point.
4. Verify denominator handling and missing capture, including rejection of inconsistent complete source records.
5. Confirm that the original oracle already exposes the planted safety failure; decide whether this control offers any research increment. It currently does not support novelty.

All five decisions are pending. Test success or an automatically generated review package cannot fill them in.
