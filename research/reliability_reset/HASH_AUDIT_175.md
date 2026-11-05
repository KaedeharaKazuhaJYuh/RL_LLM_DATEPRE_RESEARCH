# 1.0.75：记录哈希与多重集盲区的隔离复现

日期：2026-10-26。**确认了公开状态比较辅助函数的一个合成输入反例；尚未确认 AppWorld 完整任务评分的真实假成功。** 本版没有改动 AppWorld 原函数、原任务或历史分数。

## 结论与上一版更正

哈希排除了主键 ID，既有比较也有意允许同内容记录删除后重建。这一设计本身不足以构成漏洞。但在总行数不变、内容哈希集合不变而重复次数变化时，两项原辅助函数都可能返回“无变化”；这比单纯 ID 变化更窄，也不依赖给任务追加历史义务。

1.0.70 将待核验哈希定义描述为位于受保护实现，这一点不准确。实际定义在公开的 [`src/appworld/apps/lib/models/orm.py` L1074–1087](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/apps/lib/models/orm.py#L1074-L1087)。本版明确更正；不改写已冻结的 [1.0.70 原报告](APPWORLD_AUDIT_170.md)及证据。

## 固定源码与许可范围

继续固定官方提交 `42b5bcf3cd334fee33f0c37c02070a9f5807add5`。本轮新增读取 6 份公开明文文件／LFS 指针，复用 1.0.70 的公开比较源码、常量、README 和许可。逐个文件与固定 Git tree 核对，定位见 [SOURCE_MANIFEST_175.json](evidence/1.0.75/SOURCE_MANIFEST_175.json)。

为检查实际模型约束，另外读取了官方应用源码加密包：193,950 字节，SHA-256 为 `88d21fc526c1655bb3eee4adfca78ccac793921e4506f28f734ecdb19af77a62`，与固定提交的 LFS 指针一致。使用官方公开的解包参数及兼容的本地 .NET 解码读取源码，未调用安装器、执行受保护应用代码、下载任务／任务生成器包或运行 AppWorld 环境。解码后的内容仅在本地忽略目录；不公开受保护源码或逐类派生清单。

本地静态约束核验发现，不能从唯一性声明得出“所有内容哈希必然唯一”的全局保证。但声明为空**不证明**真实 API 可以创建该反例：字段、自验证、时间戳、关联关系与操作约束仍可能阻止它。公开记录保留原加密包定位、汇总状态和本地清单摘要，不将这些检查计作任务样本。

仓库内的 [公开函数摘录](fixtures/appworld_175_excerpt.py)仅来自 Apache-2.0 明文部分；附有[原许可](fixtures/APPWORLD_LICENSE)和[来源／摘要](fixtures/appworld_175_source.json)。不含受保护模型实现。

摘录目录单独保留原始字节，避免 Windows 换行转换破坏源码与许可摘要。该设置仅位于新增目录，不修改根目录的历史 CI 集成规则或冻结清单。

## 根因链与对照

1. [ORM L1074–1087](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/apps/lib/models/orm.py#L1074-L1087) 对除 ID、内部路径和自身哈希外的属性生成内容哈希。
2. [ModelCollection L122–130](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/collections/models.py#L122-L130) 将行哈希转为集合，重复次数随之丢失。
3. [比较器 L432–449](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/collections/models.py#L432-L449) 在变更计数器不同时检查行数及哈希集合；两者相同仍返回未变。
4. [更新识别 L487–505](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/collections/models.py#L487-L505) 检查新哈希是否出现在另一状态的任意行中，所以改变后的内容若已在别行出现，更新列表也可能为空。

公开 [test_model_collection.py L36–55](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/tests/package/test_model_collection.py#L36-L55) 将删除后重建同内容记录判为未变。因此，本版保留该良性对照，不将所有主键差异都重标为错误。

隔离复现从固定摘录中编译未改动的两个私有比较函数及名称验证函数，用简单内存对象提供表读取接口。命名适配仅接受已经规范化的 `Item`。为避免误依赖“表变更计数相同”的快捷返回，各例都设置不同计数器。

输入 `a/b/c` 是不透明内容标签，不是实际 xxhash 运行结果；哈希排除 ID 的结论来自公开源码。没有导入 AppWorld、运行 ORM、建立数据库或真实工具。用独立的 `Counter` 检查内容多重集，用 ID→内容映射检查身份差异；两者都是诊断参照，不替换原生成功定义。

| 软件控制 | 原辅助函数结果 | 独立内容参照 | 本轮解释 |
| --- | --- | --- | --- |
| 内容不变 | 无变化 | 相同 | 正常 |
| 普通内容更新 `b→c` | 检出模型及更新行 | 不同 | 正对照通过 |
| 普通新增／删除 | 检出模型及增删行 | 不同 | 正对照通过 |
| 新增一条相同内容记录 | 行数变化被检出 | 不同 | 并非所有重复内容都漏检 |
| 删除后重建同内容、ID 改变 | 无变化 | 相同 | 保留官方有意的内容等价 |
| 既有 ID 之间交换内容 | 无变化 | 相同 | 身份语义须看具体契约，不记为内容多重集漏检 |
| `[a,a,b]→[a,b,b]`，总行数相同 | 模型变化、增删改列表均为空 | 不同 | **隔离边界上的内容多重集漏检** |

共 8 个软件控制，其中普通新增和删除分别运行。它们不是随机抽样，不能报告为“1/8 的任务漏检率”。反例也不依赖哈希碰撞：原来和后来都只有 a、b 两种既有内容，只改变了各自的次数。

首轮诊断程序因内存适配对象缺少字典式索引而报错，在执行案例前终止；补齐该边界接口后 8 项回归测试通过。此错误属于本地诊断适配层，不归责给 AppWorld，原辅助函数没有修改。

全仓检查还发现 1.0.70 根更新日志的新标题与历史发布测试的顶部摘要约定冲突。本版保留继承基线的顶部摘要，将研究版本条目放到其后；版本内容不删除，冻结测试、清单与实验分数不修改。

## 已证明、未证明与本版决定

| 判断 | 当前证据 |
| --- | --- |
| ID 不参与记录哈希 | 公开固定源码已确认 |
| “哈希一定含 ID，因此可关闭疑点” | 已排除 |
| 相同行数与内容集合足以判断所有多重集相同 | 未改动辅助函数的隔离反例已否证 |
| 所有 AppWorld 实际模型都排除重复内容 | 不能由已核验声明得出 |
| 反例可由一个真实任务允许的 API 到达 | **未知** |
| 完整原生 `evaluation.py` 会错误通过 | **未知**，其他测试可能已经拒绝 |
| 真实 Agent 经常触发／系统排序改变 | **没有证据** |

本版准许准备一例原生任务核验，**不把辅助函数反例升级成 Benchmark 漏洞或论文创新**。没有提出／合入上游补丁，没有改动生产评分或训练模型。独立科学主张仍 HOLD；当前恢复算法路线仍 NO-GO。

下一步只做一个 train/dev 原生案例的核验准备：固定任务说明、相容起止库、完整评分程序／测试清单、公开工具及版本；使用合法工具构造正常／候选状态，保留原始完整评分。任务材料收集、具体 ID、包大小和运行范围须先形成记录，本版没有执行下载。若操作不可达、差异与契约无关、或原生完整测试已经拒绝候选，关闭该案例。只有该阶段取得真实误判，才考虑原轨迹和系统选择影响；不启动跨模型或付费实跑。

## 复现与验证

```powershell
python -m research.reliability_reset.hash_probe175 work/hash-probe175-replay.json
python -m unittest tests.test_reliability_reset_hash_probe175 -v
```

第一条命令只写新输出路径，已有文件会被拒绝覆盖。干净检出即可运行，无网络、AppWorld 安装或额外 Python 依赖。冻结结果见 [HASH_PROBE_175.json](evidence/1.0.75/HASH_PROBE_175.json)，源码与结论分级见 [SOURCE_CHECK_175.json](evidence/1.0.75/SOURCE_CHECK_175.json)，检查记录见 [VALIDATION_175.json](VALIDATION_175.json)。

本轮全仓运行 1,037 项：初次 1,033 项通过、3 项条件跳过、1 项根更新日志标题断言失败。修复日志顺序后，受影响发布模块、版本模块及新诊断的 25 项测试全部通过。没有再运行一轮完整套件，不将局部复验写成全仓重新全绿。历史冻结审计与冻结结果逐字节重放通过。

本轮新增模型调用、轨迹、真实任务、原生完整评分执行和研究环境运行均为 0；隔离软件执行与仓库测试另外计数。摘要仍只是本地一致性和固定公开对象的绑定，不是独立评审或真实性认证。

方法采用系统化根因排查与 scientific-critical-thinking 流程；流程来源沿用 Kassis 等（2026），*Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*，[arXiv:2609.00065](https://doi.org/10.48550/arXiv.2609.00065)，2026-10-26 已核对记录为 v2。流程辅助不构成独立审阅。
