# Prompt-robustness results

## Question

Does an LLM data-analysis agent retain its tool-routing performance when task wording changes but the dataset, task contract, budget, gold answer, and reference output do not?

## Protocol

`tasks/variants/wording_v1.jsonl` applies one of five instruction wrappers to each of the 50 benchmark prompts. Every non-linguistic task field is preserved. DeepSeek was evaluated through five independent API calls at temperature 1.0 in two conditions: raw routing without contract protection, and operation-family contract masking. The numbered repeats are not provider-controlled random seeds.

## Results

| Dataset condition | Method | Passed | Pass rate | Mean verifier score | Mean tool calls |
|---|---|---:|---:|---:|---:|
| Original tasks | Raw LLM | 192 / 250 | 76.8% ± 3.03 pp | 0.8271 ± 0.0184 | 1.048 ± 0.0179 |
| wording_v1 | Raw LLM | 151 / 250 | 60.4% ± 5.18 pp | 0.7283 ± 0.0315 | 1.064 ± 0.0219 |
| Original tasks | Contract mask | 245 / 250 | 98.0% ± 0.0 pp | 0.9555 ± 0.0 | 1.000 ± 0.0 |
| wording_v1 | Contract mask | 245 / 250 | 98.0% ± 0.0 pp | 0.9555 ± 0.0 | 1.000 ± 0.0 |

The raw pass-rate difference between original wording and wording_v1 is 16.4 percentage points. The contract-masked condition is unchanged on this split.

## Failure analysis

Under wording_v1 raw routing, T08, T09, T26, T31, T41, and T50 fail in all five repeats. This shows that the model's raw action selection is sensitive to the wrapped task presentation. With the broad operation-family contract, every repeat fails only T11: `task_analysis` remains allowed for the aggregation family but does not return the expected monthly aggregate.

## Interpretation and boundary

This is evidence that a broad, declarative action-family constraint can stabilize routing on this prompt perturbation. It is not evidence that the LLM has learned a robust policy: the contract still supplies useful task information and is reported as an ablation. The next robustness split should change data values or schema while rebuilding independent gold/reference artifacts before evaluation.

