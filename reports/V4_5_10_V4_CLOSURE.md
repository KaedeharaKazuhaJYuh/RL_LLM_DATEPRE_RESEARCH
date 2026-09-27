# V4.5.10：新来源留出评测与 V4 收尾

日期：2026-09-27。本版先在提交 `256a3d6` 冻结[协议、数据、权重摘要与指标](V4_5_10_PREREGISTRATION.md)，再执行专家与本地 DeepSeek 评测；没有依据本次结果修改题目、提示或模型。协议 manifest SHA-256 为 `e58a5b60149ebe8327281fac3672ea486d624f21ce370d17c5e8bab7785c03e4`。

## 本版交付与证据

新增两份此前未用于本项目 V3/V4 的公开 UCI 数据：[Forest Fires](https://archive.ics.uci.edu/dataset/162/forest)（Cortez & Morais，2007，DOI 10.24432/C5D88D）和 [Rice (Cammeo and Osmancik)](https://archive.ics.uci.edu/dataset/545/rice+cammeo+and+osmancik)（2019，DOI 10.24432/C5MW4Z）。两者为 CC BY 4.0。仓库冻结各 240 行的派生 CSV、原档案与派生摘要、选行规则、12 道中英配对两步任务和空训练 oracle。对照 V3 全部八个真实来源和 V4.5.8 的三个来源核对了 URL；无来源重复。题目沿用已经使用过的三种动作组合和提示模板，因而**只留出了数据来源**，不是组合/模板全盲测。

本地 DeepSeek-R1-Distill-Qwen-1.5B 的 BF16 CUDA 基座和 V4.5.5 SFT100 seed 20260921 适配器摘要分别为 `58858233513d76b8703e72eed6ce16807b523328188e13329257fb9594462945` 和 `867a6c91b74a1c4a8b233de6511977e7876008c17ace9df8bab12a877696c9ff`。固定贪心解码、每步最多 48 token、相同工具参数与隔离环境。专家在全部 48 次执行中通过，说明这些目标在工具边界内可达；这不是模型分数。

| 冻结条件 | 专家 | SFT 模型 |
| --- | ---: | ---: |
| 正常 | 12/12 | **10/12** |
| 瞬时读取失败 | 12/12 | 7/12 |
| 超时 | 12/12 | 9/12 |
| 部分写入 | 12/12 | 9/12 |
| 合计 | 48/48 | **35/48** |

模型按来源为森林火灾 16/24、稻米 19/24；按组合为去重→移动平均 15/16、类别规范化→计数 8/16、截断→数值描述 12/16；中文 15/24、英文 20/24。13 次失败中，首次偏离标记为错误动作 12 次、重复动作 1 次。具体轨迹中，森林火灾中文类别题多次把 `normalize_categories` 误作 `normalize_dates`；稻米中文类别题在两步完成后额外调用去重或在故障后提前计数；部分数值题在首步故障后没有重试原动作。这些是**轨迹所见行为**，不能凭小样本断定唯一成因。注入在所有故障执行中均实际触发；专家对超时与部分写入验证了失败产物不进入已提交状态。

[专家逐题审计](v4_5_10_expert_fault_audit.json) SHA-256 为 `cbca9662214ace2f527ad0bf5b3f5a3843d75269cd1fddbe5b2f3aa6a327b5ac`；[模型逐题审计](v4_5_10_model_audit.json) SHA-256 为 `8b38fdb40960669c1815fa89191cc006454406657c432bc755436f4990b28931`。原始模型输出保存在本机被 Git 忽略的 `work/v4_5_10_model_evaluation.json`，SHA-256 为 `6521f790c177722ee962c94386fc99611f48e56570f96fe14a811fbef8c68e56`。审计文件含动作与失败分类，但不含完整逐 token 原文；无本地权重与原始输出时，其他机器不能逐字节重建原评测。

旧来源 V4.5.9 的 17/18（正常）、69/72（四条件）仅是已在 V3 使用过的数据诊断；本版新来源的 10/12、35/48 是单次来源留出结果。来源、题数及样本选择不同，**不能直接用两个通过率差值量化模型退化**。它提示先前诊断分数不足以代表新来源表现。因为只评测了一个 SFT 适配器，且没有在这些新来源上并排跑 GRPO、DPO 或多种子模型，本版**不能宣称 RL 优于 SFT，也不能把失分归因于 RL**。

## V4 最终状态

- **研究主线已打通**：工具环境与独立验证器、DeepSeek 监督轨迹、LoRA SFT、DPO、在线 GRPO、正常与故障条件评测、GPU 主评测及 NPU 量化试跑均有本机执行证据。V4.5.6 等预算三种子进度 GRPO 相对新 SFT 合计仅 +3/288，种子差异大；旧强种子课程扩展后回退，尚无稳定 RL 增益。新来源留出模型评测未覆盖 RL 变体。
- **工具边界已加强但不是安全沙箱**：子进程隔离、超时、部分写入丢弃、摘要与终态核验在小矩阵成立。Windows Job Object、硬内存限额及跨进程树取消仍未实现；不能把现状视为恶意代码执行隔离。
- **设备与系统为原型**：Intel NPU 路径能运行量化模型，但已记录的 15/24 低于 GPU BF16 的 21/24，不能替代主评测。C++ 小内核完成数值差分，小表 CLI 未带来收益；Go 只验证单机固定作业启动与摘要核验，没有持久队列或多机验收。
- **证据边界明确**：合成开发集反复使用；V4.5.8/9 三个真实来源也在 V3 出现过；本版仅提供两来源、12 题的一次性来源留出测试。模板、动作族、环境语义、参数绑定仍沿用开发阶段。此仓库适合作为可复核研究原型，不应宣称生产就绪或普遍泛化。

## V5 接续顺序与验收门槛

1. **先修训练信号，再谈 RL 收益**：在训练来源构造“错用日期规范化、失败后跳步、完成后多做一步”等可验证困难负例和恢复轨迹；保留旧任务比例及强种子基线，冻结预算和至少三种子配置。仅以全新来源/新任务模板上的配对结果判断是否推广 GRPO，不能反复调本版 12 题。
2. **补一个真正独立的评测层**：另取有许可的新来源，同时留出提示模板和至少部分工具组合；评测标签与训练作业隔离，先登记问题、指标、模型和停止规则再评测。保留 V4.5.10 作为已消耗的诊断来源，不再用它作 V5 最终盲测。
3. **系统 alpha**：按[V5 三语言规划](V4_5_7_V5_ARCHITECTURE_PLAN.md)先完成完整 SFT/GRPO 性能剖析。C++ 只在差分全通过、完整任务速度达到预设门槛后接入；Go 先实现单机持久队列、资源独占、租约/fencing、进程树取消和原子结果登记，通过失联/重启测试后再做第二台主机。GPU 与 NPU 分别记录精度、吞吐和能耗，不合并成同一策略分数。

## 本机复核

本机验证：Python `unittest discover` **84/84** 通过；Go `go test ./...` 通过；既有 C++ 原生测试程序通过；`research.benchmark` 通过；历史 V2 数据保护路径无差异。新来源协议的离线完整性测试为 `tests.test_v4_final_holdout`。若本机仍有相同模型文件，可用下列命令重新产生新的、不会覆盖旧结果的评测输出；评测器也会拒绝与 manifest 不符的模型或适配器权重：

```powershell
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_real_fault_audit --protocol tasks/v4/final_holdout_v1 --out work/v4_5_10_expert_repeat.json
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_llm_eval --protocol tasks/v4/final_holdout_v1 --model work/modelscope_deepseek_r1_1p5b --adapter work/v4_llm_composition_sft100_seed20260921/adapter --fault-modes none,transient_read,timeout,partial_write --out work/v4_5_10_model_repeat.json
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_real_model_audit --protocol tasks/v4/final_holdout_v1 --evaluation work/v4_5_10_model_repeat.json --out work/v4_5_10_model_audit_repeat.json
```
