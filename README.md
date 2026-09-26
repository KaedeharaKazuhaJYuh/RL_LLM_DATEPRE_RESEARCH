# RL + LLM Data Analysis Agent — V4.5.7

V4.5.7 已在 [V5 三语言架构规划](reports/V4_5_7_V5_ARCHITECTURE_PLAN.md)之外，完成 [分阶段计时与 Go 单机运行器原型](reports/V4_5_7_IMPLEMENTATION.md)。Python 负责 DeepSeek 与 RL 训练；本版可对专家导出和冻结 GPU 评测计时，Go 可按固定清单启动这两种 Python 作业、记录日志并核验产物摘要。手动运行与 Go 启动的导出和评测结果一致。C++ 原生内核、持久队列、租约和真实多机调度仍属 V5 后续工作；V4.5.6 的模型实验结论未改变。

V4.5.5 在训练来源内部增加四类三步组合，保持原 96 条开发执行不变。三种子 SFT100 从旧课程的 52、65、82/96 变为 72、76、70/96：前两个种子受益，最强种子退化 12 题，因此尚不能把扩展课程设为稳定默认方案。V4.5.6 用相同 32 条在线训练预算对照静态/动态采样和进度/二值奖励。三种子的静态进度 GRPO 为 72、76、73/96，动态进度为 71、76、74/96，静态二值为 71、76、72/96；动态相对静态的平均变化为零。当前收益主要在已见组合故障恢复，仍需新的真实数据盲测。详见 [V4.5.5 / V4.5.6 结果与局限](reports/V4_5_5_5_6_RESULTS.md) 和 [预设实验协议](reports/V4_5_5_5_6_PROTOCOL.md)。

V4.5.4 从训练集内部固定抽取全部 8 类三步组合，分别扫描三个 SFT 种子的无更新采样信号，再只对有成功或正确前缀差异的组做保守 GRPO。冻结开发结果为 58、66、82/96，相对 SFT100 分别 +6、+1、0，逐任务无回退；相对 V4.5.3 普通 GRPO，前两个种子各多通过 1 条。扫描额外消耗 192 条训练执行，7 条相对 SFT 的新增通过中有 6 条属于已见组合的故障条件，不能宣称采样更高效或已解决组合泛化。DeepSeek LoRA 已是神经网络权重训练；后续重点是训练信号、组合课程和独立盲测。详见 [V4 神经网络与训练信号研究](reports/V4_NEURAL_RL_RESEARCH.md)。

V4.5.3 完成三个独立随机种子的 SFT100→GRPO 配对审计。SFT100 冻结结果分别为 52、65、82/96，GRPO 后为 57、65、82/96；平均变化为 +1.67 题，但只有 1/3 个种子提升。三轮均无回退，说明当前低学习率与 KL 约束较安全；收益仍依赖初始化和训练组奖励方差，不能宣称稳定提升。见 [V4.5.3 多种子审计](reports/V4_5_3_MULTI_SEED_AUDIT.md)。

V4.5.2 新增三步困难协议、任务级动态预算、正确前缀进度奖励和 SFT→GRPO 课程学习。完整四来源开发评测中，三步 SFT 为 52/96，保守 GRPO 为 57/96；逐任务配对得到 5 条新增通过、0 条回退。该结果是合成开发集上的单次运行，尚需多随机种子重复，见 [V4.5.2 困难任务与 GRPO 报告](reports/V4_5_2_HARD_GRPO.md)。

V4.5.1 将 NPU 接入纳入正式版本范围：训练与 BF16 金标准评测继续使用 CUDA GPU，Intel AI Boost NPU 用于 OpenVINO 量化推理和精度研究。见 [V4.5.1 发布说明](reports/V4_5_1_RELEASE.md)。

## V4.5.2 困难任务结果

