# 2026-11-10｜1.1.10 完成 Year22 XS census 与时间切分冻结

完成 CESNET-TLS-Year22 XS HDF5 的全表读取与本地 SHA-256 记录：357 个日期表、10,000,000 条 flow，八个缺失日期与固定 DataZoo 元数据一致；生成逐日×APP 完整枚举计数、周统计、日期 split manifest 和 45 列输入字段契约，并对 APP/CATEGORY 标签映射单独记录哈希。修正 ISO week-only 错误：2022-01-01/02 属于 2021-W52，不得混入 2022 年 W52 部分尾窗。新增协议 v0.2，记录测试窗口类别支持仅为聚合 census、未产生模型预测，并量化均匀抽样预算下的服务类别覆盖。数据 census 不代表模型效果，ANN/SNN 未训练，科学状态继续 HOLD。原始 HDF5 和本机环境留在仓库之外。

# 2026-11-08｜发现 ServDeg 时间戳缺失具有选择性

在修正 NULL 分桶后，进一步对 MON 按 `start_time_aggr` 缺失分层：1,828,437 条空时间戳 flow 与 1,356,999 条有时间戳 flow 的大小和标签构成显著不同。空值组 SDd 标记及持续事件行率均为零；有时间戳组 SDd=6.330%、持续事件=0.656%，其包/字节分位数也高得多。因而仅用有时间戳行估计分钟流量会产生选择偏差；其他四日尚未做该分层。已将 ServDeg 的分钟负载校准用途标为暂停/不准入，直到缺失来源可解释；不将 flow cohort 累计包/字节误称为逐分钟速率。报告和门槛已更新；无 Agent/API/Docker 运行，科学状态 HOLD。

# 2026-11-08｜纠正 ServDeg 分钟负载统计的空时间戳分组

分钟统计复核发现 `start_time_aggr` 大量为空（五天缺失率 52.21%–70.49%）。首轮 SQL 把全部 NULL 合并成一个时间桶，产生虚假的极端峰值；已在脚本中改为单独计算缺失率，并仅对非空时间戳分桶，旧极端峰值不再采用。即使过滤后，分钟值也是按 flow 起始时间归组的流 cohort 总量，不是该分钟逐包发送速率；累计 bytes/packets 不能直接转成链路负载。ServDeg 当前只保留为横截面 flow-size 参考，不进入分钟级发生器校准。已同步更正五日报告、机器结果与研究门槛；科学状态 HOLD，未运行 Agent/API/Docker。

# 2026-11-08｜完成 LossSight 近邻的机制边界复核

逐节核对 LossSight 论文与其公开数据仓库：LossSight 已覆盖 INT 缺失检测、定位、诊断、恢复，并对黑洞使用 INT Source/Sink 计数差；因此广义的“从缺失遥测推断数据面丢包”及“融合源汇计数”不构成本项目贡献。当前仅余一个更窄的任务差异待验证：NIKA 的 sink exporter 已生成报告、业务包已到 service，但报告在 collector 前丢失。此差异尚未构成独立科学贡献；若相同工具下计数/规则即可解决，则关闭候选。LossSight 数据仓库未见明确许可证，不纳入可再分发数据。已把边界和停止条件写入一页门槛；没有运行模型/API、Docker 或新网络仿真。科学状态 HOLD。

# 2026-11-08｜补齐 ServDeg 五日负载分布复核

为判断单个星期一文件能否代表可用负载统计，使用本地 Python 与 DuckDB `httpfs` 对 Zenodo 上 TUE–FRI 文件进行远程列式读取，并与已下载且 MD5 校验的 MON 比较；未使用 Docker，也未完整下载四个远程文件。五个文件均为 TCP、各含 17 个 location 标签，窗口仅约 42–54 分钟；SDd/SDj 行率及包/字节分位数存在日间变化，星期三的包数 P99 和字节 P99 分别约为星期五的 2.16 倍和 2.35 倍。新增[五日复核报告](experiments/communication_telemetry/SERVDEG_WEEKDAY_SHIFT_2026_11_08.md)、[读取脚本](experiments/communication_telemetry/audit_servdeg_weekday_shift.py)和[JSON结果](experiments/communication_telemetry/SERVDEG_WEEKDAY_SHIFT_2026_11_08.json)，并同步一页研究门槛。该数据只支持 trace-derived synthetic workload 参数范围，不能代表全天、跨网络、真实包回放或 RCA 真值；发生器尚未校准，强规则尚未重测，Agent/API 未运行，科学状态仍 HOLD。

# 2026-11-08｜更正 NIKA 轨迹数据许可记录

复核 Zenodo record API 后发现 `metadata.license=null`，下载归档内也没有 LICENSE/README；NIKA GitHub 的 MIT 许可针对软件，不能据此认定轨迹数据为 CC BY 4.0。更正此前 P4 轨迹审计、研究方向文档和准入门槛中的 CC BY 4.0 记载，并更新复算脚本与机器可读结果为许可未核实。Zenodo 文件校验和匹配，但校验和只证明文件一致，不证明再利用授权。取得明确数据许可前，不将该轨迹集纳入新的可再分发分析；已有结构审计仅作为带来源限定的历史记录。研究主线保持 AI × 通信网络遥测；科学状态仍 HOLD。此修正和本轮离线审查未使用 Docker、未运行模型/API，也未推送。

# 2026-11-08｜用 DuckDB 审计 ServDeg 流量负载适用性

对随 README 明确标注 CC BY 4.0 的 ServDeg MON.parquet 做目标列全文件聚合并读取完整 schema，确认 3,185,436 条匿名 TCP flow、110 列和嵌套服务退化标注。文件覆盖 53 分 49 秒；包数分布强偏态（中位数 6、P99 1,533、最大 6,928,103）。点级 SDd/SDj 旗标和持续事件序列的行覆盖率分别约 2.70%/2.75% 与 0.28%，不能混作同一分母。此数据可给后续 *trace-derived synthetic workload* 提供流量统计，不含原始包、路径/设备根因，不支持真实包回放或 RCA 真值；单日结果也不能代表跨日。新增[审计报告](experiments/communication_telemetry/SERVDEG_MON_WORKLOAD_AUDIT_2026_11_08.md)、[DuckDB 复算脚本](experiments/communication_telemetry/audit_servdeg_workload.py)及[JSON 结果](experiments/communication_telemetry/SERVDEG_MON_WORKLOAD_AUDIT_2026_11_08.json)。该数据源审计不改变 NIKA 候选 HOLD，未运行 Agent/API/Docker。

# 2026-11-07｜复核 NetOpsBench v0.2 遥测轨迹的时间顺序与强规则对照

对固定 NetOpsBench 源码及公开 HF v0.2 轨迹离线复算：在 319 个案例中，只使用初始可见 `anomalies_detected` 字段的零工具二元规则答对 274/319，公开 Agent 轨迹答对 227/319；packet-loss 子集为 25/26 对 5/26。上游已报告相同 packet-loss Agent 结果及相似的历史窗口/当前 ping 混用，因此该复算是已知现象上的单字段基线对照，不是独立新贡献，也不是全部观察/权限匹配的强规则比较。26 个 packet-loss 轨迹有 20 个包含与某条 Pingmesh anomaly 相同主机/IP 端点（正向或反向）的 live ping，其中 18 个最终 verdict 仍错误；端点相同不等于 ICMP hash、受影响接口和测量窗口相同。源码顺序显示 live ping 在故障 episode 观测后、incident close 恢复前，不推断 Agent 实际恢复状态。新增[报告](experiments/communication_telemetry/NETOPSBENCH_TEMPORAL_EVIDENCE_AUDIT_2026_11_07.md)、[逐案复算脚本](experiments/communication_telemetry/audit_netopsbench_v02_traces.py)和[派生 CSV](experiments/communication_telemetry/NETOPSBENCH_V02_CASE_AUDIT_2026_11_07.csv)。描述性结果，不作显著性推断；主线仍为 AI × 通信网络遥测，NIKA 配对候选维持 HOLD。未运行 Agent/API。

# 2026-11-07｜接入 NIKA report-only 单臂预检（未运行）

将 hosted preflight 扩展为一个报告通道故障单臂：预计算 NIKA 固定 flow key，冻结 leaf sink 的 flow-scoped wildcard 丢弃计划；在 collector 节点将 collector 从 UDP/32766 移到 32767 并启动有限时长 relay；service 端以 evaluator UDP socket 记录应用层收件，并用 AF_PACKET 记录对应 flow/IP-ID，再核验 relay 丢弃、collector 保留上游行及无 sink 行。relay 新增 `--duration-seconds`，以保存完整 `run_finished` 汇总。NIKA/Kathara 源码没有改动；本地没启动 Docker/WSL，workflow 未推送/执行。此为未验证单臂，不含配对数据面丢包burst、独立任务簇或Agent，科学状态仍 HOLD。

# 2026-11-07｜为报告 relay 增加可审计的时限收尾

给 `telemetry_report_relay.py` 增加可选 `--duration-seconds`：有限窗口结束时写入既有 `run_finished` 汇总并退出，兼容原有按报告数停止方式；NIKA 配对预检可据此保存完整的 relay 接收/丢弃/转发尾记录。此改动尚未集成或运行于 Kathara/NIKA，事件时序、转发和 collector 对账均无 runtime 证据，不视为配对实验结果。研究方向固定，唯一候选继续 HOLD。

# 2026-11-07｜补入健康 UDP burst 的 service 侧逐包观测（未运行）

固定研究方向仍为 AI Agent × 通信网络遥测；唯一候选仍为末端业务丢包与 sink 报告丢失的区分。扩展 hosted NIKA preflight：在 service `eth0` 启动 12 秒、仅写 evaluator JSONL 的 AF_PACKET 捕获，保留目标 UDP 包的观测时间、五元组和 IPv4 identification，并与 collector sink 报告按 `flow_id + packet_id` 连接。固定 Kathara 3.8.3 源码确认默认 capability 集包含 `NET_RAW`，且 service startup 静态配置 `eth0`；workflow 精确安装 Kathara 3.8.3，避免依赖浮动版本。账本仅校准故障注入前的健康 burst，不能证明任一故障臂、完整 relay 路径或 Agent 能力。脚本/工作流尚未推送与运行，实际 capability、抓包、流量完整性和 ID 对齐率均未验证；没有新增运行时或科学结果，状态继续 HOLD。未启动本机 Docker/WSL，未调用模型 API。

## 2026-11-07｜修正 NIKA leaf-loss preflight 的业务路径基线

源码复核发现，service IP 落在 gateway 的 `10.0.0.0/8` INT watchlist 内；P4 会将匹配流 IPv4 protocol 改为 253 并插入 INT-MX，而 pinned NIKA pipeline 未提供 service-side 解封装路径。因此原预检将直连 service HTTP 作为唯一健康基线，存在由遥测封装扰动应用流量的风险。现改为同时记录直连 watched-service HTTP（诊断用）与 VIP HTTP（该路径跳过 INT 插入，作为业务可用控制）；对 VIP 后端池覆盖到的全部 leaf service-facing 端口写入 100% 丢包，确认表项读回并检查 VIP 响应变化及各端口计数。此改动只验证故障注入和粗粒度服务影响；VIP 控制不含 INT 轨迹，直连路径即使返回 HTTP 也不等于逐包配对就绪。仍需单独实现/验证 service 端点对 INT-MX 包的接收账本及 relay/collector report-only 臂。未运行 NIKA/Docker、未调用模型 API，候选 HOLD。

## 2026-11-07｜让 NIKA runtime preflight 记录强规则可见计数

扩展 `nika_leaf_service_loss_preflight.py`：在健康 HTTP 探测前后、loss 注入后探测前后，调用 pinned NIKA 的 `p4rt_manager.py counters --switch leaf_1`，将原始 ingress/egress per-port packet/byte 快照写入预检 JSON，并计算 service-facing BMv2 port 的 egress packet delta。该记录用于判定当前近 100% 丢包设置是否被公开计数直接识别，服务于后续强规则准入；它不包含 report-only 对照，不是配对实验，也不包含模型结果。workflow 未触发，故此改动仍待 hosted runner runtime 验证，科学状态 HOLD。

## 2026-11-07｜明确通信遥测候选的可识别性与停机门槛

将配对实验定义改为：两臂共享相同的初始 INT 缺失视图，Agent 可在相同权限和预算内获取后续证据；如果最终可见证据被限制为完全相同，则故障标签不可识别，不能把模型猜测表现成诊断能力。新增运行时逐包账本、冻结同信息 per-port counter/INT/探测强规则、按 workload/seed 隔离的 Agent 对照与测试集要求；强规则若达到 Agent 同等效果即关闭候选。`topo_size=s` 仅用于可达性/测量验证，不支持“大规模”泛化主张。RL、恢复策略和跨模型扩展暂不进入当前问题。研究章程、一页门槛和根 README 已同步；未运行 NIKA/Docker、未调用模型 API，科学状态仍 HOLD。

## 2026-11-07｜冻结通信遥测研究的首个验证问题

将长期方向固定为 AI Agent × 通信网络遥测分析与运维，并把当前阶段进一步收窄为一个问题：在相同可见遥测、工具权限和预算下，Agent 能否区分末端业务包丢失与已到 sink 后 UDP 遥测报告丢失，并胜过同信息强规则。探测/停止策略、恢复、RL 与跨模型扩展均暂不进入当前主张，待配对运行时实验通过后再单独评估。此收窄依据 pinned NIKA 源码：P4 丢弃钩子在 INT 添加后运行；hop exporter 只为实际捕获的出口 INT 帧发送报告；P4 公开端口计数是强规则必须纳入的基线。以上只确定实验设计边界，不证明运行时配对可达或 Agent 有优势。更新见[研究方向章程](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md)与[一页准入门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)；科学状态仍 **HOLD**。

## 2026-11-07｜准备 NIKA leaf/service 丢包运行时 preflight

