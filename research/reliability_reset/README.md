# Reliability Reset：Agent 评测研究线

当前研究版本 **1.1.05**。研究线以历史 FaultDA 基础设施为起点，集中检验原生评分与可证实的可靠性偏差；价格分析和 RL 是条件性后续工作。

## 当前状态

- **研究结论：**所查具体候选被原生完整评分识别；尚无跨独立任务、跨模型的可靠性误判证据。研究状态 **HOLD**。[原生控制](NATIVE_CONTROL_185.md) · [审计汇总](APPWORLD_AUDIT_CLOSEOUT_2026_10_27.md) · [论文主张内部评审](PAPER_CLAIM_REVIEW_2026_10_27.md)
- **历史官方轨迹：**复用 AppWorld 官方 GPT-4o 训练集 90 条、开发集 57 条历史轨迹。四个开发案例已由两位人工审阅者独立盲审，未形成原生通过但违规的证据链；其余轨迹的副作用不因此得到裁决。0.1.0 直接重放与归档评分存在差异，补充推导标记后检查项一致，但不能称为原样复现。[清点](EVALUATOR_GAP_190.md) · [审阅与重放](APPWORLD_REVIEW_2026_11_02.md)
- **最新接口试跑：**在同一原生训练任务中实跑 DeepSeek API 和 CUDA 本地小模型，记录原始提案、工具响应及模型用量；双方均未完成任务，独立安全裁决仍未知。[试跑结果](APPWORLD_PILOT_195.md)
- **1.1.0 扩展：**增加 Qwen 与 SmolLM 本地模型，四个检查点在同一已见任务中均未完成；恢复了真实 NPU 量化模型生成，但尚无跨任务或 NPU 精度结论。[1.1.0 结果](APPWORLD_PILOT_110.md)
- **六场景试跑：**DeepSeek、Qwen、Granite 和受输入上限约束的 SmolLM 均未产生原生评分通过的运行；后者五条受资源约束，Granite 为探索性补充。两条扩展轨迹的成功状态与完整原生评分不一致，已在新进程复核。[1.1.05 结果与逐次调用账本](APPWORLD_PILOT_115.md)
- **已有开发结果：**60 条旧记录中有 24 次预算拒绝、3 次升级，22 条未安全完成记录的终态正确；这些是相关开发轨迹，不是独立任务样本。[终止分类](TERMINAL_TAXONOMY.md)
- **最新评估回应：**已整理三份评估与价格对照。旧评估器默认 `dev_seen` 可能混入合成 profile；未来重算请使用显式筛选的 [seen_evaluation.py](seen_evaluation.py)。[评估回应](REVIEW_RESPONSE_SEEN_2026_10_28.md)
- **下一步设计：**只有具体候选通过[一页设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)，才考虑针对性实测与跨任务比较；不以增加模型或版本数量代替科学证据。[旧价格试点](EXTERNAL_PRICE_PILOT_2026_10_28.md)仅作背景。

## 工作入口

| 目的 | 入口 |
| --- | --- |
| 离线证据审计与程序控制 | [audit.py](audit.py) · [controls.py](controls.py) · [数据契约](SCHEMA_V1.md) |
| 公开证据、工具规划与终止 | [evidence_planner.py](evidence_planner.py) · [joint_control.py](joint_control.py) · [tool_contracts.py](tool_contracts.py) |
| 终止分类与 AppWorld 重放 | [terminal_taxonomy.py](terminal_taxonomy.py) · [native_replay185.py](native_replay185.py) · [terminal_binding185.py](terminal_binding185.py) |
| 真实轨迹清点与未决风险 | [official_dev_inventory.py](official_dev_inventory.py) · [结果与实验计划](EVALUATOR_GAP_190.md) |
| 独立盲审与历史评分重放 | [审阅结果和复核方法](APPWORLD_REVIEW_2026_11_02.md) · [加密证据包](evidence/appworld-review-2026-11-02.bundle) |
| 真实模型与工具接口试跑 | [appworld_pilot195.py](appworld_pilot195.py) · [试跑结果](APPWORLD_PILOT_195.md) |
| 模型模板解析与 NPU 重建 | [appworld_pilot110.py](appworld_pilot110.py) · [本版结果](APPWORLD_PILOT_110.md) |
| 六场景试跑、调用成本与评分重放 | [appworld_pilot115.py](appworld_pilot115.py) · [结果与账本](APPWORLD_PILOT_115.md) |
| 原始协议、实验与复审流程 | [历史与复审指南](HISTORY_AND_REVIEW_GUIDE.md) · [更新记录](CHANGELOG.md) |
| 研究草稿与新候选设计 | [研究草稿](PAPER_DRAFT.md) · [重置协议](RESET_PROTOCOL.md) · [一页设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md) |

```sh
python -m research.reliability_reset.terminal_taxonomy
python -m unittest tests.test_reliability_terminal_taxonomy tests.test_reliability_reset_seen_evaluation
```

第一条只读并打印摘要；使用 `--output` 需要一个不存在的新路径。历史命令、原始证据和运行限制仍保留；软件控制、哈希一致性与本地重放不能替代独立人工审阅或真实模型验证。
