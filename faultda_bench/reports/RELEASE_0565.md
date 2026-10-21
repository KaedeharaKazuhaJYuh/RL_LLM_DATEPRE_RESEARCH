# FaultDA-Bench 0.5.65-dev｜离线验证代价诊断（VeriCost）

2026-10-21。**本版本 API 调用 0 次、花费 ¥0、下载 0 次**；无新来源、无独立测试集、无任何 provider 请求，
科学门仍为 HOLD，新独立人审尚未安排。全部结果带 `split: development`、`seen_cluster: true`、
`independent_test: false`、`generalization_claim: none`，**不作任何泛化声明**。

本版本的头条结论是一个阴性结论：**在预注册的主 regime 上，一条廉价固定规则落在 ε 之内**，即该 benchmark
的主 regime 可被廉价固定规则绕过。它被原样报告、给出 family、成员与精确 regret，**不作任何“不可绕过”声明**，
也没有为此重新调参（ε、主 regime、arm 列表、指标与 regime 网格在 C_freeze 之后从未改动）。

## 1. 为什么重设范围（RESCOPE）

所有者的下一阶段优先级第 3 项要求**先选定唯一研究主张**，再决定是否建立未见任务。独立测试集是**一次性**的：
在主张未定之前消耗它，是不可逆的浪费。因此本版本把设计文档中的数据获取、留出划分、pilot 与实跑区块全部
记为"未运行"，只建设**离线分析核心**：精确代价/效用模型、精确 DP 上界与其最优性证书、Gate 0 可绕过性地图、
13 个 arm 的离线对照，以及把每个阴性结果保留下来的证据链。本版本因此**不产生任何模型能力证据**，
也不解除任何门。决定本身不在本文件内作出，证据集中在
[`faultda_bench/docs/CLAIM_DECISION_INPUT_0565.md`](../docs/CLAIM_DECISION_INPUT_0565.md)。

### 范围决定记录（0 API 调用、¥0）

任务简报原本包含预算与实跑章节。用户随后的指令"先不考虑实跑吧，其他的可以继续迭代"晚于简报，
因此简报的预算章节在本版本被取代：不发送任何 `chat/completions`、不请求 `GET /user/balance`、
不下载任何数据（包括 UCI）、不执行 `pip install`。**¥30 授权没有被撤回，也没有被使用**，原样结转给未来的
实跑版本，协议记录在 [`VERICOST_0565_LIVE_PROTOCOL.md`](../docs/VERICOST_0565_LIVE_PROTOCOL.md)。
被取代的简报文本在记录中保留，**密钥一律以 `[key redacted]` 替换**；写入前断言 provider 密钥模式在整份
记录中无匹配，提交历史的同一检查计数为 0。

**密钥轮换建议**：密钥曾在对话中以明文粘贴，因此建议在任何实跑之前轮换密钥。本版本只有
`vericost565/audit.py --secret-scan` 读取 `.env.local`，它在内存中比较值与 sha256，**只打印计数**
（本轮 `key_matches 0, sha256_matches 0, pattern_matches 0, files_scanned 2040, blobs_scanned 2229, clean true`），
该文件从未被打开、打印、记录或提交。

## 2. GATE 0 REGIME MAP（本版本的主要实证结果）

ε = 0.05。`min_fixed_r` 是 F ∪ F_size ∪ F_hist 三族中最小的精确期望归一化 regret，并记录取到最小值的
family 与成员；`E[U*]` 来自精确 DP。预注册的主实例集为 **DEV-SYN**（6 个合成 profile），主 regime 为
`k0.30_L3`，永不重选。

### 2.1 rev-1 latent 模型，DEV-SYN（预注册决定集）

