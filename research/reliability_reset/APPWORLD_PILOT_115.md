# 1.1.05：六场景模型试跑与调用账本

实验记录日期：2026-10-31；整理日期：2026-11-01。研究问题仍是：**原生完整评分通过的 Agent 运行中，是否存在可独立确认的协议违规或有害副作用？** 本轮没有原生通过的模型运行，因而无法计算这一条件下的漏判率。强规则对照和独立安全裁决尚未完成，科学状态保持 HOLD。

## 六个训练场景

从 AppWorld 0.2.0 的 train 场景按本地固定规则选择六个不同场景 ID；每个场景取一个任务变体。它们不是随机或未见测试集，任务血缘尚未独立审查。下表按场景计数，重试不算新场景：

| 模型或检查点 | 原生完整评分通过 | 终止情况 | 解释 |
| --- | ---: | --- | --- |
| DeepSeek Flash API | 0/6 | 3 次 stop、3 次达到 16 轮上限 | 真实 API，启用 JSON 模式 |
| Qwen2.5-0.5B-Instruct | 0/6 | 3 次 stop、3 次达到 16 轮上限 | 本地 CUDA |
| Granite 4.0-350M | 0/6 | 6 次 stop | 本地 CUDA；不在最初的本地协议模型清单中，作为探索性补充 |
| SmolLM2-360M-Instruct | 0/6 | 5 次输入上限、1 次达到 16 轮上限 | 本地 CUDA；前五条为资源截断，不能当作等预算模型排名 |

前三组采用每轮最多 512 输出 token、16 轮和 48,000 提示字节上限；SmolLM 另受 **2,000 输入 token、10,000 提示字节**限制。模型聊天模板不同，DeepSeek 使用 JSON 模式，本地模型没有等价的服务端约束。原始 1.1.05 方案还列出 DeepSeek-R1-Distill-Qwen，六场景运行未完成；Granite 不是预先冻结清单中的替代对照。四个模型来源不等于四个独立样本，六个场景也尚不能支持总体或跨任务的统计推广。

Granite 的本地 `model.safetensors` SHA-256 为 `21bc1ccaf0eb6a8a503addd93cb7422df71129de0a641a5525e4a665813b6dfc`，与 [IBM 官方模型文件元数据](https://huggingface.co/ibm-granite/granite-4.0-350m/blob/bd8a1497065c0d6ba1ef19af6b0d2b14bacf71c2/model.safetensors)一致；这只校验权重文件。Qwen 和 SmolLM 权重检查见 [1.1.0 记录](APPWORLD_PILOT_110.md)，DeepSeek 服务端模型别名可能变化。

## 中断、资源上限与计数

蓝屏前两条 SmolLM 记录都在同一场景中断；为排查蓝屏另有一次短时重试。这三条均保留为未完成或诊断尝试，不算三个场景。此前一条轨迹中，输入从 534 增长到 5,751 token，记录的 PyTorch 累计显存分配峰值从约 0.77 GiB 增至 5.34 GiB。它说明输入增长与显存需求同时上升，**不能证明蓝屏根因**。

新增的本地输入上限在 tokenizer 完成后、输入送入 CUDA 前检查；超过上限时记录 `input_token_limit`，保留原始提案，不补参数或修改历史轨迹。受限试跑中六个场景的 PyTorch 累计分配峰值约为 1.04–1.22 GiB；这是进程内分配量，不是整卡保留显存或能耗。首条验证轨迹曾把上限拒绝也计入 `model_calls`；该原始记录保留，随后修正了控制器计数，公开账本将拒绝单独标注。

## 探索性扩展与原生重放

在观察原始结果之后，为 DeepSeek 加入公开的发现接口与 supervisor 参数说明，六个场景的完整评分仍为 0/6；改变了提示内容，不能称为配对的模型能力提升。被蓝屏中断的第六条以新名称重试，原始中断记录和其不完整末行均保留。

另一组事后增加轮数的探索性尝试中，两条轨迹的 supervisor 状态为 `success`，但原生完整评分分别为 **4/5、5/6**。SDK 的 `task_completed()` 同时将 `success` 和 `fail` 视为任务已结束，不能把该布尔值本身当作成功；这里的 `success` 来自记录的 supervisor 响应。两个原生评分在各自独立的新进程中重放一致，并核对了五个既有评分源码文件的摘要。它们说明状态信号与完整评分可能不同，并未证明原生评分漏判了不安全行为。

[重放结果](evidence/1.1.05/NATIVE_REPLAY_115.json)使用同一批本地数据和既有摘要，不是独立人工复审或外部历史认证。扩展组还包含三次请求错误（`URLError`，没有 HTTP 状态）和一次中断；重试与原尝试分别保留，不能当成新增独立任务。

## 调用记录与费用范围

[脱敏账本](evidence/1.1.05/CALLS_115.jsonl)包含 1,690 条模型请求、工具调用和 SDK HTTP 记录；工具调用与其内部 HTTP 记录存在嵌套，不能把它们简单相加成独立动作。账本不含原始任务、模型回复、参数或模拟凭据。[汇总](evidence/1.1.05/SUMMARY_115.json)和[场景映射清单](evidence/1.1.05/COHORT_115.json)保留中断、重试、上限和不可用值。SDK 的 `sdk_track` 是 SDK 标志，不单独证明动作责任。

所有已纳入尝试中，DeepSeek 有 402 条收到的响应、3 条请求错误及 3 条中断后未确认的请求。按运行时记录的峰时单价计算，已收到且有用量字段的响应合计约 **0.08965667 美元**；未知请求是否计费、账单折扣和实际付款均未知，所以这不是总账单或完整成本上界。[DeepSeek 价格说明](https://api-docs.deepseek.com/quick_start/pricing/) · 本地推理记录了耗时与部分 GPU 分配量，但没有电力费用和能耗。

## 重现与后续门槛

原始 AppWorld 任务、数据库、模型权重和请求/回复只在本机 `work/` 中；公开结果不随仓库分发这些内容。具有相应原始数据及运行环境时，可用以下命令在新的输出目录重建脱敏记录，并用两个独立进程重放上述原生评分：

```powershell
python -m research.reliability_reset.appworld_ledger115 work/reliability-reset-1.1.05 research/reliability_reset/evidence/1.1.05/COHORT_115.json work/reliability-reset-1.1.05/new-ledger
python -m research.reliability_reset.appworld_replay115 work/reliability-reset-1.1.05 work/reliability-reset-1.0.85/venv/Scripts/python.exe research/reliability_reset/evidence/1.1.05/COHORT_115.json work/reliability-reset-1.1.05/new-replay.json --attempt deepseek-ext-115-s01 --attempt deepseek-ext-115-r03
```

下一步应先建立具有相同公开信息、工具权限和预算的强规则对照，并完成任务血缘与独立副作用裁决。只有出现足够的原生通过轨迹，才能评估原生评分漏判；当前六个场景和不等资源限制不支持扩大到数百任务或 RL 提升的结论。
