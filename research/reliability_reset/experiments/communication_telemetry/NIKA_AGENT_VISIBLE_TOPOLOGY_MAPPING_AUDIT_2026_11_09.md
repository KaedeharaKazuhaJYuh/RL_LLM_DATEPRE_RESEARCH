# NIKA Agent 可见拓扑与端口映射审计｜2026-11-09

## 目的与范围

核验“`p4rt read` 不含端口邻接表，因此 Agent 不能把服务映射到计数器”的说法。审计固定 NIKA commit `ac4422d8a4a03be2b905e28edf72993d467e1b81` 的任务提示生成、Agent 调用链、MCP 服务器注册、`p4_dc_gateway` 小拓扑端口构造及 P4 读接口。未运行 Agent 或网络实验；以下是代码路径审计与按固定拓扑源码计算的可见性结论。

## 审计结果

### 1. 任务提示已经暴露接口级拓扑

- `ProblemBase.get_task_description()` 将 `net_env.get_info()` 插入诊断任务文本。
- `NetworkEnvBase.get_info()` 输出角色清单以及 `Topology: (node:ethX, node:ethY)` 边表。
- `get_topology()` 遍历 Kathara 实际声明的机器接口，并将 link 两端格式化为带接口名的节点对。
- 故障注入工作流保存此 `task_description`，Agent 工作流把该字段原样传给 `run_agent()`。

因此，拓扑邻接不是只存在于 evaluator 私有对象，也不依赖 `p4rt read` 单独返回 peer 字段。Agent 初始上下文即可看见如 `leaf_1:eth2` 与服务节点相连的拓扑边。源码：[ProblemBase](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/problems/base.py) · [NetworkEnvBase](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/base.py) · [Agent workflow](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/workflows/agent/run.py) · [fault injection workflow](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/workflows/failure/inject.py)

### 2. 诊断工具允许查询服务和 P4 状态

固定 MCP 注册逻辑对所有诊断会话启用 Kathará host server；`p4_dc_gateway` 的场景 token 使 BMv2/P4Runtime server 注册。host server 提供 `exec_shell(host_name, command)`；默认访问策略允许全部工具和节点角色，除非运行配置显式收紧。BMv2 server 提供 `p4rt_exec(args)`，可读 forwarding entries 和 per-port counters。因而规则可从服务节点查询实际 IP/MAC，再结合任务提示中的拓扑和 P4 转发表/端口计数构造可审计映射；这个信息面与 Agent 共享。

源码：[MCP registry and server selection](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/mcp/registry.py) · [host tools](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/mcp/servers/common/host_server.py) · [BMv2 tool](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/mcp/servers/kathara/bmv2_server.py) · [default access policy](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/run_config/schema.py)

### 3. 当前 `topo_size=s` 的映射可由固定拓扑顺序推出

固定 `SIZE_TABLE["s"]=(2 gateways, 2 spines, 2 leaves, 2 clients, 4 services)`；每个 leaf 先按 spine 顺序连接两条 spine-facing 接口，再按服务顺序连接其两个服务。接口索引 `ethN` 对应 BMv2 port `N+1`。所以该版本固定小拓扑中，`leaf_1` 的端口构造顺序是：`eth0→spine_1`、`eth1→spine_2`、`eth2→service_1_1`、`eth3→service_1_2`；service-facing `eth2` 对应 BMv2 port 3。`service_1_1` 的地址构造为 `10.0.1.11`，其 leaf 路由前缀为 `10.0.1.0/24`。

这部分既可从 Agent 收到的拓扑边直接读出接口 peer，也可用 `exec_shell` 查询服务地址/MAC，再同 `p4rt read` 的 prefix→group→member/egress port 与 counters 对照。后者不需要向 Agent 提供 evaluator 的 `model.port_to_peer()` 或隐藏故障标签。源码：[P4 topology model](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/topology_model.py) · [P4 lab construction](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/p4_dc_gateway/lab.py) · [P4 read/counters](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/net_env/utils/kathara/p4rt_manager.py)

## 对研究假设的影响

1. “Agent 看不到服务到端口的映射”不成立；此前把 `p4rt read` 的单个 JSON 结构误当作 Agent 全部上下文。历史 Agent 原始工具输入/输出未存档，限制了对**已发生轨迹**的追溯审查，但不改变 pinned 代码中任务提示和 MCP 权限实际暴露这些信息的事实。
2. 在当前双故障任务契约下，10000 bp 端口级数据面故障使目标 service-facing egress counter 为零；report-only 故障下业务包通过且计数增加。结合显式拓扑、服务节点查询、P4 read/counters，冻结的 same-information 规则可以定位并区分两臂。先前离线 replay 2/2 与源码投影 30/30 均支持“当前简单场景已被强规则解释”，但它们仍不是多任务簇的运行评估。
3. 当前终末 packet-loss vs. sink-report-loss 配对没有可支撑 Agent 独立增量的接口盲点。停止扩大该场景矩阵；保留它作为机制/规则负对照，并把主要研究问题留在 AI Agent × 通信网络遥测与运维。此结论不代表整个研究方向 NO-GO，也不代表已有跨任务科学验证。

## 下一步研究准入

下一项候选须提出一个不同且具体的通信运维决策问题，并在一页门槛中预先给出：Agent 任务提示/工具可见信息；同信息确定性规则或经典网络诊断基线；独立任务/拓扑簇；可量化的安全/业务结果与测量成本；近邻工作逐项差异及能否证伪的预测。在这些项目完成前，不启动新 Agent/API 实验，也不把当前配对包装为论文贡献。