| regime | E[U*] | min_fixed_r | ≤ ε | 取到最小值的 family/成员 |
| --- | --- | --- | --- | --- |
| k0.03_L1 | 0.921397038539 | 0.00868277714933 | 是 | F_hist（9 单元 MAP-type × 规模查表） |
| k0.03_L3 | 0.907156327693 | 0.0100105068447 | 是 | F_hist（9 单元） |
| k0.10_L1 | 0.81248032124 | 0.00482207434742 | 是 | F_hist（9 单元） |
| k0.10_L3 | 0.770814764155 | 0.0319121154715 | 是 | F_hist（9 单元） |
| k0.30_L1 | 0.737959711946 | 0.0103696861875 | 是 | F_hist（9 单元） |
| **k0.30_L3（主）** | **0.682267789726** | **0.0315391087846** | **是** | **F_hist（9 单元）** |
| k1.00_L1 | 0.590706640934 | 0.00655102071841 | 是 | F_hist（9 单元） |
| k1.00_L3 | 0.512775746047 | 0.039351727369 | 是 | F_hist（9 单元） |

8 个 regime 全部可采纳且全部 ≤ ε，因此 `hard_stop: true`、`primary_inadmissible: false`、`trigger: true`、
`scope: "measurement"`。**这就是头条结论**：在主 regime 上，一个 9 单元查表以
`min_fixed_r = 0.0315391087846` 的归一化 regret 贴住精确 DP。
设计期探索的 E9 预测为 F_hist 在主 regime 上 0.029（偏斜）/ 0.036（等份）；DEV-SYN 合并两种形状，0.0315 与之一致。

### 2.2 同一地图在另两个实例集上并不相同（必须同时陈述）

| 集 | profile | cluster | k1.00_L1 | k1.00_L3 | 主 regime | hard_stop / trigger |
| --- | --- | --- | --- | --- | --- | --- |
| DEV-SYN | 6 | synthetic | 0.00655102071841 | 0.039351727369 | 0.0315391087846 | true / true |
| DEV-SEEN | 24 | 3 个已见来源 | 0.0999024644006 | 0.180085602665 | 0.0100224687785 | false / false |
| ALL | 30 | 4 个 | 0.0744909677605 | 0.135920618803 | 0.014189449731 | false / false |

在真实已见切片上，κ = 1 的两个 regime 超出 ε，**因此"ε 内可绕过"是合成形状 profile 的性质，不是真实已见
切片在 κ = 1 上的性质**。三个集各自携带完整 `decision` 块，没有任何一个被隐藏；顶层 `decision` 按预注册取
DEV-SYN（`decision_set: dev_syn`）。DEV-SEEN 只有一个规模桶 `seen8`，该集上 F_size 等同于 F、F_hist 退化为
3 个 MAP-type 单元，`size_buckets_present` 如实记录；在该集的多个 regime 上取到最小值的成员是
F 族的 `always_full_recompute`。

### 2.3 D1 latent 模型（预注册的唯一重设计）

`trigger(rev1, development)` 为真，因此按预注册启用 D1（全局故障只命中随机非空子集，q_g = 0.5）。
D1 下 DEV-SYN 的 `min_fixed_r` 为
`[0.0103027082467, 0.0112264441331, 0.0052320249624, 0.037255631514, 0.019539807224,
0.0352313961227, 0.00798047385115, 0.0522962496574]`：`k1.00_L3` 的 0.0522962496574 > ε，
因此 `hard_stop: false`、`trigger: false`、`live_round_verdict: PASS`、`model_used: d1`、`scope: measurement`，
主 regime `min_fixed_r = 0.0352313961227`。**两件事必须分开**：rev-1 在每个可采纳 regime 上都可被 ε 内的
廉价固定规则绕过（头条结论）；D1 为未来实跑提供了一个不被覆盖的配置（仅此而已，本版本没有模型结果）。

### 2.4 没有单条规则能一招通吃

每个集、每个模型的 `single_rule_literal.within_epsilon_all_admissible` 均为 `false`：不存在单个 f ∈ F 在所有
可采纳 regime 上同时落在 ε 内；绕过依赖逐单元查表。这是对"固定规则很强"这一结论的限定，而不是削弱。

## 3. INV-DP 最优性证书（C1–C5）

