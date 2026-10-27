# 近邻查新审计（2026-10-27）

范围：2026-06 至 2026-10-27 的 arXiv 公开成果，检索工具为 WebSearch（快照日期 2026-10-27）。目的不是文献综述，是**逐条判断本项目哪一条主张已经被抢先，哪一条还没有**。

结论写在最前面：本项目的三个主要假设——"判断与动作脱节"、"证据到动作的断链"、"RL 不胜等预算监督"——各自在 2026-06 至 2026-10-15 之间被至少一篇论文以 10 倍规模做过。**分支 1.0.x 开工日（2026-10-22）之前 17 天，它的核心论点已经发表。**

---

## 1. 逐条对照

| 编号 | 日期 | 标题 | 它做了什么 | 抢先了本项目哪一条 |
|---|---|---|---|---|
| 2606.26027 | 06-24 | Why Multi-Step Tool-Use Reinforcement Learning Collapses and How Supervisory Signals Fix It | 工具 RL 的灾难性崩溃归因到控制 token 的概率尖峰；系统比较各类监督信号；SFT 与 RL 交错训练提升稳定性 | V5.0.15 的 0/240 不再算"发现"；机理与修法都已有 |
| 2608.26218 | 08-28 | 旧工具结果截断（169 题 SWE-bench Verified） | 同权重、同任务，只改 harness 的上下文截断策略，fail-to-pass 28% → 49% | "harness 比模型重要"这条已被拿走 |
| 2609.17848 | 09-15 | SFT or RL for Tool-Calling Agents? A Controlled Study Across Data, Method, and Scale（EMNLP 2026 REALM） | 6 个 Qwen3（0.6B–32B）× 三种训练策略；LoRA SFT 在 15/18 设置最强，GRPO 只赢 2；跨数据集 GRPO 赢 29/54，平均差 < 1 分 | **V5.0.05 的"等预算监督胜过 RL"** |
| 2610.06191 | 10-05 | Judged Useless, Queried Anyway | 7 个 agent；97–100% 把工具结果判为"无用"后仍继续查询；提示干预只改变何时停、不改变为何停；预算让 7–8B 模型刷满上限；harness 强制 5-strike 规则有效；300 题预注册复现 | **1.0.35 的"43 终态正确 / 21 判完成"、"判断-动作脱节"** |
| 2610.07753 | 10-06 | From Evidence to Action: How Tool-Using Agents Fail（SafeActBench） | 656 案例、6 个运营领域、5 种协议、10 个 model-harness 组合；来源绑定的 Evidence Ledger + 确定性轨迹评分；"调查到一半就停"与"证据未到位就动手"两侧都存在 | **1.0.60 的"证据到动作的断链"框架** |
| 2610.21098 | 10-15 | ToolBottleneckBench | 固定合成企业任务，单变量扰动：工具目录规模、可见菜单、认证链复杂度、**返回记录编码方式**；菜单 8→128 掉 17.5 分；**编码方式效应小且校正后不显著** | V3.5"日志保真度是瓶颈"的迁移版；且结果与之相反 |
| 2610.32285 | 10月 | TraceTrial-Bench | 把 harness 拆成七部分；4 个 harness × 9 个模型 × 95 任务 × 3,420 runs；31.1% 的成功 run 至少违反一条 harness 准则 | "评分口径不等于能力" |
| 2610.32483 | 10月 | When Agents Fail: Model or Harness, Who's to Blame? | 111 个设置、52,168 条轨迹；harness 排名随模型与基准变化；没有单一最优 harness | harness 归因的规模版 |
| 2610.32555 | 10月 | MCP-Injector（NeurIPS 2026 poster） | 从 1,774 个开源 MCP 仓库的 57,240 条 issue/PR 挖真实工具故障；gpt-oss 分数 8.08 → 3.23；"框架级错误处理比模型规模更重要" | **"故障注入 benchmark"这个形式本身** |

---

## 2. 三条必须承认的判断

**一、V5.0.15 的 0/240 不能写成"RL 失败"。** 报告自己第 1 条已经写了：初始适配器并非已掌握 A/B/C/D 四分类的模型，起点 0/240 不代表历史能力；branch 臂只训首动作、后缀仍由当时策略采样，与 SFT/GRPO 的更新目标不同源。2606.26027 给出的是控制 token 概率尖峰这类可实现机理解释。当前证据更支持"这个适配器没学会恢复接口"，而不是"RL 不行"。

**二、V5.0.05 的匹配监督对照是正确设计，但结论已被更早、更大规模地发表。** 2609.17848 覆盖 6 个模型规模，SFT 在 15/18 设置最强。本项目的三种子、144 题对照只能作为独立复现，不能作为主张。

**三、V3.5 的"日志保真度是瓶颈"与 2610.21098 冲突。** 本项目的观测是 480 条恢复案例中 5 个错误全部落在截短日志（85/90，截短 17/22 vs 其他 68/68）；2610.21098 在固定任务上扰动返回记录编码，效应小且校正后不显著。两者不一定矛盾（操纵的变量不同：一个是日志截短，一个是记录编码），但在写成主张之前必须做一次同构对照，否则审稿人会直接引 2610.21098 否掉。

---

## 3. 仍然空着的格子

九篇论文共有同一个假设：**检查的成本是约束（budget、max turns、timeout），不是价格。**

- 2610.06191 自己写了：预算是"外部刹车，与证据无关"。
- SafeActBench 用布尔前置条件：证据到位没有，不问值不值。
- ToolBottleneckBench 只扰动接口，不给观测定价。
- MCP-Injector 注入故障，不计成本。

成本当约束时，能测的只有"在哪一步被截断"；成本当价格时，能测的是决策。这个区别带来三件近邻做不到的事：

1. **每个实例的最优策略已知，不是估的。** 近邻判"过度检查"只能相对模型自评或人工前置条件；本项目有 C1–C5 数值证书，可以给出"在该 (κ, L) 下检查的边际价值精确等于多少"。
2. **偏差可带符号分解。** 查少了要加证据，查多了要加停止判据，修复方向相反。混在一个 regret 里只能得到"agent 不够好"。
3. **价格弹性可测。** κ 扫描下检查率是否跟随最优。若不跟随，结论是"检查行为不是成本决策"，这把 2610.06191 的定性观察升级成可量化的定律。

---

## 4. 引用与复核

所有编号均可在 arxiv.org/abs/ 后接编号直接访问。日期取首次提交日。

本审计是 2026-10-27 的快照。该方向当前约两周一代，**任何投稿前两周必须重做一次**，检索词：

```
cost-aware agent evaluation price elasticity evidence acquisition
certified optimal policy regret decomposition tool-use agent
policy headroom benchmark discriminability adaptive versus fixed policy
value of information agent stopping certificate
harness attribution agent benchmark variance decomposition
```
