# FaultDA-Bench

**证据约束下数据分析 Agent 的语义恢复评测。**

FaultDA-Bench 研究：当工具执行状态不明确、分析产物可能错误、检查证据需要成本时，Agent 能否获取必要信息，完成正确修复，并避免重复副作用。当前是可运行的开发基准，尚未完成独立最终测试。

当前基准版本：`0.5.0-dev` · 研究分支：`faultda-bench` · 继承代码基线：`V5.0.15-beta.2`。
<!-- inherited-release: V5.0.15-beta.2 -->

[复现指南](docs/REPRODUCIBILITY.md) · [研究协议](reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md) · [最新结果](faultda_bench/reports/VALIDITY_0500_RELEASE.md) · [历史研究汇总](docs/PROJECT_HISTORY.md)

## 研究问题

- **提交与正确性：** 工具已提交，是否意味着产物符合分析契约？
- **证据与决策：** Agent 能否合理检查、修复、结束，或在信息不足时升级？
- **归因与泛化：** 失败来自分析、故障恢复还是接口说明？简单规则与学习策略各能解决什么？

相关工作已覆盖多种通用恢复机制。本项目将其作为对照；提交歧义与分析语义的联合影响仍是待验证假设，不宣称已确立新的失败机制。见[查新与定位修订](faultda_bench/docs/OVERLAP_AUDIT_2026_10_09.md)。

## 已实现

- 三份历史公开数据上的 **24 个开发任务**，分组与版本分析在每个来源上交叉设置；另保留时间窗口诊断。
- CSV 实际计算、SQLite 持久报告、暂存更正、版本比较后替换、幂等请求与历史副作用审计。
- 提交确认丢失、语义扰动，以及不同证据可用性和检查预算。
- 独立 Decimal 参考验证、程序基线与发布守卫、DeepSeek 接口及可重放轨迹。

执行流程：**公开任务契约 → Agent 选择工具 → 状态与产物更新 → 私有独立验证 → 分条件汇总**。验证答案与故障标签不进入 Agent 的工具观察。

## 当前证据

| 范围 | 已有结果 | 解释边界 |
| --- | --- | --- |
| 自洽工具环境 | 24 个程序状态、72 条读取/终止对照，保留时区等价与隐藏历史对照 | 同一历史任务/数据簇；程序动作不是 LLM 工具成绩 |
| 真实回执事实诊断 | 24 次真实请求；旧 lookup 主分数 0/12 与 6/12，模糊句按 last-publish 备选参照可匹配 12/12 | 备选解释待独立裁决，不替换旧分数，不宣称模型/RL 提升 |
| 责任与来源 | 72 条公开视图可逆迁移；actor 范围与 scripted/unknown 生成来源分开 | active_actor 不等于模型生成；没有新模型实验 |
| 历史跨来源开发 | 三个来源、24 题及多种强程序/学习对照；分条件结果归入历史汇总 | 既有签字仅覆盖已确认范围，未确立额外机制或稳定外部 RL 优势 |

当前已确认的积累是可执行环境、证据重放与有效性控制。旧回执差异应限定为接口指代表达；尚未确立新的通用恢复机制。新增独立复审 pending，科学 HOLD。详见[本版报告](faultda_bench/reports/VALIDITY_0500_RELEASE.md)与[历史证据](docs/PROJECT_HISTORY.md)。

## 快速复核

从完整仓库根目录运行，需要 Python 3.11+。以下步骤不需要 GPU 或 API 密钥：

```sh
python -m pip install -e .
python -m unittest tests.test_faultda_validity500 tests.test_faultda_validity500_review tests.test_faultda_validity500_acceptance -v
python -m faultda_bench.validity500.audit
```

统一入口核对 502 份冻结文件、历史结果汇总和新实验，重新解析响应正文、程序反馈、提出与执行动作及模型结果传递；分别记录已有人工审阅、新实验待复审与科学 HOLD。本地哈希不认证供应商或历史真实性；早期大规模套件的独立重放入口见复现指南。重新生成实验、可选付费 API 调用和旧版本复现见[复现指南](docs/REPRODUCIBILITY.md)；新实验使用新输出路径，不覆盖冻结记录。仅安装 wheel 不包含全部任务数据，不能替代完整仓库。

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

现有 [24 题独立人工审阅](faultda_bench/reports/SCIENTIFIC_REVIEW_24.md)及六条历史专项复审已通过，签字不覆盖新增实验。本轮为内部技术复审后的工程实跑，新独立人审/科学结论仍待完成；下一步先核查本轮四条真实轨迹的回执、终止动作和数值理由；若需额外诊断，覆盖全部回执后快照、预先冻结问题与预算，不只重跑失败例。第二模型暂缓，科学HOLD，不宣称超出强基线的模型发现。见[复审指南](faultda_bench/reports/RECEIPT_0380_REVIEW_GUIDE.md)。
