# NetOpsBench v0.2 公开轨迹时间证据复核

日期：2026-11-07  
研究主线：AI Agent × 通信网络遥测与运维。本文是该主线内的外部证据复核，不引入新方向，也不把复算结果当作论文贡献。

## 问题与数据来源

检查 NetOpsBench v0.2 的公开轨迹：一个只读取 Agent 初始上下文中 `anomalies_detected` 单一布尔字段的零工具规则，对二元 fault/healthy 判断能达到什么水平？此外，复核 packet-loss 轨迹中“历史异常与当前探测”之间的时间顺序。

- NetOpsBench 源码固定在 commit `d121e55b51f317b9f6bc684be0745184457740b8`。
- Hugging Face 轨迹集固定在 dataset revision `f7ef8e5ecde5eba030c9b4cd9ec4cda7703edc42`；v0.2 发布项包含 7 个尺度、319 个已评分案例及 319 条 ATIF 轨迹。上游结果页称该快照使用单一 `minimal-deepagent / deepseek-v4-pro` 配置。[上游结果](https://github.com/NetX-lab/NetOpsBench/blob/main/docs/content/docs/run-benchmarks/results.mdx) · [轨迹集与发布说明](https://huggingface.co/datasets/yyyyyt/netopsbench-trace)
- 本地下载清单 SHA-256：`1d9feb3cd32e90e79ee4c1496d69a487573b95caab5b12a71909f03e725b96f3`。
- 复算逐案 CSV SHA-256：`d43150174d7982b6358367289195e2587c64050bfc7da0e0b0a86cd84ea27627`。
- 端点匹配 ping 事件 CSV SHA-256：`a64fa81469b2a5cfa3d9a07f116769ed31f53419cefbcd0428a34108e50cd467`。
- 原始归档保留在本机临时目录，未复制进仓库；仓库只保存脚本和派生逐案表。上游 pinned manifest 提供各归档 SHA-256。

## 规则和评分范围

基线规则严格限定为：若 Agent 初始用户上下文中可见 `anomalies_detected=true`，输出 `fault_detected`；否则输出 `network_healthy`。与同一案例的上游二元 ground truth 比较。规则只使用 Agent 可见初始上下文的一个字段，不调用工具、不定位根因或设备/接口，也不输出 `inconclusive`。这是 Agent 可见信息的**子集基线**，并非拿到了完全相同全部观察与工具预算的强规则；结果只比较**二元 verdict**，不能解释成全面诊断能力或完整任务分数，也不能证明强规则公平配对实验已完成。

## 复算结果（描述性）

| 案例 | Agent | 单字段零工具规则 |
|---|---:|---:|
| 全部 v0.2，319 案例 | 227/319（71.2%） | 274/319（85.9%） |
| packet-loss，26 案例 | 5/26（19.2%） | 25/26（96.2%） |

在 319 个配对案例中，两者同对 193 个案例判断正确、同错 11 个；仅规则正确 81 个，仅 Agent 正确 34 个。规则的混淆矩阵为 TP=249、FP=0、FN=45、TN=25。它在 packet-loss 上很强，但遗漏其他 45 个故障案例，不能称为通用基线最优。

| 尺度 | 案例数 | Agent verdict 正确 | 规则 verdict 正确 | packet-loss（Agent / 规则） | 有至少一次同源目的端点 ping |
|---|---:|---:|---:|---:|---:|
| XS | 14 | 13 | 12 | 1/1 / 1/1 | 1/1 |
| Small | 15 | 14 | 14 | 1/1 / 1/1 | 1/1 |
| Medium | 28 | 22 | 26 | 1/2 / 2/2 | 0/2 |
| Large | 52 | 39 | 48 | 0/4 / 4/4 | 4/4 |
| Xlarge | 70 | 49 | 49 | 1/6 / 5/6 | 4/6 |
| Fat-tree K=8 | 70 | 48 | 66 | 1/6 / 6/6 | 5/6 |
| Fat-tree K=12 | 70 | 42 | 59 | 0/6 / 6/6 | 5/6 |

上游结果页已报告 packet-loss 的正式信号为 25/26、正确 verdict 为 5/26，也已将“把 episode 窗口证据与恢复后的 live state 混合”和“用一次成功 ping 否定历史多 hash 丢包”列作轨迹失误。因此，本复算是对已有公开现象的**单字段基线对照和定量复现**，并非首次发现该失败模式，也不是完整信息/权限匹配的强规则比较。[上游 packet-loss 结果与错误分析](https://github.com/NetX-lab/NetOpsBench/blob/main/docs/content/docs/run-benchmarks/results.mdx)

## 时间顺序复核

固定源码的调用顺序为：`ExecutorIncidentBackend.prepare()` 调用 `observe_episode()`；故障注入及 episode 观测在此完成。随后 `ScenarioExecutor.run_scenario()` 才执行 diagnosis callback。故障恢复由 `IncidentEngine.close()` 持有，close 在诊断回调和提交结束后的 `finally` 中运行。`episode_runner.py` 也明确说明 episode observation 阶段不做恢复，恢复属于 incident close。源码：[incident backend](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/scenario/incident_backend.py) · [scenario executor](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/scenario/executor.py) · [episode runner](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/scenario/episode_runner.py) · [incident close](https://github.com/NetX-lab/NetOpsBench/blob/d121e55b51f317b9f6bc684be0745184457740b8/netopsbench/platform/incident/engine.py)

逐案按 Pingmesh anomaly 的 source/destination 主机名和 IP，与 Agent 的 `ping_test` 参数比对：26 个 packet-loss 案例中，20 个至少有一次 ping 使用了与某个历史异常相同的端点对（正向或反向）；其中 18 个 Agent 最终 verdict 仍错误。进一步把这些案例的 ATIF `ping_test` 工具结果按 `tool_call_id` 去重，并解析每条结果中的发送/接收数：20 个案例共含 57 条端点匹配结果，累计 490 个包已发、433 个收到。它们嵌套于 20 个案例，不是 57 个独立样本。关键是这 20 个案例的初始 `anomalies_detected` 全为 true，ground truth 全为故障；原有单字段零工具规则因此在该子集 **20/20** 正确，而 Agent 仅 **2/20**。规则在两个 ping 子组也分别为 all-clean 13/13、any-loss 7/7；这组现象不需要额外 ECMP 推断即可复现。

端点匹配子集呈现两种不同的可见轨迹模式：13 个案例的所有匹配 ping 均无丢包，其中 12 个 Agent verdict 错误（11 次判为 `network_healthy`、1 次 `inconclusive`）；7 个案例至少一条匹配 ping 报告丢包，其中 6 个 Agent 判为 `inconclusive`、1 个 `fault_detected` 且二元 verdict 正确。此为对单一上游模型轨迹的描述性分类；不能据此推断普遍的“过度弃答”或 Agent 相对规则的独立效应。26 例中其余 6 例没有端点匹配 ping。

端点匹配只核对主机/IP，不代表 ICMP 标识、ECMP hash、受影响物理接口或探测窗口相同。固定源码中的 `ping_test` 接口可设源、目的、包数（上限 20）、负载大小和 DF，但没有暴露可指定/记录的 ECMP 流标识；固定拓扑配置则为 Pingmesh 定义 16 个 RTT 端口池及按拓扑每周期探测 4 或 8 个端口。故公开轨迹不能确认 Agent ping 覆盖了 Pingmesh 的流/路径样本，也不能反向证明路径哈希差异就是错误原因。源码调用顺序确认诊断在故障 episode 观测后执行、恢复在 incident close；该证据不是“自动恢复后”探测。K=12 案例 `case-48ed00f134a6` 的 Pingmesh 窗口为 `13:26:49Z–13:28:43Z`；Agent 约在 `13:30:34Z` 查询 client68→192.168.165.2，并在提交前声称“transient loss has resolved”。现在可以把问题缩窄为：**历史 Pingmesh 多端口/多流采样与单次当前 `ping_test` 在覆盖对象和时间窗上的差异，是否足以解释各类错误 verdict？**

## 数据与推断限制

- 319 个案例来自 7 个尺度的生成式场景；独立任务簇结构不足以支持把 episode 当作独立样本作显著性检验。本文只报告描述性配对计数，不提供 p 值或显著性结论。
- 单一 Agent 配置；此处没有新模型运行、API 调用或模型干预。
- 66 条初始上下文达到/超过 200,000 字符边界。规则只依赖靠前的 `anomalies_detected` 字段；这些长上下文的其余内容存在截断风险，不能据此断言完整上下文都被逐字复核。
- 布尔 anomaly 基线是低成本诊断规则，不等同于最强可能规则；它的可用性依赖上游公开暴露该字段。
- packet-loss 子集只有 26 个案例，且单一规则胜出不能证明新的机制、跨模型稳定性或工程选择影响。

## 对固定研究主线的影响

该复算把“时间/对象错配”拆成两类错误轨迹：无丢包 ping 后错误判健康，与看到丢包后弃答。但在所有端点匹配案例中，初始单字段规则已 20/20 正确；继续追查 hash/路径不会改变这个 verdict 对照，也不能把上游已公开的 5/26 失败升级为新贡献。因此关闭本轮 NetOpsBench 公开轨迹的扩展归因，不继续追加针对这 26 条样本的分析。事件级派生数据保留供审查。研究工作回到唯一固定候选：完成 pinned NIKA 两种末端故障的完整运行时账本、检查同信息计数器/遥测规则在预注册可识别性分层里的表现；只有规则存在重复、可解释且独立任务簇稳定的盲点时，才设计 Agent 配对实验。当前研究状态 **HOLD**，不启动模型/API。

## 复现

使用与上述 revision 相同的公开归档，解压各 v0.2 archive，使每个 `run_id` 目录位于同一 `extracted-root` 下，并保存发布 manifest CSV。然后执行：

```powershell
python research/reliability_reset/experiments/communication_telemetry/audit_netopsbench_v02_traces.py `
  --manifest <path-to-v0.2-manifest.csv> `
  --extracted-root <path-to-extracted-run-directories> `
  --output research/reliability_reset/experiments/communication_telemetry/NETOPSBENCH_V02_CASE_AUDIT_2026_11_07.csv `
  --ping-output research/reliability_reset/experiments/communication_telemetry/NETOPSBENCH_V02_MATCHED_PING_EVENTS_2026_11_07.csv
```
