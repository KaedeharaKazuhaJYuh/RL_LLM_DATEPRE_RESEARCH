# 0.5.65-dev VeriCost：研究主张决定的证据输入（不作决定）

2026-10-21。**本文件只提供证据，不作出定位决定。** 决定权在项目所有者；本文件把 0.5.65 离线核心产生的
数字、它们对两个候选主张的含义、仓库自身的六道门与 NO_GO 条件的逐条对照，以及"什么新证据会改变结论"
列齐，使决定可以在证据之上作出，而不是在叙述之上作出。

所有数字直接取自已提交产物：`faultda_bench/reports/vericost565/{analysis,gate0_rev1_dev,gate0_d1_dev,
learned_eval,offline_eval,dp_certificate_dev,cross_version}.json`，没有任何数字在本文件中被重新计算或估计。
全部结果带 `split: development`、`seen_cluster: true`、`independent_test: false`、
`generalization_claim: none`；**没有真实模型结果，没有独立测试集，没有新来源，没有任何 provider 请求。**

## 1. 本版本实际建立的事实

1. **精确 DP 上界是可核验的。** `dp_certificate_dev.json` 的 C1–C5 全部 `pass`，`tol = 1e-9`，
   `mi_threshold_bits = 1e-12`，最大违反量分别为 C1 1.11022302463e-16、C2 1.11022302463e-16、
   C3 3.33066907388e-16、C4 3.33066907388e-16、C5 0.0，`c3_scope: "full"` 未缩减。
   证书失败即不写文件（五个变异演示见 `wf-0565/guard-demonstrations.md`）。
2. **主 regime 上廉价固定规则落在 ε 之内（头条结论）。** 预注册的主实例集 DEV-SYN、rev-1 latent 模型下，
   8 个 regime 的 `min_fixed_r` 为
   `[0.00868277714933, 0.0100105068447, 0.00482207434742, 0.0319121154715, 0.0103696861875,
   0.0315391087846, 0.00655102071841, 0.039351727369]`（regime 顺序 k0.03_L1 … k1.00_L3），
   每一个都 ≤ ε = 0.05，因此 `hard_stop: true`、`trigger: true`、`scope: "measurement"`；
   主 regime `k0.30_L3` 上 `min_fixed_r = 0.0315391087846`，`E[U*] = 0.682267789726`，取到最小值的 family 是
   **F_hist**（9 单元 MAP-type × 规模查表）。**不作任何"不可绕过"声明。**
3. **这一可绕过性是合成形状 profile 的性质，不是真实已见切片在 κ = 1 上的性质。** 同一 ε 下
   DEV-SEEN 的 `min_fixed_r` 在 `k1.00_L1` / `k1.00_L3` 为 0.0999024644006 / 0.180085602665，
   ALL 集为 0.0744909677605 / 0.135920618803，均 > ε，故这两个集上 `hard_stop: false`、`trigger: false`。
   三个集各自携带完整 `decision` 块，没有任何一个被隐藏；顶层 `decision` 按预注册取 DEV-SYN。
4. **单条固定规则并不能一招通吃。** 每个集、每个模型的 `single_rule_literal.within_epsilon_all_admissible`
   都是 `false`：没有任何单个 f ∈ F 能在所有可采纳 regime 上同时落在 ε 内；绕过依赖逐单元查表。
