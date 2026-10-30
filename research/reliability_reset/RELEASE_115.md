# Reliability Reset 1.0.15 — partial-capture attribution and review fidelity

Date: 2026-10-24. Branch: `agent-eval-reliability-reset`. Base checkpoint: `cd717b0` (1.0.10).

## Fixed defects

1. **Malformed partial capture could invent responsibility.** In 1.0.10, continuity was checked only when capture was complete. A modified incomplete `inspect` fragment with an empty before-state and an invented second after-row was accepted and attributed an environment publication/duplicate to the subject. The extractor now validates every retained step before attribution. This adapter supports a contiguous prefix from zero, immutable append-only publications, monotonic unique revisions and one-way deactivation. Read-only actions cannot mutate the ledger and no action follows a captured stop/escalate. Inconsistent evidence is rejected rather than scored as a subject violation.
2. **Recursive identity normalization could alter application data.** Fields named `origin`, `run_id`, `driver_origin`, `reported_terminal` or `capture_limitation` were transformed even inside business payloads. The exporter now changes only explicit native capture-envelope identity paths and omits only the two runner-only top-level fields. All nested business values remain unchanged; contract, public input, specification, CSVs and SQLite retain original bytes.

Valid incomplete captures still yield unknown terminal correctness/action/support. Already-proven subject harm remains confirmed even after an uncaptured repair; a correct final snapshot does not reconstruct the missing actions. Unknown actor provenance for a demonstrably harmless row is not itself a confirmed unsafe effect.

## Review export and verification

The separate `review_fidelity.py` verifier does not invoke the exporter transformation. It reverses permitted identity substitutions and compares all remaining typed JSON values with the bound native source, then byte-compares every other source. Source/mapping, case and file coverage are checked independently of the view's hash inventory. Regenerating that inventory does not make changed payloads or CSV bytes acceptable. Missing required sources, duplicate attachment basenames, extra answer files and dropped review rows are rejected. Filled annotations remain permissible.

Exports are staged and verified before the finished view is exposed. The private map uses schema 2 and binds the source bundle plus inventory; bundle schema 1 is unchanged. Old 1.0.10 views/maps are preserved and not silently migrated. The new package is a derivative for local review preparation, not a certified blinded study. Neither its hashes nor this same-project verifier authenticate the source producer or replace independent adjudication.

## Reproduce

Use fresh directories; these commands do not contact a model provider:

```powershell
python -m research.reliability_reset.semantic_adapter work/reset115-development
python -m research.reliability_reset.audit work/reset115-development/bundle.json --output work/reset115-audit --review-output work/reset115-phase-two
python -m research.reliability_reset.review_views work/reset115-development/bundle.json --output work/reset115-first-pass --mapping work/reset115-audit/private-first-pass-map.json
python -m research.reliability_reset.review_views work/reset115-development/bundle.json --output work/reset115-first-pass --mapping work/reset115-audit/private-first-pass-map.json --verify
python -m unittest tests.test_reliability_reset tests.test_reliability_reset_adapter tests.test_reliability_reset_fidelity tests.test_faultda_semantic tests.test_faultda_vericost565_release -v
```

Validation results and artifact hashes are recorded in [VALIDATION_115.json](VALIDATION_115.json). These are designed engineering controls from one already-seen lineage; agreement is relative to supplied legacy evidence, not independent accuracy or cross-task model performance. No new full-repository run is claimed for this increment.

The final selected regression run passed 87 tests without failures or skips in 55.005 seconds. Sixteen additional tests cover partial-history attribution and source/view fidelity. Release metadata, compilation and whitespace checks passed. Re-extraction of all 24 frozen 1.0.10 records reproduced their supplied facts and states exactly; their bundle, audit and two archives retained the recorded hashes. The rebuilt 1.0.15 controls retain 11 behavior signatures, legacy-relative violation agreement of four positives/eighteen negatives/two unknowns, and two unknown terminal assessments. These counts are unchanged engineering diagnostics.

New first-pass material has 24 cases and 192 evidence files plus instructions, inventory and a blank review form. Source comparison passed both at export and through the verification CLI. Separate first-pass and phase-two archives are under `work/reliability-reset-1.0.15/final/`; neither includes the private map. The first test run exposed an incorrect new assertion about harmless unknown-origin content; the assertion was corrected, with no production-code change required, before the final passing run.

## Review and research decision

See [GO_NO_GO_115.md](GO_NO_GO_115.md). Independent human/scientific review and validation of the review protocol remain pending. The received 1.0.05 memo remains external-agent feedback. Scientific HOLD, the current broad-claim NO-GO and zero new model/API/paid-run budget remain unchanged. This version closes specific implementation defects; it adds no recovery mechanism, new task family, model improvement or paper-level novelty.
