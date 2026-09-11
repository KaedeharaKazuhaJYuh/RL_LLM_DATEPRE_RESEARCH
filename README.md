# RL + LLM Data Analysis Agent

这是我的一个可复现研究项目。我希望研究：强化学习能否利用可验证的数据分析反馈，让 LLM Agent 更准确地选择工具、调整分析计划、处理错误，并减少不必要的工具调用。

## 我在研究什么

我把数据分析 Agent 看成一个连续决策系统：Agent 读取任务和数据状态，选择下一步工具，获得数据观察结果，再根据 Verifier 的反馈继续行动或停止。我的核心研究问题是：

> 当数据分析结果可以被程序化验证时，Verifier 反馈能否训练出比固定规则更好的工具选择策略？

我先用小型 CSV 数据集和 50 个可复现实验任务建立可靠基线，再逐步引入 Contextual Bandit、Offline RL 和参数高效的 LLM 训练。这样可以先验证“学习式决策是否有效”，再扩大模型和训练规模。

## 项目假设

- 规则路由可以提供稳定、低成本的初始基线。
- LLM 可以完成开放式任务理解，但容易选择不匹配的工具。
- 任务合同、动作约束和 Verifier 可以降低无效行动，并让奖励信号可计算。
- 当任务状态、动作和奖励定义足够稳定时，Contextual Bandit 有机会学习到比静态规则更好的策略。

## 系统架构

```text
任务 + 数据集
      │
      ▼
状态提取 ──► 策略层：Rule Router / LLM / Contextual Bandit
      │                                      │
      │                                      ▼
      └──────────────────────────────► 工具白名单
                                             │
                                             ▼
                                      Observation / Trace
                                             │
                                             ▼
                                  Verifier：正确性、证据、合同、成本
                                             │
                                             ▼
                                  Reward ──► Bandit 更新 / 轨迹记录
```

我把策略层、工具层和验证层分开，因此可以在相同任务、数据和预算下公平比较不同方法：

- Rule Router：根据任务特征和关键词选择确定性工具。
- LLM Agent：让 DeepSeek 等 OpenAI-compatible 模型从动作白名单中选择工具。
- Contextual Bandit：使用 LinUCB 根据状态特征选择动作，并用 Verifier 分数更新参数。
- 后续 Offline RL：使用已经记录的状态、动作、观察和奖励训练更长程的策略。

## 50 个实验任务

我设计了 50 个任务，并按能力分成十组：

| 能力组 | 任务 | 主要验证内容 |
|---|---:|---|
| 数据读取与概览 | T01–T05 | 字段、行列数、缺失率、类别频数、重复行 |
| 数据清洗 | T06–T10 | 去重、日期、异常值、缺失值、类别拼写 |
| 聚合分析 | T11–T15 | 月度汇总、分组均值、Top-K、占比、透视 |
| 统计分析 | T16–T20 | 描述统计、置信区间、相关性、A/B 差异、异常影响 |
| 时间序列 | T21–T25 | 趋势、环比、移动平均、峰值和简单预测 |
| 可视化 | T26–T30 | 图表选择、分布、趋势、分组比较和异常标注 |
| 特征工程 | T31–T35 | 日期特征、比率、标准化、编码和泄漏检查 |
| 建模 | T36–T40 | 回归、分类、树模型、交叉验证和基线比较 |
| 解释与决策 | T41–T45 | 特征解释、业务建议、成本收益和报告生成 |
| 鲁棒性与恢复 | T46–T50 | 列名变化、文件缺失、重试、复核和预算限制 |

任务定义位于 `tasks/tasks.jsonl`，参考输出位于 `tasks/reference_outputs.json`。参考答案只用于独立验证，不应该被 Agent 直接看到。

## Verifier 与奖励

我使用程序化 Verifier 检查四类内容：

1. 输出结构是否完整，是否真的产生了答案和证据。
2. 数值或结构化结果是否符合 `gold.expected` 或参考输出。
3. 工具调用是否属于任务允许的白名单，是否超过预算。
4. 对 T12–T50，分析操作和必需字段是否符合任务合同。

当前奖励由正确性、证据和成本组成。每个任务结束后，Bandit 使用 Verifier 分数更新；所有轨迹会保存为 JSONL，方便之后进行错误分析和 Offline RL。

## 运行方式

安装依赖后，我可以运行规则基线：

```powershell
python -m pip install -e .
python -m experiments.run --mode rule --out reports/rule_results.jsonl
```

运行 Contextual Bandit：

```powershell
python -m experiments.run --mode bandit --seed 7 --no-contract-protection --out reports/bandit_seed7.jsonl
```

运行 DeepSeek：

```powershell
$env:LLM_PROVIDER="deepseek"
$env:DEEPSEEK_MODEL="deepseek-chat"
$env:DEEPSEEK_API_KEY="粘贴你的 DeepSeek API Key"
python -m experiments.run --mode llm --limit 50 --out reports/deepseek_results.jsonl
```

为了研究任务级动作约束的作用，我可以额外开启动作掩码：

```powershell
python -m experiments.run --mode llm --limit 50 --task-action-mask --out reports/deepseek_masked.jsonl
```

我不会把 API Key 写入代码、任务文件或 GitHub。多 seed 实验可以使用：

```powershell
python -m scripts.run_matrix --seeds 1,2,3,4,5 --methods rule,bandit
```

结果汇总：

```powershell
python -m experiments.aggregate reports/rule_results.jsonl reports/bandit_seed7.jsonl --out reports/summary.json
```

## 项目结构

```text
.
├─ agent/                 # 状态、策略、Bandit、工具和 LLM 适配器
├─ configs/               # 实验配置
├─ data/                  # 可复现实验数据
├─ tasks/                 # 50 个任务、schema、gold 和参考输出
├─ verifier/              # 结果、合同、合法性和成本验证
├─ experiments/           # 单轮运行、矩阵运行和结果汇总
├─ reports/               # 实验结果、失败分析和报告
├─ scripts/               # 任务生成和批量运行脚本
├─ tests/                 # 核心单元测试
├─ CHANGELOG.md           # 项目变更记录
└─ pyproject.toml         # Python 项目配置
```

## 我的研究路线

我计划按以下顺序推进：

1. 固定任务、数据、Verifier 和预算，建立 Rule Router 与 LLM 基线。
2. 分析 LLM 的错误工具选择，并比较 raw 与 task-action-mask 条件。
3. 在相同任务上训练和评估 Contextual Bandit，报告多 seed 均值和标准差。
4. 积累高质量轨迹，进入 Offline RL，学习多步计划和错误恢复。
5. 在资源允许时，再研究 LoRA、GRPO/PPO 和更大规模的数据分析 Agent。

我会把实验数字和失败分析放在 `reports/`，把过程变更放在 `CHANGELOG.md`，而不是把运行记录混入项目介绍页。

## 研究边界

当前项目是一个研究原型，不是面向生产环境的通用数据分析平台。现阶段数据集较小，工具集合有限，Bandit 仍需要更多任务重复和更丰富的状态特征。我的目标是先保证问题定义、Verifier、实验条件和结果记录足够清楚，再逐步扩大规模。

