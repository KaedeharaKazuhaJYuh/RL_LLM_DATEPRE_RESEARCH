# FaultDA-Bench 0.5.60-dev｜冻结结果不确定性报告、CI 对齐与英文概览

2026-10-20。工程与论文准备版本：API/新模型/训练/重打分 0，科学 HOLD，新增独立人审尚未安排。不提出新的科学发现或模型提升。

## 本版内容

- **CI 对齐与防漂移**：`.github/workflows/faultda-current.yml` 改用 Python 3.11（与 `requires-python` 一致）。YAML 里**不再内联任何模块清单**：单一事实来源移到 [`current_evidence_v1.json`](../protocols/current_evidence_v1.json)，由 `python -m faultda_bench.current_evidence --list/--run-tests/--run-audits` 执行，上传四份结果。两道守卫：完整性测试要求每个 `tests/test_faultda_*.py` 要么登记、要么带理由排除（原先 77 个文件中有 22 个静默缺失），YAML 守卫要求工作流不得重新内联清单且必须调用该入口。历史 `tests.yml` 未改（属冻结文件）。
- **指标语义修正（独立复审 Q2，冻结前改正，只增不删）**：原表把 `complete_public_rule` 在 `supported_correct_termination` 上的 72/72 当作结果并做显著性检验，而它是定义性恒等；`actual_safe_completion` 又只加分不扣分，使 `always_stop` 看似胜出。本版就地标注 7 行恒等（`definitional_identity` + `†`），并新增 `terminal_outcome_accounting`：补上派生的"真实不安全 stop"（规则 0/72、`always_stop` 36/72）与按 `METRICS_0510_PROTOCOL.md` 分层的分母（协议主指标规则 48/48 对 24/48），同时记录 `raw`/`shared_numeric` 当前不测量任何东西。**既有计数、p 值与 Holm 族大小 15 一个未改**，只补另一侧与标记。详见[说明](../docs/UNCERTAINTY_0560.md)。
- **不确定性报告**：新增 `faultda_bench/stats560/`（numpy+标准库）与离线审计 `python -m faultda_bench.stats560.audit --output <path>`。输入经 [`stats560_inputs_v1.json`](../protocols/stats560_inputs_v1.json) 绑定 `acceptance_v46.json` 冻结哈希；各臂计数必须与冻结摘要一致，C5 须与 C4 完整规则逐行相同。方法与边界见[说明](../docs/UNCERTAINTY_0560.md)，完整输出见[摘要](stats560/summary.md)。
- **跨版本浮点确定性**：`build_summary()` 返回前只在一处调用 `core.round_floats`，把摘要里每个浮点量化到 12 位有效数字（记录在 `settings.float_significant_digits`）。CPython 3.12 把内置 `sum()` 改为补偿求和，`sign_test_power` 相对 3.11 差 1–2 个 ULP（96 个不一致对：`...887876` vs `...887874`），曾使历史 `tests.yml`（Python 3.12）上的「提交摘要 == 新运行」断言失败。选有效数字而非小数位，是因为本审计的精确 p 值最小到 `2.5e-29`，按 12 位小数会被写成 `0.0`。量化只为跨平台逐字节一致，不改变任何计数、排序或统计结论；`summary.md` 逐字节未变。方法见[说明](../docs/UNCERTAINTY_0560.md)。
- **测试入口**：三个旧测试类在 `setUpClass` 中创建被忽略的 `work/`，干净检出时 `python -m unittest discover -s tests` 不再出现 7 个 `FileNotFoundError`；`python -m pytest` 同样可用（`pip install -e .[test]`）。
- **英文概览**：[docs/en/FAULTDA_BENCH_OVERVIEW.md](../../docs/en/FAULTDA_BENCH_OVERVIEW.md)，所有数字注明来源文件，并列出 KDD 准备缺口。
- `VERSION`（5.0.15-beta.2）与 `pyproject.toml` 未改：后者在 660 份冻结文件内，改动会使冻结核验失败，因此未添加项目元数据。

