# τ²-bench Airline task 2：单轨迹评分依据复核

日期：2026-11-06  
状态：**运行时政策与评分元数据已复核；政策标签未独立裁定；与既有审计重叠，不构成新发现。**

## 问题

公开的 `llmcontract-tau2` 规则把第一次匹配到的肯定词作为永久授权。该状态机确有作用域限制，但本次案例还允许直接核对轨迹所带的运行时政策和 reward 元数据，因此重点改为检查可能遗漏于 reward basis 的政策义务。

## 观察到的轨迹

- **[事实]** 输入来自 τ²-bench 固定快照 `033bf082f48e4a3c6a1256208e93cf2ce9c3bb6f` 的公开归档，模型结果组 Claude 3.7 Sonnet、airline、task 2、trial 0；轨迹原生 `reward=1.0`，`reward_basis` 只有 `DB` 与 `COMMUNICATE`。
- **[事实]** 此轨迹的 `environment_info.policy` 保存了当次运行时政策文本。该文本要求不得在用户明确要求前主动提供补偿；延误航班补偿只列于用户希望改签或取消且完成相应操作的条件下。轨迹中 Agent 先主动提出补偿选项，用户表示只想获得补偿，之后 Agent 发放 `$50` 凭证；用户没有要求改签或取消。
- **[事实]** 同一 `reward_info` 保存了两条未满足的自然语言断言，其中一条是“不得在用户要求前主动提出补偿”；这些断言没有进入该轨迹的 `reward_basis`。原生总分仍为 1.0。
- **[事实]** 在零起算消息索引 3，用户回答 `Sure, my user ID is ...`，是在助手索取用户 ID 后提供账户信息。该肯定被配套监控器永久保留；其协议将 `send_certificate` 列为写操作。
- **[事实]** Agent 在消息索引 24 主动提出补偿选项；用户在索引 25 表示只想获得补偿；Agent 在索引 26 说明 `$50` 金额并在同一条消息调用 `send_certificate(amount=50)`。因此“早先身份答复被沿用为凭证授权”不是唯一或最强解释：用户后续明确表达了获得补偿的意愿，但金额告知后没有额外的确认轮次。

## 解释边界