| 冻结开发切片 | 三步 SFT100 | SFT100 → GRPO |
| --- | ---: | ---: |
| 已见三步组合，正常 | 31/32 | 31/32 |
| 已见三步组合，故障 | 16/32 | 20/32 |
| 未见三步组合，正常 | 5/16 | 5/16 |
| 未见三步组合，故障 | 0/16 | 1/16 |
| 合计 | 52/96 | 57/96 |

这轮 GRPO 使用 4 类训练任务、每组 4 条轨迹和一次更新；8 个条件组中有 5 个产生非零优势，参考策略 KL 约为 `1.24e-4`。改善集中在故障恢复，正常条件没有发生配对回退。最终盲测仍未创建，因此不能把 57/96 解释为外部泛化结果。

## V4.5.1 概览

训练主线为 `环境验证监督轨迹 → LoRA SFT → action-level DPO → 在线 GRPO`。所有策略输出都在同一个多步工具环境中执行，以终局任务结果计分；GPU、CPU 和 NPU 评测共用任务协议与严格 JSON 动作解析。

| 项目 | 当前状态 | 结果或边界 |
| --- | --- | --- |
| LoRA SFT / DPO | 已完成 | BF16 DPO 冻结开发集 83/96 |
| 在线 GRPO | 链路完成并已审计 | 修正错误分组后仍为 83/96，尚未超过 DPO |
| Intel NPU | 已真实接入 | OpenVINO NPU 图和 1.5B INT4 LLM 均可运行 |
| NPU 冻结评测 | 已完成首轮对照 | 混合 INT4/INT8 为 15/24，低于 GPU BF16 的 21/24 |
| 最终盲测 | 尚未创建 | 待困难训练任务、量化门槛和发布清单冻结后创建 |

旧 GRPO 实现曾因混合正常与故障条件产生伪优势；对应的 85/96 已撤回。修正实现按条件分别成组，并在组内优势全为零时跳过优化器。当前 64 条均衡训练轨迹没有奖励方差，说明下一阶段首先需要构造可学习的困难任务，而不是继续增加更新轮数。

### 快速验证

基础测试不需要 API 密钥或 GPU：

```powershell
python -m pip install numpy==2.3.5
python -m unittest discover -s tests -v
```

NPU 使用独立环境，避免改动 CUDA 训练依赖：

```powershell
python -m venv work/.venv-v4-npu
work/.venv-v4-npu/Scripts/python.exe -m pip install -r requirements-v4-npu.txt
work/.venv-v4-npu/Scripts/python.exe -m experiments.v4_npu_probe
```

使用已转换的 OpenVINO 模型进行 NPU 冻结评测：

```powershell
work/.venv-v4-npu/Scripts/python.exe -m experiments.v4_llm_eval_npu `
  --model work/modelscope_deepseek_r1_1p5b_dpo_merged_ov_int4_ratio08 `
  --device NPU --both-faults --limit 12 `
  --out work/v4_llm_npu_eval.json
