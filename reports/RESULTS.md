# Current results

`final_comparison.json` records the current comparison status. The Verifier now checks both `gold.answer` and `gold.expected`, rejects missing answers, and still validates task contracts and reference outputs.

The rechecked local Rule Router baseline completes 50/50 tasks with a mean score of 0.9675 and one tool call per task. The first genuine Bandit run (seed 7, without contract protection) completes 19/50 tasks, with a mean score of 0.5740 and 1.24 tool calls. This is a useful diagnostic result: exploration and reward updates are active, but the Bandit is not yet competitive.

The corrected single-seed DeepSeek run completes 41/50 tasks (82.0%), with a mean score of 0.8595 and one tool call per task. The nine failures are T03–T11. Their traces show that the model often selected `task_analysis` or `profile_schema` for tasks that require a specific cleaning or counting tool. This is the first reliable error pattern to address.

The corrected five-run raw DeepSeek matrix completes 192/250 tasks, for a mean pass rate of 76.8% (sample standard deviation 3.03 percentage points), mean score 0.8271 (standard deviation 0.0184), and mean tool calls 1.048 (standard deviation 0.0179). These are independent API repetitions stored with legacy seed labels; they are not provider-controlled random seeds. The per-run results are in `reports/llm_raw_seed_summary.json`.

After enabling the task-level action mask, DeepSeek completes 50/50 tasks (100.0%), with a mean score of 0.9675 and one tool call per task. This is a controlled ablation showing that constraining the candidate action set removes the observed T03–T11 routing failures. It is not evidence that the underlying model has learned a better policy; the mask supplies task-specific prior knowledge.

The five-run masked matrix confirms the same pattern: 250/250 tasks pass, with pass-rate standard deviation 0.0, mean score 0.9675 (standard deviation 0.0), and mean tool calls 1.00 (standard deviation 0.0). These are independent API repetitions stored with legacy seed labels. This stability is useful for the ablation, but the current mask is derived from task-level knowledge and should not be treated as a learned policy.

The operation-family contract precheck completes 49/50 tasks (98.0%), with a mean score of 0.9555 and one tool call per task. The single failure is T11: the aggregation contract permits both `aggregate` and `task_analysis`, and the model chose `task_analysis` even though T11 requires the dedicated monthly aggregate tool. This is retained as a meaningful routing error; the contract is intentionally not narrowed to one correct action.

The five-run operation-family contract matrix completes 245/250 tasks. Its mean pass rate is 98.0% (sample standard deviation 0.0), mean score is 0.9555 (standard deviation 0.0), and mean tool calls are 1.00 (standard deviation 0.0). Every repetition failed only T11 with the same `task_analysis` selection; after excluding run metadata, the task-level result records are identical. These are repeated API calls labelled with legacy seed-style filenames, not provider-controlled seeds. The result demonstrates stable behaviour for this prompt and condition, but it does not establish robustness to prompt, dataset, or task-distribution changes.

The earlier 250-task DeepSeek figures remain listed for traceability, but they were generated before the new `gold.expected` check and should be treated as superseded process records, not final paper results.

## Next experiment

Use the corrected raw, legacy task-mask, and operation-family contract-mask matrices as the current DeepSeek ablations. The schema-driven contract mask is implemented with broad operation families, rather than a single correct action: each task declares a family such as overview, cleaning, or aggregation; the runtime translates it into candidate actions and intersects them with `allowed_tools`. The immediate next experiment should perturb task wording and table values while preserving contracts, then rerun the raw and contract conditions. Keep every constrained condition labeled as an ablation, not as an unconstrained LLM result.

