# Data-aware value-perturbation results

## Conditions

All conditions use `dataset_profile_v1_read_only`: a read-only ten-dimensional aggregate CSV state before action selection. The value_v1 runs use transformed CSVs and regenerated gold/reference artifacts. Each condition contains run-0 plus four independently labelled follow-up API calls.

| Data | Method | Passed | Pass rate | Mean score | Mean tool calls |
|---|---|---:|---:|---:|---:|
| Original | Raw LLM | 147 / 250 | 58.8% ± 1.79 pp | 0.7186 ± 0.0111 | 1.068 ± 0.0303 |
| value_v1 | Raw LLM | 155 / 250 | 62.0% ± 4.69 pp | 0.7382 ± 0.0283 | 1.052 ± 0.0179 |
| Original | Contract mask | 245 / 250 | 98.0% ± 0.0 pp | 0.9555 ± 0.0 | 1.000 ± 0.0 |
| value_v1 | Contract mask | 241 / 250 | 96.4% ± 1.67 pp | 0.9459 ± 0.0100 | 1.000 ± 0.0 |

The numbered runs are independent calls, not provider-controlled random seeds.

## Interpretation

The 3.2-point raw difference between original and value_v1 is smaller than the observed variation in the value_v1 raw condition. I therefore do not interpret it as a stable numerical-data effect. The operation-family contract stays high but drops modestly on value_v1, driven by within-family choices rather than verifier misalignment.

## Recurring errors

- Original contract: T11 fails in all five runs.
- value_v1 contract: T11 fails in all five, T03 fails in three, and T04 fails once.
- Raw conditions have broader recurring routing errors and must not be compared directly with text-only raw runs because the data-aware profile changes their LLM input.

## Next step

The reproducible data-aware state/action/reward logs are now sufficient to improve the Contextual Bandit and evaluate it against Rule Router under matched observed state. A schema-perturbation benchmark is deferred until tool remapping and independent verifier regeneration are implemented.