`dp_certificate_dev.json`（sha256 `668c4f32fedd5c1bb78b72d22d22f07275622dc84a85b5f5e6eac4c52e08b8a7`）
`status: pass`，`tol = 1e-9`，`mi_threshold_bits = 1e-12`，`c2_scope: full`、`c3_scope: full`（**未缩减**，
预注册的缩减触发条件是 dev C3 在 8 worker 上超过 3 小时；实测 C3 为 4786.6 s CPU，约 10 分钟）。
最大违反量：C1 1.11022302463e-16、C2 1.11022302463e-16、C3 3.33066907388e-16、C4 3.33066907388e-16、C5 0.0。
一次 `certificate --split development --workers 8` 的墙钟为 869.6 s（103 min CPU）。
证书失败即不写文件；五个变异（类相关幅值、跨 part 的读取、按返回行计费、latent 相关的报告合计、
粗化的 compact 状态）与 C4 的手工超优 arm 都被演示为**真实抛错**，记录在
`.agents/tasks/vericost565/wf-0565/guard-demonstrations.md`。C4 的最大违反量 3.33066907388e-16 意味着在某些
(profile, history, regime, model) 单元上，一个被计价的程序 arm**恰好等于** DP 最优值——这是真实结果，不是缺陷。

## 4. 离线策略对照（13 个 arm）

主 regime `k0.30_L3` 的归一化期望 regret（全部 30 个开发 profile）：

| arm | regret | 说明 |
| --- | --- | --- |
| F_hist_plus | 0.0138051012414 | 66 单元查表，仅供参考（不在预注册的 bf 候选集内） |
| **bf = F_hist** | **0.014189449731** | 预注册 bf = argmin{F, F_size, F_hist} |
| thompson | 0.0241588323286 | 最好的学得 arm，仍不及 bf |
| F_size | 0.0309986668882 | |
| linucb | 0.155694955762 | |
| F = always_full_recompute = static_semantic | 0.252907632527 | 同值 |
| q_only | 0.307923762624 | 确认性假设 O2 的 arm |
| guarded_read | 0.319163752445 | |
| escalate_all | 1.0 | 退化对照 |
| never_verify | 1.85155645976 | 退化对照 |

**结论（阴性，保留）：没有任何 CPU 学得策略在同等代价下胜过最佳固定规则。**
确认性假设 O2（`q_only` 的期望效用高于 bf 且代价不更高）判定 **FALSIFIED**，**由点估计否证，与功效不足无关**：
四个 cluster 的 ΔU 全为负（synthetic −2.44327118094、uci_auto_mpg −1.3029029437、uci_glass −1.20536320603、
uci_occupancy −1.25734943368），均值 **-1.55222169109**，精确单侧 cluster 符号翻转 **p = 1.0**，
`dominated: false`（`q_only` 便宜 0.0576311217151 个代价单位，但安全性低 0.257396515255，故不被 Pareto 支配，
**仅在效用上被否证**）。探索性：`thompson` ΔU −0.0526826156682（被 bf 在 (safe, cost) 上支配，两重否证）、
`linucb` ΔU −0.747777519439；三者 Holm 校正后 p 均为 1.0（标注为探索性）。
`gap_recovered` 全为负（q_only −20.7008952751、thompson −0.7025912059、linucb −9.97258587986，
分母 0.299933248386 > gap_floor 0.01，故有定义）：没有任何学得 arm 回收 bf 到 DP 之间的任何一部分差距。

**cluster bootstrap 区间（仅描述性，B = 10000，seed 5652026，stdlib `random.Random`）**：
ratio-of-sums 点估计 −0.293734312893，区间 [−0.476548585633, −0.216085122564]；
macro 点估计 −0.314931120737，区间 [−0.503467682211, −0.216149562513]。
判定与区间相互独立：把全部 bootstrap 边界替换为任意值后，`analysis.json` 除 bootstrap 键之外逐字节不变（有测试）。

