# FaultDA-Bench 组件索引

项目定位、当前结果和限制见[仓库首页](../README.md)；操作步骤见[复现指南](../docs/REPRODUCIBILITY.md)。当前开发版本为 `0.2.05-dev`。

## 实现分层

| 组件 | 职责 |
| --- | --- |
| [clarity/](clarity/) | 跨来源任务、契约说明对照、事后诊断及证据复核 |
| [semantic/](semantic/) | CSV 计算、持久报告、暂存/CAS 修复、独立 oracle 与基线 |
| [protocols/](protocols/) | 冻结任务、来源引用、许可、行选择和派生说明 |
| [reports/](reports/) | 分条件结果、API 协议、压缩轨迹和人工审阅表 |
| 根目录 P0 模块 | 原始状态与非幂等副作用探针，保留原有语义 |

策略只接收公开 JSON 观察；环境对象和私有参考验证留在可信 runner。当前没有针对任意恶意本地代码的 OS 隔离保证。

## 协议与证据

| 阶段 | 实施协议 | 结果报告 |
| --- | --- | --- |
| P0 `0.1.0-p0` | [状态与副作用](docs/P0_IMPLEMENTATION_PROTOCOL.md) | [84 次探针](reports/P0_START.md) |
| `0.2.0-dev` | [联合故障与语义修复](docs/SEMANTIC_V1_PROTOCOL.md) | [首个开发版本](reports/SEMANTIC_V1_RELEASE.md) |
| `0.2.05-dev` | [契约诊断与来源交叉](docs/CLARITY_V2_PROTOCOL.md) | [当前结果](reports/CLARITY_V2_RELEASE.md) |

总体研究约束见[研究协议 v2](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md)；[原始 v1](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V1.md)和[相关工作复核](docs/OVERLAP_AUDIT_2026_10_09.md)保留。不同阶段的指标和样本不能混池汇总。

[24 题人工审阅表](reports/CROSS_SOURCE_REVIEW.md)目前仍待人工填写；程序测试不等于独立人工认可。历史 source_id 注册表包含别名和派生来源，不能把其条目数当独立数据集数量。
