# CESNET-TLS-Year22 持续学习数据契约审计

审计日期：2026-11-09  
数据源：CESNET-TLS-Year22   
DataZoo 源码快照：`CESNET/cesnet-datazoo` commit `85afe5613a9a1ea840d174d779042ee13f87b4e2`  
范围：只读审查数据论文、公开元数据及 DataZoo 源码；本次未下载 CESNET 流量文件，未训练模型。

## 已核实的事实

1. CESNET-TLS-Year22 覆盖 2022 全年，发布 180 个 Web 服务标签，约 507,739,073 条流；提供流统计、前 30 个包的序列、包直方图和 TLS ClientHello 字段。起止时间按小时取整，服务标签由 TLS SNI 标注流程产生。[数据论文](https://www.nature.com/articles/s41597-024-03927-4) · [官方 DataZoo 元数据](https://cesnet.github.io/cesnet-datazoo/dataset_metadata/)
2. 采集和发布流程不是“每个服务等比例随机采样”：采集阶段按服务流行度使用动态采样率，之后又对数据作统一 1:10 抽样。因此，发布标签比例不能直接解释为网络中的真实服务先验；论文的类均衡/加权必须与生产流量占比分开报告。[数据论文](https://www.nature.com/articles/s41597-024-03927-4)
3. 数据论文确认存在两类不同时间变化：第 6 周 peering 链路恢复引发服务占比变化、假期对应周期性变化；第 10 周（2022-03-07 至 03-13）则因 `ipfixprobe` 更新、开始跳过重传包而改变包序列分布。论文建议将第 1–9 周与第 11–52 周分开，避免将测量管线变化误当成自然流量漂移。[数据论文的漂移分析](https://www.nature.com/articles/s41597-024-03927-4)
4. DataZoo 源码在初始化 Year22 时也发出第 10 周警告。固定源码快照中，`CESNET-TLS-Year22` 的默认训练/测试 period 为 2022 年第 9、10 月；这些默认值不是本研究所需的月度持续学习协议。
5. DataZoo 的默认 validation approach 是从训练数据随机分层切分。该设置会使验证样本与训练来自同一组日期，不能用于前向时间验证。配置支持显式日期周期/日期及 `VALIDATION_DATES`。
6. DataZoo 公开 `XS/S/M/L` 档，源码分别将规模定义为 10M、25M、50M、100M。DataZoo 通过先随机化索引再取所需训练规模的方式构造指定 `train_size`；亦支持 `train_dates_weights` 按日期抽取。源码和尺寸常量不证明任一档在每个月、每个服务上均有足够支持数，必须在实际选定的档案上统计并冻结日期×类别覆盖。
7. 文中列出的可用字段包含 `TLS_SNI`、服务标签、时间戳及网络端点字段。SNI 是标签生成链路的一部分，必须从输入中排除；时间仅用于有序切分/分组；源/目的地址、端口、ASN、JA3 等应逐字段审查其是否成为服务身份捷径。数据论文说明客户端地址经加盐哈希，可用于隐私保护下的用户分组；本研究仍须实测其跨日期稳定性及组间泄漏。

## 对研究协议的直接约束

### 归档可获取性探测（2026-11-09）

- DataZoo 官方下载端点对 CESNET-TLS-Year22 XS HDF5 文件接受 1 字节 HTTP Range 请求，返回 `206 Partial Content`，报告完整长度 `2,692,800,942` 字节。探测文件只保留 1 字节，不包含数据样本。
- 官方 Zenodo 原始归档列出 `CESNET-TLS-Year22.zip` 为 `30,491,259,088` 字节，另附 24,817 字节 `servicemap.csv`；本研究不默认下载 30.5 GB 原始归档。[Zenodo API 记录](https://zenodo.org/api/records/10608607)
- XS 完整下载尚未完成；官方端点确认 Range 可读，但当前连接慢且并行大范围请求没有稳定完成。仓库外保留未拼装的 Range 分片，供后续续传；DataZoo Python 包及 PyTables 当前未安装，故尚未检查 HDF5 结构或统计日期×类别支持数。目录位于 `C:\Users\jyuh1\Datasets\CESNET-TLS-Year22\XS`。
- XS HDF5 无单独公开 SHA-256 清单可由当前记录直接核验；下载完成后必须跑 HDF5/Table 完整性检查，并对文件记录 SHA-256、来源 URL、字节长度和 DataZoo 源码 commit。仅 HTTP 长度匹配不等于文件完整性验证。

### 主实验：自然的跨期服务流量变化

- 不跨第 10 周合并训练和测试。主分析限定在第 11–52 周，按严格时间前推的月或周分段；第 1–9 周另作独立前期区间，不与第 11 周后数据拼成一个连续同分布流。
- 训练/适配/验证/测试窗口必须由明确日期列出。每个测试时间段晚于所有用于该次模型更新的样本；调参验证也必须来自更早但独立的时间窗，不能调用默认随机分层 validation。
- 真实服务先验并非由发布样本频率直接表示。主结果同时报告原发布分布指标和按服务类宏平均指标；以标签预算抽样造成的类均衡结果单独标注。
- 以“同等标签数、同一日期样本、同一更新计算预算和同等记忆字节”配对 ANN 与 SNN。流序列输入必须相同；统计特征模型另列，不能充作 SNN 的唯一 ANN 对照。

### 单独的测量管线变化压力测试

第 10 周作为有公开来源解释的 measurement-pipeline shift 单独测试。它不是自然网络流量概念漂移，也不能混进主结果后再统一解释。报告包重传相关特征及其移除/替换后的结果；检验模型是否把采集器版本特征当成服务身份。主文应将该部分标为测量流程压力测试，而非自然漂移泛化证据。

### 规模与子集冻结

1. 先核验本地归档及许可，再选最小档；审计工具输出所选档每月/每日样本数、服务标签数、缺失日期、每类支持数和包序列长度分布。
2. 若尺寸档不能提供预注册窗口的最低支持数，用 DataZoo 显式日期配置和每日期权重选取可复现子集，并保存逐日期、逐服务计数与随机种子；不可默认按全局随机子集模拟月度流。
3. 冻结 `datasetzoo` Python 包版本、数据库及服务映射文件哈希、所有字段转换参数、时间窗口、标签映射和样本索引 manifest。只对训练期拟合归一化参数。
4. 每月的少标签适配例只从当月适配窗口抽取。测试期样本、未来服务频率、未来的归一化统计和未来标签不能进入采样/调参逻辑。

## 关键来源

- CESNET 数据论文（包括采样、字段匿名化、时间漂移与第 10 周 exporter 变更）：[Scientific Data 2024](https://www.nature.com/articles/s41597-024-03927-4)
- [CESNET DataZoo 官方文档与元数据](https://github.com/CESNET/cesnet-datazoo)
- 源码审计快照：[`cesnet_dataset.py`](https://github.com/CESNET/cesnet-datazoo/blob/85afe5613a9a1ea840d174d779042ee13f87b4e2/cesnet_datazoo/datasets/cesnet_dataset.py)、[`config.py`](https://github.com/CESNET/cesnet-datazoo/blob/85afe5613a9a1ea840d174d779042ee13f87b4e2/cesnet_datazoo/config.py)、[`constants.py`](https://github.com/CESNET/cesnet-datazoo/blob/85afe5613a9a1ea840d174d779042ee13f87b4e2/cesnet_datazoo/constants.py)、[`indices_setup.py`](https://github.com/CESNET/cesnet-datazoo/blob/85afe5613a9a1ea840d174d779042ee13f87b4e2/cesnet_datazoo/pytables_data/indices_setup.py)
- [官方数据集使用指南](https://cesnet.github.io/cesnet-datazoo/)

## 决策

数据源满足长期真实流量研究需要，进入本地元数据与小规模归档审计。它同时要求将自然流量变化与已知测量管线变化拆开。下一项工程产物是**按时间窗×服务类的公开元数据 census 和冻结 split manifest**，之后运行 ANN 时间前推基线；在此之前不需要搭建复杂 SNN 或下载 507M 全量流。

