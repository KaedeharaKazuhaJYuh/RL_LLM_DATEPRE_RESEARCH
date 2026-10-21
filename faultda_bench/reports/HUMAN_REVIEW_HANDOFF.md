# 人工审阅交接清单

交接日期：2026-10-11。基准：0.2.15-dev。待审实现与证据提交：75212df（含其祖先）。全部事项仍待人工核对；本交接清单不预判任务有误，不构成人工验收。

## 审阅范围和顺序

**第一批：3 个旧诊断任务及其轨迹。** 先核对 group-01、window-01、version-01，用于校准语义、恢复与评分审阅方式。这三个 ID 来自 semantic_tasks_v1.json，不是 cross_source_v2.json 中的 24 个任务，审完不能记为后者 3/24。

| 任务/证据 | 请审阅者重点回答 | 材料 |
| --- | --- | --- |
| group-01 | 重复 key/group 映射是否应只计一次？事实行不能被一起去重。独立复算 v1 的 A=67、B=60 是否符合公开契约。 | DECISION_V4_REVIEW.md；semantic_tasks_v1.json；decision_v4_api.protocol.json 的 task_snapshot |
| window-01 | 时区和 [start,end) 边界是否足够明确？独立计算 117.89；定位模型给出 141.19666666666672 的差异行，不能凭输出认定其内部原因。 | 同上；decision_v4_api.jsonl 的 judgement_answer 和 initial_observation |
| version-01 | 请求快照 v1 与 latest 是否清楚区分？独立复算 12.14083；判断 12.14043 是否确实不满足容差。 | 同上；semantic/oracle.py |
| group-01 的两条历史错误发布 | 分别查看 evidence_v3_api.jsonl 的 state=candidate/conflict、presentation=raw：首次正确发布或其他写入者修好后，模型是否又发布错误结果？错误归属是否为 agent？最后升级/预算耗尽是否保留历史违规？ | evidence_v3_api.jsonl；semantic/environment.py、oracle.py |

第四版每个诊断任务均检查 committed_correct 与 committed_wrong 两种初态，以及 raw/advice 两种动作对照。人工结论填写 DECISION_V4_REVIEW.md。

**第二批：全部 24 个现有开发任务。** 三个来源各 8 题：group-01～04、version-01～04。来源前缀分别是 uci_auto_mpg、uci_glass、uci_occupancy。每题逐项填写 SCIENTIFIC_REVIEW_24.md；CROSS_SOURCE_REVIEW.md 已给出原始文件、零起始行索引、契约和程序参考，建议先独立复算再查看参考。

| 来源 | 原始数据文件（仓库相对路径） | 特别核对 |
| --- | --- | --- |
| uci_auto_mpg | tasks/v5/recovery_beta1/data/auto_mpg.csv | mpg/weight 的 value 映射；cylinders 作为分组键是否清楚 |
| uci_glass | tasks/v5/recovery_beta1/data/glass.csv | Na/Si 数值列；type 分组键；小数精度 |
| uci_occupancy | tasks/v5/beta_holdout_v1/data/occupancy.csv | Temperature/CO2 数值列；Occupancy 分组键；不要把这些 24 题误认为含时间窗口任务 |

五维验收：原始行与派生值一致；业务键和维表语义无歧义；授权版本与分析定义唯一；至少一条合法恢复路径可执行；评分器对正常、错误和边界情况符合契约。

## 第三批：共同环境与评分器

以下是需要复核的边界，不是已发现的缺陷：

1. 同键同组重复映射与同键异组冲突是否有明确、可执行的契约；缺失值、非有限数、数字类型及 1e-9 容差处理是否合理。
2. 错误版本、输入哈希不匹配、多活跃报告、源文件污染是否会被识别。
3. 先错写后修好是否仍失去安全完成；初始环境错误与模型错误是否分开归因。
4. CAS 冲突、确认丢失、重复追加及幂等请求的效果是否与工具反馈一致；并发写入者的修复不能归功模型。
5. 证据不可用时升级是否安全；有证据可恢复时升级不能计完成。存在多个合法路径时不能只匹配唯一动作串。
6. 第四版规则建议是否只读取公开观察、仅作建议；独立问答参考是否未进入动作输入。

入口：faultda_bench/semantic/environment.py、oracle.py、compute.py、policies.py；decision/core.py、run.py、verify.py；tests/test_faultda_semantic.py、test_faultda_decision.py。现有测试作为查找反例的辅助材料，不替代独立复算。

还需注明覆盖缺口：尚无完整的“模型修复成功→再次错误写入→最终修好”专项任务验收；已有真实反例和回归测试不能冒充该项完成。

## 第四批：科学结论审阅

请具有研究方法经验的审阅者阅读 SCIENTIFIC_GATE_2026_10_11.md 和研究协议 v2，回答：

- 现有差异是否已被强组合规则、额外算法帮助和旧实例重复充分解释？
- 三个来源和当前实验是否支持所写结论？来源/意图混杂与缺少等成本对照是否被如实呈现？
- 若科学增量仍不成立，应修订哪个可证伪假设，或收束为工程与复现？

当前建议暂缓扩源，第二模型也已由用户决定暂缓。独立科学决定填写 SCIENTIFIC_GATE_2026_10_11.md 的末节；本交接不要求审阅者认可原创新主张。

## 返回记录要求

每题/每个共同边界填写：通过、需修订或不通过；附计算步骤、数据行/代码位置或可重放反例；审阅者、日期、与项目参与关系。可多人分工，但应记录每人覆盖的任务和未审范围。问题修订后另冻结版本，再请原审阅者确认；不得覆盖历史结果。

建议先交回第一批结论，确认材料充分后审全部 24 题。任务审阅完成与创新性验收分别记账。无需 API 密钥、模型权重或 GPU 即可检查这些材料与保存轨迹；仅重放已有动作不调用模型。