5. **没有任何 CPU 学得策略在同等代价下胜过最佳固定规则。** 主 regime 归一化期望 regret：
   `bf = F_hist` 0.014189449731 < `thompson` 0.0241588323286 < `linucb` 0.155694955762 <
   `q_only` 0.307923762624。确认性假设 O2（`q_only` > `bf`）判定 **FALSIFIED**（被点估计否证）：
   四个 cluster 的 ΔU 全为负（synthetic −2.44327118094、uci_auto_mpg −1.3029029437、
   uci_glass −1.20536320603、uci_occupancy −1.25734943368），均值 −1.55222169109，
   精确单侧符号翻转 p = 1.0，`dominated: false`（`q_only` 便宜 0.0576311217151 个代价单位，但安全性低
   0.257396515255，因此不被 Pareto 支配，仅在效用上被否证）。探索性的 `thompson`（ΔU −0.0526826156682，
   被 `bf` 支配）与 `linucb`（ΔU −0.747777519439）同样 FALSIFIED。
   三个学得 arm 的 `gap_recovered` 全为负（q_only −20.7008952751、thompson −0.7025912059、
   linucb −9.97258587986，分母 0.299933248386 > gap_floor 0.01，故有定义）：没有任何学得 arm 回收了
   bf 到 DP 之间的任何一部分差距。实跑 episode 上 `q_only` 对 `bf` 的精确 McNemar 为 0 胜 24 负，
   p = 1.19209289551e-07（描述性）。
6. **功效声明（产生数字之前写入）。** 开发集只有 4 个 cluster，精确单侧符号翻转检验的最小可得 p 为
   `2^-4 = 0.0625 > α = 0.05`，任何 p 都不可能达到显著。因此除被点估计或支配关系判为 FALSIFIED 之外，
   O 系列只能是 `INCONCLUSIVE (under_powered)`。O2 的 MDE 为 0.991834342603 U 单位 =
   0.0469223856362 归一化 regret 单位；观测效应 −0.0734335782233 regret 单位，量级大于 MDE 但方向相反。
7. **表示能力不是借口。** 用 DP 自身的动作价值给同样的 9 个 gate 动作打分，greedy 结果就是
   `spot_flagged`，coverage mapping 测试通过；因此"学得不如规则"不能被解释为动作集被削弱。
   另一方面，在预注册配置与 episode 预算下 tabular Q 确实**训练不足**：post-flag 状态的 DP 动作为
   `spot:1`（状态价值 0.9391），而 Q 的 greedy 动作在 type-A 历史下是 `escalate`，type-B/C 历史下该状态
   从未被访问；20 000 / 50 000 episode 仍为 `escalate`，1 000 000 / 3 000 000 episode 变为 `full`
   （Q = 0.700 = V − κ），`spot_flagged` 仅 0.615 / 0.698。20 000 个预注册 episode 的长度分布为
   `{1: 13848, 2: 4525, 3: 1053, 4: 531, 5: 41, 6: 2}`，69% 的 episode 只有一个决策。
   三条区分必须保持锋利：**不是表示能力缺陷**；**是预注册预算下的训练不足**；**其他配置是否能恢复该动作
   未经测试**，本文件不声称"没有学习器可以做到"。

## 2. 对两个候选主张的含义

### 候选 A：「可验证终止/验证诊断相对已有 Benchmark 有独立增量」

本版本的证据**不支持**这一主张，并且在两处直接削弱它：

- 主 regime 上一个 9 单元查表就落在 ε 内（事实 2）。若主张的核心是"模型/方法必须付出可验证的验证代价
  才能正确终止"，那么在本版本的主实例集上，这个代价结构**被一条廉价固定规则以 0.0315391087846 的
  归一化 regret 绕过**。这不是推测，是精确期望值。
- 学得策略没有在同等代价下胜过规则（事实 5），而这正是仓库自己的 NO_GO 条目之一；由于表示能力已被
  独立确认（事实 7），该 NO_GO 不能被解释为动作集缺陷造成的假象。

仍然属于候选 A 的**未被否证部分**：真实已见切片在 κ = 1 的两个 regime 上不被 ε 内的固定规则覆盖
（事实 3），且 D1 latent 模型下 DEV-SYN 的 `k1.00_L3` 为 0.0522962496574 > ε（`hard_stop: false`、
`live_round_verdict: PASS`、`model_used: d1`）。这给出了一个**未来实跑的可用配置**，但它本身不是增量证据：
本版本没有任何模型结果。两件事必须分开陈述，不得互相掩盖。

### 候选 B：「定位为工程诊断 Benchmark」

