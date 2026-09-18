# V4 可训练 LLM 试验协议（2026-09-17）

## 研究问题

此前 V4 更新的是独立的轻量决策策略，没有更新语言模型权重。该试验改为在 DeepSeek-R1-Distill-Qwen-1.5B 上训练 LoRA 适配器，考察模型是否能依据用户请求、工具执行历史和故障反馈输出下一步动作。监督微调是起点；RL 阶段需在此基础上另行实现与比较，不能把监督训练称作 RL。

## 划分与证据边界

`tasks/v4/llm_pilot_v1` 包含 20 个新生成的合成 CSV 来源、176 个两步任务。16 个来源的 128 个任务属于训练；4 个来源的 48 个任务属于开发，其中 32 个沿用训练中的动作组合，16 个使用四种训练阶段未见的动作组合。训练与开发来源和 CSV 哈希不相交，未见组合与训练组合不相交。训练集和开发集的答案分别放在独立文件中。此试验没有外部真实数据测试，也没有最终盲测集。

导出器对训练任务分别在正常执行和第一次工具调用瞬时失败的条件下做专家回放，得到 256 条完整轨迹、896 条状态—动作监督样本。开发任务的 96 条专家回放只用于检验环境和上界，不写入训练步骤。模型输入只含请求、列名、动作成败历史、剩余预算和允许的动作；参数由环境绑定。原始数据、任务/答案文件和导出训练文件均应记录哈希。

## 训练与评测

`experiments.v4_llm_sft` 提供最多 20 个优化步骤的 LoRA 试跑入口。它只对动作 JSON 的答案 token 计算损失，记录训练数据哈希、基座版本、可训练参数数量和适配器哈希。`experiments.v4_llm_eval` 在冻结模型上以贪心解码运行开发任务，并分别报告已见/未见动作组合以及正常/故障执行的通过数。无效 JSON 视为失败，不做答案修复。训练运行目录位于被 Git 忽略的 `work/`，不提交权重或个人密钥。

建议先对基座和 SFT 适配器使用相同的开发子集做配对比较，再扩大至全部 48 个开发任务及两种故障条件；随后冻结 SFT 基线，实现逐轨迹奖励训练，并分别报告成功率、格式错误、额外工具调用、不同来源方差和成本。SFT 在开发集的改进只能支持开发结论，不能证明泛化；进入最终盲测前应冻结训练和模型选择规则。

## 本机首轮实测

本机 RTX 5070 Ti Laptop GPU（12,227 MiB 显存）已运行 `torch 2.9.1+cu128`、Transformers 5.17.0、PEFT 0.21.0、Accelerate 1.15.0。基座从 ModelScope 的 `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` 获取，本地 `model.safetensors` 的 SHA-256 为 `58858233513d76b8703e72eed6ce16807b523328188e13329257fb9594462945`。训练步样本哈希为 `702d3968920410c9ea55f4616bf9ddeb7114724047134c9f1e9c1e436139170b`。独立 4 步烟测和 100 步训练均已保存适配器；后者更新 9,232,384 个 LoRA 参数，平均训练损失 0.1704，运行约 144 秒、显存约 5.9GB，适配器 SHA-256 为 `472acb2748d87b277d16e05561558a487fec078dc9b2b6ce77598c05059a8fb3`。

100 步模型与原始基座在同一 48 个开发任务、每题正常/瞬时故障各一次、贪心解码、最多 48 个新 token、严格 JSON 解析下比较：

| 切片 | 基座 | 100 步 SFT |
| --- | ---: | ---: |
| 已见组合，正常 | 0/32 | 32/32 |
| 已见组合，故障 | 0/32 | 32/32 |
| 未见组合，正常 | 0/16 | 7/16 |
| 未见组合，故障 | 0/16 | 7/16 |
| 合计 | 0/96 | 78/96 |

基座的 96 次执行均在首个输出发生严格 JSON 解析错误；SFT 没有格式错误。额外将基座输出上限增至 256 token，在前四题的正常/故障共 8 次执行仍全部发生格式错误。因此 0→78 的改善包含输出格式学习，不能单独解释为规划能力提升。训练后已见组合全过、未见组合仅 14/32：`normalize_categories → profile_missingness` 和 `normalize_dates → profile_schema` 在四个开发来源上均被提前 `stop`，`deduplicate → correlate` 偶发顺序反转。故障成功与正常成功一一对应，说明本次错误主要集中在组合选择，不在重试机制。所有结果仍属于小规模合成开发集、单一随机种子和贪心执行；尚未进行真实数据、外部盲测、随机解码或 RL 更新。

