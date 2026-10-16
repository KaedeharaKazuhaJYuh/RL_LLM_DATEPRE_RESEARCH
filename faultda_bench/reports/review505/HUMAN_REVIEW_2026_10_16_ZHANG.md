# 0.5.0-dev 独立复审记录

日期：2026-10-16。审阅对象：`FaultDA_0.5.0-dev_Review_2026-10-16_e29d39c.zip`，基准 `0.5.0-dev`，manifest 声明 Git 提交 `e29d39c1dc9ea26de3c3c3428b4eee0a318d98ec`（分支 `faultda-bench`）。

**审阅者**：张雨田。

**交接包完整性**：manifest 声明 513 个文件，逐一计算 SHA-256 与字节数，**513/513 全部匹配**，无缺失、无多余（仅 manifest 自身不在其声明内，属常规自排除）。`acceptance_v37` 目录下 502 份冻结文件经项目清单核验通过。

---

## 一、总计

| 项                          | 数量                                        |
| -------------------------- | ----------------------------------------- |
| 复审组 1：12 对既有响应的解释注释（24 行）  | **通过 12 / 需修订 0 / 排除 0**                  |
| 复审组 2：24 个环境组三读取视图迁移（72 行） | **通过 24 / 需修订 0 / 排除 0**                  |
| 复审组 3：内部科研结论清单（1 份）        | **通过 1 / 需修订 0 / 排除 0**                   |
| 合计                         | **37 组全部通过**                              |
| 非阻塞修订建议                    | 2 项（见第四节，均为打包/文档层面，不动科学内容）                |
| 机械复跑                       | 聚焦 23 项、CI 列表 269 项、包内全量 287 项测试**全部 OK** |

37 组逐组填入项目模板 `validity_v39_review_template.json` 并经项目 CLI 校验：`scope_validated_identity_unverified`，无 issue，37/37 登记，剩余 0。CLI 如实返回 `reviewer_identity_authenticated: false`、`human_review_registered: false`、`reviewed_commit_resolved: false`——机器登记不等于身份认证或科学接受。

---

## 二、第一批：12 对响应的解释注释（24 行）

### 复算方法

从最原始的 `coherent_v38_deepseek.requests.jsonl`（24 条真实请求正文与回复）和 `coherent_v38_offline.json`（72 个程序状态）出发，不经过项目评分代码，逐条重推：

1. **备选参照（last-publish）**：取 history 中最后一个 `publish` 事件（须 `ok=true` 且 revision 为整数），构成 `{request_id, committed=true, revision, event_id=history:N, responsibility=按边界}`。
2. **旧参照（lookup 目标）**：`history[-1]` 为 `receipt_lookup`，以其 `params.request_id` 为目标；该请求的持久真值（committed/revision）**以持久回执读数为准**，事件位置取对应 publish 的 history 下标，responsibility 按 `current_model_start_history_index` 边界推定。
3. **双参照判分**：把模型自报五字段分别与旧参照、备选参照做严格类型+等值比对。
4. **角色锚定**：从模型自报 `receipt_event_id` 反查——必须是 publish、request_id 须匹配，否则记为不可绑定（stage 误报或越界），不推断模型内部思维。

### 三方比对结果

审阅者独立复算值 vs `validity_v39_interpretation.json` 记录值，**24/24 行逐字段一致**：observation 摘要、reported_facts、旧参照判分、备选参照判分、anchored_role、final_publish_reference 全部吻合。每行旧参照另与 `coherent_v38_offline.json` 的 `expected_receipt_facts`（项目钉死的真值）比对，**24/24 一致**。24 条请求正文的摘要与冻结计划 `coherent_v38_plan.json` 的 cell 绑定**全部匹配**（发送前钉计划、发送后钉字节，无重试、无挑选）。

### 汇总数字（独立复算复现，与文件一致）

| 臂               | 回答数 | 旧参照全对    | 备选(last-publish)全对 | 角色一致 | 角色不一致 | 不可绑定 |
| --------------- | --- | -------- | ------------------ | ---- | ----- | ---- |
| contextual（歧义句） | 12  | **0/12** | **12/12**          | 12   | 0     | 0    |
| explicit（显式句）   | 12  | **6/12** | **0/12**（已标不适用）    | 6    | 4     | 2    |

`old_primary_scores_replaced=false`、`best_of_reference_scoring_used=false`、`new_provider_requests=0`，与文件声明一致。contextual 行全部标记 `plausible_ambiguous_reference_not_independently_adjudicated`，explicit 行全部标记 `explicit_lookup_target_alternative_not_eligible`，**没有把较高分参照偷换为主分数**。

### 典型案例

