# VeriCost 0.5.65-dev 预注册修正记录（仅追加）

本文件与 `faultda_bench/protocols/vericost_v1_amendments.json` 配对，二者只允许追加，不允许修改或删除
已有条目。追加条目必须同时写入两个文件，`seq` 从 1 开始连续递增。

允许的 `kind`（见预注册 `amendment_policy.allowed_kinds`）：`mde_regret_units`、`k_power_table`、
`gate0_number_change`、`certificate_scope`、`post_eval_erratum`。前四种只在第一个最终评估产物出现之前有效；
之后只允许 `post_eval_erratum`，它可以新增 `analysis_erratum<k>.json`，但永远不能替换任何确认性输入或输出。

禁止修改的键：假设、阈值、arm 列表、指标、regime 网格、主 regime、epsilon。

条目字段：`seq`、`utc`、`kind`、`after_commit`、`text`、`changes`。

## 条目

### seq 1 — `mde_regret_units`（utc 2026-10-21T04:20:00Z，after_commit `c8ab5c89018f72fb51927360cf1b50c74d4d3426`）

在任何最终评估产物出现之前，用开发集的离散度计算 O2 的最小可检测效应。四个开发 cluster 上的精确单侧
符号翻转检验需要 `d_z = (t_0.95,3 + t_0.80,3) / sqrt(4) = 1.66591787358`（`t` 分位数
2.3533634348 与 0.978472312363，自由度 3）。主 regime 上按 cluster 合计的 `SD(ΔU_c) = 0.595368090067`
（U 单位），因此 MDE 为 `0.991834342603` U 单位；以 `Σ E[U*] = 21.1377646118` 归一化后为
**0.0469223856362 归一化 regret 单位**。

本条目不修改任何假设、阈值、arm 列表、指标、regime 网格、主 regime 或 epsilon。

`changes`：`verdict_rules.power.dz_n4_alpha05`、`verdict_rules.power.t_quantiles_df3`、
`hypotheses_offline.O2.sd_delta_u_primary`、`hypotheses_offline.O2.mde_u_units`、
`hypotheses_offline.O2.mde_regret_units`（均由 `null` 新增）。

### seq 2 — `k_power_table`（utc 2026-10-21T04:20:00Z，after_commit `c8ab5c89018f72fb51927360cf1b50c74d4d3426`）

记录实际 cluster 数与可达的符号翻转下界。开发集共 4 个 cluster（`synthetic`、`uci_auto_mpg`、
`uci_glass`、`uci_occupancy`），精确单侧下界为 `2^-k`，即 k = 4 时 **0.0625 > alpha_O2 = 0.05**：
任何 p 都不可能达到显著，除被点估计或支配关系判为 FALSIFIED 之外，O 系列结论只能是
INCONCLUSIVE（under_powered）。该条目只确认预注册中的 under-power 声明，不修改任何阈值。

`changes`：`verdict_rules.power.k_table`（k = 1..4 → 0.5 / 0.25 / 0.125 / 0.0625）、
`verdict_rules.power.n_clusters_realized`、`verdict_rules.power.min_attainable_signflip_p_realized`。

### seq 3 — `post_eval_erratum`（utc 2026-10-21T05:40:00Z，after_commit `c8ab5c89018f72fb51927360cf1b50c74d4d3426`）

**预注册预期未达成；只修改"预期结果的记录"，不修改测量结果。** 预注册的断言是一个预测，不是规格说明；
当测量与预测不一致时，被改写的是预测结果的记录，而不是测量本身。

原预测（wf-0565 plan 第 12 项，逐字保留于 `changes`）：the q_only flag test - on a synthetic cc-flag
episode (G = 4, 20 000 reduced episodes, fixed seed) the greedy action at the post-flag state equals
the DP's (spot_flagged/spot(j))。

