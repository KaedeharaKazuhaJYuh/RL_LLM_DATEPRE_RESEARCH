# 实验结果

运行器会把逐任务结果保存为 JSONL。用下面的命令汇总多个方法：

```powershell
py -m experiments.aggregate reports/rule_results.jsonl reports/bandit_results.jsonl reports/deepseek_results.jsonl
```

输出指标包括任务数、通过数、通过率、平均 Verifier 分数和平均工具调用次数。正式实验还应按 seed 重复，并报告均值与标准差。

