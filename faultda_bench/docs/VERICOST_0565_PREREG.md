# 0.5.65-dev VeriCost：离线预注册

2026-10-20。科学 HOLD、新人审尚未安排、**本版本 API 调用 0 次、花费 ¥0**。本文件与
`faultda_bench/protocols/vericost_v1_prereg.json` 同为 C_freeze 内容；JSON 是机器可读的唯一阈值来源，
`witness.py` 与 `analysis.py` 只从 JSON 读取阈值，不从代码常量读取。修正只能通过只追加的
`VERICOST_0565_AMENDMENTS.md` + `vericost_v1_amendments.json` 进行。

## 1. 版本范围与决定记录

本版本不发送任何 `chat/completions`，不请求 `GET /user/balance`，不下载任何数据（包括 UCI），
`pip install` 亦不执行。这不是待定项：用户后续指令"先不考虑实跑吧，其他的可以继续迭代"晚于任务简报，
由工作流 `wf_aa54a053c8676e8c` 的父会话在通知 `notify-047ec505-506d-42b8-95f1-33358fd038f1` 中逐字转述，
因此简报的预算章节与 allocation 步骤 1–4 在本版本被取代。¥30 授权并未撤回，留待未来的实跑版本按此处
记录的协议原样使用。用户消息 7 在记录中已将密钥替换为 `[key redacted]`；写入前断言 provider 密钥模式
（字面量 `sk` 接连字符再接 20 位以上 `[A-Za-z0-9]`）在整份记录中无匹配。该模式本身在仓库中不以字面量出现，
以免仓库级密钥扫描把说明文字计为命中。

RESCOPE 删除的内容全部记录为"未运行"，不作为阴性结果，也不作为已完成工作：新数据源与一切网络获取、
dev/held-out/reserve 划分与独立测试集、pilot 与实跑区块 A/B/P1/P2、provider 请求路径
（`client.py`/`prompts.py`/`mock.py`）、Direction B 的 `terminal.py`、`hybrid` arm。
`q_only` 作为独立 arm 保留。

## 2. 实例集与标签

两套实例，均为 `split: development`、`seen_cluster: true`、`independent_test: false`、
`generalization_claim: none`，共 4 个 cluster（3 个已见来源 + 1 个合成族）：

- **DEV-SYN**：6 个合成 profile = {等份 [1/8]×8，偏斜 [35,20,12,10,8,6,5,4]} × N ∈ {500, 5 000, 50 000}；
- **DEV-SEEN**：`cross_source_v2.json` 中 24 个已见跨源任务（uci_auto_mpg / uci_glass / uci_occupancy，
  family 为 group 与 version），源 CSV 的 sha256 在建索引时重新校验，无网络访问。

`B_ref` 按实例集分别计算：合成集用设计公式 `5000 × median(bytes/N)`；已见集用
`median bytes(profile)`，因为每个已见切片恰好 8 行（文档化偏差 R8）。DEV-SEEN 只有一个规模桶
（`seen8`），因此该集上 F_size 等同于 F、F_hist 退化为 3 个 MAP-type 单元；此事实写入 regime map 的
`size_buckets_present`，不隐藏。

公开观测在任何 latent 下逐字节相同：已发布报告固定，latent 只决定仓库源在哪些 part 与报告不一致，
每个受影响 part 的差额恒为 `9·w_j = 0.9·v_j`，是 (profile, part) 的公开函数。

## 3. 效用、代价与 regime 网格

`U = V·[safe_complete] − L·[false_completion ∨ forbidden_effect] − Σcost(op)`，L 至多计一次。
`cost(op) = κ·billed_bytes(op)/B_ref`；`read_rows` 每次调用按整个 part 的字节计费，与返回行数无关；
`consistency_check` 计 `64·G`。κ ∈ {0.03, 0.10, 0.30, 1.00} × L ∈ {1, 3} 共 8 个 regime，
主 regime 固定为 `k0.30_L3`，永不重选。regime 可采纳当且仅当 `E[U*] ≥ 0.10`。
所有 argmax 使用 `canon.argmax_first`，在 `round(·,12)` 处相等时取最早列出者
（`tie_break: earliest_listed_wins_at_round12`）。

## 4. 离线假设（确认性，但本版本功效不足）

**功效声明（在产生任何数字之前写入）**：开发集只有 4 个 cluster，精确单侧 cluster 符号翻转检验的
最小可得 p 为 `2^-4 = 0.0625 > α = 0.05`，任何 p 都不可能达到显著。因此除被点估计或支配关系判为
FALSIFIED 之外，O 系列结论只能是 `INCONCLUSIVE (under_powered)`；`analysis.json` 会在每个结论旁打印
`min_attainable_signflip_p`。由于每个 arm 的取值都是精确期望（无抽样噪声），点估计与支配关系是精确可判定的。

- **O1 (descriptive).** The Gate 0 regime map reports, per regime and model, E[U*], `min_fixed_r`,
  the argmin family and member, F_hist⁺, `always_full_recompute` and the licensed scope. O1a is read
  on the development set; O1b (held-out replication) is **not run** in this version.
- **O2 (confirmatory arm `q_only`, one one-sided test at α = 0.05, no Holm).** A CPU-learned policy
  achieves higher expected utility than the development-selected best fixed rule at the primary
  regime, at no higher expected cost. SUPPORTED iff p < 0.05 **and** the point estimate T > 0 **and**
  `q_only` is not dominated by `bf` on (E[safe_complete], E[cost_units]). FALSIFIED iff T ≤ 0 or
  `q_only` is dominated. INCONCLUSIVE otherwise. `thompson` and `linucb` get the same statistics
  labelled exploratory, with no verdict.
