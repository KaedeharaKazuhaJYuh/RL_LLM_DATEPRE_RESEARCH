# Reliability Reset 1.0.10 — engineering review corrections

Date: 2026-10-23. Branch: `agent-eval-reliability-reset`.

## Scope and received review

The user supplied a sixteen-row review CSV and a review memo. The memo explicitly identifies its author as an agent rather than a human. It is registered as external-agent technical feedback; independent human/scientific review remains pending. Original bytes and all disagreements are retained. See `REVIEW_RESPONSE_110.md`.

## Corrected engineering behavior

- `snapshot_correct` records the physical snapshot assessment separately. `terminal_correct` and `termination_action` require complete capture with a matching final stop/escalate action; missing termination evidence propagates null. Original oracle grades remain untouched.
- Input hash consistency is an assessment-integrity monitor, not a subject-writable prohibition. Invalid source bindings prevent supported numeric conclusions and do not create an attributed subject violation.
- Environment initialization includes failed attempts/feedback, distinct from committed rows. Subject scope uses `subject` plus `programmatic_driver` kind and explicit program origin.
- A declared development derivative changes one v2 value, and adds duplicate, wrong-version, incorrect-final-state and missing-value controls. The historical task manifest and 1.0.05 outputs are not changed.
- Agreement reporting separates classes, unknowns, behavior signatures and executed controls. No independent sample size or population accuracy is inferred.
- A normalized first-pass view removes explicit condition/arm names and machine-derived labels. The original/derived source package is for unblinded phase-two verification. Transformations and private mappings remain auditable; scientific blinding validation is pending.

## Reproduce

```powershell
python -m research.reliability_reset.semantic_adapter work/reliability-reset-1.0.10/development
python -m research.reliability_reset.audit work/reliability-reset-1.0.10/development/bundle.json --output work/reliability-reset-1.0.10/audit --review-output work/reliability-reset-1.0.10/phase-two
python -m research.reliability_reset.review_views work/reliability-reset-1.0.10/development/bundle.json --output work/reliability-reset-1.0.10/first-pass --mapping work/reliability-reset-1.0.10/audit/private-first-pass-map.json
python -m unittest tests.test_reliability_reset tests.test_reliability_reset_adapter tests.test_faultda_semantic tests.test_faultda_vericost565_release -v
```

Use new output directories; existing evidence is not overwritten. The first-pass package must not contain the private map or be supplied alongside phase-two labels during initial review. CSV/SQLite bytes are preserved, while JSON identifier normalization is recorded; this is a preparation tool, not an independent blinding approval.

Validation completed: 71 relevant tests passed without skips in 11.193 seconds; release metadata, compilation and whitespace checks passed. A fresh full-repository run was not performed for this increment. Final local artifacts are under `work/reliability-reset-1.0.10/final/`, including separate first-pass and phase-two archives; private mapping is excluded from both.

The 24 executions contain 11 observed behavior signatures within one family. Legacy-relative violation checks have four positives, eighteen negatives and two unknowns. Captured terminal correctness is comparable on 22 records and unknown on two; physical snapshot correctness remains separately comparable on all 24, including one incorrect final snapshot. Both declared subject prohibitions have positive controls. These counts establish engineering agreement on designed controls, not independent accuracy or an empirical sample of model behavior. Exact records and hashes are in `VALIDATION_110.json`.

## Research decision

`SYSTEMS_CONTEXT_110.md` adds foundational database/distributed-system context to the prior Agent literature screen. No new model run, dataset acquisition, held-out construction, recovery mechanism or scientific increment is claimed. The existing broad paper claim remains NO-GO and scientific HOLD; no paid calls are approved. Further engineering verification does not restart the paper route automatically.

## Follow-up audit findings (queued, not fixed in this checkpoint)

The subsequent local audit reproduced an attribution defect: incomplete captures skip continuity validation of their retained prefix, so inconsistent before/after rows can incorrectly attribute an environment publication to the subject. The current normalized-view implementation also matches metadata names recursively, which can alter business payload fields using the same names. These limitations require a separate correction and source-to-view fidelity checks before the new first-pass workflow is used for substantive independent adjudication. The 1.0.10 source hashes, original results and test counts remain frozen; passing designed controls does not resolve these newly identified cases.
