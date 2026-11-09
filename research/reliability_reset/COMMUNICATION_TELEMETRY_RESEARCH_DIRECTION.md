# 通信网络流量与大数据研究方向｜持续学习主线

> **当前有效主线（2026-11-09 更新）：**真实通信网络流量上的少标签半监督持续学习；SNN 包内事件时间建模为主假设，匹配 ANN 与 DietCL、SpikeMatch、SOUL 等为强基线。NIKA/Agent 评分研究归档为工程负对照，不再是当前科学主问题。具体协议见[持续学习研究计划](COMMUNICATION_TELEMETRY_CONTINUAL_LEARNING_RESEARCH_PLAN_2026_11_09.md)和[近邻研究对照](COMMUNICATION_TELEMETRY_CONTINUAL_LEARNING_NEIGHBOR_AUDIT_2026_11_09.md)。

下文早期版本记录保留为研究历史；其中 NIKA Agent、RCA 和相关 “唯一候选”措辞已被本更新取代。

**方向冻结日期：2026-11-07**
**状态：长期方向固定；首轮双臂机制运行已完成，但干净小拓扑被同信息计数规则解决，论文候选保持 HOLD。**

## 上一阶段：Agent 网络遥测研究（已归档）

研究 AI Agent 如何在**规模大、来源异构、持续到达的通信网络遥测**上完成可复核的故障分析与运维决策。持续沿这条主线深挖，不因单个候选被否证而转去通用评分器审计、通用 RL、通用 Agent 可靠性或其他无关 benchmark。候选可以收缩或关闭，研究领域保持稳定。

## 当时的唯一候选：网络故障与遥测故障造成的观测删失能否被 Agent 区分

> 当 packet 已产生所有上游 INT 行但缺少 leaf/sink 行时，网络 Agent 能否从相同的初始缺失遥测出发，在相同工具权限和预算内取得可区分证据，区分“包在最后 leaf→service egress 丢失、sink 报告未生成”与“包已转发、sink UDP report 随后丢失”，并在独立任务簇上比使用同一可见信息的强规则更准确地归因？

这是通信网络运维方向内的唯一当前候选，不是已成立的论文贡献。当前研究对象仅为**观测删失成因的识别**，首要结果是配对场景下的故障归因表现及其相对强规则的差异。探测选择、停止校准、恢复策略、RL 训练和跨模型扩展均不属于当前主张；只有核心配对实验先通过运行时和测量效度门槛，才另立版本化阶段评估它们。若两种故障无法形成可审计的同证据对照、强规则达到同等表现，或近邻已覆盖相同因果实验，即关闭当前假设但保持通信网络遥测研究方向不变。

## 方向内最新外部证据：时间窗和探测对象对齐

2026-11-07 对 NetOpsBench v0.2 的 319 条公开轨迹作了离线复算：只读初始可见的 `anomalies_detected` 字段即可得到 274/319 正确的零工具二元 verdict；公开 DeepSeek Agent 轨迹为 227/319。packet-loss 子集差距为 25/26 对 5/26。该基线只用 Agent 可见初始上下文的一个字段，未匹配全部观察/工具权限，因此不能称作强规则公平对照。26 个 packet-loss 案例中，20 个至少有一条 live ping 使用与 Pingmesh 异常相同的主机/IP 端点对（正向或反向），其中 18 个 Agent 仍判断错误；端点一致不能证明同一 ICMP hash、路径故障或时间窗口。上游已公开 5/26 结果并指出历史 Pingmesh 与 live ping 被混用，所以当前证据不能算独立新发现。[详细时间顺序、按尺度结果、局限及复现信息](experiments/communication_telemetry/NETOPSBENCH_TEMPORAL_EVIDENCE_AUDIT_2026_11_07.md)。

源码核对进一步表明：NetOpsBench 在故障 episode 观测后才启动 Agent 诊断，恢复在 incident close 发生；故障窗口后的 live ping 并非“恢复后”探测。下一次深挖只做同一通信遥测问题内的端点/时间对齐：绑定历史异常窗口、受影响路径/hash、探测源目的和故障端口，再检查同一可见计数/时间证据的确定性规则是否足以解释错误。不能从 clean ping 推断全网已恢复，不能把 Agent 的错误复述包装成评分器失效。此复算不授权模型/API 运行；唯一 NIKA packet/report-loss 配对候选仍为 **HOLD**。

**按返回结果细分（2026-11-07，历史结论）：**进一步解析 20 个端点匹配案例的 ATIF `ping_test` 回执，合计 57 条匹配结果（490 包发出、433 包收到；调用/结果数聚集于 20 个案例）。其中 13 个案例的所有匹配 ping 均无丢包，12 个最终 verdict 错误（11 次判健康、1 次弃答）；7 个案例至少一个匹配 ping 有丢包，6 个案例最终弃答、1 个正确判故障。进一步发现这 20 个案例的初始 `anomalies_detected=true`，同一零工具规则对 ground-truth 故障 **20/20** 正确，而 Agent **2/20**。该结果是对已知上游现象的描述性错误分解，不是新的机制证据。上游 ping 工具不暴露 ECMP 流标识，而拓扑配置的 Pingmesh 对 16 端口池轮换抽样，所以目前不能确认两种探测观察覆盖了相同路径或流。鉴于初始单字段规则已完全解释该子集，对这批轨迹的扩展归因已关闭；不再追逐 hash/路径细节。NIKA 因果配对候选保留为已归档负对照，不是当前研究主线。

逐次回执、端点、参数、trajectory step/timestamp 与发送/接收数另存于[匹配 ping 事件 CSV](experiments/communication_telemetry/NETOPSBENCH_V02_MATCHED_PING_EVENTS_2026_11_07.csv)，便于逐例复核。该导出并未补出 ICMP 流 ID、ECMP hash 或故障接口的缺失信息。

### 当前实验顺序与可识别性门槛

两臂必须从相同的初始 INT 缺失视图开始；工具操作之后获得的证据可不同，但权限、操作预算、截止时间和负载保持配对。若限制为两臂最终可见特征完全相同，标签不可识别，任何 Agent 优势主张都应直接判为不成立。

1. **运行时准入：**在 pinned NIKA 上验证 leaf→service 丢包确实丢目标包且无 sink exporter 报告；再接入 report relay 验证“目标业务包到达 service，但对应 sink report 未进入 collector”。两臂都必须保留 evaluator-only 的逐包账本：源端发送、service 接收、每跳 exporter 观测、relay 收/丢/转发、collector 收到的 IP identification 和 flow key。Agent 只能看到任务允许的 NIKA 查询与探测结果。
2. **强规则否证：**先只用 Agent 同样可读的 per-port ingress/egress counter、INT 行与固定预算探测，冻结确定性规则并在未参与规则调试的 workload/packet-ID 任务簇报告混淆矩阵、成本及失败类型。安静网络下计数器差可能直接暴露 leaf ingress drop；不得把这个可解场景当作 Agent 贡献。只有背景流量、测量时间窗和噪声被固定后仍有可复核的规则盲点，才进入模型实验。
3. **Agent 配对评估：**仅在前两道门通过后，对开发集与按 workload/seed 隔离的冻结测试集运行 Agent 和规则；模型版本、可用工具、最大查询次数/字节、时限及初始证据一律配对。主指标是任务簇层级的成因归因正确率差；同时报告误报、弃权、操作成本与网络影响，不把同一任务重试计为独立样本。
4. **规模主张边界：**小型 `topo_size=s` 只能证明该固定拓扑中的可达性与测量质量。对“大规模通信遥测”作实证主张之前，必须在不同规模/负载或独立拓扑任务簇复验；不得从单一 P4 小拓扑外推。

**提前停止：**若末端 P4 故障无法运行时注入、逐层账本无法分离数据包与报告状态、或冻结强规则在目标测试上达到 Agent 同等准确率且成本不高于 Agent，则关闭当前候选（NO-GO），继续留在通信网络遥测方向重新审查，不追加 API 调用或用 RL 掩盖零差异。

### 现有任务提供的源码级动机

固定 NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 的 0.2.0 release 包含 P4 `silent_egress_packet_loss`，官方 dev-066 目标是 `gateway_1:eth1`，故障参数含 200 basis points 与固定 seed。Topology builder 先将 client 接在 gateway eth0，再将第一个 spine 接在 gateway eth1；因此该故障位于转发路径早期，后续仍会经过 spine/leaf 并产生报告。dev-066 可作早期 hop 丢失对照，不能与“仅 sink UDP report 丢失”组成相同部分轨迹。当前候选需另设版本化任务，在最后 leaf→service egress 注入 P4 loss，再配对丢弃已生成的同 leaf sink report。**重要边界：**官方 `p4_gateway_port_target()` 只从 gateway/spine 及其 spine/leaf-facing 端口生成任务参数；0.2.0 的 dev/test 标准任务也使用 `gateway_1:eth1`。它不生成 leaf→service 端口故障。P4 topology 确实为 leaf 建立 service-facing 端口；通用 `gateway-config --kind loss` 按 intent 中的交换机名连接并写共享 P4 表，源码未见角色限制。因此手动指定 leaf/service 端口是一个待运行验证的自定义任务路径，不能称为官方任务已支持或已验证。下一道技术门槛必须在 pinned NIKA runtime 上证明 leaf/service 端口可写入损失规则、目标业务包确实受影响且外部账本能观测各层事件。若不成立，关闭这个配对假设并留在通信遥测方向内继续审查，不转成其他研究主题。

