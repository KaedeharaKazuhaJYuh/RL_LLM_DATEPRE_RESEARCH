# 1.0.30：预算感知工具选择干预

日期：2026-10-24。由 [1.0.25 实跑](RELEASE_125.md)中的 status → inspect 预算失败推进。

本轮问题：**把公开工具之间的信息包含关系讲清楚，能否使模型在一次检查预算内完成任务？**

## 调用前固定的设计

| 项目 | 设计 |
| --- | --- |
| 模型 | DeepSeek `deepseek-flash`，temperature=0，thinking disabled，沿用本地凭据 |
| 任务 | group/window/version 各 01、02 两个历史开发实例 |
| 状态 | healthy、semantic_error |
| 主轨迹 | 6 实例 × 2 状态 × 3 提示 = 36 条真实模型轨迹 |
| 提示臂 | 原提示；信息包含关系与预算提示；等 UTF-8 字节的服务背景提示 |
| 控制提示长度 | ASCII 尾随空格补至同字节数，**不声称 token 数相同**；实际 token 单独报告 |
| 强规则 | 每个任务/状态单独执行一次 task_semantic，共 12 次，三个提示共享该对照 |
| 上限 | 检查 1、写入 6（含环境初始化）、总决策 16、每模型轨迹调用 8、总请求 288 |
| 费用 | 峰值未缓存单价估算上限 $0.60；没有自动重试或模型回退 |
| 顺序 | 任务/状态块按固定种子交错；全部六种提示顺序各用两次 |
| 主要观察 | 安全完成率、首次提出的工具 |
| 成本与副作用 | 工具响应字节、请求/输入/输出 tokens、峰值费用估算、不安全发布及终止原因 |

完整提示及代码/任务哈希保存到 `protocol.json`，生成在第一条请求之前。`--prepare` 还对 12 个状态离线调用公开 status/inspect，验证提示描述的字段包含关系；这 24 次工具读取不是模型实验。

干预明确说明：在 E0 中，inspect 包含 status 的所有字段，另有当前报告、输入及目录；两种读取各占一次检查，但 inspect 响应更多、token 可能更贵。提示不提供正确数值、stage_id、参考答案或故障标签，也不直接改写模型动作。

模型臂中**没有 helper**。三种提示的观察、权限、预算与执行器一致。任何模型提出的超预算调用保留为失败；供应商、费用或输入限制导致的未评估单元保留为未知。

## 判别与下一步

- 若信息提示同时优于原提示及背景对照，且首次 inspect 增加，则支持本环境中的信息规划解释。
- 若背景提示同样有效，不能把改善专门归到信息包含关系。
- 若选对 inspect 仍未完成，继续查看 stage、publish 与 stop，而不能以首步正确冒充恢复成功。
- 若三臂相同或仍均失败，保留反结果，改查实际决策与信息内容，不追加未计划的付费试验。

按任务、状态、01/02 实例层报告配对得失。02 以前已用于离线开发，属于额外开发实例，**不是独立测试集**。三种分析意图共享一个环境家族；每单元单次供应商采样，不作独立同分布 episode 显著性结论。提示改善属于系统层干预，不是权重训练或 RL 效果。

## 复现

```powershell
python -m research.reliability_reset.tool_planning work/reset130-new --prepare
python -m research.reliability_reset.tool_planning work/reset130-new --execute
python -m research.reliability_reset.tool_planning work/reset130-new --verify work/reset130-new-offline-replay
```

prepare/verify 不调用供应商；execute 会使用现有 DeepSeek 凭据。已有目录不覆盖。价格与接口已对照 [官方价格](https://api-docs.deepseek.com/quick_start/pricing/)及 [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)，峰值未缓存输入 $0.30/百万 tokens、输出 $1.20/百万 tokens；用量估算不是供应商账单。
