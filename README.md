# RL + LLM Data Analysis Agent — V2

> V3 已加入未见提示模板、正交泛化切片、两步有序计划和澄清任务；`research/v3_runtime.py` 会逐步验证产物、更新输入状态并支持一次参数恢复。设计与首轮结果见 `reports/V3_BASELINE_DESIGN.md`。

> V3.1 进一步加入三份带许可和哈希记录的 UCI 真实数据、五类实际故障及训练后冻结的恢复分类器。方法、结果和解释边界见 `reports/V3_1_REAL_RECOVERY.md`。

> V3.2 将冻结测试扩大到三个真实数据源和 102 条故障记录，并加入测试阶段未见故障及低置信度升级机制。结果见 `reports/V3_2_HARDENED_RECOVERY.md`。

> V3.3 将训练、阈值校准、测试来源分离，并加入复合故障、部分写入、编码损坏、随机延迟与 Wilson 区间。结果见 `reports/V3_3_CALIBRATED_COMPOUND_RECOVERY.md`。

> V3.4 使用真实子进程实施硬超时和部分写入，并补充按数据来源bootstrap。结果见 `reports/V3_4_PROCESS_ISOLATION.md`。

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
