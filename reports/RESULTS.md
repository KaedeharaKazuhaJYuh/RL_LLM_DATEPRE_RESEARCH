# Current results

`final_comparison.json` records the current comparison status. The Verifier now checks both `gold.answer` and `gold.expected`, rejects missing answers, and still validates task contracts and reference outputs.

The rechecked local Rule Router baseline completes 50/50 tasks with a mean score of 0.9675 and one tool call per task. The first genuine Bandit run (seed 7, without contract protection) completes 19/50 tasks, with a mean score of 0.5740 and 1.24 tool calls. This is a useful diagnostic result: exploration and reward updates are active, but the Bandit is not yet competitive.

The corrected single-seed DeepSeek run completes 41/50 tasks (82.0%), with a mean score of 0.8595 and one tool call per task. The nine failures are T03–T11. Their traces show that the model often selected `task_analysis` or `profile_schema` for tasks that require a specific cleaning or counting tool. This is the first reliable error pattern to address.

The corrected five-seed raw DeepSeek matrix completes 192/250 tasks, for a mean pass rate of 76.8% (sample standard deviation 3.03 percentage points), mean score 0.8271 (standard deviation 0.0184), and mean tool calls 1.048 (standard deviation 0.0179). The per-seed results are in `reports/llm_raw_seed_summary.json`.

After enabling the task-level action mask, DeepSeek completes 50/50 tasks (100.0%), with a mean score of 0.9675 and one tool call per task. This is a controlled ablation showing that constraining the candidate action set removes the observed T03–T11 routing failures. It is not evidence that the underlying model has learned a better policy; the mask supplies task-specific prior knowledge.

The five-seed masked matrix confirms the same pattern: 250/250 tasks pass, with pass-rate standard deviation 0.0, mean score 0.9675 (standard deviation 0.0), and mean tool calls 1.00 (standard deviation 0.0). This stability is useful for the ablation, but the current mask is derived from task-level knowledge and should not be treated as a learned policy.

The earlier 250-task DeepSeek figures remain listed for traceability, but they were generated before the new `gold.expected` check and should be treated as superseded process records, not final paper results.

## Next experiment

Use the corrected raw and masked five-seed matrices as the current DeepSeek ablation. A schema-driven contract mask is now implemented: each task declares required capabilities, which are translated into actions and intersected with `allowed_tools`. The next experiment is to run this condition across five seeds and compare it with raw and the legacy task mask. Keep every constrained condition labeled as an ablation, not as an unconstrained LLM result.

