# AppWorld 历史轨迹：独立盲审与评分重放

审阅表日期：2026-11-02；补充记录：2026-11-03。此记录延续 [1.0.90 历史轨迹清点](EVALUATOR_GAP_190.md)，不是新版本发布。研究主张仍为 **HOLD**。

## 审阅结论

从 [AppWorld](https://aclanthology.org/2024.acl-long.850/) 官方历史开发集输出中，按原生评分结果分层选取四个不同场景：两个原生完整评分通过，两个未通过。两名人工审阅者分别先判断任务契约与记录中的实际行为，随后才与原生评分对照；另有三份代理意见作为辅助，不计入人工人数。协调者确认两位审阅者本人独立完成；审阅表自述事先未见原生评分。原表中的利益冲突字段未完整说明各自与项目的关系。

两个被审阅者判定存在任务要求冲突的案例，官方保存的完整评分都判为失败，其中一个与实际状态变化有关；两个原生评分通过的案例，在各自已检查范围内未发现违规。**这四例没有形成“原生完整评分通过但实际违规”的证据链。**审阅范围之外仍为未知。

该样本按结果分层选取，并非代表性抽样；不能用它估计漏检率、证明漏检率为零或推断跨任务稳定性。独立审阅原表和身份资料仅在私下保存，未在公开仓库发布，外部读者因此无法仅凭本仓库核验审阅过程。

复核还纠正了审阅表中两个不影响最终分类的事实描述差异；原表均保留，审阅范围外仍标为未知。

## 评分重放

历史输出记录的代码、数据及评分版本为 0.1.0。使用官方发布的 0.1.0 软件包，在独立的 Windows / Python 3.12 环境中，针对同一批开发集快照逐案以新进程运行完整评分器，没有执行 Agent 代码或调用模型。

| 条件 | 与历史报告的通过项、失败项均一致 |
| --- | ---: |
| 仅使用归档中保存的状态 | 1 / 4 |
| 在独立副本中补充由数据库变化推导的标记 | 4 / 4 |

直接重放时，其余三例均多出一项失败。对同一路径进行开关对照：增加或移除状态变化标记，仅改变了对应的那一项检查。由此可知，在本次重放环境和样本中，归档缺少的状态比较元数据会影响重评分。

补充的标记只是根据保存的数据库变化构造的诊断输入，**并非找回了历史运行时的原始计数**。4/4 只表示通过、失败的检查项与已保存报告一致，不表示所有内部状态或错误详情均一致，更不能称为原样复现。历史依赖未冻结，公开的同版本软件包也不能单凭版本号证明与当时执行的源码逐字节相同。

## 查新与已有方案对照（2026-11-05）

**判断：当前重放差异值得保留为工程复现案例，但不足以单独支撑论文创新。**AppWorld 上游 [issue #218](https://github.com/StonyBrookNLP/appworld/issues/218) 已于 2026-08-24 报告：两侧变化计数都为零时，变化检测可能提前跳过实际数据库差异；[PR #219](https://github.com/StonyBrookNLP/appworld/pull/219) 提出了零计数条件下继续比较的修复，截至本次查阅仍未合并。上游报告中的触发条件是未启动变化跟踪；本次离线案例是历史归档缺少该元数据。两者不是同一批实验，但共享零计数相等导致提前跳过的关键条件。

| 一手资料 | 与本项目的关系 |
| --- | --- |
| [Gao 和 Zhou，2026](https://arxiv.org/html/2605.10448v1) | 已对 AppWorld 的 100 个案例、三个模型共 300 条记录开展证据审计；作者报告样本内原生评分未发现冲突，同时保留了更强检查层面的盲点。该样本不证明整个基准无缺陷。 |
| [Chen，2026](https://arxiv.org/html/2610.16067v2) | 已研究评分器有效性、历史轨迹重评和配置影响，并报告 AppWorld 迁移尝试受限；其 AppWorld 负结果不能直接归因为本次观察到的计数问题。 |
| [Liu，2026-11-03](https://arxiv.org/html/2611.04399v1) | 已使用公开排行榜轨迹研究评分工具错误和重评版本差异，并报告分数及排序变化；它并未研究本次这组 AppWorld 归档。 |

作为更强的已有方案对照，本次预先写下本地比较方案，在四个既有案例上分别启动新进程，将 PR #219 的**零计数判断条件**适配到 0.1.0 的评分方法中，仅在进程内替换该条件；未修改安装文件、官方归档或原始评分记录，也未补造状态标记。结果四例的通过、失败检查项均与保存的历史报告一致，包含原本失败的无变化对照。该结果是**修改后评分器的对照**，不是完整 PR 测试或原始评分器在历史运行中的验证。四例按原分数选取，无法估计影响范围；本地方案也不是独立时间戳或外部预注册。

此次于 2026-11-05 检索 arXiv 的 `all:"agent benchmark" AND all:replay`，共检索到 28 条匹配记录，按相关性查看返回的前 20 条；另做定向检索并直接查阅上述论文与上游讨论。这是有范围的查新，不是穷尽性系统综述。

## 可复核材料

去标识化案例映射、原始来源文件散列、人工及代理判断标签、两种重放结果和重放脚本保存在 [加密证据包](evidence/appworld-review-2026-11-02.bundle)；包内不含审阅者姓名、原始审阅表、任务正文或模型响应。AppWorld 要求其受保护数据及衍生内容公开再分发时保持加密；这里使用上游公开的加密参数，**不是保密措施**。请遵循[上游许可证](https://github.com/StonyBrookNLP/appworld#lock_with_ink_pen-license)和[开发集使用限制](https://github.com/StonyBrookNLP/appworld#no_entry_sign-agent-development-restrictions)。

证据包 SHA-256：`23bb3a02356afbcd0aeb7337de6b6e26ee57a9098e6a2da35ddda5f5ceb4e892`。散列用于识别文件，不证明原始实验历史或人工盲审的真实性。

以下示例以 Windows、Python 3.12 为基准，先在独立环境中安装 `appworld==0.1.0`，再在仓库根目录操作。先取得与包内清单散列一致的官方 0.1.0 数据包和 0.1.3 历史输出包；脚本只读取所选开发集任务，不使用测试集任务。解密内容和生成状态应保存在不公开的本地目录。

```powershell
python -c "from appworld.common.constants import PASSWORD,SALT; from appworld.common.utils import unpack_bundle; unpack_bundle('research/reliability_reset/evidence/appworld-review-2026-11-02.bundle','work/appworld-review-extract',PASSWORD,SALT)"
python -m pip install -r work/appworld-review-extract/requirements-win-py312.txt
python -c "import appworld; from pathlib import Path; from appworld.common.constants import PASSWORD,SALT; from appworld.common.utils import unpack_bundle; p=Path(appworld.__file__).parent; unpack_bundle(str(p/'.source'/'apps.bundle'),str(p),PASSWORD,SALT)"
python work/appworld-review-extract/replay_010.py work/reliability-reset-1.0.90/official-data-0.1.0.bundle work/reliability-reset-1.0.90/official-experiment-outputs-0.1.3.bundle work/appworld-review-replay
```

最后一个目录必须不存在。包内的依赖清单记录的是本次重放环境，不是历史运行的依赖锁定文件。脚本核对输入散列并保存两种条件的检查项比较；它不执行原始轨迹中的 Agent 代码。

新增的 [PR #219 适配对照材料](evidence/appworld-pr219-control-2026-11-05.bundle) 包含本地比较方案、四例结果、可执行对照脚本及上游许可证；它依赖上述原证据包及相同官方归档。包 SHA-256：`5371aa2d5508430dc8dad6a49e5ed721cbd86e109d580011d2a3ef7d801dcac2`。先按上文准备原重放目录，再用同一环境解开本包，按其中 `METHOD.md` 运行。与原证据包相同，加密是上游再分发要求，不是保密措施。

```powershell
python -c "from appworld.common.constants import PASSWORD,SALT; from appworld.common.utils import unpack_bundle; unpack_bundle('research/reliability_reset/evidence/appworld-pr219-control-2026-11-05.bundle','work/appworld-pr219-extract',PASSWORD,SALT)"
Get-Content work/appworld-pr219-extract/METHOD.md
```

## 研究决定

目前不支持“原生完整评分系统性误判可靠性”的论文主张；将本次零计数重放机制作为独立论文创新的决定为 **NO-GO**，整体科学状态保持 **HOLD**。已有上游报告和近邻研究覆盖了关键机制或更广的重评问题。这个案例可以作为工程复现与文献比较的材料，不能据此宣称评分器在原始运行中漏检、排行榜错误或存在跨任务、跨模型影响。若今后获得不被现有工作解释、可独立核验且会改变评测结论的证据，再重新评审论文主张。

四例中，以保存的历史完整评分为基准，直接重放的最终通过状态变化如下：

| 历史保存评分 | 重放通过 | 重放失败 |
| --- | ---: | ---: |
| 通过 | 0 | 2 |
| 失败 | 0 | 2 |

三例的检查项发生变化，其中两例的完整评分由历史通过变为重放失败。适配已有零计数条件后，四例的通过／失败检查项与保存报告一致。这些是**离线重评分的变化**，与“历史原生评分通过但实际违规”是不同问题；四例按保存结果选取，不可用上述比例估计实际发生率或模型性能。

不继续随机寻找评分缺陷。只有出现具体候选，并先通过[一页研究设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)——包括原任务契约、合法可达性、完整原生评分为何可能漏检、否证条件与最小成本——才开展新的针对性核验。

审查方法参考：Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://arxiv.org/abs/2609.00065)。
