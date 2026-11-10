# DAComp-DA 第三阶段独立来源审阅说明

## 目的

本阶段在 Stage 1（rubric-only）和 Stage 2（metadata）已独立锁定之后，判断公开论文方法、固定 scorer 和任务输出之间是否能形成唯一、可重建的 rubric 分数分母契约。本表不是作者意图确认，也不要求审阅者猜测缺失信息。

## 请审阅的固定来源

- DAComp revision：`027ccaf20f0d3743d9291fd575d9bc785a5fe3db`
- 论文 v1 §2.2、App. 10.3.2–10.3.3：[固定论文版本](https://arxiv.org/html/2512.04324v1)
- 官方 scorer：[`rubric_scoring.py`](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/core/rubric_scoring.py)
- 总分导出：[`get_score.py`](https://github.com/ByteDance-Seed/DAComp/blob/027ccaf20f0d3743d9291fd575d9bc785a5fe3db/dacomp-da/evaluation_suite/get_score.py)
- 每个任务的 rubric 与 metadata：以 Stage 1/2 表中相同的固定任务 ID 与 SHA 锁定副本为准。
- 若任务有已公开原始 Judge JSON/评分行，也一并核对；缺失时填 `not available`，不推测。

## 独立填写

两位审阅者各自从一份 Stage 3 CSV 副本填写，不查看对方意见。填写前写入自己 Stage 1/2 锁定文件的 SHA-256。请逐任务回答：

1. 按论文公式，所选路径及其 leaf-item 权重和能否从公开任务与输出唯一重建？
2. 零分标准是否保存了被选路径？若无，是否会影响分母重建？
3. 固定 scorer 的分母来源是什么？代码是否执行论文所述路径归一化？
4. 依据可核验来源，最妥当结论是 `method_implementation_mismatch`、`task_document_conflict`、`consistent`、`insufficient_evidence` 还是 `other`？
5. 必须引用具体代码/论文/任务原文和行号，并指出还需要什么证据才能裁决。

## 判定边界

- `metadata.Total` 是代码实际使用的分母，不自动意味着它在规范上优先。
- 论文与代码表达不同，不自动证明分数算错；缺少作者确认或完整逐题结果时，保留 `insufficient_evidence` 是有效结论。
- 条件分数重算仅表示对分母解释的敏感度，不等于正确修正分或模型效果。
- 不评判整体研究新颖性，不估计排行榜影响，不运行模型或 API。
- 不改写、不覆盖 Stage 1/2 的已锁定原始文件；发现修正或异议时另附说明。

## 交付

使用 [`DACOMP_CONTRACT_REVIEW_STAGE3_2026_11_07.csv`](DACOMP_CONTRACT_REVIEW_STAGE3_2026_11_07.csv)；每位审阅者提交自己的副本。保留原文件、完成时间和各阶段 SHA-256。争议不得投票抹平，应并列呈现。
