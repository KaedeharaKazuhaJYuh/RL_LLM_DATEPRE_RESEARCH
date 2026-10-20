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

每次重采样都由给定种子新建生成器（默认 10000 次、种子 560、置信度 0.95），结果确定且与调用顺序无关。

## 输入绑定与输出位置

[`stats560_inputs_v1.json`](../protocols/stats560_inputs_v1.json) 列出 7 个输入。审计先确认 `acceptance_v46.json` 自身哈希为固定 0.5.55 值，再要求每个输入的清单哈希 = 冻结目录哈希 = 实际字节哈希，否则拒绝。各臂计数须与冻结摘要一致（C5 还须与 C4 完整规则逐行相同），以证明只是再计数。

`python -m faultda_bench.stats560.audit --output work/stats560.json` 同时写 `.json` 与 `.md`，以独占模式打开，不覆盖已有文件。仓库内只允许写入 `work/` 或 `faultda_bench/reports/stats560/`；冻结清单中的文件和 `faultda_bench/protocols/` 一律拒绝。提交的[摘要](../reports/stats560/summary.md)由默认设置生成，测试核对其与新运行完全一致。

## 比较与不可用项

- C1 coherent395 回执事实（真实 DeepSeek，12 对，窗口簇 3）；C2 clarity v2 说明对照（真实 DeepSeek，12 对，任务=来源簇 3）；C3 跨来源六个程序策略（384 格，任务簇 24、来源簇 3）；C4 termination550 完整规则与总停/总升级负对照（每种信息条件 72 行，任务簇 6、状态簇 24）；C5 termination555 注册评分（144 包，单臂）。
- U1 终止包上的模型臂从未运行；U2 C5 无配对臂；U3 24 题上无冻结的学习策略逐案结果，继承 V5 结果协议不同、不合并；U4 C1/C4/C5 只有一个数据来源，无法做来源级簇自助；U5 没有独立留出测试与人类接口有效性审查。

## 解释边界

全部为已见历史开发簇，不是独立测试。精确检验假定配对独立，而这里配对在簇内相关，C3、C4 还是确定性脚本，p 值只描述计数不对称。簇少于 10 的簇自助区间只作描述；零宽区间来自平衡设计，不代表确定性。本模块不提出新的科学发现或模型提升。
