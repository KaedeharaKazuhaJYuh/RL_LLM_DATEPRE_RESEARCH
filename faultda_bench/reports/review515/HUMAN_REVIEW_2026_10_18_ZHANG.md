# FaultDA 0.5.10-dev 复审记录（含四格设计见证补充包）

审阅人：张雨田

日期：2026-10-18

审阅范围：主包 `FaultDA_0.5.10-dev_Review_2026-10-18_97b8a21.zip`（commit `97b8a218babc10be8b2bbd9dbb34080a671431b9`）；补充包 `FaultDA_Design_Witness_Supplement_2026-10-18_727fb42.zip`（commit `727fb42ecb50ccf2e92e89fa08c1ae93849c1251`）

原始文件：未修改。两个 zip 及其 `.sha256` 保持原状，复审在解压副本上进行，产出另存。

---

## 1. 结论先行

1. **技术一致性通过。** 包内 `review510.audit.verify()` 返回 verified（12 对／4 题／72 条脚本对照／1 个独立簇／HOLD／0 次新 provider 请求）；`unittest discover` 跑完 318 项全过，与 `BUNDLE_VALIDATION.json` 的 `test_count: 318` 对上；补充包 11 个文件 SHA-256 与 `SUPPLEMENT_MANIFEST.json` 全部一致；`review_packet.json` 摘要重算为 `83f8e869…9f80`，与模板登记值一致。
2. **12 对指代的裁决：explicit 是 lookup，contextual 是 both_plausible。** contextual 的 0/12 与备选读法下的 12/12 同时成立。所以"explicit 比 contextual 高 6 分"这句话只能当接口描述，不能当能力差。
3. **责任字段的失败集中在一种措辞碰撞上。** explicit 臂在 6 条 `scripted_current` 上 `receipt_request_id`／`committed`／`revision` 全对，只有 `responsibility` 全错（写成 `historical_agent_action`）。这不是没读懂回执，是被"全部事件都叫 history"的命名带偏了。
4. **四项设计意见：全部 revise。** 两条硬伤在数据层，不在措辞层：全部 12 对来自同一段 8 行切片；而这段切片正是被标为 `external_test: true` / `one_time_evaluation: true` 的 beta_holdout。
5. **科学闸门维持 HOLD，不批准实跑。** 本审阅不构成科研创新性通过，也不授权任何 API 调用。

---

## 2. 我做了哪些核对

| 核对项    | 做法                                                                  | 结果                                               |
| ------ | ------------------------------------------------------------------- | ------------------------------------------------ |
| 包摘要绑定  | 按 `digest()` 规则重算 packet 的 SHA-256                                  | `83f8e869…9f80`，与模板一致                            |
| 包内自检   | `review510.audit.verify()`                                          | verified，范围和绑定均通过                                |
| 测试     | `python -m unittest discover -s tests`                              | 318 项全过（本机 224 秒，与包内 61.7 秒的差异属环境差异）             |
| 补充包完整性 | 逐个文件核对 SHA-256                                                      | 11/11 一致，无缺件                                     |
| 真值复算   | 用 `Decimal` 独立重算 `[14:30:00, 15:24:59)` 的 Temperature 和             | 117.89，与 `TOTALS['base']` 一致；15:24:59 那一行确在右端点之外 |
| 成本表    | 从 `program_results.json` 逐格复算 checks/mutations/decisions/bytes 及差中差 | 与 `FOUR_CELL_WITNESS` 表逐格相符；两条规则的差中差全为 0         |
| 数据来源   | 把包内 8 行输入逐条比对 `tasks/v5/.../occupancy.csv`                          | 8/8 时间与数值完全一致（见第 5.2 节）                          |
| 初始故障   | 读 `recover325/environment.py` 的 `_compute`                          | 118.89 = 117.89 + 1.0，标量注入                       |

没有做模型调用，没有新增数据源，没有改动包内任何文件。

---

## 3. 12 对指代裁决

判断依据只看 prompt（system + user 原文）。每格的目标回执都以 `history:10` 那条 `receipt_lookup` 的 `params.request_id` 为准。

