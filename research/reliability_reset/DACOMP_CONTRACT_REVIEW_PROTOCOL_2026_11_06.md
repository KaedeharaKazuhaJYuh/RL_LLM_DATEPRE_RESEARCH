# DAComp-DA 计分契约盲审流程

状态：**审阅包已准备，尚未发送给审阅者；当前未获得人工裁决。** 本文件仅说明怎样取证，不是审阅结果。

## 目标

判断 rubric 本身能否唯一确定每个任务的总分上限，再判断 metadata `Total` 是否与 rubric 兼容。审阅者不能从单个文件矛盾直接推断作者意图；证据不足时必须标记“无法判定”。

## 审阅设计

- 固定源：DAComp commit `027ccaf20f0d3743d9291fd575d9bc785a5fe3db`。
- 共 24 个任务：14 个待审候选（原有11个静态分母候选，加上手工核对的路径—父级 ceiling 候选 `052/063/084`），以及从其余86题中用 `random.Random(20261107)` 抽出的10个对照；盲审表行序由 `random.Random(20261108)` 固定打乱。对照仅用于流程/漏检检查，不用于估计总体冲突率。旧包尚未发送或填写，故在外发前整体重建；没有覆盖任何审阅意见。
- 内部复现用固定对照 ID：`007, 025, 033, 037, 045, 056, 066, 085, 090, 099`。外发的 Stage 1 表没有 candidate/control 标签。
- 两位审阅者独立完成。每人使用自己的表格副本；互相不可见对方答案，也不告知哪些条目属于候选。外发时**仅发送**[中性审阅说明](DACOMP_REVIEWER_BRIEF_RUBRIC_ONLY_2026_11_06.md)、Stage 1 表和对应 rubric 来源；不要发送本内部流程文件、metadata、公开分数、审计报告、候选标记或其他审阅者意见。

## 阶段 1：仅审 rubric

填写 [`DACOMP_CONTRACT_REVIEW_STAGE1_2026_11_06.csv`](DACOMP_CONTRACT_REVIEW_STAGE1_2026_11_06.csv)。逐项记录：

1. rubric 标题总分；
2. 顶层 Requirement 上限与总和；
3. nested criterion/path 是否互斥、是否存在更细的冲突；
4. rubric 是否能唯一确定最大可计分值；若能，记录最有依据的值；否则记录“under-determined”；
5. 用原文行号说明判断和置信度。

填写完成后保存一个不可继续编辑的副本，并记录 SHA-256 与锁定时间。不得先看 metadata 或评分结果。

## 阶段 2：揭示 metadata

只有阶段 1 文件已锁定后，才提供 [`DACOMP_CONTRACT_REVIEW_STAGE2_2026_11_06.csv`](DACOMP_CONTRACT_REVIEW_STAGE2_2026_11_06.csv)。该表包含相同任务的 metadata `Total`，审阅者需引用锁定的 Stage 1 文件哈希，并逐项判断：

- metadata 是否与 rubric 的最佳支持上限一致；
- 若不一致，现有发布物更支持“计分契约冲突”“仅文档不一致”还是“无法判定”；
- 若无作者确认，是否仍需作者意图才能裁决。

揭示 metadata 后不得回改阶段 1 的原始判断；若审阅者补充说明，另加一列/另存补充文件并保留原始记录。

## 阶段 3：核对论文方法与固定实现

只有 Stage 1 和 Stage 2 各自已锁定后，才提供固定 DAComp 论文 §2.2、App. 10.3.2–10.3.3、对应版本 `rubric_scoring.py` / `get_score.py`，以及该任务已有的原始 Judge JSON（若公开）。本阶段不是回改前两阶段，而是分别记录：

1. 论文公式中的 `Σ w_k` 能否仅凭任务 rubric 唯一重建；每个 zero-score sub-requirement 的 selected path 是否被输出保存；
2. 固定 scorer 实际采用哪个分母、是否执行论文公开的 selected-path 归一化；
3. 根据完整公开材料，最稳妥分类是“实现与方法不一致”“仅任务文档不一致”或“证据不足”；不能将实现实际使用 metadata 直接视为其规范正确；
4. 哪些任务/输出可以支持上述判断，哪些仅有结构候选而没有输出证据。

每位审阅者从独立副本填写 Stage 3 表，并引用 Stage 1/2 锁定文件哈希。论文、代码与公开输出是同一来源层次内的可核验材料，不得冒充作者确认。两位审阅者的结论与异议原样保留。

## 使用限制与判定门槛

- 这次审阅只裁决“公开文本是否足以确定可计分上限”。它不能代替作者对 intended source of truth 的正式确认，也不能证明模型分数或排行榜受影响。
- 052/063/084 是在固定 rubric 中发现的路径子项和与明确 criterion/standard ceiling 不一致候选。审阅者需逐题判断该 ceiling 是否为硬上限、最佳路径求和是否优先，且不能把该静态矛盾直接登记为已发生的 Judge 超额评分。
- 若两位审阅者对多数候选均认为 metadata 是唯一规范来源，或均认为 rubric 不足以裁决，则该机制不能表述为已确认的错误评分；需获得作者澄清或把论文问题改写为“已发布评分契约不可识别”。
- 若两位审阅者分歧，原样保留异议，不投票抹平；第三位裁决者可补充但不能覆盖原始记录。
- 即使契约冲突得到确认，也必须取得合法的逐题、多模型 raw Judge 输出，才可检验分数敏感性与比较结论变化。聚合榜单不可反推逐题值。
- 科学状态在完成独立复审、来源权威判定与配对影响分析前维持 **HOLD**。

## 文件

- [Stage 1 rubric-only 表](DACOMP_CONTRACT_REVIEW_STAGE1_2026_11_06.csv)
- [外发用中性 Stage 1 说明](DACOMP_REVIEWER_BRIEF_RUBRIC_ONLY_2026_11_06.md)
- [Stage 2 metadata reveal 表](DACOMP_CONTRACT_REVIEW_STAGE2_2026_11_06.csv)
- [Stage 3 方法—实现对照表](DACOMP_CONTRACT_REVIEW_STAGE3_2026_11_07.csv)
- [Stage 3 审阅者说明](DACOMP_REVIEWER_BRIEF_STAGE3_2026_11_07.md)
- [固定资产审计报告](DACOMP_RUBRIC_CONTRACT_AUDIT_2026_11_06.md)
- [一页研究门槛](ONE_PAGE_RESEARCH_DESIGN_GATE.md)