实测（`cert-g4-1`，主 regime，seed 565001，20 000 episodes）：DP 在 post-flag 状态选择 `spot:1`
（该状态价值 0.9391）；tabular Q 的 greedy 动作在 type-A 历史下是 `escalate`（唯一被探索到的动作
`spot_large` 仍为 -0.0717，低于价值为 0 的终止动作），在 type-B 与 type-C 历史下该状态从未被访问，
`q_only` 退化为 F_hist 成员。延长 reduced run 同样无法恢复：固定历史后 20 000 / 50 000 episodes 仍为
`escalate`，1 000 000 / 3 000 000 episodes 变为 `full`（Q = 0.700 = V − κ，确定性收益），而
`spot_flagged` 仅为 0.615 / 0.698，远低于真值 0.9391。

诊断：在预注册配置与 episode 预算下（Q0 = 0、γ = 1、ε 0.3 → 0.02、tie-break 顺序以 `escalate` 开头、
每步成本为负），信用传播过慢；20 000 个预注册 episode 的长度分布为
`{1: 13848, 2: 4525, 3: 1053, 4: 531, 5: 41, 6: 2}`，69% 的 episode 只有一个决策。

**这不是表示能力缺陷**：用 DP 自身的动作价值为同样的 9 个 gate 动作打分，greedy 结果就是
`spot_flagged`（capability 断言），且 coverage mapping 测试通过——因此"learned vs rule"的比较没有因为
缺少动作而被偏置（回溯验证了 review-2 增加 `spot_flagged` 的修正）。其他配置是否能恢复该动作**未经测试**，
本文件也不声称"没有学习器可以做到"。

本条目不修改任何假设、阈值、arm 列表、指标、regime 网格、主 regime 或 epsilon，不改变任何已提交的
Gate 0 数字，也不替换任何确认性输入或输出。`kind` 说明：预注册的 `allowed_kinds` 没有为"plan 层面的
预测未达成"准备的类别，因此使用 `post_eval_erratum` 作为"记录更正"类别；它在第一个最终评估产物出现之前
追加，且不新增任何 erratum 产物。

`changes`：`plan.item12.q_only_flag_test_prediction`（原预测 → 未达成，并记录实测结果）。

## 产物形式的修正条目（`analysis_erratum<k>.json`）

第一个最终评估产物出现之后（`first_output_commit` = `96d16c0`），预注册的
`amendment_policy.timing` 只允许 `post_eval_erratum`，并明确允许它**新增 `analysis_erratum<k>.json`**。
此后的修正条目因此以产物形式记录在该文件中，**不再追加到本文件与 `vericost_v1_amendments.json` 的
`amendments` 数组**：该数组文件的 sha256 被固定在一次写入的 `analysis.json` 的 `inputs.amendments` 内，
而 `audit --cross-version` 会重算 `analysis.json` 并与已提交副本逐字节比对，追加会破坏跨解释器字节一致证明，
且 `analysis.json` 作为预注册的一次写入输出无法吸收新哈希。两种形式都是只增不改。

### erratum 1 — `post_eval_erratum`（utc 2026-10-21T10:20:00Z，after_commit `fcb138a2838eec4c9aae19888fe09d70287cdbd7`）

**D1 的 `live_round_verdict: PASS` 是脆弱的、且依赖家族集的选择。** 该判定只由 DEV-SYN 的单个单元
`k1.00_L3` 决定，余量 **0.0022962496574**（0.0522962496574 对 ε = 0.05）；同一份已提交产物
`gate0_d1_dev.json` 在该单元上记录 `F_hist_plus = 0.0487633864427 ≤ ε`，纳入最小值后 8 个可采纳 regime
全部 ≤ ε，判定变为 `hard_stop: true`、`trigger: true`、`live_round_verdict: FAIL_NEGATIVE`。
预注册在任何数字出现之前即把 `min_fixed_r` 固定为 "min over F, F_size and F_hist" 并把 F_hist_plus 列为
informational，因此这是**有条件的结果而非协议违规**；**没有任何已提交的 Gate 0 数字被改变**。
rev-1 的头条结论不受影响（无论是否纳入 F_hist_plus 均为 `hard_stop: true`）。

产物：`faultda_bench/reports/vericost565/analysis_erratum1.json`
（sha256 `604db50ede5901700939db1c65f88e38281eacc0b4b2453f349aab1ac9dc2c70`）。
叙述见 `faultda_bench/reports/RELEASE_0565.md` §2.3.1 与
`faultda_bench/docs/CLAIM_DECISION_INPUT_0565.md` §2。