在固定 NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 上新增有界脚本 `experiments/communication_telemetry/nika_leaf_service_loss_preflight.py`，并将手动 GitHub Actions workflow 改为运行该脚本及保存 JSON 结果。脚本先确认 `p4_dc_gateway` 小型拓扑中 `leaf_1:eth2` / BMv2 port 3 指向 `service_1_1`，测直接 HTTP 健康基线，再用官方 `silent_egress_packet_loss` 注入流程设置近 100% loss，检查 P4 表读回和服务影响，并关闭 lab。该高丢包率只验证注入和服务影响，不用于比较诊断能力：固定 NIKA 源码还提供返回 ACK 数的 `active_tcp_probe`，它可能直接分开完全断路与 report-only 条件。复核 NIKA 的会话关闭接口后，脚本现将未完成的预检会话标为 `error`，仅在步骤完成且会话关闭后写入 `passed=true`，避免失败运行被登记成正常结束。进一步审计发现上游 lab 固定将 exporter 和 collector 都接到 UDP/32766；报告 relay 实验需在 runner 使用可审计 overlay 把 collector 移到 32767。NIKA exporter 的 `flow_id` 可由预注册五元组确定，`packet_id` 来自每包 IPv4 identification；relay 已增加仅限 `(flow_id, switch_id)` 的 packet-ID 通配匹配，并通过 localhost 合成回环确认目标 flow/switch 下的两包被丢弃，其他 flow 或 switch 的两包到达 collector。复播脚本与结果分别位于 `experiments/communication_telemetry/relay_flow_scope_smoke.py` 和 `artifacts/relay_flow_scope_smoke_retry1/result.json`。这仍不验证 NIKA 网络命名空间与 collector 集成。预检不含成因配对或 Agent 运行；workflow 尚未推送和触发，未产生 NIKA runtime 证据。科学状态保持 HOLD。

## 2026-11-07｜核实 NIKA 标准任务的 P4 丢包注入边界

固定 NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 后追到 `p4_gateway_port_target()` 与 `p4_dc_gateway` topology model：标准注入参数只覆盖 gateway/spine 的 fabric-facing 端口，标准 dev/test `silent_egress_packet_loss` 均指向 `gateway_1:eth1`；leaf→service 端口由拓扑建立，但不会被官方目标生成器选中。底层 `gateway-config --kind loss` 通过 intent 查找指定 switch 并写共享 P4 表，静态源码未见角色限制。故 leaf/service 故障目前仅是自定义版本化任务的源码候选路径，未证明运行时可达。已同步研究章程、准入表和研究 README；当前首要门槛改为 hosted runner 验证自定义注入、目标探测和逐层事件账本。科学状态仍 HOLD。

## 2026-11-07｜将通信遥测研究问题收窄到故障耦合观测删失（无版本号变更）

继续固定在 AI Agent × 通信网络遥测方向，并将原“在线报告可见顺序”候选退为历史问题。逐行审计 pinned NIKA 0.2.0 源码：release test 有 P4 `silent_egress_packet_loss`；P4 在 INT-MX 插入后按出口端口与 packet hash 丢包；`hop_exporter.py` 只对实际捕获到的出口 INT 帧发 UDP report；collector 汇总已有报告，查询接口只返回当时 JSONL 中存在的记录。由此得到**源码级推论、尚无运行证据**：真实转发丢包可能与 exporter/collector-only 报告丢失产生相似的部分 INT trace。校正 `trace_complete` 的解释：collector 仅按 sink 是否出现及非空 hop sequence 生成该字段，不按预期拓扑逐跳核验，不能当成路径完整性证明。

查阅 LossSight 原文后确认其已覆盖 INT 丢包检测、定位、原因诊断与遥测恢复；InPatching 覆盖 INT 探测在链路故障后的绕行；TeleNoise 研究丢包/重排下的组级遥测；FaulT-Bench 覆盖网络误导工单和过度探测；TelemetrySuffBench 覆盖不同因果来源对应完全相同可见 trace 时的不可辨识与弃答。因此不主张一般遥测缺失、INT loss diagnosis、网络不可靠工单或 abstention。唯一待审问题收窄为：在固定公开视图下，Agent 是否能把数据面真实丢包与 telemetry-only 丢报告区分，并相对同信息强规则出现可复核差异。进一步核对 NIKA Agent-facing `p4rt_exec counters`：场景注册器为 P4 场景加载 BMv2 MCP server，默认诊断策略对工具和节点角色均开放；输出保留按端口 ingress/egress 计数。P4 ingress 计数在丢弃钩子前增加，egress 计数在 egress control 增加，故已知探测流的计数增量差可能构成简单强规则。NIKA test-path `silent_loss_baseline` 用 2048 个单包 UDP flow 建立隐藏 egress 映射，不能直接作为公平 Agent baseline。2% 丢包的 iid 理想化近似下，32个目标路径包至少遇到一次丢包概率为47.6%，149个约95.1%，228个约99.0%；固定 CRC 哈希使独立性尚未成立，这些数字只用于初始预算规划。`active_tcp_probe` 返回 ACK 数和总耗时，TCP 重传可能掩盖低比例丢包；`exec_shell` 是否允许 Agent 生成受控 UDP 流取决于本次诊断策略。计数规则的实际信号强度待运行验证，需逐包外部账本验证发送、接收、P4 出口、exporter 发报和 collector 收报。当前无 NIKA runtime、模型轨迹、跨任务/跨模型结果，科学状态 **HOLD**；没有调用模型 API，也未启动 Docker/WSL、未运行测试。

## 2026-11-07｜收窄在线遥测候选并完成一页研究准入审查（无版本号变更）

固定 NIKA `ac4422d8a4a03be2b905e28edf72993d467e1b81` 继续只读审计。核对 P4 `int_watchlist`、manager 写表、服务地址、Agent 工具及 benchmark 阶段顺序：遥测由匹配探测流量触发，不是后台持续生成；验证用的单次 `nc` 探测早于 Agent 阶段；Agent 可调用 `active_tcp_probe`，查询读取 collector 当前 JSONL。因此相同流量下的查询间数据增长在源码层面可设计，但必须由外部 harness 固定工作负载。collector 不记收包/持久化时间，运行时隔离与真实到达顺序尚未验证。关键修正：NIKA 原任务没有规定中途修正时限，故只凭终态 scorer 不包含轨迹时间不能称作原生评分缺陷。新增当前方向的一页准入审查：原生评分漏判主张 NO-GO；独立过程测量候选 HOLD，要求先预注册过程契约并证明它会改变有意义的模型/策略结论。未运行测试、启动 NIKA/Docker 或调用模型/API。

## 2026-11-07｜NIKA 公共 P4 轨迹子集交叉核验（无版本号变更）

下载并校验 Zenodo `NIKA Traces.zip`（MD5 与记录一致；**许可记载已于 2026-11-08 更正：未核实，见上方说明**），新增不解压归档的复算脚本与 JSON 结果。906 条 ground-truth 条目中904条有 `session_meta.json`；两条缺失记录已列出。按 P4 场景字段筛选出36条轨迹，分布在 `p4_bloom_filter` 和 `p4_mpls` 两个场景、六个故障类型、三个模型（每类每模型两次）。这些日志未记录显式名含 `int`/`telemetry` 的工具调用，且没有当前候选的末端业务包丢失/报告通道丢失因果配对。它们不能验证当前假设或替代配对运行；未重评分、未调用模型/API。完整记录：[轨迹核验报告](experiments/communication_telemetry/NIKA_PUBLIC_P4_TRACE_CENSUS_2026_11_07.md)。候选继续 **HOLD**。

## 2026-11-07｜固定 AI × 通信网络遥测研究方向（无版本号变更）

将长期研究主线固定为“大规模通信网络遥测上的可靠 AI Agent 分析与运维决策”，首个待审问题聚焦事件时间、遥测到达时间与证据新鲜度。定向查新确认 NIKA、CTBench 和 LogDx-CI 已覆盖在线网络诊断、黄金证据、成本/SLO及日志缩减等宽泛主张；不以新 benchmark、一般证据覆盖或 Token 成本为创新。新增单一研究章程和首题准入门槛；DAComp ceiling 候选转为历史暂停。当前只做 NIKA 固定版本源码/评分和遥测时间数据可达性审计，尚无源码实验、模型调用或研究 GO 决定。详见[研究方向章程](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md)。

## 2026-11-07｜NIKA 遥测双时间戳与原生评分范围初审（无版本号变更）

固定 NIKA `ac4422d8a4a03be2b905e28edf72993d467e1b81`。只读检查发现 `int_query_telemetry()` 按 `packet_timestamp` 过滤 collector 当前 JSONL 并返回原始记录，但不附独立到达时间；Agent trace 的 `timestamp` 用于整体耗时；规则 scorer 仅比较根因标签，不逐条验证遥测证据。由于工具只能读当前已写入日志，未发现未来记录直接泄漏的证据；真实 collector 写入时间、时钟精度、有效期契约和延迟分布仍待审计。仅确认评分范围边界，不确认评分错误或科研贡献。未运行测试、NIKA/Docker 或模型/API，研究状态HOLD。

## 2026-11-07｜DAComp 上游原始评分资产补查（无版本号变更）

通过 GitHub API 检查固定 DAComp 仓库公开分支、PR、tags/releases：仅有 pinned main，无 tags/releases；两个开放 PR 均未加入 DAComp-DA 原始 Judge 结果或评分矩阵。故已检查的公开上游位置没有可补用的052/063/084评分行；不外推到 fork 或作者私有产物。当前仍需独立 rubric 裁定，并取得合法原始 Judge 输出才能验证实际饱和/比较影响。无模型/API调用，研究状态HOLD。

## 2026-11-07｜公开 fork 结果资产补查与审阅协议校正（无版本号变更）

只读核对7个公开 fork 的 `main`：6个与固定官方 commit 相同；另3个基于共同祖先，其中一个仅调整 Judge 重试参数；没有发现 DAComp-DA 评分矩阵。将该有限范围写入候选门槛与审计，并把审计中仍过期的“两阶段/11候选”说明校正为当前三阶段、14候选+10对照。不是对所有分支、私有产物或外部归档的穷尽证明。无模型/API调用，盲审仍未发送，科学状态HOLD。

## 2026-11-07｜DAComp 路径 ceiling 候选的直接近邻核查（无版本号变更）

