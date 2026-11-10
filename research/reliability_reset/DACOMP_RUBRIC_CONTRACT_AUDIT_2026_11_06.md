# DAComp-DA rubric 与 metadata 计分契约核对

日期：2026-11-06
证据状态：**固定发布物中的静态冲突已确认；权威分值定义、对模型比较的实际影响及独立贡献仍未确认。科学状态 HOLD。**

## 核心问题

DAComp-DA 固定发布物中，任务 rubric 的总分标题、逐项/Requirement 上限与 `metadata.json` 的 `Total` 是否一致？若这些来源冲突，原生评分代码选用 metadata 分母是否会系统性压缩或封顶任务分数，并改变模型比较？

## 固定来源与方法

- 固定官方代码树：[`027ccaf20f0d3743d9291fd575d9bc785a5fe3db`](https://github.com/ByteDance-Seed/DAComp/tree/027ccaf20f0d3743d9291fd575d9bc785a5fe3db)。
- 2026-11-06 实时核验上游 `main` 仍指向同一 SHA；其提交时间为 2026-07-10。对 `dacomp-006/019/046` 的 rubric、metadata 与 `rubric_scoring.py` 比对 SHA-256，均与固定树一致。故截至本次检查，候选未在上游 `main` 中被修订；这不证明项目其他私有分支或作者计划中没有修复。
- DAComp Issue #11 于 2026-10-13 提问 Table 5 复现及 `±` 定义，截至本次读取仍显示 Open；现有评论是另一位用户的公开默认参数核查，未看到维护者澄清。Issue 中运行数字仍是报告者自述，不作为本研究复现实验数据。
- 对固定树评分文件复核：英文 `model_scores/` 有一条非汇总记录 `dacomp-006`；随后补查此前未纳入范围的 `model_scores_zh/`，发现中文评分 CSV 有 `dacomp-zh-005`、`dacomp-zh-006` 两条记录。因此固定树共有3条原始评分行、覆盖2个任务ID（006为中英文版本对应任务），仍没有完整任务集的逐题多模型矩阵；不能把中英两个配置差异当作控制充分的配对模型比较。
- 读取 DAComp-DA 英文任务 001–100 的 100 份 `rubric.txt` 与 100 份 `metadata.json`；未调用模型或 Judge API。
- 机器初筛覆盖：metadata 的 `Total` 为 100/100；统一格式可解析 rubric 标题总分 95/100、明示 Requirement 标题上限合计 89/100。对初筛发现的 11 个候选任务，逐个回看固定版本原文中的标题、Requirement/criterion 上限和 metadata。表中“Requirement 合计”是将明示的顶层 Requirement 上限相加所得；不把嵌套 criterion/path 另行相加，也不代表该和数已被裁定为官方权威总分。
- 因 rubric 写法并不统一、仍有 5 个标题和 11 个 Requirement 合计无法由统一规则抽取，本筛查不声称 11/100 是准确总体比例；这是已核实冲突数的下界。parser 计数也不能替代作者说明或独立人工确定计分契约。

## 已核实候选表

下表分别记录 metadata `Total`、rubric 顶部标题值、明示顶层 Requirement 标题的最高分合计。数值顺序为 `metadata / 标题 / Requirement 合计`。

| Task | metadata | rubric 标题 | rubric 层级合计 | 静态观察 |
|---|---:|---:|---:|---|
| dacomp-005 | 28 | 35 | 28 | 标题与 metadata/Requirement 1+2 合计不同；Requirement 1 标题写 24，但其下 Standard 1.2 写 maximum 28，另有内部层级冲突。 |
| dacomp-006 | 16 | 20 | 16 | Requirement 1 写 16；七个 criterion 最大分合计 20；顶标题也写 20，三个来源不完全一致。 |
| dacomp-009 | 38 | 38 | 39 | 标题与 metadata 相同，显式 Requirement 上限合计多 1。 |
| dacomp-019 | 22 | 14 | 14 | rubric 标题及两个 Requirement 各 7 分合计为 14，metadata 为 22。 |
| dacomp-021 | 13 | 13 | 14 | 标题与 metadata 相同，显式 Requirement 上限合计多 1。 |
| dacomp-046 | 18 | 25 | 25 | rubric 标题与 Requirement 1/2 上限合计为 25，metadata 为 18。 |
| dacomp-057 | 36 | 36 | 48 | 标题与 metadata 相同，显式 Requirement 上限合计多 12。 |
| dacomp-068 | 36 | 36 | 66 | 标题与 metadata 相同，显式 Requirement 标题上限合计多 30。 |
| dacomp-082 | 42 | 42 | 50 | 标题与 metadata 相同，显式 Requirement 上限合计多 8。 |
| dacomp-093 | 60 | 60 | 66 | 标题与 metadata 相同，显式 Requirement 上限合计多 6。 |
| dacomp-094 | 36 | 36 | 40 | 标题与 metadata 相同，显式 Requirement 上限合计多 4。 |

**计数解释：**4 个任务的标题值与 metadata 不同；9 个任务的显式层级合计与 metadata 不同；两类候选的并集为 11 个任务。该并集是人工回看过的已发现样本，不是对所有 100 项 rubric 的穷尽证明。

## 条件分值敏感性上界

为了确定后续人工审阅的优先顺序，可先计算每个候选在固定 rubric 原始分 `s` 下，仅替换分母可能造成的总分差上界。令 `M` 为 metadata 分母，`R` 为一个尚待裁决的 rubric 候选上限，假定 `s∈[0,R]`、两个版本都按原生方式把 rubric 百分比裁剪至[0,100]、GSB 分数相同且四项都有效，则：

`max |Δweighted_total| = 60 × (1 − min(M,R)/max(M,R))`

单位为最终 100 分总分中的百分点。此处 `R` 逐项取 rubric 标题值或明示 Requirement 合计中不同于 metadata 的候选值，不代表已经认定正确。

| Task | `M` | 候选 `R` | 上界（总分点） | 依据 |
|---|---:|---:|---:|---|
| dacomp-005 | 28 | 35 | 12.00 | 标题总分；Requirement/metadata 另为28 |
| dacomp-006 | 16 | 20 | 12.00 | 标题与 criterion 合计；Requirement 为16 |
| dacomp-009 | 38 | 39 | 1.54 | Requirement 合计 |
| dacomp-019 | 22 | 14 | 21.82 | 标题与 Requirement 合计 |
| dacomp-021 | 13 | 14 | 4.29 | Requirement 合计 |
| dacomp-046 | 18 | 25 | 16.80 | 标题与 Requirement 合计 |
| dacomp-057 | 36 | 48 | 15.00 | Requirement 合计 |
| dacomp-068 | 36 | 66 | 27.27 | Requirement 合计 |
| dacomp-082 | 42 | 50 | 9.60 | Requirement 合计 |
| dacomp-093 | 60 | 66 | 5.45 | Requirement 合计 |
| dacomp-094 | 36 | 40 | 6.00 | Requirement 合计 |

这些是候选分母间的代数上界，不是观测到的模型分差；它们假定 Judge 能到达相应 `R` 范围，也不表示真实任务协议允许这种替代。`dacomp-006` 的实际 Judge 原始分10使配对差为7.5点，低于该上界12点。优先人工裁决 `dacomp-068`、`019`、`046` 等高敏感项，可减少后续配对评分所需范围；仍需 Reviewer 判断有效分值范围，且分数差本身仍需与多模型比较结果连接。

## 对已发表 DA-Agent 排名的条件性上界

官方 Table 5 的 DA-Agent 均值按顺序为 GPT-5=50.84、Kimi-K2=41.89、Gemini-2.5-Pro=34.70、DeepSeek-V3.1=34.33、o3=28.20、Qwen3-Coder=25.13、Doubao-Seed-1.6=20.74、Qwen3-235B-A22B=13.25、Qwen3-8B=4.47。[论文 Table 5](https://arxiv.org/html/2512.04324#S3.T5)。相邻差中，三强系统的最小差为7.19分；全表最小相邻差则是 Gemini-2.5-Pro 与 DeepSeek-V3.1 之间的 **0.37分**。

如果暂时只考虑以上11个已发现任务，并假定每项候选 `R` 都被确认是权威 ceiling，单个模型在100题均值上的最大变化为 `131.77/100=1.318` 分。对任一任务，替换同一个分母会让所有模型的分数修正同向；不同模型的修正幅度可不同，但该任务对任意模型对分差的改变不超过该任务的 `B_i`。故任意模型对的总均值差改变量上界为1.318分。

**修正后的判定：**1.318小于三强系统的最小相邻差7.19，因此在这些条件假设下，已知11项不能颠倒 GPT-5、Kimi-K2、Gemini-2.5-Pro 三者顺序；但1.318大于全表的0.37，故不能排除 Gemini-2.5-Pro 与 DeepSeek-V3.1 等相邻系统发生排序变化。论文 Table 5 的 OpenHands 子表中，DeepSeek-V3.1=33.87 与 Gemini-2.5-Pro=33.38 相差0.49；若其题目覆盖与本上界假设相同，也不能排除此相邻对换序。上界只说明“可能影响”，不是实际变化证据。当前仅有3条公开逐题评分行，且盲审尚未确认规范 ceiling，因此**实际排名是否变化未知**。先前“已知11项不足以改变 Table 5 全部排序”的结论撤回。

11项上界仍不足以解释 Issue #11 报告的61.08/62.14与 Table 5 的50.84之间10.24/11.30分差。这个限定只针对目前已发现的11项；parser 未解析任务和未审任务仍可能含有额外错配。要判断全表模型比较是否变化，仍需规范盲审、覆盖全部 rubric 的人工边界核验及逐任务多模型原始评分；不能由榜单均值推算重评分结果。此候选仍未通过独立贡献门槛，需与 scorer-policy sensitivity 近邻比较并证明实际结论影响。

## 原生 scorer 的行为

源码进一步确认这是**双来源计分路径**：Judge 提示由任务目录的 `rubric.txt` 生成；英文评分提示把 rubric 的总分解释为最高分，并规定最终分是各 requirement 分数之和。Judge 提示构造没有传入 `metadata.json` 的 `Total`。后续原生 scorer 独立读取 `metadata.json` 的 `Total` 作为分母，对 Judge 的 `rubrics_total_score` 归一化并裁剪到 `[0, 100]`，之后再与 GSB 三项按 0.60/0.10/0.10/0.20 加权。[任务 rubric 加载](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/tasks_loader.py#L25-L58) · [Judge 输入构造](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/tasks.py#L76-L89) · [评分提示定义](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/prompts.py#L81-L109) · [metadata 分母与裁剪](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py#L485-L545)。

这个路径支持一个比“两个文件数值不一样”更明确的可证伪机制：模型依据自然语言 rubric 产生原始总分，程序却用另一文件的 ceiling 进行归一化。若二者不一致，分数会随 `metadata Total` 改变，即使 rubric、模型输出、Judge 输出和 GSB 都固定。因此：

1. metadata 高于 rubric 实际最高分时，原生 rubric 子分可能被压低；
2. metadata 低于 rubric 可能允许的分数时，rubric 百分比会被封顶，可能丢失区分度；
3. metadata、标题、条目若只是文档描述不一致，而 metadata 被设计为唯一规范来源，则原生实现未必违反运行契约。

因此，当前证据支持“Judge 与归一化器读取不同来源，且部分任务静态字段冲突”；作者/独立审阅者仍须确定 intended ceiling，才可称 scorer 算错。该源分离机制是候选研究增量，但仍未证明其跨模型比较影响，不能当作既定论文贡献。

### `dacomp-006` 的分子与分母具体对不上什么

对唯一公开英文 GPT-5 Judge 评分行作逐项核对后，候选比“标题20、metadata16”更具体，也更可复核：

- rubric 标题写总分20，唯一 Requirement 写最高16；其 Criterion 1.1–1.7 的最高分相加为20。metadata 的三个类别上限 `Completeness=4, Accuracy=7, Conclusiveness=5` 合计16，且与前五个 criterion 的类别权重相符；Criterion 1.6、1.7 另增加各2分。
- 公开 Judge JSON 确实给 Criterion 1.6 的 Path A 2分、Criterion 1.7 的 Path A 2分，并报告 Requirement/总 rubric 得分10。也就是说，实际计入分子的评分项包括 metadata 16分类别上限以外的4分。
- 论文 §2.2 将 rubric 分写成“已得权重之和 / 权重之和”，Judge prompt 又规定 rubric 总分是最高分且最终分为各 Requirement 得分之和；原生 scorer 则把 metadata `Total=16` 用作唯一归一化分母。公开材料没有解释为什么被 Judge 计分的1.6/1.7两项不进入该分母。

因此这里可直接核验的是**已评分项目与固定归一化分母之间的结构性不一致候选**，而非仅有两个静态文本数字不同。规范解释仍未裁定：可见的候选上限至少有 metadata/Requirement 16、任务总标题/criterion 全局最高20；若按该行所选路径替代同层最大路径，结构派生上限暂算19（1.2选了3分Path B而不是4分Path A）。19是依据评分轨迹的敏感性口径，不是官方公布值或已确认正确分母。于是相同原始 Judge=10、GSB=(40,0,20) 下：分母16重现原生45.5；分母19得约39.58；分母20得38.0。后两者都是条件重算，不是已裁定的修正分。

这使得候选机制从“评分规则敏感”升级为一个具体可证伪观察：**Judge实际把哪些 rubric 项计入分子，是否与归一化器采用的任务 ceiling/维度上限属于同一计分契约？** 当前共找到3条公开评分行，但criterion 1.6/1.7被计入分子而metadata分类上限未覆盖的现象，只有英文GPT-5 `dacomp-006` 一行直接展示；中文两行的任务/模型/语言配置不匹配，不能确认机制复现。19/20/16的权威仍需盲审或作者澄清；不能推断其普遍性、错误率或排名影响。

## 英文 GPT-5 唯一评分行的配对复算

固定发布物中的英文 GPT-5 rubric 评分 CSV 只有 `dacomp-006` 一条评分行。原始 Judge 总分为 10，metadata 分母为 16，GSB 分别为 40、0、20；官方权重得到总分 45.5，与公开 CSV 相同。

若人工/作者判定 20 才是这条任务的规范分母，则相同 Judge 与 GSB 输出对应 rubric 50% 而非 62.5%，总分为 38.0，配对差为 **7.5 个总分点**。若按记录所选路径的暂定19分上限，总分约39.58，配对差约 **5.92个总分点**。这些均由尚未裁决的规范口径导出，**不是已证实的正确分数、模型效应或榜单变化**。其它10个候选没有公开的逐任务 Judge 分数，因此不能估算真实总分影响。

原生代码证据：[rubric_scoring.py（归一化与裁剪）](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py#L485-L545)；[get_score.py（按任务汇总公开列）](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/get_score.py#L64-L98)。样本来源：[dacomp-006 rubric](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/src/dacomp-006/rubric.txt)、[metadata](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/src/dacomp-006/metadata.json)、[公开 GPT-5 评分 CSV](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/model_scores/gpt-5-2025-08-07-test1__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv)。

### 补查中文评分行：扩展证据，但不构成独立复现

**[事实]** 固定树的 `model_scores_zh/` 另有 Qwen3-Coder-Plus 两条原始评分行：`dacomp-zh-005`（rubric=19、metadata=28、final=40.7143）与 `dacomp-zh-006`（rubric=4、metadata=16、final=17）。这修正了“整个固定发布物仅有一条任务评分行”的宽泛陈述：准确说法是英文目录一行，固定发布物合计三行、两个 underlying task IDs。来源：[中文评分CSV](https://raw.githubusercontent.com/ByteDance-Seed/DAComp/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/model_scores_zh/openai_qwen3-coder-plus-test1-zh__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv)。

- `dacomp-zh-005` rubric 标题35，Requirement 上限24+4=28，metadata `Total=28`；标准1.2自身写最高28，超过所属Requirement上限24。公开Judge给标准1.1=3、标准1.2=12、需求2=4，raw合计19，没有证据显示这条实际输出超过metadata分母。故它扩大了“静态层级冲突并有公开输出”的证据，但当前只支持敏感性分析。
- `dacomp-zh-006` 是英文 `dacomp-006` 的对应任务版本；metadata16、rubric总标题20，公开Qwen评分raw=4，1.6/1.7均为0。它与英文GPT-5版本的原始输出不同，且语言、agent和运行配置共同变化，不能当成模型间配对差。
- 因而“分子计入metadata类别上限之外的4分”目前只在英文 `dacomp-006` 的GPT-5评分行被直接观察到。中文行提供一个同任务/异语言/异模型的结果对照，但不能独立验证同一打分缺陷，也不能支撑排序效应。

### 三条已公开记录的分母敏感性（条件重算）

下表固定每条记录已有的 Judge rubric 分、GSB 结果与官方权重，只将归一化分母从 metadata `Total` 换成 rubric 顶部声明的总分。它展示的是**已发布分数对分母解释的敏感度**；标题分母尚未被裁定为正确值，不应称作修复分数或模型效应。

| 记录 | rubric raw | metadata 分母 → 标题分母 | 原生总分 → 条件总分 | 条件变化 | 限制 |
|---|---:|---:|---:|---:|---|
| 英文 GPT-5 `dacomp-006` | 10 | 16 → 20 | 45.50 → 38.00 | -7.50 | 唯一直接观察到 rubric 1.6/1.7 各得2分、且对应分值不在 metadata 类别上限中的行。 |
| 中文 Qwen3-Coder-Plus `dacomp-zh-005` | 19 | 28 → 35 | 40.7143 → 32.5714 | -8.1429 | GSB 合计为0；rubric 内部层级也冲突，35并非已裁定分母。 |
| 中文 Qwen3-Coder-Plus `dacomp-zh-006` | 4 | 16 → 20 | 17.00 → 14.00 | -3.00 | GSB 结果固定不变；raw score 没有 rubric 1.6/1.7 得分。 |

这三行让研究问题比“存在静态字段冲突”更具体：即使只看官方已公开的任务级输出，几种公开材料都可能诱导出不同归一化口径；然而目前没有受控模型对照、独立分值裁决或榜单终点。此表只提升了**条件性测量敏感性证据**，没有跨过独立论文贡献门槛。[固定英文 GPT-5评分CSV](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/model_scores/gpt-5-2025-08-07-test1__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv) · [固定中文 Qwen评分CSV](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/model_scores_zh/openai_qwen3-coder-plus-test1-zh__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv)

上述补查使证据从1行变为3行，但科学结论没有跨过门槛：没有全量逐题结果、没有盲审权威裁定，也没有匹配任务与配置下的多模型排序分析。不能再写“只有一个公开任务级评分行”，应写“仅3条公开原始评分行、覆盖2个底层任务ID”。

## 固定版原始 Agent 结果资产清点 — 2026-11-07

对固定 commit 的 `dacomp-da/evaluation_suite/agent_results/` 目录逐层清点并读取四个 `*-traj.txt` 与对应 Markdown 报告：英文 GPT-5 有 `dacomp-006`、`dacomp-063` 两条示例轨迹；中文 Qwen3-Coder-Plus 有 `dacomp-zh-005`、`dacomp-zh-006` 两条。每例均有轨迹和报告，另有图像产物。固定评分 CSV 中只有三行：GPT-5 仅 `dacomp-006`，Qwen 两行分别是 `dacomp-zh-005/-006`；`dacomp-063` 没有对应评分行。目录中的样例轨迹不是全量产物，也没有 Issue #11 两轮 100 题重跑的记录。

| 固定发布路径 | 轨迹 Git blob | 报告 Git blob | 对应固定评分行 |
|---|---|---|---|
| `agent_results/gpt-5-2025-08-07-test1/dacomp-006/` | `978e86e9d8ada7e199d8f6270d7acffd7a6da0b2` | `0d13e646db82ac2f8a6b3876e8527a32f51c9f3d` | 有：英文 GPT-5 `dacomp-006` |
| `agent_results/gpt-5-2025-08-07-test1/dacomp-063/` | `461bae85ecdb715aca9f21ac808864102c10b869` | `6883b22c67c71776dffb7a84b8d6ca42bdf748b6` | 无 |
| `agent_results/openai_qwen3-coder-plus-test1-zh/dacomp-zh-005/` | `cbd0634ce6e6f8b392c71d80b6edc33200da2ef8` | `73b4e4ff4679919a2dc988da9ea137bc945fcd46` | 有：中文 Qwen `dacomp-zh-005` |
| `agent_results/openai_qwen3-coder-plus-test1-zh/dacomp-zh-006/` | `aa4123c41948ec8d8345a54ebece77bf151a9994` | `d4d653df0d0e853821d6be0271fb6f608455a84a` | 有：中文 Qwen `dacomp-zh-006` |

这四份样例可供单轨迹核验，但不能支持多模型、多任务评分比较。英文 `dacomp-006` 与中文 `dacomp-zh-006` 是对应任务版本，但语言、模型/Agent 与运行配置同时不同，不能据此归因模型差异。两阶段盲审表目前仍未填写；本次没有运行 Agent、Judge 或模型 API。

另直接复核固定 scorer 的 `compute_file_score()`：`full_score` 取自 `metadata.Total`，rubric 总分除以该值后裁剪至 `[0,100]`，再进入固定加权总分。对任务 `dacomp-006`，rubric 顶部写20分、Requirement 1 标注16分，子标准1.1–1.7最大值合计20；metadata `Total=16`。代码证实实际归一化来源是 metadata，但不能单独裁定发布文本中哪一处应优先，因此候选仍是“规范分值不可由公开材料唯一确定”，不是已确认的 scorer bug。

## 官方当前主分支结果文件复核 — 2026-11-07

通过 GitHub API 重新读取官方 `main`：`main` 当前仍指向固定 commit `027ccaf20f0d3743d9291fd575d9bc785a5fe3db`。直接列出 `agent_results/` 下两个运行目录，其子目录恰为英文 GPT-5 `dacomp-006/-063` 与中文 Qwen `dacomp-zh-005/-006` 四个任务。对公开 CSV 按 RFC 风格引号规则计数（rubric JSON 单元格内含换行，不能直接按物理行数计）：英文 GPT-5 原始评分 CSV 为1条数据记录（仅 `dacomp-006`），中文评分 CSV为2条（`dacomp-zh-005/-006`）；每个 `overall_results.csv` 也只含相应运行配置的1条汇总记录。当前主分支没有公开的多模型×多任务逐题评分矩阵，不能连接榜单中的近邻模型对做真实配对重算。该核验确认而非改变上一节的资产计数。来源：[main commit](https://github.com/ByteDance-Seed/DAComp/commit/027ccaf20f0d3743d9291fd575d9bc785a5fe3db) · [agent_results目录](https://github.com/ByteDance-Seed/DAComp/tree/main/dacomp-da/evaluation_suite/agent_results) · [英文评分CSV](https://github.com/ByteDance-Seed/DAComp/blob/main/dacomp-da/evaluation_suite/model_scores/gpt-5-2025-08-07-test1__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv) · [中文评分CSV](https://github.com/ByteDance-Seed/DAComp/blob/main/dacomp-da/evaluation_suite/model_scores_zh/openai_qwen3-coder-plus-test1-zh__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv) · [官方复核流程](https://github.com/ByteDance-Seed/DAComp/blob/main/dacomp-da/evaluation_suite/README.md)。

## 与直接近邻的边界

*Same Outputs, Different Scores: Auditing the Unchecked Graders of Multimodal LLM Benchmarks* 已经在 8 个多模态选择题基准、5 个模型上固定输出并改变答案解析/回退规则，报告最高 22 个百分点的得分变化，并以盲审校准实际作答。它已经覆盖了“同一输出、不同 scorer 导致分数不同”这一宽泛主张；本项目不能把 scorer 审计或规则敏感性本身作为新贡献。[论文](https://arxiv.org/abs/2611.03377) · [全文](https://arxiv.org/html/2611.03377v1)

本候选只可能剩下一个窄边界：**开放式数据分析任务中，Judge 读取自然语言 rubric、程序读取外置 metadata ceiling；当两者冲突时，对模型原始得分进行不同归一化的效应是否会系统性改变比较。** 近邻的 scorer paper 改变答案解析/回退规则并对相同原始输出作重评分，已证明通用 grader sensitivity 和分差不是新贡献；本项目可能的增量只能是跨文件 ceiling 的规范来源分裂、可识别性及其对实际多模型结论的后果。PReMISE 对 rubric 的结构充分性、可靠性、偏好拟合和对抗鲁棒性进行审计；RuVerBench 研究 Agent 场景中 Judge 对 rubric 满足关系的可靠性。它们都提高创新门槛，不能仅凭摘要断言没有覆盖此相邻问题。[PReMISE](https://arxiv.org/abs/2605.30803) · [RuVerBench](https://arxiv.org/abs/2606.29920)

另两项近邻进一步关闭了更宽的表述：*When Benchmarks are Targets* 已证明多选基准对选项顺序、答案选择等评测细节敏感，排名可明显变化；*A Judge-Aware Ranking Framework* 已对异质 Judge 的模型比较估计排名及不确定性。因此，**一般的评测扰动会改变排名**和**用区间表达排名不确定性**均不能构成本项目贡献。它们未直接证明 DAComp 的 rubric 与 metadata ceiling 分裂已被处理；剩余差异仅可能是这种跨文件规范冲突经独立裁定后是否真实改变固定开放式任务输出的比较。[When Benchmarks are Targets](https://aclanthology.org/2024.acl-long.744/) · [Judge-Aware Ranking](https://arxiv.org/abs/2601.21817)

## 当前裁决与下一阶段门槛

**HOLD，不声称独立论文贡献。** 当前材料证明固定 DAComp-DA 发布物至少有11个静态ceiling冲突候选，Judge与normalizer分别读取rubric与metadata；3条公开原始评分行中，英文GPT-5 `dacomp-006` 在条件分母20下改变7.5分，中文两行没有复现“额外criterion计入分子”的同一现象。尚无作者/盲审对规范ceiling的裁决、其它候选任务评分、受控跨模型配对重算或完整解析覆盖，因此不能断言发布分数有错或模型比较被误导。

要继续推进此线，最小的科学工作顺序是：

1. 使用[三阶段盲审包](DACOMP_CONTRACT_REVIEW_PROTOCOL_2026_11_06.md)，让两位审阅者独立判断14个候选和10个随机对照；Stage 1 只看 rubric，锁定后揭示 metadata，再在 Stage 3 对照论文方法与实现。如不能判断，标记“规范本身不充分”，不猜作者意图。
2. 申请或取得合法的逐题多模型原始 Judge 结果；没有它，就把研究问题限制为评分契约设计，不能宣称排名变化。
3. 预注册按 metadata、rubric 声明上限和结构派生上限进行的三种配对重算，报告裁剪次数、分数差、模型对差及排名变化；对分歧任务进行双盲独立裁决。
4. 与至少一个结构不同的开放式 benchmark 重复同一审计，或将贡献限为 DAComp 单基准案例并降低论文主张。
5. 若独立审阅多数任务认为 metadata 是唯一规范来源，或配对重算不改变任何预注册结论，关闭该论文方向。

不调用模型/Judge API、不从总体排名反推逐题分数。固定近邻 *Same Outputs, Different Scores* 已将宽泛的 scorer-rule 影响主张占住，因此后续增量必须集中于规范来源的可判定性及其对模型比较的实际作用。

## 论文方法与固定 scorer 的分母定义复核 — 2026-11-07

**[事实｜论文方法]** DAComp 论文 v1 §2.2 说明 Judge 对每个 sub-requirement 选择最佳匹配路径，只应用该路径下的 rubric items，再自底向上聚合；随后将 rubric score 写为 `Σ s_k / Σ w_k`，且每项 `s_k ∈ [0,w_k]`。论文 App. 10.3.2 将 Requirement、Standard、Path、rubric item 定义为四层结构，App. 10.3.3 要求 rubric 语句具体、无歧义。来源：[论文 v1 §2.2](https://arxiv.org/html/2512.04324v1#S2) · [层级结构与作者规则](https://arxiv.org/html/2512.04324v1#S10)。

**[事实｜固定实现]** 固定 scorer 的 `compute_file_score()` 将 `full_score` 直接赋为 `metadata.Total`，以 `rubrics_total_score / full_score` 归一化后裁剪到 `[0,100]`；该函数不读取 rubric 路径，也不从输出重建选中 leaf-item 的权重和。`compute_weighted_total()` 后续将该 `rubrics_percentage` 以0.60权重与三个 GSB 分量（0.10、0.10、0.20）组合，所以分母差异确实进入最终发布总分，而不只是一个未使用的诊断列。来源：[固定版 rubric_scoring.py，归一化和总分组合](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py#L307-L312) · [归一化代码](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py#L565-L578) · [加权总分代码](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py#L430-L463)。这证明了论文所述公式与发布实现使用的分母表达不同；它本身还不能证明实现错误，因为论文方法是否允许固定 task-level metadata 作为实现分母、或是否有其他正式定义，尚无作者解释。

**[事实｜dacomp-006 上限]** 原始 rubric 的 criterion maxima 为：1.1=3、1.2=3或4、1.3=1/3/4、1.4=3、1.5=2、1.6=2、1.7=2。按路径组合，其显式上限可在16至20之间；rubric 标题为20，唯一 Requirement 又写16，metadata `Total` 也为16。故该例并非简单的“论文公式给出唯一20”：论文公式需要确定每个 sub-requirement 的实际所选路径及相应 `w_k`，而 rubric 同时含路径上限不同的替代路径。

**[事实｜公开输出可重建边界]** 英文 GPT-5 `dacomp-006` Judge JSON 记录了正分标准的路径证据：1.1.A、1.2.B、1.6.A、1.7.A；1.3、1.4、1.5 均为0分并保存空的 `best_path_analysis`，没有记录这些未满足标准采用的路径。raw rubric score 为10，metadata 分母为16，原生公开总分为45.5。因零分标准缺少所选路径，公开输出不能重建论文公式所需的完整 `Σ w_k`；将分母设为16、19或20所得分数只是条件敏感性，不是修正值。来源：[固定 GPT-5 评分行](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/model_scores/gpt-5-2025-08-07-test1__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv)。

**[推断｜候选边界修订]** 现有证据足以把候选从单一的 rubric-vs-metadata 字段冲突，收窄为一个三层可审计问题：任务 rubric、论文公布的路径归一化方法、固定代码/metadata 分母能否给出同一个可重建的任务分数契约。它仍可能只是单任务文档/实现不一致；三个公开评分行、一个英文直接观测任务、缺失的零分路径记录以及尚未发送的独立审阅材料，都不足以支持系统性错误或模型比较改变。候选维持 **HOLD**，不启动 API 或模型实跑。

**[待补｜独立审查]** Stage 1/2/3 表均为空、审阅包尚未发出。两位审阅者应先锁定 rubric-only 判断，再查看 metadata，最后查看论文 §2.2/App. 10.3 与固定 scorer；分别判断：`(a)` rubric 自身是否定义唯一分母，`(b)` 论文公式是否可由已保存输出重建，`(c)` 固定代码是否执行该公式，`(d)` 现有材料能否裁定这属于实现偏差、仅文档差异或证据不足。分歧和“无法判定”均保留；不能让 reviewer 把 metadata 的存在直接等同于规范正确。

## 路径子项超过父级 ceiling 的补充核对 — 2026-11-07

**[事实｜固定源手工核对]** 对 pinned commit `027ccaf20f0d3743d9291fd575d9bc785a5fe3db` 的三个 rubric 作逐行核对：

- `dacomp-052` 标题总分与 `metadata.Total` 均为30。Criterion 2.1 声明 Max 4，而路径2.1.A、2.1.B、2.1.C的子项上限各为1+4+1=6；Criterion 2.2 声明 Max 3，而其至少两条路径也各列6分子项。
- `dacomp-063` Criterion 1.1 声明 Maximum 4 points；路径1.1.B下子项分别为1、3、1分，合计5。
- `dacomp-084` Standard 3.1 声明 Max 3；路径3.1.B明示4 points。

**[事实｜评分流程]** 固定英文 Judge prompt 写明 `Requirement score = sum of its criteria scores`、`Criterion score = ... best-path score`、`Best-path score = sum of the matched path's sub-criteria scores`，未明确写出最佳路径和超过父级 ceiling 时是否再截断。固定 scorer 以 `metadata.Total` 为分母并将比例 clip 至100。这足以确认 rubric 声明与评分步骤之间存在需解释的边界；不能证明实际 Judge 对以上三题给过超上限分数。

**[条件算术｜不是实验观测]** 对 `dacomp-052`，逐个 criterion 只取一条 rubric 标示的路径后，上限为 `7+6+6+6+6+6+6=43`，而标题、criterion maxima 合计和 metadata 均为30。若固定 Judge 输出 raw=43，代码将计算 `43/30×100=143.3%` 并裁剪为100。公开资产没有该任务评分行，故这只是从明示路径规则导出的可检验边界，不是观测到的 Judge 结果或已发生的饱和。

**[事实｜结果资产限制]** `dacomp-063` 有公开 GPT-5 报告和轨迹，但无对应评分 CSV 行；`dacomp-052` 与 `dacomp-084` 当前无公开评分行/模型输出。已有 `dacomp-006` raw=10、metadata=16的真实记录未超出 ceiling，故不能作为分数饱和证据。此次没有创建模型结果或调用 Judge/API。

**[上游资产检索｜2026-11-07，范围更新]** 官方仓库仍指向固定 `main` commit `027ccaf20f0d3743d9291fd575d9bc785a5fe3db`，无 tag/release；两个开放 PR 的文件清单未包含 DAComp-DA 原始 Judge 结果或评分矩阵。另以 `git ls-remote` 核对当时可见的7个公开 fork：6个 `main` 与固定官方 commit 完全相同；`schumannx/DAComp` 与 `zyairehhh/DAComp` 指向其共同祖先 `1825069`；`zhejunliux/DAComp` 指向 `c8c1305`，它从该祖先增加的一项可见修改仅调整 DAComp-DA Judge 请求重试次数和等待时间。该 fork 相对固定官方树的差异还包含官方祖先之后的 OpenHands runtime 更新，不能误认成 fork 新贡献。抽查官方历史中的 `rubric_scoring.py` 修复只将默认任务范围从1–50改为1–100，没有产生模型评分结果。由此，在核对的官方 main、两个开放 PR、7个公开 fork 的 main 及其可见提交范围内，未找到可补用的 `052/063/084` Judge 评分行或多模型评分矩阵；这不覆盖其他分支、已删除/未索引 fork、作者私有产物或外部归档，也不证明这些结果不存在。

**[探索性筛查限制]** [路径上限清点](DACOMP_PATH_WEIGHT_CENSUS_2026_11_07.csv)由启发式 Markdown 解析器生成，82/100 行被标记为解析完整；其范围外、路径和、越过父级上限计数尚未逐项人工验证，不能作为总体比例或缺陷率。仅将人工核对的 `052/063/084` 加入候选审阅，不把其他 parser 标记直接升级为候选。

**[研究判定]** 这将既有“rubric—metadata ceiling”问题具体化为“所选路径子项求和是否越过显式父级上限，以及任务级 normalizer 是否掩盖超额”。近邻已覆盖一般 scorer 规则扰动；独立贡献只可能来自该层级契约冲突对真实输出分布或模型比较的可重复影响。24题审阅包（14个候选、10个固定随机对照）已在外发前重建；两阶段表仍为空，Stage 3 也未填写。审阅和实际原始评分未完成前，模型/API实验不准入，项目整体继续 **HOLD**。