## 描述性摘要（默认设置：10000 次重采样，种子 560）

以下均为已见历史开发簇的再计数，不是独立测试。精确检验假定配对独立，而配对在簇内相关，C3、C4 为确定性脚本，p 值只描述计数不对称；带 * 的簇自助区间簇数少于 10，零宽区间来自平衡设计。

**读表前必读两点（独立复审 Q2 后于冻结前改正，只增不删）**：

1. 带 **†** 的行是**定义性恒等**，不是结果。`design.rule()` 在 `public_evidence(obs)['evidence_supported_stop']` 为真时返回 `stop`，`design.grade()` 用同一函数、同一载荷重算 `supported`，因此 `complete_public_rule` 在 `supported_correct_termination` 上只能得 72/72。这些 p 值（低至 Holm 8.53e-14）**不构成证据**。计算值按原样保留以保全审计链，只加标记，不删除。
2. `actual_safe_completion` 只加分、不对"真实不安全却 stop"扣分，所以 `always_stop` 在合并分母下的 36/72 对 24/72 领先（Holm p = 0.00293）是单侧指标的产物：它靠 **36 次真实不安全的 stop** 换来 12 行优势，而规则是 **0 次**。补齐的扣分侧与按仓库自身 `METRICS_0510_PROTOCOL.md` 分层分母的计数见下文「终止结果双向记账」；在协议主指标上规则 **48/48** 对 24/48，反转不出现。

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
| C4 | complete_public_rule | supported_correct_termination/raw † | 72/72 | [0.949, 1.000] | [1.000, 1.000]（task, 6）*; [1.000, 1.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | complete_public_rule | actual_safe_completion/raw | 24/72 | [0.235, 0.448] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_stop | supported_correct_termination/raw | 24/72 | [0.235, 0.448] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_stop | actual_safe_completion/raw | 36/72 | [0.387, 0.613] | [0.500, 0.500]（task, 6）*; [0.292, 0.708]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_escalate | supported_correct_termination/raw | 48/72 | [0.552, 0.765] | [0.667, 0.667]（task, 6）*; [0.528, 0.806]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_escalate | actual_safe_completion/raw | 0/72 | [0.000, 0.051] | [0.000, 0.000]（task, 6）*; [0.000, 0.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | complete_public_rule | supported_correct_termination/shared_numeric † | 72/72 | [0.949, 1.000] | [1.000, 1.000]（task, 6）*; [1.000, 1.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | complete_public_rule | actual_safe_completion/shared_numeric | 24/72 | [0.235, 0.448] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_stop | supported_correct_termination/shared_numeric | 24/72 | [0.235, 0.448] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_stop | actual_safe_completion/shared_numeric | 36/72 | [0.387, 0.613] | [0.500, 0.500]（task, 6）*; [0.292, 0.708]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_escalate | supported_correct_termination/shared_numeric | 48/72 | [0.552, 0.765] | [0.667, 0.667]（task, 6）*; [0.528, 0.806]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C4 | always_escalate | actual_safe_completion/shared_numeric | 0/72 | [0.000, 0.051] | [0.000, 0.000]（task, 6）*; [0.000, 0.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C5 | registered_complete_rule | supported_correct_termination/pooled † | 144/144 | [0.974, 1.000] | [1.000, 1.000]（task, 6）*; [1.000, 1.000]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |
| C5 | registered_complete_rule | actual_safe_completion/pooled | 48/144 | [0.262, 0.414] | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 已见开发簇·非独立测试·scripted_program·来源簇 1 |

† 定义性恒等 — `complete_public_rule` 的动作即该指标的判定条件（`design.rule()` 与 `grade()` 调用同一 `public_evidence()`、同一载荷），该臂不可能得到别的分数，故此计数不是独立科学发现。

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
| C4 | complete_public_rule vs always_stop | supported_correct_termination/raw † | 48/0 | 0.667 | [0.667, 0.667]（task, 6）*; [0.528, 0.806]（state, 24）; source: 不可用 | 7.11e-15 † | 8.53e-14 † |
| C4 | complete_public_rule vs always_escalate | supported_correct_termination/raw † | 24/0 | 0.333 | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 1.19e-07 † | 1.19e-06 † |
| C4 | complete_public_rule vs always_stop | actual_safe_completion/raw | 0/12 | -0.167 | [-0.167, -0.167]（task, 6）*; [-0.236, -0.097]（state, 24）; source: 不可用 | 0.000488 | 0.00293 |
| C4 | complete_public_rule vs always_escalate | actual_safe_completion/raw | 24/0 | 0.333 | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 1.19e-07 | 1.19e-06 |
| C4 | complete_public_rule vs always_stop | supported_correct_termination/shared_numeric † | 48/0 | 0.667 | [0.667, 0.667]（task, 6）*; [0.528, 0.806]（state, 24）; source: 不可用 | 7.11e-15 † | 8.53e-14 † |
| C4 | complete_public_rule vs always_escalate | supported_correct_termination/shared_numeric † | 24/0 | 0.333 | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 1.19e-07 † | 1.19e-06 † |
| C4 | complete_public_rule vs always_stop | actual_safe_completion/shared_numeric | 0/12 | -0.167 | [-0.167, -0.167]（task, 6）*; [-0.236, -0.097]（state, 24）; source: 不可用 | 0.000488 | 0.00293 |
| C4 | complete_public_rule vs always_escalate | actual_safe_completion/shared_numeric | 24/0 | 0.333 | [0.333, 0.333]（task, 6）*; [0.194, 0.472]（state, 24）; source: 不可用 | 1.19e-07 | 1.19e-06 |

† 定义性恒等 — `complete_public_rule` 的动作即该指标的判定条件（`design.rule()` 与 `grade()` 调用同一 `public_evidence()`、同一载荷），故此 p 值不构成证据。计算值按原样保留以保全审计链，仅加标记，不删除。

### 终止结果双向记账（C4-ACCOUNTING）

与 C4 同一批冻结逐案结果的再计数，补上 `design.grade()` 缺少的扣分侧；分母按 [`METRICS_0510_PROTOCOL.md`](../docs/METRICS_0510_PROTOCOL.md)：可明确解决层（支持 stop 24 + 已确认历史违规 24 = 48）为主分母，未解决证据层 24 单列。上面 C4 的合并分母计数一个未改。

公开分层与私有真值（`private_truth.actual_safe_stop_if_taken`）交叉表：

| 公开分层 | n | 真实可安全 stop | 真实不可安全 stop |
| --- | --- | --- | --- |
| supported_stop | 24 | 24 | 0 |
| confirmed_violation | 24 | 0 | 24 |
| unresolved_risk | 24 | 12 | 12 |
| total | 72 | 36 | 36 |

| 量 | complete_public_rule | always_stop | always_escalate |
| --- | --- | --- | --- |
| 预定总数（/72） | 72 | 72 | 72 |
| 主分母：可明确解决层 n | 48 | 48 | 48 |
| **正确终止（/48，协议主指标）** | **48** | 24 | 24 |
| 安全完成（/48） | 24 | 24 | 0 |
| 已确认历史违规升级（/48） | 24 | 0 | 24 |
| 可避免升级（/48） | 0 | 0 | 24 |
| 未解决层 n（单列分母） | 24 | 24 | 24 |
| 不确定升级（/24，单列，不计入主分母） | 24 | 0 | 24 |
| 不受支持 stop（/72） | 0 | 48 | 0 |
| **真实不安全 stop（/72，派生：原表缺失的扣分侧）** | **0** | **36** | 0 |
| **对照私有真值的结果正确（/72，派生，双向）** | **60** | 36 | 36 |
| 无效/删失（/72） | 0 | 0 | 0 |

读法与边界：

- 反转的来源是 `unresolved_risk` 层内部真值 12/12 对半切：在只有加分、没有扣分的指标下，赌一把恰好收支平衡（+12 安全完成，+12 不安全 stop）。该切分是夹具属性，不携带科学含义。
- 诚实的细节：可明确解决层上安全完成 **24/48 对 24/48 打平**——本夹具上规则并未找到 `always_stop` 漏掉的安全完成。规则的全部可测价值在于不做不安全的 stop（0 对 36）与正确终止（48/48 对 24/48）。
- `raw` 与 `shared_numeric` 当前不测量任何东西：`numeric_helper` 放在 observation 旁边，而 `rule()` 与 `grade()` 只读 `public_evidence(observation)`，两个脚本对照是常量，没有任何臂读取该助手；因此两种条件下每个计数完全相同（由审计断言 `conditions_identical`，非假设）。C5 的 144 包是 72 行评两次，不是 144 个独立任务。
- 协议所列"新违规"在本夹具不可计算：终止诊断只评一个决策、不模拟动作效果，没有决策后的账本差集；按不可用列出，不编造。单一来源、单一开发簇，不支持关于模型能力或泛化的任何结论。

不可用（不给数字）：U1 终止包上的模型臂从未运行；U2 C5 只有单臂；U3 24 题上没有冻结的学习策略逐案结果；U4 C1/C4/C5 只有一个数据来源；U5 没有独立留出测试与人类接口有效性审查。

## 实际验证（本机，Python 3.11.15，`.agents` 外部虚拟环境，numpy 2.3.5）

| 命令 | 结果 |
| --- | --- |
| `python -m pip install -e .` | 成功（系统用户目录只读，改在虚拟环境中安装） |
| `python -m unittest discover -s tests`（运行前删除 `work/`） | 676 项，0 失败，0 错误，2 跳过，50.762 秒；0.5.60 早前基线 649 项，改前基线 625 项（0 失败，7 错误，2 跳过） |
| `python -m pytest -q` | 674 通过，2 跳过 |
| `python -m unittest tests.test_faultda_termination555_runtime tests.test_faultda_termination555 tests.test_faultda_stats560 -v` | 44 项通过（其中 stats560 27 项） |
| **Python 3.12.13 + numpy 2.3.5**（`unittest discover -s tests`） | 676 项，0 失败，0 错误，2 跳过，50.232 秒 |
| **Python 3.12.13 下的 `stats560.audit --output`** | 与提交摘要 `.json`/`.md` 均逐字节相同（`.json` sha256 `dd93c526…`，`.md` `1f577be4…`），证明跨版本一致 |
| `python -m faultda_bench.termination555.performance_audit`（另加 `--historical`） | `verified_optimized_offline_only`，660 份冻结文件与 11 份优化文件核验；历史重放通过 |
| `python -m faultda_bench.stats560.audit --output work/stats560.json` | 5 组比较、15 项配对检验（一个 Holm 族）、5 项不可用、1 组双向记账（7 行标注恒等）；输出与提交摘要逐字节相同 |
| `python -m scripts.release_version --check` | `V5.0.15-beta.2: release metadata consistent` |
| 当前证据 CI 作业本地逐步重放（`current_evidence --list` / `--run-tests` / `--run-audits`） | 全部步骤退出码 0；登记的 unittest 452 项通过，四份产物齐备 |
| YAML 解析 `faultda-current.yml` | PyYAML（仅验证用）与 Ruby YAML 均通过；`grep -c 'tests\.test_'` 为 0，YAML 守卫测试通过 |
| 冻结核对 | 671 个冻结/优化文件哈希全部一致，均不在相对 `faultda-bench` 的改动中 |

完整记录见 `RELEASE_0560_VALIDATION.json`。

## 待决事项

- **LICENSE**：仓库没有许可证文件，由所有者决定；本版不添加。
- 0.5.60 新文件尚未进入新的冻结目录（acceptance_v47），由所有者在发布时决定。
- `pyproject.toml` 项目元数据保持不变（冻结文件）。
- 独立留出测试集、更多来源与任务、多模型评测、人类接口有效性审查仍缺；这些也是 KDD 投稿前的主要缺口。