定向检索与核读 *Same Outputs, Different Scores*、RubricEval、PReMISE、RuVerBench 和 *Judging LLM-as-a-Judge*。一般 scorer-rule 敏感性、rubric 质量与 Judge 可靠性均已有直接研究；现阶段只保留“路径子项和超过父级 ceiling，是否与固定 metadata normalizer 共同造成真实分数饱和/模型比较变化”这一窄的可证伪差异。摘要/项目页未直接显示近邻已测相同层级契约，但这不能证明原创性；仍需全文逐项核验与真实同输出配对证据。候选继续HOLD，没有模型/API调用。详情见[一页研究门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。

## 2026-11-07｜DAComp 路径 ceiling 候选与盲审样本更新（无版本号变更）

在固定 DAComp rubric 中手工核对出三例路径子项和超过显式父级上限：任务052 Criterion 2.1 为4分而各路径为6分；任务063 Criterion 1.1 为4分而路径1.1.B子项和为5分；任务084 Standard 3.1 为3分而路径3.1.B为4分。固定 Judge prompt 按最佳路径子项求和，scorer 以 metadata.Total 归一化并裁剪至100；但这三题没有公开 Judge 评分，故目前只确认静态契约歧义，没有实际超额、饱和或模型排序证据。将三例加入尚未外发的盲审材料，更新为14个候选+10个固定随机对照；控制表未用于总体比例估计。路径全量解析器仅作探索性筛查；无模型/API调用，研究状态继续HOLD。详见[一页研究门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)、[评分契约审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)与[审阅流程](DACOMP_CONTRACT_REVIEW_PROTOCOL_2026_11_06.md)。

## 2026-11-07｜相关工作边界更新：Exactly-once、完成声明与数值溯源（无版本号变更）

补查近期直接相关工作：*Where Does Exactly-Once Live?* 已比较模型、harness 与 tool contract 对迟到提交、回执丢失、重投递和幂等键的作用；*OverclaimBench* 与 *Who Verifies the Agent's Success Claim?* 已研究完成声明与实际轨迹不一致以及 judge 自述泄漏；*NumTrace* 与 *DataSpace* 已覆盖数据分析数值声明的语义绑定和确定性结果验证。因此暂停将提交重试、一般完成声明差异、数值证据绑定或“可验证数据分析”重新包装为新贡献。此检索没有产生新的论文假设；DAComp rubric/metadata 候选仍需独立裁定与有代表性的配对原始结果，整体科学状态保持HOLD。

## 2026-11-07｜DAComp-DA 原始结果资产范围与 scorer 归一化复核（无版本号变更）

固定 DAComp commit `027ccaf20f0d3743d9291fd575d9bc785a5fe3db` 的 `agent_results/` 公开四个示例：英文 GPT-5 任务006/063、中文 Qwen3-Coder-Plus 任务005/006，四个均有轨迹与报告；配套 CSV 只有三条评分行，任务063没有评分行。逐题目录样例不是完整任务矩阵，英文与中文006也因语言、模型/Agent及运行配置同时不同而非受控配对。直接核对 `compute_file_score()` 证实实际分母取 `metadata.Total`，rubric总分除后裁剪至0–100；任务006公开文本同时出现标题/子标准上限20与Requirement/metadata上限16，源代码确定执行口径但不能确定公开材料中的规范优先级。两阶段盲审尚未返回；无模型/API调用。候选仍HOLD，未发现已改变模型比较的证据。详见[固定资产审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)及[一页门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。

## 2026-11-06｜DAComp 全任务状态交叉表与本地工具调用冒烟（无版本号变更）

新增可复核的80任务初态交叉表：固定 DAComp-DE revision `8c4a18983b0733256fffb593f7febb9ab6697854` 中有41个初始状态、29个应用族；12个族有多个状态，其中9个包含同状态Evol任务对和不同状态Impl单例，Salesforce有两个各含2个Evol与1个Impl的重复状态，Qualtrics与Workday则只有不同的单例状态。另17个单状态应用族的共享状态跨越Evol/Impl，但无法在应用族×任务类型固定效应之外识别状态变化。新设计矩阵审计显示，加入全部41个状态指示（其中28簇重复）后秩只从58增至59，唯一新增自由度来自Salesforce。故DAComp-DE状态血缘候选对独立论文主张判为NO-GO；这不是零效应结论。项目整体仍HOLD，未运行DAComp任务。详情见[完整门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)与[矩阵秩结果](DAComp_STATE_IDENTIFIABILITY_2026_11_06.json)。

本地安装Ollama 0.40.15并下载Qwen3 8B；通过只绑定loopback的服务完成一次 `report_probe(status=ready,count=3)` 工具调用，参数校验通过、未执行工具。模型摘要与单次响应记录在 `QWEN3_TOOL_CALL_SMOKE_2026_11_06.json`，GPU显存占用约5.28GB；本次未调用付费API或运行基准任务。固定DAComp版LiteLLM/OpenHands适配、实际DockerRuntime隔离与任务级实验仍未验证。

## 2026-11-06｜WorkBench Revisited 离线结果组成与补偿写入审计（无版本号变更）

固定 2026 WorkBench Revisited item-level 结果（16,560 行、690 任务、24 模型、69 模板簇）重算完成率、无条件副作用率与失败条件副作用比例。相关方向由强负向变为弱正向，但条件比例是论文已展示三类结果组成的确定性重表达，区间跨零，故不作为独立贡献。进一步发现10条主评分为正确/无副作用、gold无写入、轨迹创建后删除新记录的结果；覆盖8个任务、4个模型。它们是本地模拟状态的中间写入，不是现实外部伤害；完整输出另有 `exact_match=False` 诊断。与近期 SABench 的 trace-authorization oracle 高度接近，候选仍 HOLD，未做第二基准或模型调用。分析脚本与证据边界见[审计报告](WORKBENCH_OUTCOME_AUDIT_2026_11_06.md)和[一页研究门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。

## 2026-11-06｜隔离实验授权后的运行准备复核（无版本号变更）

用户已授权准备 WSL2/Docker；实际启动在 Docker backend 创建 `dockerInference` socket 时失败，现有路径为不可访问的旧 reparse point，WSL 同时报 `HCS_E_SERVICE_NOT_AVAILABLE`。没有启动容器、任务或模型，没有启用 Windows 功能或重启，Docker 设置已恢复并逐字节校验。另确认本机没有模型缓存和可用推理依赖。由于后续需系统级虚拟化设置且本机曾出现 `HYPERVISOR_ERROR`，不把授权准备隔离环境等同于授权重启；当前 no-run，科学状态 HOLD。详见[DAComp 状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。

## 2026-11-06｜近期基准有效性近邻复核（无版本号变更）

补充核读 arXiv:2610.16067v2 与 arXiv:2611.02978。前者已实证 oracle-integrity auditing 可纠正一个基准的成功率及模型比较，后者已进行多轮工具调用中的破坏性调用、重复写入和额外步骤的确定性轨迹评分。它们进一步排除了 FaultDA 将一般评分器完整性或终态—轨迹差异包装为独立贡献的路线。唯一保留候选仍是 DAComp-DE 精确起始数据库状态血缘是否在 task/template 条件化基线之外解释结果依赖；该问题尚无逐题模型结果。引用与边界已加入[状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)及[WorkBench 离线审计](WORKBENCH_OUTCOME_AUDIT_2026_11_06.md)。

同轮补查 DataWorld-Bench：每个 held-out world 有 cause/consequence 两题，论文 Appendix A.3.4 已按 world 配对并报告 paired MDE，A.5.2 对训练前后系统也按相同 task name 配对。此举否决“首次采用共享环境配对/聚类”的宽泛主张。官方 repo tree 仅列引擎、文档、示例和测试，没有逐题模型结果；公开表为汇总值。剩余候选被收窄为 DAComp 完全相同的初始数据库跨 task ID 重用是否在常规配对与 task-family 控制后仍解释残差依赖并改变预注册推断。DataWorld 暂作结构性外部对照，不下载其 50.7 GB 全集，也不以汇总表反推逐题结果。详见[状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。

再用官方 GitHub API 核对 DAComp 与 Data-World 的 releases 和固定 DAComp DE tree：两仓库均无 release；7,263 项 DAComp tree 中的结果文件只对应 DA 示例轨迹与 DA judge 分数，DE 部分没有逐题预测矩阵。由此关闭“官方 release 里另有未入树结果包”的检索支线；仍保留外部未索引/私有文件的可能性，不将未找到写成不存在的绝对结论。

## 2026-11-06｜DAComp-DE 历史结果资产与 CUDA 隔离路线补查（无版本号变更）

固定官方 Hugging Face `DAComp/dacomp-de-gold` revision `11f04f026f67ae9dfaabdc0aa9a6f10f70661d08` 并读取完整文件清单：只有 gold 压缩包（2,987,710,403 bytes）及仓库元数据，没有历史逐任务模型输出。复核官方 ICLR 2026 论文中的 DE 指标定义与结果章节，确认已查部分提供任务级指标公式和聚合结果，但未提供完整 task × model 矩阵；结论不排除未索引补充材料或私有记录。确认 WSL1 不适用于当前 CUDA 路线；依据项目执行门槛，没有启动 WSL2/Docker、安装发行版或保留先前下载尝试。状态血缘假设仍 HOLD，实证未决；后续必须取得可审计历史结果，或在获得明确授权后做隔离的小型本地配对运行。详见[状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。

## DAComp-DE runner 与安全隔离准入边界 — 2026-11-06

核实官方 DE Agent quickstart 支持指定任务 ID、任务类型与实验名，并将单 Agent 结果写入按任务类型区分的输出目录；配置有 `base_url`，但示例只明确展示 `azure_raw`，本机端点兼容性未验证。对固定 DAComp Git tree `027ccaf20f0d3743d9291fd575d9bc785a5fe3db` 的 runner、runtime registry 与 CLI runtime 源码追踪后，确认 DE `get_config()` 选中 `runtime='cli'`，映射到 `CLIRuntime`，由本机 subprocess 执行命令；同一 SandboxConfig 内的 `sysbox`/远程 API 字段不能证明该 CLIRuntime 隔离。故官方 runner 原样运行会在宿主机执行 Agent 生成的任务代码，暂停该实跑路径。源码中存在 `DockerRuntime`：DE 会先把题目文件复制到每题输出 workspace；Docker runtime 只挂载配置的 workspace（需核对额外卷），默认不是 host network，但 bridge 网络仍可能出站。切换配置可能只需改 runtime 字段，但任务兼容与行为等价尚未验证；该变化须登记为实验条件。针对80任务/41簇做标准化配对均值差的假设情景灵敏度计算：状态内ICC从0到1时，近似80%功效所需差值约0.32–0.48 SD；该计算不等于真实功效，也不检验主假设的残差依赖和决策变化。当前未发现常用本地模型服务进程或标准 API 端口监听；没有安装模型权重、推理依赖或启动容器。因本机此前发生过 HYPERVISOR_ERROR，不自行启动 Docker/WSL/虚拟化。详见 [DAComp 状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。

## 2026-11-06｜DAComp-DE 本地实跑准入检查（无版本号变更）

对当前本机进行无模型的环境检查：RTX 5070 Ti Laptop 可见、12,227 MiB VRAM、驱动报告 CUDA 13.1，C: 约558 GB空闲；但缺少 PyTorch/Transformers/vLLM/llama.cpp/DuckDB/Hugging Face Hub，WSL 仅有 docker-desktop 发行版，Docker daemon 不可用。记录说明硬件可见不等于隔离实验可执行；没有安装依赖、下载任务/模型或运行模型。DAComp-DE 状态血缘假设仍需 task × model 配对输出，当前实验门槛未通过。[状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)

## 2026-11-06｜扩展 DAComp-DE 逐题结果资产检索（无版本号变更）

在既有官方 Git 树、leaderboard 与文档检索之外，检查 DAComp 官方 Hugging Face `dacomp-da-eval` 固定提交 `9702386a7b6da0cc06c730b5fc81e927b5188305`。任务目录展示参考图、instruction、metadata 与 rubric，未发现历史模型输出矩阵；其范围是 DA 子集，不能提供 DE 结果。此举扩大了“公共来源中尚无可用逐任务结果”的已查证范围，但不排除未索引或私有材料，也不构成假设的反证。DAComp-DE 状态血缘候选仍 HOLD，下一步需可审计的配对输出或单独准入的新运行。没有数据集全量下载、模型运行或 API 调用。详情见[状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。

## 2026-11-06｜三条公开评分记录的分母敏感性复算（无版本号变更）

对固定版英文 GPT-5 与中文 Qwen3-Coder-Plus 三条 CSV 记录保持 Judge/GSB 输出和官方权重不变，仅以 rubric 顶部总分替代 metadata `Total` 重算：英文006为45.50→38.00（-7.50），中文005为40.7143→32.5714（-8.1429），中文006为17.00→14.00（-3.00）。这些是条件敏感性值，标题分母均未获独立裁定，不是“修正分”；只有英文006直接显示 rubric 1.6/1.7额外计入raw分子。修正一页门槛残留的“仅一条真实计分行”旧表述，限定为三条公开记录、两项任务ID，其中一条支持该具体观察。无模型/Judge调用，科学状态仍HOLD。详见[固定资产审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)。

## 2026-11-06｜补查中文评分资产并扩展逐题证据边界（无版本号变更）

递归检查固定DAComp树时发现 `model_scores_zh/` 此前未纳入英文目录清点：新增发现Qwen3-Coder-Plus两条原始评分记录（`dacomp-zh-005/-006`）。固定发布物现确认为3条评分记录、两个底层任务ID，而非全库仅一个评分行。`zh-005` 的metadata28与Requirement合计28一致，rubric标题35且标准1.2上限高于其所属Requirement，但记录raw19尚未超过分母；`zh-006` 与英文006为对应中英任务，Qwen raw4且1.6/1.7均未得分。由于语言、模型与任务版本共同变化，这不是受控配对复现。仅英文GPT-5 `dacomp-006` 实际出现rubric 1.6/1.7共4分计入raw numerator而metadata类别上限未涵盖的观察。现有证据扩大到3行但仍无完整矩阵、独立权威裁定或排序结论，科学状态继续HOLD。更正范围见[DAComp固定资产审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)、[跨基准筛选](SCORE_CONTRACT_IDENTIFIABILITY_SCREEN_2026_11_06.md)、[一页门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)与[README](README.md)。

## 2026-11-06｜DAComp-006 分子/分母冲突的逐项复核（无版本号变更）

依据官方 DAComp 论文 §2.2 的 rubric 归一化定义、固定 Judge prompt、`dacomp-006` rubric/metadata 与唯一公开评分行，发现候选不只是静态上限不同：Judge 实际将 criterion 1.6、1.7 各2分计入 raw rubric=10，而metadata类别上限 `4+7+5=16` 与前五个criterion对应；原生 scorer 仍以16作分母。该任务标题/criterion总上限20、Requirement与metadata16；按输出选择的路径推导的19仅作敏感性口径。相同输出下原生45.5，分母20时38.0、分母19时约39.58；两种替代值均未获规范裁定。将一页门槛改为检验真实“分子项目—归一化分母”一致性，并强化盲审问题。没有模型/API调用或新实验，独立贡献仍HOLD。详见[固定资产审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)、[跨基准近邻筛选](SCORE_CONTRACT_IDENTIFIABILITY_SCREEN_2026_11_06.md)及[一页研究门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。

## 2026-11-06｜评分契约主张的新颖性降级与边界收窄（无版本号变更）

全文审查 *Do Agent Benchmarks Do What They Say?* 与 *Measurement Risk in Supervised Financial NLP* 后，撤销“通用评分契约可识别性审计方法”作为潜在独立方法贡献的表述：前者已追踪工具契约、实现到 evaluator score provenance，后者已检验 rubric/metric/aggregation 敏感性及排序稳定性。仅保留一个 DAComp-DA 经验候选：rubric 上限与 scorer metadata 分母是否存在盲审后仍无法消解的规范冲突，且对固定逐题输出的合法解释是否改变预注册比较并超过 Judge 波动。为避免泛称敏感性分析，进一步定义共同任务解释下的配对比较识别区间；该 estimand 只是待审设计，不是方法贡献。该候选尚未通过独立审阅或配对结果验证，科学状态继续 HOLD；没有模型/API调用、基准运行或测试。更新见[直接近邻与候选边界](SCORE_CONTRACT_IDENTIFIABILITY_SCREEN_2026_11_06.md)、[一页研究门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)与[研究线说明](README.md)。

## 2026-11-06｜评分契约可识别性跨基准筛选（无版本号变更）

检查 FDABench、KramaBench 官方代码与数据格式，固定代码快照并区分结构性阴性对照和候选阳性案例；未发现与 DAComp 同构的 rubric/metadata 分母分离路径。将潜在研究概念收窄为评分契约可识别性：由盲审裁定允许的规范解释集合，再检查冻结逐题分数下的预注册模型比较是否稳健。新增跨基准筛选说明与可证伪假设，记录在[一页研究门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)及[跨基准筛选报告](SCORE_CONTRACT_IDENTIFIABILITY_SCREEN_2026_11_06.md)。本轮只读文献/代码审查，无数据集运行、模型/API调用或论文贡献声明；研究状态 HOLD。

## DAComp-DA rubric/metadata 计分契约离线审计 — 2026-11-06（无版本号变更）

固定官方树中筛查 100 题 rubric 与 metadata，标题解析覆盖 95/100、Requirement 最大分解析 89/100；对发现的 11 个来源冲突候选回看原文。实时核验发现上游 main 与固定 SHA 仍完全一致，Issue #11 仍开放且无维护者澄清。原生 scorer 以 metadata `Total` 归一化并裁剪到 0–100。唯一公开评分行 `dacomp-006` 按 rubric 标题20分而非 metadata/Requirement 16分重算时，总分条件性地从45.5变为38.0；按候选分母替换计算的最大敏感性上界为1.54–27.27总分点，均非观测效应。分值权威尚未裁决，且没有任务级多模型矩阵，故不称为评分错误或论文贡献。新增固定来源、11项明细、解析限制、近邻边界和后续否证门槛；无模型/Judge API调用。详见[审计记录](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)与[一页研究门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。

补充准备两阶段人工复核包：固定样本含11个候选与10个固定种子随机对照；Stage 1 只审 rubric，锁定后 Stage 2 才显示 metadata。两份 CSV 与逐阶段交接规则已生成；尚未发送给审阅者，未有人审结论。详见[盲审流程](DACOMP_CONTRACT_REVIEW_PROTOCOL_2026_11_06.md)。

继续沿着原候选核查代码输入边界：Judge prompt 只由任务 `rubric.txt` 构造，prompt 把 rubric 总分定义为最高分、最终分为各 Requirement 得分之和；评分程序却从 `metadata.json` 读取 `Total` 作归一化分母并裁剪。这将候选从“文本字段不一致”收窄为**Judge 规范来源与 scorer 执行来源分离**；不过 rubric 本身也可能内部冲突，权威分值仍需独立审阅，跨模型影响未验证。逐文件清点所有官方英文 `model_scores/*.csv` 后确认只有 `dacomp-006` 一条任务评分行，暂无排名变化分析所需矩阵。两阶段盲审包已准备，尚未送审；无模型/Judge API调用。源码入口见[固定资产审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)与[外发用说明](DACOMP_REVIEWER_BRIEF_RUBRIC_ONLY_2026_11_06.md)。

使用11项候选分母替换上界，对公开 DA-Agent Table 5 做条件性排名影响审查：单模型100题均值最大改变量≤1.318分；因同一任务对所有系统的分母修正方向相同，任意模型对差变化同样≤1.318分，小于最低相邻间隔7.19分。故已知11项不足以改变 Table 5 排序或解释 Issue #11 所报约10–11分重跑差。此为受 parser 未覆盖任务限制的否定性边界，不能代表100题完成审计。关闭“已知错配解释 DA-Agent 排名/重跑差”的窄主张；契约可识别性是否能独立成文仍 HOLD，需盲审与跨基准增量。无模型/Judge API调用。详见[条件性影响上界](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)。

## DAComp-DA 固定发布物覆盖范围修正 — 2026-11-06（无版本号变更）

递归清点固定官方代码树，发现两个 GPT-5 示例输出（dacomp-006、dacomp-063），以及只含 dacomp-006 一行的评分 CSV。该任务的原始答复、轨迹、逐维评分与 rubric/GSB 输出可连接；按公开权重离线复算得到 45.5，与 CSV 一致。因此修正“没有任何逐题评分”的过宽说法：准确边界是仅有一条已评分英文 DA 任务，不覆盖论文 Table 5 的 100 题均值，也不是 Issue #11 两次重跑的任务级产物。此单任务算术复核不支持差异归因或独立贡献，候选仍 HOLD；没有模型 API 调用。

## DAComp-DA 方差定义与汇总代码核验 — 2026-11-06（无版本号变更）

继续核对 Table 5 `±` 的定义：论文明确将 Table 10 的 8 次评分限定为固定 Agent 输出上的 Judge 稳定性实验，但没有说明 Table 5 多个 `±` 的抽样单位或运行次数。固定源码 `rubric_scoring.py` 与 `get_score.py` 只计算/写出均值和样本数，不产生 Table 5 的标准差；这不能排除作者另有未公开汇总脚本。Issue #11 所报 61.08/62.14 与论文中心分差因此仍无法归因于任务、Agent、Judge 或配置来源。候选依旧 HOLD，新增这一来源核验到一页门槛与 README；没有真实模型调用，未把报告包装成复现失败或独立贡献。

## DAComp-DA 重跑差异候选门槛 — 2026-11-06（无版本号变更）

审查公开 Issue #11 对 Table 5 GPT-5/DA-Agent 得分的两次重跑报告，并与论文固定输出上的 8 次 Judge 稳定性、跨 Judge 排序分析、Judge 同输入重复评分研究、通用 LLM 基准重复实验和 Agent 评测重放近邻对照。固定公开代码快照确认当前 Agent 与 Gemini Judge 的默认参数，但不能证明这些设置等同于历史 Table 5 运行；issue 仍开放、无作者确认，也没有逐任务原始产物。故该差值只能作为候选线索，不能称为已复现分差或评测缺陷。新增一页可证伪门槛：严格复现条件、区分 Agent/Judge/配置来源、跨模型比较及关闭条件均须先明确；未批准或执行任何模型/API 调用。详见 [一页研究设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。

## DAComp-DE 结果资产核验 — 2026-11-06（无版本号变更）

在官方 DAComp 仓库固定树 `027ccaf20f0d3743d9291fd575d9bc785a5fe3db` 中核查 `dacomp-de/`，未找到逐任务模型结果或基线分数文件；可见的模型轨迹与评分 CSV 属于 DAComp-DA，不支持当前 DE 起始数据库血缘问题。公开 leaderboard 仅提供类别汇总。因而没有可直接开展的离线结果分析，状态血缘候选维持 HOLD；不从汇总值推算任务分数，也不以单系统新跑充当论文证据。下一步需取得合法的配对 `task × system × run` DE 结果矩阵，否则需另行审批并预算配对运行。详见 [状态血缘候选门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。

## LongDS v1.1 更新后的复核入口 — 2026-11-06（无版本号变更）

补查 LongDS 官方 v1.1 更新：新版修订任务语义并提供 24-task/777-turn Lite 与逐轮结果输出运行器；公开榜单是不同原生 Agent 框架的聚合成绩，未发现论文 reset 对照的逐任务原始成绩或运行轨迹。因此旧 reset 候选仍不构成独立贡献；若未来重开，需在 v1.1 上用独立前置状态测量、随机化重置时点和同预算三臂对照重新实证。详见 [LongDS 重置条件化诊断](LONGDS_RESET_CONDITIONING_DIAGNOSTIC_2026_11_06.md)。

## DCR 候选的公开复现资产核验 — 2026-11-06（无版本号变更）

检索发现一个未由论文链接、也未证实与作者有关联的 StateGuard 源码与测试仓库；它未声明许可证，也没有逐任务结果或运行轨迹，基线 runbook 中的完整基准生成需要配置模型 API。故它只作为未验证工程线索，不填补 DCR 支持集分解所需数据，也不据此运行付费复现。DCR 跨系统支持集可比性仍 HOLD；详见 [DCR 研究门槛](DCR_CAUSAL_VALIDITY_GATE_2026_11_06.md)。

## DCR 共同支持方法基线复核 — 2026-11-06（无版本号变更）

复核 arXiv:2609.07785v1 后确认，它已系统覆盖 Agent 比较中的 estimand、共同支持、目标标准化、任务簇不确定性与排名变化；G-theory 近邻也处理了任务/benchmark/scaffold 方差异质性。因此 DCR 候选仅剩“系统运行后父节点错误/缺失导致的 DCR 组成员迁移，是否在成对运行中改变 DCR 结论”这一待测边界；还必须与普通标准化/分层分解比较。没有真实逐任务轨迹，故仍 HOLD，不声称独立贡献或运行 API。详见 [DCR 研究门槛](DCR_CAUSAL_VALIDITY_GATE_2026_11_06.md)。

将 DCR 成员迁移问题整理为一页候选门槛，固定问题、事实动机、最强比较基线、否证条件、双任务族要求和当前运行条件；候选仍 HOLD，未运行模型/API。详见[一页研究设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。

## AppWorld 147 条重放与直接近邻审查 — 2026-11-06（无版本号变更）

将 147 条历史重放结果与 *Re-executing Coding-Agent Evaluations* (arXiv:2610.14460v1) 逐项对照：该文重跑 1,929 条 SWE-bench 归档评测并检验最佳系统选择/组别排名，虽有 23 条记录分歧，两项预设决策均未改变。AppWorld 的 51/76 保存通过转离线重放失败仍是单一 GPT-4o ReAct 血缘，且其零哈希判断已有 AppWorld issue #218 / PR #219 报告。故归档重放的一般主张和 AppWorld 具体机制均不作为独立贡献；保留为工程复现结果，科学状态 HOLD。

启动了 147 条 PR #219 条件适配扩展，但约 7 分钟仅推进至第 4 个复杂任务，单个任务反复触及 120 秒超时。由于该扩展只重复一个已知上游条件，且不能改变缺少第二模型、排名结论和独立违规裁决的事实，停止了该新增运行；没有全量适配结果。原始 147 条重放与此前四例适配对照保持不变。

## DAComp 状态血缘候选的近邻边界复核 — 2026-11-06（无版本号变更）

复核 DAComp 原论文 §7.4：其评测已报告人工与 LLM 评分器的 item-level、case-level ICC(A,1) 和 model-level Kendall's tau-b 排名一致性。因此不得把一般评分可靠性、名次一致性或任务不确定性包装成本研究贡献。官方 leaderboard 与论文检查范围未提供本候选所需的完整逐任务、逐模型结果矩阵；官方评测器可在固定新运行中导出逐任务 scores.csv，但新跑结果本身不证明新颖性。保留唯一窄候选：精确初始数据库 SHA-256 血缘是否在最强任务条件不确定性方法之外解释额外结果依赖，并改变预设模型比较。当前无模型运行栈，安全隔离路径未解决；未运行模型或基准，科学状态 HOLD。

## 数据库状态血缘候选与近邻复核 — 2026-11-06（无版本号变更）

对固定 Hugging Face revision `8c4a18983b0733256fffb593f7febb9ab6697854` 的 DAComp-DE ZIP central directory 做范围读取，没有下载完整 2.27 GB 数据包。发现 50 个 evol 与 30 个 impl 任务共 80 个任务 ID，按数据库文件名、归档 CRC32 与解压大小归并为 41 个初始状态签名；初步核验时仅一组跨类型数据库完成 SHA-256 校验。50 个 evolution 任务的问题索引里，共享状态的 20 对任务都有不同题面；简单词集合 Jaccard 为 0.205–0.356，仅是探索性文本筛查。该结构提示外推到新数据环境时应检查任务内相关性，但不说明固定任务集分数有错，也没有模型结果证明置信区间或排序会变。

复核 DAComp-DE 每任务平均的原生指标定义，并查阅 Agent Evaluation Reliability 的任务层级方差分解；后者是强近邻，通用聚类推断本身不能作为新颖性。新增状态血缘候选门槛，状态仍 HOLD；下一步仅查逐任务公开基线结果和补齐重复状态 SHA-256 清单。未调用模型/API、未运行基准、未安装环境、未推送。详见 [状态血缘候选门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。

进一步逐节复核 arXiv:2609.07785《What Does an LLM-Agent Leaderboard Rank Actually Compare?》。该工作已明确处理 estimand、任务条件/分组重采样、配对系统差异及不确定性；它没有单独建模精确数据库状态血缘，但这使通用“任务簇不确定性”主张更难成立。官方 DAComp-DE 评测说明允许从新模型输出导出每任务 `scores.csv`，所以缺少公开历史矩阵并非不可逾越的数据障碍；但跑一个新模型只会生成案例数据，不足以证明贡献。将研究问题收窄为：数据库状态血缘能否在任务条件基线之外解释残余依赖并改变预设比较。维持 HOLD；未下载大包、未安装运行器、未调用模型/API、未运行测试或推送。详见 [状态血缘候选门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。

后续通过固定 revision 的 HTTP Range 请求读取所有重复签名对应的 67 个起始数据库成员，合计 373,718,692 字节压缩数据；逐个检查解压长度、CRC-32 和 SHA-256，28 个重复状态组全部字节一致。由此确认 80 个任务 ID 的 41 个起始状态中，28 个状态被复用到 67 个任务 ID，另有 13 个单例状态。脚本 [da_comp_state_lineage.py](da_comp_state_lineage.py) 与哈希清单 [DAComp_START_STATE_SHA256_2026_11_06.json](DAComp_START_STATE_SHA256_2026_11_06.json) 保存复核方法和结果；没有将数据库落盘。来源结构证据已完成，但仍没有逐任务模型结果，也就没有依赖效应或模型结论变化的证据。近邻与方法边界不变，科学状态 HOLD。

## DCR 复现实验路线与来源审计更新 — 2026-11-06（无版本号变更）

补齐 DCR 支持集候选的可行性证据：发现 `bmbgsj/StateGuard-RL` 有公开 Qwen3 8B BF16 checkpoint（约 16.4 GB），但无模型卡/许可证且与论文作者身份未验证；本机 GPU 约 12.2 GiB，不能原样常驻。DAComp-DE 的官方代码与 Hugging Face 数据卡标注 MIT，官方 CFS 评测器能输出逐任务、逐表结果，可作为第二基准候选；LongDS 仍要求遵守 Kaggle 来源规则。增加了明确标注为合成的 DCR 支持集混合反例：同样的分层父错误关联差可产生反向的聚合 DCR，证明数学可能性但不是基准实证。本机未安装 PyTorch、Transformers、Hugging Face Hub 或本地推理服务，尚无直接实跑环境。

研究状态仍 HOLD；未证明任何已发表比较实际受构成影响，也未下载数据或权重、未调用模型/API、未运行测试、未推送。详见 [DCR 支持集门槛](DCR_CAUSAL_VALIDITY_GATE_2026_11_06.md)。

## DCR 指标解释与可比性准入复审 — 2026-11-06（无版本号变更）

将“DCR 因果效度”主张降为 NO-GO：StateGuard 把 DCR 明确定义为观测关联差值，因此仅指出它不是随机化因果效应，不构成对其原定义的反证。进一步登记一个更窄、尚未证实的候选：不同系统的 DCR 比较是否受模型特异的父节点正确性与可评分支持集变化影响。该候选仍为 HOLD，当前没有独立贡献或实跑资格。

核对 StateGuard §4.3/Appendix C.4、论文页面和同名公开仓库；未发现论文作者链接的逐任务轨迹复现资产。LongDS v1.1 Lite 有 24 任务/777 轮，但官方卡标注许可证 `other`，要求遵守相关 Kaggle 竞赛规则。当前工作区没有这些任务运行资产。本轮没有下载数据、调用模型/API、运行测试或推送。详见 [DCR 因果效度与支持集审查](DCR_CAUSAL_VALIDITY_GATE_2026_11_06.md)。

## LongDS 重置效应的基线条件化诊断 — 2026-11-06（无版本号变更）

**[事实]** 对照 LongDS-Bench v3 §5.3 / Appendix C.7 后，修正上一条候选：LongDS 已研究 reset 与 persistent，并按 persistent accuracy 分层、用基线表现选择重置轮次；AFT-Bench 也覆盖提交后丢回执。因此“回执丢失 × 分析状态依赖”不再作为新颖性主张。

**[推断]** 新的高风险候选是恢复效应的基线结果条件化/干预时点选择敏感性。完成了一个零真实效应、等方差联合正态的解析诊断：以同一 persistent outcome 分层并计算 reset−persistent 差值，会机械地产生低基线组表观改善、高基线组表观退化。该计算仅证明统计机制可能出现，不是 LongDS 数据重分析，也不证明其结论有偏。

检查固定 DataMind 源码快照的 GitHub 文件树，仅找到论文图表，没有逐任务两臂分数或原始运行日志；这不排除数据发布在其他位置。科学状态仍为 HOLD；没有模型/API 调用、底层数据下载或测试运行。详见 [条件化诊断](LONGDS_RESET_CONDITIONING_DIAGNOSTIC_2026_11_06.md) 和 [更新后的研究设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)。
## Research direction search — 2026-11-06 (no version bump)

Reopened direction search at the user's explicit request to pursue an independent paper contribution. A bounded arXiv screen found close neighbors in benchmark maintenance and leaderboard regrading (Terminal-Bench continuous validation; Silent Instrument Errors), long-horizon analytical state evolution (LongDS), tool-effect recovery (AFT-Bench), process-level analysis evaluation (DataClawBench), and verifiable heterogeneous analytics (DataSpace). No novelty claim is made from combining these areas. A single falsifiable candidate now asks whether post-execution/lost-response faults interact with downstream analytical-state dependency depth. The one-page gate allows only source/artifact feasibility review; the candidate is not yet an independent contribution and the study remains HOLD.

Inspected DataMind source snapshot `a814927159470ad1624602d233f57b7c0be5882e`: the LongDS judge scores each turn's question, reference answer, and text solution, not the execution state; `MultiTurnReActDSAgent` retains one `AllocatedCodeEnv` per task, and the environment returns execution exceptions as agent-visible observations. This identifies a client-boundary fault adapter that could hide a successful tool response without changing the task or judge; actual implementation, hidden-state audit, and wire-level fault behavior remain untested. A metadata-only fetch of the 24 LongDS v1.1 Lite task JSON files confirmed 777 turns; a simple phrase scan found explicit prior-task references in four task files only, leaving the other task dependency structures unknown. The official LongDS dataset snapshot `6b448459c333ecc050a2e89fcc65c0e044d763ac` reports license `other`, use restrictions tied to source datasets/competition rules, and educational/research use; no underlying dataset was downloaded. Local CLI checks found Docker and the NVIDIA utility entry point but no Hugging Face/PyTorch/Transformers runtime. No paid model-provider API calls, agent runs, test suite, dataset download, or push. See the [updated one-page design gate](ONE_PAGE_RESEARCH_DESIGN_GATE.md).

## Research audit correction — 2026-11-06 (no version bump)

Refined the τ²-bench airline task-2 review using policy text embedded in the published trajectory. The episode records native reward 1.0 with `reward_basis=[DB, COMMUNICATE]` while two stored NL assertions are false; the policy says not to proactively offer compensation and restricts delayed-flight certificates to a change/cancel flow. The archived task predates the later v1.0.1 rewrite; upstream Issue #384 lists the later T2 among reward-basis omissions. A static comparison of v0.1.0 to v1.0.1 found selected contract-field changes in 29/50 airline tasks and 114/114 retail tasks, including the effective reward-basis migration after normalizing the old schema default. Together with the existing upstream audit, Liu's evaluator-version regrade study, and Inspect Evals versioning guidance, this closes task-version drift as an independent paper claim; version pinning remains an engineering requirement. No historical scorer rerun or ranking effect was estimated. Updated the task-2 review and manuscript evidence map; NO-GO/HOLD remain, with no model/API call.


## Research audit note — 2026-11-06 (no version bump)

Preliminary review of a published τ²-bench airline trajectory suggested that an early “Sure” answering a request for the user's ID might be carried forward to a later $50 certificate write. The follow-up recovered the run-time policy text and reward metadata embedded in that trajectory, which point instead to an unscored compensation-policy assertion; the exact historical source commit remains unavailable. This preliminary consent-binding interpretation is superseded by the correction above. No prevalence estimate or API call. See [revised task-2 review](TAU2_TASK2_SCORING_BASIS_REVIEW_2026_11_06.md).


## Research update — 2026-11-06 (no version bump)

Reanalyzed the published τ²-bench retail/airline archive with an independent event-order implementation. It reproduced the prior report's 11/1,755 native-pass and 13/869 native-fail confirmation-before-mutation flags. Removing the 11 pass flags did not change observed result-group order within either domain. Because the same policy discrepancy and monitor were already publicly reported, this closes the current candidate as a standalone novelty claim (NO-GO); scientific status remains HOLD. The archive has configuration and source-commit differences, and labels have no independent human adjudication. Updated the venue-neutral manuscript to distinguish both AppWorld and τ²-bench offline reanalyses from new executions. No model/API calls or push. See [the reanalysis report](TAU2_RANKING_REANALYSIS_2026_11_06.md), [design gate](TAU2_RANKING_REANALYSIS_DESIGN_2026_11_06.md), and [paper draft](PAPER_DRAFT.md).

# Reliability Reset releases

## Research decision — 2026-11-05 (no version bump)

Compared the four archived AppWorld 0.1.0 replay cases against prior work and an adaptation of the zero-counter guard proposed in upstream PR #219. In unmodified replay, two saved passes became failures; both saved failures remained failures. The adapted scorer matched saved passed and failed requirement labels for all four without synthetic change markers; this is neither the full upstream PR nor historical-runtime reconstruction. The related zero-counter mechanism was already reported upstream, and closer published studies address evaluation and regrading validity. The present mechanism is NO-GO as a standalone paper contribution; scientific HOLD remains. The working manuscript now incorporates the blind review and distinguishes saved-score reproducibility from original false-success claims. A supplementary encrypted control package enables local rechecking. No new task, model call, or original-score modification. See [the research decision](APPWORLD_REVIEW_2026_11_02.md).

## Research evidence update — 2026-11-03 (no version bump)

Recorded two independent human blind reviews and three auxiliary AI reviews of four stratified historical development cases. Both confirmed task conflicts were caught by the saved native full score; the two native-passing cases showed no violation in the reviewed scopes. A same-version 0.1.0 replay matched one of four saved reports using archived state alone. A paired, synthetic state-change marker control restored matching passed and failed test names for all four, without recovering historical runtime metadata. The sample cannot estimate a miss rate, historical dependencies remain unknown, and the scientific claim stays HOLD. Published a de-identified, encrypted evidence bundle and retained raw reviews privately. See [the review and replay](APPWORLD_REVIEW_2026_11_02.md).

## 1.1.05 — 2026-11-01

Continued the interrupted AppWorld train-scenario pilot. DeepSeek Flash, Qwen2.5-0.5B and an exploratory Granite 4.0-350M each received six native scores without a pass; a guarded SmolLM2-360M run also received six scores, with five censored by a 2,000-input-token limit. These arms are not an equal-budget ranking. Completed the interrupted sixth DeepSeek public-schema run, preserved all retries and partial journals, and exported a payload-free per-call cost ledger. Two exploratory extended runs had supervisor status `success` but failed full native scoring; both scores matched fresh-process replays. This does not demonstrate that native scoring missed a violation. Strong-rule controls, independent safety adjudication, representative held-out tasks and a valid missed-violation estimate remain unavailable; scientific HOLD remains. See [the study](APPWORLD_PILOT_115.md).

## 1.1.0 — 2026-10-31

Investigated the local model's template-opened thinking segment without changing the frozen 1.0.95 parser or reclassifying its outputs. Two controlled format preflights still produced no accepted action. Downloaded Qwen2.5-0.5B-Instruct and SmolLM2-360M-Instruct, verified their weights against upstream LFS metadata, and ran one original AppWorld train task per model under the existing structured interface and budget; both failed the native task score. Reconstructed an accessible INT4 model from an existing DPO-merged FP16 checkpoint, retained the initial GBK logging failure, and verified NPU generation with a 16-token limit. This is one task and four checkpoints, not four independent model families; no strong baseline, independent safety labels or paper claim is established. See [the study](APPWORLD_PILOT_110.md).

## 1.0.95 — 2026-10-30

Ran a bounded AppWorld 0.2.0 train-task interface pilot with DeepSeek Flash and the locally available DeepSeek-R1-Distill-Qwen 1.5B on CUDA, plus a no-action weak control. Both models failed to complete the task within eight turns; the local model exhausted all eight output limits. Captured protected request/response and usage records, corrected AppWorld's frozen process clock for real timestamps, and reproduced all three native scores in fresh processes. Intel NPU graph execution succeeded; the prior INT4 model files were not readable, so no NPU LLM result is claimed. One task and two related checkpoints are not a cross-model study; safety labels and the strong baseline remain pending. See [the pilot](APPWORLD_PILOT_195.md).

## 1.0.90 — 2026-10-28

Reused the official AppWorld 0.1.0 GPT-4o/ReAct train and dev outputs, matched all 147 tasks to their original split lists, and separated task-level native scores from scenario-level scores. All 76 native-passing runs have unadjudicated side-effect status; the archives lack the specified provider log and do not establish actual token cost. Added an inventory for the two permitted development splits, explicit unknown-aware bounds and a focused test set. No new model call, independent safety labeling or cross-model estimate. Scientific HOLD remains. See [the results and experiment plan](EVALUATOR_GAP_190.md).

Prepared and locally checked an encrypted four-scenario development review packet, with native scores and the mapping kept outside the reviewer package. This is a feasibility sample, not a completed review or prevalence study.

## Repository maintenance — 2026-10-28 (no version bump)

The root and component READMEs now link to grouped historical and branch guides; the original reports and frozen evidence remain in place. The terminal-taxonomy command defaults to read-only output and refuses to overwrite an explicit output. A separate offline audit entry can write to a fresh `work/` subdirectory while leaving the frozen CI runner intact.

Rechecked the DEV-SEEN cohort selection, 0.5.66 price comparisons and terminal classifications against the recorded data; corrected their scope without changing the historical figures. Added the direct CostBench and CAM-DF comparisons and a bounded, unexecuted external-pilot design. The Windows checkout rules now preserve the expected LF bytes of 14 historical files.

Previous verification covered 84 focused checks in a clean Windows-style checkout, all 717 current or archived v48 paths, and byte-identical outputs from the default and fresh-directory offline audits. No new model calls or independent-task results were produced; the scientific status remains HOLD.

## Terminal taxonomy — 2026-10-27 (no version bump)

Read all 60 committed 1.0.35 executions as one population for the first time: 24 hit the one-check cap, 3 escalated, and no false completions, wrong publications, duplicate events or forbidden effects were recorded. Twenty-two of the 27 incomplete runs had a correct terminal record. The 48 model runs score 43/48 (89.6%) on record correctness and 21/48 (43.8%) on safe completion. All 60 used the same one-check cap, so the effect of changing the cap is not identified. Whether individual termination decisions were reasonable requires their public evidence and policy context. No new execution, no model call, ¥0. See the [corrected record](TERMINAL_TAXONOMY.md) and [unchanged artifact](evidence/terminal-taxonomy-2026-10-27/TERMINAL_TAXONOMY.json).

## 1.0.85 — 2026-10-26

**2026-10-27 closeout, no new version:** Bound the two existing terminal-output directories to 38 per-file digests extracted from the previously frozen packet. Completed a scoped AppWorld candidate summary and internal paper-claim review: the concrete native negative control was detected, current paper claims are NO-GO, and scientific status remains HOLD. Future concrete candidates require a one-page design before implementation. No new native-score, model, or environment execution; frozen 1.0.85 evidence is unchanged.

Ran the first two AppWorld native program controls on the same existing train task with original full scoring: reference passes 2/2; a legal title exchange followed by the same reference passes the answer test but fails collateral-state checking (1/2), while both completion signals are true. Title support is preserved but full record-hash support differs, so this concrete candidate is closed. Resolved three dependency bootstrapping failures with compatible version constraints, preserving all 567 public and 120 protected upstream files. Kept an initial incorrect same-process replay caused by retained low-level task caches; per-arm fresh processes reproduce the original scores, and a source/input-bound replay utility plus six integrity tests guard this lifecycle boundary. Freeze metadata, runtime lock and an encrypted native packet include original inputs/tests, terminal deltas, IO, requests, scores and failure records; base DBs are referenced, raw per-call response bodies were not captured. Two completed trajectories, 150 tracked user API requests and eight full scorer invocations including replays are one task, not model/cross-task evidence. No provider API calls, official model outputs or scoring patches; scientific HOLD remains.

## 1.0.80 — 2026-10-26

Prepared exactly one native train task, selected as the first official train entry before task inspection. Bound the minimal 0.2.0 package, 25 original task files and 12 base databases. Unchanged public SQL replay applies all 18 original delta statements; 103 hash-bearing tables contain 373,497 rows, no repeated hashes and no invalid hashes. Distinct start hashes exclude the 1.0.75 multiplicity mechanism under equal row count/hash support, so this candidate receives a task-specific NO-GO without fabricating an end state or running the full scorer. Added eight software controls and kept the original synthetic miss. Protected contents stay local, original tasks/scoring and prior evidence stay unchanged. No official-output download, native scorer, environment, legal tool trajectory or model API call; original terminal DB/log/score packet remains incomplete. Scientific HOLD remains; no automatic task expansion.

## 1.0.75 — 2026-10-26

Located the public ORM record-hash definition and corrected the 1.0.70 protected-source attribution without rewriting old records. Reproduced a content-multiplicity miss using unchanged public comparison function bodies and synthetic boundary adapters: equal-sized `[a,a,b]` and `[a,b,b]` states produce no reported changes. Retained ordinary update/add/remove/size-change controls and benign same-content recreation; an identity-only permutation is not mislabeled as a content-multiset miss. Added eight regression tests and Apache-2.0 public-source excerpts with provenance. A local static application-schema check does not establish global hash uniqueness or legal API reachability; protected code is not redistributed. No task/output download, native task scorer, real model call or AppWorld environment run. Next is preparation of one original train/dev full-scorer case; no real benchmark false success or paper novelty established, scientific HOLD unchanged.

## 1.0.70 — 2026-10-26

Pinned AppWorld commit 42b5bcf3cd334fee33f0c37c02070a9f5807add5 and verified 19 plaintext source/document files (522,076 bytes) against the official Git tree and SHA-256. Reviewed native collateral-state checks, task-specific score dispatch, the separate completion signal, TGC/SGC aggregation and log limitations. Closed generic completion-flag/metric conflations without claiming all tasks correct. Retained one conditional hash-set/record-identity question, explicitly missing hash semantics, actual constraints, full per-task tests and original run evidence. No real native false success is confirmed; no rate or ranking estimate is available. No task/output/protected bundle download, AppWorld execution, new model call or task family. Source-level facts and candidate decisions are frozen separately from unknown runtime facts. Next is a bounded source check with explicit close conditions; scientific HOLD and current recovery-algorithm NO-GO remain.

## 1.0.65 — 2026-10-25

Screened one recovery/termination claim against the frozen public rule and actual post-timeout prefixes. All six text/state pairs share the same canonical public prefix, retaining five terminal-escalation improvements. Four state/projection pairs match exactly: completion and final escalation are unchanged, but projection removes two continuation calls and lowers their recorded tokens from 12998 to 7906. Reported the unactivated fault and the remaining request-ID difference without normalization. Seventeen existing post-fault records contain four distinct public prefixes; the unchanged public rule proposes escalation for all seventeen without environment execution or numerical recomputation. Added EpiSEM-Bench, AgentAbstain and TelemetrySuffBench to the design screen. Current new-algorithm claim remains NO-GO; no new tasks, model trajectories or API calls. Thirty-two related tests pass; no new full-suite run is claimed. Next step is a bounded read-only audit of a public benchmark's native contract and full scorer, before any expansion.

## 1.0.60 — 2026-10-25

Completed a primary-manuscript comparison of AFT-Bench v2, INTENT v1 and HyperAgent v1, including section-by-section AFT overlap. Reclassified current budget/interface/receipt/termination methods as engineering rather than an established original algorithm. Added explicit per-tool input contracts and an opt-in offline rejection gate preserving original proposals without defaults or coercion. Reparsed 207 frozen responses and found exactly one missing publish.mode; all 63 historical completion labels remain unchanged. Added orthogonal private-world/public-evidence/termination/fault/rejection outcomes without treating safe escalation as recovery completion or assuming escalation optimality. Added 10 tests; full suite: 1023 tests, 1020 passes and 3 conditional skips. Zero new API calls or model trajectories. Cross-task expansion and paid runs now wait for a differentiated hypothesis plus task/metric design review.

## 1.0.55 — 2026-10-24

Added a budget-projected tool registry/action enum with full-namespace parsing that preserves excluded proposals. Ran 54 actual DeepSeek trajectories and 9 shared backend controls with identical completion text, receiving all 207 responses without parse/provider errors. Ordinary-receipt completion was 12/12 in all three arms, qualifying earlier attribution to state tracking. Under planned receipt loss, matched text/soft state/projected tools had 6/1/0 rejected reads; projection realized only five faults because one publish omitted mode and was rejected before commit. All five realized projection faults escalated, but there was no improvement in fault-case completion; no unsupported stops occurred. Projection used the same total requests as soft state and 3.36% fewer total tokens, while ordinary-case requests/tokens increased. Preserved the parameter failure and all extra attempts. All 54 model traces, 9 rule traces and 207 response classifications replayed offline; 1013 tests completed with 1010 passes and 3 conditional skips. Next 1.0.60 targets per-tool parameter contracts and source-linked evidence compaction.

## 1.0.50 — 2026-10-24

Added public evidence validity, staged-candidate/CAS-receipt binding and advisory cost-feasible actions. Ran 54 real DeepSeek trajectories plus 9 shared backend controls, with 181 received responses and no parse/provider errors. Under confirmed receipts, joint planning completed 12/12 versus combined prompting 5/12 and read-only planning 1/12; post-publication rejected reads fell from 10 to zero relative to read-only planning. Receipt-loss controls remain unresolved: joint planning escalated once and exceeded the budget five times after six realized lost receipts. Added an explicit shared completion-evidence contract and additive protocol score while retaining original scoring; no unsupported stops occurred in actual samples. All 54 traces/181 classifications replayed offline; 1006 full-repository tests completed with 1003 passes and 3 conditional skips. Next 1.0.55 tests structured admissible-action interfaces and stronger text controls.

## 1.0.35 — 2026-10-24

Completed 48 real DeepSeek trajectories and 12 shared rule controls across a 2x2 prompt experiment and a public-contract planner with canonical/opaque read names. Budget-only completed 3/6, relation-only 2/6, combined 6/6 and context 0/6. Automatic evidence planning improved transfer completion from 1/6 to 2/6 under canonical names and 3/6 to 4/6 under opaque names, retaining one canonical regression. All 155 requests returned without parse/provider errors; 48 offline replays matched. Posthoc failure localization found 16 correct publications followed by an unaffordable extra read. Added exact public evidence coverage and lossless action namespaces, without overriding model choices. Next release is 1.0.50, skipping the reserved 40–49 interval, and targets joint evidence/action/termination planning.

## 1.0.30 — 2026-10-24

Ran a frozen three-arm DeepSeek intervention on six historical development instances under one-check caps. Budget/information guidance safely completed 12/12, the original prompt 0/12, length-matched service context 1/12, and separate public-rule controls 12/12. All 87 API responses returned without parse/provider errors; 36 offline model replays and response classifications agreed. Retained larger information/token costs and one redundant healthy-state staging action. Added public information-inclusion preflight and explicit prompt/call-cap configuration. Registered evidence byte-preservation rules in the living CI integration catalog to fix the prior push's two Python failures; historical evidence unchanged. The next experiment separates budget salience from information-relation guidance.

## 1.0.25 — 2026-10-24

Ran the first live DeepSeek recovery-credit pilot: 12 actual model trajectories, 12 exact-prefix helper continuations and 12 public-rule replacements. Recorded 41 received API responses with no parsing failures. All six one-check model trajectories requested status then an unaffordable inspect; all six four-check trajectories succeeded. Added named model dispatch, helper isolation, raw-response/decision bindings, explicit rejected-budget proposals and separate external missingness. Fifty-one relevant tests passed; 24 additional offline replays and all 41 response classifications were verified without further model calls. Next experiment targets budget-aware tool selection, with information/token costs retained.

## 1.0.20 — 2026-10-24

Built and ran an exploratory recovery-credit experiment: primary alone, primary plus a public semantic helper, and helper alone with shared tool/decision caps and charged handoff. Twelve historical tasks, three analysis intents in one environment, six conditions and two budgets produce matched control triplets. Added a separate Fraction/CSV/SQLite assessment, full original metric retention, actor-level execution evidence and replacement/interference diagnostics. Research exploration is active; these are programmatic controls, not model improvement. Added a focused literature comparison and two concrete research candidates.

## 1.0.15 — 2026-10-24

Fixed attribution from malformed partial captures by validating the retained prefix and append-only history before using its events. Valid missing suffixes remain unknown, without discarding already-proven harm. Replaced recursive metadata-name filtering with explicit capture-envelope substitutions, preserving business payloads and all other source bytes. Added a separate inverse/source fidelity verifier, complete attachment/case coverage checks, and staged export before publication. Original 1.0.10 artifacts remain frozen. Engineering validation only; human/scientific review pending, HOLD and zero paid-run budget unchanged.

## 1.0.10 — 2026-10-23

Registered user-supplied external-agent review without treating it as human confirmation. Separated snapshot correctness from captured termination, moved input integrity out of subject-writable rules, retained initialization attempts, made version/missing/duplicate/final-state controls explicit, and reported class balance and behavior duplication. Added normalized first-pass review views with private mappings; original/derived sources are explicitly unblinded phase-two material. Database/distributed-system background added. Scientific HOLD, current broad-claim NO-GO and zero paid-run budget retained.

## 1.0.05 — 2026-10-23

First real workflow adapter: existing historical CSV/SQLite group task, original grader retained, separate Fraction/SQL/source-capture reconstruction, original-source review export and safe-escalation semantics. Sixteen programmatic engineering controls; the repaired-history violation is already covered by the original safety metric. No live model run; scientific HOLD and paid-run NO-GO retained.

Same-version research review: added close-work sources and explicit limits, screened three prospective sources without collecting tasks, revised unsupported originality framing, and prepared a pending focused human review form. Zero candidate designs admitted; implementation version and technical validation unchanged.

## 1.0.0 — 2026-10-22

First offline audit implementation: independent input paths for terminal score and reliability facts, provenance/actor/resource checks, missingness-aware family summaries, exact paired comparisons and source review export. Twenty synthetic control records, no live model or scientific efficacy result. HOLD retained.

## Design checkpoint — 2026-10-21

Research reset protocol and manuscript drafted from FaultDA-Bench 0.5.65-dev. No executable reset audit yet.
## Research direction gate — 2026-11-06 (no version bump)

The retrospective-source-correction candidate is closed as NO-GO: StateGuard directly describes a revised COGS value invalidating previous artifacts, preserving committed states and triggering targeted recomputation; TimeSage-EV and ChurnBench cover temporal cutoff and retrieval-time versus evaluation-time freshness. The previous LongDS baseline-conditioned reset candidate also remains closed as a paper headline, without alleging that LongDS results are biased. The initial DCR causal-validity framing is also closed as NO-GO because StateGuard explicitly defines DCR as an observational association. A narrower HOLD candidate asks whether cross-system DCR comparisons are sensitive to model-specific parent-state and score-support composition. This remains a design hypothesis only and lacks trajectory-level evidence. No model/API run, new task family, dataset download, or tests. See [DCR support-comparability gate](DCR_CAUSAL_VALIDITY_GATE_2026_11_06.md), [closed source-correction gate](RETROSPECTIVE_CORRECTION_PROPAGATION_GATE_2026_11_06.md), and [closed reset gate](ONE_PAGE_RESEARCH_DESIGN_GATE.md).

## DAComp state-lineage novelty check — 2026-11-06 (no version bump)

Checked arXiv:2607.12338v1 and arXiv:2605.10448v1 against the remaining exact-start-state-lineage candidate. Partial-task decision preservation, task-group coverage, evidence labels, and score bounds are already covered; they are removed from the potential contribution. Exact initial database-state lineage remains an untested boundary only, not an established contribution. The experiment remains HOLD because task-level outcomes are missing and WSL2 cannot start until Virtual Machine Platform is enabled and Windows restarted. Docker Desktop was updated from 4.70.0 to 4.98.0, which cleared its stale-socket startup error; no task, container, model, or API was run. See [state-lineage gate](TASK_STATE_LINEAGE_GATE_2026_11_06.md).

## 2026-11-06｜Docker 隔离预检恢复（无版本号变更）

修复本机 Docker Desktop 4.98.0 启动失败：Windows 无法访问遗留的 `docker-secrets-engine/engine.sock`（错误1920）。在确认 Docker 已停止、目录仅含该 socket 后将目录移入本地备份；Docker 随后自行隔离新残留 socket 并启动成功。Docker 29.9.2 / WSL2 引擎可响应。按 DAComp runner 声明镜像固定 digest，在无网络、只读根文件系统、非特权 UID、限资源容器中完成 Python 3.12.16 / Node 22.23.4 启动预检；未挂载仓库或任务数据，未运行 benchmark、模型或 API。既有 `kdd-dev` 容器在引擎恢复边界以 255 退出，未删除、未重启；该事件需保留为本机环境状态。研究仍 HOLD，下一步是选择并验证本地模型端点，再冻结最小配对 pilot。详见[状态血缘门槛](TASK_STATE_LINEAGE_GATE_2026_11_06.md)。
## 2026-11-07｜更正 DAComp Table 5 敏感性结论（无版本号变更）

复核论文 Table 5 的完整 DA-Agent 行后发现，先前将“三强系统内部最小相邻差7.19”误写成“全表最小相邻差”。完整 DA-Agent 行中 Gemini-2.5-Pro=34.70 与 DeepSeek-V3.1=34.33 只差0.37分；OpenHands 子表中 DeepSeek-V3.1=33.87 与 Gemini-2.5-Pro=33.38 差0.49分。已知11个 rubric ceiling 候选的条件性模型对分差上界为1.318分：它不足以颠倒 DA-Agent 前三名顺序，但无法排除上述全表相邻对换序。先前“11项不足以改变 Table 5 全部排序”的结论撤回；实际变化仍未知，因为只有3条公开逐题评分、规范分母未裁定。该上界仍不足解释 Issue #11 的约10–11分重跑差。更新了审计正文和一页门槛；没有模型/API调用。科学状态仍HOLD。
## 2026-11-07｜DAComp 当前主分支结果矩阵核验（无版本号变更）

用 GitHub API 复核官方 `main` 仍固定在 `027ccaf20f0d3743d9291fd575d9bc785a5fe3db`。`agent_results/` 仅有 GPT-5 与中文 Qwen 两个目录，共四个样例任务；正确解析含嵌入换行 rubric JSON 的 CSV 后，英文评分记录1条、中文2条，各自汇总文件也只有单一运行配置的1条汇总。未发现能连接榜单近邻模型对的公开逐题矩阵，因此不能计算真实排名改变量。此核验确认现有样例覆盖，不产生新的模型/基准证据，候选仍HOLD；没有模型/Judge API调用。详情见[契约审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)。
## 2026-11-07｜评分契约候选近邻边界更新（无版本号变更）

对照 *When Benchmarks are Targets* 与 *A Judge-Aware Ranking Framework* 的原始论文：前者已表明多选基准中小型评测细节扰动可改变排行榜；后者已为异质 Judge 的模型分数差与排名提供不确定性建模。故不把一般排名敏感、Judge不确定性区间或重评分差异作为独立增量。DAComp候选只剩更窄的待检验事实：独立裁定为合法的跨文件rubric ceiling解释，是否会改变固定开放式数据分析输出的预注册模型比较，并超过Judge波动。固定版本只有3条逐题评分，无法实证该命题；候选未通过贡献门槛，科学状态HOLD。未引入新候选、未运行模型/API。
## 2026-11-07｜DAComp rubric 公式与固定 scorer 分母对照（无版本号变更）

补读 DAComp 论文 §2.2 与 App. 10.3：论文规定按每个 sub-requirement 的选中路径应用 leaf items，并以 `Σs_k/Σw_k` 归一化；固定 `rubric_scoring.py` 则将任务级 `metadata.Total` 用作分母，所得 rubric 百分比以0.60权重进入最终总分。对 `dacomp-006`，不同路径上限令 rubric 可计分权重和介于16–20，且公开 Judge 输出没有保存三个零分标准的路径选择，因而不能重建完整论文分母。该证据证明方法文本与实现采用不同分母表达且此百分比会影响最终分，但不能单独裁定实现错误或公开分数错误。扩展两阶段人工审查为三阶段，在锁定 rubric-only 与 metadata 记录后再审方法—实现对照；阶段表仍空，科学状态HOLD，没有调用模型/Judge API。详见[固定资产审计](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)、[一页门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)和[审阅流程](DACOMP_CONTRACT_REVIEW_PROTOCOL_2026_11_06.md)。
## 2026-11-07｜校正 NIKA 时间戳语义并收窄首个假设（无版本号变更）

复核固定 NIKA 提交的 P4 与 exporter 代码后，校正前一条源码初审中的表述：`packet_timestamp` 不是 P4 交换机处理时刻，而是 exporter 在用户态 `recvfrom()` 捕获并解析帧后调用 `time.time_ns()` 得到；P4 `egress_global_timestamp` 只用于虚拟队列计算，没有写入遥测。Collector 目前也没有记录 UDP 收包时间。因此当前最多存在 exporter→collector 管线延迟的测量入口，尚不能声称已具备网络事件时间、端到端事件延迟、双时钟可比性或 Agent 决策时刻可见性证据。首题收窄为先审查时钟、延迟与数据真值的可达性；长期“AI × 通信遥测”方向不变，科学状态继续HOLD。无模型/API、容器或测试运行。
## 2026-11-07｜NIKA 时钟域与管线干预入口源码审计（无版本号变更）

固定 NIKA 提交的源码进一步确认：P4 gateway fabric 将交换机 telemetry egress 与 collector 放在专用 `telemetry_lan`；通用 `TCMixin.tc_set_netem()` 支持 delay/jitter/reorder，且诊断 MCP 工具白名单不向 Agent 暴露该工具，可作为权限不变的外部处理入口。NIKA 通过 Kathara `get_instance()` 选择实际 manager，仓库依赖约束未固定 Kathara 精确版本；官方配置默认 manager 为 Docker，但支持 Kubernetes/远程 Docker。Docker 容器共享 Linux kernel；NIKA 的 `time.time_ns()` 取 Unix realtime，Linux time namespace 不虚拟化 realtime，Python 文档称 `CLOCK_REALTIME` 对进程共享。因此同一 Docker daemon 内 wall-clock 差值有结构依据，但实际 manager、时钟步进、权限和接口隔离仍未在运行时验证。受控管线延迟实验有工程可达性依据，测量有效性与科研增量仍HOLD。未启动容器或模型。
## 2026-11-07｜收窄通信遥测候选并完成近邻复核（无版本号变更）

查阅 TelemetrySuffBench、WirelessOpsAgent/WirelessOptBench 及传统 INT 故障定位工作后，关闭“泛化的新鲜度感知 Agent”主张：近邻已覆盖遥测证据充分性、网络 action assurance、事件/摄取时间、新鲜度/乱序和安全执行；经典网络系统也已研究遥测老化对定位时长与误告警的影响。仅保留“同一次多步网络排查中，遥测逐步/乱序到达是否造成错误定论或迟到后不修正，冻结快照是否遗漏这一过程差异”作为待审候选。已核读 WirelessOpsAgent 论文和公开 artifact：其正文明确冻结 episode 输入并覆盖 freshness/order；artifact 仅公开说明文件，底层数据和轨迹 withheld，无法核验更细的动态到达实现。因此不能据此宣称存在研究空白。接下来核对 NIKA 在线工具查询语义与该假设的可测性；科学状态HOLD，未实跑、未调用模型/API。

## 2026-11-07｜在线遥测测量入口与公平强规则审计（无版本号变更）

继续审阅固定 NIKA 源码：`failure_inject_complete` 写入 `nika.jsonl`，Agent `tool_start/tool_end` 及输出写入 `messages.jsonl`，两处均提供 UTC 时间戳；成功 submit 回执可与 canonical `submission.json` 交叉核验。因此故障注入完成到终态提交存在源码级计时入口，但时钟校准、不同 Agent adapter 一致性、工具输出完整性及报告 ID 可见绑定仍未验证。另核对 NIKA `flap_probes.py`：150个、每100ms一次的 echo train 可识别周期性丢包/恢复，但验证输出直接使用 `problem.root_cause_name`，属于真值可见 verifier，不是公平根因规则。查阅 AdapINT 原文确认其已用 DRL 优化双时间尺度 INT 探测路径/时延/开销；INT-label、Probe-Optimizer 等也覆盖探测路径/资源分配。故撤下“首次正确提交时间”表述，当前改为注入完成到唯一成功提交回执的耗时，并按最终正确/错误分层；研究候选须检验在线可见顺序是否改变 Agent 相对同信息、同预算强规则的结论。科学状态继续 HOLD；未运行容器、测试、Agent 或 API。

## 2026-11-07｜固定通信遥测主线并校正过程指标（无版本号变更）

按用户要求固定 AI × 通信网络遥测方向，不再切换到无关主题。依据固定 NIKA 源码，`submit` 是一次性最终提交；已有 `submission.json` 后后续提交被拒绝，公开轨迹没有结构化逐步 RCA。因此撤下“中途纠错率/修正时延”作为现有协议可测指标；现阶段候选指标改为最终 RCA、首次正确终态提交耗时（须先校准故障起点和接受提交时钟）、探测/查询/模型开销及网络服务影响。补入 ECG-Scroll 对通用流式 Agent 与检测时延的覆盖，以及 Real-Time Detection and Repair 对通用逐步监控/恢复的覆盖。候选被收窄为通信遥测在线可见顺序与网络 RCA/探测负载的关系，并与同预算确定性规则比较；尚未证明超出领域迁移，科学状态 HOLD。只更新本仓库研究文档，未启动 NIKA/Docker、未调用模型/API、未训练或运行实验。
## 2026-11-07｜GPINT 与 INTCollector 近邻边界复核（无版本号变更）

核读 GPINT 全文相关方法与实验：SQR 在数据面缓存 INT probe，等待下一跳反馈，超时后触发探测恢复或重路由，并评估丢包、链路退化、收集延迟及恢复开销；这关闭了“网络内 INT probe 丢失恢复”作为增量的可能。INTCollector 明确讨论 sink→collector UDP 报告可能丢失，LossSight 覆盖数据包携带 INT 时的路径丢失。当前候选只保留终端业务交付失败与 sink 报告传输失败的配对归因评测，且必须胜过同信息确定性规则；NIKA 聚合端口计数可能令规则直接解决，故仍 **HOLD**。同时收紧公开轨迹统计脚本的工具名匹配条件并复算，计数仍为0。未运行 NIKA、容器或模型/API。
## 2026-11-07｜冻结 NIKA 聚合计数规则上限与混淆条件（无版本号变更）

从 pinned NIKA `p4rt_manager.py` 与 `gateway.p4` 复核 Agent 可见计数粒度：`read`/`counters` 返回逐端口 ingress/egress 汇总包数。推导低背景、同一背景回放时的必要负对照：末端业务包丢失会减少目标出口 egress 增量，单独丢 sink UDP report 不会；同信息规则在该设置下应可直接区分。不同背景回放时，其他同端口丢包可与目标丢包混淆；这是汇总指标的构造性条件，不是 NIKA 实验观察。已写入一页 gate：不可隐藏计数器，须由外部逐包账本验证背景配对，并在相同可见信息/预算下比较。此判断尚需 hosted-runner 运行验证；科学状态 **HOLD**。
## 2026-11-07｜NIKA P4 公开轨迹 Agent 计数器使用审计（无版本号变更）

扩展已校验 Zenodo P4 清点：逐条统计公开诊断日志和提交文件。36条 P4 轨迹中35条调用过 BMv2 计数器工具（95次）；28条存在 submission，缺失的8条全部为 GPT-OSS 20B。旧 submission/ground truth 字段字面相同比较：异常检测27/28、设备14/28、根因名12/28。当前固定 NIKA scorer 期望结构化 `root_causes`，公开归档用旧 `root_cause_name`/`faulty_devices`；字段比较只作历史记录核验，不能称官方评分重放。新增逐轨迹计数和比较行至 JSON，并更新报告与 gate。结论：Agent 在历史 P4 任务中已广泛读取计数器，同信息强规则必须优先实证；历史轨迹没有候选配对，也不构成当前准确率证据。科学状态 **HOLD**。
## 2026-11-07｜补入经典主动/被动故障定位基线并收紧贡献门槛（无版本号变更）

定向检索并阅读 KDD'14 数据中心故障定位、被动端到端测量指导的顺序测试及 Bayesian 渐进式网络探测工作。它们已经覆盖主动业务探测与被动设备遥测融合、成本约束下的顺序诊断和按信息价值选探测；KDD'14 还报告 Azure 生产部署。因此本项目不得把这些机制作为新算法。更新研究章程和一页 gate：候选仅能作为网络 Agent 的受控评测研究继续，必须在独立故障簇上对比计数规则、主动/被动融合、顺序测试与 Bayesian 探测，证明稳定且可复核的 Agent 特有差异。单一配对、超过简单规则或 benchmark 代码均不足。当前仍 **HOLD**，无运行结果或论文贡献结论。
## 2026-11-07｜固定 AI × 通信遥测主线并收敛近邻边界（无版本号变更）

按用户要求维持同一研究方向，不再切换到通用 Agent、RL 或其他评测主题。定向复核 NIKA、CTBench、FaulT-Bench 及 INT 丢失监测近邻：网络 Agent benchmark、证据导向诊断、错误工单、缺失 INT 报告检测/定位均已有直接研究覆盖，均不作为本项目新颖性主张。只保留一个尚未证实的配对问题：网络 Agent 能否在同一初始 sink 行缺失视图、相同权限与预算下，区分终端业务包丢失与 sink UDP 报告丢失，并胜过共享相同观测的规则。明确当前小型 NIKA 预检只能验证运行可达性，不支持“大规模”实证主张；需要独立拓扑/负载和规则对照。候选仍 **HOLD**。未运行 Docker/WSL、NIKA、模型或 API；本机 Docker Desktop 故障下不冒险启用虚拟化。相关来源与边界见一页准入门槛。

## 2026-11-07｜更正 NIKA leaf INT-MX 解封装判断并强化运行预检

固定 NIKA 源码的 `gateway.p4` 显示 `ROLE_LEAF` ingress 会识别 INT-MX、还原 IPv4 protocol、减少 IP total length 并移除 7 字节头部，随后继续向 service 转发。此前“固定 pipeline 未提供 service-side 解封装”的风险判断已撤回；源码支持服务端接收原始 TCP/UDP payload，但仍需 runtime 验证。将 hosted preflight 升为 v0.3：直连 watched-service HTTP 成功成为故障前准入条件；注入后分别检查直连 service 和 VIP，并分开记录两路端口计数增量。此结果只验证受控运行路径，仍不构成 report-only 配对或 Agent 证据。静态 AST 解析与 `git diff --check` 通过；未启动 Docker/WSL 或模型/API。NIKA pinned source: [gateway.p4](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4)。

进一步核对 pinned `hop_exporter.py`、`Dockerfile.base` 与 `Dockerfile.nginx`：exporter 将 INT-MX 中的原始 UDP 五元组规范化，并以 IPv4 identification 输出 `packet_id`；客户端基础镜像提供 Scapy，服务镜像需增加研究用 UDP sink。故可让 probe payload 携带与 IP ID 相同的预注册编号，再用 collector 的 `(flow_id, packet_id)` 与 service receipt 做 evaluator-only 关联。已把该可实现路径及其未验证边界写入研究方向章程；没有运行 NIKA 容器或声称端到端账本已实现。

## 2026-11-07｜修复 hosted preflight 在研究分支的触发入口

检查 GitHub 仓库后确认新增 workflow 尚未进入远端，且只配置 `workflow_dispatch`；GitHub 官方要求手动触发的 workflow 文件存在于默认分支。为避免依赖先合并到 `main`，添加限定 `agent-eval-reliability-reset` 分支且只匹配预检 workflow/脚本的 `push` 触发器，保留手动触发入口供其进入默认分支后使用。此改动将在用户推送后才会触发；尚无 runner 结果。见 [GitHub 手动运行 workflow 说明](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)。

## 2026-11-07｜核对 TelemetrySuffBench 并收紧可主张差异

阅读 *TelemetrySuffBench: Is Agent Telemetry Sufficient for Failure-Origin Diagnosis?* 全文。它已构造模型可见 payload 完全相同、隐藏 origin 不同的配对样本，区分故障检测与来源定位，并测量歧义输入下的安全弃答（五个模型、同生成器家族冻结 holdout）。因此“同视图不同来源不可辨识”及一般遥测歧义弃答不再是本项目可主张的创新。其公开方法描述的是生成式 Agent 执行轨迹与 telemetry masks，没有描述 live packet network 中 sink exporter/collector 的报告丢失，也未见交互式网络证据查询；当前候选的残余差别仅是网络因果干预与动作获取证据，仍须胜过同信息探测/规则并在独立网络任务簇复现。未检查其完整代码 artifact，故不据此主张精确实现差异。科学状态 **HOLD**。 [arXiv:2608.07899](https://arxiv.org/abs/2608.07899)

## 2026-11-07｜让运行预检保留强规则所需的端口计数增量

复核预检脚本后发现：虽然原始 leaf counter snapshots 已记录，但结构化增量仅覆盖 service egress，不能直接检查同一受控探测窗口中 ingress/egress 的完整 per-port 差值。现在为基线直连、基线 VIP、注入后直连和注入后 VIP 四个窗口同时记录所有可见端口的 ingress/egress packet delta，并保留原始快照，以便审查计数器 reset/wrap。该数据仍是窗口聚合，不具逐流归因能力；当前仍没有 report-only 臂、NIKA runtime 配对或 Agent 结果，因此不能判断强规则是否被击败，科学状态保持 **HOLD**。仅做 `git diff --check`；未运行 Docker/WSL、NIKA、测试或模型/API。修改待用户推送后才会进入 hosted runner。

## 2026-11-07｜明确低背景端口计数规则的结构性强度

直接复核 pinned NIKA `gateway.p4` 后确认：ingress counter 在 fault-loss hook 之前计数，而 egress counter 只在 egress control 计数。**源码推论：**对隔离、已知路径的单向固定五元组 UDP 探测窗口，映射入口与目标服务出口计数差可直接给出 ingress 丢弃数量；report-only 丢失不会改变业务包转发计数。因此清洁低背景配对预计由确定性规则解决，应作为规则负对照而非 Agent 贡献。NIKA counters 是按端口聚合，未绑定流；当前唯一可能保留的差异须来自预注册并发背景/测量窗口下同信息强规则的可复核失败，再看 Agent 是否稳定克服。该推论未通过 runtime 配对验证，不能写成实测准确率；科学状态 **HOLD**。来源：[pinned gateway.p4 ingress](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L160-L236) 与 [egress](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L243-L263)。

## 2026-11-07｜复用 NIKA 内置可复现 UDP 背景流量入口

在 pinned NIKA `src/nika/traffic/burst.py` 中核实 `BurstTrafficGenerator` 支持固定 seed、源与目标节点、速率、包长、持续时间和 flow 数；`raw_udp` 路径会启动 UDP sink 与 paced sender，并返回实际五元组/flow ID。它可用于当前通信遥测假设下的受控并发背景实验，优先于新写一套流量生成器。其现有 sink 不保存逐包接收记录，因此仍需 evaluator-only 收包观测；其流量是受控合成 burst，不能写成真实生产流量。仅完成固定源码审查，未运行生成器；当前 pair/Agent runtime 尚未执行，研究状态仍 **HOLD**。 [pinned burst.py](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/traffic/burst.py)

## 2026-11-07｜把固定 UDP 背景 burst 纳入 hosted 运行预检

更新预检协议为 `nika-leaf-service-loss-preflight-v0.4-background-counter`：健康 HTTP 基线后，在 `topo_size=s` 中由所有 client 向目标 service 各发两条固定 seed UDP flow（每 flow 32Kbit/s、128B、3秒），记录 burst 前后 leaf 全端口 ingress/egress packet delta，并从 collector 过滤匹配 flow 的 INT 摘要。该步骤复用 pinned NIKA `BurstTrafficGenerator(raw_udp=True)`，不引入新的流量生成器；它只验证受控并发流量与可见遥测，不包含 report-only 臂、逐包 service 收件账本或 Agent。未运行 NIKA/Docker/WSL，未调用 API；待用户推送后才会进入 hosted runner，科学状态仍 **HOLD**。
# 2026-11-07｜补入 NetOpsBench 直接近邻边界

NetOpsBench commit `d121e55b51f317b9f6bc684be0745184457740b8` 的源码清点发现：内置 campaign YAML 覆盖 packet-loss 故障，handler 通过 `tc netem loss` 注入；该基准已报告多规模 live 网络 Agent 的故障类型与定位成绩。通用网络 Agent 诊断、数据面丢包诊断和规模化 benchmark 因而不构成本项目贡献。这个 pinned built-in campaign 未定义 INT sink-exporter/collector report-loss case，但 NetOpsBench 支持自定义 fault，因此不能把“内置列表未覆盖”当成原创性证明。当前唯一候选仍限于 NIKA 中 packet-before-sink 与 report-after-sink 的因果配对、evaluator 逐包真值和公平同信息基线；配对 runtime 和 Agent/强规则实验均未完成，科学状态 HOLD。研究 gate 已登记固定 SHA 及文件级依据。引用：[pinned campaign](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/scenario/specs/fault_campaign.yaml) · [pinned impairment handler](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/faults/handlers/impairment.py) · [methodology](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/docs/content/docs/run-benchmarks/methodology.mdx)

# 2026-11-07｜完成 NetOpsBench 工具与评分器边界核对

在同一固定 commit `d121e55b51f317b9f6bc684be0745184457740b8` 检查 Agent 的 observability MCP 与 scorer：可见接口包含 device logs、interface metrics、BGP events、Pingmesh summary/hotspots；评分输出覆盖 fault/healthy verdict、fault type、device/interface location 与效率。NetOpsBench 已足以否定“首次评测网络 Agent packet-loss diagnosis”等宽泛主张。其余差别只在 NIKA 的 per-packet INT sink UDP report 可以被放在业务包到达 service 之后、collector 之前单独干预；该实验边界是否产生非平凡 Agent-vs-rule 结论仍待运行和独立任务复验，不是已证明贡献。[pinned tools](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/toolkit/mcp/observability.py) · [pinned scorer](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/evaluator/scorer.py)

# 2026-11-07｜复核 NIKA collector 重接线源码前提

在 pinned NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 核实 `lab.py` 将 collector 模块复制为工作目录的 `collector.py`，启动命令正是 `python3 collector.py --output /var/lib/nika/int_reports.jsonl`；collector 默认监听 UDP/32766，并创建输出目录、追加写 JSONL。因此 preflight 的进程定位、端口迁移及输出路径与源码启动约定一致。此为源代码核对，不证明 runner 内 PID 搜索、套接字释放、relay 转发或 collector 实际收件；这些仍待 hosted runtime。没有运行 NIKA/Docker、模型/API，也没有新 Agent 实验；HOLD 不变。

进一步逐字段比较 pinned `hop_exporter.py` 与预检 AF_PACKET parser：两者使用相同的 `src|dst|protocol|src_port|dst_port` 编码、BLAKE2b-64 flow ID 和 IPv4 identification；collector 将 packet ID 规范成字符串。脚本中 IP 地址的两种来源现有显式相等检查。这仅验证了静态 join 定义一致，不能证明 Kathara/NIKA 在运行时保留 ID 或产生匹配收件；相关 runner 实验仍待执行。
# 2026-11-07｜收窄 AI × 通信遥测研究主张

精读 LossSight 原文后明确：其 missing-at-server report 检测和 sink-to-server 延迟模型覆盖遥测报告未到达问题；source/sink flow-match counter 用于持续黑洞诊断，但论文未给出终端业务包丢失与 sink 后 UDP report 丢失的逐包配对因果标签。修正研究记录措辞，不再暗示 LossSight 未覆盖报告缺失，也不把伪代码歧义当成实现错误。补入 AIOps2025/RCA100 与 OpenRCA 对多模态大规模 Agent RCA、证据已存在/缺失分析的直接近邻：通用遥测 Agent benchmark 不作为贡献。长期方向仍固定为 AI × 通信网络遥测；当前唯一窄候选继续 HOLD，只检验 Agent 是否在等信息、等权限、等预算的通信遥测因果诊断中稳定超越 LossSight 思路与端口聚合计数强规则。无运行时、Agent 或跨任务新证据；未运行测试或容器，未调用模型 API。

## 2026-11-07｜NIKA 本地预检首跑及探针语义修正

在一次性 Docker runner 中真实启动 pinned NIKA `ac4422d8a4a03be2b905e28edf72993d467e1b81` 的 `p4_dc_gateway` 小型拓扑。首跑项目脚本在 `baseline_service_probe` 以直连 `http_ok(service.ip)` 为门槛失败；VIP HTTP 两次通过，直连探测窗口在 leaf service-facing port 3/4 观察到聚合 egress 增量 15/6。Pinned NIKA `p4_dc_gateway/verify.py` 将直连 service TCP 探测明确定义为 observation packet，正常服务健康由 VIP HTTP 检查；故根因是项目自有预检的错误 HTTP 假设，不是 NIKA 基线失效。脚本现改为发出原生 `nc -z` TCP observation probes，以目标端口 egress 增量确认转发，并保留 VIP HTTP 健康检查。首跑未进入 UDP relay、报告丢失、leaf loss injection 或 Agent 阶段，不支持候选假设。Teardown 因 runner 缺少 `iproute2` 抛错；结果先行写入 JSON，退场后 Docker inventory 未发现本次 Kathara lab 容器，但该记录仍标记 `lab_closed=false`。完整边界与产物见 `experiments/communication_telemetry/NIKA_RUNTIME_PREFLIGHT_2026_11_07_RUN1.md` 及同目录 JSON。下一轮仅重跑同一 bounded preflight，给临时 runner 补 `iproute2` 并复核 teardown；研究状态 **HOLD**。

## 2026-11-07｜report-only relay 运行成功，逐包端点绑定待修

修正直接探针门槛并在带 `iproute2` 的隔离 Docker runner 再运行 pinned NIKA。VIP HTTP 通过；直连 TCP observation probe 使目标 service egress port 3 计数增加 2。固定 seed 的四条 UDP flow 各有 94 个应用层 datagram 收件；report relay 共收到 1128 条 sink/hop report，按计划丢弃 376 条 leaf sink report（每 flow 94），转发 752 条上游 report，collector 每 flow 保留 188 行。service `eth0` AF_PACKET 匹配数仍为 0，故应用 socket 与 report 缺失尚未按 packet ID 绑定；不能称为完成的逐包账本或因果配对。Teardown 返回 `lab_closed=true`，Docker inventory 未见残留 lab 容器。保存预检 JSON、842 KB relay JSONL 与[运行记录](experiments/communication_telemetry/NIKA_RUNTIME_PREFLIGHT_2026_11_07_RUN2.md)。下一次仅将 service AF_PACKET 改为全接口抓取并记录目标端口原始 tuple，定位接口绑定或 flow-key 问题；随后才评估 leaf loss arm。研究状态 **HOLD**，未运行 Agent 或模型 API。

## 2026-11-07｜report-only arm 精确 packet-ID join 完成

第三轮在固定 NIKA commit、相同小拓扑与四条固定 flow 下使用全接口 AF_PACKET。每 flow 的应用 UDP socket 收到 94 个 datagram，AF_PACKET 得到 94 个 IPv4 ID；relay JSONL 中同一 flow 与 sink switch 的 `report_dropped` 事件也恰有相同的 94 个 ID。对四流逐 ID 比较为 376/376 完全匹配，零单边 ID。relay 共收 1128、转发 752、丢弃 376 条报告，collector 每流留下 188 条上游行且无对应 sink 行。这验证了**单一 report-only arm**，不构成 packet-loss/report-loss 的配对实验。随后 leaf→service loss 表项在两个 service-facing port 均成功读回；TCP observation probe target egress 为零，VIP HTTP 三次失败；没有在该 loss condition 下发送 UDP burst。Preflight `passed=true` 只表示本地 bounded preflight 流程完成，不能解释为候选或科学门槛通过。原始结果、relay ledger、带源文件哈希的独立 join 审计和[第三轮报告](experiments/communication_telemetry/NIKA_RUNTIME_PREFLIGHT_2026_11_07_RUN3.md)已保存。下一步在 verified loss table 下重放同四流、以 pass-through relay 观察 sink report 与 per-port counters，再评估强规则；科学状态仍 **HOLD**，无 Agent/API 结果。

## 2026-11-07｜通信遥测双臂机制核验

完成 pinned NIKA 小拓扑的固定流 workload 配对：report-only 臂四流各 94 包抵达 service、对应 376 个 sink report 被 relay 丢弃；leaf-loss 臂四流各 0 包抵达 service。两臂 collector 均为每流 188 条上游行、零 sink 行。受控窗口内 target egress delta 为 376 vs 0，公开 P4 counters 显示此配对可被 R0 规则族区分，但还不是独立簇上的冻结 baseline 评估；不准入该条件的 Agent/API 对比。完整证据见 [配对报告](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.md) 和配对审计 JSON。单拓扑/单次配对不足以证明泛化或论文增量；研究候选保持 HOLD。
# 2026-11-07｜细分 NetOpsBench packet-loss 轨迹中的 ping 返回与 verdict

在固定的 319 条 NetOpsBench v0.2 轨迹中，将端点匹配的 `ping_test` 工具回执按工具调用 ID 去重并提取逐次发送/接收数：20 个匹配案例包含 57 条结果（490 发/433 收）。13 个所有匹配 ping 均无丢包的案例中，12 个 verdict 错误（11 判健康、1 弃答）；7 个至少一次有丢包的案例中，6 个弃答、1 个正确判故障。关键新增核对是这 20 例初始异常位全为 true、ground truth 全为故障，因此单字段零工具规则 **20/20**、Agent **2/20**。该结果定量分解已有上游现象，不将轨迹/调用当作独立样本，不宣称一般机制。新增[逐次 ping 事件表](experiments/communication_telemetry/NETOPSBENCH_V02_MATCHED_PING_EVENTS_2026_11_07.csv)，并更新[审计报告](experiments/communication_telemetry/NETOPSBENCH_TEMPORAL_EVIDENCE_AUDIT_2026_11_07.md)、[一页准入门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)和[固定通信遥测方向](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md)。逐案 CSV SHA-256：`d43150174d7982b6358367289195e2587c64050bfc7da0e0b0a86cd84ea27627`；事件 CSV SHA-256：`a64fa81469b2a5cfa3d9a07f116769ed31f53419cefbcd0428a34108e50cd467`。该公开轨迹扩展归因到此收束，研究回到 NIKA 的逐包因果账本和同信息强规则检验；科学状态维持 HOLD，未运行模型/API。
# 2026-11-07｜对流级并发负载扩展作 NO-GO 裁决

按 pinned NIKA 源码核实，`SilentEgressPacketLoss` 只接受 `bmv2_port`；P4 loss table 以 `egress_spec` 为唯一键，公开计数器按 ingress/egress port 聚合。固定环境不能只丢目标五元组而保留同端口并发包；host-side `tc` 会改变故障位置，P4 五元组扩展则是新环境。结合多点流级计数、LossSight、SPADA/PINT、TelemetrySuffBench 和 FaulT-Bench 的覆盖，单加“流级丢包 + 并发负载 + 聚合计数”未显示独立增量，裁决 **NO-GO**，不改 P4、不跑 Agent/API。仅关闭该扩展；原 packet-loss/report-loss 配对仍是唯一研究候选，维持 **HOLD**。详见[一页门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)与[通信遥测研究方向](COMMUNICATION_TELEMETRY_RESEARCH_DIRECTION.md)。
