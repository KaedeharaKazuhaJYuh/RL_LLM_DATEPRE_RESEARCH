# Ablation study

The runner supports a controlled comparison between raw LLM action selection and LLM action selection with benchmark contract protection.

Protected DeepSeek:

```powershell
py scripts/run_matrix.py --methods llm --seeds 1,2,3,4,5
```

Raw DeepSeek:

```powershell
py scripts/run_matrix.py --methods llm --seeds 1,2,3,4,5 --raw-llm
```

Use separate output folders or rename the raw files before aggregation so the two conditions are not mixed. Compare pass rate, mean score, tool calls, and failure types.