本版本的证据**与候选 B 一致**，并且提供了候选 B 所需要的那种东西：一个带可核验最优性证书的精确代价/效用
模型、一张逐 regime 的可绕过性地图（含取到最小值的 family 与成员）、13 个 arm 的离线对照、
一次性写入与跨解释器字节一致的证据链，以及把每个阴性结果都保留下来的记录。
候选 B 不需要"学得策略胜过规则"，也不需要独立测试集。

**本文件不在 A 与 B 之间作出选择。**

## 3. 仓库自身六道门的逐条对照（引自 `faultda_bench/docs/R_COMPARISON_0520.md`）

| 门 | 原文（节录） | 本版本证据下的状态 |
| --- | --- | --- |
| 1 接口门 | 「先独立确认目标 request、回执读取事件、发布尝试、责任交接及实际动作来源」 | **未通过（未解除）**：`independent_review: not_arranged` 仍成立，本版本没有任何 request 或回执，环境是离线模拟。 |
| 2 同权限门 | 「两者共用合法观察、工具、运行时约束及帮助」 | **在 arm 之间通过，但是空载通过**：所有 arm 共用同一个按字节计价的分页环境，公开观测在任何 latent 下逐字节相同（C2 证书），固定规则不读私有真值；但**没有模型 arm**，因此该门没有被非空载地检验。 |
| 3 同面板门 | 「所有臂在初始任务上使用共同、独立审查且事前冻结的分母」 | **部分**：分母共同且事前冻结（30 个 profile、8 个 regime、13 个 arm，`vericost_v1_instances.json` + 预注册），但**未经独立审查**，且全部是已见 cluster。 |
| 4 目标门 | 「安全完成、确认历史违规后的升级、真正信息不足的升级各自定义」 | **通过（在本版本范围内）**：`safe_complete`、`false_completion`、`forbidden_effect`、`safe_escalation`、`unsupported_escalation`、`dominated_reads`、`wrong_publication` 逐项分列于 `offline_eval.counts_by_arm`；`unsupported_escalation` 全 arm 为 0。 |
| 5 实际成本门 | 「检查、写入、决策、字节、token、帮助计算、时延和费用分列；相同上限不是相同实际成本」 | **部分**：检查/写入/决策/字节/代价单位逐项分列并按 `B_ref` 归一化，墙钟与 CPU 时间逐产物记录；**token 与费用为 0（无 provider 请求），能耗未测**。 |
| 6 科学门 | 「差距消失、仅重现已知恢复失误，或独立审阅不能指出具体非平凡增量时，不继续机制主张」 | **未通过，且被本版本加强**：主 regime 上差距被廉价固定规则收进 ε 之内（事实 2），独立审阅仍未安排。 |

## 4. NO_GO 条件的逐条对照（引自 `tests/fixtures/vericost565_rejection_conditions.txt`）

来自 `RESEARCH_CONTRIBUTION_DESIGN_2026_10_19.md` 的清单：

| 条件 | 是否触发 | 证据 |
| --- | --- | --- |
| the method equals existing memory repair or active information acquisition | 不适用 | 本版本未提出新方法，只建立代价/效用测量与 DP 上界。 |
| gains come only from privileged evidence or helpers | 否 | 公开观测逐字节相同（C2），`read_rows` 按整 part 字节计费，无特权证据。 |
| **the strong rule or full recompute dominates** | **是（部分，但关键）** | 主 regime 上 `bf = F_hist` regret 0.014189449731，强于全部学得 arm；`always_full_recompute` 本身在主 regime 上 regret 0.252907632527（并不占优），但 F_hist 这一廉价规则占优。 |
| **RL does not beat a rule or SFT with the same representation** | **是** | 事实 5；且表示能力已独立确认（事实 7），该条触发不能被解释为动作集缺陷。 |
| only the old dev cluster shows it | **是** | 4 个 cluster 全为已见/合成，`independent_test: false`。 |
| it only proves that models sometimes err | 不适用 | 本版本没有模型执行。 |