**功效不足声明（在产生任何数字之前写入）**：开发集只有 **4 个 cluster**，精确单侧 cluster 符号翻转检验的
**最小可得 p 为 2^-4 = 0.0625 > α = 0.05**，任何 p 都不可能达到显著。因此除被点估计或支配关系判为 FALSIFIED
之外，O 系列结论只能是 `INCONCLUSIVE (under_powered)`。O2 的 MDE 为 **0.991834342603** U 单位
（= 0.0469223856362 归一化 regret 单位，`d_z = 1.66591787358`，`t_{0.95,3} = 2.3533634348`、
`t_{0.80,3} = 0.978472312363`、`SD = 0.595368090067`）；观测效应 −0.0734335782233 regret 单位，
量级大于 MDE 但方向相反。

**实跑 episode（描述性，每 profile 3 个冻结单元，共 90 对）**：主 regime 上 bf 安全完成 88/90 = 0.977777777778
（Wilson95 [0.922554733114, 0.993884558014]），q_only 64/90 = 0.711111111111 [0.61035956402, 0.794578727408]；
精确双侧 McNemar（q_only vs bf）为 0 胜 24 负，p = 1.19209289551e-07。
720 个 episode 的分项计数：`never_verify` 312 次假完成、`guarded_read` 312 次被支配读取、
`always_full_recompute`/`escalate_all`/`static_semantic` 全 0、bf 18 次假完成与 1 次错误发布、
q_only 20 次假完成、linucb 25 次、thompson 18 次；`unsupported_escalation` 全 arm 为 0。
**`duplicate_effects` 全为 0 是结构性的，不是"测到了 0"**：抽象转移没有 request_id 重试路径，
环境层的幂等守卫由 C2 证书覆盖；该说明逐字记录在 `offline_eval.header.duplicate_events`。

**学习器的训练不足诊断（阴性结果，保留，且边界不得越过）**：预注册的 q_only 旗标预测**未达成**
（修正条目 seq 3 `post_eval_erratum`）。原则：预注册的断言是一个**预测**，不是规格说明；当测量与预测不一致时，
被改写的是"预测结果的记录"，而不是测量。实测在 `cert-g4-1` 主 regime、seed 565001：DP 在 post-flag 状态选
`spot:1`（状态价值 0.9391），tabular Q 的 greedy 动作在 type-A 历史下是 `escalate`，type-B/C 下该状态从未被访问；
20 000 / 50 000 episode 仍为 `escalate`，1 000 000 / 3 000 000 episode 变为 `full`（Q = 0.700 = V − κ），
`spot_flagged` 仅 0.615 / 0.698。20 000 个预注册 episode 的长度分布为
`{1: 13848, 2: 4525, 3: 1053, 4: 531, 5: 41, 6: 2}`，69% 只有一个决策。
三条区分：**不是表示能力缺陷**（用 DP 自身的动作价值给同样 9 个 gate 动作打分，greedy 结果就是 `spot_flagged`，
coverage mapping 测试通过）；**是预注册预算下的训练不足**；**其他配置是否能恢复该动作未经测试**，
本文件不声称"没有学习器可以做到"。Q0、ε 衰减、奖励与 episode 数全部如预注册，未作任何调参。

## 5. 实跑假设 H1–H3：`pending_live`，本版本不评估

H1–H3 连同其阈值、Holm 家族与 review-5 NIT 7 的修正（partial-A 门限
`< ceil((2/3) · planned_pairs)`；H1 FALSIFIED 当且仅当点估计 `D ≤ 0` 或
`signflip_p([ε − regret_raw_c]) < 0.025`）全部**保持为预注册的 `pending_live`**，
**从不作为本版本的结论呈现**。完整协议见 [`VERICOST_0565_LIVE_PROTOCOL.md`](../docs/VERICOST_0565_LIVE_PROTOCOL.md)，
其中记录了修正后的价格（CNY/1M tokens 峰时 flash 0.04/2/8、v4-pro 0.30/9/27，非峰时半价）与北京时间峰时时段
（周一至周五 09:00–12:00、14:00–18:00，排除中国法定节假日，`tz: Asia/Shanghai`），来源
`https://api-docs.deepseek.com/zh-cn/quick_start/pricing`、访问日期 2026-10-20，由设计复审第 5 轮记录，
**实现期未重新获取**（本版本不发起网络请求），唯一键名 `re_verify_before_live: true`。

