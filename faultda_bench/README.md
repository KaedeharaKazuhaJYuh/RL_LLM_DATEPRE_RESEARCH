# FaultDA-Bench 组件索引

最新（2026-10-17）：**0.5.05-dev** 接收张雨田 37 组人工技术复审，合理备选指代保留、最终裁决未进行；完成两类证据/决策假设、相关工作与强规则对照、跨任务准入草案。新设计未独立验收；科学 HOLD，新增 API 0。
[本版报告](reports/REVIEW_0505_RELEASE.md)。

最新（2026-10-16）：**0.5.0-dev 已完成**。保留旧 0/12、6/12 主分数，另注释 contextual 的 last-publish 合理解释（12/12，不替换主分数）；72 条 actor/origin 视图可逆迁移。496 项测试通过，新增 API 0。研究主张收束为接口/工程有效性，新独立复审 pending，科学 HOLD。下一版 0.5.05-dev 先整理复审、查新及可证伪竞争解释。
[本版报告](reports/VALIDITY_0500_RELEASE.md) · [复审指南](reports/VALIDITY_0500_REVIEW_GUIDE.md)。

项目定位、当前结果和限制见[仓库首页](../README.md)；操作步骤见[复现指南](../docs/REPRODUCIBILITY.md)。当前开发版本为 `0.5.05-dev`。

## 实现分层

| 组件 | 职责 |
| --- | --- |
| [review505/](review505/) | 37 组人审接收、命题级证据对照、设计准入及隔离复核包 |
| [validity500/](validity500/) | 旧分数保留、参照解释注释、中性 actor/origin 视图与结论审计 |
| [coherent395/](coherent395/) | 自洽 CSV/SQLite 轨迹、真实回执指代配对与复审 |
| [probes390/](probes390/) | 聚焦事实探针、固定答案负对照、离线资格与复审 |
| [postreceipt385/](postreceipt385/) | 全部四个回执后快照、独立行算术、真实事实诊断与四对复审 |
| [receipt380/](receipt380/) | 新回执动作的真实两步交互与同权限规则对照 |
| [semantics305/](semantics305/) | 三因素说明对照、等价时区事实诊断、公开强规则及本版验收 |
| [rowdiag/](rowdiag/) | 逐行选取/时间比较/求和诊断、响应正文重放与有限多步接续 |
| [release030/](release030/) | 新版统一验收，保留历史代码字节与旧人工签字范围 |
| [pilot/](pilot/) | 共同公开可靠性说明、离线对照、固定计划及有上限的 DeepSeek 入口 |
| [trust/](trust/) | 真实计算缺陷、同源错误反例、公开数据数值守卫与弃权对照 |
| [surface/](surface/) | 公开 stage 返回证据、暂存参考强规则及读写成本交换 |
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

| `0.2.50-dev` | [工具证据与基线](docs/SURFACE_V9_PROTOCOL.md) | [第九开发版](reports/SURFACE_V9_RELEASE.md) |

| `0.2.55-dev` | [暂存证据可信边界](docs/TRUST_V10_PROTOCOL.md) | [第十开发版](reports/TRUST_V10_RELEASE.md) |

| `0.2.60-dev` | [模型诊断入口](docs/MODEL_PILOT_V11_PROTOCOL.md) | [第十一开发版](reports/MODEL_PILOT_V11_RELEASE.md) |

| `0.2.65-dev` | [真实诊断接收](docs/MODEL_PILOT_V12_INTAKE.md) | [第十二开发版](reports/MODEL_PILOT_V12_RELEASE.md) |

| `0.2.70-dev` | [动作输出诊断](docs/FORMAT_V13_PROTOCOL.md) | [第十三开发版](reports/FORMAT_V13_RELEASE.md) |

| `0.2.75-dev` | [多步设计冻结](protocols/multistep_v15_design.json) | [后续状态复核](reports/FOLLOWUP_V14_RELEASE.md) |

| `0.2.80-dev` | [多步可执行计划](reports/multistep_v15_plan.json) | [完整多步诊断](reports/MULTISTEP_V15_RELEASE.md) |

| `0.2.85-dev` | [三臂干预设计](protocols/intervention_v17_design.json) | [发布归因审计](reports/PUBLICATION_V16_RELEASE.md) |

| `0.2.90-dev` | [三臂可执行协议](docs/INTERVENTION_V17_PROTOCOL.md) | [真实三臂对照](reports/INTERVENTION_V17_RELEASE.md) |

| `0.2.95-dev` | [判断/单步动作计划](reports/stopping_v18_plan.json) | [数值与停止诊断](reports/STOPPING_V18_RELEASE.md) |

| `0.3.0-dev` | [窗口诊断与验收](docs/ROWDIAG_030_PROTOCOL.md) | [版本收尾](reports/ROWDIAG_030_RELEASE.md) |

| `0.3.05-dev` | [三因素与时间表达](docs/SEMANTICS_0305_PROTOCOL.md) | [本版收尾](reports/SEMANTICS_0305_RELEASE.md) |
| `0.3.10-dev` | [公开一致性检查](docs/CONSISTENCY_0310_PROTOCOL.md) | [本版收尾](reports/CONSISTENCY_0310_RELEASE.md) |

| `0.3.15-dev` | [反馈与守卫对照](docs/FEEDBACK_0315_PROTOCOL.md) | [本版收尾](reports/FEEDBACK_0315_RELEASE.md) |

| `0.3.20-dev` | [真实修订与动作接续](docs/HANDOFF_0320_PROTOCOL.md) | [本版收尾](reports/HANDOFF_0320_RELEASE.md) |

| `0.3.25-dev` | [合法恢复与事实审计](docs/RECOVER_0325_PROTOCOL.md) | [本版收尾](reports/RECOVER_0325_RELEASE.md) |

| `0.3.30-dev` | [故障与强策略资格核验](docs/QUALIFY_0330_PROTOCOL.md) | [本版收尾](reports/QUALIFY_0330_RELEASE.md) |

| `0.3.35-dev` | [离线可执行协议](docs/RUNTIME_0335_PROTOCOL.md) | [本版收尾](reports/RUNTIME_0335_RELEASE.md) |

| `0.3.50-dev` | [技术复审后工程实跑](docs/LIVE_0350_PROTOCOL.md) | [本版收尾](reports/LIVE_0350_RELEASE.md) |

总体研究约束见[研究协议 v2](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md)；[原始 v1](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V1.md)和[相关工作复核](docs/OVERLAP_AUDIT_2026_10_09.md)保留。不同阶段的指标和样本不能混池汇总。

[24 题独立人工审阅](reports/SCIENTIFIC_REVIEW_24.md)已通过；新增六条专项路径已复审通过，程序测试不等于独立人工认可。历史 source_id 注册表包含别名和派生来源，不能把其条目数当独立数据集数量。
