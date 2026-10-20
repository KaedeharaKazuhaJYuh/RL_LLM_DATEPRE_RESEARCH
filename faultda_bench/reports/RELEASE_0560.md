# FaultDA-Bench 0.5.60-dev｜冻结结果不确定性报告、CI 对齐与英文概览

2026-10-20。工程与论文准备版本：API/新模型/训练/重打分 0，科学 HOLD，新增独立人审尚未安排。不提出新的科学发现或模型提升。

## 本版内容

- **CI 对齐**：`.github/workflows/faultda-current.yml` 改用 Python 3.11（与 `requires-python` 一致），在原 review530 测试后补跑 release535、binding_probe、trajectory_evidence_audit、termination_case_analysis、termination550、termination555、termination555_runtime、stats560 与 release_version 测试，并执行 `scripts.release_version --check`、`termination555.performance_audit` 与 `stats560.audit`，上传四份结果。历史 `tests.yml` 未改（属冻结文件）。
- **不确定性报告**：新增 `faultda_bench/stats560/`（numpy+标准库）与离线审计 `python -m faultda_bench.stats560.audit --output <path>`。输入经 [`stats560_inputs_v1.json`](../protocols/stats560_inputs_v1.json) 绑定 `acceptance_v46.json` 冻结哈希；各臂计数必须与冻结摘要一致，C5 须与 C4 完整规则逐行相同。方法与边界见[说明](../docs/UNCERTAINTY_0560.md)，完整输出见[摘要](stats560/summary.md)。
- **测试入口**：三个旧测试类在 `setUpClass` 中创建被忽略的 `work/`，干净检出时 `python -m unittest discover -s tests` 不再出现 7 个 `FileNotFoundError`；`python -m pytest` 同样可用（`pip install -e .[test]`）。
- **英文概览**：[docs/en/FAULTDA_BENCH_OVERVIEW.md](../../docs/en/FAULTDA_BENCH_OVERVIEW.md)，所有数字注明来源文件，并列出 KDD 准备缺口。
- `VERSION`（5.0.15-beta.2）与 `pyproject.toml` 未改：后者在 660 份冻结文件内，改动会使冻结核验失败，因此未添加项目元数据。

## 描述性摘要（默认设置：10000 次重采样，种子 560）

以下均为已见历史开发簇的再计数，不是独立测试。精确检验假定配对独立，而配对在簇内相关，C3、C4 为确定性脚本，p 值只描述计数不对称；带 * 的簇自助区间簇数少于 10，零宽区间来自平衡设计。

### 各臂计数

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

### 配对精确检验（Holm 族大小 15）

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

不可用（不给数字）：U1 终止包上的模型臂从未运行；U2 C5 只有单臂；U3 24 题上没有冻结的学习策略逐案结果；U4 C1/C4/C5 只有一个数据来源；U5 没有独立留出测试与人类接口有效性审查。

## 实际验证（本机，Python 3.11.15，`.agents` 外部虚拟环境，numpy 2.3.5）

| 命令 | 结果 |
| --- | --- |
| `python -m pip install -e .` | 成功（系统用户目录只读，改在虚拟环境中安装） |
| `python -m unittest discover -s tests -v`（运行前删除 `work/`） | 640 项，0 失败，0 错误，2 跳过，47.163 秒；改前基线 625 项，0 失败，7 错误，2 跳过 |
| `python -m pytest -q` | 638 通过，2 跳过 |
| `python -m unittest tests.test_faultda_termination555_runtime tests.test_faultda_termination555 tests.test_faultda_stats560 -v` | 32 项通过（其中 stats560 15 项） |
| `python -m faultda_bench.termination555.performance_audit`（另加 `--historical`） | `verified_optimized_offline_only`，660 份冻结文件与 11 份优化文件核验；历史重放通过 |
| `python -m faultda_bench.stats560.audit --output work/stats560.json` | 5 组比较、15 项配对检验（一个 Holm 族）、5 项不可用；输出与提交摘要逐字节相同 |
| `python -m scripts.release_version --check` | `V5.0.15-beta.2: release metadata consistent` |
| 当前证据 CI 作业本地逐步重放（无 `work/` 的副本） | 全部步骤退出码 0；所列 unittest 416 项通过 |
| YAML 解析 `faultda-current.yml` | PyYAML（仅验证用）与 Ruby YAML 均通过 |
| 冻结核对 | 671 个冻结/优化文件哈希全部一致，均不在相对 `faultda-bench` 的改动中 |

完整记录见 `RELEASE_0560_VALIDATION.json`。

## 待决事项

- **LICENSE**：仓库没有许可证文件，由所有者决定；本版不添加。
- 0.5.60 新文件尚未进入新的冻结目录（acceptance_v47），由所有者在发布时决定。
- `pyproject.toml` 项目元数据保持不变（冻结文件）。
- 独立留出测试集、更多来源与任务、多模型评测、人类接口有效性审查仍缺；这些也是 KDD 投稿前的主要缺口。
