# FaultDA-Bench

**可验证数据分析 Agent 的工程基础设施与研究重置。**

此前围绕恢复策略和验证成本的机制研究暂时停止，已实现的环境、工具、状态记录、审计与复现能力继续保留。

当前基准版本：`0.5.65-dev`（离线验证代价诊断） · 研究分支：`agent-eval-reliability-reset` · 继承代码基线：`V5.0.15-beta.2`。
<!-- inherited-release: V5.0.15-beta.2 -->

新的工作先检验一个更基础的问题：

> 结果导向的 Agent 评测，是否会对实际运行可靠性产生有后果、可独立复核，并能在不同任务家族中重复出现的误判？

当前研究区分 Agent 自主恢复、外部修复器代做和两者交互，并检验共享预算、工具信息与提示如何改变实际完成能力。已从程序控制推进到真实模型受控实验；跨独立任务的结论尚未建立。

## 当前研究

对每条 Agent 轨迹并列保留原始终态评分与独立可靠性判定。后者核对任务契约、完整工具轨迹、持久状态和副作用。比较系统必须使用相同任务、可见信息、工具权限和资源上限；未解决的案例单独报告，不将安全停止算作虚假成功，也不以重复措辞、随机种子或单一应用中的多个数据源冒充独立任务家族。

新设计和草稿位于 [`research/reliability_reset/`](research/reliability_reset/README.md)：

**当前版本：Reliability Reset 1.0.55（2026-10-24）。** 已完成相同文字说明下的公开状态整理与预算投影工具接口对照：54 条真实模型轨迹、9 个共享规则、207 次收到响应的 DeepSeek 请求。正常回执三组均完成 **12/12**；丢失回执设置下，文字／软状态／投影组超预算读取为 **6／1／0**。投影组实际触发五次故障且均升级，另一次因发布参数遗漏而提前失败；升级不计完成。见[结果、失败与成本](research/reliability_reset/RELEASE_155.md)及[设计](research/reliability_reset/FEASIBLE_INTERFACE_155.md)。

**基础设施检查点（1.0.0–1.0.15）。** 已具备离线证据审计、CSV/SQLite 适配、终止未知传播、历史责任区分和原件对照复审导出。历史 0.5.65-dev、旧评分和审阅原件保持保留；版本细节收在[更新记录](research/reliability_reset/CHANGELOG.md)、[1.0.15 修复报告](research/reliability_reset/RELEASE_115.md)与[审阅回应](research/reliability_reset/REVIEW_RESPONSE_110.md)。

- [研究问题与现有证据草稿](research/reliability_reset/PAPER_DRAFT.md)
- [重置协议、独立性要求与三周决策门槛](research/reliability_reset/RESET_PROTOCOL.md)

前序 [1.0.20](research/reliability_reset/RELEASE_120.md) 建立恢复贡献归因，[1.0.25](research/reliability_reset/RELEASE_125.md) 定位查询预算失败，[1.0.30](research/reliability_reset/RELEASE_130.md) 获得提示收益，[1.0.35](research/reliability_reset/RELEASE_135.md) 定位正确发布后的终止失败。1.0.50 改善了已确认状态下的控制，但六个修复回执丢失单元中仍有五次超预算。下一版 **1.0.55** 将比较软提示与结构化可行动作接口。新增完成证据要求对各臂相同，原评分保留；跨版本分数不直接拼接。

## 0.5.65-dev 检查点

0.5.65 完成离线 VeriCost 验证代价环境、精确动态规划上界与最优性证书，以及预注册规则和学习策略的比较。主要结果限制旧机制主张：

- 预注册的合成主设置可被一条廉价固定规则以 `0.031539` regret 落在 `ε = 0.05` 阈值内。
- 完整开发集上最佳注册固定规则 regret 为 `0.014189`；表现最好的学习策略 Thompson regret 为 `0.024159`，没有学习策略胜过该固定规则。
- D1 的边界结果对规则家族选择敏感；报告已披露其极小余量和更大规则家族下的反例。
- 没有新来源、独立测试集、模型调用或训练；这些结果不能支持跨任务或真实 Agent 能力结论。

0.5.60 的历史指标审计也发现：一个 `72/72` 对照属于规则与评分器共享同一逻辑的定义性恒等；`always_stop` 的表面优势来自单向计分，计入不安全停止后结论改变。它来自单一脚本开发簇，只作为评测有效性动机，不是跨任务发现。

详细数据和边界见 [0.5.65 版本报告](faultda_bench/reports/RELEASE_0565.md)、[0.5.60 指标审计](faultda_bench/reports/RELEASE_0560.md)及[历史研究汇总](docs/PROJECT_HISTORY.md)。不同版本、任务和评分协议的结果不合并为排行榜。

## 项目积累

- **V2–V3：** 实际 CSV 工具、独立数值验证、多步产物、故障注入及冻结恢复策略。
- **V4–V5：** DeepSeek SFT、DPO 与 GRPO 对照；CUDA/NPU 推理路径；可选 C++ 内核和 Go 单机实验协调。历史结果没有建立稳定的 RL 优势。
- **FaultDA-Bench：** 持久状态与副作用审计、状态不确定性、数据分析契约、工具回执、独立评分、来源血缘与复现记录。
- **当前方向：** 不再按版本堆叠功能，先判断终态评分与实际可靠性之间是否存在独立、重要且可重复的测量差异。

各阶段协议和数据分母不同，不能直接横向比较。汇总见[项目历史](docs/PROJECT_HISTORY.md)。

## 复现与入口

从仓库根目录开始，完整环境和冻结记录的复核步骤见[复现指南](docs/REPRODUCIBILITY.md)。常用入口：

| 路径 | 内容 |
| --- | --- |
| [`faultda_bench/`](faultda_bench/README.md) | 基准组件、任务协议、审计与发布记录 |
| [`research/reliability_reset/`](research/reliability_reset/README.md) | 新研究重置、草稿与设计门槛 |
| [`tasks/`](tasks/) 与 [`data/`](data/) | 任务和数据说明、来源及派生记录 |
| [`tests/`](tests/) | 状态、评分、故障和复现检查 |
| [`reports/`](reports/) 与 [`faultda_bench/reports/`](faultda_bench/reports/) | 历史实验报告和证据 |
| [`docs/PROJECT_HISTORY.md`](docs/PROJECT_HISTORY.md) | 前序版本的压缩研究脉络 |

## 限制

当前项目只有已见开发任务，没有经过新研究协议冻结的独立跨任务测试集。三个历史数据来源不等于三个独立任务家族。测试通过、文件哈希或程序重放只能支持其具体覆盖范围，不能证明供应商响应真实性、历史记录不可变性或 Agent 泛化能力。当前已观察到本地提示收益及局部自动规划收益；没有权重训练、RL 提升或跨环境泛化结论。
