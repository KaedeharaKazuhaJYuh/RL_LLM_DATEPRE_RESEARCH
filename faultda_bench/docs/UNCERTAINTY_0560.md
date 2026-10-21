# 0.5.60 不确定性报告｜方法与边界

`faultda_bench/stats560/` 只用 numpy 与标准库，对已冻结、已评分的历史开发结果重新计数并给出区间与配对检验。不重打分、不运行模型或供应商请求，科学 HOLD。

## 方法（`stats560/core.py`）

| 函数 | 内容 |
| --- | --- |
| `wilson_interval` | 二项比例 Wilson 得分区间，裁剪到 [0, 1] |
| `bootstrap_ci` | 独立重采样百分位自助区间（均值/比例） |
| `cluster_bootstrap_ci` | 整簇有放回重采样，重算合并比率；簇少于 2 个时拒绝 |
| `exact_sign_test` / `mcnemar_exact` | 双侧精确二项符号检验；McNemar 即对不一致对做符号检验 |
| `holm_bonferroni` | Holm 逐步校正，按输入顺序返回，封顶 1 |
| `min_discordant_for_significance`、`sign_test_power`、`mde_two_proportions` | 最少不一致对数、精确符号检验功效、两比例最小可检测差（正态近似） |
| `round_floats` | 输出前把摘要里每个浮点数量化到 12 位有效数字，见下「跨平台可复现」 |

每次重采样都由给定种子新建生成器（默认 10000 次、种子 560、置信度 0.95），结果确定且与调用顺序无关。

## 跨平台可复现（浮点量化）

`build_summary()` 在返回前**只在这一处**调用 `core.round_floats`，把摘要中每个浮点数量化到 **12 位有效数字**（`core.QUANTIZE_DIGITS`，并写入摘要的 `settings.float_significant_digits`）。因此提交的摘要、`--output` 产物与测试看到的数值完全一致。

双精度本身带 15–17 位有效数字，末几位会随解释器与平台合法地变化。CPython 3.12 把内置 `sum()` 改为补偿（Neumaier）求和，于是 `sign_test_power` 这类浮点求和相对 3.11 会差 1–2 个 ULP：96 个不一致对的精确功效在 3.11 为 `0.9999916596887876`，在 3.12/3.13 为 `0.9999916596887874`。量化丢掉这些不稳定的低位，使 `.json` 与 `.md` 在不同 Python 版本和平台上逐字节相同。

**为什么用有效数字而不是小数位**：本审计的精确符号检验 p 值最小到约 `2.5e-29`，若按 12 位*小数*四舍五入会被写成 `0.0`，等于宣称一个检验从未得出的精确零值；12 位有效数字让每个 p 值与区间端点都保持有意义，同时仍丢掉不稳定的低位。

量化只是可复现措施：计数、排序、Holm 族大小与任何统计结论都不改变。整数、布尔、字符串与 `None` 原样通过，`-0.0` 归一为 `0.0`，键顺序不变。Markdown 本就按 3 位格式化，量化前后逐字节相同。回归测试固定了这份契约：幂等、量化到既定精度、`-0.0` 归一、非浮点不变，且 `build_summary()` 的每个浮点都等于自身的量化值（任何未量化的浮点都无法进入产物）。

## 输入绑定与输出位置

[`stats560_inputs_v1.json`](../protocols/stats560_inputs_v1.json) 列出 7 个输入。审计先确认 `acceptance_v46.json` 自身哈希为固定 0.5.55 值，再要求每个输入的清单哈希 = 冻结目录哈希 = 实际字节哈希，否则拒绝。各臂计数须与冻结摘要一致（C5 还须与 C4 完整规则逐行相同），以证明只是再计数。

`python -m faultda_bench.stats560.audit --output work/stats560.json` 同时写 `.json` 与 `.md`，以独占模式打开，不覆盖已有文件。仓库内只允许写入 `work/` 或 `faultda_bench/reports/stats560/`；冻结清单中的文件和 `faultda_bench/protocols/` 一律拒绝。提交的[摘要](../reports/stats560/summary.md)由默认设置生成，测试核对其与新运行完全一致。

## 指标语义修正：定义性恒等与双向记账

独立复审（终止协议复审 Q2）指出原表有三个呈现缺陷，本版在冻结前改正，**只增不删**：原有计数、p 值与 Holm 值一个未改，Holm 族仍为 15。

