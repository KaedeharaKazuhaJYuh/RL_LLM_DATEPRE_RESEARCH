# CESNET-TimeSeries26 公开数据源审计

日期：2026-11-08
范围：数据许可、数据规模、事件标签与 Agent 研究可用性。只读取公开元数据及小型 `outages.csv`；未下载时序大文件、未运行 Agent/API、未使用 Docker。

## 结果

### 已核实事实

- Zenodo 主记录 `10.5281/zenodo.21945629` 及四个分卷记录均标为公开访问、CC BY 4.0。五条记录合计约 330 GB；主记录中 10 分钟全 IP 压缩文件约 95.3 GB，故本次不做整库下载。[Zenodo 主记录 API](https://zenodo.org/api/records/21945629) · [Zenodo 分卷 1](https://zenodo.org/api/records/23278901) · [分卷 2](https://zenodo.org/api/records/23280650) · [分卷 3](https://zenodo.org/api/records/23280754) · [分卷 4](https://zenodo.org/api/records/23283552)
- 官方数据页称主数据覆盖 2023-10-09 至 2026-06-30，含 285 个机构、566 个机构子网和 278,466 个 IP；提供 10 分钟、小时、日聚合。完整 10 分钟 IP 文件约 54.6 亿行，公开文档警告旧版读取器存在 int32 行偏移溢出。[CESNET-TimeSeries26 数据页](https://cesnet.github.io/cesnet-tszoo/cesnet_timeseries26/)
- 主记录的小型 `outages.csv` 为 1,418 字节，共 13 条记录：6 条是 2022–2023 年 `subnet_longitudinal` 的 subnet-local `present-zero`，7 条是主数据集的 infrastructure-wide `grid-gap`，发生在 2025–2026 年。2024 年还有一次部分容量下降，论文正文单独讨论、没有列入该 CSV。[Zenodo outages.csv](https://zenodo.org/api/records/21945629/files/outages.csv/content) · [数据集论文](https://arxiv.org/html/2610.14799)
- 数据集论文指出，网络级停测会造成时间网格缺口；观测到的实体窗口是稀疏的，存在监测扩容、DST 重复/合并和未记录短缺口等因素。论文建议不要对长停测段插补。数据集还明确把年周期、概念漂移和长期预测作为其自身研究对象。

### 对研究设计的判断

- **方向一致：**它提供真实、大规模、多年通信遥测，适合后续作为网络 Agent 的外部验证数据源，避免继续依赖单一合成拓扑。
- **不足以作为当前主实验：**主集合只有 7 个被记录的全网停测事件；按事件簇计数远小于数百个独立任务。6 个 subnet-local 事件来自另一条更长、指标较少的时间序列；不能与主集合混作同分布重复样本。把单个事件拆成很多时间窗或实体行不会增加独立故障数。
- **标签捷径风险：**若将 `outages.csv` 直接提供给 Agent，已记录事件近似查表；若隐藏它，仍需定义仅凭公开遥测可识别的真值范围，并把 DST、实体稀疏/生命周期、监测扩容和真实流量异常作为对照。当前发布数据和已审阅资料没有形成足够多、独立且同契约的事件簇。
- **近邻限制：**网络 Agent RCA 已有 CTBench 等直接研究；TelemetrySuffBench 已研究 Agent 遥测视图与失败来源定位；CENTILE 已把遥测预测接到网络配置/调度决策回放。因此“LLM 分析网络时序”“遥测缺失时安全弃答”或“预测误差影响决策”都不能直接作为新贡献。[CTBench](https://arxiv.org/abs/2608.12002) · [TelemetrySuffBench](https://arxiv.org/abs/2608.07899) · [CENTILE](https://arxiv.org/abs/2608.01725)

## 裁决

**数据准入：通过（受限）。科学主张准入：NO-GO，当前只适合作为后续已成立方法的外部验证或数据工程压力测试，不足以单独支撑网络 Agent 的跨事件能力结论。** 不启动 API 实验，不扩成新研究分支，也不改变现有唯一 NIKA 候选的 HOLD。下一步保持同一 AI Agent × 通信遥测主线：先完成 NIKA 同信息强规则与独立故障簇的核心证伪；只有出现稳定且规则无法解释的结果，才把 CESNET-TimeSeries26 用作外部真实数据验证。若未来决定用它作主实验，先形成事件级任务契约和按故障簇划分的冻结方案，再评估需读取的最小子集；不要下载 330 GB 全集。

## 可复核来源与限制

- Zenodo API 五条公开记录均返回 `access_right=open`、`license.id=cc-by-4.0`；该许可只说明发布记录的标注许可，正式复用仍应遵循记录给出的引用与署名要求。
- `outages.csv` 是唯一在本次通过公开接口读取的原始表；未解包 HDF5/CSV 归档，未独立重算全量样本数、缺失模式或论文统计。
- [CESNET-TimeSeries26 官方数据页](https://cesnet.github.io/cesnet-tszoo/cesnet_timeseries26/) · [Zenodo DOI](https://doi.org/10.5281/zenodo.21945629) · [论文预印本](https://arxiv.org/abs/2610.14799)
