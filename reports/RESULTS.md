# Current results

`final_comparison.json` records the current comparison status. The Verifier now checks both `gold.answer` and `gold.expected`, rejects missing answers, and still validates task contracts and reference outputs.

The rechecked local Rule Router baseline completes 50/50 tasks with a mean score of 0.9675 and one tool call per task. The first genuine Bandit run (seed 7, without contract protection) completes 19/50 tasks, with a mean score of 0.5740 and 1.24 tool calls. This is a useful diagnostic result: exploration and reward updates are active, but the Bandit is not yet competitive.

The corrected single-seed DeepSeek run completes 41/50 tasks (82.0%), with a mean score of 0.8595 and one tool call per task. The nine failures are T03–T11. Their traces show that the model often selected `task_analysis` or `profile_schema` for tasks that require a specific cleaning or counting tool. This is the first reliable error pattern to address.

The earlier 250-task DeepSeek figures remain listed for traceability, but they were generated before the new `gold.expected` check and should be treated as superseded process records, not final paper results.

## Next experiment

Use the corrected 50-task run as the current DeepSeek baseline. Next, add an action mask or task-specific tool contract for T01–T11, rerun the same 50 tasks, and then repeat across five seeds if the API budget is acceptable. Compare raw routing, contract-protected routing, Rule Router, and the updated Bandit using the same task split and report mean and standard deviation.

