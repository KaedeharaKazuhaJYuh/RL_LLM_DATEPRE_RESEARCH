# Changelog

## 2026-09-12

- 为全部 50 个任务增加声明式 `contract.required_capabilities`，并将其定义为操作族而非单一正确工具。
- 新增 `agent/contracts.py`，将合同能力映射为候选动作，并与 `allowed_tools` 取交集。
- 新增 `--contract-action-mask`，保留 raw 和旧 `--task-action-mask` 条件用于消融比较。
- 更新任务 schema、生成脚本、矩阵脚本和项目说明。
- 验证 50 个任务的合同结构，并完成 Rule Router 50/50 回归和合同掩码模拟调用检查。
- 为 LLM 结果加入模型、温度和重复调用编号元数据；将 LLM 的多轮结果明确表述为独立重复调用，而非 API seed。
- 完成操作族合同掩码预检：DeepSeek 在 50 个任务中通过 49 个；T11 保留为真实的候选工具选择错误。
- 完成操作族合同掩码的五次独立 API 重复：共 245/250 通过；每次均为 49/50，唯一失败均为 T11。新增汇总文件，明确该稳定性只适用于当前提示与任务条件。
- 新增 `wording_v1` 任务扰动生成器与运行器参数透传；该变体保持任务 ID、数据、合同、预算和独立答案不变，仅加入五种自然语言指令包装。
- 完成 wording_v1 的 Rule Router 回归：50/50 通过；新增扰动协议，明确它是管线对齐检查，尚不能代表 LLM 鲁棒性结论。
- 完成 DeepSeek wording_v1 单次预检：raw 为 31/50，操作族合同掩码为 48/50。新增逐任务日志与汇总；将该结果标注为误差分析信号，等待多次独立重复后再作稳健性结论。
- 完成 wording_v1 的 DeepSeek 五次独立重复：raw 为 151/250（平均 60.4%，标准差 5.18 个百分点），操作族合同掩码为 245/250（98.0%，标准差 0.0）。将其与原始任务集比较后，记录为当前提示鲁棒性实验的正式结果。
- 新增 `value_v1` 数值扰动生成器：同步生成变换后的三份 CSV、50 个任务、11 个 gold 答案和 39 个分析参考输出，避免数值变化后复用旧答案。
- 完成 value_v1 的 Rule Router 回归与完整性验证：50/50 通过；确认 T05、T11 和后续参考统计均随数据变化而重建。
- 新增 `dataset_profile_v1_read_only` 数据感知状态：在首次工具选择前提供十维聚合 CSV 特征，不包含行级数据且不占用工具预算。
- 完成 data-aware 原始集与 value_v1 的 Rule Router 回归：两者均为 50/50；后续 LLM 结果将与此前 text-only 条件分开报告。
- 完成 DeepSeek data-aware 四条件单次预检：原始 raw/合同为 29/50、49/50，value_v1 raw/合同为 33/50、48/50。明确标注为端到端预检，尚不用于数值鲁棒性结论。

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

