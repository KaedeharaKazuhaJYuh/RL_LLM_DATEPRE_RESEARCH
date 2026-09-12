# Value-perturbation protocol

## Why a new artifact bundle is required

Changing CSV values invalidates the original expected answers and reference outputs. This evaluation therefore does not reuse those artifacts. `scripts/make_value_variant.py` deterministically creates transformed CSV files, aligned tasks, stage-one gold answers, and T12-T50 reference outputs together.

## value_v1 transformation

- `sample.csv`: transform every `revenue` value as `1.15 * revenue + 7`.
- `churn.csv`: increment `tenure_months` by one and transform `monthly_fee` as `1.10 * monthly_fee + 3`.
- `students.csv`: add 0.5 to `study_hours` and add 2 to `score`.

The split preserves row order, column names, task prompts, task IDs, operation-family contracts, allowed tools, and budgets. It isolates sensitivity to the numerical contents of the data rather than to schema changes or language changes.

## Valid comparison

Every value_v1 run must use all three aligned paths:

```text
tasks/variants/value_v1/tasks.jsonl
tasks/variants/value_v1/gold_answers.json
tasks/variants/value_v1/reference_outputs.json
```

The first check is the deterministic Rule Router. Raw LLM and operation-family contract conditions will then be evaluated using the same aligned bundle. The contract result remains an ablation, not an unconstrained-policy result.