- **O3 (descriptive).** Regret of each learned arm against the exact DP at the primary regime, the
  gap recovered (reported `undefined` if its denominator point estimate ≤ 0.01) and the cost/safety
  frontier for every program and learned arm × 8 regimes.

每个阴性或零结果都如实报告。"学得策略没有胜过 9 单元查表"本身就是一个结论。

## 5. 实跑假设（已预注册，`pending_live`，本版本不评估）

- **H1.** A raw LLM arm leaves measurable regret against the exact DP, and more than the
  development-selected best fixed rule. SUPPORTED iff `q_raw < 0.025` and Holm-adjusted
  `p_H1 < 0.05`; FALSIFIED iff `q_raw ≥ 0.025`, or the point estimate D ≤ 0, or
  `signflip_p([ε − regret_raw_c]) < 0.025`.
- **H2.** A Q-gated hybrid arm raises safe completion over the raw arm by at least 0.25 without
  losing utility and without being dominated by `always_full_recompute` or `bf`.
- **H3.** On `safe_stop` packets the raw arm escalates without public support at a pooled rate above
  0.30, with a significantly positive `shared_numeric` residual; because every residual is
  non-negative this condition is exactly **k ≥ 6** clusters with a positive residual
  (2⁻⁶ = 0.015625 < 0.025, while 2⁻⁵ = 0.03125 is not). This corrects review 4's "k ≥ 5".

Holm family {H1, H2, H3} at one-sided α = 0.05; O2 stays a separate single test. Partial-A rule:
fewer than `ceil((2/3)·planned_pairs)` usable pairs caps H1 and H2 at INCONCLUSIVE, labelled
under-powered. H1–H3 are never presented as findings in this version.

## 6. Gate 0 与范围判定

`min_fixed_r(regime)` 取 F ∪ F_size ∪ F_hist 的最小精确期望归一化 regret，并记录取到最小值的 family 与
成员。`hard_stop` ⇔ 每个可采纳 regime 都满足 `min_fixed_r ≤ ε = 0.05`；`primary_inadmissible` ⇔ 主 regime
`E[U*] < 0.10`；`trigger = hard_stop ∨ primary_inadmissible`；`scope = mechanism` 当且仅当
`¬primary_inadmissible ∧ min_fixed_r(primary) > ε`，否则为 `measurement`。D1 是唯一预注册的重设计
（全局故障只命中随机非空子集，q_g = 0.5），不允许任何其他重设计；`model_used = d1` 当且仅当
`trigger(rev1, development)`。本版本计划文件无论结论如何都是 `live_authorized: false`。
gate0 输出中不得出现任何学得策略的取值。

设计期框定：若廉价固定规则在主 regime 上落在 ε 之内，这就是头条结论，报告直接写明该 benchmark 在主
regime 上可被廉价固定规则绕过（给出 family、成员与 regret），不作任何"不可绕过"声明，也不为此重新调参。

## 7. 设计期探索与不可复现项

`faultda_bench/docs/vericost565_exploration/` 内 4 个 `gate0*.py` 是设计期脚本的逐字节副本，驱动器
`run_exploration.py` 以子进程重跑 E1–E9 并写出 `exploration_log.txt`（其 sha256 记入预注册
`design_exploration.log_sha256`）。E7 的 R1/R2 费率向量、E8 的 R2 费率向量未被设计期记录，驱动器
如实写出"not reproducible with unmodified script"并只重跑 R0 切片，不修改脚本。
被探索但未采纳：R2 费率、更短历史 H=5/H=3、L=5、把主 regime 移到 κ=1、q_g=0.3。

## 8. 一次写入、修正政策与提交顺序

每个产物只经 `canon.write_json_once` 写入一次（底层 `clarity.tasks.write_json` 以 `xb` 打开），
第二次写入抛 `FileExistsError` 而不覆盖证据。`write_once.frozen_at_gate0_plan` 与 `write_once.outputs`
在 JSON 中列明。修正条目字段为 `{seq, utc, kind, after_commit, text, changes}`；
`mde_regret_units`、`k_power_table`、`gate0_number_change`、`certificate_scope` 只在第一个最终评估产物
出现之前有效，之后只允许 `post_eval_erratum`。禁止修改：假设、阈值、arm、指标、regime 网格、
主 regime、ε。提交顺序：C_freeze ⊂ C_gate0a ⊂ C_gate0b ⊂ C_plan ⊂ C_eval ⊂ release。

## 9. DP 最优性证书（INV-DP）

证书分 C1–C5，`tol = 1e-9`，`mi_threshold_bits = 1e-12`，任何一项失败即抛
`RuntimeError('INV-DP violated: <part>/<case>')` 且不写出任何文件。C3 若在 8 worker 上超过 3 小时，
按预注册的缩减方式把 off-path 深度 2 检查限制到主 regime，置 `c3_scope: "primary_offpath"` 并追加
`certificate_scope` 修正；C1、C2、C4、C5 与 on-path C3 永不缩减。证书从不被削弱以换取通过。

## 10. 必须保留的限制

本版本没有真实模型结果、没有独立测试集、没有新来源、没有任何 provider 请求，因此不对任何模型能力、
泛化性或方法新颖性作出声明。全部数字都带 `split: development`、`seen_cluster: true`、
`independent_test: false`、`generalization_claim: none`。NO_GO 清单中"only the old dev cluster shows it"
在本版本未被解决，如实记录为未解决。
