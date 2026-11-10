# NIKA 同信息规则压力门槛｜2026-11-09

**研究主线：**AI Agent × 通信网络遥测与运维
**候选：**终末业务包丢失 vs. sink 遥测回执丢失
**状态：**HOLD；本文件是实验准入设计，不是实验结果，也不授权模型/API 调用。

## 1. 唯一待检验问题

在相同初始现象（上游 INT 行存在、sink 行缺失）下，最后一跳业务包确实未到达服务，与业务包到达服务但 sink UDP 回执在 collector 前丢失这两种历史，能否被 Agent 以相同工具权限和预算稳定地区分，并优于一个能使用完全相同公开证据的冻结确定性规则？

本问题不主张新的通用遥测充分性机制、网络 RCA 基准、弃答算法或丢包定位算法。它只考察特定通信因果边界及 Agent 相对已有/构造规则的剩余价值。

## 2. 现有证据与关键反例

- **已观测运行事实：**2026-11-07 NIKA `p4_dc_gateway` 小拓扑配对实验中，两臂均有 4 条 UDP 流、每流 94 个包；report-only 臂服务端收到每流 94 包，真实终末丢包臂服务端收到 0 包。目标服务端口 egress counter 差为 376 对 0，因而这一次低背景配对已可由计数规则区分。结果来自单拓扑、单次配对，不是冻结基线或独立任务簇结果。详见 [配对机制核验](experiments/communication_telemetry/NIKA_PAIRED_PACKET_REPORT_LOSS_2026_11_07.md)。
- **信息边界：**relay 的丢弃日志、注入配置、逐包隐藏账本和评测端抓包属于 oracle/evaluator-only，不得暴露给 Agent 或强规则。Agent 可见数据限于 pinned NIKA MCP 工具实际返回的 INT 行、只读 `read`/`counters` 和配额内主动探测。
- **强规则回放：**对已存配对文件运行 counter-only replay 后，两臂计数守恒规则均与评测真值一致（2/2 条件）；这是一组小拓扑、单一 workload profile 的离线复算，不是盲测、独立任务族或模型对照。[回放报告](experiments/communication_telemetry/NIKA_R1_R2_EVIDENCE_AUDIT_2026_11_09.md) · [机器输出](experiments/communication_telemetry/NIKA_COUNTER_RULE_REPLAY_2026_11_09.json)
- **可见信息限制：**pinned `p4rt_exec read` 能返回交换机名、转发表前缀、转发 member 的端口号和 per-port counters；拓扑模型中的端口对端映射不直接返回。现有运行未保存原始 MCP `read` 输出，所以不能回溯证明 Agent 可见字段足以把 `leaf_1` 作为目标范围；后续必须保留完整工具调用与输出。该工具接收原始 CLI 参数，若实验限制为只读必须用白名单包装器。
- **实现边界：**pinned NIKA 的 loss 表按 egress port 生效，不支持五元组单流注入；低于 10000 bp 时，hash threshold 可对该端口各流形成确定性子集丢包；10000 bp 时该端口所有包均丢。背景压力在原生 P4 上可实现，但不能假设只丢目标流而让同端口背景流通过。不得将 host-side `tc`、更改 P4 注入器或隐藏评测字段伪装成 pinned 原生任务。
- **严格配对的发送端约束：**pinned NIKA `BurstTrafficGenerator(raw_udp=True)` 使用 `SOCK_DGRAM.sendto`，固定 seed 只决定流五元组，不控制内核分配的 IPv4 ID；旧两臂因此只匹配 workload profile。现有 relay 可依据 `(flow_id, packet_id, switch_id)` 精确丢报告。要做 packet-level matched pair，runner 必须用 raw-IP/pcap replay 固定包长、五元组、payload 与 IPv4 ID，并将 data-loss 臂实际缺失的 ID 集合转成 report-only 臂的精确 relay drop plan。此路径尚未实现或实测。
- **真实负载校准：**ServDeg 同一宿舍网络的 MON–FRI 五日记录包含约 1,395 万条聚合 TCP flow。流数总体 CV 为 8.13%，单流 P99 包数约 1,290–2,785；P99 字节数约 1.12–2.62 MB。五日画像可以定义共享端口压力档位，但不提供逐包时序，也不能直接作为 NIKA UDP 包回放。逐日统计与转换边界见 [ServDeg 五日负载审计](experiments/communication_telemetry/SERVDEG_CROSSDAY_PROFILE_AUDIT_2026_11_09.md)。
- **计数规则投影更正：**旧 v1 的“目标全丢、同端口背景通过”与端口键控注入器矛盾，已作废。按 pinned P4 的 10000 bp 全端口丢包与 report-only 条件重算，五日 15 个负载档位的 30 个公式场景中，冻结计数规则 30/30 可确定地区分两类标签。该代数结果不是运行或 Agent 结果；不能据此研究“背景负载使 R2 弃答”。详见 [v2 投影结果](experiments/communication_telemetry/NIKA_SHARED_PORT_RULE_PROJECTION_2026_11_09.json) 及[更正方法](experiments/communication_telemetry/SERVDEG_CROSSDAY_PROFILE_AUDIT_2026_11_09.md)。