```

模型权重、转换产物、密钥和逐次运行文件位于被 Git 忽略的 `work/` 或本地环境文件中，不会进入仓库。完整 NPU 方法、设备信息和量化对照见 [NPU 接入与精度审计](reports/V4_NPU_ENABLEMENT.md)。

V4 可训练 LLM 试验已建立新来源与未见工具组合划分，并导出经环境回放验证的监督轨迹。LoRA 训练、冻结模型评测及其结果须分开记录；目前的划分是合成开发协议，不是外部真实数据或最终盲测。见 [V4 可训练 LLM 试验协议](reports/V4_LLM_TRAINING_PILOT.md)，入口为 `research.v4_llm_protocol`、`experiments.v4_llm_export`、`experiments.v4_llm_sft` 和 `experiments.v4_llm_eval`。

V4 已增加 SFT 后的 action-level DPO 试验：`experiments.v4_llm_dpo` 用环境验证的专家动作对比提前 stop 和错误动作，作为在线 RL/GRPO 之前的偏好优化基线。首轮完整开发评测为 83/96，仍需在线采样和最终盲测。

V4 已完成最小在线 GRPO 链路烟测：`experiments.v4_llm_grpo` 从 SFT→DPO 适配器采样完整工具轨迹，用环境终局奖励做组内相对优势更新；8 条训练轨迹全部通过，12 任务开发子集为 21/24。该结果仅证明链路可运行，不代表已完成 RL 泛化。

V4 GRPO 后续审计修正了正常/故障轨迹混组造成的伪优势，并在零优势时跳过优化器以避免浮点 KL 经 Adam 放大。均衡覆盖 8 个训练组合族的 64 条轨迹全部通过、组内无奖励方差，冻结开发结果仍为 83/96，与 DPO 相同；当前瓶颈是训练任务过易、缺少有效 RL 信号，而不是继续增加更新轮数。

V4 已接入本机 Intel AI Boost NPU：OpenVINO 计算图和 1.5B INT4 LLM 均已实际运行，并新增 NPU 探测、LoRA 合并与冻结评测入口。当前最佳混合 INT4/INT8 NPU 版本在 24 条开发执行中为 15/24，仍低于 BF16 DPO 的 21/24，因此 NPU 暂用于量化研究与辅助推理，CUDA GPU 继续承担训练和金标准评测。见 [NPU 接入与精度审计](reports/V4_NPU_ENABLEMENT.md)。

V4 多步学习阶段：已完成明确任务协议、监督初始化与 REINFORCE 对照，见 [阶段报告](reports/V4_SEQUENCE_RL_STAGE.md)。本轮 RL 从监督基线退化，原始负结果完整保留；不代表 DeepSeek 权重微调。运行入口为 `experiments.v4_sequence_train` 和 `experiments.v4_sequence_live`。

V4 稳定性修正：批量策略梯度、历史条件基线、更新幅度约束及可选监督保持项，将三种子开发验证通过率恢复至 100%；尚未超过监督基线。见 [退化诊断与优化报告](reports/V4_RL_STABILITY.md)，入口 `experiments.v4_sequence_stabilize`。

V4 后续审计发现，前述 100% 仅针对贪心执行；随机执行通过率约 21.8%，新两步组合中本地策略全部失败。DeepSeek 在组合开发探针温度 0 的一次运行中完成 12/12，仍需重复验证。见 [随机执行与组合泛化审计](reports/V4_STOCHASTIC_AND_COMPOSITION.md)。

V3 主结果与边界见 [V3 最终审计](reports/V3_FINAL_AUDIT.md)，后续研究见 [V4 规划](reports/V4_RESEARCH_PLAN.md)。V4 已有外部控制策略 RL 结果，尚无 LLM 权重训练结果。

V4.0 初始协议位于 `tasks/v4/protocol.json`，就绪检查使用 `python -m research.v4_readiness`；当前最终测试集尚未创建，以保留后续盲测有效性。

V4 现已接入 DeepSeek + Bandit 开发试跑：`python -m experiments.v4_pilot --out work/v4_pilot_001`。先在环境变量或被忽略的 `.env.local` 配置 DeepSeek 密钥；方法、费用记录与权重训练边界见 [V4 DeepSeek RL 试跑](reports/V4_DEEPSEEK_RL_PILOT.md)。

运行 `python -m unittest discover -s tests -v` 后，运行 `python -m research.v3_release --out work/v3_acceptance` 完成离线验收。主恢复比较为 480 条交叉测试，自动完成与升级分别计分。以下 V3.1–V3.5 为历史实验，不能代替最终主结果。

> V3 已加入未见提示模板、正交泛化切片、两步有序计划和澄清任务；`research/v3_runtime.py` 会逐步验证产物、更新输入状态并支持一次参数恢复。设计与首轮结果见 `reports/V3_BASELINE_DESIGN.md`。

> V3.1 进一步加入三份带许可和哈希记录的 UCI 真实数据、五类实际故障及训练后冻结的恢复分类器。方法、结果和解释边界见 `reports/V3_1_REAL_RECOVERY.md`。

> V3.2 将冻结测试扩大到三个真实数据源和 102 条故障记录，并加入测试阶段未见故障及低置信度升级机制。结果见 `reports/V3_2_HARDENED_RECOVERY.md`。

> V3.3 将训练、阈值校准、测试来源分离，并加入复合故障、部分写入、编码损坏、随机延迟与 Wilson 区间。结果见 `reports/V3_3_CALIBRATED_COMPOUND_RECOVERY.md`。

> V3.4 使用真实子进程实施硬超时和部分写入，并补充按数据来源bootstrap。结果见 `reports/V3_4_PROCESS_ISOLATION.md`。

> V3.5 将真实数据池扩展到8个来源，采用按来源留一法和异质日志条件，暴露出截短诊断信息下的恢复错误。结果见 `reports/V3_5_LEAVE_ONE_SOURCE_OUT.md`。

V2 是独立验证的单步数据分析路由实验。修复了原版的任务编号捷径、占位清洗、同源参考计算、数据包损坏、奖励与合法性不一致以及不完整日志。

## 已实现

12 种真实参数化操作：schema、缺失率、类别计数、去重、描述统计、日期规范化、阈值截断、中位数填补、类别规范化、分组求和、相关系数、移动平均。清洗会输出实际 CSV，独立验证器读取产物检查。

360 个合成任务实例，按表划分 216/72/72 训练、验证、测试。规则、监督岭分类器、LinUCB 和随机/固定基线共享工具及公开任务；测试时模型冻结。数据实例留出不等于未见模板或真实数据泛化。

## 本地运行

需要 Python 3.11+（本次验证 3.12.14）及 NumPy 2.3.5。运行不要求 GPU、pytest 或 API 密钥。

```sh
python -m pip install numpy==2.3.5
python -m unittest discover -s tests -v
python -m scripts.run_matrix --out-dir reports/my_run --epochs 6
python -m research.compare_v1 --v1-root ../v1 --out-dir reports/my_comparison
```

可选真实 DeepSeek：配置 `DEEPSEEK_API_KEY`、可选 `DEEPSEEK_MODEL` 后运行 `python -m experiments.run --mode llm --out reports/my_llm.jsonl`。本次仅验证模拟客户端，没有执行真实 API 请求。不要提交密钥。

## 结果

[V1/V2 实验报告](reports/V2_COMPARISON.md)记录具体协议与限制。共同 72 题 V1 15/72，V2 Rule 72/72；V2 Rule、监督和 Bandit 在五次冻结测试中都是 72/72。仅数据特征的 Bandit 是 6/72。结果说明已修复基础能力与任务状态，但尚未证明 RL 优于规则。

## 架构

- `research/benchmark.py`：任务、数据、清单生成；历史 CSV 修复。
- `research/oracle.py`：独立参考计算，不调用被测工具。
- `agent/tools.py`：真实计算、参数校验、清洗产物。
- `research/features.py` / `policies.py`：具名数据 profile、文本哈希特征、策略。
- `research/runtime.py`：合法性、预算、完整单步轨迹。
- `verifier/score.py`：答案、证据、产物和资源一致性检查。
- `experiments/run.py`：训练/冻结测试、模型保存、版本哈希。

## 研究边界

任务参数由公开规格提供，尚未训练列名/参数生成。当前不是多步 RL；没有实现旧 T12–T50 文本所宣称的全部建模、绘图、决策与恢复能力。旧 `tasks/tasks.jsonl` 与早期 reports 保留作历史证据，正式 v2 CLI 明确拒绝旧 schema；不得把旧 98%/100% 当作当前真实分析能力。

本地工具在执行前后检查墙钟预算，超时结果失败；不提供 OS 级抢占沙箱。训练与产物在 `artifacts/`，实验日志在显式 manifest 列出的 reports 路径；禁止用宽泛通配符混合版本。新实验会拒绝覆盖同名输出。
