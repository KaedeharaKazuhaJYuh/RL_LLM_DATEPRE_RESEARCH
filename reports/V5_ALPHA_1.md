# V5.0.0-alpha.1：固定负载性能剖析

日期：2026-09-27。基于 V4.5.10 收尾提交 `f2291e4` 建立 `v5` 分支。本版交付可选的 CUDA 同步计时、峰值显存记录、重复测量审计，以及本机 SFT、在线 GRPO 和完整干净开发评测各三次重复结果。模型效果研究结论仍以 V4 报告为准；此处只判断系统耗时方向，不增加新训练结论。

## 固定输入与测量方法

本机为 Windows 11、Python 3.12.14、PyTorch 2.9.1+cu128、Transformers 5.17.0、PEFT 0.21.0、NVIDIA GeForce RTX 5070 Ti Laptop GPU。基座权重 SHA-256：`58858233513d76b8703e72eed6ce16807b523328188e13329257fb9594462945`。所有测量顺序串行，使用同一 GPU；每个负载在新 Python 进程执行三次，带模型加载和输出保存，原始结果与计时 JSON 留在本机 Git 忽略的 `work/v5_alpha1_*`。

| 负载 | 固定条件 | 三轮结果一致性 |
| --- | --- | --- |
| SFT | `tasks/v4/llm_composition_v1` 的 1728 条训练步骤，输入摘要 `9470cf5c…3fb`，seed 20260921，2 个优化器步骤、每步 4 次梯度累积 | 3 个适配器摘要均为 `79308e70…2d3f` |
| GRPO | `tasks/v4/llm_hard_v1`、旧 SFT 适配器摘要 `7f845067…817`，训练来源扫描预选 1 个有信号组，4 条轨迹、1 次更新、1 个 PPO epoch，seed 20260921 | 每轮 4 条轨迹、1 组真实更新、1 条终局成功；3 个适配器摘要均为 `a3606204…c961` |
| GPU 评测 | 同一旧 SFT 适配器、`tasks/v4/llm_hard_v1` 全部 48 条开发任务，干净条件、贪心解码 | 每轮 36/48，完整结果 JSON SHA-256 均为 `6c3c6fad62590ec5f4450a73df71f432768744708df46cc8b33e26380fc8d855` |

GPU 计时在每个阶段前后同步设备，避免把异步提交当作计算完成；阶段可以嵌套，例如训练循环包含前向/反向，环境步骤包含工具和验证，**不得把各阶段秒数直接相加**。记录从 profiler 建立到写入结果前的墙钟时间，以及 PyTorch 最大已分配 CUDA 显存；不含进程启动和 Python 导入。这里的 p95 为三次重复的最近秩统计，恰好等于三次中的最大值，不能当作稳定尾延迟估计。同步计时会产生额外开销，不能用于宣称优化后吞吐提升。

## 本机结果

| 负载 | 总墙钟中位数 / 三次最大 | 关键阶段中位数 | 峰值 CUDA 已分配 |
| --- | ---: | --- | ---: |
| SFT，2 步 | 10.88 / 10.89 秒 | 模型加载 2.77 秒；训练循环 3.49 秒，其中前向/反向 3.17 秒；输入分词 0.68 秒 | 4.19 GB |
| GRPO，4 条轨迹 | 21.57 / 21.99 秒 | 采样及环境 7.90 秒；行为/参考前向 2.81 秒；更新前向/反向 3.14 秒；模型加载 4.10 秒；工具执行 0.023 秒 | 5.34 GB |
| 完整干净开发评测，48 题 | 94.14 / 96.45 秒 | 197 次模型生成合计 88.74 秒；模型加载 3.92 秒；149 次工具执行合计 0.435 秒；CSV 读取 0.091 秒 | 3.64 GB |

机器可读的 [SFT](v5_alpha1_sft_profile_audit.json)、[GRPO](v5_alpha1_grpo_profile_audit.json) 和[完整评测](v5_alpha1_eval_full_profile_audit.json)审计保留每次计时文件的 SHA-256、调用次数、墙钟区间及所有阶段。审计拒绝工作负载元数据、阶段集合或调用次数不一致的重复结果。本轮 SFT/GRPO 仅为**固定小预算训练探针**，并非 100 步 SFT 或多组 GRPO 全程性能；完整评测只覆盖干净条件，不包含 NPU 或故障矩阵。