## 6. 未运行清单（RESCOPE 删除的内容，记为未运行而非阴性结果）

逐项同时记录在 `analysis.json` 的 `not_run` 块中：

| 键 | 内容 | 原因 |
| --- | --- | --- |
| `new_sources` | ≥ 21 个 UCI 候选来源、页面/许可/DOI 筛查、下载与 sha 固定、`sources.py` | `rescope_no_downloads` |
| `heldout_split` | dev/held-out/reserve 划分、全部留出任务、`gate0_*_heldout.json`、`dp_certificate_heldout.json`、`heldout_offline.json`、留出冻结清单 | `rescope_heldout_deferred_until_claim_decided`（独立测试集一次性） |
| `pilot` | pilot 单元、packet、measures、`pilot.json`、投影修正 | `owner_scope_no_live_runs` |
| `a` / `b` / `p1` / `p2` | 实跑区块 A、B（Direction B packet）、探针 P1、P2 | `owner_scope_no_live_runs` |
| `provider_requests` | 全部 DeepSeek 请求：`chat/completions`、`GET /user/balance` | **0 次请求、¥0** |
| `provider_path` | `client.py`（预留/headroom/账本/余额下限/thinking 泄漏中止）、`prompts.py`、`mock.py` | `rescope_no_provider_path`；其缺失正是 `audit --no-network` 所断言的 |
| `direction_b` | `terminal.py` 的三种 packet 状态、未决目标符号规则、`SYSTEM_B`、`grade()`、两个 packet 产物 | 未实现 |
| `hybrid_arm` | flash + Q 门控的 hybrid arm、accept/override、τ = 0.05、`gate_override` 字段 | 未实现（`q_only` 作为独立 arm 保留） |
| `suite_modes` | `suite --dry-run/--live/--resume/--finalize-crashed/--verify/--render-prompts`、`vericost565.trace.v1`、`OUT.requests.jsonl`、崩溃恢复、实跑前置条件 (c)(d)(f)(g)(i) | 未实现 |
| `hypotheses_live` | H1、H2、H3 及其评估器、`analysis_dryrun_validation.json` | 未运行，保持 `pending_live` |
| `second_model_and_training` | P1/P2 探针子集、flash-thinking 与 v4-pro arm、LoRA/SFT/GRPO、任何 GPU 或 torch 工作、第二供应商 | 未运行 |
| `generalization_claim` | 任何泛化声明 | `none` |

## 7. 记录但未修改的历史缺陷

`agent/llm.py` 与 `agent/bandit.py` 不在冻结清单内，但**本版本不编辑它们**；
`faultda_bench/semantic/deepseek.py` 在 660 份冻结文件内，**不可编辑**。记录如下：

- `agent/llm.py` 从不设置 `thinking` 字段，只传 `model`/`temperature`/`response_format`；
- `faultda_bench/semantic/deepseek.py` 从不设置 `thinking`，固定 `max_tokens = 800`、`temperature = 0`，
  并存在模型别名漂移；设计文档把它记为 pilot_v12 截断的可能原因；
- `agent/bandit.py` 的 `LinUCBBandit.select` 在闭包内计算分数且在模块层 import numpy，因此
  `VeriCostLinUCB` **重新实现**同一分数并只在训练函数内部惰性 import numpy 与 `agent.bandit`，不改动父类。

实跑版本必须在新代码中处理 thinking 与 token 上限，而不是改动上述文件。
在 thinking 模式下 provider 忽略 `temperature`，因此未来 P1 的输出不能通过重跑复现（见实跑协议第 5 节）。

