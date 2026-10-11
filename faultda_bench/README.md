# FaultDA-Bench 组件索引

项目定位、当前结果和限制见[仓库首页](../README.md)；操作步骤见[复现指南](../docs/REPRODUCIBILITY.md)。当前开发版本为 `0.2.35-dev`。

## 实现分层

| 组件 | 职责 |
| --- | --- |
| [allocation/](allocation/) | 固定/随机/按需检查与强规则的共同执行器负对照 |
| [acceptance/](acceptance/) | 冻结证据统一核验、原始审阅文件核对及分层验收状态 |
| [regression/](regression/) | 三段式历史归因冻结计划、完整工具/台账重放和篡改检测 |
| [decision/](decision/) | 数值语义判断、可选动作建议、正确状态退化检测及输入重放 |
| [evidence/](evidence/) | 公开事实抽取、无损历史布局对照、条件恢复与并发修订诊断 |
| [clarity/](clarity/) | 跨来源任务、契约说明对照、事后诊断及证据复核 |
| [semantic/](semantic/) | CSV 计算、持久报告、暂存/CAS 修复、独立 oracle 与基线 |
| [protocols/](protocols/) | 冻结任务、来源引用、许可、行选择和派生说明 |
| [reports/](reports/) | 分条件结果、API 协议、压缩轨迹和人工审阅表 |
| 根目录 P0 模块 | 原始状态与非幂等副作用探针，保留原有语义 |

策略只接收公开 JSON 观察；环境对象和私有参考验证留在可信 runner。当前没有针对任意恶意本地代码的 OS 隔离保证。

## 协议与证据

下一阶段按[执行清单](docs/NEXT_STAGE_CHECKLIST.md)推进：[24 题人工审阅](reports/SCIENTIFIC_REVIEW_24.md)已通过，科学审阅建议 HOLD，收束工程与复现；[接收记录](reports/HUMAN_REVIEW_ROUND2_INTAKE.md)列明依据。新增六例的独立复审已通过，见[接收记录](reports/REGRESSION_REVIEW_INTAKE_2026_10_11.md)，第二模型接入暂缓。

| 阶段 | 实施协议 | 结果报告 |
| --- | --- | --- |
| P0 `0.1.0-p0` | [状态与副作用](docs/P0_IMPLEMENTATION_PROTOCOL.md) | [84 次探针](reports/P0_START.md) |
| `0.2.0-dev` | [联合故障与语义修复](docs/SEMANTIC_V1_PROTOCOL.md) | [首个开发版本](reports/SEMANTIC_V1_RELEASE.md) |
| `0.2.05-dev` | [契约诊断与来源交叉](docs/CLARITY_V2_PROTOCOL.md) | [当前结果](reports/CLARITY_V2_RELEASE.md) |
| `0.2.10-dev` | [证据与条件恢复](docs/EVIDENCE_V3_PROTOCOL.md) | [第三开发版](reports/EVIDENCE_V3_RELEASE.md) |
| `0.2.15-dev` | [语义判断与状态保持](docs/DECISION_V4_PROTOCOL.md) | [第四开发版](reports/DECISION_V4_RELEASE.md) |
| `0.2.20-dev` | [三段式工程套件](docs/REGRESSION_V5_PROTOCOL.md) | [第五开发版](reports/REGRESSION_V5_RELEASE.md) |

| `0.2.25-dev` | [统一证据验收](docs/ACCEPTANCE_V6_PROTOCOL.md) | [第六开发版](reports/ACCEPTANCE_V6_RELEASE.md) |

| `0.2.30-dev` | [专项复审登记](docs/ACCEPTANCE_V7_PROTOCOL.md) | [第七开发版](reports/ACCEPTANCE_V7_RELEASE.md) |

| `0.2.35-dev` | [检查分配负对照](docs/ALLOCATION_V8_PROTOCOL.md) | [第八开发版](reports/ALLOCATION_V8_RELEASE.md) |

总体研究约束见[研究协议 v2](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md)；[原始 v1](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V1.md)和[相关工作复核](docs/OVERLAP_AUDIT_2026_10_09.md)保留。不同阶段的指标和样本不能混池汇总。

[24 题独立人工审阅](reports/SCIENTIFIC_REVIEW_24.md)已通过；新增六条专项路径已复审通过，程序测试不等于独立人工认可。历史 source_id 注册表包含别名和派生来源，不能把其条目数当独立数据集数量。
