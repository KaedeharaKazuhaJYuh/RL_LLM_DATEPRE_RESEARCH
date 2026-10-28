# 分支与文档导航

以下为 **2026-10-28** 核对远程分支时的快照；提交可能继续变化。当前工作在 `agent-eval-reliability-reset`，本机未提交修改以 `git status` 为准。

| 类别 | 远程分支 | 快照提交 | 用途与状态 |
| --- | --- | --- | --- |
| 主线 | `main` | `a769ce7` | 包含 FaultDA-Bench 0.5.65 阶段，见 [PR #10](https://github.com/KaedeharaKazuhaJYuh/RL_LLM_DATEPRE_RESEARCH/pull/10)。 |
| 当前研究 | `agent-eval-reliability-reset` | `9b1b11c` | Reliability Reset 与 0.5.66 的离线分析；后续工作尚未合入 `main`。 |
| 历史检查点 | `faultda-bench` | `240e159` | FaultDA 阶段检查点，已进入 `main`。 |
| 历史检查点 | `v2-verifiable-routing` | `cbc18c0` | V2 代码与研究背景，已进入 `main`。 |
| 历史检查点 | `v3-discriminative-benchmark` | `1d75caf` | V3 代码与研究背景，已进入 `main`。 |
| 历史检查点 | `v4-protocol` | `1c4ad89` | V4 代码与研究背景，已进入 `main`。 |
| 历史检查点 | `v5` | `5fa33c4` | V5 代码与研究背景，已进入 `main`。 |
| 已合入的开发分支 | `faultda-0.5.60-dev` | `304fd9d` | 经 [PR #8](https://github.com/KaedeharaKazuhaJYuh/RL_LLM_DATEPRE_RESEARCH/pull/8) 合入 `faultda-bench`，随后进入 `main`。 |
| 已合入的开发分支 | `faultda-0.5.65-dev` | `8fec88e` | 经 [PR #9](https://github.com/KaedeharaKazuhaJYuh/RL_LLM_DATEPRE_RESEARCH/pull/9) 合入 `faultda-bench`，随后进入 `main`。 |
| 已合入的开发分支 | `faultda-0.5.66-dev` | `7392ab3` | 经 [PR #11](https://github.com/KaedeharaKazuhaJYuh/RL_LLM_DATEPRE_RESEARCH/pull/11) 合入当前研究分支。 |
| 已合入的开发分支 | `terminal-taxonomy` | `4410d00` | 经 [PR #12](https://github.com/KaedeharaKazuhaJYuh/RL_LLM_DATEPRE_RESEARCH/pull/12) 合入当前研究分支。 |

优先使用表中的无前缀分支名。已合入的四个开发分支可作为后续整理候选，`main`、当前研究线和历史版本检查点应按其用途保留。分支可能在此快照之后更新；清理前重新核对分支提交和 PR。合并方式也可能改变提交祖先关系，不能仅凭祖先判断是否合入。

PR 的说明保留提交时的原文。0.5.66 和终止分类的后续表述更正见[版本报告](../faultda_bench/reports/RELEASE_0566.md)和[终止分类记录](../research/reliability_reset/TERMINAL_TAXONOMY.md)。

## 文件从哪里找

| 需要查找 | 入口 |
| --- | --- |
| 当前项目范围、主要结果与使用方式 | [项目首页](../README.md) |
| 当前研究、最新评估回应与试点设计 | [Reliability Reset](../research/reliability_reset/README.md) |
| 基准组件、协议和证据 | [FaultDA 组件索引](../faultda_bench/README.md) |
| 按阶段查阅旧版本及完整索引 | [项目历史](PROJECT_HISTORY.md) · [研究线更新记录](../research/reliability_reset/CHANGELOG.md) |
| 运行当前检查和查询旧命令 | [复现与运行指南](REPRODUCIBILITY.md) |

各阶段报告、原始协议和冻结证据继续位于原路径。可编辑指南和跨平台检出规则的当前摘要由 CI 单独登记，历史冻结清单保留原状。不要将不同协议、数据或评分得到的结果合并比较；哈希与本地重放只能说明对应范围内的一致性。
