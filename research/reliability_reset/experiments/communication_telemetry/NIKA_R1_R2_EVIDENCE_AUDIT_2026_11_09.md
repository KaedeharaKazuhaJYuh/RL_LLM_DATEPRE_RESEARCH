# NIKA R1/R2 可见证据与规则回放审计｜2026-11-09

**范围：**固定 NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 的 P4 接口源码审计，以及 2026-11-07 配对机制运行的离线计数规则回放。
**状态：**低背景配对已由公开计数规则解释，保留为冻结的规则负对照；先前共享背景压力投影因注入范围假设错误已撤回。当前只核验目标服务到端口计数的可见映射；没有 Agent/API 运行。

## 固定源码的可见字段

- `p4rt_exec(args)` 将原始参数交给 `p4rt_manager.py` 执行；接口本身允许任意管理器子命令。若实验规定只读权限，必须在 MCP 前增加参数白名单，不能只在说明里要求 Agent“不要写”。[BMv2 MCP tool](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/mcp/servers/kathara/bmv2_server.py#L13-L19)
- pinned `cmd_read` 默认读取所有配置交换机，返回按交换机名组织的观测；每台设备的观测包含 forwarding members、groups、IPv4 LPM、按端口 ingress/egress counter、寄存器和部分运行时配置。member 暴露 egress port ID，IPv4 LPM 将目的前缀映射到 group，group 再映射到 members；因此服务路由到端口号可由公开转发表推导，但拓扑模型中的 `ports[*].peer` 邻接映射本身不在此 JSON 结构内。[p4rt_manager.py](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py#L552-L676) · [`cmd_read`](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py#L751-L766)
- **字段级映射边界：**固定 `cmd_read` 调用 `observed_switch()` 后只序列化 `pipeline`、`members`、`groups`、`ipv4_lpm`、`counters`、`registers`、`runtime_config` 和 `arbitration`；`ipv4_lpm` 暴露目的前缀到 group ID，group/member 再暴露 egress port 和 MAC 字段，但返回对象不含 topology model 的 `ports[*].peer`/peer role。故可恢复“目的前缀关联到哪些转发端口”，但“该端口物理连接目标 service”是否能由 task prompt、其他 MCP 工具或 MAC/ARP 观测推出，不能只凭 `cmd_read` 字段清单定论。历史 runner 用 evaluator-side `model.port_to_peer()` 选择 `leaf_1:eth2/port 3`；它不能替代 Agent 可见证据。下一次 live audit 应留存 task prompt/tool allowlist、真实 `read`/`counters` 原文、必要的只读 host/ARP 输出，以及不读取 evaluator model 的 R0 复算记录。
- `cmd_counters` 可返回所有交换机的 ingress/egress 每端口累计计数；对比测量窗口前后快照即可得到 delta。[`cmd_counters`](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py#L1026-L1039)
- **本地证据缺口：**原运行归档保存了计数快照和测试 harness 推导的 `target_switch`/静态端口映射，但没有保存 Agent 实际调用 `p4rt_exec read` 得到的原始 JSON。因此本次离线规则以 `leaf_1` 为范围，尚不能证明 Agent 可仅由当时实际返回的工具信息确定该范围。未来运行必须同时保存原始工具参数与原始 JSON 输出。

## 同信息计数规则复算

规则只读该窗口目标 leaf 的端口计数快照，计算：

```text
I = 窗口内所有 ingress port packet delta 之和
E = 窗口内所有 egress port packet delta 之和
若 I > 0 且 E = 0：terminal_data_plane_loss
若 I > 0 且 E = I：packet_reached_egress_report_loss
否则：underdetermined
```

没有将 relay 日志、服务端抓包、fault-table 配置、评测标签或隐藏逐包账本传给规则。真值只在规则预测完成后用于评分。复算命令：

```powershell
python research/reliability_reset/experiments/communication_telemetry/replay_nika_public_counter_rule.py `
  --output research/reliability_reset/experiments/communication_telemetry/NIKA_COUNTER_RULE_REPLAY_2026_11_09.json
```

| 条件 | ingress delta | egress delta | 规则预测 | 评测端服务/回执真值 | 是否一致 |
|---|---:|---:|---|---|---|
| report-only sink receipt loss | 376 | 376 | 包已到达 egress，回执丢失 | 服务收到 376 包，relay 丢弃 376 个 sink report | 是 |
| terminal leaf packet loss | 376 | 0 | 终末数据面丢包 | 服务 socket 与 AF_PACKET 均收到 0 包 | 是 |

**离线回放：2/2 条件匹配。**这不是统计准确率，不是盲测，也不是 Agent 比较；两个条件来自同一小拓扑、同一 workload profile 的一组机制运行，且并非逐包 ID 完全相同的重复测量。机器可读输出及输入 JSON SHA-256 见[回放结果](NIKA_COUNTER_RULE_REPLAY_2026_11_09.json)，实现见[回放脚本](replay_nika_public_counter_rule.py)。

## 对更严格压力试验的影响

固定 P4 在 ingress 中先记录普通 ingress counters，再执行终末 loss hook；hook 依据 `packetHash[15:0] < threshold` 丢包，`packetHash` 从 packet length、IPv4 identification 与 flow hash 确定；配置表按 `egress_spec`（端口）索引，随后 egress counter 才计数。loss 参数可设 basis points，故可用原生 P4 对端口上所有流施加确定性哈希阈值子集丢包；它不是五元组选择，也不是外部随机噪声。[loss 参数](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/problems/link_interface/p4_gateway.py#L14-L22) · [hash 与 loss hook](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L170-L179) · [计数与 hook 顺序](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/gateway.p4#L233-L263)

P4 可实现端口级共享背景负载，但这不构成强规则盲区：两臂严格同输入仍需复现相同 packet length、五元组和 IPv4 ID，并记录 report-only relay 命中情况；旧运行的 packet IDs 不同，不能视为 exact-equal trace。更重要的是，不能把“端口故障只丢目标包、同端口背景包通过”设为场景。v1 代数投影正是这样设定，已作废。

### 2026-11-09 投影协议更正

固定 P4 的哈希调用使用 `max=65535`，10000 bp 参数映射为阈值 65535；按 P4 hash extern 的 `base + (h % max)` 语义，写入 16 位比较字段的结果在 0–65534，故 `packetHash[15:0] < 65535` 对该端口所有包为真。数据包计数按“先 ingress 计数、执行端口级损失、再 egress 计数”处理。更新后的脚本与 JSON 将五日 15 个负载档位分别配对到 report-only 和 10000 bp port-wide loss，共 30 个公式场景；结果为计数规则可确定区分 30/30、弃答 0、错误确定 0。这个结果是源码约束的代数推演，不是实时运行或 Agent 结果。

进一步核对 pinned NIKA `src/nika/traffic/burst.py`：`BurstTrafficGenerator(raw_udp=True)` 的发送端仍使用 `socket.socket(AF_INET, SOCK_DGRAM)` 与 `sendto`，并以 `b"x" * size` 生成负载。它能控制五元组、payload 长度和速率，但没有设置 IPv4 identification；固定 seed 只参与五元组选择。因此旧实验 seed 相同不意味着 packet IDs 或 P4 hash 子集相同。项目现有 [telemetry_report_relay.py](telemetry_report_relay.py) 已支持 `(flow_id, packet_id, switch_id)` 精确 drop plan，relay 侧不需新增机制；严格配对的工程缺口在发送端，需要 raw IPv4/pcap replay，并记录每个预定 packet ID 的发送完成情况。

## 决策

1. **冻结低背景规则负对照：**现有配对上公开计数守恒规则已解释全部结果；后续实验不再把这个简单条件当作模型增量测试。
2. **先核验目标映射：**在原生 NIKA 运行中保存完整只读 MCP `read`/`counters` 调用与输出，检查 Agent 是否能从目的前缀和转发表推导目标服务对应的端口计数器。当前数据面/回执配对已由计数规则代数区分，不把 ServDeg 负载档位当成强规则压力盲区。
3. **本机运行限制：**本机未找到 Kathará、Containerlab、Podman、P4 编译器或 BMv2 可执行程序；仅发现 Docker CLI 和 WSL 启动器。本轮没有启动它们。下一次运行需转到已配置的 Linux/Kathará 环境或预先审查的自动化 runner，并在该环境中实现固定 IPv4 ID 的发送端；不能把离线重放写成网络运行。
4. **候选停止条件：**若经严格配对后计数规则在所有预定盲测簇仍可准确区分，终止这个 Agent 机制候选并继续留在通信网络遥测方向内选取经一页门槛审查的问题；不追加模型家族或扩大 NIKA 场景数来回避负结果。

**版本更正：**本报告旧版关于“共享背景压力降低计数规则覆盖”的推进建议依赖不可实现的 v1 投影假设，以上述端口级源码语义及 v2 投影为准。历史旧句不再作为当前研究计划或结论。

### 2026-11-09｜Agent 可见拓扑映射的后续源码审计

此前“p4rt JSON 不含 peer 字段，所以 Agent 可能无法把 service 映射到端口”的限定只描述单个工具响应，忽略了 NIKA 任务提示中的接口级拓扑边，以及默认 MCP 面可查询 service 地址和 P4 counters。固定 commit 的完整调用路径审计确认，该信息在标准配置下对 Agent 可见；旧实验缺少原始 MCP transcript 仍限制逐轨迹追溯，但不再构成下一步假设。具体链路、固定 `topo_size=s` 的端口映射与来源链接见[专门审计](NIKA_AGENT_VISIBLE_TOPOLOGY_MAPPING_AUDIT_2026_11_09.md)。据此，当前低背景 packet/report-loss 配对维持规则负对照，相关实验候选关闭；不改变更广泛的 AI × 通信遥测研究线。
