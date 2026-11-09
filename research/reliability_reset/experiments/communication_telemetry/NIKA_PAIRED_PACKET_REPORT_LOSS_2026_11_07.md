# NIKA 配对故障机制核验｜2026-11-07

## 结论

在 pinned NIKA 小型 `p4_dc_gateway` 拓扑中，使用同一四条固定五元组 UDP 流配置（seed 20261107、32 Kbit/s、128 B、3 秒）完成了 report-only 与 leaf→service 丢包两臂。两臂的 collector sink 行均为零，但业务包实际到达状态不同：report-only 臂服务端逐流收到 94 包，并由 relay 丢弃同 ID 的 94 条 sink report；真实 leaf 丢包臂服务端收包为 0。两臂 collector 都得到每流 188 条上游记录、零 sink 记录。

这个低背景受控条件下，公开 P4 端口计数已经区分两臂：目标 leaf 服务端口 3 的 egress packet delta 在 report-only 为 376，在真实 leaf loss 为 0；两臂观察到的 ingress delta 一致（端口 1 为 282、端口 2 为 94）。这给出低背景下 R0 可解的负对照：受控窗口内 target service-facing egress 计数为 376/0，直接区分了这一次配对。它是对公开计数上限的观察，并非已在独立开发簇冻结、多次评估的 baseline。当前不支持“Agent 在该条件下有额外诊断价值”。

## 逐流结果
- `28a4463f718872b0`：报告丢失臂服务端包 94，真实丢包臂服务端包 0，两臂 collector 行数 188/188，两臂 collector sink 报告 0/0。
- `5560a874d0f2acfe`：报告丢失臂服务端包 94，真实丢包臂服务端包 0，两臂 collector 行数 188/188，两臂 collector sink 报告 0/0。
- `f6e760d978c438b2`：报告丢失臂服务端包 94，真实丢包臂服务端包 0，两臂 collector 行数 188/188，两臂 collector sink 报告 0/0。
- `fde41913c03f2870`：报告丢失臂服务端包 94，真实丢包臂服务端包 0，两臂 collector 行数 188/188，两臂 collector sink 报告 0/0。

## 运行记录

- NIKA commit：`ac4422d8a4a03be2b905e28edf72993d467e1b81`；Kathara `3.8.3`；四流、单一小型拓扑、单次 paired workload。
- report-only relay：收到 1128 条报告，转发 752，按计划丢弃 376 条 sink 报告；collector 收到 752 行。
- leaf-loss relay：收到并转发 752 条报告，丢弃 0；collector 同样收到 752 行。
- report-only 四流各有 94 个服务端 UDP 收件；AF_PACKET ID 与 relay-dropped sink-report ID 在 RUN4 中逐流精确匹配（每流 94/94）；原始记录保留逐包 ID。
- leaf-loss 四流 AF_PACKET 与应用 socket 收件均为 0；P4 两个 service-facing loss 表项验证为阈值 65535。目标服务 TCP probe 的 port-3 egress 为 0，VIP HTTP 三次失败。
- 容器退场成功，`lab_closed=true`，没有残余 Kathara 拓扑容器。此处 `passed=true` 只表示预定的有界运行和清理完成。

## 解释边界

- 两臂匹配的是 workload/flow profile，不是相同的逐包 IP IDs；packet IDs 在不同 burst 间自然不同。
- 单次、单拓扑运行不能说明跨拓扑或真实网络中的稳定性，也不能支持论文 headline。
- 同一批受控背景下，端口计数已解决机制区分；不应再为这个低背景案例调用模型。
- 下一步仍在 AI × 通信遥测方向内：若继续研究 Agent 额外价值，应先预注册未知/并发背景下对 R0/R1/R2 的压力测试，明确计数窗口、拓扑可见映射与同信息约束；只有强规则在独立 workload cluster 上出现可复核失败，才有理由准入 Agent 配对。
