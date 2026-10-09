# 查新复核与定位决策（2026-10-09）

结论：原设想与 UndoBench 存在核心重叠，应改研究定位，不能只换数据格式。没有证据支持“新方向已证明原创”；本次是风险排除与可证伪方案设计。

## 原始证据与阅读边界

| 来源 | 本次核查范围与事实 | 对项目的决策 |
| --- | --- | --- |
| [UndoBench v1](https://arxiv.org/abs/2610.05622v1)，2026-10-04 | 摘要及此前正文 §2–3：成对正常/故障试验、多个突变边界、效果历史和状态 oracle | lost-ACK、重复副作用和胜任/恢复分离不列独立创新 |
| [作者仓库](https://github.com/tradertanmay/undobench)，访问 2026-10-09 | 阅读 README、B6 探测/重试实现、状态 oracle 关键判定及许可证文件标识，具体见下节 | 不得称其没有主动查询、弃权或语义约束；未完成全仓库复现 |
| [Verified Tool Calls](https://arxiv.org/html/2608.02645v1) | 正文方法与摘要：非原子失败下的后置条件验证、幂等键、验证后重试 | 必须纳入直接恢复对照，不能把 verify-before-retry 当新方法 |
| [When Stale Constraints Go Unchecked v3](https://arxiv.org/abs/2608.25553v3) | 摘要：固定预算中选择检查旧记忆的 provenance；强制关键路径含实验者知识 | “付费检查＋旧证据”本身不足创新；特权证据只作上界 |
| [Concord v2](https://arxiv.org/abs/2610.05281v2) | 摘要：追踪工具观察与可变来源，处理过期上下文 | 版本刷新是必要对照，不能独占“陈旧状态”问题 |
| [REVISE v1](https://arxiv.org/abs/2609.00643v1) | 摘要：依据依赖与有效性保留/重算工作，提交前再验证 | 不把血缘、选择性重算或提交前验证当新算法 |
| [DataSpace v1](https://arxiv.org/abs/2608.03451v1) | 摘要：异构工作区分析、完整表格产物与确定性评测 | 数据分析语义评分不是空白，需比较联合故障实验设计 |

后四项为摘要级筛查，未宣称完成其全代码审计。网络检索未发现某功能不等于该功能不存在。本轮外部仓库只作本地只读核查，不将其源码纳入本项目，不执行其脚本，不声称复现论文分数。

## UndoBench 源码抽查

已将作者仓库下载至忽略的 `work/related_work/undobench`，锁定提交 `4a25c4fa0f12bb6c79dc6e0e3a8f31deeb6af21e`。以下是静态阅读，不是运行验证：

- [B6 探测实现](https://github.com/tradertanmay/undobench/blob/4a25c4fa0f12bb6c79dc6e0e3a8f31deeb6af21e/recoverbench/recovery_methods/verify_before_retry.py#L24)：具有 PRESENT/ABSENT/UNKNOWN；`wrap_tool` 根据探测结果抑制重复、重试或抛出异常弃权。存在领域特定读取适配，不能把注释中的 zero-privilege 自动当作已审计的沙箱安全保证。
- [状态评分器](https://github.com/tradertanmay/undobench/blob/4a25c4fa0f12bb6c79dc6e0e3a8f31deeb6af21e/recoverbench/oracle/state_oracle.py#L41)：检查效果重数、禁用效果、终态、注册的不变量与顺序。语义和中间副作用检查都不是本项目独有。
- `LICENSE` 标识 Apache License 2.0，`LICENSE-DATA` 标识 CC BY 4.0，与主页声明一致。正式引入任何代码/任务时仍须按具体文件归属保留许可与署名；本次没有引入。

尚未核验：全部任务模板、探测预算公平性、完整权限边界、论文结果复现。局部源码存在上述机制已足以否定原先过宽的创新定位，但不足以证明新方向未被覆盖。

## 修改范围

执行 [研究协议 v2](../../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md)。候选差异只放在数据任务中多种不确定性的交互，以及相同合法证据/预算下的检查选择；必须打败简单组合解释才能继续扩展。

原 v1、P0 实施协议及 84 条程序探针结果保留；原结果不是新协议实验。当前环境没有自主语义修复、联合因子实验或正式模型基线，这些在 v2 明列为待办。此次文档修订不构成新 LLM/RL 成果。