**1. 定义性恒等就地标注。** `design.rule()` 在 `public_evidence(obs)['evidence_supported_stop']` 为真时返回 `stop`，而 `design.grade()` 用同一函数、同一载荷重算 `supported`，所以 `complete_public_rule` 在 `supported_correct_termination` 上的 72/72 是数学恒等，不是结果；`unsupported_stop = 0` 与 `unjustified_escalation_by_legacy_proof = 0` 同理。凡该臂落在这三个指标上的行（含 C5 的 `registered_complete_rule`，其逐行等同 C4 完整规则），`summary.json` 加 `definitional_identity: true` 与 `identity_note`，`summary.md` 在指标名与 p 值后标 `†` 并在表下给脚注。**不删除任何计算值**：删掉 p 值会丢失审计链，使产物无法由代码复现；恒等的处理方式是标注，不是隐藏。受影响 7 行（C4 各臂 2 + C5 1 + C4 配对检验 4）。

**2. 补上单侧指标缺失的扣分侧。** `actual_safe_completion` 定义为 `action == 'stop' and actual_safe_stop`，只加分、不对"真实不安全却 stop"扣分。因此 `always_stop` 在合并分母下以 36/72 对 24/72 领先（Holm p = 0.00293）——该计数不对称是真的，但它靠 **36 次真实不安全的 stop** 换来，而规则是 **0 次**。新增 `terminal_outcome_accounting` 从同一批冻结行派生出扣分侧：`truth_unsafe_stop_all_rows`（规则 0/72、`always_stop` 36/72、`always_escalate` 0/72）与双向的 `outcome_correct_vs_private_truth_all_rows`（60/72、36/72、36/72）。`grade()` 里没有任何真值参照的惩罚指标，这个量此前无处可见。

**3. 按仓库自身协议分层分母。** [`METRICS_0510_PROTOCOL.md`](METRICS_0510_PROTOCOL.md) 要求未解决证据层单列、不计入可明确解决层主分母；0.5.50 的 `grade()` 与 C4 却把 72 行并入一个分母。新章节按协议给出分层计数：主分母 48（支持 stop 24 + 已确认历史违规 24），未解决层 24 单列。协议主指标"正确终止"上规则为 **48/48**，两个退化对照各 24/48，合并分母下的反转不出现。保留一个诚实的细节：可明确解决层上安全完成 **24/48 对 24/48 打平**——在本夹具上规则并未找到 `always_stop` 漏掉的安全完成，规则的全部可测价值在于不做不安全的 stop。协议所列量中"新违规"在本夹具不可计算（终止诊断只评一个决策、不模拟动作效果），按不可用列出而非编造。

**4. 记录 `raw` 与 `shared_numeric` 当前不测量任何东西。** `design.packet()` 把 `numeric_helper` 放在 observation 旁边，而 `rule()` 与 `grade()` 只读 `public_evidence(observation)`，两个脚本对照是常量，没有任何臂读取该助手。因此两种条件下每个计数完全相同——这一点由审计断言（`conditions_identical`）而非假设，并写在数字旁边。C5 的 144 包是 72 行评两次，不是 144 个独立任务。

分层交叉表同时说明反转的来源：`unresolved_risk` 层内部真值 12/12 对半切，使"赌一把"在真值上恰好收支平衡（+12 安全完成，+12 不安全 stop），所以在只有上行、没有下行的指标下赌必胜。该 12/12 切分是夹具属性，不携带科学含义。

本节是对已冻结输入的描述性再计数：不重打分、未运行模型、无供应商请求，科学仍为 HOLD。

## 比较与不可用项

- C1 coherent395 回执事实（真实 DeepSeek，12 对，窗口簇 3）；C2 clarity v2 说明对照（真实 DeepSeek，12 对，任务=来源簇 3）；C3 跨来源六个程序策略（384 格，任务簇 24、来源簇 3）；C4 termination550 完整规则与总停/总升级负对照（每种信息条件 72 行，任务簇 6、状态簇 24）；C5 termination555 注册评分（144 包，单臂）；C4-ACCOUNTING termination550 双向结果记账（按 METRICS_0510 分层分母，派生自同一批冻结行，不做检验）。
- U1 终止包上的模型臂从未运行；U2 C5 无配对臂；U3 24 题上无冻结的学习策略逐案结果，继承 V5 结果协议不同、不合并；U4 C1/C4/C5 只有一个数据来源，无法做来源级簇自助；U5 没有独立留出测试与人类接口有效性审查。

## 解释边界

全部为已见历史开发簇，不是独立测试。精确检验假定配对独立，而这里配对在簇内相关，C3、C4 还是确定性脚本，p 值只描述计数不对称。标 `†` 的行更弱一层：该臂的分数由构造固定，p 值连计数不对称都不描述，不构成证据。簇少于 10 的簇自助区间只作描述；零宽区间来自平衡设计，不代表确定性。C4-ACCOUNTING 的分层计数与派生量同样来自单一来源、单一开发簇的旧数据，只说明本夹具上三个脚本臂的结果结构，不支持任何关于模型能力或泛化的结论。本模块不提出新的科学发现或模型提升。
