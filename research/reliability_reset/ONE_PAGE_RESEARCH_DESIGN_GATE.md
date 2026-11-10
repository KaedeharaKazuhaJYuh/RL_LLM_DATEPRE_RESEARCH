# 当前候选一页准入门槛：故障耦合 INT 观测删失与网络 Agent RCA

日期：2026-11-07　｜　长期方向固定：AI Agent 对大规模通信网络遥测进行可靠分析与运维决策。只推进这一条主线；本候选被否证时关闭假设，不换成无关研究方向。

**2026-11-09 主线推进：**NIKA 固定配对的端口映射疑问已由完整源码调用链审计解决：Agent 初始 task description 包含接口级拓扑，默认 MCP 面可查 host 与 P4 counters。此前把 `p4rt read` 单一 JSON 不含 `peer` 推广为 Agent 不可见，是范围错误。该配对冻结为强规则负对照；详见[映射审计](experiments/communication_telemetry/NIKA_AGENT_VISIBLE_TOPOLOGY_MAPPING_AUDIT_2026_11_09.md)。长期方向继续聚焦 AI × 通信网络遥测，下一项深挖主题转为网络流量在时间漂移和标签稀缺下的持续学习，研究设计见[通信遥测持续学习研究计划](COMMUNICATION_TELEMETRY_CONTINUAL_LEARNING_RESEARCH_PLAN_2026_11_09.md)。此计划不是 Agent 实验准入，也不代表任何模型结果。

**2026-11-09 边界记录：**CESNET 多层级遥测分析是同一通信遥测主线内的一个*离线可行性候选*，并未取代 NIKA 主候选，也未获 Agent/API 实验准入。其独立论文增量尚未成立；完整一页门槛见[CESNET 多层级 Agent 设计](CESNET_MULTISCALE_AGENT_GATE_2026_11_09.md)。先验证真实字段能否形成可人工审查、且精确结果/测量契约有区分力的任务，再决定是否纳入当前主门槛。

**2026-11-09 配对预检审计：**检查当前本地 v0.9 runner 时发现，原来的 `passed` 只由流程是否走到 `complete` 决定，无法保证真实丢包臂确实零服务收包、同一流配置有效、collector 只留上游行或 report relay 未误丢；pinned 流量发送器也不记录实际发出的包 ID。因此 runner 现要求两臂流配置与五元组一致，并用源端 AF_PACKET 逐包记录实际发出的 `(flow_id, IPv4 ID)`；report-only 臂源端、service ingress、collector 上游 ID 必须吻合，leaf-loss 臂源端与 collector 上游 ID 必须吻合且 service 侧为零。还核验目标出口计数器存在、入口有流量、report relay 正常转发；`passed=true` 只有在完整成对账本通过时才成立。旧 `RUN1–RUN3` JSON 是 v0.7 report-only 结果，不得当成 v0.9 配对运行。当前工作流 push 触发分支已对齐 `comm-telemetry-crossday-load-audit-2026-11-09`；该工作流和 runner 尚未推送，所以没有新的 runtime 数据。此代码审计只提高下一次运行的测量有效性，不构成机制或 Agent 贡献；主假设仍 **HOLD**。详见[预检代码审计](experiments/communication_telemetry/NIKA_PAIRED_PREFLIGHT_CODE_AUDIT_2026_11_09.md)。

**本轮准入复核（2026-11-07）：**第五轮 pinned NIKA 双臂运行已保存 collector 原始行：report-only 臂 376 个唯一包组中 0 个路径角色反转，leaf-loss 臂 376 个中 1 个反转；此前另一轮的反转数不同，故不能把单轮比例解释成稳定现象。完整收尾 `passed=true`、`lab_closed=true`。结果见[复跑报告](experiments/communication_telemetry/NIKA_COLLECTOR_ORDER_RERUN_2026_11_07.md)和[结构化审计](experiments/communication_telemetry/artifacts/nika_pair_collector_rerun_20261107_retry1/NIKA_COLLECTOR_ORDER_AUDIT.json)。此次仍无 Agent 轨迹，也没有推翻先前低背景条件下目标端口计数差 376 vs 0 的 R0 负对照。

**Agent 可见性准入（2026-11-07）：**对上述两份保留的 collector JSONL 作离线比较，两臂各 752 行、376 个 flow/packet 键，所有行均为 `sink_seen=false`、`trace_complete=false`；按 hop switch 序列统计，两臂分布相同，leaf-loss 臂仅多 1 个单包顺序反转。评测侧 service 抓包为 376 对 0，但该抓包不属于当前已定义的 Agent 观察。故 collector-only 版本不能把成因标签当成可识别答案；若加入能区分两臂的端口计数，须先以完全相同输入重跑 R0 强规则。当前配对只保留为运行时/信息边界诊断，不进入 Agent 能力评分。详见[复跑报告](experiments/communication_telemetry/NIKA_COLLECTOR_ORDER_RERUN_2026_11_07.md)。科学状态 **HOLD**。

**工具面复核与候选裁决（2026-11-07）：**固定 NIKA 的 `p4_gateway` tags 会启用 `kathara_bmv2_mcp_server` 与 `kathara_telemetry_mcp_server`；`p4rt_exec(args)` 调用含 `counters` 子命令的 `p4rt_manager.py`，`int_query_telemetry(...)` 查询观察到的 INT 轨迹。端口 counter 可由标准工具读取。本轮 evaluator 侧 service 抓包为 376 对 0，但该轮没有两臂配对的 counter 快照；较早低背景运行曾记录目标端口 counter 差 376 对 0。故 R0 是强预期基线，正式对照仍须在相同配对窗口保存 Agent 与规则可见的 counter 输入。**NO-GO：**当前低速 terminal pair 暂不进入 Agent 能力实跑：collector-only 视图没有稳定区分信号；完整工具面下尚未补齐同轮 counter 快照与锁定后的强规则配对结果。此裁决只关闭这一具体实验设定；AI Agent × 通信网络遥测运维仍是唯一长期方向，整体研究保持 **HOLD**。任何替代设定须先通过一页门槛，给出不同于简单计数规则的可证伪预测。

**同方向候选复核（2026-11-08）：**新增对 NetOpsBench v0.2 全部 319 条 Agent 可见工具观测的 `Bad Peer AS` 规则检查：它在 26 条 BGP neighbor mismatch 上 26/26 命中，且在其余 293 条上无命中；因此它完全匹配 Agent 的 BGP 二元 verdict，但作为通用故障规则只有 TP=26、FP=0、FN=268、TN=25。该规则是事后观察到的窄类线索，不可冒充预注册或通用强基线；它足以否定“现有 BGP verdict 切片证明了 Agent 额外价值”。Skill 条件化候选详见[一页门槛](NETOPSBENCH_SKILL_CONDITIONING_GATE_2026_11_08.md)和[逐案审计](experiments/communication_telemetry/NETOPSBENCH_V02_SKILL_CONDITIONING_2026_11_08.csv)：现有切片的独立贡献 **NO-GO**；Skill 因果效应/跨任务泛化仍 **HOLD**，没有 skill ablation、held-out cluster 或第二模型，故不启动 Agent/API 实跑。

**同方向真实流量负载来源审计（2026-11-08）：**ServDeg 随数据发布的 README 明确 CC BY 4.0；本轮用本机 DuckDB 对 MON.parquet 目标列做全文件聚合，并读取完整 schema：3,185,436 个匿名 TCP flow、110 列、`start_time_aggr` 覆盖 53 分 49 秒、17 个 `location` 标签；包数中位数 6、P99 1,533、最大 6,928,103。点级 `SDd`/`SDj` 标记分别覆盖 2.70%/2.75% 行，持续事件 `SD_count>0` 仅 0.28%，必须使用不同分母。数据是聚合流特征，不含 PCAP、路径或设备/链路根因标签；只可作为 *trace-derived synthetic workload* 的统计参考，不可称真实包回放或 RCA 真值，也不能直接等同 NIKA UDP 流。报告、复算脚本和 JSON 见[ServDeg 单日可行性审计](experiments/communication_telemetry/SERVDEG_MON_WORKLOAD_AUDIT_2026_11_08.md)。此数据源审计未清除 NIKA 候选 HOLD；其余四日分布及生成器保真度仍待审计，未运行 Agent/API。

**ServDeg 五日负载漂移与时间戳完整性复核（2026-11-08）：**使用本地 Python + DuckDB `httpfs` 远程列式读取五个工作日；无 Docker、未完整下载四个远程文件。每天窗口约 42–54 分钟；`start_time_aggr` 缺失率为 52.21%–70.49%。MON 缺失时间戳行与非缺失行在 flow size 和 SD 标记率上显著不同（缺失组 `SDd`/`SD_count>0` 均为 0；有效组分别为 6.330%/0.656%），表明缺失具有选择性；其余四天缺失机制尚未分层。分钟统计只是有效时间戳下的 flow 起始 cohort，并非逐分钟传输速率；此前未过滤 NULL 造成的“极端峰值”已废弃。ServDeg 不用于分钟级负载校准，先查明五日时间戳缺失机制或改找有许可且时间完整的流量源。详见[报告](experiments/communication_telemetry/SERVDEG_WEEKDAY_SHIFT_2026_11_08.md)。NIKA 主候选仍 **HOLD**；没有 Agent/API 实验。

**CESNET-TimeSeries26 数据准入审计（2026-11-08）：**改用本机 PowerShell/公开 Zenodo API 核验主记录及四个分卷：均为 open、CC BY 4.0；全记录约 330 GB，故只读取 1.4 KB 的 `outages.csv`，未下载大文件。主集合明确记录的全网监测缺口只有 7 个事件簇，另有 6 个 subnet-local 事件且属于不同的纵向子集；拆分实体或时间窗不能增加独立事件样本。数据适合后续外部真实遥测验证/数据工程压力测试，但不足以单独支持 Agent 跨事件能力结论；“LLM 网络时序分析、遥测不足时归因/弃答、预测驱动决策”已有 CTBench、TelemetrySuffBench、CENTILE 等近邻。裁决：**数据准入受限通过，当前科学主张 NO-GO**；不改变 NIKA 主候选 HOLD，不下载全集、不启动 API。详见[CESNET-TimeSeries26 数据源审计](experiments/communication_telemetry/CESNET_TS26_DATASET_AUDIT_2026_11_08.md)。

**NetOpsBench ping 返回细分（2026-11-07）：**20 个端点匹配 packet-loss 案例中，初始 `anomalies_detected=true` 单字段规则对 ground-truth 故障判断为 **20/20**，Agent 为 **2/20**。ATIF 中 57 个匹配 ping 结果（490 发/433 收）又分成 13 个所有 ping 干净的案例（规则 13/13、Agent 1/13）和 7 个至少一次丢包的案例（规则 7/7、Agent 1/7）。此为单一上游模型轨迹的描述性核验；数值细分了已有上游错误，不形成独立机制。逐次事件见[匹配 ping 事件 CSV](experiments/communication_telemetry/NETOPSBENCH_V02_MATCHED_PING_EVENTS_2026_11_07.csv)，完整方法/限制见[审计报告](experiments/communication_telemetry/NETOPSBENCH_TEMPORAL_EVIDENCE_AUDIT_2026_11_07.md)。因为初始可见单字段已完全解释该子集 verdict，结束这 26 条公开轨迹的继续扩展归因；工作回到唯一 NIKA 候选的运行时账本和公平强规则否证。科学状态仍 HOLD，没有 Agent/API 实验准入。

