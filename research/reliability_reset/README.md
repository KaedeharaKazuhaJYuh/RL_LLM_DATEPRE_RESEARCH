# Reliability Reset：Agent 评测研究线

当前研究版本 **1.1.05**。当前主线为**真实通信流量上的少标签半监督持续学习**，重点检验 SNN 包事件时间建模在时间漂移下的作用。FaultDA、AppWorld 与 NIKA 保留为历史工程和评测记录。研究问题与设计见[持续学习计划](COMMUNICATION_TELEMETRY_CONTINUAL_LEARNING_RESEARCH_PLAN_2026_11_09.md)及[实验协议 v0.1](experiments/communication_telemetry/COMMUNICATION_TELEMETRY_EVENT_DRIFT_GATED_SSL_PROTOCOL_V0_1_2026_11_09.md)。

## 当前研究阶段

- **研究问题：**每期只获得少量标签、同时接收大量未标注流量时，怎样在真实网络时间漂移中适应新变化，并避免遗忘旧服务？SNN 包事件动力学是否能在同标签、计算和记忆预算下改善这一折中？SNN 流内时间编码与跨期记忆分别作为独立因素评估。
- **当前机制候选：**“稀疏标签锚定的分视图三态更新门”。分别监测包事件与流级摘要视图的变化；用更新前预测及当期延迟释放标签判断证据属于预测损害、无实质损害或证据不足；仅在标签支持预测损害且伪标签可靠时，允许无标签样本更新 SNN 时间分支。该机制仍是待检验假设，不是已建立的论文创新。
- **数据与实验状态：**CESNET-TLS-Year22 XS 档已确认可通过官方 Range 接口获取，完整文件为 2,692,800,942 字节；当前下载未完成，尚无日期×服务 census、冻结实际切分或 ANN/SNN 模型结果。W10 exporter 变化作为独立测量流程压力测试，不并入自然流量主结果。详细限制见[数据契约审计](experiments/communication_telemetry/CESNET_TLS_YEAR22_CONTINUAL_DATA_CONTRACT_AUDIT_2026_11_09.md)。
- **当前执行顺序：**续传 XS → 完成 HDF5 检查和日期×类别 census → 冻结真实切分与标签预算 → 运行配对 ANN 基线 → 运行 SNN 与持续学习/半监督基线 → 检验三态门控的独立作用。当前尚未训练模型。

## 归档研究与历史证据