## 8. 证据链与工程事实

- **提交（本版本，均以 Claude 作者身份、按名暂存、仅本地）**：`cae8621` 干净检出的测试发现修复；
  `f6a9d8f` C_freeze 预注册/实例/离线环境；`c8ab5c8` C_gate0a DP 与 INV-DP 证书；
  `a6456b8` C_gate0b Gate 0 regime map 与学得策略；`1492513` C_plan 冻结计划与一次写入审计；
  `25ff1c6` 把重放来源标记排除在字节比较之外；`96d16c0` C_eval 离线策略对照与分析；
  以及本次发布提交。
- **测试**：完整回归 **838 项**（0 失败、0 错误、2 跳过）；0.5.65 子集
  `-p 'test_faultda_vericost565*.py'` 为 213 项。分支基线 `540f7fb` 为 625 项、0 失败、
  **7 个错误**（干净检出缺少 `work/` 目录的历史问题），该问题由本版本的第一个提交修复，此后错误数为 0。
- **冻结**：`faultda_bench.termination555.audit` 退出 0，`"frozen_files": 660`；
  `540f7fb..HEAD` 的修改/删除/重命名集合只含 7 个允许路径。
- **一次写入**：10 个产物全部只写一次，第二次写入抛 `FileExistsError` 且不覆盖；git 历史层面的
  "只增一次、不改不删不重命名"由 `audit --write-once` 与 `suite --preconditions` 强制。
- **跨解释器字节一致**：7 个产物在 CPython 3.11.15 与 3.12.13 下重算后逐字节相同；
  **唯一记录在案的例外是 `learned_policies.json`**（LinUCB 训练需要 numpy，本机 3.12 没有 numpy 且离线无法安装），
  其缓解措施是它的每一个消费者（`learned_eval.json`、`offline_eval.json`、`analysis.json`）都在两个解释器下重算。
- **墙钟（8 worker）**：证书 869.6 s；gate0 rev1 220.7 s、d1 878.4 s；训练 489.1 s + 14.7 s；
  学得评估 271.6 s；离线评估 287.1 s；分析 0.3 s；`audit --all` 270.6 s；`audit --cross-version` 1138.3 s。
- **零 API 证据**：`faultda_bench/reports/vericost565/` 下不存在任何 `*.requests.jsonl`；
  `audit --no-network` 在 patch 掉 `socket.socket` / `socket.create_connection` / `socket.getaddrinfo` /
  `urllib.request.urlopen` 的子解释器中跑完 7 个 CLI 模式；`analysis.json` 带
  `"api_calls": 0, "cny_spent": "0.000000"`。
- **验收登记**：`faultda_bench/protocols/acceptance_v48.json` = acceptance_v46 的 660 份冻结映射 + 本版本
  全部新证据的 sha256（命名为 v48 以避开并行 0.5.60 工作占用的 v47）；
  `faultda_bench/reports/vericost565/audit_0565.json` 为 `audit --all` 的记录。

## 9. 证据边界（必须与每个数字同时陈述）

`split: development`、`seen_cluster: true`、`independent_test: false`、`generalization_claim: none`。
没有真实模型结果、没有独立测试集、没有新来源、没有任何 provider 请求，因此**不对任何模型能力、泛化性或
方法新颖性作出声明**。NO_GO 清单中的 "only the old dev cluster shows it" 在本版本**未被解决**，如实记录为未解决；
"RL does not beat a rule or SFT with the same representation" 在本版本**被触发**，且由于表示能力已独立确认，
该触发不能被解释为动作集缺陷造成的假象。独立人审仍为 `not_arranged`，科学门仍为 HOLD。

---

## English summary

**Scope: 0 API calls, ¥0, 0 downloads.** This version builds only the offline analytical core of VeriCost:
a byte-priced paged verification environment, an exact DP upper bound with a C1–C5 optimality certificate,
the Gate 0 regime map, and an offline comparison of 13 arms. There is no live model round, no new source and
no independent test set, because the owner's priority item 3 requires the single research claim to be chosen
before a single-use independent test set is consumed. The ¥30 authorization is carried forward unused.