来自 `RESEARCH_RESTART_2026_10_19.md` 的清单：`ordinary postconditions already cover it`（无法在本版本判定，
需要文献级独立审查）；`it reduces to version-key matching`（否）；`the difference comes from missing information
or unequal help`（否，信息对等已由 C2 证明）；**`full recomputation removes the phenomenon at the same budget`**
（在 κ 小的 regime 上**是**：`k0.03_*`/`k0.10_*` 上 `always_full_recompute` 的 regret 为
0.00870621458694 / 0.00575957607954 / 0.0483514661071 / 0.0393047840221，全部 ≤ ε；在 κ = 1 上**否**，
regret 升至 2.33335956123 / 2.77076888306）；**`only the old dev cluster shows it`**（**是**）。

`Protocol V2 §7` 要求的「至少 6 个全新独立来源」「以来源 cluster 而非 episode 为单位」「效应与功效在看到最终
数据前固定」：本版本**没有新来源**（0 次下载），单位确实是来源 cluster（4 个），MDE 与功效在产生数字之前
写入并以修正条目 seq 1/2 记录。`historical_sources.json` 的 `final_test_sources` 仍为空。

## 5. 独立技术复审的印证（0.5.50 / 0.5.55）

`/projects/sandbox/RL_LLM_DATEPRE_RESEARCH/.agents/tasks/termination-protocol-review.md` 是对上两个版本的
独立技术复审（同一自动化代理血统，**不能解除任何待定人审门**，其 §7 自述如此）。其执行摘要的结论与本版本
证据方向一致：R 的机制路线在仓库自身六道门下仍为 NO_GO（其 §6 认定六道门中四道失败、一道部分、一道空载通过，
并逐条认定两份 NO_GO 清单中共六个条件被满足），建议把 0.5.50–0.5.60 **定位为工程诊断 Benchmark 而不是独立
研究增量**。本版本独立地在一个不同的层面（精确 DP 上界 + 代价定价 + 可绕过性地图）得到同向证据。
**这仍然是证据，不是决定**；两份文档都不能替代独立人审。

## 6. 什么新证据会改变结论

| 新证据 | 会改变什么 | 代价与风险 |
| --- | --- | --- |
| **独立留出来源集**（≥ 6 个全新来源、血缘隔离、评估前冻结） | 直接解除"只有旧开发簇"与"同面板门部分"两项；使 cluster 数从 4 升到可判定显著性的量级（k ≥ 6 时 2⁻ᵏ = 0.015625 < 0.025） | **一次性消耗**。本版本故意未获取（`rescope_heldout_deferred_until_claim_decided`）：主张未定之前消耗独立测试集是不可逆的浪费。 |
| **一次实跑模型轮次**（本文件之外的 `VERICOST_0565_LIVE_PROTOCOL.md` 协议） | 非空载地检验同权限门，给出 H1–H3 的首批证据；D1 latent 模型下 `k1.00_L3` 已有一个不被 ε 内固定规则覆盖的配置可用 | 需要解除 API HOLD、实现 provider 路径与预算守卫；¥30 授权已结转但未动用。 |
| **第二个 provider / 第二个模型** | 排除"结论是单一供应商实现细节"的解释 | 本版本范围外（`second_model_and_training` 未运行）。 |
| **另一种学习器配置或更长训练预算** | 可能推翻事实 7 的"训练不足"部分，但**不会**推翻"本预算下规则更优"这一已测事实 | 必须在新的预注册下进行，不得改写已提交数字。 |
| **独立人审** | 唯一能解除科学门与接口门的途径 | 仍为 `not_arranged`。 |

## 7. 本文件不作的事

不选择 A 或 B；不宣称任何泛化性；不宣称 benchmark"不可绕过"；不把 H1–H3 当作结论；不把独立技术复审当作
人审；不因为结论不利而重新调参（ε、主 regime、arm 列表、指标与 regime 网格在 C_freeze 之后从未改动，
修正记录只追加）。
