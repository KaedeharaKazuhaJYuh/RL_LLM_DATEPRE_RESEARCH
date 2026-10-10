# FaultDA-Bench

**证据约束下数据分析 Agent 的语义恢复评测。**

FaultDA-Bench 研究：当工具执行状态不明确、分析产物可能错误、检查证据需要成本时，Agent 能否获取必要信息，完成正确修复，并避免重复副作用。当前是可运行的开发基准，尚未完成独立最终测试。

当前基准版本：`0.2.15-dev` · 研究分支：`faultda-bench` · 继承代码基线：`V5.0.15-beta.2`。
<!-- inherited-release: V5.0.15-beta.2 -->

[复现指南](docs/REPRODUCIBILITY.md) · [研究协议](reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md) · [最新结果](faultda_bench/reports/DECISION_V4_RELEASE.md) · [历史研究汇总](docs/PROJECT_HISTORY.md)

## 研究问题

- **提交与正确性：** 工具已提交，是否意味着产物符合分析契约？
- **证据与决策：** Agent 能否合理检查、修复、结束，或在信息不足时升级？
- **归因与泛化：** 失败来自分析、故障恢复还是接口说明？简单规则与学习策略各能解决什么？

相关工作已覆盖多种通用恢复机制。本项目将其作为对照；提交歧义与分析语义的联合影响仍是待验证假设，不宣称已确立新的失败机制。见[查新与定位修订](faultda_bench/docs/OVERLAP_AUDIT_2026_10_09.md)。

## 已实现

- 三份历史公开数据上的 **24 个开发任务**，分组与版本分析在每个来源上交叉设置；另保留时间窗口诊断。
- CSV 实际计算、SQLite 持久报告、暂存更正、版本比较后替换、幂等请求与历史副作用审计。
- 提交确认丢失、语义扰动，以及不同证据可用性和检查预算。
- 独立 Decimal 参考验证、六种程序基线、DeepSeek 接口及可重放轨迹。

执行流程：**公开任务契约 → Agent 选择工具 → 状态与产物更新 → 私有独立验证 → 分条件汇总**。验证答案与故障标签不进入 Agent 的工具观察。

## 当前证据

| 实验 | 结果 | 解释边界 |
| --- | --- | --- |
| 跨来源离线开发实验，2,304 次执行 | 强组合基线在 E0/E1、检查预算 4 时各完成 96/96 | 这些条件共享 24 题，不是独立样本；尚未支持额外耦合失败 |
| 历史说明与证据布局诊断 | 说明修正和历史重排均未提高各自实验的完成数 | 不同协议不可混池；详细负结果见历史汇总 |
| DeepSeek 语义与动作建议对照，6 对 | 原始策略安全完成 2/6，规则建议辅助为 6/6；强规则也为 6/6 | 三个旧实例、单次条件诊断；辅助系统收益，不是 RL 或模型能力提升 |
| 工程验证 | 149 项测试通过，本轮 48 条轨迹重放一致 | 验证实现与记录一致，不代表研究假设成立 |

上述实验使用不同范围，不能合并成一个总成功率。完整分母、调用量、协议与局限见[本轮报告](faultda_bench/reports/DECISION_V4_RELEASE.md)，早期记录见[组件索引](faultda_bench/README.md)。本研究分支未进行新的 RL 训练。

## 快速复核

从完整仓库根目录运行，需要 Python 3.11+。以下步骤不需要 GPU 或 API 密钥：

```sh
python -m pip install -e .
python -m unittest tests.test_faultda_semantic tests.test_faultda_clarity tests.test_faultda_evidence tests.test_faultda_decision -v
python -m faultda_bench.decision.verify faultda_bench/reports/decision_v4_offline.json
python -m faultda_bench.decision.verify faultda_bench/reports/decision_v4_api.json
```

上述命令默认重放保存动作并核对评分。重新生成实验、可选付费 API 调用和旧版本复现见[复现指南](docs/REPRODUCIBILITY.md)；新实验使用新输出路径，不覆盖冻结记录。仅安装 wheel 不包含全部任务数据，不能替代完整仓库。

## 项目演进

| 阶段 | 保留下来的主要积累 |
| --- | --- |
| V2–V3 | 真实工具、独立验证、多步文件状态、故障注入与选择性恢复 |
| V4–V5 | DeepSeek 微调与 RL 对照、GPU/NPU 路径、可选 C++ 内核和 Go 单机实验协调 |
| FaultDA P0 → 0.2.0-dev | 持久副作用、联合扰动、语义修复及基准原型 |
| FaultDA 后续开发版 | 字段契约复核、来源×意图交叉，以及证据抽取和条件恢复诊断 |

各阶段评测协议不同，历史分数不作横向排行榜。早期局部 RL 增益经过更强监督对照后未形成稳定优势；详细结论及修正记录归入[历史研究汇总](docs/PROJECT_HISTORY.md)，不在首页逐版堆叠。

## 代码与文档入口

| 路径 | 内容 |
| --- | --- |
| [faultda_bench/](faultda_bench/README.md) | 当前基准组件、协议和记录索引 |
| [tests/](tests/) | 状态、评分、故障和复现检查 |
| [agent/](agent/)、[experiments/](experiments/)、[research/](research/) | 继承的工具、模型训练和研究实现 |
| [native/](native/)、[orchestrator/](orchestrator/) | 可选原生计算与单机实验协调 |
| [reports/](reports/) | 历史实验报告与原始证据 |

## 当前限制与下一步

目前仅使用三个已见来源，属于受控参数绑定；合成维表重复和版本修订不等于真实生产事件。工具 JSON 接口不是任意不可信代码的 OS 安全沙箱。数据引用、许可与派生方式见[任务清单](faultda_bench/protocols/cross_source_v2.json)。

当前优先完成 [24 题独立人工审阅](faultda_bench/reports/SCIENTIFIC_REVIEW_24.md)与科学验收，第二模型家族暂缓。现有证据尚不足以支持新的机制或超出强基线的发现，先调整研究假设，再决定是否扩源。详见[科学验收预审](faultda_bench/reports/SCIENTIFIC_GATE_2026_10_11.md)与[下一阶段清单](faultda_bench/docs/NEXT_STAGE_CHECKLIST.md)；自动化预审不等于独立验收通过。
