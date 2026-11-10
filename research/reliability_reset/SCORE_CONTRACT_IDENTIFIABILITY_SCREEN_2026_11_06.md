# 评分契约可识别性：跨基准近邻筛选

日期：2026-11-06  
研究状态：**HOLD；“评分契约可识别性审计方法”作为宽泛方法主张判为 NO-GO；只保留一个待检验的 DAComp 经验假设，尚未建立独立论文贡献。**  
范围：公开论文、官方代码与公开说明的定向审查；未下载大型数据集、未运行基准、未调用模型/Judge API。

## 研究问题的收窄

DAComp-DA 的初步候选不应再写成“评分器容易改变分数”。这种泛化说法已被 grader 规则敏感性、rubric 可靠性和评分重放工作覆盖。

更精确的待检验问题是：

> 对开放式 Agent 评测，当任务规范、Judge 输入、机器可读评分元数据与归一化/聚合代码分别承载评分契约时，公开材料是否足以唯一确定每个任务的合法分数？若不唯一，所有符合公开契约的解释是否会改变一个预先指定的模型比较？

此前拟称“评分契约可识别性”的通用框架，现不再作为独立方法贡献。可识别性、rubric/metric敏感性、评分来源溯源及工具契约到评分的追踪，已被多个近邻分别覆盖。项目只保留一个更窄的经验问题：

> 在 DAComp-DA 这类开放式数据分析 Agent 任务中，公开任务文本给出的分值上限与可执行 scorer 使用的分母是否出现无法由显式优先级消解的冲突？经盲化裁定后，这种冲突是否会改变一个预先指定、使用相同逐题模型输出的系统比较？

该问题不是新审计框架的贡献声明；它目前只是针对 DAComp-DA 的可证伪候选。只有规范来源冲突真实存在、独立裁定允许多于一种解释、配对重算实际改变预设比较，且差异超出 Judge 波动与近邻已知情况，才可能形成独立经验贡献。

旧版通用框架可作为操作步骤使用，但不得作为新颖性主张：

1. 对每个任务列出规范性来源（任务说明、rubric、Judge prompt）和执行来源（schema/metadata、解析、归一化、裁剪、聚合）。
2. 只有来源之间存在无法由文档明确优先级消解的矛盾，才标记“契约未识别”；单纯比较两种任意评分规则不算。
3. 由盲审者在不看模型输出和分数的阶段裁定可接受的契约解释；无法裁定时保留多个解释，不擅自选有利版本。
4. 对相同的冻结逐题 Judge 结果计算各可接受解释下的分数范围，并检验预注册的模型差异/排序是否在该范围内保持不变。

关键估计对象不是“最大可制造分差”，而是**独立裁定后的合法解释集合是否非单点，以及该集合是否改变预设系统结论**。若没有作者/专家确认规范权威，结果只能称公开材料未能确定评分契约，不能称原生评分错误。

## 直接近邻复核与新颖性降级

| 近邻 | 已覆盖内容 | 对本候选的影响 |
|---|---|---|
| *Do Agent Benchmarks Do What They Say? An Executable-Contract Audit of Tool-Using Agent Environments* (arXiv:2609.37315v1) | 在四个 Agent 基准中把工具广告表面作为可执行契约，核验工具实现，并沿任务文件与 evaluator 追踪评分来源；报告工具/评测器发现、负对照和构造轨迹上的 verdict 变化。 | **否决**“提出契约溯源审计方法、把代码链追到评分”作为本项目的新方法贡献。其主要对象是 advertised tool surface 与工具实际状态变化，不是 rubric 上限、metadata 分母的规范优先级；因此不能仅凭摘要断言它已实证覆盖 DAComp 的精确冲突。 |
| *Measurement Risk in Supervised Financial NLP: Rubric and Metric Sensitivity on JF-ICR* (arXiv:2604.27374v2) | 对固定金融 NLP 测试集改变 rubric、序数指标和聚合方案，报告标签一致性与系统排序稳定性，并提出 metric-identifiability reporting discipline。 | **否决**一般“rubric/metric/aggregation 可识别性审计”新颖性。仍待核实的窄边界是：跨文件规范来源冲突而非研究者主动替换 rubric/metric；是否存在不能从公开材料裁定的权威分值，以及合法解释是否改变固定输出上的比较。 |
| *Same Outputs, Different Scores* (arXiv:2611.03377) 与 Judge/rubric 可靠性工作 | 固定输出下改变评分规则或 Judge 配置并评估分数/排序变化。 | 因此，“同一输出重算后分数不同”本身没有增量。只允许检验经独立裁定的合约解释，而不是任意规则敏感性。 |
| *When Benchmarks are Targets* (ACL 2024) | 在 MMLU 等多选基准改变选项顺序、答案选择等评测细节，观察到排行榜排名可发生明显变化。 | 排名对评测细节敏感是已知现象，不能作为本项目贡献；其研究对象不是 DAComp 中 rubric 与 metadata 分母的来源冲突。 |
| *A Judge-Aware Ranking Framework for Evaluating Large Language Models without Ground Truth* (arXiv:2601.21817) | 用 judge-specific discrimination 建模异质 Judge，并为分数差和模型排名提供置信区间。 | “把 Judge 不确定性纳入榜单/提供排名区间”不是增量；该工作未在当前可见方法中处理同一 rubric 原始输出由不同来源 ceiling 归一化的规范解释集合。 |
| *DataSpace* (arXiv:2608.03451)；*NumTrace* (arXiv:2610.34887) | DataSpace 对完整数据分析表格结果作确定性检验；NumTrace 将财务数值声明拆成 value、binding、support，并检查实体、概念、期间、单位和范围。 | **否决**将“数据分析结果可验证”或“数值/证据绑定”作为本候选的独立增量。它们未因此证明 DAComp 的 rubric ceiling 与 metadata 分母冲突已被解决；本候选仅剩独立裁定规范来源及固定分数比较后果。 |

