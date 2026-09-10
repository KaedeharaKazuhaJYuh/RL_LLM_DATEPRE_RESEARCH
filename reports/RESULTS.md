# Current results

`final_comparison.json` records the current comparison status. The Verifier now checks both `gold.answer` and `gold.expected`, rejects missing answers, and still validates task contracts and reference outputs.

The rechecked local Rule Router baseline completes 50/50 tasks with a mean score of 0.9675 and one tool call per task. The first genuine Bandit run (seed 7, without contract protection) completes 19/50 tasks, with a mean score of 0.5740 and 1.24 tool calls. This is a useful diagnostic result: exploration and reward updates are active, but the Bandit is not yet competitive.

The earlier 250-task DeepSeek figures remain listed for traceability, but they are provisional because they were generated before the new `gold.expected` check. They must be rerun before being used as final paper results.

## Next experiment

Run DeepSeek on one 50-task seed with the corrected Verifier, then repeat across five seeds if the API budget is acceptable. Compare raw routing, contract-protected routing, Rule Router, and the updated Bandit using the same task split and report mean and standard deviation.