- **同Snapshot 对照对**（`utc_end|base|historical|bad_never_committed|first`）：歧义句下模型答最后一次 publish（request-31, committed, rev 3, history:8, historical_agent_action）——仅在备选参照下全对；显式句下模型答 request-17（uncommitted, null, history:4, historical）——旧参照全对。同一观察、仅末句不同，0/12 与 12/12 的摆动**只隔离出指代措辞这一个变量**，属接口有效性观察，不是模型能力差异。
- **角色不一致 4 例**：全部落在 `scripted_current` 环境（如 `utc_end|trim_start|scripted_current|bad_never_committed|first`）：模型请求 id、committed、revision、event_id 四字段全对，但把锚定 publish 的 responsibility 标成 `historical_agent_action`，而边界（`current_model_start_history_index`）要求 `current_model_action`。判分依账本边界字段，不靠输出反推。
- **不可绑定 2 例**：模型自报 `event_id` 指向 stage 而非 publish（如 `utc_end|base|scripted_current|bad_never_committed|second` 报 `history:5`，实为 stage 动作）——正确地按不可评分处理，未从分母中偷删。
- **bad_committed 设计确认**：持久回执显示 committed=true 而 publish 确认超时丢失的场景（如 `utc_end|trim_start|scripted_current|bad_committed|first`：request-23, committed=true, revision=2），模型答 committed=true 按持久读数是**正确**的。复核中确认：旧参照以持久回执为权威，不把丢失的 ack 当未提交——这正是 receipt_lookup 工具的存在意义。

### 判断

「final receipt」的指代歧义**真实存在**：旧读法（最后一次 receipt_lookup 的回执）与备选读法（最后一次 publish 的回执）都说得通。项目的处理——两个参照都保留、不择优、contextual 标「合理但未独立裁决」、explicit 标「不适用换参照」——**克制且正确**。12 对是同 Snapshot 提示对，属同一任务簇（3 窗口 × 2 角色 × 2 隐藏历史），**不是 12 个独立任务**，不能以 episode 数替代独立支持；这一点项目在 plan scope 中已自述，本轮予以确认。

---

## 三、第二批：24 个迁移组（72 条只读视图）

### 复算方法

不调用项目 adapter，自行实现令牌反转（`pre_handoff_actor→historical_agent_action`、`active_actor→current_model_action`、`actor_handoff_history_index→current_model_start_history_index`、`responsibility-v2-neutral-actor→responsibility-v1.1-receipt-witness`），对 `validity_v39_migration.json` 的 72 行逐行：

1. 剥掉 `generation_contract`/`generation_context` 后反向重命名，与 `coherent_v38_offline.json` 对应行的 `public_observation` **全等比对**（精确往返）。
2. 工具 `history` 逐字节未变；`legacy_observation_sha256` 与离线源摘要双向绑定。
3. `neutral_public_evidence` 反向重命名后与离线 `public_evidence` 全等——即公开证据仅是词汇翻译，其中 `evidence_supported_stop`（stop 许可）与 `confirmed_violation_event_ids`（违规事件集）逐行不变。
4. `expected_receipt_actor_scope` 为离线 `expected_receipt_facts.receipt_responsibility` 的正确重命名。
5. `legacy_private_truth_sha256` 仅作哈希钉住，`private_effects_reassigned=false`  everywhere——私有效果没有被重新归责。
6. 生成来源：72 行全部为 `scripted_fixture`，且 `source_sha256` 绑定 `coherent_v38_offline.json`（该文件又被 `acceptance_v36.json` 目录钉死）；`provider_authenticity_verified=false`；`actual_model_tool_action_origins=0`。

### 结果

**72/72 精确往返、history 不变、许可不变、违规集不变、来源仅 scripted**，与 migration 文件的 checks 和 summary 完全一致。`active_actor` 只表示交接边界下的责任范围，**没有**被提升为「模型生成了这些动作」；自行申报或旧字段名 `current_model_action` 都不会获得模型来源标记——adapter 对来源提升的封堵在 72 行上实测有效。模型的事实问答（24 次 API 响应）**没有**被当作工具历史的生成证据。

---

## 四、需修订项（2 项，均非题目内容，非阻塞）

### 修订 1：交接包的复核入口与文档不一致

在交接包内按 README「快速复核」执行：

- `python -m pip install -e .`——包内**没有** pyproject.toml / setup.py，命令无法按文档执行（测试可从仓库根直接跑，实际影响有限）。
- `python -m faultda_bench.validity500.audit`——**失败**：`ModuleNotFoundError: No module named 'research'`。断链为 `acceptance.audit → clarity.verify → clarity.compare → semantic.deepseek → agent.deepseek_config → research.io`，继承代码基线（`research/` 等）未随交接包分发。复审指南第 1 步要求运行该入口，审阅者拿到的包却跑不了。