## 3. 预注册式比较

| 臂 | 输入 | 目的 |
|---|---|---|
| R0 trace-only | Agent 可见的上游 INT 部分轨迹 | 验证两种隐藏历史是否确实产生相同初始观测；若轨迹已不同，配对构造失败。 |
| R1 raw visible tools | 完整只读 NIKA 工具输出：实际返回的转发表字段、计数器、INT 轨迹；缺失的邻接映射不得由研究者补入 | 测量现有公开工具是否直接解开成因，不允许读取隐藏注入端口映射或 oracle。 |
| R2 frozen rule | 仅使用与 Agent 完全相同的 R1 字段、相同探测/读取预算；证据冲突或不可辨识时必须输出 `underdetermined` | 作为主强规则基线；规则、阈值、窗口和异常处理在开发簇冻结后不得看盲测标签调参。 |
| R3 Agent | 与 R1/R2 相同工具、起始观察、调用/探测预算和时间限制 | 仅在 R2 于独立盲测簇存在可复现的错误或高弃答后准入；与 R2 配对比较。 |
| R4 measurement extension | 在 R1 之外增加 LossSight 类标记或流级传感器 | 可选机制上限分析；不用于声称 Agent 在原生 NIKA 同信息条件下优于规则。 |

## 4. 最小实验设计与记录

1. **机制验证先于模型。**对每个 seed/工作负载配对记录相同上游 report key、服务端收到包 ID、sink exporter 生成的 report ID、relay 转发/丢弃事件、collector 收件及各公开端口计数。必须逐包复现相同 packet length、五元组与 IPv4 ID，并验证 hash threshold 在两臂选择同一包集；隐藏账本必须逐包闭合。旧运行仅匹配 workload profile，packet IDs 不同，不作为 exact-equal trace 证据。report-only 臂的 relay drop plan 由先行 data-loss 臂的逐包记录生成，执行时须检查目标 ID 全部命中且没有多余丢弃。
2. **盲测切分按来源簇。**开发与测试须隔离 workload/flow-profile seed；若可用多个拓扑，拓扑也整簇留出。重复、重试、同一流的时间窗变化及同一 seed 的两个故障臂都不是独立样本。若只有一个拓扑或一个 workload 家族，结论限于该环境的机制检查，不能进入跨簇 Agent 主张。
3. **预先固定压力变量。**只改变与目标共享终末 egress port 的背景流及其与计数窗口的重叠；背景档位按 ServDeg 五日 P50/P90/P99 画像预先固定，NIKA 生成流的 TCP→UDP 映射规则单独记录并先验证包数/字节预算。拓扑、故障位置、工具权限、规则和总调用预算保持不变。原生 loss threshold 会作用于该端口全部流量，必须将每个背景包纳入包级真值账本。不得用事后筛选“规则失败”的 episode。
4. **同信息执行。**Agent、R2 和 R1 使用相同公开字段。执行者和评分程序不可向被测策略泄露真实标签、relay 日志、hidden fault config、ground-truth packet ID 列表或结果文件。
5. **完整逐 episode 留证。**保存环境与代码 commit、配置、随机种子、工具输入/原始输出、规则版本、Agent 原始响应（若获准运行）、每次调用成本/延迟、盲测标签、账本校验和异常退出。模型供应商响应未保存原文时，不得声称已复核模型行为。

## 5. 主指标与分析单位

- **首要机制指标：**R1/R2 在配对真值上的正确归因率与 `underdetermined` 率；同时报告每个独立 cluster 的配对混淆矩阵。不得只报告聚合准确率掩盖簇间不稳定。
- **Agent 增量指标（仅 R3 准入后）：**同一盲测 episode 上 `R3 正确归因且 R2 错误/弃答` 与反向不一致对；报告配对差值、cluster bootstrap 区间，并单列安全错误归因和合理弃答。样本量在看盲测标签前依据开发集不一致率和目标最小可检测差异计算；本文件不虚构所需样本数或效果值。
- **资源指标：**工具调用数、探测包数、总字节、墙钟延迟及 API 成本（如实际发生）；预算越界按失败记录，不删样本。
- **业务影响：**只有任务契约能预先定义错误归因对应的后续运维决策及危害时，才报告“运维结论影响”；否则不把分类差异升级为运营收益。

