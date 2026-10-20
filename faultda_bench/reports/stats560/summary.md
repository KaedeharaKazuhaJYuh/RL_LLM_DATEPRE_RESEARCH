# 0.5.60 冻结结果不确定性摘要（描述性）

本表只对已冻结、已评分的历史开发结果重新计数；全部为已见开发簇，不是独立测试，不重打分，未运行新模型或供应商请求。科学 HOLD。

设置：置信度 0.95，自助重采样 10000 次，种子 560，百分位区间。带 * 的簇自助区间簇数少于 10，仅作描述；零宽区间只说明各簇比率相同（平衡设计），不代表确定性。精确 McNemar/符号检验假定配对单元独立；这里的配对单元在任务/来源簇内相关，C3、C4 又是确定性脚本程序，所以 p 值只描述配对计数的不对称，不是推断或泛化证据。

## 各臂计数

| 比较 | 臂 | 指标 | k/n | Wilson 95% | 簇自助 95%（簇键, 簇数） | 证据边界 |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | contextual | all_fields_correct | 0/12 | [0.000, 0.242] | [0.000, 0.000]（window, 3）*; source: 不可用 | 已见开发簇·非独立测试·llm_deepseek_flash·来源簇 1 |
| C1 | explicit | all_fields_correct | 6/12 | [0.254, 0.746] | [0.500, 0.500]（window, 3）*; source: 不可用 | 已见开发簇·非独立测试·llm_deepseek_flash·来源簇 1 |
| C2 | original | safe_complete | 4/12 | [0.138, 0.609] | [0.000, 1.000]（task_id, 3）* | 已见开发簇·非独立测试·llm_deepseek_flash·来源簇 3 |
| C2 | explicit | safe_complete | 4/12 | [0.138, 0.609] | [0.000, 1.000]（task_id, 3）* | 已见开发簇·非独立测试·llm_deepseek_flash·来源簇 3 |
| C3 | abstain | safe_complete | 0/384 | [0.000, 0.010] | [0.000, 0.000]（task_id, 24）; [0.000, 0.000]（source_id, 3）* | 已见开发簇·非独立测试·scripted_program·来源簇 3 |
| C3 | blind_retry | safe_complete | 96/384 | [0.209, 0.296] | [0.250, 0.250]（task_id, 24）; [0.250, 0.250]（source_id, 3）* | 已见开发簇·非独立测试·scripted_program·来源簇 3 |
| C3 | generic_verify | safe_complete | 192/384 | [0.450, 0.550] | [0.500, 0.500]（task_id, 24）; [0.500, 0.500]（source_id, 3）* | 已见开发簇·非独立测试·scripted_program·来源簇 3 |
| C3 | version_refresh | safe_complete | 216/384 | [0.513, 0.611] | [0.484, 0.641]（task_id, 24）; [0.562, 0.562]（source_id, 3）* | 已见开发簇·非独立测试·scripted_program·来源簇 3 |
| C3 | static_semantic | safe_complete | 288/384 | [0.704, 0.791] | [0.750, 0.750]（task_id, 24）; [0.750, 0.750]（source_id, 3）* | 已见开发簇·非独立测试·scripted_program·来源簇 3 |
| C3 | task_semantic | safe_complete | 288/384 | [0.704, 0.791] | [0.750, 0.750]（task_id, 24）; [0.750, 0.750]（source_id, 3）* | 已见开发簇·非独立测试·scripted_program·来源簇 3 |
| C4 | complete_public_rule | supported_correct_termination/raw | 72/72 | [0.949, 1.000] | [1.000, 1.000]（task, 6）*; [1.000, 1.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | complete_public_rule | actual_safe_completion/raw | 24/72 | [0.235, 0.448] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_stop | supported_correct_termination/raw | 24/72 | [0.235, 0.448] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_stop | actual_safe_completion/raw | 36/72 | [0.387, 0.613] | [0.500, 0.500]（task, 6）*; [0.292, 0.708]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_escalate | supported_correct_termination/raw | 48/72 | [0.552, 0.765] | [0.667, 0.667]（task, 6）*; [0.528, 0.806]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_escalate | actual_safe_completion/raw | 0/72 | [0.000, 0.051] | [0.000, 0.000]（task, 6）*; [0.000, 0.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | complete_public_rule | supported_correct_termination/shared_numeric | 72/72 | [0.949, 1.000] | [1.000, 1.000]（task, 6）*; [1.000, 1.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | complete_public_rule | actual_safe_completion/shared_numeric | 24/72 | [0.235, 0.448] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_stop | supported_correct_termination/shared_numeric | 24/72 | [0.235, 0.448] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_stop | actual_safe_completion/shared_numeric | 36/72 | [0.387, 0.613] | [0.500, 0.500]（task, 6）*; [0.292, 0.708]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_escalate | supported_correct_termination/shared_numeric | 48/72 | [0.552, 0.765] | [0.667, 0.667]（task, 6）*; [0.528, 0.806]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_escalate | actual_safe_completion/shared_numeric | 0/72 | [0.000, 0.051] | [0.000, 0.000]（task, 6）*; [0.000, 0.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C5 | registered_complete_rule | supported_correct_termination/pooled | 144/144 | [0.974, 1.000] | [1.000, 1.000]（task, 6）*; [1.000, 1.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C5 | registered_complete_rule | actual_safe_completion/pooled | 48/144 | [0.262, 0.414] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |

## 配对精确检验（Holm 族大小 15）

| 比较 | 臂 A vs 臂 B | 指标 | 配对 b/c | 差值 | 差值簇自助 95% | 精确 p | Holm p |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | explicit vs contextual | all_fields_correct | 6/0 | 0.500 | [0.500, 0.500]（window, 3）*; source: 不可用 | 0.0312 | 0.125 |
| C2 | explicit vs original | safe_complete | 0/0 | 0.000 | [0.000, 0.000]（task_id, 3）* | 1 | 1 |
| C3 | task_semantic vs static_semantic | safe_complete | 0/0 | 0.000 | [0.000, 0.000]（task_id, 24）; [0.000, 0.000]（source_id, 3）* | 1 | 1 |
| C3 | static_semantic vs version_refresh | safe_complete | 72/0 | 0.188 | [0.109, 0.266]（task_id, 24）; [0.188, 0.188]（source_id, 3）* | 4.24e-22 | 5.51e-21 |
| C3 | version_refresh vs generic_verify | safe_complete | 72/48 | 0.062 | [-0.016, 0.141]（task_id, 24）; [0.062, 0.062]（source_id, 3）* | 0.0353 | 0.125 |
| C3 | generic_verify vs blind_retry | safe_complete | 96/0 | 0.250 | [0.250, 0.250]（task_id, 24）; [0.250, 0.250]（source_id, 3）* | 2.52e-29 | 3.79e-28 |
| C3 | blind_retry vs abstain | safe_complete | 96/0 | 0.250 | [0.250, 0.250]（task_id, 24）; [0.250, 0.250]（source_id, 3）* | 2.52e-29 | 3.79e-28 |
| C4 | complete_public_rule vs always_stop | supported_correct_termination/raw | 48/0 | 0.667 | [0.667, 0.667]（task, 6）*; [0.528, 0.806]（state, 24）; source: 不可用 | 7.11e-15 | 8.53e-14 |
| C4 | complete_public_rule vs always_escalate | supported_correct_termination/raw | 24/0 | 0.333 | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 1.19e-07 | 1.19e-06 |
| C4 | complete_public_rule vs always_stop | actual_safe_completion/raw | 0/12 | -0.167 | [-0.167, -0.167]（task, 6）*; [-0.236, -0.097]（state, 24）; source: 不可用 | 0.000488 | 0.00293 |
| C4 | complete_public_rule vs always_escalate | actual_safe_completion/raw | 24/0 | 0.333 | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 1.19e-07 | 1.19e-06 |
| C4 | complete_public_rule vs always_stop | supported_correct_termination/shared_numeric | 48/0 | 0.667 | [0.667, 0.667]（task, 6）*; [0.528, 0.806]（state, 24）; source: 不可用 | 7.11e-15 | 8.53e-14 |
| C4 | complete_public_rule vs always_escalate | supported_correct_termination/shared_numeric | 24/0 | 0.333 | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 1.19e-07 | 1.19e-06 |
| C4 | complete_public_rule vs always_stop | actual_safe_completion/shared_numeric | 0/12 | -0.167 | [-0.167, -0.167]（task, 6）*; [-0.236, -0.097]（state, 24）; source: 不可用 | 0.000488 | 0.00293 |
| C4 | complete_public_rule vs always_escalate | actual_safe_completion/shared_numeric | 24/0 | 0.333 | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 1.19e-07 | 1.19e-06 |

## 不可用比较

- U1 model (LLM/RL) arm on the termination550/555 packets：never executed: new_model_executions = 0 in both qualification files
- U2 paired arm comparison for C5：only one arm is graded; reported as single-arm counts plus equality with C4
- U3 learned SFT/DPO/GRPO arms on the 24 FaultDA cross-source tasks：no frozen per-case FaultDA file exists; inherited V5 results use another protocol/task suite and are not combined
- U4 source-level cluster bootstrap for C1, C4, C5：one data source only (n_clusters = 1)
- U5 independent held-out test set; human interface-validity review：none exist in the repository; all inputs are seen historical development data

## 样本量边界

- 双侧 α=0.05 精确符号检验至少需要 6 个同向不一致对。
- 两比例最小可检测差（正态近似，基线 0.5，功效 0.80，未计聚类）：n=12: 0.572，n=72: 0.233，n=144: 0.165，n=384: 0.101。
- With 12 pairs no split below 6 discordant pairs can reach p <= 0.05; MDE uses baseline 0.5, alpha 0.05, power 0.80 and ignores clustering, so the true detectable effect is larger.