- **[推断]** 轨迹嵌入的政策文本与未满足断言支持“该运行违反至少一项任务政策”的解释；但断言本身是自动生成的标签，不是独立人工裁决。是否应以这些条件判该轨迹失败，仍需按任务契约作独立复核。
- **[事实]** 对应历史运行提交 `c30d59aaa71c65f9b9eb6a8f8636b48945028fcf` 与 GPT‑4.1 mini 记录的 `ade39493be54aad326a4c65295f77fe09780329b` 均未出现在 τ²-bench 完整公开历史中；按 SHA 从当前仓库及前身 `tau-bench` 仓库直接 fetch 均返回 `not our ref`。前身仓库完整克隆尝试因 GitHub 连接失败未完成，因此不能声称已排除其完整历史中仍有对象。公开结果内嵌的政策文本和评分元数据可读，但完整历史执行源码仍未恢复。
- **[事实] 版本边界：**嵌入的航空政策文本与 τ²-bench `v0.1.0` 至 `v1.0.1` 的 `airline/policy.md` 字节规范化后内容一致；但 task 2 本身发生了变化。[`v0.1.0` 的 airline task 2](https://github.com/sierra-research/tau2-bench/blob/v0.1.0/data/tau2/domains/airline/tasks.json) 目的写着客户应获得 `$50`，用户模拟指令会先抱怨并尝试让 Agent 主动提出补偿；[`v1.0.1` 的 airline task 2](https://github.com/sierra-research/tau2-bench/blob/v1.0.1/data/tau2/domains/airline/tasks.json) 则改为“客户不应获得补偿”，并要求用户永不改签或取消。归档轨迹时间为 2025-06-05，早于 `v0.1.0` 标签日期 2025-06-10，且历史源码提交无法取回，因此 `v0.1.0` 只能作为近邻版本参照，不能冒充精确运行版本。
- **[事实]** τ²-bench Issue #384 将后续版本的 airline T2 列入 reward-basis 遗漏的 no-write/refusal 任务，同时提出 populated criteria 未纳入 reward basis 的通用校验。该 issue 并未以本报告中的 2025 轨迹作为具体例子；它覆盖的是后续任务定义及同类评分依据问题。Issue #298 则已报告同一归档语料中结果分数与程序合规的差异。因此，本例不是被两个 issue 逐字逐样例复述，但其任务评分机制和主张类别已有直接近邻，不足以单例构成新贡献。[Issue #384](https://github.com/sierra-research/tau2-bench/issues/384) · [Issue #298](https://github.com/sierra-research/tau2-bench/issues/298)
- **[推断]** 这次复核没有估计此类任务的总体频率，不能把一个轨迹推广成基准级误判率。

## 研究门判断

| 门槛 | 判断 |
| --- | --- |
| 原始契约 | 运行时政策文本已嵌入轨迹，且与正式标签版本一致；历史执行源码和精确任务定义仍未恢复 |
| 源码与事件证据 | reward、reward basis、NL assertion 和 `send_certificate` 调用都在原始轨迹中 |
| 完整评分漏检预测 | 原生 reward=1，而两条 NL assertion 未通过且未纳入 reward basis；政策违例解释有直接支持，但标签不是独立审定 |
| 强对照与近邻 | τ²-bench Issue #384 后续审计列出 airline T2 及相同 reward-basis 缺口；Issue #298 直接覆盖 outcome 与程序合规差异 |
| 否证条件 | 独立复核若认为该补偿符合任务契约，或历史评分对未通过 assertion 另有处理，则关闭此例 |
| 最低成本 | 离线单例复核已完成；若要登记最终标签，需独立审阅者裁定这段已嵌入的政策/评分证据；无需模型 API |

**决定：NO-GO，作为独立论文主张停止；HOLD 维持。** 这例可供盲审者核对既有 τ²-bench 发现中的评分依据遗漏，但即使确认也只会补强已公开的 Issue #384/#298，不自动触发扩源、模型运行或新贡献主张。

## 有界后续研究门：任务版本契约差异

**候选假设：**同一 benchmark task ID 在版本升级时可能改变规范目标或评分条件；若历史运行没有精确绑定任务版本，将其与新版本结果直接对比会混淆“Agent 行为变化”和“任务定义变化”。当前直接证据只有 airline task 2，不能支撑普遍性主张。

- **来源与已有合法证据：**公开 τ²-bench `v0.1.0` 与 `v1.0.1` 的任务数据中，同一 ID 的目标文字已不同；历史发布轨迹也保留 task ID 和运行元数据，但对应源提交无法取回。
- **预测与否证：**若对齐两个版本后，只有 task 2 改变，或历史轨迹都能精确绑定旧版且新版结果不与旧版直接比较，则跨任务版本漂移假设不成立；若多个独立 task ID 的目标/评估条件发生改变，且历史运行缺少精确版本绑定，才有理由继续评估其测量影响。该预测不是已观察结果。
- **基线与指标：**以逐版本锁定的原生任务与评分配置为基线；静态比较 task ID、目的、用户指令、初态、gold actions、reward basis、NL assertions、communication criteria。只报告变更数与变更类别，不把字段差异等同于语义错误或分数变化。
- **最小成本：**离线比较 τ²-bench `v0.1.0` 和 `v1.0.1` 的 airline/retail 任务 JSON；不运行 Agent、环境或 API。保留未变任务作为负对照。
- **近邻与决策：**τ²-bench Issue #384 已审计 task data 中缺失/未接入的评分条件，并明确指出修复会影响 leaderboard 可比性；[Liu (2026)](https://arxiv.org/abs/2611.04399) 已用公开轨迹重放展示 evaluator 版本变化可改变 leaderboard 结论，并建议固定 evaluator 版本、发布重评分差异。后者集中于 evaluator/记录代码，任务数据重评分不是其摘要中的实验对象；但与本候选的“版本化评测变迁”主张高度相邻。故**不批准新的论文机制主张**；仅 GO 进行一次只读的版本差异盘点。若结果只证实已有任务修订且没有旧轨迹版本精确配对，就停止此路线。

### 执行记录与门槛裁决

**[事实]** 对 τ²-bench `v0.1.0`（2025-06-10）与 `v1.0.1`（2026-07-16）的 `airline/tasks.json`、`retail/tasks.json` 作只读字段比较。两域 task ID 均完整对应，没有增删任务。比较前按两版 schema 将缺省 `reward_basis` 规范化；`v0.1.0` 的缺省值为 `[DB, COMMUNICATE]`，不能把“未显式写出”误记成语义改动。

| 域 | 任务数 | 改动的任务数 | 观察到的变化 |
| --- | ---: | ---: | --- |
| Airline | 50 | 29 | purpose 10；用户任务指令 17；gold actions 12；NL assertions 12；reason_for_call 7；communication_info 1；unknown_info 1。各类别可重叠；有效 reward basis 未变。 |
| Retail | 114 | 114 | 有效 reward basis 全部改变：从 `[DB, COMMUNICATE]` 变为 112 个 `[DB, NL_ASSERTION]`、2 个 `[DB]`；另有 reason_for_call 21、NL assertions 35、gold actions 10、communication_info 2 项有字段变化。 |

**[推断]** 任务版本漂移不是 task 2 的孤例：两个公开版本间多项用户目标和评分条件有变；但静态字段变化本身不等于错误，也不说明任何模型分数或排序实际改变。Retail basis 变化与 τ²-bench Issue #384 报告的后续任务配置直接一致，因而支持的是版本绑定与数据校验需求，而非新的科学机制。

**裁决：**只读版本盘点 **GO 且已完成**；跨版本重评分 **NO-GO**。旧运行提交不可得，且任务契约已广泛变化；把旧轨迹套到新版本无法给出可信的历史评分因果量。未执行 Agent、模型、环境或 scorer；不估计排名影响。独立论文状态仍为 **HOLD**。

**[推断] 研究贡献裁决：**静态版本漂移是工程上重要的复现条件，但目前没有证据证明它改变了模型分数、排序或科学结论。Issue #384 已直接讨论 τ²-bench 的 task-data 与评分配置修订；近期 leaderboard 审计则覆盖 evaluator 版本迁移。跨版本轨迹影响可能是两者之间的窄区别，但只有在同一任务可精确绑定旧/新契约与完整评分版本，并观察到可复核的结论变化时，才值得重新开启；本仓库当前材料不满足该条件。

## 版本研究线的关闭条件复核

**[事实]** Inspect Evals 的公开维护规范要求：会影响评测结果可比性的 task 变化应增加可比性版本号，并为每个 task 指定版本。[Task versioning guidance](https://github.com/UKGovernmentBEIS/inspect_evals/blob/main/TASK_VERSIONING.md)

**[推断]** 这进一步说明“需要版本化并提示不可比”本身属于已形成的工程规范，不能作为本文创新。学术上仍可能存在的增量只能是实证量化：在有精确旧/新任务契约与完整归档轨迹的数据中，分离 task-data 变化与 evaluator-code 变化，并测出其对可靠性判断或系统排序的独立影响。现有 τ²-bench 轨迹缺少精确 source commit，Issue #384 已覆盖该 benchmark 的评分配置修订，项目 AppWorld 档案又只有单一 agent lineage，因此当前不满足这个设计的识别条件。

**最终决定：**关闭“版本漂移”作为本项目当前论文主张；将版本绑定列为后续工程报告要求。除非出现可精确配对的历史归档数据，且初步审计预测会改变一项实际评测结论，否则不继续在这条线上扩任务或重评分。

## 可复现定位

原始归档未复制进项目仓库。案例定位：`data/tau2/results/final/claude-3-7-sonnet-20250219_airline_default_gpt-4.1-2025-04-14_4trials.json`，`task_id=2`、`trial=0`。公开归档中的完整对话含模拟身份数据，故本记录只保留核查所需的去标识摘要。