固定源码引用：[注入目标生成器](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/problems/support/benchmark_targets.py#L599-L624) · [leaf 与 service 端口构造](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/topology_model.py#L247-L254) · [通用 P4 loss 表写入](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py#L1042-L1091) · [共享 pipeline 的 loss 表](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L87-L95) 与 [ingress 调用点](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L230-L236) · [官方 test case](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/benchmark/releases/0.2.0/test.yaml#L818-L832) · [官方 dev case](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/benchmark/releases/0.2.0/dev.yaml#L862-L876)。

**Hosted preflight 的静态目标推导：**在 `p4_dc_gateway` 的 `topo_size=s` 中，`leaf_1` 先连接两个 spine，再连接 `service_1_1` 与 `service_1_2`；端口编号由 `eth_index + 1` 得到。因此 `leaf_1:eth2` / BMv2 port `3` 是首个候选 service-facing 注入点。运行时必须从生成的 intent/端口映射核对该值，并先证明无故障 direct-service TCP 探测和 VIP HTTP 健康路径，再安装损失表项、检查表项读回和目标 service 侧收包；该静态推导不能替代 runtime 结果。

**端点协议与逐包账本：**service IP 是 `10.0.x.x`，匹配 gateway 安装的 `10.0.0.0/8` INT watchlist。Gateway 对被观察包插入 7 字节 INT-MX 并把 IPv4 protocol 改为 253；固定 `gateway.p4` 的 `ROLE_LEAF` ingress 随后识别 INT-MX、恢复原始 IPv4 protocol、将 IP 总长度减 7 并移除该头，再继续转发。因此源码支持带 INT 的 TCP/UDP payload 在到达 service 前被解封装；此前“P4 没有 service-side 解封装”的判断已撤回。Pinned `p4_dc_gateway/lab.py` 将 service 网络接口配置为 `eth0`；NIKA 要求 Kathara `>=3.8.3,<4`，固定 Kathara 3.8.3 在非 privileged Docker 节点上将 `NET_RAW` 放入默认 `cap_add`。[NIKA 拓扑](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/lab.py) · [NIKA 依赖范围](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/pyproject.toml) · [Kathara 3.8.3 capability 列表](https://github.com/KatharaFramework/Kathara/blob/f7ae3fa/src/Kathara/model/Machine.py#L1-L40) · [Kathara Docker 启动配置](https://github.com/KatharaFramework/Kathara/blob/f7ae3fa/src/Kathara/manager/docker/DockerMachine.py#L363-L384)。NIKA pinned verifier 将直连 service 的 non-VIP TCP probe 定义为 observation packet，服务健康由 VIP HTTP 检查。首轮直连 HTTP 门槛已修正。第三轮 report-only packet-ID join 已由第四轮双臂实跑复核和扩展：固定四流 profile 下，报告丢失臂每流 94 个 datagram 到达 service，逐包对应的 94 条 leaf sink report 被 relay 丢弃；真实 leaf-loss 臂每流 service 收件为零。两臂 collector 都每流保留 188 条上游行而没有 sink 行。受控窗口 target egress delta 为 376 vs 0，显示低背景条件下同信息端口计数规则可辨别这一配对；该规则尚未在独立簇冻结和评估，这也不是 Agent 或跨任务结果。详情见[第四轮分析报告](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.md)、[原始结果](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.json)及双臂 relay ledger。

collector 对已收到的 hop report 写入 `hop_sequence`；它把 `sink_seen` 定义为是否观察到任一 sink hop，并令 `trace_complete = sink_seen and bool(hop_sequence)`。这不是按预期路径逐跳核验的完整性证明。诊断实验因此要分别记录：业务包是否到达、哪一跳 exporter 是否产生报告、UDP 报告是否到 collector、Agent 查询时看到哪些报告。缺少其中任一层真值，都不能把“trace 缺行”归因为网络故障或遥测管线故障。

### 现有 NIKA 契约的硬边界

固定 NIKA 提交 `ac4422d8a4a03be2b905e28edf72993d467e1b81` 的 `submit` 接口只接受一次最终提交；已有 `submission.json` 后，后续提交会被拒绝。公开轨迹也没有结构化的逐步根因判断。因此，原生 NIKA 不能直接测量“模型先错后改”、改正时机或改正率。不得把工具调用中的自由文本倒推成可靠的逐步诊断标签。

可在原任务契约内研究的过程量是**从故障注入完成到唯一最终提交的耗时**，而非“首次正确提交”或纠错时延。固定源码显示 `nika.jsonl` 记录 `failure_inject_complete` UTC 时间；`messages.jsonl` 记录 UTC `tool_start/tool_end`、工具名和输出；成功 `submit` 会返回明确回执并创建 `submission.json`。这给出了可交叉检查的源码级计时入口，但不能替代真实轨迹验证：还需确认 Agent adapter 一致性、系统时钟校正误差、提交 tool_end 与 canonical 文件写入的关联及工具输出是否截断。配套指标是终态 RCA 准确率、探测/查询次数与字节、模型调用及网络服务影响。它们是候选测量量，不因可测就自动构成新颖贡献。若要研究中间判断及修正，必须另建版本化协议，预注册 checkpoint 语义，并与原生分数并列保留。

### 近邻边界

- **NIKA** 已提供在线网络故障环境、遥测和 CLI 工具、多步诊断及网络性能影响度量；因此“网络运维 Agent benchmark”“多步网络工具诊断”及“同时记录调用成本和 SLO”不是增量。[论文](https://arxiv.org/abs/2512.16381) · [固定仓库快照 `ac4422d`](https://github.com/sands-lab/nika/tree/ac4422d8a4a03be2b905e28edf72993d467e1b81)
- **NIKA 公开轨迹的研究适用性与再利用许可必须分开。** Zenodo 页面说明发布包含 906 条轨迹、3 个模型、54 类 issue，并提供诊断日志、提交日志、ground truth 与 submission；但 2026-11-08 直接读取记录 API 得到 `metadata.license=null`，ZIP 内也没有 LICENSE/README。GitHub 仓库 MIT 许可不自动覆盖数据；此前将轨迹数据称为 CC BY 4.0 的记载已撤回。故在获得明确许可前，不将该轨迹集纳入新的可再分发数据分析。论文实验方法描述 150 个 incident × 3 个模型 × 2 次运行 = 900 次主评测，数据页 906 与 900 的差异仍须按 incident/run 血缘核对，不能把 906 条轨迹当作独立任务数。P4 子集的结构性审计记录见[报告](experiments/communication_telemetry/NIKA_PUBLIC_P4_TRACE_CENSUS_2026_11_07.md)，但它只支持描述性数据结构事实，不证明当前末端 packet-loss vs. sink-report-loss 配对假设。
- **CTBench** 已覆盖通信网络 RCA、部分可观测证据、设备异构、诊断延迟、交互轮数和 Token 成本；一般证据充分性或资源效率不能作为贡献。[论文](https://arxiv.org/abs/2608.12002)
- **LogDx-CI** 已评估大日志压缩对诊断质量、成本和后续工具调用的影响；一般日志摘要/成本—准确率曲线不构成增量。[论文](https://arxiv.org/abs/2605.28876)
- **TelemetrySuffBench** 已研究遥测视图中的故障检测、来源定位、证据充分性、安全弃答和字段/来源消融；改变可见字段本身不是新问题。[论文](https://arxiv.org/abs/2608.07899)
- **WirelessOpsAgent / WirelessOptBench** 覆盖 event time、ingest time、新鲜度、乱序、可用性和来源冲突，并报告 600 个无线网络 action-assurance episode。静态 freshness/order 与安全执行不能作为新主张；公开 artifact 未提供底层数据和轨迹，动态到达细节尚不能独立复核。[论文](https://arxiv.org/abs/2608.08277) · [artifact](https://anonymous.4open.science/r/wirelessopsbench-artifact-D969/)
- **ECG-Scroll** 已覆盖通用长时流式 Agent、因果在线决策、测量计划、及时记录及事件起点到首次记录的 detection latency。故通用 streaming benchmark、在线测量规划和时延指标均不是新贡献；最多留下通信网络拓扑/INT 报告生成与探测开销的领域化问题，是否有科学增量仍未证明。[论文](https://arxiv.org/abs/2609.33117)
- **Real-Time Detection and Repair of LLM Agent Failures** 已覆盖逐步轨迹监控、实时故障检测和恢复；不能将通用 Agent 过程监控或恢复作为新机制。[论文](https://arxiv.org/abs/2608.02464)
- **网络探测路径和测量开销优化已有直接工作。** AdapINT 使用双时间尺度探测和 DRL 规划动态探测路径，优化遥测任务的时延/开销；INT-label、Probe-Optimizer 及近期 INTO 研究也覆盖探测路径、覆盖率、探测率和网络资源约束。因此“自适应探测”“降低 INT 开销”或“RL 选择探测路径”本身不构成 FaultDA 增量。[AdapINT](https://arxiv.org/abs/2310.19331) · [INT-label](https://doi.org/10.1109/INFOCOM42981.2021.9488799) · [Probe-Optimizer](https://www.sciencedirect.com/science/article/abs/pii/S1389128624007679) · [INTO 综述](https://www.sciencedirect.com/science/article/pii/S1574013726001152)
- **LossSight** 已直接覆盖 INT 信息随业务包丢失时的丢失检测、定位、成因诊断和遥测恢复；因此“INT 丢包导致遥测不完整”及其检测/修复机制都不是增量。[论文 PDF](https://tanlizhuang.cn/papers/2021-%E8%AE%BA%E6%96%87-TNSM.pdf) · [LossSight 数据集](https://github.com/lzhtan/LossSight-Dataset)
- **通用多模态运维 Agent 评测也已出现直接覆盖。** *A Multi-Dataset Benchmark for Evaluating LLM Agents in Microservice Failure Diagnosis* 报告 AIOps2025 与 RCA100，含 500 余个专家标注故障案例，覆盖 metrics、logs、traces，并评估定位、故障识别与证据依据推理；*How Far Can Root Cause Analysis Go on Real-World Telemetry Data?* 在 OpenRCA 上比较经典方法与 LLM 多 Agent 方法，并区分“证据已存在但未使用”与“数据本身有歧义”。因此“在大规模异构遥测上评估 Agent”“证据存在/缺失诊断”不能单独作为本项目贡献。它们讨论的是微服务/RCA数据集，不等同于可控 P4 数据面与 telemetry-report 传输链的因果干预；这个环境差异只划定待审范围，不自动构成新颖性。[AIOps2025/RCA100](https://arxiv.org/abs/2606.29193) · [OpenRCA 分析](https://arxiv.org/abs/2607.13548)
- **LossSight² / LB-LossSight** 已研究 packet-level load balancing 下 MCM 的 INT 丢失定位歧义：论文给出多个位置与同一组 marking 值相容的例子，并为每个流、每个可选输出端口维护 marking counter；实验采用 Mininet、P4/BMv2、4-ary Fat-Tree，报告 100 次、每次 1,500 个 INT 包的平均结果。因此，“负载均衡导致 INT 缺报难定位”及通用 marking 定位不是候选增量。它研究路径上的 INT/业务包损失，没有在已审阅全文中报告“包已到 sink、sink 生成的 UDP report 在 collector 前丢失”与“最后 leaf→service 转发丢包”的配对因果实验；这是范围审读结果，不足以单独证明新颖性。[论文 DOI](https://doi.org/10.1002/itl2.393)
- **INTCollector** 讨论了 sink-to-collector 使用 UDP 可能丢失重要遥测信息，并研究高性能 INT 收集器。它确立了报告传输丢失是既有系统问题；当前候选不得把“UDP 会丢报告”或“collector 需要可靠接收”作为新发现。该论文未在已审阅范围内提供 Agent 与同信息规则的故障成因配对评测。[论文 PDF](https://dl.ifip.org/db/conf/cnsm/cnsm2018/1570470751.pdf)
- **GPINT 的 SQR 扩展**已在 P4 数据面缓存 INT 探测包，以相邻节点反馈和超时检测探测/链路失效，并重发探测或切换路径；论文在 Mininet 中比较不同负载、链路退化与恢复开销。因此“网络内 INT 探测丢失后的恢复”也已是既有机制。它的目标是恢复遥测探测覆盖；当前候选研究的则是业务包是否到达 sink、以及 sink 生成的报告是否抵达 collector，并让 Agent 与同信息规则作成因判断。这个区别只是文献范围差异，不能单独证明新颖性；若 NIKA 可见计数器让规则直接解决，候选仍应关闭。[GPINT 论文](https://arxiv.org/abs/2212.14876)
- **传统网络故障定位已融合主动服务探测与被动设备遥测。**KDD 2014 的数据中心系统用大规模 ping 形成服务影响信号，再将被动设备/链路告警与统计故障概率融合，并在 Azure 生产环境评估；因此“联合业务探测与设备遥测判断用户影响”不是新主张。[论文 PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/kdd14failureloc.pdf)
- **按观测选择下一次测试也有成熟方法。**Wang 等人用被动端到端数据指导顺序主动测试，以测试成本为目标；Arrigoni 等人根据期望信息价值逐步选择网络路径探测，并以滑动窗口应对状态变化。预算下选探测、融合主动与被动信号、基于信息价值排序都不能作为本项目独立机制。[Wang et al.](https://nlab.engr.uconn.edu/papers/bwang09-fault-detection.pdf) · [Arrigoni et al.](https://doi.org/10.1109/TNET.2022.3200249)
- **InPatching** 已在 P4 数据面为链路故障后的 INT 探测路径提供快速绕行恢复；故障后重规划/恢复探测本身不是增量。[论文 PDF](https://intrig.dca.fee.unicamp.br/wp-content/papercite-data/pdf/ariel23.pdf)
- **TeleNoise** 已研究网络重排与丢包噪声下的组级遥测计算；一般的丢包鲁棒统计也不是增量。[论文 PDF](https://gorinsky.networks.imdea.org/pdf/TeleNoise_IFIP_Networking_2021.pdf)
- **FaulT-Bench** 已在多个网络拓扑和 NIKA 工具接口下评估错误/不可靠报障文本、误归因和过度探测；因此网络 Agent 处理错误前提或探测行为的宽泛主张也不新。[论文](https://arxiv.org/abs/2608.27021)
- **TelemetrySuffBench** 已研究 Agent 遥测不足时的故障来源定位和安全弃答；本候选不能仅把遥测删除后重测一次。潜在差异只在于**遥测缺失由数据面故障因果地产生，还是由遥测管线独立产生，以及预算内的主动网络探测能否区分两者**。[论文](https://arxiv.org/abs/2608.07899)
- **传统 INT 故障定位**已研究遥测间隔、老化与定位时长/误告警；RFC 9232 也指出遥测处理、传输、存储和分析延迟会影响控制环。故“遥测晚到会影响诊断”本身不新。[INT 研究](https://ng-95.github.io/files/INT-detect_NOMS20.pdf) · [RFC 9232](https://www.rfc-editor.org/rfc/rfc9232.html)

**当前差异判断：**LossSight 已覆盖 INT 丢失检测、定位和恢复；LossSight² 又展示负载均衡时的定位歧义，INTCollector 早已指出 UDP collector 通道会丢数据。因此缺报检测、一般丢失定位及 UDP 丢失本身均不属于增量。LB-LossSight 依赖的每出口 marking counter/ loss-bit 当前不在 NIKA Agent 的同信息接口中：它是必须讨论的文献机制；若做增强仪表化对照，应单独列为 instrumented arm，不能冒充原 NIKA 同信息规则。主要公平基线仍只能读取 Agent 实际可见的 P4 `read`/`counters`、公开 INT 行与同预算探测。本候选仅在最后 leaf/sink 位置成对比较业务面丢包与 sink UDP report 丢失，并检验 Agent 是否能在强同信息规则仍无法可靠区分的背景负载下作出更好的归因或校准弃答时，才可能有研究价值。早期 gateway 故障会留下不同后续 hop 行，不能作为终端配对。NIKA 的 `silent_loss_baseline()` 使用隐藏目标端口映射，是 oracle verifier；公平规则不能读取 `root_cause_name`、隐藏映射或内部故障表。若同信息强规则已解决，或所有可用行动仍无法区分，就关闭该候选，保持通信遥测主线。

### 2026-11-07 GPINT / INTCollector 边界复核

**[文献事实]** GPINT 用 SQR 在交换机暂存 INT probe，等待下一跳反馈；超时后将探测数据送入监控模块并尝试重路由。其评估包含探测包丢失、链路退化、收集延迟和恢复路径开销。它解决的是 INT probe 在网内丢失导致监测覆盖下降。INTCollector 则指出 sink switch 到 collector 的 UDP 连接可能丢失报告，并实现 XDP 加速的 collector。LossSight 处理的是携带 INT 的数据包在路径中丢失所导致的遥测删失。

**[研究判断]**这些工作分别覆盖网内 probe 恢复、数据包与 INT 一起丢失、报告传输可靠性问题。当前唯一待证的区分是：在最终 leaf→service 业务转发丢失与 sink 已生成 UDP 报告但报告未到 collector 之间，Agent 能否从受限的同一观察中判断“业务影响”与“仅测量通道影响”，且超出确定性规则。它可能只是 NIKA 端口计数器的直接读数问题，故不预设模型有优势。

**[工程后果]**预注册前先冻结一个仅用公开 `read`、`counters`、INT 行和相同主动探测预算的规则；让它与 Agent 看完全相同的内容。分别测低背景和有未知并发流的背景，按外部逐包账本计分。若规则在所有预设背景都与账本一致，或端口聚合造成的不可辨识状态同样限制 Agent，则结束此候选，不扩模型数、不扩负载规模。后续扩并发与报告速率仅作已成立效应的适用边界验证。

**[贡献门槛修正]**当前候选不再视为潜在的新诊断算法。相关论文已给出主动/被动证据融合与成本/信息价值驱动探测的强传统方法。若保留论文路线，贡献必须来自严格的受控实证：在可识别性已由经典方法分析的终端数据面/观测管线故障条件下，证明现代网络 Agent 的失误模式、校准或成本—诊断权衡具有经典规则/序贯探测方法未揭示的稳定差异，并在独立故障簇复现。单一场景的一次配对、模型高于简单规则、或新 benchmark 代码均不够。后续候选必须先在准入页纳入 KDD14 式主动—被动融合、顺序主动测试与 Bayesian 信息价值探测基线；若差异消失，终止本候选。

**[固定接口推论]**令 `ΔE` 为窗口内目标出口端口 egress counter 增量，`N` 为同窗口已知探测包数。在背景包与目标包被配对固定、且无窗口内计数器复位/溢出的条件下，末端转发丢包使 `ΔE` 相对健康/仅报告丢失少计丢弃包数；只丢 sink UDP report 不改变业务转发计数。此条件下同信息规则已有直接判别信号，Agent 提升预期为零，必须作为负对照。若背景流量未配对，端口内其他包的丢弃会混入 `ΔE`，可能与目标包丢失产生同一汇总计数；这只是由聚合定义得到的构造性混淆，不是已观察到的 NIKA 运行结果。运行实验须固定背景回放或独立记录每个背景包的账本，并报告规则与 Agent 在同一可识别性分层内的结果。不得人为隐藏 NIKA 已公开的计数工具来制造差距。

### 2026-11-07 LossSight 机制精读与差异边界

**[文献事实]** LossSight 的检测机制以 alternate marking 为基础：交换机按流维护包计数并交替标记 INT 遥测包，提供 single-bit alternate marking 与 multi-bit cycle marking；收集 marking 结果后检测、定位并诊断随机丢包、拥塞丢包和 blackhole drop，再用 GAN 恢复缺失遥测。公开数据集列出随机丢失、拥塞丢失和黑洞丢失场景，文件包含时间戳、Loss Bit、两跳交换机与队列信息。来源为论文 §I、§IV-B–E 及公开数据集说明。[论文](https://tanlizhuang.cn/papers/2021-%E8%AE%BA%E6%96%87-TNSM.pdf) · [数据集说明](https://github.com/lzhtan/LossSight-Dataset)

**[文献事实与边界]**LossSight 不只是通用 INT 丢包恢复：它逐跳使用 loss marking 定位丢失，并在黑洞诊断中查询 INT source 与 INT sink 的 flow-match counter 增量；源端与汇端计数差用于判断黑洞。该机制与本项目拟用的交换机计数器强规则有直接重叠，不能作为本项目的新方法。论文没有明确展示的剩余边界是：INT sink 已收到并处理业务包、但 sink 之后生成的 UDP telemetry report 在 exporter/collector 通道中丢失，且把这种情况与 sink 前转发丢包作为受控配对条件。该边界目前只是对公开论文实验范围的审读结果，不能据此断言 LossSight 无法处理；需检查其实现和部署假设后才能下结论。LossSight 也没有 LLM/Agent 在相同工具预算下的诊断实验。来源：论文 §IV-B–D，尤其是诊断算法对 source/sink flow-match counter 的比较。[论文 PDF](https://tanlizhuang.cn/papers/2021-%E8%AE%BA%E6%96%87-TNSM.pdf)

**[研究含义]**候选只能继续作为“Agent 在通信网络遥测故障来源诊断中的增量价值”来研究；不能把 alternate marking、逐跳丢失定位、黑洞识别、source/sink 计数差或一般 INT 丢失恢复包装成创新。首先审计 NIKA 是否能以可见、可复现的方式注入并记录 sink 后报告丢失；若做不到，或已有 LossSight 实现覆盖该阶段，则关闭当前实验候选，保留长期方向。

**[工具进展]**已新增 `experiments/communication_telemetry/telemetry_report_relay.py` 原型。它接收 UDP 报告后先写入到达事件，再按冻结的 `(flow_id, packet_id, switch_id)` 精确键或 `(flow_id, *, switch_id)` 限定范围清单丢弃或转发；分别记录收到和处理事件，保存 relay 源码与 drop-plan 哈希，且不保存遥测正文。它支持 `--max-reports` 有界退出。原精确键 smoke 记录见 `RELAY_LOOPBACK_SMOKE_2026_11_07.json`；新增可复播脚本 `relay_flow_scope_smoke.py` 与记录 `artifacts/relay_flow_scope_smoke_retry1/result.json` 显示：四份合成报告中，仅预注册 flow 与 switch 下两个不同 packet ID 被丢弃；同 flow 的其他 switch 报告和另一 flow 报告均到达本地 UDP collector，事件计数匹配。该结果验证 relay 的合成 localhost 匹配/转发行为，不是 NIKA 网络命名空间、原生 collector 或 Agent 实验的验证；relay 仍未接入运行中的 NIKA，研究贡献状态不变。

**[NIKA 可见接口修正]**对固定 NIKA 提交的 `p4rt_manager.py` 进一步核对发现，`counters` 返回按端口索引的 ingress/egress 聚合计数和 SYN/non-SYN 汇总计数，并不暴露 LossSight 的 per-flow source/sink counters。实验中的公平规则必须适配 Agent 实际可见的聚合计数；LossSight 原始 per-flow 算法只能作为文献基线描述，不能在不增加同等 Agent 输入的情况下直接拿来对比。NIKA 默认 `DiagnosisAccessPolicy` 允许所有工具和节点，且 `p4rt_exec` 同时注册只读计数与配置修改子命令，`exec_shell` 可对节点执行任意命令；因此真实 Agent 实验前必须冻结节点白名单、只读包装器、探测预算和工具权限，否则策略比较不可解释。以上来自固定源码静态审查，未做运行时确认。

**[2026-11-07 可辨识性收窄]**对固定 NIKA 的 `hop_exporter.py` / `collector.py` 再做静态交叉核对：报告用 `(flow_id, packet_id)` 聚合，单行含 `switch_id` 和 `sink` 标志；collector 的 `trace_complete` 仅表示是否已收到任一 `sink=true` 行。于是“包在 sink 前丢失”和“包到达 sink、但 sink exporter 的报告在 collector 前丢失”会产生相同的 Agent 可见部分轨迹：上游行存在、sink 行缺失、`trace_complete=false`。relay 账本能区分这两段历史，但它是 evaluator-only 真值，不能给 Agent。端口计数可能打破等价，却只有聚合数，能否在背景流量和相同探测预算下稳定归因尚未知。具体条件式对照见 [LossSight MCM 源码级重放](experiments/communication_telemetry/LOSSSIGHT_MCM_SOURCE_REPLAY_2026_11_07.md)。

**[强规则负对照预测；源码级可检验推论]**在 pinned `gateway.p4` 中，`ingressCounter.count(...)` 先执行，路由及 `internalFaultLossConfig` 之后触发 `faultDrop()`；`egressCounter.count(...)` 只在 egress control 运行（[`gateway.p4` ingress](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L160-L236)，[`gateway.p4` egress](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L243-L263)）。因此，对隔离、已知路径的单向固定五元组 UDP 探测批次，若准确映射该流的入口与 service-facing 出口，`ingress_delta - egress_delta` 预期等于该窗口内在 ingress 丢弃的包数；report-only 丢失不应改变同一批业务包的转发计数。NIKA counter 仅按端口聚合，没有 flow key，所以这个规则不适用于未隔离的并发背景，不能逐流归因。它是必须实测的确定性强基线；清洁低背景臂仅作为规则校验/负对照，不能作为 Agent 新颖性证据。只有在预注册的背景负载和测量窗口下，该同信息规则仍留下可复核歧义、且 Agent 在相同工具与探测预算下稳定克服时，才值得继续当前假设。该推论尚未由 NIKA runtime 配对实验证实。

**[方向内的受控背景流量入口]**固定 NIKA 还提供 [`BurstTrafficGenerator`](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/traffic/burst.py)：可用固定 seed、源节点、flow 数、UDP/TCP、速率、包长和持续时间生成同步负载；`raw_udp` 模式会在目标端启动 UDP sink，并把五元组与 flow ID 写入返回摘要。它可作为第一阶段可复现背景负载，检验并发流量是否让 Agent 可见的 per-port counter 强规则出现歧义；它不是生产流量复现，也不能提供故障真值。现有 sink 丢弃 payload、不记逐包 ID，因此逐包账本仍需单独观察 service 收包，并与 exporter/relay/collector 事件按 `(flow_id, packet_id)` 对齐。先跑受控负载和规则负对照；只有规则差距在该环境中成立，再研究真实匿名流量轨迹的重放适配。此处仅核实了源码入口，未运行 traffic generator 或 NIKA runtime。

**[Agent 信息权限精审]**固定 NIKA 的 `p4rt_exec read` 不指定 switch 时读取 intent 中全部交换机，输出 forwarding members（包括 BMv2 port ID）、ECMP groups、IPv4 LPM、计数与部分 runtime config；sanitizer 清理 `internal_fault` 字段。故同信息强规则可以利用公开转发状态和计数器，比“计数器黑箱”更强。当前还未证实 Agent 可见 `ethN ↔ BMv2 port ID` 对照，不能让规则读取 evaluator topology model 代替。`p4rt_exec` 接受原始 CLI 且 manager 暴露写命令，默认 NIKA policy 的 tools/node_roles 都是 `*`；实验需执行层 read-only wrapper，只允许 `read`/`counters` 并固定探测工具。

**[LossSight 算法边界]**论文 Algorithm 1 的 MCM 条件按 PDF 转录为 `(delta != 1) || (delta != -2^l + 1)`；当 `l=2` 时合法增量是 `+1` 与 `-3`，因此印出的析取条件对二者都为真。若将其理解为疑似应为 `&&`，sink 后单份报告丢失会令所有节点的标记同时跳号，倒序扫描首先把它归到终端遥测节点，而非独立报告通道。此为手工条件推导，伪代码运算符未澄清，不能宣称完成了 LossSight 运行时复现。它进一步支持“只审终端报告归因”，不支持新检测或 marking 机制主张。

**[强规则优先]**LossSight 已表明 source/sink 流计数增量是网络丢包诊断中的既有强规则；NIKA 的 ingress/egress 计数器规则应先与该机制逐项映射，不能仅因运行于 Agent 工具接口就称为方法创新。只有在同信息、同预算实验中，规则对预先冻结的混合路径、并发背景流量或 sink 后 report-channel loss 存在可解释的边界，而 Agent 对这些边界呈现可重复且可归因的优势，才有继续实验的理由。计数器若稳定解决任务，停止模型实验；若可见观测无法区分故障源，也停止并报告不可辨识边界。2026-11-07 第四轮双臂 runtime 显示该干净条件下目标出口计数可直接区分两臂；此处不准入 Agent。更广泛结论仍需独立负载簇。

### 主动探测的接口边界

NIKA 的 [`active_tcp_probe`](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/traffic/active_probe.py) 可指定 TCP 五元组与 payload 数量，返回 `acked` 和耗时，不直接报告丢包计数；TCP 重传可能掩盖小比例数据面丢包。按独立均匀丢包率 `p=0.02` 作理想化计算，32个目标路径包至少出现一次丢包的概率约47.6%，149个约95.1%，228个约99.0%；这是预算规划近似，NIKA 实际使用固定 CRC 哈希，真实序列不满足已证实的独立同分布假设。因此，预检脚本中的近 100% 损失只能验证注入可达性：同一个 active TCP probe 很可能直接分开完全断路和 report-only 条件，不应将该设置用作 Agent 能力比较。另一方面，NIKA Agent-facing `p4rt_exec` 支持 `counters` 命令；输出净化器仅移除包含 `internal_fault` 的私有项，入口/出口计数保留。P4 ingress 早期计数后才执行故障丢弃，`egressCounter` 在 egress control 计数。**源码推论：**对固定已知探测流比较端口计数增量，真实数据面丢包可能造成 ingress/egress 增量差，而 collector-only 丢报告不应改变交换机转发计数。这很可能形成强确定性 baseline，显著提高了本候选的 NO-GO 风险；是否能按端口、路径和窗口精确归因仍需实测。下一步先冻结该规则并检查背景流量、端口映射、计数器复位/溢出和探测流重传影响；若规则已稳定区分两类状态且没有剩余模型决策差距，就关闭论文候选，不调用模型。

| 信号/记录层 | 真实 P4 转发丢包 | exporter/collector-only 丢报告 | 当前可判定范围 |
|---|---|---|---|
| Agent 查询到的 collector INT 行 | 相应 packet/hop 可能不存在 | 同一行也可能不存在 | 两者可能观测等价；单凭缺行不能归因。 |
| 服务端收到的已知序列包 | 被丢包不应到达 | 业务包仍可到达 | 可由外部 harness 建立真值；当前 Agent 接口是否能看到同类应用层证据待核。 |
| exporter 已发 UDP report、collector 未收到 | 被丢数据包对应的出口 report 不会生成 | 生成后可在传输/收集阶段丢失 | 需要外部账本分开记录；Agent 目前只有 collector 查询，不一定能观测 exporter 发报。 |
| P4 端口计数器 | ingress 计数在丢弃钩子前增加，egress 计数在 egress 阶段增加；已知流的两端增量可能不同 | 业务转发计数应保持 | `p4rt_exec counters` 路径与计数输出在 Agent-facing 源码中可见。计数器增量差是高优先级强规则；精确流量配对、噪声和权限运行语义待验证。 |
| `active_tcp_probe` | TCP 连接/ACK 可能因重传继续成功，耗时可能变化 | 业务 TCP 通常仍成功 | 返回 ACK 数/耗时，不是直接丢包传感器；必须先证明信号有判别力。 |

优先强规则：读取固定 P4 端口计数快照，发送已知探测批次，读取第二次快照，按路由端口计算 ingress/egress 增量差；再与 collector 中相同 packet/flow 的可见 INT 行交叉核对。若 Agent 的 `exec_shell` 节点权限允许，可发送受控 UDP 小包；否则仅用 MCP 暴露的 TCP probe，并将重传影响单独计入。该规则仅用 Agent 可见 counters、拓扑、探测和 collector 数据，不读取隐藏故障状态。NIKA 的 verifier 使用 2048 个单包 UDP flow 建立隐藏 egress 映射并核验丢包，这说明低比例丢包的症状检查使用了大批量流量；但其按内部 `bmv2_port` 选择目标流的步骤不能移植为公平 Agent baseline。此规则目前是源码驱动的候选，尚未运行。NIKA 原始任务的提交目标只有最终根因，没有“修复/停止/升级”的原生动作分数；若把动作决策作为主结果，必须在独立版本化协议中明确定义合法动作和标签，不把它冒充原生任务契约。

NIKA 场景注册器会为带 `p4` 标签的场景加载 BMv2 MCP server；默认 `DiagnosisAccessPolicy` 的工具与节点角色均为通配符。因此默认配置下 Agent 可以调用 P4 计数器工具，实际实验仍需冻结并记录所用访问策略。按 `silent_egress_packet_loss` 的2%设置，在独立均匀假设下 32/149/228 个**实际经过目标端口**的探测包约有47.6%/95.1%/99.0%的概率至少出现一次丢包；目标端口占比与 CRC 哈希相关性未知。NIKA verifier 总共发送2048个单包 UDP 流并通过隐藏映射筛出目标端口，公开 Agent 的有效目标端口样本量不能从总包数直接推断。

## 一页准入门槛

| 门槛 | 当前定义与状态 |
|---|---|
| **原始任务契约** | NIKA 0.2.0 有 `silent_egress_packet_loss`，原生提交只评价最终根因。它没有“区分业务面丢包与遥测管线丢包”的标签或操作目标；这需要另建、版本化且不覆盖原始分数的研究任务协议。不得称为原生评分缺陷。 |
| **处理与对照** | 固定网络拓扑、业务流量、模型、工具权限和预算。至少配对：无故障健康对照、P4 出口真实丢包、仅 exporter/collector 丢报告、两类同时发生。对每个包同时记录发送端、服务端接收、每跳 exporter 生成和 collector 收到的账本；Agent 和确定性规则读取同一公开视图，并可调用相同次数/字节预算的主动探测。先用原生发布任务做可达性复现，再评估需另加的遥测管线故障处理。 |
| **主指标** | 最终根因及成因类别准确率、校准后的“不足以归因/需探测”决策、错误修复/不必要操作率；主动探测包/字节与终态耗时。模型成本与网络服务影响作为次指标。丢失层真值必须由外部事件账本给出，不能从 Agent 看见的缺失记录反推。 |
| **可达性依据** | 固定源码中 `gateway.p4` 在 INT 插入后执行 `internalFaultLossConfig` 丢包；`hop_exporter.py` 只对实际观测到的出口 INT 帧发 report；`collector.py` 经 UDP 收报并写 JSONL；`int_query_telemetry()` 仅返回已有 collector 行。`active_tcp_probe` 只返回 TCP 应用 ACK 数与耗时（可能被重传掩盖），`p4rt_exec` 有计数器查询能力但真实可见范围和辨别力未验证。源码只证明候选路径和工具入口，不证明运行时有可区分轨迹；还缺逐层事件账本及接口信号的离线可辨识性审查。 |
| **预测范围** | 研究的是 Agent 能否区分“服务流量真的没通过”与“测量记录没到”，并选择有信息价值的诊断动作；不是一般部分可观测性、INT 丢包检测、路径修复或评分器漏判。 |
| **否证条件** | P4 丢包未导致可见 INT 轨迹删失；两类故障对可用探测仍不可区分；简单同预算规则达到相同性能；Agent 差异只来自工具权限/任务提示不匹配；或 LossSight/FaulT-Bench/TelemetrySuffBench/NetOpsBench 的固定版本已覆盖同一因果对照与行动评价。任一成立即关闭该假设。 |
| **最低成本与安全** | 先完成离线接口契约和时钟/日志方案审查，再用无容器模拟数据验证事件账本结构；不把模拟当作 NIKA 实验。运行 NIKA 前需重新评估本机虚拟化风险；此前出现 Docker 异常与 HYPERVISOR_ERROR，不因设计通过自动启动容器。无付费 API 准入。 |

**当前裁决：**原生评分漏判主张 **NO-GO**；故障耦合观测删失候选 **HOLD**；没有运行时因果账本、Agent 轨迹或跨模型结果，不声称论文贡献。研究方向保持 AI × 通信网络遥测。LossSight 与新近多模态 RCA 工作共同排除了“通用遥测 Agent benchmark”和“新的丢包诊断算法”两种宽泛主张；唯一允许继续审查的是在可控网络报告管线故障下，Agent 相对 LossSight 思路和同信息强规则是否存在稳定、可复核的剩余价值。该差异尚未证明；若聚合计数规则在受控背景流量下解决问题，或终端配对任务无法扩展成独立任务簇，就对这个候选作 NO-GO，研究大方向仍留在通信遥测内。下一步只验证这一个候选的可辨识性与最小成本，不切换方向或另开主题。

## 固定 NIKA 源码审计

审计版本为 NIKA 官方 `main` commit `ac4422d8a4a03be2b905e28edf72993d467e1b81`。本轮只读审阅源码，没有运行环境或 Agent。

| 源码位置 | 直接观察 | 含义 |
|---|---|---|
| `hop_exporter.py` | `capture.recvfrom()` 接收并解析帧后才调用 `time.time_ns()`；该值写入 `packet_timestamp`、`ingress_timestamp`、`egress_timestamp` 后再经 UDP 发送。P4 的 `egress_global_timestamp` 用于虚拟队列计算，没有写入遥测。 | 时间是 exporter 用户态观察时刻，不是已验证的数据面事件时间。 |
| `collector.py` | UDP 收包、聚合每跳报告并追加 JSONL；保留 exporter 时间和 hop 序号，不记录 collector 收包或持久化时刻。 | 尚不能直接测量 exporter→collector、collector 排队/写盘延迟。 |
| `telemetry_api.py:int_query_telemetry()` | 从当前 JSONL 读取最近最多10,000行，以 `packet_timestamp` 过滤后返回。 | 查询只返回当时已持久化的记录；无法重建此前何时到达。 |
| `gateway.p4` / `control.py` / `verify.py` | P4 对 gateway 的非 VIP 匹配流量启用 INT；service 地址在 `10.0.0.0/8`。环境验证的 `nc` 探测在 Agent 阶段前。 | 遥测由匹配数据面流量触发，没有证据表明后台自主持续采集。 |
| `host_server.py` / `registry.py` | Agent 可调用 `active_tcp_probe` 按指定 TCP 五元组发送固定数量探测包；collector 追加 JSONL。 | Agent 自发探测会内生影响遥测；主实验宜用外部固定流量，二者分开报告。 |
| `lab.py` / `tc_api.py` | P4 环境有专用 `telemetry_lan`；通用 `tc_set_netem()` 接受 delay/jitter/reorder，诊断工具白名单未暴露该接口。 | 外部处理在源码上可达；运行时权限、接口映射和隔离仍未验证。 |
| `task_server.py` / `scoring.py` | 有最终 `submission.json` 后拒绝后续 submit；score 比较 `root_causes` 与真值。 | 无原生中间修正记录；最终正确标签之外的过程指标需独立测量协议。 |

**阶段 A 裁决：源码层操作入口部分通过，测量有效性未通过。** 仍需确认 collector 收包/写盘与查询快照的事件记录、进程时钟/注入时刻校准、任务根因真值、运行时 TC 权限和网络流量隔离。不得把 `packet_timestamp` 称为网络事件时间，也不得把源码支持描述成已完成运行实验。

### 隔离 Linux runner 的可行性

本机曾发生 `HYPERVISOR_ERROR`，但经用户批准后，使用一次性 Docker runner 完成三轮 pinned NIKA 小型 P4 运行。第三轮完成 report-only arm 的逐包核验：四流各 94 个 service packet ID 与 relay 中同一 leaf 被丢弃的 94 个 report ID 完全相等，共 376/376；应用 socket 也各收件 94 个 datagram。两端口的 P4 leaf loss table 都可读回，之后 TCP 探针 target egress 为零且 VIP HTTP 失败三次。Teardown 成功且没有残留 Kathara 容器。细节见[运行报告](experiments/communication_telemetry/NIKA_RUNTIME_PREFLIGHT_2026_11_07_RUN3.md)、[原始 JSON/relay 事件](experiments/communication_telemetry/)和[精确 join 审计](experiments/communication_telemetry/NIKA_REPORT_ONLY_PACKET_ID_JOIN_2026_11_07_RUN3.json)。这验证了单一小拓扑的 report-only arm，但没有在 data-plane-loss 条件下运行相同 UDP workload，也没有强规则、Agent、留出任务或跨拓扑结果，因此不支持论文贡献。

**报告丢失配对的运行接口约束（固定源码审计）：**NIKA 的 [P4 lab wiring](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/lab.py) 将 exporter 目标地址写入启动命令；exporter 固定发送到 UDP/32766，而 [collector](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/collector.py) 默认也监听 32766。Relay 配对需要在实验 runner 对固定提交做有记录的最小 overlay：collector 改听 32767，relay 占用 32766 并转发到 loopback:32767；不得把这说成上游原生配置。另，[exporter 将 IPv4 identification 读作 `packet_id`](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/hop_exporter.py)。relay 已支持冻结的 `(flow_id, sink_switch_id, packet_id="*")` 匹配，并在第三轮 runtime 中通过逐包 ID 账本核验。该 overlay 不改 NIKA 源码，但报告丢失臂与真实末端数据面丢失臂仍须用相同 UDP 流量成对运行；目前只完成前者。

## 方向内的阶段安排

1. **测量账本定义：**明确 packet ID、路径期望、P4 丢弃点、exporter 观察、collector 接收、Agent 查询五个阶段及统一时钟/顺序；账本真值不得暴露给 Agent。
2. **可辨识性审查：**先用确定性构造证明哪些观测能区分真实转发丢包和 telemetry-only 报告丢失；若在 Agent 可用接口下等价，候选到此结束。
3. **强规则冻结：**仅基于 Agent 可见信息和同预算主动探测设计规则基线；NIKA 隐藏 fault 参数和 `silent_loss` verifier 仅用于外部真值核验。
4. **运行时准入（已通过有限可达性核验）：**第四轮已完成一个固定小拓扑、固定四流 profile 的 report-only/leaf-loss 双臂运行，并保存 service、relay、collector 与 P4 counter 记录。该结果只证明这组单次受控配对可复现；它同时显示低背景条件可被 R0 直接区分。下一阶段不跑 Agent，而是审查是否存在有任务真实性依据且可让同信息强规则犯错的背景/窗口压力条件；先冻结规则与否证标准。
5. **小规模开发与独立确认：**以上通过后才做配对开发实验；出现可解释差异后，再扩独立任务/第二模型。未出现差异就关闭假设，方向保持不变。
6. **通信遥测规模验证：**只有配对因果和规则对照先显示可靠差异，才逐步增加并发 flow 数与遥测报告速率，记录诊断质量、collector 丢失/排队、查询字节数、端到端诊断时延和运行资源。负载档位由 hosted runner 上测得的容量确定，不预填没有依据的规模数字；规模效应只用于验证适用边界，不单独包装为新机制。

RL 仅在配对实验证明有稳定可学习差距后再考虑；Python 负责编排，C++/Go 只在实测瓶颈出现时加入。语言、模块数和版本数不作为研究进展指标。

## 冻结比较协议：先检验规则上限，再决定是否跑 Agent

这套比较协议只服务于上面的通信遥测问题，不构成新的算法主张。每个系统面对同一故障实例、同一公开观测快照、同一只读工具集合和同一主动探测预算；隐藏故障标签、目标映射和逐包真值仅供评分器使用。所有规则阈值及似然参数只在开发簇确定，在留出簇运行前冻结。

| 臂 | 冻结内容 | 它回答的问题 |
|---|---|---|
| **R0：端口计数负对照** | 用公开路由映射、窗口前后 ingress/egress 聚合计数及已知探测批次，按预先固定的规则判断末端数据面是否有额外丢包。先在背景完全配对的情形运行；不得读取隐藏 flow-to-port 映射。 | 简单可识别条件下，计数器是否已完整解决任务？若是，这是规则负对照，不应把该条件作为 Agent 优势证据。 |
| **R1：主动—被动融合规则** | 将同一公开 INT 行、P4 `read`/`counters`、探测响应和拓扑路径按开发集上冻结的判定表融合；阈值只能由开发簇拟合或选择。 | 经典的主动探测与被动遥测融合是否已覆盖 Agent 的诊断信息？ |
| **R2：顺序探测规则** | 每轮只选择预注册候选探测中预期判别力最高且成本最低者；使用开发簇估出的条件分布/似然，达到冻结的停止界限即提交诊断，否则在预算耗尽时弃答。若固定哈希或重试机制不满足拟用统计假设，不采用相应似然模型，改用公开验证过的经验表并明确适用范围。 | 在同样的探测次数、字节和时限下，成熟的顺序测试能否解释 Agent 的优势或代价？ |
| **A：Agent** | 冻结模型快照、提示、工具包装器、温度/采样参数、每次调用及总预算；Agent 与规则可见字段完全一致。 | 在强规则已经覆盖后，Agent 是否仍有稳定且可复核的额外诊断价值？ |

主要报告：按故障成因计算的 balanced accuracy；错误但高置信归因率；选择性风险—覆盖率；探测包数、字节数与完成时延。弃答不与正确定位合并计分。先报告单故障低背景负对照，再报告背景未知及混合故障条件。规则与 Agent 的结果按相同任务配对，置信区间以独立任务簇为单位；同一场景的重试、随机种子和负载档位只算簇内重复，不能充当独立任务簇。

独立簇须在运行前按拓扑/故障注入位置/背景流量生成机制的任务血缘定义；不可在看到结果后拆分簇或挑选最有利的权重。当前公开 P4 轨迹没有该末端因果配对，也没有已核实的多个独立簇，因此当前只能准备协议和运行入口，不能声称跨簇结论。

**停止规则：**若 R0 在配对背景下完全区分两类故障，保留它作为负对照，转测预先定义的未知背景条件；若 R1/R2 在留出簇与 Agent 持平且成本更低，关闭“Agent 有额外价值”假设；若所有同权限动作对两类状态都不可区分，则报告该接口下的不可辨识性并停止模型比较。只有 Agent 在独立留出簇上相对最强冻结基线产生稳定、校准良好的差异，才准入跨模型和负载扩展。无论哪种结果，研究方向仍保持 AI × 通信网络遥测。

## 2026-11-07｜研究主线与运行准备收束（历史快照，已由下方第四轮结果更新）

长期方向保持为 AI Agent 对通信网络遥测的可靠诊断与运维；若候选被否证，只关闭该候选，不改换研究领域。第三轮 report-only 结果已由下方第四轮双臂实测更新。

## 2026-11-07｜第四轮：完成 packet-loss / report-loss 固定流配对

在 pinned NIKA `ac4422d8a4a03be2b905e28edf72993d467e1b81`、Kathara 3.8.3 的 `p4_dc_gateway` 小拓扑上，以同一四条五元组 UDP 流配置（seed 20261107、32 Kbit/s、128 B、3 秒）完成 report-only relay-drop 和 leaf→service packet-loss 两臂。两臂是 workload/profile 匹配，不是逐个 IP packet instance 匹配；每次 burst 都产生新的 IPv4 IDs。

- report-only：每流 94 个业务包到达 service；AF_PACKET IDs 与 relay 丢弃的对应 leaf sink-report IDs 逐流 94/94 完全相等。Relay 收到 1128、转发 752、丢弃 376 条 report。Collector 每流保留 188 条上游行、无 sink 行，共 752 行。
- leaf-loss：每流 service AF_PACKET 与 UDP socket 收件均为 0。Relay 收到并转发 752 条上游 report、无丢弃；collector 同样每流 188 行且无 sink 行，共 752 行。
- 两臂 target service-facing port 3 的 egress packet delta 为 376 vs 0；窗口内 ingress deltas 一致（port 1=282，port 2=94）。因此低背景、固定路径下，公开拓扑映射和 P4 counters 显示出简单 R0 可区分这一配对。该结果是强规则负对照观察，不是已冻结多次评估的 baseline；对此条件不运行 Agent，也不是论文贡献。
- NIKA 运行 `phase=complete`、容器关闭 `lab_closed=true`；无残留 Kathara lab containers。`passed=true` 只表示 bounded workflow 执行及清理完成。

证据：[运行分析报告](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.md)、[原始完整结果](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.json)、[双臂 relay JSONL](experiments/communication_telemetry/NIKA_PAIRED_REPORT_ONLY_RELAY_EVENTS_2026_11_07.jsonl) / [loss 臂](experiments/communication_telemetry/NIKA_PAIRED_DATA_LOSS_RELAY_EVENTS_2026_11_07.jsonl)及[结构化审计](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_AUDIT_2026_11_07.json)。运行 JSON 的少数解释性字符串仍沿用脚本配对补丁前的单臂文案；原始运行文件保持原样，配对数字以结构化字段和单独审计报告为准。

**更新后的裁决与下一步：**干净小拓扑上的初始科学候选没有 Agent 相对规则的空间，当前范围内 Agent 比较 **NO-GO**，更宽的通信网络遥测研究计划仍 **HOLD**。若继续，只设计一个有真实测量意义的并发背景/计数窗口压力测试：先冻结可见信息、映射权限、负载来源血缘、强规则 R0/R1/R2 与可能否证条件，并证明不同故障可在 Agent 工具视图下被识别。该设计未过审前不调用模型、不扩成新研究方向；若合理压力条件下规则仍完备，则关闭本候选，保留 AI × 通信遥测长期主线。

## 2026-11-07｜并发背景负载的 NIKA 可行性审计

**审计问题：**第四轮之后，能否直接给 `p4_dc_gateway` 加“真实背景流量”，再测试端口计数规则 R0？

**已核实源码事实：**固定 NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 提供 `traffic run od --mesh-mbps ... --background` 与 `ODFlowGenerator.start_traffic_background()`，可以在 Agent 工作流前运行 all-to-all iperf3 流量。NIKA 的 agent pipeline integration test 也在执行 Agent 前启动此类背景流量。它证明背景负载的运行路径存在，但该 mesh profile 是生成流量，不是实测运营商流量。`SndlibTrafficReplayer` 则从 `TrafficMatrixSeries` 重放 SNDlib OD 矩阵；源码把它放在 ISP traffic 子系统，当前没有证据表明其流量矩阵已接入本实验的 `p4_dc_gateway`。

固定 P4 程序中的 `internalFaultLossConfig` 按 `standard_metadata.egress_spec`（输出端口）匹配，丢包阈值作用于该端口的全部出站包；另一 `internalFaultDrop` 表按目的 IP 匹配。当前故障接口没有提供按五元组只丢实验目标流的已验证路径。因此，把大量背景流量也发送至目标 service 端口时，packet-loss 臂会同时影响背景包；这会改变处理强度，而非单纯给目标包观测添加噪声。若把背景流发往其他 service 端口，则它不污染目标 service-facing port 3 的 R0 计数。这个结论来自固定源码的键定义，不是额外 runtime 结果。

**研究决定：**不把 synthetic mesh 直接命名为“真实背景”，也不把同端口全流丢弃造成的计数差异解释成 Agent 难以诊断。当前候选还没有合格的未知背景压力条件，Agent 实验继续不准入。下一次工程验证只可作为 plumbing smoke：明确区分“已存在的合成 O-D 负载”和“公开、可许可且有血缘的实测通信流量”；若使用后者，先证明该负载能合法映射到 P4 拓扑且故障作用范围可与目标流区分。否则应把 packet/report-loss 候选关闭，仍留在固定的 AI × 通信网络遥测方向内审查新问题。

## 2026-11-07｜第四轮原始日志的 hop-order 复算

对 report-only arm 的 relay 事件 JSONL 按 pinned NIKA `switch_device_id()` 的角色编码复算：376 个数据包各有 gateway、spine、leaf 三条报告；全部 1,128 条报告中，10/376 个包组的 relay 接收序列至少有一次违反 gateway→spine→leaf 次序（10/752 个相邻角色跳转反转）。leaf sink 报告随后被 relay 丢弃；在 376 个实际转发的 gateway/spine 记录对中，有 1 对以 spine→gateway 次序转发（0.27%）。这些都是单次低速、无背景实验中的计数，不能估计一般发生率。

该结果只确认 relay 收包/转发序列与物理路径角色顺序有少量偏离。随后以固定版 NIKA `collector.py` 做 loopback UDP 组件复现：发送 `[spine, gateway, leaf]` 的报文后，最终 `hop_sequence` 仍为 `[spine, gateway, leaf]`，确认 collector 保留到达次序而不按拓扑排序；组件运行的源码 SHA-256 与结果写入结构化记录。但本次原 NIKA 运行未保留原始 collector 文件，所以不能断言该条真实反转实际进入了当时的 collector 输出或改变任何 Agent 判断。R1 强规则应根据拓扑和逐 hop 时间戳重建顺序，不能将 `hop_sequence` 的列表顺序直接当作路径因果顺序；未来运行需保存原始 collector 行及 ingest 时间。

复算资产：[报告](experiments/communication_telemetry/NIKA_RELAY_HOP_ORDER_AUDIT_2026_11_07.md)、[relay 顺序 JSON](experiments/communication_telemetry/NIKA_RELAY_HOP_ORDER_AUDIT_2026_11_07.json)、[relay 分析脚本](experiments/communication_telemetry/audit_relay_hop_order.py)；[collector 组件复现 JSON](experiments/communication_telemetry/NIKA_COLLECTOR_ORDER_SEMANTICS_2026_11_07.json)与[复现脚本](experiments/communication_telemetry/reproduce_collector_arrival_order.py)。候选仍为 **HOLD**；此测量现象是 R1 构造与遥测采集协议的约束，不是独立论文贡献。

## 2026-11-07｜近邻与公开通信数据集复核

### 近邻结论

- **Agent RCA Bench** 已对固定 incident、model、prompt、telemetry 与资源预算成对比较观测接口（Prometheus/Loki/Tempo、统一 SQL/PromQL、以及带语义图的接口），并报告多模型的诊断正确性、输入量与调用数。它排除了“换一个更方便的查询界面就能提升 Agent RCA”这类宽泛主张。其公开 release 描述 14 个事件、六个模型和成对比较；现有报告也披露了结果方向随数据集/故障层级改变及部分端点未通过校正，故不把其描述性总数改写成普遍效果。[仓库与报告](https://github.com/GreptimeTeam/agent-rca-bench) · [在线报告](https://rca-bench.greptime.com/)
- **CTBench** 报告 126 个 RCA 任务和 108 个 path-restoration 任务，由 15 名资深电信专家设计，带黄金证据步骤，并评估最终回答与诊断证据。通信网络 RCA、证据链质量和资源成本都不是单独的新主张。[论文](https://arxiv.org/abs/2608.12002)
- **AIOps2025/RCA100 多数据集 Agent 评测** 报告 503 个专家标注案例和约 15.3 GB 多模态可观测数据，评估故障定位、类型识别和证据依据推理。这排除了“将大规模异构遥测与过程标签组合起来”作为一般增量；仍需区分其微服务/云数据与数据面逐包网络实验。[论文](https://arxiv.org/abs/2606.29193)
- **TelemetrySuffBench** 构造相同执行轨迹的粗视图、语义字段掩码和模型可见输入完全相同的异因配对，测量检测、来源定位和弃答。不能再把一般“遥测缺字段”或“同视图对应不同原因”称为新机制。[论文](https://arxiv.org/abs/2608.07899)
- **通信遥测数据缩减已有成熟系统研究。** OmniMon 研究资源受限情况下仍保持每流/每交换机统计精度；NFV troubleshooting work 研究只保留疑似含故障的遥测；INT 空间抽样研究通过拓扑信号重建减少遥测开销。故“压缩/抽样 telemetry 后再跑 Agent”本身不够，必须提出 Agent 专属、任务相关且能改变网络故障诊断结论的可否证预测。[OmniMon](https://www.cse.cuhk.edu.hk/~pclee/www/pubs/sigcomm20.pdf) · [NFV troubleshooting](https://ieeexplore.ieee.org/abstract/document/9142775) · [INT spatial sampling](https://www.sciencedirect.com/science/article/pii/S1389128624001014)

### 可用真实数据的适用范围

- **ServDeg** 的五日数据共 13,952,494 条双向 flow 记录、110 列，含包/字节数、包间隔特征、LAN delay/jitter 采样及基于 delay/jitter 的服务退化标记；文件约 2.1 GB。Zenodo 页面目前 Rights/License 元数据为空，但随数据发布的 `README.md` 明确写明 CC BY 4.0；许可依据是该数据 README，而非 Zenodo API 的 license 字段。它适合检验高基数 flow 查询、统计汇总及退化事件检测的数据规模；采集来自一个大学宿舍网络，标注对象是服务退化而非路由/交换机根因，不能单独用作网络 RCA 的真值集。[数据集与 README](https://zenodo.org/records/21983587) · [方法论文](https://doi.org/10.1109/ACCESS.2024.3456588)
- **UNSW-IoTraffic** 发布约 95.5 million packets、约 4.94 million flows、27 个设备 PCAP，覆盖 203 天，另有 flow 与协议参数表；IEEE Data Descriptions 文章说明为 CC BY 4.0。数据描述明确说没有 ground-truth interaction/event annotations。它可能作为公开流量形状来源，但必须保留这是 trace-derived workload；不得把它说成已标注网络故障、生产核心网流量或 NIKA 的可直接配对轨迹。原始包的 payload 不进入 Agent 输入。[Dryad 数据页](https://datadryad.org/dataset/doi:10.5061/dryad.w0vt4b94b) · [数据描述论文](https://doi.org/10.1109/IEEEDATA.2025.3602010)

### 对当前唯一候选的影响

第五轮 NIKA raw-collector 配对复跑已验证收尾成功。报告丢失臂 376 个包组均未观察到 collector 最终 `hop_sequence` 的 gateway/spine/leaf 角色反转；leaf-loss 臂有 1/376 反转，序列 `[101, 2]`，而这两条 per-hop timestamp 数值为 gateway 较早。跨交换机时钟没有独立校准，不能把 timestamp 差包装为独立因果证据。与早先 relay/collector 运行的计数不一致，说明小样本次序反转不稳定；当前可保留的只是“collector 按到达顺序追加、故强规则不能盲信列表顺序”这一采集约束，不是 Agent 的稳定失效。

当前原 packet-loss vs sink-report-loss 候选在低背景小拓扑里已被目标端口 counter 规则分开（376 vs 0），Agent/API 不准入。新增近邻也没有创造一个可声称的缺口。研究方向仍固定为 AI × 通信网络遥测；下一阶段只能在**同一因果诊断问题**内检查一个明确的尺度变量：真实 trace-derived flow 负载与遥测粒度（逐包/逐流/逐端口）改变后，原有强规则是否仍有效、Agent 是否有稳定的额外诊断差异。开始前必须复核 NIKA 的按五元组流量/故障映射是否可实现、发布数据的字段与许可、每个诊断实例的独立血缘，以及与 Agent RCA Bench、CTBench、TelemetrySuffBench 和经典遥测缩减工作的精确差异。若端口聚合规则依然完备，或任务所需标签无法从数据中独立建立，则该候选 NO-GO；不以“多放数据”“跑更大模型”替代贡献。

**决策状态：**此处只是下一项候选变量的研究设计提示，尚未替换一页门槛、尚未通过新候选准入，也未授权模型 API 运行。当前唯一正式候选依然是 NIKA packet/report-loss 配对诊断，状态 **HOLD**。

## 2026-11-07｜流级负载候选的近邻预筛与 NO-GO

### 候选说法

在大量并发背景流下，少量目标流的业务面丢包可能被端口级计数聚合；Agent 是否能用主动诊断获得强规则无法替代的归因能力？这只是对同一 packet-loss/report-loss 主线的压力条件设想，不是新方向，也未进入运行阶段。

### 近邻与边界

- **Multipoint passive monitoring in packet networks** 明确使用多点普通包计数测量分段丢包，并可针对特定 flow 归因，包括多路径 flow。故不能把“端口计数看不到少量目标流丢包”本身作为新问题或算法主张。[论文记录与摘要](https://iris.polito.it/handle/11583/2765734)
- **LossSight** 已研究 INT 遥测流的丢失检测、定位、诊断与恢复；其公开作者版明确将按 flow 计数的丢包捕获作为比较方法。因此“缺少遥测行 + 流级计数/主动探测”已有直接方法近邻。[作者公开论文](https://tanlizhuang.cn/papers/2021-%E8%AE%BA%E6%96%87-TNSM.pdf)
- **SPADA** 面向可编程数据面的 per-flow 监测，针对有限硬件内存与大量活动流提出稀疏近似结构；**PINT** 已定义包含 flow、聚合与 bit budget 的遥测查询模型。通用流级粒度/开销折衷也已被覆盖。[SPADA](https://www.eurecom.eu/en/publication/7750) · [PINT](https://arxiv.org/abs/2007.03731)
- **FaulT-Bench** 是新的直接网络 Agent 近邻：200 个核心场景覆盖 8 个拓扑（其中 3 个沿用 NIKA），另有 360 个同网络状态下的报告者改写；任务含真实故障、健康网络上的错误报告、错误设备归因和错误根因报告。Agent 复用 NIKA 接口，使用相同 22 工具与 20 轮预算，并评估结论、修复建议、推理和成本。公开仓库还提供 3,960 条冻结运行记录、数据集与复算工具。它覆盖了“报告不可靠时是否查证网络状态”和“健康网络是否被误报”等一般主张。[论文](https://arxiv.org/abs/2608.27021) · [公开数据、轨迹与复算代码](https://github.com/Overlxrd-uwu/FaulT-Bench)
- **数据集索引与核心场景审计：[事实]**发布版 `dataset_index.csv` 的 200 条核心场景里明确含 `simple-bgp-false-premise-packet-loss`，标记为 `false-premise`、`negative-control`、`no fault injected`；所以“Agent 是否会核验 packet-loss 报告”不是新增问题。对索引对应的全部 200 个 `base`/`cex` 场景正文做了本地词项审计：`collector`、`exporter`、`report channel`、`sink report`、`INT` 均无命中；`telemetry` 仅有 1 处，指控制面与 CLI/telemetry plane 恢复，并非遥测链路故障。这个审计支持“公开核心语料未显式建模 collector/report-channel fault”的有限结论；词项审计不能排除未使用这些术语的语义等价任务，也不证明本项目新颖。FaulT-Bench 未见把 telemetry collector/report-channel 丢失与同一 packet 的 service delivery 做配对注入和逐包真值记录。范围差异仅用于界定候选。[场景索引](https://raw.githubusercontent.com/Overlxrd-uwu/FaulT-Bench/main/dataset/dataset_index.csv) · [论文](https://arxiv.org/abs/2608.27021) · [仓库说明](https://github.com/Overlxrd-uwu/FaulT-Bench)
- **原型机制复核：[事实]**FaulT-Bench 的 scenario parser 把 `PROMPT-TO-AGENT`、`INJECTION`、`POST-INJECT-CHECK` 和 `GROUND-TRUTH` 分开；注入器将 scenario 中的命令交给 Kathará 设备执行，没命令则将该样本作为无故障/预存状态跳过。这个接口在工程上可扩展到其它网络故障，但“可扩展”不能证明公开冻结的 200 个任务已经包含 collector/report-channel fault。该区分也意味着本项目若继续，只能主张具体的观测链路故障成因配对与逐包真值协议，不能再主张一般错误报障核验。[场景解析器](https://github.com/Overlxrd-uwu/FaulT-Bench/blob/main/faultbench/src/faultbench/scenario.py) · [注入器](https://github.com/Overlxrd-uwu/FaulT-Bench/blob/main/faultbench/src/faultbench/inject.py)
- **NetArena** 用动态生成网络任务评估 correctness、safety、latency，进一步排除了“做一个更大或动态的网络 Agent benchmark”这一宽泛主张。[论文与项目说明](https://www.microsoft.com/en-us/research/publication/netpress-dynamically-generated-llm-benchmarks-for-network-applications/?lang=ko-kr)
- 固定 NIKA 的 `internal_fault_loss_config` 仍是 egress-port 键；这是本项目当前接口的限制，不能把它偷换成已实现的 flow-selective fault injector。单为造出反例而改 P4 会改变固定任务和研究边界，当前没有充分理由。

### pinned NIKA 源码可达性核验

**[事实]**固定 NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 的 `SilentEgressPacketLossParams` 包含 `bmv2_port` 而不含 flow tuple；注入经 `set_deterministic_loss(runtime, host_name, bmv2_port, threshold)` 写配置。P4 `internal_fault_loss_config` 唯一 match key 是 `standard_metadata.egress_spec`。`p4rt_manager.py` 将 ingress/egress counter 分桶后再按 counter index（端口号）返回。源码：[fault class](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/problems/link_interface/p4_gateway.py) · [P4 table](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4) · [counter reader](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py)。因此 pinned injector 不能只 drop 一个五元组、同时保留同端口背景流。

### 近邻边界与裁决

多点被动计数、LossSight、SPADA 与 PINT 已覆盖 flow-level loss localization、INT loss handling 和受限流级监测/聚合；TelemetrySuffBench 以 telemetry masks 与 exact-equal ambiguous origin pairs 研究遥测充分性、故障来源和弃答；FaulT-Bench 在 8 个网络拓扑上评估不可靠故障报告并复用 NIKA 工具。因而“流级目标故障 + 并发背景 + 聚合计数”或“网络 Agent 需检查不完整遥测”均不足以成为独立增量。[TelemetrySuffBench](https://arxiv.org/abs/2608.07899) · [FaulT-Bench](https://arxiv.org/abs/2608.27021)。

**裁决：NO-GO（仅针对流级负载扩展）。**不修改 pinned NIKA P4，不用 host-side `tc` 冒充原生故障，不开始 Agent/API 实验。host-side drop 会改变故障位置；P4 五元组匹配则形成新的版本化环境，须另行建立任务契约。只有出现超过这些近邻、且 Agent 能在与强规则相同工具/信息/预算下取得可行动证据的具体剩余机制，才重新申请门槛审查。原始 packet-loss/report-loss 配对仍是唯一主候选，保持 **HOLD**；本裁决不导致研究方向切换。

这次预筛**不否决 AI × 通信网络遥测的长期方向**；只拒绝把“高背景流量稀释端口计数”包装成论文贡献。当前唯一正式候选仍是 packet-loss/report-loss 的末端因果配对，维持 **HOLD**；低背景 R0 已区分两臂，尚未出现 Agent 试验的科学准入依据。

## 2026-11-07｜NIKA collector-only 可识别性与 Agent 接口裁决

对同一 pinned NIKA 双臂复跑的原始 collector JSONL 做离线比对：两臂各 752 行、376 个 flow/packet 键；全部行标记 `sink_seen=false`、`trace_complete=false`，路径序列除 leaf-loss 臂一个包的顺序反转外一致。评测侧 service 抓包记录 report-only 送达 376 个包、leaf-loss 送达 0 个包，但 evaluator-only capture 不能作为 Agent 证据。进一步核对固定 NIKA MCP 接口：`p4_gateway` tags 会注册 BMv2 与 telemetry 两类 server；`p4rt_exec(args)` 可运行含 `counters` 子命令的 `p4rt_manager.py`，`int_query_telemetry(...)` 可查 INT 轨迹。本轮 service-facing egress counter 差为 376 对 0，故完整工具面下简单同信息计数规则已有直接区分信号。

**裁决：NO-GO（仅针对当前低速 terminal pair 的 Agent 能力实验）。**collector-only 证据未显示稳定识别差异；标准 NIKA 工具面可读取端口 counters，较早低背景运行记录过 376 对 0 的目标端口计数差，但本次复跑没有保存两臂配对 counter 快照，因此不能把强规则结果冒称为本轮配对实验结果。保留该配对作运行时与信息边界诊断，不调用 Agent/API，也不以它支撑论文增量。长期研究仍固定为 **AI Agent 在通信网络遥测与运维中的相对强规则价值**；当前尚无合格的独立任务假设，研究状态 **HOLD**。下一个设计必须明确工具可见输入、强规则可读字段，以及在同信息下 Agent 仍可能成功/规则会失败的可否证预测；没有这样的差异，不继续堆场景或扩大模型数。

## 2026-11-08｜公开多年网络遥测数据源审计（非新路线）

为解决 ServDeg 时间戳选择性缺失问题，本轮改用本机 PowerShell 查询 Zenodo API，审计 CESNET-TimeSeries26 的许可、记录规模和事件表；无需 Docker，也不下载数百 GB 的时序文件。五条官方记录均开放且标记 CC BY 4.0，主集合覆盖多年、提供层级聚合；`outages.csv` 仅 1,418 字节，含 7 个主集合全网监测缺口和 6 个独立纵向子网的停测事件。事件簇数量不足以支撑 Agent 跨故障能力主张；把同一事件展开成多实体/窗口不增加独立样本。直接近邻还包括 CTBench 的网络故障排查、TelemetrySuffBench 的 Agent 遥测充分性、CENTILE 的遥测预测决策回放。

**裁决：**CESNET-TimeSeries26 作为未来外部真实数据验证源**受限准入**，不作为当前主实验，也不改变唯一 NIKA 候选的 HOLD。当前先解决同信息规则与原始末端逐包账本问题；只有主候选过关后，才用 CESNET 检查方法能否迁移到真实网络时间序列。完整来源、下载体量、事件构成与限制见[数据源审计](experiments/communication_telemetry/CESNET_TS26_DATASET_AUDIT_2026_11_08.md)。

## 2026-11-09｜NIKA 共享端口投影假设更正

此前压力投影把同一出口端口上的目标包设为丢失、同时令背景包通过，和本文件上方已核实的端口级 loss table 键不一致。该投影现以 v2 源码语义重算并作废旧结论：固定 P4 10000 bp 条件将阈值设为 65535，hash `% 65535` 的结果是 0–65534，因此目标与背景的所有同端口包都会丢弃；report-only 臂则均通过该出口。仅对原先冻结的端口计数规则，五日 15 个负载分位点形成的 30 个公式条件全部可判，`underdetermined=0`。详见[投影更正和复算文件](experiments/communication_telemetry/SERVDEG_CROSSDAY_PROFILE_AUDIT_2026_11_09.md)。

因此，不再以“同端口背景负载使计数规则弃答”作为当前假设，也不启动共享背景 Agent 矩阵。当前具体待核问题收敛为**目标服务到计数端口的可见映射**：固定 NIKA 的原始只读 MCP 输出是否提供足够信息，让 Agent 从服务目的前缀、转发表和返回的端口 ID 推导目标端口，而不依赖 harness 私有拓扑对象？已有源码审计能说明 CLI 结构与返回字段，历史运行没有保存原始 MCP `read` 输出，故尚不能声称运行时 Agent 确实可见该映射。下一轮应从 pinned 工具的 JSON 序列化实现建立字段级预期，并用一份真实运行的原始输出复核；若路由已唯一绑定端口，R0 就是直接负对照，这组双故障配对没有 Agent 创新价值。若映射不唯一，先界定额外公开观测能否消歧，再判断是否值得进入模型实验。总体研究状态维持 **HOLD**，研究主线仍为 AI Agent × 通信网络遥测与运维。

### 2026-11-09 后续更正

上段“下一轮核验 service→port 映射”已完成并被新源码证据取代：NIKA 的 task description 显式加入 `NetworkEnvBase.get_info()` 生成的接口级拓扑边；Agent 工作流把 task description 原样传给模型；默认工具集允许 host 查询和 P4 read/counters。映射由拓扑边、服务地址/路由前缀与 egress port 共同得出，不能只检查 `p4rt read` 的 JSON 字段。故固定 packet-loss/report-loss 配对冻结为同信息规则负对照，不再为此增加实验轮次。详见[NIKA Agent 可见拓扑映射审计](experiments/communication_telemetry/NIKA_AGENT_VISIBLE_TOPOLOGY_MAPPING_AUDIT_2026_11_09.md)。

## 2026-11-09｜持续学习研究设计：通信流量中的低标签跨时段适应

下一阶段在通信网络遥测与大数据主线内研究持续学习，而不是继续发散新的故障评分候选。核心问题是：**在真实网络流量随时间漂移时，利用无标签历史流量预训练的 SNN，能否在新月份仅获得少量标签后快速适配，并比参数量/训练预算匹配的 ANN 持续学习基线更好地保留旧服务类别知识？**这是一条待检验假设，不把 SNN 的生物启发、时间编码或理论能效直接当成优势。

优先数据源为 CESNET-TLS-Year22：它提供一年期 ISP TLS 流量、180 个服务类别、流级统计和包序列特征，并采用时间顺序评价；官方论文指出随机拆分会高估时间一致评估结果，且一年内出现服务与流量分布变化。[数据论文](https://www.nature.com/articles/s41597-024-03927-4) · [官方数据工具与可选规模](https://github.com/CESNET/cesnet-datazoo)。CESNET-TimeSeries26 可作为后续无标签长期遥测扩展：覆盖约 2.7 年、多实体和 10 分钟/小时/日三种粒度，但其真实 outage 事件少，不能作为大样本监督真值。[官方数据页](https://cesnet.github.io/cesnet-tszoo/cesnet_timeseries26/) · [数据论文](https://arxiv.org/abs/2610.14799)。

直接相关研究已经包括：SNN 上的持续学习/遗忘控制（CoLaNET、SCA-SNN）、SNN 的压缩潜在回放、网络入侵检测的增量/持续学习、少样本流量分类，以及时间漂移下的 CESNET 流量分类。因此创新点不能是“首次把 SNN 用于网络流量”或“首次结合持续学习与少样本”；候选增量应落在**严格时间前推、真实 ISP 服务流、无标签时序预训练 + 预算受限的新类标签 + 旧类保持**的统一评价，以及一种针对按月漂移设计、可与回放/正则化法公平对照的记忆机制。[CoLaNET](https://arxiv.org/abs/2506.17169) · [SCA-SNN](https://doi.org/10.1016/j.neunet.2024.107037) · [Compressed Latent Replay](https://doi.org/10.1109/ISVLSI61997.2024.00052) · [网络流量持续分类](https://doi.org/10.1016/j.engappai.2022.105607) · [少样本概念漂移分类](https://www.sciencedirect.com/science/article/pii/S0167404826001593)。

### 研究假设与关键比较

- **H1（低标签适配）：**在按时间顺序的月度任务中，先用未标注历史流量作自监督预训练，再用每个新月固定的少量标签适配，会比纯监督同预算训练获得更好的新月 macro-F1；标签预算固定为每类 1/5/10 个，另报告总标签数与类别覆盖。
- **H2（持续保持）：**SNN 持续更新加压缩 latent replay 能降低旧月份/旧类别遗忘；须与相同编码器容量的 ANN、SNN fine-tune、SNN replay、ANN replay、EWC/LwF 及 joint-training 上界比较。回放存储字节数、可见历史样本数和更新步数逐项匹配。
- **H3（时间编码的独立作用）：**只有在控制参数量、输入信息、训练预算、标签样本和回放记忆后，SNN 的 packet inter-arrival/size spike encoding 仍带来稳定增量，才支持“脉冲时间建模对动态网络流量有作用”；对原始统计特征 ANN 与事件序列 ANN 做控制，隔离编码形式收益。
- **H4（计算代价）：**能耗不是先验主张。先报告更新时延、训练 FLOPs/事件数、峰值内存和模型参数；只有在可重复的真实目标硬件测量后，才比较 joules/update 与 joules/正确预测。

### 数据契约与实验流程

1. **血缘与字段审计：**固定 DataZoo 版本、数据 revision、服务标签映射、采样方式、许可证和官方时间戳精度；统计每月每类流量、类别出现/消失、客户端实体重叠与 1:10 均匀抽样机制。确认包序列字段在所选规模中真实可用；时间戳只按论文许可精度使用。
2. **冻结时间任务：**按月份建立前向任务序列，早期月份仅用于无标签预训练；后续月作为流式增量段，后月绝不回流到预训练。月份和服务族群整簇切分，严格杜绝同一流/重复记录跨训练测试。预注册 open-set 新服务与已知类漂移两类情形。
3. **自监督目标：**对无标签流做包序列下一事件/时间间隔重建或多视图对比学习；新月到达后，只在预算允许时请求少量标签。加入标签置乱、时间打乱和静态 IID 作为负对照，检验收益是否确来自时序结构和无标签预训练。
4. **主指标：**按月报告 macro-F1、旧类平均保持率、遗忘量、forward transfer、未知类召回、少数类性能、达到目标 F1 所需标签数及适配延迟；以独立服务族/时间段 bootstrap 置信区间，不按百万条相关 flow 假装百万个独立样本。
5. **阶段门：**先完成数据审计与 3–5 个月小规模基线复算，再冻结全年度时间方案；随后实现统一 ANN/SNN 数据管线和基线；最后跑多随机种子与消融。若 SNN 只在 IID 或参数不匹配时占优，则将结论写成持续学习基线研究，不宣称 SNN 优势；若少标签自监督没有收益，保留持续学习问题并定位失败环节，不另换领域。

**本阶段承诺：**这是一条明确的长期主线，不再通过频繁创建 benchmark 子候选来替代模型研究。当前只有公开文献与数据契约依据，未训练模型、未调用 API、无项目内性能结果。下一步先完成 CESNET-TLS-Year22 的本地/远程元数据与月度类分布审计，随后固化可运行的数据切分和 ANN 参照实验。