被 Git 忽略的原始运行记录位于 `work/`。关键文件的 SHA-256：100 步训练摘要 `bcb6ae94ee4a65369c796fd90ab207345a47b6a55b469abcf4d90e0336525861`，基座全量评测 `6eeb4ffed7d513f3cfe0314bf1bf053afa3982cd42b38b7b0b0c351b80f38b34`，SFT 全量评测 `ce7f2c1908222e0bb43bcc0809175999e1c3cad174909d6b6e62ca03396d0596`。

## 第二轮：SFT 后 action-level DPO

首轮直接从基座做 DPO 的 96 次执行仍为 0/96，说明它没有先学会严格动作 JSON。因此 DPO 被改为从 100 步 SFT 适配器继续训练。每个训练状态保留专家下一动作作为 chosen，同时构造提前 `stop` 和一个错误允许动作作为 rejected；参考策略固定为 SFT 适配器，策略只更新 LoRA 参数。40 步训练的损失从 0.6931 降到 0.5766，更新 9,232,384 个参数，适配器保存在被忽略的 `work/v4_llm_sft_dpo_40_001/adapter`。

在同一协议、同一基座、同一贪心评测和 96 条开发执行下，SFT 后 DPO 得到 83/96：

| 切片 | 100 步 SFT | SFT→DPO |
| --- | ---: | ---: |
| 已见组合，正常 | 32/32 | 32/32 |
| 已见组合，故障 | 32/32 | 32/32 |
| 未见组合，正常 | 7/16 | 8/16 |
| 未见组合，故障 | 7/16 | 11/16 |
| 合计 | 78/96 | 83/96 |

这说明环境奖励构造的偏好对对故障重试和部分未见组合有帮助，但不能宣称已经完成 RL 泛化。当前 DPO 仍是离线、单随机种子、单一负动作构造；它没有让模型在线采样轨迹，也没有使用 GRPO 的组内相对优势。下一步应固定 SFT 与 DPO 基线，按同一任务采样多条完整轨迹，以环境最终通过、额外调用和提前停止分别计算奖励，再做小组相对策略更新；所有模型选择必须在开发集冻结后进行最终盲测。

## 运行顺序

Windows 上先建立项目专用环境并下载模型（约 3.55GB）：

```powershell
python -m venv work/.venv-v4-llm
work/.venv-v4-llm/Scripts/python.exe -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
work/.venv-v4-llm/Scripts/python.exe -m pip install -r requirements-v4-llm.txt
work/.venv-v4-llm/Scripts/python.exe -c "from modelscope import snapshot_download; snapshot_download('deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B', local_dir='work/modelscope_deepseek_r1_1p5b')"
```

随后使用同一个环境运行下列模块；如果采用本地模型目录，训练和评测都加上 `--model work/modelscope_deepseek_r1_1p5b`。

```sh
python -m research.v4_llm_protocol
python -m experiments.v4_llm_export --out work/v4_llm_export_001
python -m experiments.v4_llm_sft --out work/v4_llm_sft_001
python -m experiments.v4_llm_eval --out work/v4_llm_base_dev.json --limit 12
python -m experiments.v4_llm_eval --adapter work/v4_llm_sft_001/adapter --out work/v4_llm_sft_dev.json --limit 12
```

生成协议时必须使用一个尚不存在的输出目录；训练和评测的输出路径也不能复用。训练需要独立 Python 环境、CUDA 版 PyTorch、Transformers、PEFT 和 Accelerate，以及模型权重下载。当前 Windows GPU 已用 `torch 2.9.1+cu128` 验证可见。在中国大陆网络环境下可从 [ModelScope 的 deepseek-ai 模型页](https://www.modelscope.cn/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B) 下载，并将本地目录传给 `--model`；训练记录会保存权重 SHA-256。环境、权重和实际训练结果应在运行记录中另行确认；仅有本文件和脚本不构成训练完成证据。