- **NIKA 数据包丢失/报告丢失候选：**归档为工程与规则基线，不再是当前科学主问题。标准任务生成器不产生 leaf→service 目标故障，候选自定义注入路径未完成运行时配对验证；已有源码线索和计数规则审查不能替代 Agent 配对结果。[P4 轨迹交叉核验](experiments/communication_telemetry/NIKA_PUBLIC_P4_TRACE_CENSUS_2026_11_07.md) · [LossSight 与计数器审查](experiments/communication_telemetry/LOSSSIGHT_MCM_SOURCE_REPLAY_2026_11_07.md)
- **研究结论：**所查具体候选被原生完整评分识别；尚无跨独立任务、跨模型的可靠性误判证据。研究状态 **HOLD**。[原生控制](NATIVE_CONTROL_185.md) · [审计汇总](APPWORLD_AUDIT_CLOSEOUT_2026_10_27.md) · [论文主张内部评审](PAPER_CLAIM_REVIEW_2026_10_27.md)
- **历史官方轨迹：**复用 AppWorld 官方 GPT-4o 训练集 90 条、开发集 57 条历史轨迹。四个开发案例已由两位人工审阅者独立盲审，未形成原生通过但违规的证据链；其余轨迹的副作用不因此得到裁决。147 条 0.1.0 历史评分重放中，76 条归档通过有 51 条在离线重放中失败、没有失败转通过；这是档案重评分差异，不代表原始在线评分漏判。四例零哈希条件对照与上游已公开的 PR #219 条件一致，但不构成完整 PR 复现。新的直接近邻已对 1,929 条编码 Agent 归档评测重跑并检验固定历史决策，故本项目的 147 条单血缘结果作为工程复现案例，不作为独立论文贡献。[147 条重放审计](APPWORLD_CENSUS_2026_11_06.md) · [清点](EVALUATOR_GAP_190.md) · [盲审与四例对照](APPWORLD_REVIEW_2026_11_02.md)
- **最新接口试跑：**在同一原生训练任务中实跑 DeepSeek API 和 CUDA 本地小模型，记录原始提案、工具响应及模型用量；双方均未完成任务，独立安全裁决仍未知。[试跑结果](APPWORLD_PILOT_195.md)
- **1.1.0 扩展：**增加 Qwen 与 SmolLM 本地模型，四个检查点在同一已见任务中均未完成；恢复了真实 NPU 量化模型生成，但尚无跨任务或 NPU 精度结论。[1.1.0 结果](APPWORLD_PILOT_110.md)
- **六场景试跑：**DeepSeek、Qwen、Granite 和受输入上限约束的 SmolLM 均未产生原生评分通过的运行；后者五条受资源约束，Granite 为探索性补充。两条扩展轨迹的成功状态与完整原生评分不一致，已在新进程复核。[1.1.05 结果与逐次调用账本](APPWORLD_PILOT_115.md)
- **已有开发结果：**60 条旧记录中有 24 次预算拒绝、3 次升级，22 条未安全完成记录的终态正确；这些是相关开发轨迹，不是独立任务样本。[终止分类](TERMINAL_TAXONOMY.md)
- **最新评估回应：**已整理三份评估与价格对照。旧评估器默认 `dev_seen` 可能混入合成 profile；未来重算请使用显式筛选的 [seen_evaluation.py](seen_evaluation.py)。[评估回应](REVIEW_RESPONSE_SEEN_2026_10_28.md)
- **暂停的历史候选（HOLD，非当前主线）：DAComp-DA 路径分值契约。** 固定源手工核对了路径与父级上限冲突及现有评分资产范围，但尚无052/063/084的Judge分数、超额评分或分数饱和证据。24题三阶段盲审材料未发送、未填写；无独立评分影响证据。该线作为历史审计保留，不再占据当前研究主线。详见[历史候选门槛记录](ONE_PAGE_RESEARCH_DESIGN_GATE.md)与[契约审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)。
- **评分分子/分母冲突候选（HOLD，非贡献）：**新近邻 *Do Agent Benchmarks Do What They Say?* 已追踪工具契约、实现与 evaluator 的 score provenance；*Measurement Risk in Supervised Financial NLP* 已研究 rubric/metric/aggregation 敏感性与排名稳定性，故通用审计方法不再作为创新主张。补查固定发布物发现3条评分记录、覆盖2个底层任务ID：英文GPT-5一条，中文Qwen3-Coder-Plus两条。直接观察到 rubric criterion 1.6/1.7合计4分被Judge计入raw分子、而metadata类别上限不含这4分，仅在英文 `dacomp-006`；对应原生45.5，标题20分母38.0，路径派生19分母约39.58，后二者未获权威裁定。中文 `dacomp-zh-005` 与 `-006` 提供更多实际记录，但与英文任务在模型/语言/任务设置上不构成受控配对，尚无多模型排序证据。仍需独立审阅，科学状态 **HOLD**，不能称评分错误或论文贡献。[评分记录与近邻边界](SCORE_CONTRACT_IDENTIFIABILITY_SCREEN_2026_11_06.md) · [固定资产审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md) · [一页门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。
- **次级候选（HOLD）：DAComp-DA 端到端分数复现。** 公开 Issue #11 报告 GPT-5/DA-Agent 两次完整100题重跑为61.08、62.14，而论文Table 5为50.84 ± 3.12；报告没有这两轮的逐任务产物，仍未获作者确认。固定发布仅有英文006与中文005/006三条评分行，无法解释全量分差。重复评分、基准复跑和编码Agent评测重放均是直接近邻；只在能取得配对逐题产物、区分Agent/Judge/配置来源且影响预设跨模型结论时继续，否则NO-GO。[一页研究设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。
- **关闭的候选（NO-GO）：DAComp-DE 数据库状态血缘。** 80 个 implementation/evolution 任务对应 41 个精确起始数据库状态；已核对重复成员字节哈希。应用族×任务类型基线设计秩为58，加入全部41个状态簇指示后仅增加1个自由度，且全部来自Salesforce；没有同一任务提示跨状态的重复运行。因此当前公开任务结构不足以支撑跨应用独立状态效应主张，不启动该候选的Agent实跑。这不是“状态效应为零”的结论。完整记录见[状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)和[可识别性结果](DAComp_STATE_IDENTIFIABILITY_2026_11_06.json)。DCR 因果效度主张已关闭；DCR 支持集与追溯更正候选均保持 HOLD/历史记录，不作为已建立贡献。

## 新近邻边界（2026-11-07）

- **状态化工作流与重复运行已被直接覆盖。** ThinkingBox-Bench 发布507个有状态业务工作流，采用可执行的终态/副作用检查，并报告20次尝试下的 pass@1、pass@20 与 pass^20；STATE-Bench 有450个企业工作流，pass@1按每题五次运行平均，另报全五次通过率 pass^5。因此，本项目不能再将“状态化工具任务”“最终数据库状态评分”“重复运行可靠性”或其组合本身主张为新贡献。[ThinkingBox论文](https://arxiv.org/abs/2608.19741) · [ThinkingBox固定数据发布说明](https://github.com/microsoft/thinkingbox-data/blob/main/releases/thinkingbox_bench_v1/README.md) · [STATE-Bench](https://github.com/microsoft/STATE-Bench)
- **证据依据行动同样有直接邻近。** EnvTrustBench公开页面将任务定位为环境证据与真实状态冲突时的行为评测，使用最终工件和轨迹关联的oracle；该页面称稿件审查中，原始轨迹未公开。因此它可用于划定近邻，但目前不能作为可独立复算的数据源。[项目页](https://envtrustbench.github.io/EnvTrustBench/)
- **提交后不确定与重试语义已被直接研究。** *Where Does Exactly-Once Live?* 对服务端迟到提交、回执丢失、重投递、幂等键和多种恢复策略进行了模型、harness、tool-contract 对照；因此本项目不能把“超时后是否重试”或“幂等接口降低重复副作用”单独作为新机制。[论文](https://arxiv.org/abs/2609.29095)
- **Agent 完成声明与轨迹不一致已有专门评测。** *Quantifying Overclaiming Propensity in Frontier LLM Agents* 与 *Who Verifies the Agent's Success Claim?* 分别研究未完成时的误导性声明及评分时纳入自述造成的泄漏；不能将一般“Agent 说完成但证据不足”作为独立贡献。[OverclaimBench](https://arxiv.org/abs/2609.20812) · [Self-Report Leakage](https://arxiv.org/abs/2610.29609)
- **数据分析报告的数值依据已有直接邻近。** NumTrace 对财务 Agent 数值声明的 source、entity/concept/time/unit/scope binding 进行审计；DataSpace 使用确定性 evaluator 检验完整表格结果。因而“数值声明需绑定证据”或“数据分析结果可验证”本身不构成本项目的新颖主张。[NumTrace](https://arxiv.org/abs/2610.34887) · [DataSpace](https://arxiv.org/abs/2608.03451)
- **Rubric/scorer 可靠性也已成为直接近邻。** *Same Outputs, Different Scores* 研究固定模型输出受 scorer 规则影响；RubricEval、PReMISE 与 RuVerBench 分别评测 rubric 级判断、rubric 的测量性质和 Agent 场景 rubric 验证。FaultDA 当前候选只能继续检验路径子项与父级 ceiling 冲突是否造成真实评分饱和或比较变化，不能把一般 rubric 审计、Judge 不稳定或重评分敏感性当作贡献。[Same Outputs, Different Scores](https://arxiv.org/abs/2611.03377) · [RubricEval](https://arxiv.org/abs/2603.25133) · [PReMISE](https://arxiv.org/abs/2605.30803) · [RuVerBench](https://arxiv.org/abs/2606.29920)
- **研究含义：**新候选必须指出这些基准仍未回答的明确问题，并证明有公开或可合法取得的配对结果可回答；不能只把相同任务、评分终态或重复次数换成 FaultDA 的术语。该检索没有产生新的论文贡献，科学状态仍为 **HOLD**。

## 工作入口

| 目的 | 入口 |
| --- | --- |
| 离线证据审计与程序控制 | [audit.py](audit.py) · [controls.py](controls.py) · [数据契约](SCHEMA_V1.md) |
| 公开证据、工具规划与终止 | [evidence_planner.py](evidence_planner.py) · [joint_control.py](joint_control.py) · [tool_contracts.py](tool_contracts.py) |
| 终止分类与 AppWorld 重放 | [terminal_taxonomy.py](terminal_taxonomy.py) · [native_replay185.py](native_replay185.py) · [terminal_binding185.py](terminal_binding185.py) |
| 真实轨迹清点与未决风险 | [official_dev_inventory.py](official_dev_inventory.py) · [结果与实验计划](EVALUATOR_GAP_190.md) |
| 独立盲审与历史评分重放 | [审阅结果、查新和复核方法](APPWORLD_REVIEW_2026_11_02.md) · [原证据包](evidence/appworld-review-2026-11-02.bundle) · [上游方案对照包](evidence/appworld-pr219-control-2026-11-05.bundle) |
| 真实模型与工具接口试跑 | [appworld_pilot195.py](appworld_pilot195.py) · [试跑结果](APPWORLD_PILOT_195.md) |
| 模型模板解析与 NPU 重建 | [appworld_pilot110.py](appworld_pilot110.py) · [本版结果](APPWORLD_PILOT_110.md) |
| 六场景试跑、调用成本与评分重放 | [appworld_pilot115.py](appworld_pilot115.py) · [结果与账本](APPWORLD_PILOT_115.md) |
| 原始协议、实验与复审流程 | [历史与复审指南](HISTORY_AND_REVIEW_GUIDE.md) · [更新记录](CHANGELOG.md) |
| 研究草稿与新候选设计 | [研究草稿](PAPER_DRAFT.md) · [重置协议](RESET_PROTOCOL.md) · [一页设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md) |

```sh
python -m research.reliability_reset.terminal_taxonomy
python -m unittest tests.test_reliability_terminal_taxonomy tests.test_reliability_reset_seen_evaluation
```

第一条只读并打印摘要；使用 `--output` 需要一个不存在的新路径。历史命令、原始证据和运行限制仍保留；软件控制、哈希一致性与本地重放不能替代独立人工审阅或真实模型验证。