**Headline finding (negative, reported unsoftened).** On the pre-registered primary instance set DEV-SYN and the
rev-1 latent model, a cheap fixed rule stays inside ε = 0.05 of the exact DP in **every** admissible regime, so
`hard_stop: true`, `trigger: true`, `scope: measurement`. At the primary regime `k0.30_L3` the minimum is
`min_fixed_r = 0.0315391087846` with `E[U*] = 0.682267789726`, attained by the **F_hist** family (a 9-cell
MAP-type × size lookup). The benchmark's primary regime is therefore **bypassable by a cheap fixed rule**;
this is measured and priced, not prevented, and **no unbypassability claim is made**. The same map differs on the
real seen slices: on DEV-SEEN `min_fixed_r` is 0.0999024644006 / 0.180085602665 at k1.00_L1 / k1.00_L3
(ALL: 0.0744909677605 / 0.135920618803), both above ε, so bypassability within ε is a property of the
synthetic-shaped profiles, not of the real seen slices at κ = 1. No single rule is within ε across all admissible
regimes on any set (`within_epsilon_all_admissible: false` everywhere).

**Does a CPU-learned policy beat the best fixed rule at equal cost? No.** At the primary regime the normalized
expected regret is `bf = F_hist` 0.014189449731 < `thompson` 0.0241588323286 < `linucb` 0.155694955762 <
`q_only` 0.307923762624. The confirmatory hypothesis O2 is **FALSIFIED by the point estimate**: all four cluster
ΔU values are negative, mean −1.55222169109, exact one-sided sign-flip p = 1.0, `dominated: false`
(q_only is cheaper by 0.0576311217151 cost units but less safe by 0.257396515255). `gap_recovered` is negative for
every learned arm. Cluster bootstrap (descriptive only): ratio −0.293734312893 [−0.476548585633,
−0.216085122564]; macro −0.314931120737 [−0.503467682211, −0.216149562513].

**Under-power statement (pre-registered before any number existed).** The development set has 4 clusters, so the
exact one-sided cluster sign-flip floor is 2^-4 = 0.0625 > α = 0.05 and no p value can ever clear α; every O-verdict
is `INCONCLUSIVE (under_powered)` unless FALSIFIED by the point estimate or by dominance. The O2 MDE is
0.991834342603 U units (0.0469223856362 normalized regret units); the observed effect is larger in magnitude and
in the wrong direction.

**Certificate.** C1–C5 all pass at `tol = 1e-9` with `c3_scope: full` (no reduction); max violations 1.11e-16,
1.11e-16, 3.33e-16, 3.33e-16, 0.0; sha256 `668c4f32fedd5c1bb78b72d22d22f07275622dc84a85b5f5e6eac4c52e08b8a7`.
Each guard is demonstrated **failing** with its real exception text, not merely passing.

**Learner diagnosis.** The pre-registered q_only flag prediction was not met and the record of the prediction —
never the measurement — was amended (`post_eval_erratum`, seq 3). Under the pre-registered configuration and
episode budget tabular Q does not recover the DP's post-flag action; this is **under-training, not a
representation defect** (scoring the same nine gate actions with the DP's own action values returns
`spot_flagged`), and whether another configuration would recover it is **untested**.

**H1–H3 stay pre-registered and `pending_live`** with the corrected prices, the Beijing peak windows and the
review-5 NIT 7 corrections recorded in `VERICOST_0565_LIVE_PROTOCOL.md`; they are never presented as findings.

**Evidence boundaries.** `split: development`, `seen_cluster: true`, `independent_test: false`,
`generalization_claim: none`. No model capability, generalization or novelty claim is made anywhere. The
positioning decision between "independent research increment" and "engineering diagnostic benchmark" is the
owner's; the evidence for it is assembled in `CLAIM_DECISION_INPUT_0565.md` and the decision is **not** made here.
