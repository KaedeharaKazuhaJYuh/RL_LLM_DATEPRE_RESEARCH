# FaultDA-Bench

**面向数据分析 Agent 的可靠性评测与研究基础设施。**

当前研究主张仍处于 **HOLD**：已有工程结果和开发实验，尚未证明跨任务稳定的独立科研增量。

当前研究版本：`1.1.05` · 当前研究线：`agent-eval-reliability-reset` · 历史基准：`0.5.66-dev`。
<!-- inherited-release: V5.0.15-beta.2 -->

## 项目在做什么

项目研究 Agent 在分析数据、使用工具和处理故障时的可靠性。环境保留工具动作、持久状态与副作用，并区分最终结果正确、安全完成、升级及状态未知。历史 V4/V5 也包含 DeepSeek 训练对照、可选 C++ 计算内核和 Go 实验调度。

## 目前的结论

- **可靠性评测：**在单一开发环境中，终态正确与符合协议地安全完成可能不同；已有数据不足以推断跨任务发生率。[终止分类](research/reliability_reset/TERMINAL_TAXONOMY.md)
- **验证成本：**0.5.66 是 24 个已见 profile 的离线仿真，使用自建成本模型；历史字段 `min_fixed_r` 仅对 `F`、`F_size`、`F_hist` 三族取最小，不能解释为所有固定规则的最小值。扩大规则族会改变自适应价值的估计；结果不能直接推广到真实任务。[0.5.66 报告](faultda_bench/reports/RELEASE_0566.md) · [0.5.65 报告](faultda_bench/reports/RELEASE_0565.md)
- **外部基准：**在 AppWorld 训练集的六个场景试跑四个模型；本地 SmolLM 的五个场景受输入上限截断，结果不能作为等预算排名。尚无原生评分通过的运行，独立副作用标签和强规则仍待完成。[试跑结果与成本](research/reliability_reset/APPWORLD_PILOT_115.md)
- **模型训练：**历史实验尚未建立稳定的 RL 优势；不同任务、预算和评分不能合并成一个排行榜。[项目历史](docs/PROJECT_HISTORY.md)

## 从哪里开始

| 目的 | 入口 |
| --- | --- |
| 查看当前研究、评估回应和试点 | [Reliability Reset](research/reliability_reset/README.md) |
| 查看基准组件、协议和证据 | [FaultDA 组件索引](faultda_bench/README.md) |
| 查找任务、数据、测试及早期报告 | [任务](tasks/) · [数据](data/) · [测试](tests/) · [历史报告](reports/) |
| 离线复核与运行历史实验 | [复现指南](docs/REPRODUCIBILITY.md) |
| 查找分支、文件与历史阶段 | [分支与文档导航](docs/BRANCHES.md) · [项目历史](docs/PROJECT_HISTORY.md) |
| 查看版本记录 | [仓库更新记录](CHANGELOG.md) · [研究线更新记录](research/reliability_reset/CHANGELOG.md) |

## 当前离线检查

```sh
python -m scripts.release_version --check
python -m research.reliability_reset.terminal_taxonomy
python -m faultda_bench.ci565
```

这些命令检查版本、终止分类和冻结证据，不能单独证明模型能力或独立科研结论。完整测试及历史命令见[复现指南](docs/REPRODUCIBILITY.md)。
