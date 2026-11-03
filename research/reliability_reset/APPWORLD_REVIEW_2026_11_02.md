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

## 研究决定

目前不支持“原生完整评分系统性误判可靠性”的论文主张。重放元数据问题是一个可复核的测量与复现限制，不能据此宣称评分器在原始运行中漏检，也尚未证明跨任务、跨模型影响或新颖性。

不继续随机寻找评分缺陷。只有出现具体候选，并先通过[一页研究设计门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)——包括原任务契约、合法可达性、完整原生评分为何可能漏检、否证条件与最小成本——才开展新的针对性核验。

审查方法参考：Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026), [Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents](https://arxiv.org/abs/2609.00065)。
