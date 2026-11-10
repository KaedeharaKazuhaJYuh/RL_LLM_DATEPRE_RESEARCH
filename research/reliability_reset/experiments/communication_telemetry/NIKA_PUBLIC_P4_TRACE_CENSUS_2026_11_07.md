# NIKA 公共 P4 轨迹交叉核验

日期：2026-11-07  
用途：确认 NIKA 公共轨迹能否作为当前“末端业务包丢失 vs. sink 遥测报告丢失”假设的外部证据。  
结论：**可作网络 Agent 的 P4 行为参照；不能验证当前配对假设，也不能作为独立论文贡献。**

## 数据来源与复算

- Zenodo 固定记录：[NIKA Traces](https://zenodo.org/records/17971675)。**许可状态更正（2026-11-08）：**直接读取 Zenodo record API 时 `metadata.license` 为 `null`，归档内没有 LICENSE/README 文件。NIKA GitHub 仓库的 MIT 软件许可不能自动推定覆盖该轨迹数据。因此该数据的再利用许可目前未核实；不得在论文或发布包中将轨迹数据标为 CC-BY-4.0，继续公开复用前应取得明确许可信息。此前本报告的 CC-BY-4.0 记载撤回。
- 下载文件：`NIKA Traces.zip`，15,113,410 bytes。ZIP 的 MD5 为 `cc940a7fadd29677d5ef942847a5c45c`，与 Zenodo 文件记录一致；SHA-256 为 `0ca421d15fafc1b94e0344e4fc48c0f3953aedec18682824c1bb713e0fccf71b`。
- 复算脚本直接读取 ZIP 中的 `session_meta.json` 和诊断日志，不展开数据。[脚本](nika_public_p4_trace_census.py) · [机器可读结果](NIKA_PUBLIC_P4_TRACE_CENSUS_2026_11_07.json)
- 复算命令：

```powershell
python nika_public_p4_trace_census.py "NIKA Traces.zip" --output NIKA_PUBLIC_P4_TRACE_CENSUS_2026_11_07.json
```

## 观察到的内容

| 项目 | 结果 |
|---|---:|
| ZIP 中 `ground_truth.json` 记录数 | 906 |
| 对应 `session_meta.json` 记录数 | 904 |
| 有元数据的 P4 场景轨迹 | 36 |
| P4 场景 | `p4_bloom_filter`、`p4_mpls` |
| P4 故障类型 | 6 类；每类 3 个模型、每模型 2 条轨迹 |
| P4 工具调用中显式名含 `int` 或 `telemetry` 的次数 | 0 |
| P4 日志文件缺失 | 0 |

36 条 P4 场景轨迹里，24 条的故障名以 `p4_` 开头，另有 BMv2 switch down 与 MPLS label limit 两类。记录的主要工具是 BMv2 counters、table dump、switch log 和 reachability/ping。脚本统计 `tool_start` 事件；它不将模型自述重算为 NIKA 官方得分，也不从工具名推断日志正文中绝无遥测内容。

### 公开 Agent 的计数器使用和提交文件

- 36 条 P4 轨迹中，35 条至少调用一次计数器工具，合计 95 次计数器工具调用。历史 Agent 已把 BMv2 计数作为实际诊断证据使用；它不支持“让 Agent 第一次学会查看计数器”这一研究主张。
- 28 条轨迹有 `submission.json`，另 8 条缺失，均为 `gpt-oss:20b`。只对现存文件做字段字面比较（列表排序后比较）：`is_anomaly` 27/28、`faulty_devices` 14/28、`root_cause_name` 12/28 完全相同。
- 上述比较是数据结构审计，不是官方评分重放。公开文件使用旧字段 `root_cause_name` / `faulty_devices`；固定 NIKA commit [`ac4422d`](https://github.com/sands-lab/nika/blob/ac4422d8a4a03be2b905e28edf72993d467e1b81/src/nika/evaluator/scoring.py) 的 scorer 读取结构化 `root_causes`，两者 schema 不同。不能将 12/28 等字段匹配数写成当前 NIKA RCA 准确率。

逐轨迹工具计数、提交是否存在及字段比较结果写入 JSON 的 `p4_agent_observation_summary.trace_rows`；其中 `session_id` 对应 Zenodo 归档路径，可逐条复核。

全档案有两条轨迹缺少 `session_meta.json`：`link_fragmentation_disabled/1205174051` 和 `icmp_acl_block/1204172412`。这条目级缺失应保留在数据血缘记录中；它本身不能解释论文主设计 900 次评测与数据发布 906 条轨迹的全部差异。

## 对当前假设的含义

**数据事实：**公开 P4 轨迹覆盖 BMv2/P4 的表项缺失、表项错误、P4 编译/头部定义错误、交换机失效和 MPLS 标签上限。它们属于两个 P4 场景，且没有“最后 leaf→service 数据面丢包”与“sink UDP report 在 collector 前丢失”的配对条件。P4 子集日志没有记录名为 INT/telemetry 的工具调用。

**研究判断：**这些轨迹可用于检查 Agent 在 P4 表、计数器和设备日志上的一般工具使用；35/36 轨迹曾读取计数器，故计数器是现实可用且 Agent 已使用的信号。它们不能提供当前两种末端成因的标签、共享部分轨迹或隐藏账本真值，也没有能与当前固定 scorer 对齐的提交 schema。因此，它们既不能证明 Agent 擅长当前诊断，也不能证明强规则会失败。公开轨迹不替代新建配对任务和外部逐包真值账本。

**样本边界：**36 条不是 36 个独立任务族。它们由 6 个故障类型、2 个 P4 场景、3 个模型和每模型每类 2 次运行组成。当前只做结构和工具事件计数，没有重跑原生 scorer、抽取完整 Agent 文本做人工裁决或计算显著性。

## 下一道研究门槛

1. 使用项目固定 NIKA commit，在隔离 Linux runner 验证 P4 gateway 启动和账本所需接口。
2. 先运行无 Agent 的配对机制检查：逐包确认两个故障条件共享上游 INT 行，账本能分别观察业务包到达、sink exporter 发报、relay 丢弃/转发和 collector 收报。
3. 冻结同信息、同探测预算的确定性规则；在规则无法稳定区分的背景流量下，再准入 Agent 配对运行。
4. 只有配对差异出现并经独立任务重复后，才增加并发流数和报告速率评估规模边界。

当前科学状态保持 **HOLD**。本交叉核验是公开数据的描述性资产审计，不是 Agent 能力提升或新颖性证据。
