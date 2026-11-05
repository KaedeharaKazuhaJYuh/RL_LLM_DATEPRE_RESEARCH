# FaultDA-Bench 组件索引

**0.5.66-dev** 是该基准线的离线检查点。其价格扫描基于已见开发数据与有限仿真，不能直接解释为真实 Agent 的价格弹性或跨任务泛化。[本版报告](reports/RELEASE_0566.md) · [0.5.65 报告](reports/RELEASE_0565.md) · [研究状态](../research/reliability_reset/README.md)

## 组件

| 路径 | 作用 |
| --- | --- |
| [semantic/](semantic/) | CSV 计算、报告状态、分析契约与独立验证 |
| [vericost565/](vericost565/) | 验证成本环境、有限状态 DP 和规则／学习策略对照 |
| [stats560/](stats560/) · [termination555/](termination555/) | 已有结果的统计描述、终止及证据绑定 |
| [acceptance/](acceptance/) · [current_evidence/](current_evidence/) | 冻结证据及当前验收入口 |
| [protocols/](protocols/) · [docs/](docs/) | 任务协议、来源和研究设计 |
| [reports/](reports/) | 按阶段保留的结果、审阅记录和证据 |

其他历史模块保留在本目录；需要追查具体版本时，从[项目历史](../docs/PROJECT_HISTORY.md)的协议与组件索引进入。当前参考资料见[跨分支评估](docs/CROSS_BRANCH_ASSESSMENT_2026_10_27.md)和[近邻查新](docs/NOVELTY_AUDIT_2026_10_27.md)。

## 证据边界

部分任务与规则曾接受人工技术复审，范围以[审阅记录](reports/SCIENTIFIC_REVIEW_24.md)为准；程序测试不等于独立科学验收。旧分数、任务契约和冻结证据保持原路径，不同阶段的数据与指标不能混池。策略只能使用公开观察；不要把私有参考结果当作可用工具。
