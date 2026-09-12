# Changelog

## 2026-09-12

- 为全部 50 个任务增加声明式 `contract.required_capabilities`，并将其定义为操作族而非单一正确工具。
- 新增 `agent/contracts.py`，将合同能力映射为候选动作，并与 `allowed_tools` 取交集。
- 新增 `--contract-action-mask`，保留 raw 和旧 `--task-action-mask` 条件用于消融比较。
- 更新任务 schema、生成脚本、矩阵脚本和项目说明。
- 验证 50 个任务的合同结构，并完成 Rule Router 50/50 回归和合同掩码模拟调用检查。

## 2026-09-11

- 重写 README，使其成为项目介绍页，并统一使用第一人称说明研究目标、系统架构、实验任务、运行方式和研究路线。
- 新增可选的 `--task-action-mask`，用于限制 T01–T11 的候选动作，和 raw LLM 条件区分。
- 扩展 LLM 动作白名单，使其包含统计、清洗、聚合和任务分析工具。
- 保留 raw 条件，避免把动作掩码结果误当作无约束 LLM 结果。
- 完成本地语法检查和动作掩码配置检查。
- 完成修正 Verifier 下的 DeepSeek masked 50 任务实验：50/50 通过。
- 新增 `scripts/aggregate_seeds.py`，用于自动计算多 seed 的通过率、平均分和工具调用均值及标准差。
- 完成修正 Verifier 下的 DeepSeek raw 五 seed 矩阵实验：250 个任务中 192 个通过。
- 完成修正 Verifier 下的 DeepSeek masked 五 seed 矩阵实验：250 个任务中 250 个通过。

## 2026-09-10

- 修正 Verifier，使其检查 `gold.expected` 并拒绝空答案。
- 为 Contextual Bandit 接入随机种子、随机探索和任务结束后的 Verifier 奖励更新。
- 完成 Rule Router 与 Bandit 的 50 任务诊断实验。
- 生成并上传修正后的逐任务日志和结果汇总。

## 2026-09-09

- 建立 50 个数据分析任务、任务 schema、参考输出和基础验证规则。
- 实现 Rule Router、LinUCB Bandit、LLM 适配器、数据工具和实验运行器。
- 接入 DeepSeek 的 OpenAI-compatible API 调用方式。