## 6. GO / NO-GO 决策门

**先做离线/运行时技术门，不调用模型 API：**

- 两故障臂是否在起始 trace 上真正相同、在 oracle ledger 上确实不同？
- R1 工具是否暴露足以区分两臂的计数/拓扑字段？端口与服务映射是否由 Agent 可见信息推出，而非由实验者私有拓扑知识补入？
- R2 是否只用允许字段，并能在无唯一归因时拒绝猜测？
- 当前 NIKA 注入能力是否支持拟定的背景压力而不改变目标故障语义？

**NO-GO：**如果低成本公开计数/探测规则在所有可实现的盲测簇都同等或更优；如果差异只依赖 oracle/新增传感器；如果两臂初始观测不匹配、逐包账本不能闭合、任务簇并不独立，或 FaulT-Bench/TelemetrySuffBench/NIKA/LossSight 的完整方法审计已覆盖同一操纵与指标，则关闭该 Agent 机制候选，保留通信网络遥测方向，不扩模型、不转去另一个宽泛 benchmark。

**R3 GO：**必须同时满足：至少一个预先指定的独立盲测 cluster 中，冻结 R2 有账本确认的成因误判或超出预算的合理弃答；错误不是配对构造、映射或计数窗口缺陷；并且按开发集预定的样本量计划，在同信息同预算下 Agent 的配对增量方向稳定且区间排除预先定义的无实质差异范围。达到这些条件只准入小规模、预注册的 Agent 试验，不自动构成论文贡献。任何最终论文主张还需独立任务/拓扑复现和近邻论文逐项复核。

## 7. 当前裁决

当前 counter-only 离线 replay 在两个低背景条件中均与服务端/relay 真值一致（2/2）；它以 harness 记录的目标 leaf 为范围，旧运行也不是逐包 ID 完全相同的盲测配对。v1 压力投影已因故障范围假设不可实现而撤回；源码一致的 v2 代数结果在 30/30 个公式场景中均可被计数规则区分。故“共享端口背景降低规则覆盖”不再是合格研究问题。更关键的是，2026-11-09 对 pinned NIKA 的完整任务提示与工具链源码审计确认：拓扑边表已进入 Agent 初始任务文本，默认 MCP 面同时提供 host 查询和 P4 read/counters；此前“服务到计数端口映射可能不对 Agent 可见”的疑问不成立。详见[Agent 可见拓扑审计](experiments/communication_telemetry/NIKA_AGENT_VISIBLE_TOPOLOGY_MAPPING_AUDIT_2026_11_09.md)。因此这组配对正式冻结为同信息规则负对照，不再扩矩阵或等待该映射的运行时审计。整体研究仍 **HOLD**，下一阶段转入同一 AI × 通信遥测方向的长期学习研究设计：以多时段真实流量、少标签适配与遗忘为主问题，先做任务/标签/时间切分的可复核数据契约，再实现 SNN 与匹配 ANN 的离线比较。模型/API Agent 运行仍未发生。

### 2026-11-09｜对 v1 共享端口投影的更正

源码核对：NIKA 的 P4 loss 表以 egress port 为键，注入器将 10000 bp 转成 threshold 65535；P4 hash extern 的 `base + (h % max)` 语义使 `max=65535` 的结果范围为 0–65534，因此固定程序中的 `< threshold` 会丢弃该出口端口上的所有包。[NIKA loss 配置](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/problems/link_interface/p4_gateway.py#L14-L60) · [P4 port-keyed loss hook](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L87-L96) · [P4 hash semantics](https://p4.org/wp-content/uploads/2024/08/P4_tutorial.pdf)。故“只丢目标包、同端口背景包通过”不可能由该 pinned fault 实现。按端口级全量丢包重算后，冻结规则在 30/30 个公式场景均确定区分 report-only 与 terminal packet-loss。作废的 v1 与理由写入机器结果 JSON；ServDeg 审计和一页门槛同步撤回“15/30 coverage”解释。

## 8. 主要近邻（用于设计审查，不替代完整相关工作）

- NIKA：网络故障诊断工具 Agent 基准，https://arxiv.org/abs/2512.16381
- CTBench：电信网络故障排查、路径恢复及证据路径评估，https://arxiv.org/abs/2608.12002
- FaulT-Bench：不可靠网络故障票据与错误报告，https://arxiv.org/abs/2608.27021
- TelemetrySuffBench：遥测充分性、故障来源定位和安全弃答，https://arxiv.org/abs/2608.07899
- LossSight：INT 报告丢失检测/定位机制，https://doi.org/10.1109/TNSM.2021.3125012
- LB-LossSight：多路径下的 INT 丢失定位，https://doi.org/10.1002/itl2.393