本轮改用组件级核验替代并全部通过：`validity500.suite`（24 条注释、72 条迁移、旧分未换、HOLD）、`validity500.review`（37 组范围）、`check_inventory`（502 份冻结文件）、GO/NO-GO 三项哈希绑定（source_live / claims / internal_review 均匹配）。

建议：README 或 manifest 注明「统一 audit 需完整仓库」，或随包附最小 `research` 存根/打包元数据。

### 修订 2：测试总数口径未随包收窄

`VALIDITY_0500_RELEASE.md` 称「全量 496 项测试通过（116.904 秒）」。交接包内实测：测试函数共 287 个，全量 discover **287/287 通过**（本机 228.927 秒；CI 列表 269 项亦全过）。496 项应为完整仓库口径（含未随包分发的继承轨测试）。建议报告注明该数字的仓库范围，避免审阅者拿包复现时误判为失败。

---

## 五、覆盖缺口（如实标注）

1. **供应商真实性未认证**：包内无凭据，本轮未调 API；本地重放只能核对一致性。`provider_authenticity_verified` 全程为 false，项目亦未声称已认证。
2. **V5 继承轨未涉及**：`research/`、`experiments/`、`native/`、`orchestrator/` 未随包分发，其测试与结论未复核。
3. **历史版本报告未逐份重审**：本轮只核 0.5.0 相关的冻结链（0.3.95 的 24 条真实响应、72 条程序状态及其引用），更早报告仅沿用既有哈希核验。
4. **0.3.80 四条真实轨迹未重跑**：属 0.3.85 已离线审计的历史数据；本轮仅目测其 summary 与 0.3.80 发布报告一致（4 轨迹、8 请求、3/4 正确终止、prompt 25594 / completion 275 token），未独立重放。
5. **独立裁决未做**：contextual 的 last-publish 解释本轮只确认「合理且未被替换主分数」，**没有**替项目做独立裁决——按项目自定的 pending 状态处理。

---

## 六、科学结论审阅

`validity_v39_claims.json` 五项判断与文件逐一核对，状态值与证据描述一致：

- 回执指代 → `descriptive_interface_validity_only`：0/12 与 12/12 的差是措辞变量，不得解释为模型或 RL 改善。**认可**。
- 目标/角色分离 → `observed_under_scripted_actor_semantics_not_mechanism_proof`：4 条角色不一致、2 条 stage 误报是 represented-script 语义下的外显记录。**认可**。
- 自洽基准 → `engineering_qualification_not_scientific_novelty`：24 状态 + 72 对照是工程资格。**认可**。
- 模型生成来源 → `not_established_for_tool_history`：API 事实问答不等于工具动作作者。**认可**。
- RL/新机制 → `not_established`。**认可**。

`live_decision=NO_GO_LIVE`、`approved_transport_requests=0`、`scientific_gate=HOLD`、`independent_review=pending` 与全部声明一致。**本轮独立复算未发现任何分数操纵、参照偷换或来源提升**；科学门维持 HOLD 是恰当的。0.5.05-dev 的下一步（先整理复审与查新、构造可证伪对照再决定最小实跑）与上述边界自洽。

---

## 七、返回记录

| 项    | 内容                                                                                                                                                             |
| ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 结论   | 37 组**全部通过**（12 响应对注释 + 24 迁移组 + 1 结论清单）；2 项非阻塞修订建议（打包/文档）                                                                                                     |
| 计算证据 | contextual 旧参照 0/12、备选 12/12；explicit 6/12、备选 0/12（不适用）；角色 12 一致 / 4 不一致 / 2 不可绑定；72/72 精确往返、许可与违规集不变、来源全 scripted                                             |
| 机械复跑 | 聚焦 23 项 OK；CI 列表 269 项 OK（220.851s）；包内全量 287 项 OK（228.927s）；audit 入口因缺 `research` 模块在包内失败（修订 1）                                                                |
| 提交物  | `validity_v39_review_submission_zhangyutian.json`（37 组全填）+ CLI 校验结果 `validity_v39_review_result_zhangyutian.json`（scope_validated_identity_unverified，无 issue） |
| 审阅者  | 张雨田                                                                                                                                                            |
| 日期   | 2026-10-16                                                                                                                                                     |
| 参与关系 | 未参与实现与证据生成；复算脚本本轮新写、不 import 项目计算路径；未调 API、未训模型、未改原始文件                                                                                                         |

**未复核范围**：供应商真实性；V5 继承轨；更早版本报告逐份重审；0.3.80 四条轨迹独立重放；contextual 备选解释的独立裁决。旧人工签字范围不扩展，独立复审在项目侧仍登记 pending，科学 HOLD 不变。
