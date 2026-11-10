# ServDeg 单日高基数遥测可行性审计

日期：2026-11-08
目的：判断许可明确的公开网络流数据，能否为当前 AI Agent × 通信网络遥测研究提供真实负载分布或独立根因真值。
结论：**可作为统计性流负载参考；不能作为真实包回放、拓扑根因标签或当前 NIKA 配对假设的验证集。**

## 来源与复现

- 数据集：[ServDeg Zenodo 记录](https://zenodo.org/records/21983587)；随数据发布的 `README.md` 明确标注 CC BY 4.0。[数据 README](https://zenodo.org/records/21983587/files/README.md?download=1)
- 本轮只下载 `MON.parquet`，未下载其余四日数据；原始文件和独立 DuckDB 环境放在被 Git 忽略的 `work/servdeg_eda_2026_11_08/`。
- 文件大小：500,075,664 bytes；MD5：`833e7b9c411358011bad3172ee541a55`；SHA-256：`6f1a157f67523660247404ea9c19f901fa72d73c74e5578aaad38b3ff80bcff6`。
- 使用 DuckDB 2.0.0 对 Parquet 做列式汇总，未读取或输出匿名化地址、MAC 或逐流身份。复算程序：[audit_servdeg_workload.py](audit_servdeg_workload.py)；机器可读结果：[JSON](SERVDEG_MON_WORKLOAD_AUDIT_2026_11_08.json)。
- 复算命令：

```powershell
python audit_servdeg_workload.py MON.parquet --output SERVDEG_MON_WORKLOAD_AUDIT_2026_11_08.json
```

## 本次观测

| 指标 | MON 文件结果 |
|---|---:|
| Parquet 列数 | 110 |
| Flow 行数 | 3,185,436 |
| 文件中 `location` 标签数 | 17 |
| 聚合 flow 时间范围 | 2024-01-15 19:24:40 至 20:18:29（53 分 49 秒）|
| `protocol=6` | 3,185,436（全部为 TCP）|
| 至少一个 `SDd` 点标记的 flow 行 | 85,899（2.70%）|
| 至少一个 `SDj` 点标记的 flow 行 | 87,684（2.75%）|
| `SD_count > 0` 的 flow 行 | 8,907（0.28%）|
| Web 类 flow 行 | 2,088,722（65.57%）|
| 有持续事件序列的行中 Web 类 | 7,231 / 8,907（81.18%）|

流量呈强偏态：双向包数中位数 6、P90 40、P99 1,533、最大 6,928,103；双向字节数中位数 452、P90 14,719、P99 约 1,293,566、最大 6,443,883,860；流时长 P99 约 984 秒，最大 1,800 秒。该分布足以说明均匀小流负载不能代表此文件的统计形状，但目前只有 MON 一天，不能据此做跨日结论。

## 研究边界与候选影响

1. **可支持的用途：**以匿名 flow 统计特征构造并明确标注为 *trace-derived synthetic workload* 的负载分布；或另行设计对流级统计、时延/抖动点标记和持续事件序列的离线查询任务。
2. **不能支持的用途：**该文件是 Parquet 聚合流特征，不含可直接回放的原始包序列或路径/交换机根因标签；因此不能宣称真实 PCAP 回放、真实设备故障注入或因果 RCA 真值。`protocol=6` 也不能直接替代 NIKA 现有 UDP 目标流设置。
3. **标签单位不同：**点级 `SDd`/`SDj` 标记约覆盖 2.7% 的 flow 行，而 `SD_count` 持续事件序列只覆盖约 0.28%。它们不是可互换分母。这个差异来自原始数据定义；它本身不是 Agent 缺陷或新颖性证据。
4. **对当前主候选：**可用于后续设定合成背景流量分布，但必须单列转换过程、包数/速率保真度和同信息强规则；由于没有原始包、路径和故障标签，本次数据审计不清除 NIKA packet-loss/report-loss 候选的 HOLD，也不授权模型实跑。

## 决定

这是数据源可行性与分析单位审计，不是 Agent 能力实验或独立论文贡献。当前候选仍 **HOLD**。下一步若要把该数据用于 NIKA 背景负载，先核对其余四日的分布稳定性，并在离线生成器上验证 trace-derived 转换保持哪些量、丢失哪些量；只有强规则在等信息条件下出现明确盲点，才重新评估 Agent 实跑准入。整个过程不依赖本机 Docker。
