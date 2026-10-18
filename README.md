# FaultDA-Bench

**证据约束下数据分析 Agent 的语义恢复评测。**

FaultDA-Bench 研究：当工具执行状态不明确、分析产物可能错误、检查证据需要成本时，Agent 能否获取必要信息，完成正确修复，并避免重复副作用。当前是可运行的开发基准，尚未完成独立最终测试。

当前基准版本：`0.5.15-dev` · 研究分支：`faultda-bench` · 继承代码基线：`V5.0.15-beta.2`。
<!-- inherited-release: V5.0.15-beta.2 -->

[复现指南](docs/REPRODUCIBILITY.md) · [研究协议](reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md) · [最新结果](faultda_bench/reports/REVIEW_0515_RELEASE.md) · [历史研究汇总](docs/PROJECT_HISTORY.md)

## 研究问题

- **提交与正确性：** 工具已提交，是否意味着产物符合分析契约？
- **证据与决策：** Agent 能否合理检查、修复、结束，或在信息不足时升级？
- **归因与泛化：** 失败来自分析、故障恢复还是接口说明？简单规则与学习策略各能解决什么？

相关工作已覆盖多种通用恢复机制。本项目将其作为对照；当前四格设计可被廉价统一重算绕过，已停止作为主实验。下一候选收缩为无歧义责任与回执条件下的终止诊断，尚无科学准入或新机制结论。见[本轮研究定位与查新](faultda_bench/docs/RESEARCH_POSITION_0505.md)。

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
| 真实回执事实诊断 | 24 次真实请求；旧 lookup 主分数 0/12 与 6/12，模糊句按 last-publish 备选参照可匹配 12/12 | 已收到 both-plausible/lookup 人审意见；最终裁决未登记，不替换旧分数或解读为能力差 |
| 责任与来源 | 72 条公开视图可逆迁移；actor 范围与 scripted/unknown 生成来源分开 | active_actor 不等于模型生成；没有新模型实验 |
| 终止指标资格 | 72 条既有程序对照：24 安全完成、24 历史违规升级、24 不确定升级 | 单个历史簇的事后资格核对；未来主分母须独立审查、各臂共用 |
| 历史跨来源开发 | 三个来源、24 题及多种强程序/学习对照；分条件结果归入历史汇总 | 既有签字仅覆盖已确认范围，未确立额外机制或稳定外部 RL 优势 |

当前积累是可执行环境、证据重放与有效性控制。张雨田的最新复审已返回 12 对指代意见与四项设计 revise；最终裁决按原文仍未登记。已落实已见来源准入拦截，旧 holdout 的后续开发复用不能成为新独立测试，也不能反推早期训练泄漏。科学 HOLD；没有新增模型、RL 或跨任务提升。详见[本版报告](faultda_bench/reports/REVIEW_0515_RELEASE.md)与[历史证据](docs/PROJECT_HISTORY.md)。

## 快速复核

从完整仓库根目录运行，需要 Python 3.11+。以下步骤不需要 GPU 或 API 密钥：

```sh
python -m pip install -e .
python -m unittest tests.test_faultda_review515_intake tests.test_faultda_review515_lineage tests.test_faultda_review515_panel -v
python -m faultda_bench.review515.audit
```

统一入口核对历次冻结证据、新复审的接收范围及血缘资格，保持科学 HOLD。完整仓库测试与复核包子集分别计数；复核包可直接按[包内入口](faultda_bench/docs/REVIEW_0515_GUIDE.md)运行。哈希只校验一致性，不认证供应商或历史真实性。旧版入口保留在[复现指南](docs/REPRODUCIBILITY.md)，新输出不得覆盖冻结记录。

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

现有 [24 题独立人工审阅](faultda_bench/reports/SCIENTIFIC_REVIEW_24.md)、六条历史专项和最新 37 组技术复审仅覆盖各自明确范围。最新人工复审、来源拦截和共同分母修订见[本轮协议](faultda_bench/docs/REVIEW_0515_PROTOCOL.md)。下一步先裁决候选诊断问题是否具有非平凡增量；通过后才设计未见任务、真正无故障对照和独立真值，不在旧切片上继续扩格。第二模型暂缓；当前无新增 API 批准，不宣称超出强基线的模型/RL 发现。
