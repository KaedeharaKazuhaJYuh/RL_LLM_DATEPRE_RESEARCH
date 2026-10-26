# 1.0.80：一例原生起点核验与候选关闭

日期：2026-10-26。**选定真实 train 任务的起始数据不满足 1.0.75 重复次数反例的必要条件，因此关闭这例任务上的该候选，不进入完整评分实跑。** 不是运行后发现原生评分拦截，也不是证明 AppWorld 没有其他评分缺陷。

## 范围与事先选择

本版执行上一版的一例原生任务核验准备。固定源码提交仍为 `42b5bcf3cd334fee33f0c37c02070a9f5807add5`，源码包声明 `0.2.0.dev0`、数据版本及兼容列表为 `0.2.0`。这只确认静态版本约束相容，未验证完整运行依赖。

先登记 [收集范围](evidence/1.0.80/COLLECTION_PLAN_180.json)，再取得官方 minimal 数据包。选择规则是在查看任务内容前，取官方 `train.txt` 的首个非空条目 `82e2fac_1`。任务 ID 也出现于公开 [test_appworld.py L54](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/tests/package/test_appworld.py#L54)。没有按是否容易出现反例筛选或换任务，没有阅读 test_normal/test_challenge 的任务内容。

数据包实收 **34,908,601 字节**，SHA-256 为 `c9299e6cafe92bce4592a3c117c047c973d1554a667c21dd81537e78ab2f532e`；由固定公开解密函数获得 ZIP，34,908,585 字节，SHA-256 为 `f029a84ad87749864be93c4aec0e8c309b119d129847a59ad4dccab15be7f9cf`。先 HEAD、再用 If-Match 取得同一 ETag 对象，记录见 [数据包收据](evidence/1.0.80/DATA_PACKAGE_180.json)。S3 ETag 不是 SHA-256，上述摘要是本地收件绑定，不是独立认证或上游签名。官方 0.1.3 输出包 HEAD 为 179,524,924 字节，本轮没有下载。

只在本地读取选定任务的原始说明、完整 `evaluation.py`、测试清单、解答原件及 12 份起始增量；不修改或执行受保护的解答／评分代码。25 份任务原件和 12 份基础库均绑定摘要。基础库原字节合计 136,835,072。原数据、任务代码、答案、参数、逐表清单和解密材料均留在忽略目录，不在仓库明文发布；公开记录只提供文件元数据、聚合检查与本项目的结论。

## 起始库重建与决定性证据

[公开 db.py L367–416](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/apps/lib/models/db.py#L367-L416) 规定增量任务先载入基础库，再应用对应 JSONL。诊断对 12 份原基础库逐一使用 SQLite 内存反序列化，再调用**函数体未修改**的公开 [apply_db_changes L341–358](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/apps/lib/models/db.py#L341-L358)。只适配标准 JSONL 读取和类型／导入边界；没有导入 AppWorld、启动 API、执行 ORM 或完整任务评分。

每份增量文件先与原 ZIP 的对应成员比较；即使应为空，也不能缺失。因为上游函数本身对不存在的增量返回空列表，诊断另在边界拒绝缺失文件，防止将不完整输入误当成原生起点。没有修补或放宽原评分器。

| 检查对象 | 本次结果 |
| --- | ---: |
| 任务原件审查／SQLite 起点重建 | 1 / 1 |
| 基础库／原始增量文件 | 12 / 12 |
| 原始增量语句 | 18 |
| 起始库中带 `record_hash` 的表 | 103 |
| 这些表的总行数 | 373,497 |
| 同表内重复哈希组 | 0 |
| 缺失、空字符串或非字符串哈希行 | 0 |

这里读取的是**已存储的哈希**，没有重新执行 ORM 哈希生成器。表、行、SQL 语句不是任务样本或独立家族；没有据此估计真实 Agent 的误判率。完整可重放记录见 [NATIVE_PREFLIGHT_180.json](evidence/1.0.80/NATIVE_PREFLIGHT_180.json)。记录里的计数对应一次规范重建；开发时另做了基础库扫描和一次重建检查，规范工具又作了一次字节重放。这些重复执行均属于同一个原生起点，不增加任务数。

决定性条件是：若某表起点有 `n` 行、`n` 个不同哈希，终点也有 `n` 行且哈希集合相同，那么终点必须将这 `n` 个哈希各放一次。因此两边哈希**多重集**也相同，不能发生 `[a,a,b] → [a,b,b]` 这种重复次数改变。

回归测试用三种内容标签、长度 0–4 的序列穷举核对该条件，独立使用 Counter 作参照；同时保留 1.0.75 的重复起点反例，防止把“本例条件不满足”误写成“辅助函数已正确”。这是基本计数事实及软件控制，不是新算法或科学独立样本。

## 原生任务契约与材料缺口

已在本地审查原始任务完整测试及其通用比较调用，不添加新的历史义务或身份要求。合法工具范围按公开 [Task.load L126](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/task.py#L126) 的非 admin 应用集合理解；`required_apis.json` 是参考解答依赖，不能当成 Agent 的工具白名单。没有实际尝试这些工具。

原始任务专属测试仍不变，原生评分仍是比较对象。但**起点检查不等于完整评分复现**：本轮没有终止库、候选合法工具轨迹、官方原运行日志或分数，没有调用原始 `evaluation.py`。收集的是一例原生任务的准备材料，不是完整官方运行原件包。逐项状态见 [TASK_PACKET_STATUS_180.json](evidence/1.0.80/TASK_PACKET_STATUS_180.json)。

## GO / NO-GO 与适用边界

**本例 NO-GO：不再为重复次数机制构造候选终态或运行完整评分。** 必要条件已由起始库存储哈希否定；追加模型调用不会补回该条件，也不能先改起点或追加原测试未要求的义务来制造证据。

该决定只覆盖 1.0.75 的内容重复次数机制在这一固定起点上的实例化。没有核验哈希碰撞、哈希更新失效、变更计数器异常、ID／关联身份交换、中间事件语义或其他任务起点；这些是不同候选，需要自己的原生契约证据。也没有证明其他任务都无重复或 AppWorld 总体评分正确。

本版不自动转入另一个任务搜阳性。若继续研究，先给出新的、能在既有原始契约下导致实质误判且可执行核验的具体候选，再决定是否值得实跑。没有这样的候选时，保留这次反例收缩和工程复核结果；不把版本数或数据行数当成研究突破。科学状态 HOLD，已关闭的恢复算法主张不重开。

## 复现和工程验证

受保护输入需由复核者在本地从官方 minimal 0.2.0 包取得。使用固定公开 `crypto.decrypt_bytes` 及官方 `constants` 参数产生 ZIP，再只提取 `data/tasks/82e2fac_1/` 至本地工作目录；不公开解密后的内容。不需要安装 AppWorld 即可检查原件：解密需兼容的 cryptography，重放程序本身只使用 Python 标准库。ZIP 摘要和每份增量原件均在 SQL 执行前校验。

```powershell
python -m research.reliability_reset.native_case180 work/reliability-reset-1.0.80/data.local.zip work/reliability-reset-1.0.80/native-case work/native-preflight180-fresh.json
python -W error::ResourceWarning -m unittest tests.test_reliability_reset_native_case180 tests.test_reliability_reset_hash_probe175 -v
```

第一条要求新的输出路径，并拒绝不同输入包、被修改或缺失的增量。没有受保护数据的干净检出仍可执行第二条软件控制测试；不能把这些测试当成真实原生评分运行。

本版新增 8 项测试，初次 16 项新旧诊断测试均通过，但出现本地测试连接未关闭的警告。根因是 sqlite3 的事务上下文不关闭连接，已改用显式关闭上下文；随后警告作为错误的复验通过。最终检查见 [VALIDATION_180.json](VALIDATION_180.json)，冻结摘要见 [PUBLIC_RECORD.json](evidence/1.0.80/PUBLIC_RECORD.json)。此前冻结证据、根 VERSION、原生评分、模型权重和实验分数不变。