| 格（window｜role｜mode）                                   | contextual 判读  | explicit 判读 |
| ----------------------------------------------------- | -------------- | ----------- |
| base｜historical｜bad_never_committed｜first             | both_plausible | lookup      |
| base｜historical｜bad_committed｜first                   | both_plausible | lookup      |
| base｜scripted_current｜bad_never_committed｜second      | both_plausible | lookup      |
| base｜scripted_current｜bad_committed｜second            | both_plausible | lookup      |
| trim_start｜historical｜bad_never_committed｜second      | both_plausible | lookup      |
| trim_start｜historical｜bad_committed｜second            | both_plausible | lookup      |
| trim_start｜scripted_current｜bad_never_committed｜first | both_plausible | lookup      |
| trim_start｜scripted_current｜bad_committed｜first       | both_plausible | lookup      |
| early_end｜historical｜bad_never_committed｜first        | both_plausible | lookup      |
| early_end｜historical｜bad_committed｜first              | both_plausible | lookup      |
| early_end｜scripted_current｜bad_never_committed｜second | both_plausible | lookup      |
| early_end｜scripted_current｜bad_committed｜second       | both_plausible | lookup      |

**为什么 explicit 是 lookup。** 原句点名了事件位置和动作：`observation.history[-1], whose action is receipt_lookup`。`history:10` 的 params 只有一个 `request_id`，返回 `committed` / `revision`，它指向的那次 publish 在第 4 或第 6 条。位置、动作、字段三者对齐，没有第二种读法。

**为什么 contextual 是 both_plausible。** 原句只有 `the final receipt` 一个限定词。可指向 `history:10` 的 lookup 返回（合同里这就是 durable 回执读取），也可指向 `history:8` 成功 publish 的 `{ok:true, revision:3}`（最后一次写入确认）。两种读法都能恰好填满 `receipt_request_id` / `committed` / `revision`，句子本身没排除任何一方。

有一条不对称的证据要记下来：目标 publish 自己的应答是 `timeout`，而 `reliability_contract.limits` 明写 timeout 不能认证提交，所以 lookup 读法更受支持。但"更受支持"不等于"排他"——`history:8` 的确认回执仍然是合法读法。

**模型实际回答（复核阶段）。**

- contextual：12/12 都报 `history:8` 那次成功 publish（`request-31/17/23`，`committed=true`，`revision=3`）。按 last_publish 读法这是 12/12 全对；按 lookup 读法是 0/12。两个分数都成立，差距全部来自读法。
- explicit：12/12 的 `request_id`、`committed`、`revision` 全对。6 条 historical 全字段正确；6 条 scripted_current 全部把责任写成 `historical_agent_action`，其中 base 那 2 条还把事件号写成 `history:5`——那是 `stage` 事件，不是任何一次 publish，属于无效指代。

一个对照值得项目自己看：同一个模型在 contextual 臂里把 `current_model_action` 判对了 6/6（因为它报的是 index 8，在 scripted 格里 >= 3），在 explicit 臂里却全错。这说明它读得懂 `current_model_start_history_index`，问题出在"目标落在早期 publish 上"时被 `historical` 这个词带偏。措辞问题，不是能力问题。

---

## 4. 责任范围与来源标签

- historical 格：`current_model_start_history_index = 10`，目标 publish 在 4／6，落在边界之前，`historical_agent_action` 唯一，边界清楚。
- scripted_current 格：边界是 3，目标 publish 在 4／6，按合同应判 `current_model_action`。但同一条 user 消息里：11 个事件统一叫 `history`；系统提示并列给出 `historical_agent_action` 这个标签；`trajectory_provenance` 又声明这些动作是脚本生成、"not LLM-generated actions"。三句话对着拉，这一格的 actor 边界我不认为算清楚——本包 6/6 的失配就是这几句话的直接后果。
- 来源标签：`trajectory_provenance` 写得很明确（scripted program counterexample，非模型生成），这一点没有歧义。它和 `current_model_action` 可以并存（前者讲生成来源，后者讲责任归属），但并存本身需要读者自己完成一次区分，文档没有把这层区分说破。

---

## 5. 四项设计意见

### 5.1 design｜increment — revise

材料自己把增量写成待证组合：`RESEARCH_POSITION_0505.md` 末节写"尚未证明该组合是现有评测未充分覆盖的非平凡增量"。这一轮的合格证据还在往反方向推：W4 里 `verify_then_reuse` 与 `always_restage` 在 checks／mutations／decisions／response_bytes 四项上的差中差全为 0，即语义因素 S 能被"一律重新暂存"这条廉价公开规则消掉，S 没有承载不可替代的分析依赖。

对着已列的前作，真正可能剩下的差异只有"actor 责任归属 × 回执不可见"这一维。缺的具体比较是：同一任务上"公开状态推理 + 按风险读回执"强规则与模型的成对差，且该差不能由措辞、检查次数或字节数解释。建议把增量收缩到这一维，并给出可否决的预测；或者放弃 S 维。

