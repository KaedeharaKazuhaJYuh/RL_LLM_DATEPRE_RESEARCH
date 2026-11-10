# FaultDA-Bench

**面向数据分析 Agent 的可靠性评测与研究基础设施。**

当前研究主张仍处于 **HOLD**：已有工程结果和开发实验，尚未证明跨任务稳定的独立科研增量。

当前研究版本：`1.1.20` · 当前工作分支：`comm-telemetry-crossday-load-audit-2026-11-09` · 历史基准：`FaultDA-Bench 0.5.66-dev`。
<!-- inherited-release: V5.0.15-beta.2 -->

当前研究方向是**真实通信流量上的少标签半监督持续学习**，重点检验 SNN 包事件时间建模在时间漂移和灾难性遗忘下是否有独立作用。当前机制与证据状态见[研究计划](research/reliability_reset/COMMUNICATION_TELEMETRY_CONTINUAL_LEARNING_RESEARCH_PLAN_2026_11_09.md)。

## 当前研究主线

研究问题：在严格时间前推的真实 ISP 流量中，每期标签有限、无标签流量充足时，怎样利用新数据适应业务变化，同时保持过去学到的服务类别？SNN 的包事件时序编码是否能在同样的标签、计算和记忆预算下带来额外收益？

当前算法候选是**稀疏标签锚定的分视图三态更新门**：分别观察包事件和流级摘要的变化，并用延迟释放的少量标签判断预测损害是“有证据支持”“有证据支持无实质损害”还是“证据不足”；只有损害得到标签支持且伪标签可靠性达标，才用无标签数据更新 SNN 时间分支。该机制尚未实现，独立贡献仍待实验检验。

CESNET-TLS-Year22 XS 归档已完成全表读取：10,000,000 条 flow、357 个日期表，八个官方缺失日期均匹配；逐日×服务类别 census、ISO 年—周切分清单和 45 列输入字段契约已生成。此为数据支持审计，不是模型结果；ANN/SNN 尚未训练，研究结论仍为 HOLD。详见[协议 v0.2](research/reliability_reset/experiments/communication_telemetry/COMMUNICATION_TELEMETRY_EVENT_DRIFT_GATED_SSL_PROTOCOL_V0_2_2026_11_10.md)、[数据 census](research/reliability_reset/experiments/communication_telemetry/CESNET_TLS_YEAR22_XS_CENSUS_2026_11_10.json)、[输入字段契约](research/reliability_reset/experiments/communication_telemetry/CESNET_TLS_YEAR22_XS_FEATURE_CONTRACT_2026_11_10.md)和[数据契约审计](research/reliability_reset/experiments/communication_telemetry/CESNET_TLS_YEAR22_CONTINUAL_DATA_CONTRACT_AUDIT_2026_11_09.md)。

FaultDA-Bench、AppWorld 试点、NIKA 配对及 V4/V5 的训练、C++ 与 Go 组件是历史基础设施和研究记录，不代表当前并行推进多条研究路线。

## 历史项目与证据边界

- **可靠性评测：**在单一开发环境中，终态正确与符合协议地安全完成可能不同；已有数据不足以推断跨任务发生率。[终止分类](research/reliability_reset/TERMINAL_TAXONOMY.md)
- **验证成本：**0.5.66 是 24 个已见 profile 的离线仿真，使用自建成本模型；历史字段 `min_fixed_r` 仅对 `F`、`F_size`、`F_hist` 三族取最小，不能解释为所有固定规则的最小值。扩大规则族会改变自适应价值的估计；结果不能直接推广到真实任务。[0.5.66 报告](faultda_bench/reports/RELEASE_0566.md) · [0.5.65 报告](faultda_bench/reports/RELEASE_0565.md)
- **外部基准：**本项目在 AppWorld 0.2.0 训练集的六个场景试跑四个模型，尚无原生评分通过的运行；SmolLM 的五个场景受输入上限截断，不能作为等预算排名。[试跑结果与成本](research/reliability_reset/APPWORLD_PILOT_115.md) · 对官方 0.1.0 四条历史轨迹的独立盲审在已检查范围内未形成原生评分漏检的证据链；直接重放暴露了归档状态元数据不足，同类零计数问题已有上游报告。[审阅、重放与查新](research/reliability_reset/APPWORLD_REVIEW_2026_11_02.md)
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