**LossSight 直接近邻细分（2026-11-08）：**逐节核对 LossSight 论文后确认：它已提供 INT 缺失检测、时间/位置推断、原因诊断与缺失数据恢复；对持续黑洞还通过 INT Source/Sink 匹配计数差进行识别。因此，“遥测报告缺失可揭示数据面丢包”“融合端点计数做丢失定位”均不是本项目可主张的贡献。其论文主要把 INT-bearing packet 在 source→sink 路径中的缺失作为目标；我们当前 NIKA 配对中 report-only 臂是业务 UDP 包已到 service、sink 侧 exporter 生成的 UDP 报告在 collector 前丢失，与前者的阶段边界不同。该边界目前只是任务定义差异，不足以单独证明研究增量；且 LossSight 数据仓库页面列出的文件没有明显许可证字段，暂不把该数据集作为可再分发材料。候选只有在展示“sink 后报告通道故障 + 同权限同预算强规则仍无法解决 + Agent 行为改变评测结论”时才可能继续；否则关闭。来源：[LossSight 论文](https://tanlizhuang.cn/papers/2021-%E8%AE%BA%E6%96%87-TNSM.pdf)、[LossSight 数据仓库](https://github.com/lzhtan/LossSight-Dataset)、[RFC 9232](https://datatracker.ietf.org/doc/rfc9232/)、[IP 测量结果解释 Internet-Draft](https://www.ietf.org/archive/id/draft-liu-ippm-measurement-interpretation-00.html)。

**近邻与数据边界刷新：**除 Agent RCA Bench、CTBench 与 TelemetrySuffBench 外，2026-08 的 **FaulT-Bench** 已在 8 个网络拓扑上构造 200 个核心真实故障/错误报告场景和 360 个固定健康状态的报告改写；复用 NIKA 工具接口，给三个 Agent 相同 22 个工具和 20 轮预算，并公开 3,960 条冻结运行记录与复算工具。其公开场景索引还含 `simple-bgp-false-premise-packet-loss`：健康网络、不注入故障的“网络丢包”误报。因此“验证 packet-loss 报告是否真实”已有直接近邻，不能作为本项目贡献。索引元数据中未见 collector/telemetry/INT 故障标记；论文描述的是错误用户票据，而不是同一目标流的业务送达与遥测报告生成/收集状态配对。该协议差异或可保留为当前候选的精确边界，但不是贡献证明。**NetArena** 也已用动态生成任务评估网络应用的正确性、安全性和时延。故一般网络 Agent 诊断、接口成本收益、证据充分性、“同视图异因”以及错误报告核验均不作本项目贡献。公开大流量数据也不自动补足因果真值：ServDeg 的约 1,395 万条 flow 记录含时延/抖动服务退化标签，但来自单一宿舍网络且标签不是根因；UNSW-IoTraffic 含 9,550 万个包和 flow/协议层数据，但没有故障事件真值。传统网络遥测已有流量抽样、INT 空间抽样和按故障保留遥测工作，因此一般“压缩 telemetry”也不新。当前 NIKA 因果配对与 Agent-vs-rule 假设仍 **HOLD**；任何粒度/规模实验只有在新的一页设计逐项说明相对这些工作的增量、真值与同信息强规则后才准入。见[近邻与公开数据复核](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md#2026-11-07-近邻与公开通信数据集复核)。

**FaulT-Bench 场景正文补充审计（2026-11-07）：**按公开仓库提交 `ab8c45f808fb0c2a1ae5c029bcfe0194617c36f2`，对索引所列 200 个 `base`/`cex` 核心场景文件作定向词项扫描：`collector`、`exporter`、`report channel`、`sink report`、`INT` 均无命中；`telemetry` 仅命中 1 个 FRR 修复说明，描述 CLI/telemetry plane 恢复。该审计支持“核心语料未显式描述遥测采集/报告通道故障”的有限范围判断；它是词项审计，不能证明不存在未使用这些术语的等价任务，更不构成本项目新颖性证据。报告与审计范围见[通信遥测方向记录](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md#2026-11-07流级负载候选的近邻预筛)。

**NetOpsBench v0.2 公开轨迹复算（2026-11-07）：**固定源码与 HF 数据 revision 后，重算 319 条逐案轨迹的二元 verdict：只使用初始可见 `anomalies_detected` 单字段的零工具规则答对 274/319（85.9%）；公开 DeepSeek Agent 轨迹答对 227/319（71.2%）。packet-loss 子集规则 25/26、Agent 5/26；这与上游已报告的 25/26 formal signal、5/26 correct verdict 一致，故是已知现象上的单字段基线对照，不是新失败模式或论文贡献。该规则只用了 Agent 可见信息的子集，未匹配全部观察/工具预算，不能称为强规则公平对照。26 个 packet-loss 案例中，有 20 个轨迹至少包含一条与 Pingmesh anomaly 相同主机/IP 端点（正向或反向）的 live ping；18 个 Agent 在已有这种端点级探测后仍判断错误。端点匹配不代表相同 ICMP hash、故障接口或测量窗口。代码调用顺序核查确认 Agent 的 live ping 发生在故障 episode 观测后、incident close 恢复前；不能将该证据描述为“自动恢复后的状态”。案例有关联且只有一个 Agent 配置，不作显著性推断。详见[轨迹审计报告](experiments/communication_telemetry/NETOPSBENCH_TEMPORAL_EVIDENCE_AUDIT_2026_11_07.md)、[逐案 CSV](experiments/communication_telemetry/NETOPSBENCH_V02_CASE_AUDIT_2026_11_07.csv)及[复算脚本](experiments/communication_telemetry/audit_netopsbench_v02_traces.py)。该证据强化时间窗/探测对象对齐的诊断工程问题，但不改变唯一 NIKA 配对候选的 **HOLD**；不据此启动模型 API 或另起研究方向。

**范围说明：**本文件开头的通信遥测问题及其准入表是当前唯一有效门槛。其后的 AppWorld、DAComp、WorkBench 等候选条目是历史审查记录，不是当前并行路线或下一步任务；若旧段落使用“当前候选”等措辞，以本范围说明和[通信遥测研究章程](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md)为准。

**同一主线内的流级负载候选裁决（2026-11-07，NO-GO）：**候选说法是“只丢少数目标流、保留同端口并发流，从而稀释端口聚合计数；网络 Agent 是否比强规则更能区分业务丢包与 sink 报告丢失？” pinned NIKA 源码复核确认这不是现成任务可达条件：`SilentEgressPacketLoss` 注入参数传递 `bmv2_port`，经 `set_deterministic_loss(..., port, threshold)` 写入；P4 `internal_fault_loss_config` 唯一键为 `standard_metadata.egress_spec`；`p4rt_manager.py` 读取的 ingress/egress counters 也按端口编号聚合。因此固定注入会作用于该端口全部出站包，不能只损伤一个五元组。若在 service 主机用 `tc` 额外丢包，故障位置会移到 leaf egress 之后，不再是原 NIKA 故障；改 P4 匹配五元组则属于新的版本化环境，不能冒称原基准复现。

**近邻否证：**多点被动计数、LossSight、SPADA/PINT 已覆盖 flow-level loss localization、INT loss handling 和受限流级监测/聚合。更宽的“给 Agent 不完整遥测并判断故障来源/何时弃答”也已由 TelemetrySuffBench 的 telemetry masks 与 exact-equal ambiguous origin pairs 评估；FaulT-Bench 则在 8 个网络拓扑上测试不可靠故障报告，并复用 NIKA 工具接口。因此，单加流选择性、并发流量或缺失 sink 行没有独立科学增量。

**裁决与停止条件：NO-GO。**不扩建 flow-selective P4 fault，不以 host-side `tc` 变相制造 NIKA 原生任务，也不调用 Agent/API。若未来出现新的可复核机制，必须先证明它不属于上述流测量、遥测充分性或不可靠报告工作，并说明相同工具与预算下强规则失败而 Agent 能获得何种额外可行动证据；否则维持 NO-GO。本裁决只关闭流级负载扩展，不改变唯一原始 NIKA packet-loss/report-loss 候选的 **HOLD**；研究方向仍固定在 AI × 通信网络遥测。

## 可证伪问题

> 当 packet 已产生所有上游 INT 行、但缺少 leaf/sink 行时，网络 Agent 能否从相同初始遥测视图出发，在相同工具权限与探测预算内取得可区分证据，区分“业务包在最后 leaf→service egress 丢失，因此 sink 报告未生成”与“业务包已转发、sink 报告随后在 UDP 通道丢失”，并比使用同一可见信息的强规则更准确地归因？若最终可见信息被人为限制为两臂完全相同，则标签不可识别，不构成 Agent 能力评测。本问题不把检测缺报本身作为贡献；当前不评测 RL、停止策略或一般探测策略。

## 一页准入审查

**并发负载准入更新（2026-11-07）：**NIKA `p4_dc_gateway` 有生成式 all-to-all O-D 流量入口，但这不是实测通信负载；SNDlib 矩阵重放目前属于 ISP traffic 子系统，尚未证明可用于该 P4 配对。固定 P4 loss hook 按 egress port 作用于该端口全部出站流量，当前没有已验证的五元组级注入，因此把背景流量送往目标端口会同时改变故障影响范围。不得以这种配置制造 R0 盲点或据此准入 Agent；先证明背景来源、拓扑映射与故障作用范围都有效。详细源码审计见[研究方向记录](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md#2026-11-07并发背景负载的-nika-可行性审计)。

**路径顺序审计（2026-11-07）：**对第四轮 relay 原始事件的复算发现，376 个数据包中有 10 个在 relay 接收序列里出现跨角色路径次序反转；其中 1 个数据包的两条转发上游记录为 spine 先于 gateway。固定版 NIKA collector 的 loopback UDP 组件复现也确认其 `hop_sequence` 保留报文到达顺序，不按拓扑排序。但原 NIKA 运行没有保留原始 collector rows，因此尚未确认该条实际进入 collector 输出或影响 Agent。R1 必须依据拓扑和逐 hop 时间重建路径；配对预检脚本现已改为按 arm 保存目标流原始 collector 行和哈希，下一次运行可直接复核。复算：[报告](experiments/communication_telemetry/NIKA_RELAY_HOP_ORDER_AUDIT_2026_11_07.md)、[JSON](experiments/communication_telemetry/NIKA_RELAY_HOP_ORDER_AUDIT_2026_11_07.json)、[脚本](experiments/communication_telemetry/audit_relay_hop_order.py)；组件复现：[JSON](experiments/communication_telemetry/NIKA_COLLECTOR_ORDER_SEMANTICS_2026_11_07.json)、[脚本](experiments/communication_telemetry/reproduce_collector_arrival_order.py)。

| 准入项 | 证据与判断 |
|---|---|
| **原始任务契约** | NIKA 0.2.0 release 有 P4 `silent_egress_packet_loss`，原生分数只评价最终 `root_causes`，没有“遥测管线故障 vs 业务面丢包”的判断标签或动作合同。官方 dev-066 的目标是 `gateway_1:eth1`，按 topology builder 的端口创建顺序，该口连接 spine；其后仍有 spine/leaf 报告，不能充当终端 report-only 等价配对。研究需另建版本化任务，在最后 leaf→service egress 注入数据面丢包，并配对丢弃该 leaf 已生成的 sink UDP report；保留原生分数，不主张 scorer 漏判。 |
| **源码依据与可达性** | Pinned NIKA 的 gateway/spine/leaf 使用同一 P4 pipeline；loss hook 在 ingress，per-hop exporter 只对实际捕获的出口 INT 帧发 UDP report，leaf exporter 将自身行标成 sink。通用 manager 的 `gateway-config --kind loss` 从 intent 查找指定 switch 并写共享 loss 表，源码未见 switch-role 限制；但官方 `p4_gateway_port_target()` 只生成 gateway/spine 上 peer role 为 spine/leaf 的端口，0.2.0 dev/test 标准任务也只指向 `gateway_1:eth1`。因此 leaf→service 注入是自定义版本化任务路径，尚无运行证据，不是官方任务已支持的场景。collector 将收到的行追加为 JSONL。`p4rt_exec read` 返回 forwarding member 的 egress port ID、LPM、计数与部分 runtime config；`counters` 返回按端口聚合值，不提供 per-flow source/sink counter。BMv2 ingress drop 按官方语义不进入 egress pipeline。**源码推论：**低背景下计数/路由信息可能直接解开终端故障；并发背景下聚合可混淆，必须测量。 |
| **近邻覆盖** | LossSight 已覆盖“Telemetry Server 未收到预期 INT report 即记为丢失”的检测，并把 sink→server 传输/处理延迟纳入检测时延；因此“报告通道丢失检测”不属于本项目增量。TelemetrySuffBench 已构造完全相同的模型可见遥测、不同隐藏来源标签的配对，并评估来源归因与安全弃答；故一般“同视图不同原因”的不可辨识问题也不是增量。NetOpsBench 已在 live SONiC-VS/Containerlab、多拓扑规模上评估网络 Agent 的故障检测、类型判断与设备/接口定位，公开场景含 packet loss；因此通用网络 Agent 故障诊断、规模扩展及 packet-loss 定位都不是本项目增量。其公开方法页所列场景没有显示 INT sink exporter/collector 报告丢失的成对注入；这只是文档层观察，须在固定 release 源码中核验后才能作为覆盖边界。当前只保留一个更窄、仍未证实的差异：真实网络中末端业务包丢失与 sink UDP report 丢失的因果配对下，Agent 能否在相同初始视图后通过网络工具获取证据，并在相同权限/预算下胜过同信息强规则。交互式网络探测本身已有主动/被动定位和顺序探测先例，不作为算法贡献。官方 NIKA dev-066 的 gateway→spine 故障与 leaf sink 报告丢失会产生不同的中间 hop 轨迹，不能被拿来充当等价对照。 |
| **最小配对设计** | 已在 pinned NIKA 小拓扑完成一轮同固定流配置的 report-only 与 leaf→service loss 配对。每条流在报告丢失臂服务端到达 94 包、真实丢包臂到达 0 包；两臂 collector 每流均有 188 条上游行、零 sink 行。服务端真值只进 evaluator ledger。来源：[配对报告](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.md)与[原始结果](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.json)。
| **指标和预测范围** | 此单一干净拓扑中，两臂目标 egress 计数为 376 vs 0，显示预设 R0 规则族可区分这一配对；源码一致的五日负载代数投影也显示端口级 10000 bp 损失条件下规则可确定地区分 30/30 个公式场景。仍未在独立簇冻结和评估，不能据此声称跨簇性能或 Agent 价值。下一项准入问题是 Agent 可见工具输出能否将目标服务前缀映射到该端口；必须用实际 MCP 原始输入/输出复核。只有映射边界存在且在保持任务契约的条件下导致冻结 R0/R1/R2 可复核失败，才重开 Agent 准入。来源：[配对报告](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.md) 与[投影更正](experiments/communication_telemetry/SERVDEG_CROSSDAY_PROFILE_AUDIT_2026_11_09.md)。
| **权限与公平性** | NIKA 默认诊断权限为所有工具和节点；`exec_shell` 可在目标节点运行命令，`p4rt_exec` 原始参数可触发 `read`/`counters` 也可触发写配置子命令。`read` 无 switch 参数时会读所有交换机，并返回转发 group/egress port ID、LPM 与计数；sanitizer 会移除 `internal_fault` 字段，但 Agent 能否把 port ID 映射到 `ethN` 尚需确认。实验必须冻结节点白名单和探测预算，并用只读代理仅开放 `read`/`counters`，防止 Agent 改故障/转发表。Agent 与规则只看完全相同的这些结果、公开 INT 与探测响应；外部账本不得泄漏。 |
| **强规则风险** | LossSight 的 alternate marking 可检测缺报，其算法 2 已用 per-flow INT source/sink 计数差诊断黑洞；重实现均不构成创新。NIKA 当前只给 Agent per-port 聚合计数，故只可比较同信息的适配规则，不能声称复现 LossSight 原始诊断器。已完成条件式 MCM 手工重放：post-sink 丢报告令所有节点标记一起跳号；若把 Algorithm 1 中疑似错误的 `||` 按预期解释为 `&&`，倒序扫描会将其标到终端遥测节点，而不是独立的 sink→server 报告链路。论文印出的 `||` 对两种合法增量都为真，故不能把该推导当作论文实现的确定运行行为。`silent_loss_baseline()` 使用隐藏目标端口/映射，是 verifier 而非公平 Agent baseline。详见 [LossSight MCM 源码级重放](experiments/communication_telemetry/LOSSSIGHT_MCM_SOURCE_REPLAY_2026_11_07.md)。 |
| **否证条件** | 实际 P4 丢包不改变 exporter/collector 可见轨迹；Agent 可见信号没有稳定区分力；上述同信息强规则达到相同诊断性能且成本不高于 Agent；或 LossSight、FaulT-Bench、TelemetrySuffBench 已覆盖相同因果对照和行动指标。任一即 NO-GO 当前假设。 |
| **最低成本与当前裁决** | 已完成四轮 pinned NIKA 隔离运行；第四轮首次完成固定流 profile 的 report-only/leaf-loss 配对。端口计数 R0 在该低背景条件下区分两臂（目标 service port egress 376 vs 0），故该场景不支持 Agent 超越强规则的主张，也不准入 Agent/API 实验。仍只有一个小型拓扑与一次成对 workload，无独立簇、未知背景、跨拓扑或 Agent 证据。下一步先审查并冻结有现实依据的背景混淆压力设计；若公平强规则仍能解出任务，则关闭当前候选但保留 AI × 通信遥测主方向。**候选 HOLD，未证明论文贡献。**

**端点协议与逐包账本（已完成单拓扑双臂核验）：**

逐包真值仅在 evaluator 端收集：service UDP socket 和全接口 AF_PACKET 记录业务包，relay ledger 记录收到/转发/丢弃的 INT 报告，collector JSONL 记录公开报告。第四轮 report-only 臂每流 94 个 service IPv4 ID 与被丢弃的同 leaf sink-report ID 逐项相等；leaf-loss 臂同一 flow profile 的 service 收件和 AF_PACKET 均为零。两臂 collector 每流都保留 188 条上游行且无 sink 行，然而公开 P4 target-port egress delta 已分别为 376 与 0。详见[第四轮结果](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.md)。

### 本轮补充的直接近邻

- **NetOpsBench** is a direct benchmark neighbor. At pinned public commit `d121e55b51f317b9f6bc684be0745184457740b8`, its canonical campaign contains data-plane `packet_loss` cases, injected through `tc netem loss`; its Agent observability tools expose device logs, interface metrics, BGP events, and Pingmesh summaries/hotspots. Its evaluator scores fault/healthy verdict, fault type, device/interface location, and efficiency. This rules out a new general network-agent diagnosis or packet-loss benchmark claim. The pinned built-in campaign has no explicit INT sink-exporter/collector-report-loss case, although the project supports custom faults; absence from its built-in campaign is not proof of a scientific gap. The narrower technical difference is that NIKA's INT sink observation is emitted as a per-packet UDP report, allowing a controlled intervention after service-bound forwarding but before collector receipt. Whether that yields any Agent-vs-rule result beyond existing network diagnosis remains untested and may be incremental. [Pinned fault campaign](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/scenario/specs/fault_campaign.yaml) · [Pinned impairment implementation](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/faults/handlers/impairment.py) · [Pinned observability tools](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/toolkit/mcp/observability.py) · [Pinned scorer](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/evaluator/scorer.py)
- **NIKA** is already a benchmark for LLM network-incident diagnosis and troubleshooting, with P4 and other network scenarios; this project therefore cannot claim a new general network-agent benchmark. NIKA is the execution substrate and existing task contract. The proposed study is narrower: a controlled terminal-cause pair in which the same missing sink row can arise either before report generation (service-bound packet loss) or after it (sink UDP report loss). This exact paired protocol is not established by the benchmark description, but absence from the description is not proof of novelty. [Paper](https://arxiv.org/abs/2512.16381) · [NIKA release/data record](https://zenodo.org/records/17971675)
- **CTBench** evaluates telecom troubleshooting with expert-grounded evidence, diagnosis and restoration, and reports resource use; evidence-grounded diagnosis and cost-aware evaluation are therefore not standalone contributions here. Its public abstract does not establish the specific NIKA P4 terminal packet-versus-report loss pair proposed above. [Paper](https://arxiv.org/abs/2608.12002)
- **FaulT-Bench** studies unreliable tickets, false fault reports, wrong device attribution, and root-cause claims. It is a direct neighbor for noisy premises and network-agent diagnosis, so the project must not frame “diagnosis under unreliable evidence” broadly as new. The residual candidate is limited to the causal source of a missing packet-level INT sink observation and matched-information rule comparison; exact task-level overlap still requires full-method review. [Paper](https://arxiv.org/abs/2608.27021)
- **TelemetrySuffBench** directly constructs exact-equal model-visible telemetry pairs with different hidden failure origins, separates detection from origin localization, and measures abstention under insufficient evidence across five models and a frozen holdout. This closes any generic claim that “same telemetry can hide different causes” or that abstention under ambiguous telemetry is itself new. Its inspected method uses generated agent-execution traces and telemetry views; it does not describe a live packet network with sink-export/collector loss or post-view evidence acquisition. The only possible distinction left here is therefore the network-specific causal intervention plus interactive evidence acquisition—and that distinction still must beat same-information probes/rules on independent network tasks. [Paper and full text](https://arxiv.org/abs/2608.07899)
- **INT packet-loss monitoring and INTCollector** already address missing telemetry reports, loss localization, and collector behavior. Thus neither detecting missing reports nor building a collector is novel here. The only retained question is whether an Agent can correctly attribute the two terminal causes under a controlled, independently audited observation and budget contract, beyond same-information deterministic rules. [Packet-loss monitoring paper](https://tanlizhuang.cn/papers/2021-%E8%AE%BA%E6%96%87-TNSM.pdf) · [INTCollector](https://dl.ifip.org/db/conf/cnsm/cnsm2018/1570470751.pdf)
- **LB-LossSight / LossSight²** analyzes INT loss localization under packet-level load balancing and reports ambiguous loss locations. It adds per-flow, per-output-port marking counters and evaluates Mininet/P4-BMv2 on a 4-ary Fat-Tree, averaging 100 runs of 1,500 INT packets each. This rules out generic “load balancing makes INT loss hard to localize” and marking-based INT localization as new claims. The article's reported experiment studies path packet loss; the inspected full text does not describe the paired terminal causes here. [Paper DOI](https://doi.org/10.1002/itl2.393)
- **INTCollector** explicitly notes that UDP between switch and collector can lose important telemetry information, while its contribution is a high-performance collector. Thus report-channel loss itself is prior work context, not a contribution. The remaining candidate is only a controlled agent-versus-rule attribution study under matched permissions, observations, and probe budget. [Paper PDF](https://dl.ifip.org/db/conf/cnsm/cnsm2018/1570470751.pdf)
- **GPINT** already buffers INT probes in the data plane, uses next-hop feedback and timeouts to recover or reroute after probe/link failure, and evaluates packet loss, degraded links, collection latency, and recovery overhead. It covers in-network probe recovery; it does not establish the proposed paired test of final service-delivery loss against post-sink UDP-report loss. This scope gap is not novelty evidence. The candidate remains vulnerable to a simple rule using NIKA's visible aggregate port counters. [Paper](https://arxiv.org/abs/2212.14876)
- **Classical network fault localization already fuses active and passive evidence.** The KDD'14 data-center system combines large-scale active ping failures with passive device/link alerts and was evaluated on production incidents. Earlier sequential-testing work uses passive end-to-end outcomes to choose cost-effective active tests; Bayesian network monitoring selects probes by expected information utility and adapts the observation window. Therefore active/passive fusion, budget-aware probing, and information-value-based test selection are established baselines, not this project's algorithmic contribution. [KDD'14 paper](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/kdd14failureloc.pdf) · [Sequential testing](https://nlab.engr.uconn.edu/papers/bwang09-fault-detection.pdf) · [Bayesian probing](https://doi.org/10.1109/TNET.2022.3200249)

**Counter-rule ceiling (source-derived; not runtime evidence):** NIKA exposes per-port aggregate ingress/egress packet counters, and its loss table is keyed only by egress port. At the pinned 10000-bp setting, the P4 hash output is in `[0,65534]`, threshold is `65535`, and every packet on that port is dropped. Thus adding same-port background traffic does not create the previously projected “target lost/background passed” counter alias; the source-consistent algebraic projection separates port-wide loss from report-only loss in all 30 load-stratum formula cases. The prior v1 projection is invalid and has been superseded in `NIKA_SHARED_PORT_RULE_PROJECTION_2026_11_09.json`. A same-information deterministic rule remains a required negative control. Unrelated concurrent faults could affect aggregate counters, but that is a different task contract and is not evidence for the current single-fault pair. Do not hide counters from the Agent. Any future claim must preserve raw tool outputs and evaluator packet ledger and compare rule/Agent on identical observations and budgets.

**Contribution gate (revised):** The candidate is not a new active/passive fusion or probe-selection algorithm. Retaining it as a paper requires a reproducible result on independent fault clusters showing that network Agents exhibit a stable error, calibration, or cost–diagnosis tradeoff not revealed by a counter rule, a KDD'14-style active/passive fusion baseline, and sequential/Bayesian probe-selection baselines. A single paired scenario or code release does not meet this gate. The current evidence does not yet establish that distinction (**HOLD**).

**Paper positioning boundary (2026-11-07):** Position the work, if it survives the gates, as a narrow controlled study within AI-assisted communication-network telemetry diagnosis. Do not claim a new general network-agent benchmark, general evidence-grounded diagnosis, missing-telemetry detection, collector design, or large-scale-network result. The current `topo_size=s` preflight only checks runtime feasibility; “large-scale” remains the long-term domain motivation and requires larger independent topologies and workloads before it can appear as an empirical result.

**可用真实轨迹及分母边界：**NIKA Zenodo 发布记录说明数据含 906 条轨迹、3 种模型、54 类 issue，以及诊断/提交日志、ground truth 和 submission。2026-11-08 直接读取记录 API 得到 `metadata.license=null`，归档内没有许可文件；旧记录中“CC BY 4.0”的说法已撤回，GitHub 软件 MIT 许可不自动适用于轨迹数据。明确许可前不把该数据用于新的可再分发分析。论文主评测方法描述 150 个 incident × 3 个模型 × 2 次运行 = 900 次，因此 906 与 900 的差异仍须按 incident/run 血缘核对。不得把轨迹数直接当作独立任务数。论文列有 P4 testbed，但公开发布没有证据表明包含当前拟议的末端数据包丢失与 sink UDP report 丢失配对。此前结构审计只支持描述性数据结构事实，不是当前候选的验证集。[Zenodo 数据记录](https://zenodo.org/records/17971675) · [NIKA 论文](https://arxiv.org/abs/2512.16381)

**公开轨迹 P4 子集复核（2026-11-07）：**对 Zenodo ZIP 逐项核验 SHA-256/Zenodo MD5 并直接读取档案索引后，发现 906 个 `ground_truth.json` 中 904 个有 `session_meta.json`；两条缺元数据记录已列入机器结果。可归入 `p4_*` 场景的轨迹为36条：`p4_bloom_filter` 与 `p4_mpls`，六个故障类型，各含3个模型×2次运行。它们没有当前拟议的末端丢包/报告丢失配对；P4 诊断日志记录的工具名里没有显式 `int`/`telemetry` 工具调用。此结果只界定外部轨迹的覆盖范围，不能解释完整的 906/900 差异，也不能作为新配对实验的替代。复算记录见[报告](experiments/communication_telemetry/NIKA_PUBLIC_P4_TRACE_CENSUS_2026_11_07.md)、[脚本](experiments/communication_telemetry/nika_public_p4_trace_census.py)和[JSON](experiments/communication_telemetry/NIKA_PUBLIC_P4_TRACE_CENSUS_2026_11_07.json)。

**P4 历史轨迹的计数器行为（探索性字段审计）：**35/36 条日志至少调用一次 BMv2 计数器工具（共95次）；28条有提交文件，另8条缺失且全部来自 `gpt-oss:20b`。对可用文件作排序列表后的字段字面比较，根因名完全匹配为12/28。该结果既说明计数器是历史 Agent 已使用的证据，也因归档旧字段与 pinned scorer 的 `root_causes` schema 不同而不能作官方准确率。它强化了同信息计数器规则作为首要基线的必要性；不能证明当前终端故障配对上的规则效果。

**隔离运行环境的先验依据：**NIKA 上游 GitHub Actions [运行 #42040702647](https://github.com/sands-lab/nika/actions/runs/42040702647) 在 Ubuntu 24.04 hosted runner 上通过 `p4_dc_gateway` 与 `p4_dc_fabric` 的启动检查。它只证明上游 P4 场景可在该 runner 启动，不验证本项目的 relay、末端成因配对、可见工具信号或 Agent 行为。鉴于本机 WSL/Hypervisor 风险，项目预检采用固定 NIKA commit 的 Linux hosted runner，并配置为研究分支上仅在预检 workflow 或脚本变更时触发 `push`；`workflow_dispatch` 保留作默认分支登记后的手动入口。当前远端尚无该 workflow，未有本项目 runtime 运行结果。

These sources narrow novelty further; neither establishes that the proposed paired experiment is uncovered. NIKA's current Agent API does not expose LB-LossSight's per-output marking state, so that method is a literature comparator, not an equal-information baseline unless a separate instrumented arm exposes the same feature to both the rule and Agent. 论文完整方法和实验已审阅，代码与底层轨迹未复现；具体差异尚未证明。当前候选保持 **HOLD**。

## 本轮审查裁决

研究方向保持固定。LossSight 的论文已把服务器未收到预期 INT report 视为丢失事件，因此本候选不研究“是否检测到缺报”。终端两成因的 report-only 等价仅适用于最后 leaf→service egress 丢包与同 leaf sink report 丢失；官方 dev-066 的 gateway→spine 故障会移除后续 hop 行，不是等价样本。条件式手工重放显示：若按预期将 LossSight Algorithm 1 的 `||` 解释为 `&&`，post-sink 丢报告会被定位到终端遥测节点；论文打印的 `||` 是伪代码歧义，不能当作可靠运行证据。下一步先在 gate 下冻结 terminal-hop 的工具、账本和强规则，再核实 NIKA runtime 可否在 leaf egress 注入并保证两条件只差一份 sink UDP report；若做不到，关闭该候选。候选状态 HOLD。

## 当前决定性检查：报告通道删失是否可独立观测

以下是**实验设计预期，不是测得结果**。对相同流/包 ID，实验账本应分别记录 P4 发送、source/sink 计数、hop exporter 生成并发送的 UDP 报告、collector 收到并落盘的报告。预期信号如下：

| 事件 | source 看到包 | sink 看到包 | exporter 发出报告 | collector 收到报告 |
|---|---:|---:|---:|---:|
| 无故障 | 是 | 是 | 是 | 是 |
| sink 前转发丢包 | 是 | 否 | 对应下游报告否 | 否 |
| 报告发送后、collector 前丢失 | 是 | 是 | 是 | 否 |

固定 NIKA 源码提交 `ac4422d8a4a03be2b905e28edf72993d467e1b81` 中，`hop_exporter.py` 向 collector `UDP/32766` 发送 JSON；`collector.py` 支持单独配置监听端口。确定性 UDP relay 原型已通过 localhost 回环核验：原精确键试验定向丢弃目标三元组；后续 flow-scope 试验在 packet ID 变化时，只丢弃预注册 flow/switch 下的报告，其他 flow/switch 报告抵达本地 UDP collector，结果见 [flow-scope smoke](experiments/communication_telemetry/artifacts/relay_flow_scope_smoke_retry1/result.json)。这些核验只证明合成 localhost 的匹配和转发逻辑；实际 NIKA collector、网络命名空间、权限、数据面影响等仍未知。NIKA lab 当前固定启动配置，集成时需记录 overlay，将 collector 移至 32767 并让 relay 接管 32766。relay 日志保存真实报告键与哈希而不保存正文；仍需在 NIKA 隔离环境做端到端对照。

### 主动探测的接口边界

---

# 历史候选门槛归档：DAComp-DA rubric/metadata 与路径 ceiling

自2026-11-07起，本页所列 DAComp 候选不再是当前研究主线。当前固定方向与首个实验准入门槛见[通信网络遥测研究章程](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md)。以下记录保留当时的证据、否证条件和 HOLD/NO-GO 决策，不代表当前优先级。

---

# DAComp 路径子项上限超过父级 ceiling 的历史一页设计

日期：2026-11-07

当前裁决：**允许扩充现有盲审；尚不准入模型/API 实验；论文贡献仍 HOLD。** 本轮手工核对固定公开 rubric 后确认了三个路径—父级上限冲突候选，但未发现这三题的 Judge 评分行，也没有观察到分数饱和或模型比较变化。新发现不是评分错误或贡献结论。

## 可证伪问题

> 当 DAComp-DA 的最佳匹配路径子项和超过明确声明的 criterion/standard ceiling 时，固定 Judge 协议是否会按路径子项总和给分，而固定 normalizer 的 metadata 分母与 100 分裁剪是否因此隐藏超额并改变至少一个预注册的模型比较？

**可能的独立增量（待证）：**检验开放式数据分析 rubric 的“最佳路径求和—父级上限—任务级 metadata 分母”三层契约冲突，是否产生可复核的分数饱和或系统排序变化。一般 scorer-rule 敏感性、rubric 质量审计和不同 Judge 重评分均已有近邻；若结果只是静态文本不一致、无法影响实际评分，或与通用重评分敏感性等价，本候选即 NO-GO。

| 门槛 | 证据与状态 |
|---|---|
| **固定来源事实** | 固定 DAComp commit `027ccaf20f0d3743d9291fd575d9bc785a5fe3db`。任务052标题与 metadata 均为30；criterion maxima 合计30，但按每项各选一条 rubric 标示的最佳路径，上限为7、6、6、6、6、6、6，合计43；Criterion 2.1 声明 Max 4，而路径2.1.A/B/C各自子项上限为1+4+1=6。任务063 Criterion 1.1 Max 4，路径1.1.B子项为1+3+1=5。任务084 Standard 3.1 Max 3，路径3.1.B明示4。三例为逐项原文核验，不以启发式全量 parser 计数代替人工复核。 |
| **评分协议与实现** | 固定英文 Judge prompt 写明 Requirement 分数为 criteria 之和、criterion 分数可为最佳路径分数、最佳路径分数为其子项之和；它未明确说明超过 criterion/standard ceiling 时如何再截断。固定 scorer 用 `metadata.Total` 作分母并将 rubric percentage 裁剪至0–100。对052，若 raw 总分按路径上限达到43，确定性归一化为43/30=143.3%后会裁为100；这是条件算术，未观察到实际 raw=43。来源见[固定 Judge prompt](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/prompts.py#L86-L105)与[固定 scorer](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py#L570-L579)。这表明边界未被代码显式验证，不证明 Judge 实际超额给分。 |
| **可达性证据** | 任务006有一条公开 GPT-5 Judge 评分行，raw=10、metadata Total=16；报告/轨迹还显示1.6与1.7分别获得2分并计入 raw。它没有超过总分，不能证明饱和。任务063有报告和轨迹但无评分行；052、084当前无公开评分行。2026-11-07 核查官方 main、两个开放 PR 和7个公开 fork 的 main：未找到052/063/084评分行或多模型逐题矩阵；六个 fork 与固定官方提交相同，三个旧分叉的已检查差异也未增加这些结果资产。此检索不覆盖所有分支、私有材料或外部归档。 |
| **主要实验** | 第一阶段由两名审阅者在不看 metadata/评分前，判断 rubric 是否给出唯一的父级/路径上限；锁定后再揭示 metadata；第三阶段对照论文方法与固定 Judge/scorer。只有规范判定至少部分明确且取得可用的原始 Judge 输出后，才对同一冻结输出配对计算“固定实现”与“遵守声明父级上限”的分数，并检验是否出现100分饱和、分差/排序变化。现阶段无配对结果。 |
| **强基线与近邻** | 固定原生输出与 scorer；同一 Judge 输出、仅改变预先定义的 ceiling 规则；至少一个不含 ceiling 冲突的 rubric 负对照。比较必须使用同一任务、同一输出和同一 GSB 分量。*Same Outputs, Different Scores* 在8个多模态选择题基准、5个模型上研究相同输出受 scorer 规则影响，已占住一般重评分敏感性；RubricEval 与 RuVerBench 分别评估 rubric-level 判断质量、长程 Agent rubric 验证；PReMISE 审计 rubric 的结构充分性、可靠性、偏好拟合和对抗鲁棒性。上述近邻没有在本轮可见摘要中直接研究 DAComp 这种“路径子项和超过父级 ceiling + metadata 分母裁剪”的已发布契约，但没有检索到不等于证明未被覆盖。本项目只能声称该层级契约交互的实证后果，不能声称首次审计 scorer、rubric 可靠性或排名敏感性。 |
| **否证条件** | 两位审阅者认为父级 cap 明确优先且官方 prompt 可一致执行；原始 Judge 从未给出超父级分数；配对重算不改变任何预设分数/模型决策；结果仅是一般评分规则扰动，或不超过 Judge 重复评分波动。任何一项均关闭独立贡献主张。 |
| **准入与成本** | 已将052、063、084加到原有未发送的 11 候选+10 对照表，现为14候选+10固定对照。对照仅检查流程，不估总体比例。尚未发送审阅包、没有新的人工结果；不调用付费 API，不运行模型。若拿不到可用原始 Judge 输出或作者/独立审阅无法裁定，不做 DAComp 任务重跑来制造结论。 |

**当前决定：**只继续完成原有盲审材料的源核对与交接准备；不准入模型实跑。只有独立裁决和原始评分都能支持可区分的可证伪预测，才另行通过下一次 go/no-go。项目整体保持 **HOLD**。

**定向近邻核查（2026-11-07）**：检索词为 “scorer rule sensitivity / rubric-level judging / hierarchical rubric ceiling / score normalization”，并核读以下全文的任务、方法与结果相关部分：

| 工作 | 已覆盖范围 | 对本候选的边界 |
|---|---|---|
| [Same Outputs, Different Scores](https://arxiv.org/abs/2611.03377) | 固定模型回答、重放8个多模态选择题 benchmark scorer，比较解析/回退规则。 | 已占住一般 scorer 规则导致分数变化；其目标是答案抽取与 parse fallback，不是 rubric 子项—父级 ceiling 的层级聚合。 |
| [RubricEval](https://arxiv.org/abs/2603.25133) | 用人工标签评估 instruction–response–rubric 的二元满足判断。 | 研究 Judge 的 rubric-level 判断准确度，不是数值分母或 subtotal ceiling。 |
| [RuVerBench](https://arxiv.org/abs/2606.29920) | 在 Deep Research 与 Agentic Coding 轨迹上评估单条 rubric 的二元核验。 | 研究 rubric satisfaction 与 Judge 策略，不是多层分数聚合。 |
| [PReMISE](https://arxiv.org/abs/2605.30803) | 评估 policy rubrics 的结构充分性、可靠性、偏好拟合与对抗稳健性。 | 覆盖 rubric 作为测量规范的广泛质量问题；本次核读部分未发现 DAComp 式路径子项超过父级上限并与 metadata normalizer 联动的实验。 |
| [Judging LLM-as-a-Judge](https://arxiv.org/abs/2609.02942) | 测试只看 rubric 文本能否预测 Judge 标签，以及 rubric/回答反转时的反事实一致性。 | 研究 rubric 信号与 Judge 稳定性，不是分数 ceiling/归一化后果。 |

因此，当前差异**仅是一个窄的待检验候选**，不是已证明的原创性；检索范围是定向而非系统综述，“未在已读方法中发现”不等于证明文献中不存在。即使独立裁决确认契约歧义，仍须同输出配对重算并证明它造成实际分数饱和或改变预注册比较，才可继续主张。

来源：[Same Outputs, Different Scores](https://arxiv.org/abs/2611.03377) · [RubricEval](https://arxiv.org/abs/2603.25133) · [PReMISE](https://arxiv.org/abs/2605.30803) · [RuVerBench](https://arxiv.org/abs/2606.29920) · [Judging LLM-as-a-Judge](https://arxiv.org/abs/2609.02942)

---

# 已关闭候选一页设计：精确数据库状态血缘会否改变 Agent 模型比较

日期：2026-11-06

当前裁决：**此候选对独立论文贡献 NO-GO；项目整体仍 HOLD。** 固定公开资产的设计矩阵复算显示，在应用族×任务类型基线之外，重复状态指示只增加1个自由度，且全部来自 Salesforce。尚无逐题模型结果；这不是“状态效应为零”的证据，而是现有公开任务结构不足以支持跨应用的独立状态效应主张。尚未运行 DAComp Agent 任务。

## 可证伪问题

> 对 DAComp-DE 中需要外推到新数据环境的配对模型比较，精确共享起始数据库状态是否能在强任务条件化不确定性基线之外解释剩余结果依赖，并改变一个预先指定的模型比较决策？

**可能的独立增量（待证）：**不是通用任务聚类或更宽的区间，而是可审计的初始数据库 SHA-256 血缘能否提供额外预测/解释力，并改变目标明确的系统比较结论。单基准最多支持 DAComp-DE 范围内的经验结论；更广泛的 benchmark-method 主张还需第二个独立任务族。

| 门槛 | 证据与状态 |
|---|---|
| **结构事实** | 固定 DAComp-DE revision 中80个 impl/evol 任务对应41个精确初始数据库状态、29个应用族。12个应用族有多个状态：9个族包含重复Evol状态及一个不同的Impl单例状态；Salesforce有两个各含2个Evol和1个Impl的重复状态；Qualtrics与Workday各有两个不同的单例状态。其余17个族的任务共用一个初始状态。另有17个单状态族的重复状态同时覆盖Evol与Impl；这里的“跨类型状态对比”专指同一应用内存在两个均重复且跨类型的状态，只有Salesforce满足。结构本身不证明结果相关。 |
| **可识别性审计** | 对80行交叉表构造58个非空“应用族×任务类型”单元指示列，基线矩阵秩为58；加入全部41个状态簇指示列后秩为59，增量自由度为1，唯一贡献来自Salesforce。13个单例状态各自落在只有一题的应用族×类型单元，因而与该基线完全共线。可复算结果见[设计矩阵审计](DAComp_STATE_IDENTIFIABILITY_2026_11_06.json)与[脚本](da_comp_state_identifiability.py)。这只度量固定效应设计秩，不估计状态方差或结果依赖；不同任务ID的内容差异仍可能与状态差异混杂。 |
| **最强近邻** | DAComp 已报告 item/case/model 层评分器一致性；Agent Evaluation Reliability 使用 task/model/scaffold 方差分解；Huang 的 Agent 排名分析处理 estimand、配对与分组不确定性。不能把一般聚类 bootstrap、ICC、排名可靠性或更宽区间称为贡献。 |
| **关键数据** | 固定任务、模型、Agent/harness、预算下的逐任务原生分数，模型/运行元数据，完整 state-hash 血缘；配对模型结果和可用的重复运行。当前未找到公开 DE 结果矩阵。 |
| **样本灵敏度** | 仅作假设性均值差筛查：80任务/41簇时，在状态内 ICC 0–1 的情景下，近似80%功效可检出的标准化配对模型差约为0.32–0.48 SD；不代表真实功效，也不适用于主假设的残差依赖/决策变化检验。该设计目前只能按pilot处理。 |
| **比较基线** | 原生等任务权重点估计；task-IID配对bootstrap；应用族×任务类型条件化基线；在此之上才检验精确状态簇；留一应用/状态敏感性。点估计目标须固定，不将等任务与等状态权重混为一谈。 |
| **关闭条件与裁决** | 现有数据仅支持一个应用内的独立状态对比，且无同一任务提示跨多个初态的重复设计。故关闭“跨应用、跨任务泛化的独立状态血缘贡献”这一论文候选（NO-GO），不启动原定80题Agent结果实跑。若未来取得同一任务在多个可审计状态下的交叉运行矩阵，再以新一页门槛重审；不能将本次秩计算解释成状态效应不存在。 |
| **实跑准入** | 固定树 `027ccaf…` 的 DE 配置选择在宿主机通过 subprocess 执行的 `CLIRuntime`，不得原样运行。Docker 29.9.2及声明的Python/Node基础镜像已通过一次无网络隔离冒烟；这不等于验证了官方 `DockerRuntime` 的额外卷、单任务挂载或行为等价。任务级执行前仍须确认隔离与网络策略。 |
| **模型配置** | 本地Ollama 0.40.15的Qwen3 8B已通过schema工具调用冒烟，返回的函数名/参数正确且未执行；模型摘要、输出与GPU显存占用记录在[冒烟结果](QWEN3_TOOL_CALL_SMOKE_2026_11_06.json)，复现脚本为[ollama_tool_call_smoke.py](ollama_tool_call_smoke.py)。这不等于已验证DAComp固定版LiteLLM/OpenHands适配。 |

**历史裁决：该状态血缘候选 NO-GO；项目整体 HOLD。** 不把结构血缘、矩阵秩或工具调用冒烟写成论文贡献。无需为此候选继续做DAComp任务实跑。后续旧段落中列出的 DAComp、AppWorld 等候选均为历史审计记录，不再是当前研究队列。当前唯一主线是[通信网络遥测研究方向](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md)，当前唯一候选以本文件开头的通信遥测门槛为准；不得因通信候选被否证而切换到这些历史候选。当前没有调用付费模型API。

来源：[状态血缘完整门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md) · [固定 DAComp-DE runner](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/methods/de-agent/evaluation/benchmarks/dacomp/run_infer_de.py) · [runtime registry](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/methods/de-agent/openhands/runtime/__init__.py) · [CLIRuntime](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/methods/de-agent/openhands/runtime/impl/cli/cli_runtime.py) · [DockerRuntime](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/methods/de-agent/openhands/runtime/impl/docker/docker_runtime.py) · [DAComp paper](https://arxiv.org/abs/2512.04324) · [Agent Evaluation Reliability](https://arxiv.org/abs/2610.00651) · [Agent leaderboard comparison](https://arxiv.org/abs/2609.07785)

---

# 新候选一页门槛：WorkBench 的数据库状态 × 任务模板是否改变模型比较

日期：2026-11-06

当前裁决：**NO-GO：WorkBench Revisited 不含跨任务变化的初始环境状态。** 官方代码对每个任务从相同的一组本地 CSV 加载同一个 pristine state，再于任务结束后复制重置。虽然有 690×24 逐题结果，但一个固定起始环境不能识别“新数据库环境”方差，也不能验证 DAComp 的状态血缘假设。证据见下方离线审计。该结果不否定 DAComp 的 41 状态结构候选，只说明 WorkBench 不能作为其独立跨环境复制。

## 可证伪问题

> 在固定 WorkBench Revisited 任务和 24 个已发布模型结果上，将精确初始数据库状态作为一个单独的抽样/泛化因素纳入模型比较后，是否会在任务模板/任务条件化基线之外解释剩余结果依赖，并改变预先指定的模型比较结论？

**待验证的可能增量：**真实 workplace-agent 基准中，任务模板与数据库状态是交叉还是嵌套的；若交叉，区分任务语义复用与环境状态复用能否让对新数据库泛化的模型比较得出不同结论。通用多层模型、聚类 bootstrap 或“区间更宽”本身不算贡献。若数据库与模板完全嵌套，或其作用被既有 task/scaffold generalizability 方法吸收，则不成立。

| 门槛 | 证据与状态 |
|---|---|
| **公开数据可行性** | 官方 WorkBench README 声明已发布 690 个任务、24 个 2026 模型的逐题结果，以及带 `task_id`、`base_template`、domain 和逐题 verdict 的 item-level CSV；原始仓库标为 MIT。需固定 Git SHA、核验文件哈希和数据许可，不依赖需登录同意条款的 Measurement Data Bank 镜像。 |
| **结构事实** | 论文/README 声明任务由模板在五个 sandbox 数据库上生成。还未验证 690 题中每个任务对应哪个数据库、模板是否跨数据库重复、五个初始数据库文件是否确为不同且固定的状态。须从任务/数据库输入追溯关系与原始字节 SHA-256 建立交叉表；不能用 domain 标签替代状态身份。 |
| **可能的增量** | 仅当数据库状态是独立于 prompt/template 的可识别因素，且加入该因素后有可重复的残差依赖或模型比较决策变化，才保留。结果只适用于此 WorkBench 发布物，除非另一个基准独立复制。 |
| **强基线** | 原始 690 题等权模型分；task-IID 配对不确定性；任务模板簇不确定性；既有 Agent Evaluation Reliability 的 task/model/scaffold 方差分解；再加预注册的数据库状态 facet。保持 2026 run_group、当前评分器、每任务二元 correctness 与 unwanted-side-effect 终点分开。不得将 2024/2026 或不同评分版本直接混成一个模型矩阵。 |
| **决策指标** | 预先指定同一 run_group 内的模型对，比较模型差值区间、排序概率和达到实质差异阈值的结论；以数据库状态留一法/模板留一法作敏感性。若只有五个数据库簇，簇级推断可能很弱，必须明确有限样本限制；不得靠 episode 行数伪装大量独立环境。 |
| **否证条件** | 模板与数据库状态完全嵌套；状态映射不可靠；加入状态 facet 后残差相关/模型比较均无实质变化；结果仅由更换权重定义造成；或最强任务条件化/G-theory 基线已经给出相同结论。满足任一条件即关闭，不换名称续做。 |
| **最低成本** | 只取公开 MIT 仓库中的任务元数据、五个数据库源文件和已发布 item-level 结果 CSV；复算原始聚合后进行离线交叉设计审计与配对不确定性比较。不运行 Agent、不调用 API、不下载完整 Hugging Face 仓库。 |

**准入裁决：**源数据已核验，结果见下文。因每个任务使用同一初始环境，这个 candidate 对环境血缘主张为 NO-GO；不再计算其状态聚类区间。

来源：[WorkBench Revisited 官方仓库](https://github.com/olly-styles/WorkBench) · [WorkBench Revisited 论文](https://arxiv.org/abs/2606.13715) · [Agent Evaluation Reliability](https://arxiv.org/abs/2610.00651) · [WorkBench 原始论文](https://arxiv.org/abs/2405.00823)

## 离线源数据审计结果 — 2026-11-06

在 WorkBench Revisited 固定 Git commit `49c7dfd00c03d384ec59ea57374f50b766aa5613` 上，只读检查了公开代码、任务输入和 item-level 结果；原始仓库标 MIT。六个作为 `ToolState` 初态的 CSV（五个 `data/processed/*.csv` 加 `data/raw/email_addresses.csv`）均按路径以固定字节哈希核验；`state.py` 的 `_pristine_state()` 在进程内只加载这一份快照，`reset()` 复制同一快照，`inference.py` 在每题后调用 reset。因而每个 task 从同一完整环境状态起跑，不是五个 task 间变化的 state cluster。

固定 `data/results/item_level_results.csv.gz` SHA-256 为 `6035fb112bbb4fb48cd56d643898cac43c42d2d11bc6d2bb0e595d8d31ea2216`。其中 `revisited_2026` 有16,560行=690题×24模型，每题恰有24个模型结果；69个 `base_template` 各对应10个题目实例，且每个模板只出现在一个任务 domain。任务模板可以支持模板层不确定性分析，但它不能创造数据库状态变化。

**结论：**数据库状态×模板效应在此发布物上没有环境间变异，属于不可识别，不是“未发现显著差异”。关闭此跨基准状态血缘候选（NO-GO）；不再为它重算聚类区间。继续找已有任务级结果时，应先确认不同任务是否真的从不同、可审计的初始状态起跑。

来源：[固定 WorkBench commit](https://github.com/olly-styles/WorkBench/tree/49c7dfd00c03d384ec59ea57374f50b766aa5613) · [state.py](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/src/tools/state.py) · [inference.py](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/src/evals/inference.py) · [WorkBench Revisited item-level outcomes](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/data/results/item_level_results.csv.gz)

---

# 新候选一页门槛：能力—安全关联是否由失败分母耦合驱动

日期：2026-11-06

当前裁决：**允许对固定 WorkBench Revisited 发布物作离线分析；独立性和实质性尚未证明。** 不新增模型/API实验。

## 可证伪问题

> WorkBench Revisited 报告的模型完成率越高、逐题有害副作用率越低，这种关联在将有害率按失败任务条件化后是否仍成立？条件化后模型排序或对“能力与安全同步提升”的解释是否改变？

**原始契约与机制：**固定 evaluator 中 `is_correct()` 比较预测动作最终状态与 gold 动作最终状态；`has_side_effects()` 返回 `state_changed and not correct`。因此 `H=Pr(unwanted_side_effect)` 必为失败集合的子集。定义完成率 `C=Pr(correct)`、失败中的副作用比例 `Q=Pr(unwanted_side_effect | not correct)`，必有 `H=(1-C)Q`。原始逐题 H 率同时反映“少失败”和“失败更少造成副作用”，不能单独识别后者。

**可能增量（待证）：**对固定同一批公开 Agent 运行，检验已发表的能力—安全关联是否在失败条件化后仍保持，区分能力提升造成的失败减少与错误构成中副作用占比变化。这是一个对 WorkBench Revisited 实际结论的可证伪测量解释；若只是常规条件比例、没有决策含义或已被论文完整报告，不构成独立贡献。

| 门槛 | 证据、强基线与否证 |
|---|---|
| **数据** | 固定 commit `49c7dfd…` 的 `revisited_2026` 16,560 条任务×模型记录、690个任务、24个模型；每任务24个结果。只分析此同一 run_group，排除原始2024与 `other`。保留 `correct` 与 `unwanted_side_effects` 原字段。 |
| **主要量** | 每模型 `C`、原生逐题 `H`、失败条件副作用比例 `Q=H/(1-C)`；预先检查有限样本与分母。报告所有模型的并列估计及任务模板簇配对 bootstrap 区间。 |
| **比较** | 对照原论文报告的 `C` 与无条件 `H` 关系；比较模型层 rank association（例如 Spearman/Kendall）在 `(C,H)` 与 `(C,Q)` 下的方向/大小及模型顺序变化。Bootstrap 以69个 `base_template` 为任务簇、对所有模型同簇配对重采样；结论只代表这24个具名系统，不能外推模型总体。 |
| **最近邻** | WorkBench Revisited 已直接宣称完成率和 harmful-side-effect rate 同步改善，并公开逐题记录；因此仅复述该相关为 NO-GO。需读完该文方法/错误分析，并比较是否已报告 `Q` 或同等的失败条件化分解；若已报告，不成立。 |
| **否证/停止** | `Q` 与 `H` 给出相同方向、模型顺序稳定且区间变化不实质；分析仅是标签定义恒等式；作者论文已呈现相同条件分解；或结果对失败类型、任务模板权重极敏感，则关闭，不扩成新指标框架。 |
| **成本与伦理** | 仅离线复算公开 MIT 数据及固定 evaluator 源码；不重放模型、不访问账户、不调用API、不触发副作用工具。报告中将副作用作为 scorer operationalization，不冒充独立的人类伤害裁定。 |

**离线分析结果与裁决（2026-11-06）：**固定 `revisited_2026` 结果的 `rho(C,H)=-0.941`，失败条件化后 `rho(C,Q)=+0.350`；按 69 个 `base_template` 成对 bootstrap 的相关差 `rho(C,Q)-rho(C,H)=+1.291`，95%区间`[+0.774,+1.520]`，而 `rho(C,Q)` 自身区间`[-0.187,+0.605]`。论文 Figure 1 已对部分模型展示“正确/失败但无害/有害副作用”的结果组成，故 Q 是已发布三类结果的确定性重表达，**不作独立贡献**。

另在 16,560 条记录中发现 10 条 `correct=True`、`unwanted_side_effects=False`、gold action 为空，但执行轨迹包含创建并删除新 ID `00000300` 的记录；涉及 8 个任务与 4 个模型。该事件可说明终态恢复与轨迹授权不同，但记录为本地模拟工作区动作，不能推断真实外部伤害。完整结果还含 `exact_match=False` 诊断；SABench 已直接使用 trace-based authorization oracle，并报告 goal-satisfied 下的 collateral damage。对事后选取的 Gemini 3.1 Pro / Gemini 3.5 Flash 近邻进行配对模板 bootstrap 后，重分类前后的 harm-rate 差异区间均跨零。故**条件化比例候选 NO-GO；补偿写入只作为窄的 WorkBench 再分析线索，当前不支持稳健模型选择变化，且独立性仍受近邻限制**。不做第二基准扩展或模型调用。详见[WorkBench 结果审计](WORKBENCH_OUTCOME_AUDIT_2026_11_06.md)和[复算脚本](workbench_outcome_audit.py)。

来源：[WorkBench Revisited 论文](https://arxiv.org/abs/2606.13715) · [固定 WorkBench evaluator](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/src/evals/evaluation.py) · [固定逐题数据](https://github.com/olly-styles/WorkBench/blob/49c7dfd00c03d384ec59ea57374f50b766aa5613/data/results/item_level_results.csv.gz)

---

# 新候选一页门槛：DAComp-DA rubric 最高分与归一化分母是否冲突

日期：2026-11-06
当前裁决：**HOLD；固定发布物的 100 题离线筛查已发现并人工回看 11 个分值来源冲突候选，但 parser 对标题与 Requirement 层级的覆盖分别为 95/100、89/100；未确认哪个字段具有规范权威，也未证明真实分数或模型排序受影响。** 详见[固定资产审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)。没有调用模型/Judge API。

## 可证伪问题

> DAComp-DA 的 rubric 明示总分、各 criterion/path 上限与 evaluator metadata 的 `Total` 是否在任务层一致？若不一致，使用 metadata 分母的原生 scorer 是否会系统性改变分数或模型排序？

| 门槛 | 当前依据、最强对照与否证条件 |
|---|---|
| **原始契约** | `dacomp-006` rubric 标题20、唯一 Requirement 上限16、七个 criterion 上限合计20；metadata 三维上限4+7+5=16，恰与前五个 criterion 的类别权重相符，而 rubric 的1.6/1.7另加4分。其它候选包括 `dacomp-019` 14/22、`dacomp-046` 25/18。权威值未裁定。 |
| **原生计分路径** | 官方 Judge 输出 `dacomp-006` raw rubric=10，正分记录了1.1.A、1.2.B、1.6.A、1.7.A；1.3–1.5 为0分且未保留所选路径。固定 scorer 以 `metadata.Total=16` 归一化，重现45.5。论文 §2.2 则规定选择每个 sub-requirement 的最佳匹配路径、只应用该路径 items，并按 `Σs_k/Σw_k` 归一化。由于零分项路径未记录，公开输出不能重建完整 `Σw_k`；16/19/20对应的总分45.5/约39.58/38.0仅是条件敏感性值，不是正确修正。论文公式与固定实现分母表达存在差异，但是否构成实现错误仍待独立裁定。 |
| **可达性与实证范围** | 固定树 `027ccaf20f0d3743d9291fd575d9bc785a5fe3db` 的100题 rubric/metadata 已离线筛查；标题解析95/100、Requirement最大值合计解析89/100。11个初筛冲突逐项回看原文。补查发现英文GPT-5一行与中文Qwen3-Coder-Plus两行，共3条原始评分、两个底层任务ID；中英006不是受控配对，仍无全任务多模型矩阵或可作排序分析的数据。 |
| **预测的 scorer 差异** | metadata 高于合法 rubric 上限时可能压低任务分；metadata 低于 Judge 得分时 scorer 会封顶，可能损失区分度。11个候选的分母替换代数上界为1.54–27.27总分点；这不是观测效应。实际影响要由权威计分契约和逐题多模型 Judge 结果确认；不可从最大分差直接推断排行榜变化。 |
| **现有主结果的可判定影响** | 在只考虑已知11项且候选 rubric ceiling 为真时，任意模型对的100题均值差变化≤1.318分。DA-Agent前三名最小相邻差7.19分，故其顺序在这些条件下不变；但全表 Gemini-2.5-Pro 34.70 与 DeepSeek-V3.1 34.33 仅差0.37分，OpenHands 子表 DeepSeek-V3.1 33.87 与 Gemini-2.5-Pro 33.38 差0.49分，因此两组相邻次序变化均不能被上界排除（这不是变化已发生的证据）。当前只有3条逐题评分行，实际排名影响未知。已知11项上界仍不足解释 Issue #11 的10.24/11.30分差；该判断不覆盖未解析任务。 |
| **强基线 / 近邻** | 对照不是任意替换规则，而是人工核定“实际计入 Judge 分子的评分项”与“原生归一化分母”是否来自同一契约，再对冻结输出作配对重算。*When Benchmarks are Targets* 已展示评测细节扰动可改变榜单名次；Judge-Aware Ranking 已对异质 Judge 建模并估计分数/排名不确定性；*Same Outputs, Different Scores*、PReMISE、RuVerBench及 evaluator/契约审计覆盖更广的规则敏感性、rubric可靠性和来源溯踪。因此这些通用现象或方法均不是增量。本候选只剩经独立裁定的跨文件 ceiling 解释是否改变固定输出的模型比较，仍无独立性结论。 |
| **否证 / 关闭条件** | 若独立复审确认 metadata 是唯一规范来源、rubric文本不定义分值；若标准化后不一致消失；或配对分数/预注册模型比较不变，则关闭。固定发布物当前有3条原始评分行、覆盖2个底层任务ID；只有英文 GPT-5 `dacomp-006` 直接显示本候选的分子项目与metadata类别上限不匹配，不支持跨模型结论。 |
| **最低成本** | 完成11个候选任务的盲化人工分值契约判定，补齐未解析 rubric 的人工确认；随后取得合法逐题多模型原始 Judge 结果，以metadata、rubric声明值、结构上限三口径配对重算。当前没有该矩阵，故不启动模型调用或用聚合排名推算任务分数。 |

**当前决定：**固定资产只读筛查与已评分样本算术核对已完成；此候选仍非论文贡献。下一门槛是两位审阅者在原有 rubric-only 与 metadata 阶段锁定后，对论文公式、路径权重可重建性和固定 scorer 分母作独立来源对照；之后才判断是否值得获取配对逐题结果。不据此调用 API 或启动新模型实验。

## 2026-11-06 跨基准筛选与直接近邻裁决

定向检查 FDABench 与 KramaBench 两个结构不同的数据分析 Agent 基准后，暂未发现 DAComp 式“Judge 读取 rubric、归一化器另取任务总分 metadata”的同构路径。FDABench 当前公开 evaluator 按四个固定维度各 0.25 等权并比较生成报告与 ground truth；KramaBench 以 `answer_type` 选择 metrics、用逐题 ground truth/subtask 结果评分，再聚合到 workload。二者是边界/阴性对照，不是第二个阳性样本。本轮固定代码版本为 FDABench `72e50a2b59798848a06ad30c5d8a39248c1228bf`、KramaBench `b2e0d77540263f8b6119f977fe79a8c4386b5a02`；任何跨基准实证仍须另行固定各自数据 revision。

后续查新发现两个更直接的近邻：*Do Agent Benchmarks Do What They Say?* 沿工具广告契约、实现与 evaluator 追踪 score provenance；*Measurement Risk in Supervised Financial NLP* 系统研究 rubric/metric/aggregation 敏感性和排序稳定性。它们分别否决了本项目把“通用契约溯源审计”或“评分可识别性框架”作为独立方法贡献的做法。前者当前公开范围主要是工具实现与状态转移，后者主动改变 rubric/metric；是否有公开分值来源之间无法裁定的规范权威冲突，仍是一个可能不同但未验证的经验边界。

因此本项目不再把“评分契约可识别性”写成创新方法。只保留一个 DAComp-DA 经验候选：**rubric 明示上限与 scorer 使用的 metadata `Total` 是否存在经独立裁定仍无法消解的冲突；对同一冻结逐题输出，所有获裁定认可的分值解释是否会改变一项预注册系统比较，并超出 Judge 重复评分波动。** 这是假设，不是结果；一般分数重算、错配计数、最大分差或另造审计术语均不构成贡献。

**预注册 estimand 草案：[待审]** 对同一批任务使用相同的任务解释集合和冻结 Judge 输出，计算预设系统对 `a,b` 在每个获认可解释 `c` 下的配对差 `D_ab(c)=Σ_i w_i[S(z_ia,c_i)-S(z_ib,c_i)]`，报告其在审阅许可的全局自洽解释集合上的最小/最大值。只有该集合中出现与原生比较相反的方向，且任务簇不确定区间与固定输出上的 Judge 重复评分噪声不能解释该翻转，才记为“决策改变”；否则报告未识别/稳健不变。不能给各系统单独挑评分口径。该估计目标只是研究设计，不构成方法创新；主系统对、权重、实质阈值和重复次数仍待独立预注册。

否证条件：metadata 被独立审阅确认为唯一权威；未解析条目补核后冲突消失；替代解释不获审阅者认可；分数变化不改预注册比较；变化未超过 Judge 重复评分不确定性；或近邻已覆盖同种规范冲突及决策后果。任一成立即关闭该候选。详细比较见[跨基准筛选记录](SCORE_CONTRACT_IDENTIFIABILITY_SCREEN_2026_11_06.md)。未运行模型/Judge API、未请求外部实验、未声称独立贡献；科学状态仍 **HOLD**。

来源：[dacomp-006 rubric](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/src/dacomp-006/rubric.txt) · [metadata](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/src/dacomp-006/metadata.json) · [GPT-5 score CSV](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/model_scores/gpt-5-2025-08-07-test1__rubrics-gemini-2-5-flash__textgsb-gemini-2-5-flash__visgsb-gemini-2-5-flash.csv) · [scorer](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py) · [DAComp paper](https://arxiv.org/abs/2512.04324)

---

# 新线索一页门槛：DAComp-DA 端到端分数复现差异

日期：2026-11-06
当前裁决：**HOLD；线索来自公开 issue 的自报重跑，尚无原始逐任务结果，不能称为已复现差异或论文贡献。** 本门槛只允许后续做来源与实验设计审查，不代表批准 API/模型调用。

## 可证伪问题

> 在固定 DAComp-DA 100 个任务、公开版 DA-Agent、模型端点与评测配置后，端到端重跑的得分能否复现论文 Table 5；若不能，Agent 生成波动、固定输出上的 Judge 波动、运行/评测配置差异各解释多少，是否改变预先指定的模型比较？

## 一页准入审查

| 门槛 | 当前依据、最强对照与否证条件 |
|---|---|
| **原始线索** | **[外部报告，未独立验证]** DAComp Issue #11 报告者称以 `gpt-5-2025-08-07`、Gemini-2.5-Flash Judge 跑完整 100 题两次，DA-Agent 得分 61.08 与 62.14；论文 Table 5 为 50.84 ± 3.12。issue 页面没有附逐任务结果、完整配置或原始产物，且仍是开放问题。数值只能作为待复核线索。 |
| **论文与公开代码已做的工作** | 论文 Table 10 明确对固定 Agent 输出做 8 次 Judge 评分，DA GPT-5 报告 56.1 ± 0.16；这是固定输出的 Judge 波动，不是端到端 Agent 重跑差异。Table 8 另报告跨 Judge 排名。Table 5 给 DA-Agent 各维度及总分都报告 `±`，但已检查的论文正文与附录未说明其抽样单位、重复次数或计算口径。固定公开代码快照 `027ccaf20f0d3743d9291fd575d9bc785a5fe3db` 的 Agent 默认 `temperature=0`、`top_p=1`、`max_tokens=16384`、`max_steps=120`、`max_memory_length=31`；Judge 配置对 Gemini-2.5-Flash 设 `temperature=0`、`max_tokens=16384`。这些是当前发布默认值，不证明与历史 Table 5 运行完全一致。 |
| **可能独立的增量** | 不是“LLM 分数会波动”或“重跑结果不同”。仅当严格对齐公开协议后仍存在可复核的实质分差，并且分解能定位到发布协议遗漏/组件交互，且改变一个预注册的模型结论时，才有候选增量。单次复现、补 README 或一般方差分解都不够。 |
| **强近邻** | DAComp 自身报告固定输出 8 次 Judge 稳定性、跨 Judge 排名与超参数稳定性；Lau (arXiv:2603.04417) 在真实企业 QA 上比较 5 个 Judge、温度与重复评分；Blackwell et al. (arXiv:2410.03492) 研究重复实验对基准分数及预测区间的影响；*Re-executing Coding-Agent Evaluations* (arXiv:2610.14460) 重放 1,929 个编码 Agent 评测单元并检验历史决策。一般重复运行、Judge 波动或“决策未变”均不得包装为新颖性；可能剩余的边界只在同一数据集/流水线内分离 Agent 生成变化与 Judge 评分变化，并检验是否改变预设跨模型结论。 |
| **最低辨别实验** | 先由维护者/可审计原始记录确认 Table 5 的模型版本、Agent commit、提示、参数、Judge 设置、运行次数与 `±` 定义；确认不了就只能称“公开 release 可复现性”，不可称严格复现。若条件可固定，配对记录每任务 Agent 输出、原生 Judge 细分分、token/错误；对冻结输出重复评分以分离 Judge 方差；至少加入一个同协议比较模型，才能检验模型排序/差距是否改变。重复次数、功效和实际差异阈值须在运行前依据可核验方差与目标比较预注册。已公开的 `dacomp-006` 单任务 CSV可做评分聚合复算，不能替代 100 题原始产物。 |
| **否证 / 关闭** | 若差异由不匹配模型快照、任务过滤、公式/聚合、Judge 配置或公开代码与论文设置不一致解释；若可复现差异不改变预注册比较；若只能得到单一 GPT-5 汇总或自报而无任务级记录；或结果与通用重跑不确定性方法没有额外信息，则该候选 **NO-GO**，只留工程复现记录。 |
| **成本与准入** | 原始 issue 报告称做过两轮 100 题运行，但没有可供离线重算的逐题输出。本机尚无经核验的原作者 GPT-5 轨迹；复现需真实模型/Judge 调用或取得既有原始产物。成本、模型权限与双盲审阅方案未定，当前不运行。 |

**当前决定：HOLD。** 已完成一轮只读条件核验：issue 仍开放，只有报告者的重跑数值和一条非作者对当前公开默认值的核对；没有作者确认、逐任务输出或历史 Table 5 运行参数。严格历史复现目前不可识别。若后续无法取得历史运行档案，本候选只能测试“当前公开 release 可复现性”，不能称为复现 Table 5。启动任何真实 Agent/Judge 运行前仍需独立预算与准入；且必须证明候选差异超过已有重复评分研究并影响跨模型结论。 |

## 2026-11-06 追加的来源核验

- **[事实]** DAComp 论文 §3.6/Table 10 明确写出固定 Agent 回答上进行了 8 次独立 grading runs，并给出 mean ± std；该定义只适用于 Table 10。论文 Table 5 中 DA-Agent 的六个维度和 DA 总分也有 `±`，但当前检索到的主文、实验设置和附录没有把 Table 5 的 `±` 绑定到任务、Agent 重跑或重复 Judge 中的任何一种。
- **[事实]** 固定官方源码快照 `027ccaf20f0d3743d9291fd575d9bc785a5fe3db` 的 `rubric_scoring.py` 对各维度计算 `mean()` 与 `count()`；`get_score.py` 写出的 overall CSV 字段也只有各维度均值和 `count`，没有标准差或重复运行聚合。它解释不了论文 Table 5 的 `±` 是如何生成的，也不证明作者内部没有另行汇总脚本。
- **[事实]** Issue #11 的外部报告给出完整 100 题重跑均分 61.08 和 62.14，并报告多个维度均显著高于 Table 5 中心值；但没有逐任务输出、提交配置或作者确认，因此仍不能确认是否同任务集、同评分流水线与同聚合单位。
- **[推断]** 目前识别到的是公开结果的**方差定义与复现协议不可追溯**，还不是评测器错误，也不是已验证的分数不复现。该观察单独不足以构成独立论文贡献；若无原始产物，最多能形成一篇范围很窄的公开版本可复现性案例。
- **下一步准入**：只读检查可继续到“可公开证据是否足以还原 Table 5 的输入、逐题评分和聚合”。若答案是否，先关掉严格复现主张；不要用当前 release 的新 API 运行伪装历史复现。只有在预算另行批准且有可审计配对输入后，才考虑一项预注册的公开 release 重跑。

## 2026-11-07 固定发布物中的原始结果资产范围

- **[事实]** 对固定官方树 `027ccaf20f0d3743d9291fd575d9bc785a5fe3db` 清点 `agent_results/`：GPT-5/DA-Agent 有两个公开样例（`dacomp-006`、`dacomp-063`），中文 Qwen3-Coder-Plus 有两个（`dacomp-zh-005`、`dacomp-zh-006`）；四个均有报告和轨迹。评分 CSV 仍只有三条记录：GPT-5 `dacomp-006` 一条、中文 Qwen 两条；`dacomp-063` 没有评分行。故公开发布确有少量端到端样例，但没有覆盖完整 Table 5 比较的逐任务、多运行矩阵。
- **[离线复算]** 该行记录 `rubrics_total_score=10/16=62.5%`，GSB 三维分别为 readability `0.4`、professionalism `0.0`、visualization `0.2`。固定评分代码的权重为 0.60/0.10/0.10/0.20，复算 `0.6×62.5 + 0.1×40 + 0.1×0 + 0.2×20 = 45.5`，与官方 CSV 的 `weighted_total_score=45.5` 一致。该核验验证的是一个已发布样本的聚合算术，不是独立复审 Judge 的语义判断，也不是 100-task 汇总复现。
- **[范围修正]** 先前“官方 DAComp-DA 没有逐题评分结果”的概括需要限定为“缺少覆盖完整 Table 5 比较的逐任务、多运行结果矩阵”。现有证据覆盖四个示例输出、三条评分行和两个底层任务ID；未找到 Issue #11 两轮 100 题重跑的逐题结果，且官方仓库没有可证明其 Table 5 方差来源的结果档案。
- **[研究含义]** 四条样例轨迹可用于有限的端到端核验，但仅一条英文样例含公开评分，另两条中文评分属于不同语言和 Agent 配置；它们不能判断 Issue #11 分差来源、估计任务/运行方差或检验受控榜单决策。两阶段盲审仍未返回。仅有原始样例或算术复核不是论文贡献，状态仍 **HOLD**。

来源：[DAComp Issue #11](https://github.com/ByteDance-Seed/DAComp/issues/11) · [DAComp 论文](https://arxiv.org/abs/2512.04324) · [固定版 Agent 参数](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/methods/da-agent/run.py) · [固定版 Judge 配置](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/config.py) · [固定版维度汇总代码](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py) · [固定版总分输出代码](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/get_score.py) · [LLM Judge 评分一致性研究](https://arxiv.org/abs/2603.04417) · [Towards Reproducible LLM Evaluation](https://arxiv.org/abs/2410.03492) · [Re-executing Coding-Agent Evaluations](https://arxiv.org/abs/2610.14460)

---

# 备选候选一页设计：DCR 组别成员迁移与跨系统比较

日期：2026-11-06

当前裁决：**HOLD；无独立贡献证据，未准入模型/API 实跑。** 本候选进入实证前必须满足下表；长版来源、定义和可复现条件见 [DCR 研究门槛](DCR_CAUSAL_VALIDITY_GATE_2026_11_06.md)。

## 可证伪问题

> 对同一批配对数据分析任务，基线与状态管理 Agent 的 DCR 差异中，有多少来自父节点正确性/可评分性的运行后组别迁移，有多少来自相同任务轮次上的下游错误变化？分解后是否会改变一个预先指定的系统比较？

**可挂事实的动机：**StateGuard 将 DCR 定义为 contaminated 与 clean 单元的下游错误率差；其定义仅纳入可评分父节点，任一组为空时 DCR 未定义。已有近邻已系统处理 Agent 比较的 estimand、common support、目标标准化、任务簇不确定性与排名。剩余可能差异仅是 DCR 组别变量由各系统运行后的父状态与缺失情况决定，不能把一般支持集重加权包装为创新。

| 准入项 | 最小要求与当前状态 |
|---|---|
| **独立增量** | 待验证：在固定 `task × turn × dependency-map` 配对后，系统间 clean/contaminated/unscorable 成员迁移是否使原生 DCR 差值或方向改变，并且超过 Huang 式共同支持标准化及 task-cluster 不确定性基线。**未知，非结果。** |
| **可观察数据** | 每臂需有模型/Agent、任务、逐轮父子正确性、缺失原因、预算与原生评分；按任务簇配对。当前只找到 StateGuard 汇总表与无逐任务结果的第三方实现仓库；无作者认可的原始轨迹。 |
| **最强基线** | 原生 DCR；共同支持 + 直接标准化；任务簇区间/G-theory；`clean/contaminated/unscorable` 配对迁移分解；缺失不得当作错或对。父节点纠正重放仅作机制外部效标。 |
| **否证** | 迁移分解等价于常规分层/标准化、DCR 结论不变、缺少共同支持或差异依赖事后筛选，即 NO-GO。 |
| **独立复现** | 至少两个许可明确且结构独立的数据分析任务族；模型、Agent 权限、预算、评分与依赖映射冻结；不把轮次/重试当独立任务。未满足。 |
| **运行可行性** | 当前本机有 RTX 5070 Ti，但没有本地推理栈或模型缓存；作者逐任务结果未发现；完整第三方 runbook 需配置模型 API，且该仓库没有许可证声明。无 API/模型实跑授权。 |

**当前结论：HOLD。** 公开结果不足以判断假设是否成立。下一步先寻找可合法复算的配对逐任务轨迹并复核候选实现来源；若只能取得聚合表，关闭该候选，转查现有仓库中可离线重算的其他候选，不新增数据变体。

---

# 前一候选研究设计：恢复效应的基线条件化偏差

日期：2026-11-06

当前裁决：**关闭为独立论文主张（NO-GO）；这不是对 LongDS 结果有效性的结论。** 本页其余内容保留为历史候选设计与统计敏感性说明。当前新的条件性候选见[数据库状态血缘与评测不确定性门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)；此前的追溯更正审查仍见[追溯更正后的分析发布状态](RETROSPECTIVE_CORRECTION_PROPAGATION_GATE_2026_11_06.md)。

## 候选问题与可证伪假设

> 长程 Agent 的“恢复/重置帮助了弱状态、伤害了强状态”这类结论，是否会因按同一对照运行的准确率分层、再用该对照表现选择干预时点而产生？改用干预前状态质量分层和预先随机化时点后，恢复策略效果及策略排序是否仍成立？

候选主假设 **H1**：在固定任务、模型、预算和原生评分下，用干预前可观测的状态质量定义分层，并随机确定重置/故障时点后，恢复策略的条件效应或策略排序会与按无干预运行的后续准确率分层、并据其选择时点所得结论出现可测差异。方向和大小均未知，尚未检验。

潜在独立增量不是“重置有时有帮助”，也不是一般性回执/状态验证，而是检验**恢复效应的估计是否受基线结果条件化与干预时点选择影响，并且这种影响是否会改变策略选择**。这首先是测量效度候选，不是新的恢复算法；若结论不改变任何任务或策略判断，或只是已知回归均值的直观重述，则关闭为独立论文主张。

## 一页设计核对

| 门槛 | 当前依据与缺口 |
|---|---|
| **1. 原始任务与结论** | LongDS v1.1 Lite 有 24 个完整任务、777 轮。论文 §5.3 / App. C.7 已比较相同重置后轮次的 persistent baseline 与 reset 表现；排除 5 个持续基线过弱的任务，再用 persistent accuracy 的一半附近选择候选重置轮次（2、4、6、15），并按这些后续轮次的 persistent accuracy 分 Low/Medium/High。原任务/评分需冻结，复现时保留所有排除和缺失。24 任务不是已论证的样本量。 |
| **2. 候选偏差与估计量** | 若用同一 noisy control outcome `P` 同时定义层 `P` 与报告差值 `R−P`，分层差值可能出现数学耦合/回归均值；若再根据 `P` 选干预时点，估计对象又受结果驱动选择。偏差是否足以改变量级或策略排序，必须通过配对重复运行和预注册的替代分析估计；目前没有原始 per-task 两臂结果证明偏差已经发生。主要指标：预先定义分层下的配对任务完成率差、逐轮原生准确率差、策略排序变化；同时报告全部任务覆盖、缺失率和成本。 |
| **3. 干预与可达性** | LongDS 官方实现快照 `a814927159470ad1624602d233f57b7c0be5882e` 证明每个任务多轮共享 `AllocatedCodeEnv`，可执行环境重置；客户端也可在成功执行后拦截返回值，但当前候选不要求加“丢回执”故障。对照：原论文式基线条件化分析；干预前、独立测量的状态质量分层；随机化重置时点；持续状态、重置、状态重建三策略。需确认复用公开 runner/judge 的许可和所有轮次纳入规则。 |
| **4. 近邻与差异边界** | LongDS §5.3/App. C.7 已覆盖重置—持续状态、后续轮次比较和基线准确率分层；AFT-Bench 已覆盖控制接口、提交后响应丢失、状态与恢复。这两个组成部分均不能作为贡献。候选只剩下检验 LongDS 式**基于对照结果分层/选时点的恢复效应是否稳健，以及是否改变策略选择**。还需逐项查相关方法论文是否已完整讨论基线条件化偏差；不可把通用回归均值重命名为新机制。 |
| **5. 否证与关闭条件** | 若独立状态测量、随机时点与原分析得出相同效应和策略选择；若差异只由评估器/缺失任务口径造成；若只在仿真而非真实 Agent 轨迹出现；若 LongDS 复现实验不能合法、经济地完成；或该偏差已被恢复评测方法文献明确解决，则此候选不具独立贡献，关闭而不是另造指标。 |
| **6. 最低成本与决定** | 已完成解析性诊断，假设分数等方差、联合正态、零真实处理效应：`E[R−P\|P=p]=(ρ−1)(p−μ)`。在 ±0.5 SD 分层、ρ=0.5/0.8/0.95 时，模型产生 ±0.571/±0.228/±0.057 SD 的相反条件差；仅是统计机制演示，不是 LongDS 数据。确认性验证仍需冻结任务、独立运行两臂/多策略、预注册样本量并记录完整逐轮结果；预算未定前不运行。 |

## 近邻逐项界定

| 工作 | 已覆盖的内容 | 本候选未被证明覆盖的差异 |
|---|---|---|
| AFT-Bench, arXiv:2608.23628v2 | 控制接口、故障时点、提交后回执丢失、持久 SQLite、效果语义、幂等及后置验证；与“安全恢复”主张高度重叠。 | 不再把丢回执或状态核对当成本候选贡献。 |
| LongDS-Bench, arXiv:2605.30434v3 | 真实多轮数据分析、状态继承/更新/回滚/组合；§5.3/App. C.7 已比较 reset 与 persistent，按 persistent accuracy 分层，并用 persistent accuracy 启发式选时点。 | 可能差异仅为检验这种对照结果条件化/时点选择对恢复效应和策略排序的敏感性；这仍未构成贡献，且可能只是通用统计问题。 |
| DataSpace, arXiv:2608.03451v1 | 异构分析工作区和完整表格结果的确定性语义评分。 | 公开任务以单任务工作区产出表格为主；当前尚无证据其测试持久多轮状态下的故障恢复。 |
| DataClawBench, arXiv:2605.02503v3 | 真实噪声数据、多步探索分析、人工里程碑和过程失败归因。 | 公开摘要未报告工具已提交但回执丢失的受控干预。 |
| Terminal-Bench continuous validation, arXiv:2611.08417v1 | 持续审计/修复、任务与验证器变化对结果/名次的影响、时间预算效应。 | 候选研究的是既定数据分析任务内运行时故障及状态依赖交互；但其持续评测方法与基准修订主张不得再包装为新贡献。 |
| Closed-Loop Agent Evaluation, arXiv:2611.07051v1 | 分层测量、版本化规则、证据追溯、Conduct/Provenance/Adjudication。 | 候选若只增加分层记录或证据链则无新颖性；必须有受控故障交互结果。 |

## 当前决定与下一道门

**文献筛选结论（历史）：**先前的“回执丢失 × 分析依赖深度”表述过宽：AFT-Bench 与 LongDS 已分别覆盖丢回执恢复和持续/重置状态效应。LongDS §5.3/App. C.7 的公开方法描述可提出偏差疑问；解析诊断说明统计机制可能出现，但没有逐任务实验数据证明它影响了 LongDS 结论。

**当前裁决（2026-11-06 更新）：**此候选不再作为主论文路线。LongDS 已直接呈现 persistent/reset 对照、基线分层与按基线选时点；基线结果条件化及回归均值本身是成熟统计议题，恢复机制近邻也已直接研究同状态反事实恢复和决策价值。当前没有逐任务原始数据来证明本候选改变实际策略选择，因此关闭为独立贡献；统计诊断可留作风险提示或未来敏感性分析。追溯更正候选同样仍处于 HOLD，且必须通过新 gate 的来源独立性和实跑准入检查。

## 检索记录

**[事实]** 2026-11-06 通过 arXiv Atom API 定向筛选；本轮读取 LongDS v3 §5.3 和 Appendix C.7 的公开 HTML、检查 pinned DataMind GitHub tree `a814927159470ad1624602d233f57b7c0be5882e`，没有发现逐任务 reset 结果或运行日志文件；GitHub 代码树检查不能证明作者没有在其他位置发布结果。本轮解析诊断使用明确标注的正态假设，不是作者数据重分析。对 LongDS HF 数据快照只取 task list 与 24 份 task JSON；未下载 underlying datasets。该过程不是系统综述，任务 JSON 的依赖短语扫描也不是专家核验的依赖图。

- Wang, *Callability Is Not Operability: Controlled Interface Interventions for LLM Agents*, arXiv:2608.23628v2: https://arxiv.org/abs/2608.23628
- Xu et al., *LongDS-Bench: On the Failure of Long-Horizon Agentic Data Analysis*, arXiv:2605.30434v3: https://arxiv.org/abs/2605.30434
- Miratrix, Sekhon, and Yu, *Adjusting treatment effect estimates by post-stratification in randomized experiments*, JRSS B (2013): https://doi.org/10.1111/j.1467-9868.2012.01048.x
- Li et al., *DataSpace: Benchmarking Data Agents for Verifiable Analytics over Heterogeneous Workspaces*, arXiv:2608.03451v1: https://arxiv.org/abs/2608.03451
- Zhang et al., *DataClawBench: An Agent Benchmark for Exploratory Real-World Financial Data Analysis*, arXiv:2605.02503v3: https://arxiv.org/abs/2605.02503
- Buchanan et al., *Benchmarks as Software: Terminal-Bench and the Case for Continuous Benchmarks*, arXiv:2611.08417v1: https://arxiv.org/abs/2611.08417
- Ren and Ahn, *Closed-Loop Agent Evaluation: Layered Measurement and Self-Calibration*, arXiv:2611.07051v1: https://arxiv.org/abs/2611.07051
- LongDS 官方实现与 v1.1 Lite 使用说明: https://github.com/zjunlp/DataMind/tree/main/longds
- DataSpace 官方任务、评估器及数据说明: https://github.com/HKUSTDial/DataSpace
