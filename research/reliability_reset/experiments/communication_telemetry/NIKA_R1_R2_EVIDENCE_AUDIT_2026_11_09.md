# NIKA R1/R2 可见证据与规则回放审计｜2026-11-09

**范围：**固定 NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 的 P4 接口源码审计，以及 2026-11-07 配对机制运行的离线计数规则回放。
**状态：**低背景配对已由公开计数规则解释，保留为冻结的规则负对照；共享背景压力下的诊断覆盖与额外测量价值继续 **HOLD**。没有 Agent/API 运行。

## 固定源码的可见字段

- `p4rt_exec(args)` 将原始参数交给 `p4rt_manager.py` 执行；接口本身允许任意管理器子命令。若实验规定只读权限，必须在 MCP 前增加参数白名单，不能只在说明里要求 Agent“不要写”。[BMv2 MCP tool](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/mcp/servers/kathara/bmv2_server.py#L13-L19)
- pinned `cmd_read` 默认读取所有配置交换机，返回按交换机名组织的观测；每台设备的观测包含 forwarding members、groups、IPv4 LPM、按端口 ingress/egress counter、寄存器和部分运行时配置。member 暴露 egress port ID，IPv4 LPM 将目的前缀映射到 group，group 再映射到 members；因此服务路由到端口号可由公开转发表推导，但拓扑模型中的 `ports[*].peer` 邻接映射本身不在此 JSON 结构内。[p4rt_manager.py](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py#L552-L676) · [`cmd_read`](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py#L751-L766)
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

这使“有背景流的原生压力测试”在实现上可行，无须先改 P4。但要形成严格同输入配对，需要在两臂复现相同 packet length、五元组和 IPv4 ID，并在 report-only 臂只丢弃与 data-loss 臂相同的 sink report ID；固定 P4 的 hash 结果和 relay 选择器都必须由运行日志验证。旧运行的两臂 packet IDs 不同，不能视为 exact-equal trace。背景流必须和目标流共享被测端口，不能仅增加不经过该端口的流量来制造计数混淆。

进一步核对 pinned NIKA `src/nika/traffic/burst.py`：`BurstTrafficGenerator(raw_udp=True)` 的发送端仍使用 `socket.socket(AF_INET, SOCK_DGRAM)` 与 `sendto`，并以 `b"x" * size` 生成负载。它能控制五元组、payload 长度和速率，但没有设置 IPv4 identification；固定 seed 只参与五元组选择。因此旧实验 seed 相同不意味着 packet IDs 或 P4 hash 子集相同。项目现有 [telemetry_report_relay.py](telemetry_report_relay.py) 已支持 `(flow_id, packet_id, switch_id)` 精确 drop plan，relay 侧不需新增机制；严格配对的工程缺口在发送端，需要 raw IPv4/pcap replay，并记录每个预定 packet ID 的发送完成情况。

## 决策

1. **冻结低背景规则负对照：**现有配对上公开计数守恒规则已解释全部结果；后续实验不再把这个简单条件当作模型增量测试。
2. **推进共享背景压力条件：**严格复现同一 packet-ID 集合，保存原始 MCP 读输出，并在冻结的负载档位上测量计数规则的正确归因、错误归因和弃答覆盖；满足运行与账本验收后再比较模型/测量策略。
3. **本机运行限制：**本机未找到 Kathará、Containerlab、Podman、P4 编译器或 BMv2 可执行程序；仅发现 Docker CLI 和 WSL 启动器。本轮没有启动它们。下一次运行需转到已配置的 Linux/Kathará 环境或预先审查的自动化 runner，并在该环境中实现固定 IPv4 ID 的发送端；不能把离线重放写成网络运行。
4. **候选停止条件：**若经严格配对后计数规则在所有预定盲测簇仍可准确区分，终止这个 Agent 机制候选并继续留在通信网络遥测方向内选取经一页门槛审查的问题；不追加模型家族或扩大 NIKA 场景数来回避负结果。
