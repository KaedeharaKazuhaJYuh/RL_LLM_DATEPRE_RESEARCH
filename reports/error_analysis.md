# DeepSeek failure analysis

The first five-seed run contained 12 failed task instances out of 250. All failures were verifier contract failures; none were network, authentication, illegal-tool, or budget failures.

The dominant pattern was premature or mismatched action selection. In several cases DeepSeek selected `profile_schema` for a task that required the later `task_analysis` action; in other cases it selected `stop` without producing an analysis result. One statistics task made an initial aggregate call and then switched to schema profiling.

The mitigation is a contract-protection fallback in `experiments/run.py`: for T12-T50, an LLM action that is not `task_analysis` is replaced with `task_analysis`. This preserves LLM selection for the early tool-selection tasks while preventing an invalid terminal action in the benchmark groups that require structured analysis output.

This fallback should be evaluated as a separate ablation in the final paper: `LLM` versus `LLM + contract protection`.