## 由证据决定的下一步

在当前小 CSV 负载上，完整评测工具执行的 0.435 秒中位数低于总墙钟的 0.5%，而模型生成约占 94%。即使只优化该工具执行路径，其对本负载的端到端收益也有限。V4 的 C++ 移动平均原型继续保持独立；**本版不接入 Python 默认工具后端，也不声称 C++ 加速**。接下来先对 1 千、10 万和 100 万行的固定表重复测量 Python/NumPy 与 C++，核对转换成本及完整 episode 收益，只有满足既定差分和端到端门槛再接入。

模型生成和参考/更新前向是更有价值的测量方向。V5.0-alpha.2 前应在固定任务上比较模型驻留、可控批处理与显存占用，先验证结果一致及精度，再比较实际吞吐。Go 分布式实验管理目前仍是单机 runner；下一阶段按既定计划实现持久队列、租约、资源独占与进程树取消，不能从这些性能数字推导多机能力。RL 训练本身还需针对 V4.5.10 发现的错误建立新训练信号，并用全新来源及模板留出评测；不得在 V4.5.10 的 12 道题上继续选模型。

## NPU 回归检查

本机 Intel AI Boost NPU 探测和 OpenVINO 图推理通过。另以 V4 已使用的混合 INT4/INT8 DPO 合并模型，在 `tasks/v4/llm_pilot_v1` 固定前 12 题的正常与瞬时读取故障共 24 次执行中得到 **15/24**，与先前 V4 NPU 记录一致；零解析错误。原始文件 `work/v5_alpha1_npu_regression.json` 的 SHA-256 为 `ec520e03a64c06efbdf9175e046c42a335070e17922577bdd11e30ef404b4355`。本次模型编译 62.98 秒，90 次生成平均每次 3.02 秒。只执行了一次 NPU 回归，没有 p95 或跨设备性能结论。该 NPU 模型、协议和量化精度均与上表 GPU 固定负载不同，**不能把两者通过率或耗时直接比较**；GPU 仍承担训练和 BF16 主评测，NPU 作为可运行的量化推理路径保留。

## 复现入口

在本机已有相同模型与环境时，下列命令复现各负载的一次运行；重复时把输出中的 `r1` 依次改为 `r2`、`r3`，并保证 GPU 上没有其他本项目作业。输出路径若已存在，训练/评测和审计均拒绝覆盖。

```powershell
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_llm_sft --steps work/v4_llm_composition_export_v1/train_steps.jsonl --model work/modelscope_deepseek_r1_1p5b --out work/v5_alpha1_sft_r1 --max-steps 2 --seed 20260921 --profile-out work/v5_alpha1_sft_r1_profile.json
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_llm_grpo --protocol tasks/v4/llm_hard_v1 --model work/modelscope_deepseek_r1_1p5b --adapter work/v4_llm_hard_sft_100_001/adapter --signal-scan work/v4_llm_signal_scan_seed20260921/summary.json --signal-limit 1 --updates 1 --group-size 4 --ppo-epochs 1 --temperature 0.9 --seed 20260921 --out work/v5_alpha1_grpo_r1 --profile-out work/v5_alpha1_grpo_r1_profile.json
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_llm_eval --protocol tasks/v4/llm_hard_v1 --model work/modelscope_deepseek_r1_1p5b --adapter work/v4_llm_hard_sft_100_001/adapter --out work/v5_alpha1_eval_full_r1.json --profile-out work/v5_alpha1_eval_full_r1_profile.json
work/.venv-v4-llm/Scripts/python.exe -m research.v5_profile_audit work/v5_alpha1_eval_full_r1_profile.json work/v5_alpha1_eval_full_r2_profile.json work/v5_alpha1_eval_full_r3_profile.json --out work/v5_alpha1_eval_repeat_audit.json
```

本版验证：Python 单元测试 86/86、Go 单机运行器测试、C++ 既有原生测试程序和 `research.benchmark` 均通过；历史 V2 保护路径未发生改动。独立评测数据和 V4 已冻结的结果未重写。