依据：`RESEARCH_POSITION_0505.md` §可检验的增量候选与否决条件；`program_results.json` summary.cost_interactions；`FOUR_CELL_WITNESS_2026_10_18.md` §两条公开规则及成本。

### 5.2 design｜independence — revise

独立单位实际只有 1 个。12 对全部来自 `utc_end` 视图的同一段 8 行切片，三个 window 只移动端点（base `[1,6)`、trim_start `[2,6)`、early_end `[1,5)`），36 组"时区等价对"按定义不增加独立性，`coherent_v38_accounting.json` 里 `independent_task_clusters` 也是 1。

更具体的泄漏点：包内那 8 行（id 140/151/162…，2015-02-02 14:19–15:36）逐条比对后，全部来自 `tasks/v5/beta_holdout_v1/data/occupancy.csv`；同一个 manifest 写着 `"external_test": true`、`"one_time_evaluation": true`。与此同时 `faultda_bench/semantic/tasks.py:21` 把这份文件当作 window 家族的开发任务源，`split` 标成 `historical_development`。两份都被 `REVIEW_MANIFEST.json` 钉住的文件，对同一份数据给出互斥标签。

先回答"这份 holdout 到底是开发材料还是一次性外部测试"（改标签或换数据），再谈三个新簇。在数据层面，现在的多簇说法不成立。

依据：`tasks/v5/beta_holdout_v1/manifest.json`；`semantic/tasks.py:21,63`；`coherent395/suite.py:23,35-38,45-47`；`coherent_v38_accounting.json` summary；`CROSS_TASK_ADMISSION_0505.md` 第 1 条。

### 5.3 design｜metrics — revise

三态分层本身是可读的：支持 stop／已确认历史违规／证据未解决在读取前固定，主指标取可明确解决层上的簇宏平均正确终止率，分母含无效输出和预算删失，安全完成与正确升级分开计数。这几点该保留。

会改结论的有四处：

1. 只有 1 个簇，宏平均退化成单簇比率，簇间方差无从估计，成对差值给不出区间。
2. "可明确解决层"由 `public_expected` 这条参考规则判定，而它与被比较的强规则同源，分母与被检对象不独立。协议自己承认这是事后资格核对，那就不能拿它当主指标的分母依据。
3. 责任字段计进正确率。但 scripted_current 那 6 条的事实字段全对、只错 responsibility（本包 explicit 臂即如此），这类错应单列成接口无效，不进能力分母。
4. 12 对是同一格设计下的 12 个组合，不是 12 个独立任务，不能当独立样本算精度。

修订方向：加"独立裁决为无歧义"的准入闸门；按臂共用分母；指代错误与角色错误单列；簇数不足时明确只报描述、不报区间。

依据：`METRICS_0510_PROTOCOL.md` 第 2／4／5／6 段；`metrics_qualification.json`；`coherent_v38_accounting.json` pairs[].arms.explicit.grade。

### 5.4 design｜decision — revise

同意不进入实跑。8 条程序轨迹都合法完成、四次发布内容哈希一致（`a13c692f…`）、没有 Agent 错误发布；而 S 在 00 格只需 `always_restage` 多付 1 次 mutation、1 次 decision 就被绕过。`NO_GO_NEEDS_REVISION` 有证据支撑。

但不要把它读成"交互不存在"。`always_restage` 对 S 是盲的，任何 S 盲规则的四格交互按构造必然为 0——这是设计属性，不是发现。真正能说的是：在这个成本模型里，S 不构成必须恢复的耦合。

还有两点要写进下一版：

- 00 格带共同的环境修复种子。初始报告 118.89 就是真值 117.89 加 1.0 的标量注入（`recover325/environment.py` 的 `_compute`），不是健康负对照。
- S 的载体 `closed=both` 只是对合同字段的串比对错误，拿它代表"语义恢复"偏弱，这也解释了为什么一条"重新暂存"就能化解。

修订方向：换掉 S 的载体（让重算有真实代价，或不可复现），而不是在同一段 8 行切片上继续加格；补真正的 no-fault 对照。

依据：`decision.json` scientific_experiment_decision／limitations；`program_results.json` rows[].total_cost；`recover325/environment.py`；`FOUR_CELL_WITNESS_2026_10_18.md` §排除的构型、§科学决策与下一门槛。

---

以上意见只覆盖本轮所审提交与所列文件范围。旧 37 组技术签字不因本记录扩大解释，本记录也不登记为最终独立裁决。