**边界裁决：[推断]** 候选在概念层面仍与评测可靠性及 evaluator audit 接近；当前没有证据证明其独立性足以支撑顶会方法论文。若双盲审阅不确认 DAComp 的规范权威确实不可识别，或合法解释集合不改变预设比较，立即关闭此经验候选，不再扩成通用框架。

**排名敏感性边界：[事实/推断]** 一般的“微小评测变化会改变排行榜”已由 *When Benchmarks are Targets* 展示；由异质 Judge 产生的排名不确定性已有 Judge-aware 排名模型处理。故本候选如继续，必须证明一条更窄的经验事实：经独立裁定为合法的跨文件计分解释，实际作用于固定的开放式数据分析轨迹，并改变超出 Judge 波动的预注册模型比较。当前三条记录不具备该检验条件。

## 跨基准结构筛选

| 基准 | 与目标问题的关系 | 公开实现所见评分结构 | 本轮裁决 |
|---|---|---|---|
| **DAComp-DA** | 核心候选：开放式数据分析报告，Judge 与原生归一化器读取不同来源。 | 固定版 Judge prompt 以 `rubric.txt` 为规范文本；评分代码从 `metadata.json.Total` 取分母、归一化并裁剪。100题静态筛查发现11个冲突候选但解析未全覆盖。公开目录经补查共有3条原始评分行：英文GPT-5一条、中文Qwen3-Coder-Plus两条，覆盖两个底层任务ID（005、006）；006中英版本不是同一任务×系统配置下的配对实验。 | 候选仍待盲审和完整逐题数据；目前直接观察到 Judge 纳入metadata维度总上限之外4分的情况仅在英文006一行。不能据此称普遍缺陷或比较结论受影响。详见[DAComp审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)。 |
| **FDABench** | 同属数据分析 Agent，开放式 report 任务，适合检验“相同现象是否在不同任务/评测架构出现”。 | 官方 `ReportEvaluator` 对 SQL accuracy、external integration、logical reasoning、completeness 使用固定 0.25 等权；每维度限定固定分值集合，最终分为四维平均。实现比较生成报告与 ground-truth report；本轮读取的 evaluator 未呈现任务 rubric ceiling 与 metadata 分母分离路径。 | 对“跨来源分值上限冲突”是**结构性负对照**，不是复现。它说明不能把 DAComp 现象直接推广到所有 rubric-based 数据分析评测。仍需对锁定版本的 task schema/结果导出完整核验后才能纳入正式分析。 |
| **KramaBench** | 同属数据科学 Agent，具有端到端数据湖工作流，且官方说明包含 rubric partial credit。 | 任务 JSON 暴露 query、answer、answer_type 与 subtasks；官方 evaluator 按答案类型映射 metric，对逐题结果输出后再按 metric/workload 聚合。公开 README 称 rubric-based partial credit，但当前审查未发现 DAComp 式“Judge 看 rubric、归一化器另取独立任务总分元数据”的同构路径。 | 作为异构评分架构的负对照/边界比较有价值；不是当前候选的第二次阳性复现。要进一步纳入，须检查 pinned commit 的任务数据、rubric 生成与 evaluator 具体实现，不能只凭 README 定性。 |

