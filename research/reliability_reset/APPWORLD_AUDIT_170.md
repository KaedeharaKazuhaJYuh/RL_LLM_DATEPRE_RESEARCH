# 1.0.70：AppWorld 原生契约与评分链核验

日期：2026-10-26。结论：**尚未取得 AppWorld 原生完整评分发生可靠性误判的实例证据。** 已核验公开契约、通用评分入口及状态比较辅助函数；没有取得任务专属评分程序、任务数据库或官方运行原件，不能把这次审查称为完整任务评分器复现。

本轮关闭若干已被原协议解释的候选，保留一个关于记录身份比较的、可以继续否决的源码疑点。这个疑点不是已确认漏洞，更不是论文贡献。科学状态仍为 HOLD；新增模型调用、模型轨迹、任务数据下载和研究环境执行均为 0。

## 固定问题、范围与原件

唯一问题是：**遵守 AppWorld 自己的任务契约、使用其原生完整判定，是否仍会将有实质违规的真实执行记为成功，并影响系统选择？** 对照必须是原完整评分，而不是 `task_completed()`、部分测试通过率或我们另加的历史／证据规则。

固定官方仓库 [StonyBrookNLP/appworld](https://github.com/StonyBrookNLP/appworld) 的提交 [`42b5bcf3cd334fee33f0c37c02070a9f5807add5`](https://github.com/StonyBrookNLP/appworld/tree/42b5bcf3cd334fee33f0c37c02070a9f5807add5)，提交时间为 2026-09-03T20:58:16Z，tree 为 `dfce7142b8669fc11467c89a3f571b1f47d52dcf`。本轮从固定提交读取 19 个公开明文源码／说明文件，共 522,076 字节，逐个校验 SHA-256，并将 Git blob SHA-1 与官方提交树比对。

文件、固定 URL、字节数及两种摘要见 [SOURCE_MANIFEST_170.json](evidence/1.0.70/SOURCE_MANIFEST_170.json)。逐项事实与结论见 [APPWORLD_AUDIT_170.json](evidence/1.0.70/APPWORLD_AUDIT_170.json)。缓存位于忽略目录 `work/reliability-reset-1.0.70/appworld/source/`。没有安装 AppWorld、导入或执行其代码，也没有下载／解包数据或受保护源码 bundle。

摘要能帮助检测本地副本和固定公开提交是否对应，不是独立评审、第三方时间戳或历史从未修改的证明。19 个文件是审查覆盖范围，不是 19 个任务或独立样本；本轮真实任务审查数为 0，不能估计误判率或排序变化。

## 原生评分实际检查什么

| 层级 | 源码观察 | 对本研究的约束 |
| --- | --- | --- |
| 任务契约 | [生成器说明 L30–40](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/guides/developing_new_task_generators.md#L30-L40) 将评价定义为起止数据库比较，检查预期改动和非预期改动。 | 不能将它描述成只检查一个目标值。 |
| 原生任务判定 | [evaluator.py L452–508](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/evaluator.py#L452-L508) 载入起始／终止模型集合，再调用任务自己的 `evaluation.py`；[L153–181](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/evaluator.py#L153-L181) 要求通过数等于预期测试数。 | 通过率、任务完成标志和完整任务成功是不同量。不能通过删掉原测试制造假成功。 |
| 副作用与业务键 | [生成器说明 L767–853](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/guides/developing_new_task_generators.md#L767-L853) 展示改动模型名、增删改数量、目标记录 ID 与字段集合检查。 | 有额外持久改动的例子可能已被原评分发现；但教程不证明所有实际任务覆盖完善。 |
| 停止信号 | [environment.py L1357–1370](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/environment.py#L1357-L1370) 的完成查询读取 supervisor 状态；[官方测试 L743–753](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/tests/package/test_appworld.py#L743-L753) 明确允许完成标志为真而评分仍失败。 | 单凭调用 `complete_task()` 不能宣称评分误判。这里只阅读了测试，没有运行该测试或接触其任务数据。 |
| 场景聚合 | [evaluator.py L322–365](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/evaluator.py#L322-L365) 的 TGC 对任务成功求平均，SGC 对同生成器任务先取最小值，再平均；[L574–576](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/evaluator.py#L574-L576) 提醒单任务 SGC 有误导性。 | 不把换分母、只看单任务或换指标名称当作新可靠性机制。 |
| 可审查原件 | [environment.py L1084–1161](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/environment.py#L1084-L1161) 保存状态、环境输入输出和 API 请求日志。 | 公开代码说明有记录能力，不等于某个提交包确实包含全部原件。 |
| 日志含义 | [requester.py L77–119](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/requester.py#L77-L119) 的请求追踪字段是 method、url、data，且排除 admin 请求。 | API 请求日志本身不证明响应内容、实际提交或 Agent 知晓状态；应与环境输出、起止状态分别绑定。 |

## 候选处置

| 编号 | 候选解释 | 本轮决定与适用范围 |
| --- | --- | --- |
| A1 | 目标完成但有额外持久改动，原评分必然看不见 | **关闭这项笼统主张。** 原生架构与教程明确支持额外改动检查；实际某任务是否遗漏仍须审查其完整测试，当前未知。 |
| A2 | 完成接口被调用，就会自动获得成功分 | **关闭。** 官方代码和测试将完成标志与实际评分分开。 |
| A3 | 曾经改错、最后撤销，所以原评分必然有漏洞 | **排除为当前证据。** 起止状态等价并不自动违反原生状态契约；只有找到任务本来禁止的中间事件和真实执行证据，才能重开。不能临时追加过程要求。 |
| A4 | 单任务 TGC 与场景 SGC 不同，说明可靠性误判 | **关闭这项解释。** 两者本来就是不同、明确公开的聚合对象；没有系统排序实例，不作排序结论。 |
| A5 | 未确认提交后安全升级，未完成就一定是评分错误 | **排除。** 安全退出可以合理，但不等于目标完成。当前没有取得要求特定不确定性处理的原生任务及执行，不能重标。 |
| A6 | 哈希集合比较可能掩盖记录身份或重复内容变化 | **未解决，仅保留源码疑点。** 需要确认哈希定义、真实模型约束、合法 API 可达性和完整任务测试后，才判断是否构成误判。 |

关闭的是表中的具体解释，不是证明 AppWorld 全部任务无缺陷。A6 也不能因其他解释被排除就自动成为新创新。

## 唯一保留的源码疑点：集合相同是否意味着任务要求的状态相同

[ModelCollection.record_hashes L122–130](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/collections/models.py#L122-L130) 将记录哈希转为集合。[ModelCollectionPair._changed_model_names L432–449](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/collections/models.py#L432-L449) 在模型哈希快速排除后，比较行数和记录哈希集合。[同文件 L487–505](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/collections/models.py#L487-L505) 的更新记录识别也使用哈希在另一状态集合中是否出现，而不是直接按同一个 ID 比较。

**条件推理，不是真实反例：** 如果哈希不含任务相关身份，`{id1:a, id2:b}` 与 `{id1:b, id2:a}` 可以有相同行数和内容哈希集合，但 ID 对应关系不同。如果允许相同内容的多行，`[a,a,b]` 与 `[a,b,b]` 也具有相同长度及集合，重复次数不同。这只是说明该比较所需的充分条件值得核实；本轮没有运行这些人工状态，也没有将其计作任务、漏洞或假成功。

尚缺四项关键证据：

1. 受保护实现里记录哈希实际包含哪些字段，是否已包含 ID／其他足以排除例子的唯一字段。
2. 一个真实 train/dev 模型的约束及公开任务要求，确认上述变动是否合法可达且有语义影响。
3. 原生完整 `evaluation.py` 是否还有按 ID、字段、答案或数量的检查，已经拒绝该变动。
4. 固定原运行、数据库与分数的原件，确认不是替换输入、删测试或修改协议才出现差异。

另外，比较函数默认忽略 `supervisor.Task`、`admin.PaymentCard`、`amazon.BrowsedProduct`（[L373–384](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/collections/models.py#L373-L384)）。这是显式评测边界；不能单凭被忽略就断言发生违规或有人利用过它。

## 原轨迹、完整评分与准入决定

[GroundTruth.evaluation_module L83–90](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/ground_truth.py#L83-L90) 从任务目录动态载入评分代码；[L346–353](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/src/appworld/ground_truth.py#L346-L353) 要求该文件存在。因此，只审通用入口不能证明某任务漏检，也不能证明所有任务都有相同检查。

官方 [README L1452–1464](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/README.md#L1452-L1464) 给出 baseline 输出入口，包含 `simplified_react_code_agent_gpt-4o-2024-05-13_dev`。固定源码的数据版本为 `0.2.0`，实验输出版本为 `0.1.3`；这两个版本号不能证明具体输出与当前代码兼容。本轮**仅登记入口，没有下载输出或任务**，所以官方运行原件完整性、字节摘要和分数重放均为 not_checked。

若后续取得原件，最小绑定单元须同时含原始任务说明、相容起始库、终止库、原生完整评分程序及测试清单、原分数、版本、环境输入输出与请求日志；缺少材料时保留 unknown。审查限定 train/dev，遵守 [官方拆分使用要求 L941–945](https://github.com/StonyBrookNLP/appworld/blob/42b5bcf3cd334fee33f0c37c02070a9f5807add5/README.md#L941-L945)，不把 test_normal/test_challenge 的任务级错误分析用于开发。

本版决定：**没有被接纳的真实误判；不估计误判率，不声称模型提升，不启动跨模型或付费评测。** 当前机制路线仍 NO-GO，独立科学主张 HOLD。A6 可以接受一次有界源码核验，但不是通过科学准入。

下一步只回答 A6 的前置问题：取得可合法审阅的固定版本哈希实现，核实身份／重复内容是否真的被丢失；若字段与唯一性已排除疑点，立即关闭。如果源码层疑点仍成立，再提出一例 train/dev 原生契约与完整评分的核验计划；不能先造新环境，也不能在未取得原件时宣称真实假成功。新的任务材料收集和执行须另列范围，不从本版只读授权自动延伸。

## 复核方式与限制

源码摘要及行号可用下列命令在已下载缓存上复核；它只读取文本，不导入第三方代码，不访问网络：

```powershell
@'
import hashlib, json
from pathlib import Path
m = json.loads(Path('research/reliability_reset/evidence/1.0.70/SOURCE_MANIFEST_170.json').read_text(encoding='utf-8'))
base = Path('work/reliability-reset-1.0.70/appworld/source')
for r in m['files']:
    b = (base / r['path']).read_bytes()
    assert len(b) == r['bytes']
    assert hashlib.sha256(b).hexdigest() == r['sha256']
    assert hashlib.sha1(b'blob ' + str(len(b)).encode() + b'\0' + b).hexdigest() == r['git_blob_sha1']
print(len(m['files']), 'fixed-commit source files verified')
'@ | python -X utf8 -
```

新检出没有缓存时，可以逐个从 manifest 的固定 `url` 获取这 19 个明文文件后运行上述检查；这不需要安装 AppWorld 或下载任务。机器记录中的行号、AST 位置及摘要是源码审查证据，不是独立人工复审或运行证明。没有新增生产评分逻辑／修复，故没有为这些可逆文档变化添加镜像测试；发布检查与历史冻结审计见 [VALIDATION_170.json](VALIDATION_170.json)。

方法来源：本轮使用 Scientific Agent Skills 的 scientific-critical-thinking 1.5 流程区分源码事实、条件推理及未解决证据。Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). *Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents*. [arXiv:2609.00065](https://doi.org/10.48550/arXiv.2609.00065)，2026-10-26 核对当前记录为 v2；该流程不是独立验证人，也不是本版发现的实证来源。
