# RL + LLM Data Analysis Agent — V3.6 Final

V4 可训练 LLM 试验已建立新来源与未见工具组合划分，并导出经环境回放验证的监督轨迹。LoRA 训练、冻结模型评测及其结果须分开记录；目前的划分是合成开发协议，不是外部真实数据或最终盲测。见 [V4 可训练 LLM 试验协议](reports/V4_LLM_TRAINING_PILOT.md)，入口为 `research.v4_llm_protocol`、`experiments.v4_llm_export`、`experiments.v4_llm_sft` 和 `experiments.v4_llm_eval`。

V4 已增加 SFT 后的 action-level DPO 试验：`experiments.v4_llm_dpo` 用环境验证的专家动作对比提前 stop 和错误动作，作为在线 RL/GRPO 之前的偏好优化基线。首轮完整开发评测为 83/96，仍需在线采样和最终盲测。

V4 已完成最小在线 GRPO 链路烟测：`experiments.v4_llm_grpo` 从 SFT→DPO 适配器采样完整工具轨迹，用环境终局奖励做组内相对优势更新；8 条训练轨迹全部通过，12 任务开发子集为 21/24。该结果仅证明链路可运行，不代表已完成 RL 泛化。

V4 GRPO 后续审计修正了正常/故障轨迹混组造成的伪优势，并在零优势时跳过优化器以避免浮点 KL 经 Adam 放大。均衡覆盖 8 个训练组合族的 64 条轨迹全部通过、组内无奖励方差，冻结开发结果仍为 83/96，与 DPO 相同；当前瓶颈是训练任务过易、缺少有效 RL 信号，而不是继续增加更新轮数。

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