### 公开评分记录中的更精确证据

官方论文 §2.2 将 rubric score 定义为已得权重之和除以权重之和；固定英文 Judge prompt 则说明 rubric 总分是最高分、最终分为各 Requirement 得分之和。[DAComp 论文方法](https://arxiv.org/html/2512.04324#S2.SS2) · [固定版 Judge prompt](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/prompts.py#L1031-L1055)

在 `dacomp-006`：rubric 标题写20分，Requirement 上限写16，criterion 最大分相加20；metadata 三维 `4+7+5=16` 与前五个 criterion 的类别权重相符，但 rubric 的1.6与1.7又增加4分。唯一公开 Judge 输出实际为1.6得2分、1.7得2分，raw total=10；原生 scorer 仍按 metadata16归一化。也就是说，可观察到被计入分子的项目含有metadata维度上限中未包含的4分。原始 rubric、metadata、评分行分别可在[rubric](https://raw.githubusercontent.com/ByteDance-Seed/DAComp/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/src/dacomp-006/rubric.txt)、[metadata](https://raw.githubusercontent.com/ByteDance-Seed/DAComp/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/src/dacomp-006/metadata.json)、[Judge评分CSV](https://raw.githubusercontent.com/ByteDance-Seed/DAComp/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/model_scores/gpt-5-2025-08-07-test1__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv)复核。

**[事实]** 英文006原生总分45.5可复算；使用rubric标题20作分母为38.0；若依该输出中选择的1.2.B（3分而非4分）及其余criterion最大路径作暂定路径条件分母，则为19、总分约39.58。中文 `dacomp-zh-006` 公开raw得分4且没有1.6/1.7得分；中文 `dacomp-zh-005` 得分19、metadata28、rubric标题35，Criterion1.2上限还超过所属Requirement上限，但目前这条输出未超过metadata分母。**[边界]**19是英文006的审计派生敏感性口径，不是官方公布分母；三个记录跨语言/模型配置不匹配。来源授权关系仍待独立裁定，不能据此声称正式排名改变或缺陷普遍存在。

### 为什么这一步会改变研究决策

- 两个相邻数据分析基准的公开架构不同，意味着“跨任务验证”不能只换任务集；必须先确认被检验的评分契约机制在该基准中确实可表达、可观察。
- 若 FDABench 与 KramaBench 都没有独立的 per-task denominator source，则它们的无冲突是有效的阴性边界，但不能当作“普遍问题不存在”的统计证据。
- 现在最多可提出一个 DAComp 单基准候选及一套待验证的诊断方法。若只在 DAComp 发现静态不一致、而没有人类契约裁决及真实多系统分数影响，仍不足以支撑顶会论文贡献。
- 若盲审发现评分规范明确以 metadata 为唯一权威，或完整审计后矛盾消失，DAComp 阳性候选应关闭；不得因已投入筛查而改写契约。

## 可证伪经验假设（候选，不是贡献声明）

> 对 DAComp-DA 中“Judge实际计入 rubric 分子的项目”与“原生 scorer 归一化分母”不一致候选，独立审阅确认至少一题的官方计分契约确实要求分子包含 metadata维度上限之外的项目；基于相同冻结多系统逐题输出，按获裁定的契约重算后改变一项预注册系统比较，且差异超过重复 Judge 评分不确定性。

**最强反例/否证：**所有疑似任务都有单一明确权威来源；或者双盲审阅认为多种解释均不符合契约；或者合法解释的逐题结果不改变预注册比较；或者分数差与 Judge 的重复评分波动同量级；或者近邻研究已对相同规范冲突及其决策影响作过系统分析。任一成立，都应将候选缩为工程审计或关闭。

### 最小预注册估计量（设计定义，不是结果）

令 `i` 为独立任务，`a,b` 为预先选定的两个系统，`z_im` 为系统 `m` 在任务 `i` 上已经冻结的 Judge 输出；`C_i` 是盲审在看不到模型输出与得分时，确认对该任务仍符合公开契约的分值解释集合。`S(z_im,c_i)` 是将同一 Judge 输出按解释 `c_i` 计分所得分数。对同一批配对任务定义：

`D_ab(c) = Σ_i w_i [S(z_ia,c_i) - S(z_ib,c_i)]`, 其中 `c ∈ C` 且 `C` 只包含审阅确认的、全局自洽的解释组合。

主要报告对象是 `D_ab(C) = [min_{c∈C} D_ab(c), max_{c∈C} D_ab(c)]`；所有系统共用同一任务解释，不能分别给每个系统挑最有利口径。若原生比较与此区间的符号相反，则说明获认可的契约解释可翻转该比较；若区间跨零但不包含相反方向的稳健证据，只能报告比较未被识别。任务簇 bootstrap 处理抽样不确定性；重复 Judge 运行在固定 `z` 之外单独估计评分噪声，不得把一次 Judge 变化归因于契约冲突。主系统对、任务权重、方向阈值及 Judge 重复次数必须在看结果前冻结。当前没有足够逐题多系统数据计算该量，也没有预注册数值阈值。

**贡献边界：[推断]**以上只是把“会不会改变结论”变成可审核的估计目标，不能单独作为算法/方法创新；类似的 metric/rubric 敏感性与排序稳健性已见近邻。独立贡献必须来自经过盲审的真实来源权威歧义，以及它在至少一个预注册比较上的实证后果。若没有这个结果，交付只能是案例报告或工程审计。

## 最小下一步

1. 完成 DAComp 21 题两阶段独立盲审，候选与对照同样保留；Stage 1 锁定 rubric-only 判断后才揭示 metadata。审阅重点是 rubric criterion 的归属与上限、metadata 类别是否覆盖所有计入的 Judge 项，以及规范优先级；不能只问数值是否看起来不一致。
2. 对其余未解析的 DAComp rubric 进行人工边界核验，报告完整任务覆盖与分母，不以 parser 漏检充当“无冲突”。
3. 先查 FDABench 固定发布版本和 KramaBench pinned commit 的完整任务 schema/评测代码，确认两者确实是机制负对照；没有同构机制就不浪费 API 费用做无效“复制实验”。
4. 只有在独立审阅确认 DAComp 契约有多种可接受解释后，才使用已公开的同一组多系统逐题输出配对重算；当前公开 DAComp 结果不够，不能从榜单均值反推。
5. 预先规定唯一主比较、允许解释集合与 Judge 重复评分基线；若无结果能改变该比较，或变化落在 Judge 波动范围内，关闭为独立论文贡献。

当前无新增模型/API预算申请，无新实验获准；总体科学判断仍为 **HOLD**。

## 来源与核验入口

- DAComp 固定代码与此前审计来源见 [DAComp 契约审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)。
- FDABench 官方仓库 README：<https://github.com/fdabench/FDAbench/blob/main/README.md>
- FDABench 官方报告评分实现：<https://github.com/fdabench/FDAbench/blob/main/FDABench/evaluation/evaluation_tools.py>
- FDABench 官方项目页与论文链接：<https://fdabench.github.io/>
- KramaBench 官方代码与评测说明：<https://github.com/mitdbg/KramaBench/blob/main/README.md>
- KramaBench 官方 evaluator：<https://github.com/mitdbg/KramaBench/blob/main/benchmark/evaluator.py>
- KramaBench 官方聚合脚本：<https://github.com/mitdbg/KramaBench/blob/main/evaluate.py>
- KramaBench 论文：<https://arxiv.org/abs/2506.06541>
- *Do Agent Benchmarks Do What They Say? An Executable-Contract Audit of Tool-Using Agent Environments*：<https://arxiv.org/abs/2609.37315>
- *Measurement Risk in Supervised Financial NLP: Rubric and Metric Sensitivity on JF-ICR*：<https://arxiv.org/abs/2604.27374>
- *Same Outputs, Different Scores*：<https://arxiv.org/abs/2611.03377>
- *When Benchmarks are Targets: Revealing the Sensitivity of Large Language Model Leaderboards*：<https://aclanthology.org/2024.acl-long.744/>
- *A Judge-Aware Ranking Framework for Evaluating Large Language Models without Ground Truth*：<https://arxiv.org/abs/2601.21817>

**版本固定：**2026-11-06 通过 GitHub API 将本轮滚动分支固定为 FDABench `72e50a2b59798848a06ad30c5d8a39248c1228bf`、KramaBench `b2e0d77540263f8b6119f977fe79a8c4386b5a02`。固定版本中，本轮读取的主要文件 blob 分别为 FDABench evaluator `6beb63a770b9a5e196542e1639cc4e326b36f976`；KramaBench evaluator `efcdac0cac7f82385ab5cc28091dba0ad8dc4b35`、aggregate script `f1a0b7d099e806c76ddb839d48abafdd39c954dc`、`workload/legal.json` `af7790b631e1fd31efd77c012d1db5dff54ce99c`。这些固定文件可支持后续精确复核；本轮还未对两套完整数据或结果矩阵作普查，因此仍只是结构筛选，不是跨基准负结果的完整统计证据。数据集 revision 也必须在任何后续实证前单独固定。
