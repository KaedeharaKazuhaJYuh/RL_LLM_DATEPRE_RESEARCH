# Operation-family contract-mask analysis

## Result

Five independent DeepSeek API calls were evaluated on the same 50 tasks with the operation-family contract action mask enabled at temperature 1.0. The aggregate result is 245/250 passes (98.0%), mean verifier score 0.9555, and mean tool calls 1.00. Across the five calls, the observed standard deviation of these three metrics is 0.0.

## Repeated failure

All five calls fail only **T11**. Its aggregation contract exposes two broadly valid actions, `aggregate` and `task_analysis`. The model consistently chooses `task_analysis`; the action is legal and contract-compatible, but it does not produce the expected monthly aggregate answer. The verifier therefore marks only the answer check as false.

## Interpretation

This condition is more informative than the legacy task-action mask because it supplies a broad operation family rather than the exact correct action. It nevertheless remains a constrained ablation, not an unconstrained model result. Exact agreement across the five calls shows that the current prompt/provider configuration behaves reproducibly on this fixed task set; it is not evidence of general robustness or of a learned policy.

## Next experimental decision

Retain T11 as an error case. Do not narrow its contract to a singleton action merely to increase the reported pass rate. The next evaluation should use wording and data perturbations that preserve the same contracts, and compare raw LLM routing with this operation-family contract condition.

