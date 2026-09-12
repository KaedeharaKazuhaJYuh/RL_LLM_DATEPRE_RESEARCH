# Wording robustness: run-0 analysis

## Controlled condition

`wording_v1` adds a natural-language instruction wrapper to every task. Task identifiers, CSV paths, contracts, allowed tools, budgets, gold answers, and reference outputs are unchanged. Therefore changes in this comparison can be attributed to the task instruction surface form within this prototype, subject to normal API-call variability.

## Single-call precheck

| Condition | Passed | Pass rate | Mean score | Mean tool calls |
|---|---:|---:|---:|---:|
| Raw LLM | 31 / 50 | 62.0% | 0.7385 | 1.04 |
| Operation-family contract mask | 48 / 50 | 96.0% | 0.9435 | 1.00 |

The matching original-task one-run checks are 41/50 raw and 49/50 contract. This makes the raw reduction worth investigating, but one call is insufficient to quantify a confidence interval or claim a stable causal effect.

## Error pattern

Raw routing fails 19 tasks. Early failures include T04 (generic analysis instead of deduplication), T08 (generic analysis instead of outlier handling), T09 (missingness profiling instead of category normalization), and T11 (schema profiling instead of aggregation). Several later tasks fail because, without contract protection, the chosen action does not satisfy the required analysis/reference fields.

The contract condition limits failures to T03 and T11. T03 chooses schema profiling where category counting is needed; both actions remain inside the deliberately broad overview family. T11 chooses generic task analysis where the expected answer requires monthly aggregation. These are retained as genuine within-family routing errors.

## Decision

Do not refine contracts using the exact task answer. Repeat both raw and contract wording_v1 conditions before reporting a robustness result. Report all constrained results as ablations.

