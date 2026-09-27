# V4.5.9：公开真实 CSV 的冻结模型评测与故障归因

日期：2026-09-27。评测使用 V4.5.8 冻结的 3 个 UCI 来源、18 道中英改写两步题，不训练或修改 DeepSeek 权重。基座为本地 DeepSeek-R1-Distill-Qwen-1.5B，适配器为 V4.5.5 的 SFT100 seed 20260921；贪心生成、BF16 CUDA，参数仍由任务固定绑定。模型与适配器权重 SHA-256 分别为 `58858233513d76b8703e72eed6ce16807b523328188e13329257fb9594462945`、`867a6c91b74a1c4a8b233de6511977e7876008c17ace9df8bab12a877696c9ff`。协议 manifest 摘要为 `5fae0f87d06cdcf53df1c2a6300a7f8326d99352e03307ee13fa872147cb94d2`。

## 冻结结果

| 条件 | 通过/总数 | 说明 |
| --- | ---: | --- |
| 正常 | 17/18 | 同一冻结模型的正式干净基线 |
| 瞬时读取失败 | 18/18 | 首次调用失败后允许重试 |
| 超时 | 17/18 | 首次工具子进程超时并终止 |
| 部分写入 | 17/18 | 首次调用留下私有不完整 CSV 并超时 |
| 合计 | 69/72 | 专家轨迹在相同矩阵为 72/72 |

鲍鱼来源为 21/24，葡萄酒和批发客户各为 24/24；中文改写 33/36，英文改写 36/36。三个失败均是鲍鱼来源中文类别任务 `be71e4e02e0554c2`：正常条件下模型在 `normalize_categories → count_categories` 后多选了 `deduplicate`；超时和部分写入条件下，首次 `normalize_categories` 失败后，它先选了 `count_categories`，随后才重试 `normalize_categories`，无法满足要求的动作顺序。瞬时读取失败条件的同题恰好通过，不能解释为该故障类型普遍更容易。

逐题动作、故障类型与切片结果见 `reports/v4_5_9_real_fault_audit.json`。原始模型输出和阶段计时保存在本机 Git 忽略的 `work/` 中；审计文件记录原始结果摘要，其他机器若没有相同模型和适配器文件，不能逐字节复现。此协议的真实 CSV 已在仓库 V3 阶段使用，且题目数量小、只包含 3 个来源和 3 种两步组合；结果只能作为公开真实数据诊断，不能称为来源隔离的最终盲测或跨数据集泛化证明。NPU 量化模型没有参与这次 BF16 冻结评测。

另用 Go 单机运行器清单 `orchestrator/examples/v4_real_eval.json` 启动相同的正常条件评测，输出 JSON 与手动运行逐字节一致，SHA-256 均为 `6ce7b53de20c257c1a7777d8c842d121c72378c1ecb288248af30b078db29215`。运行时正在编写本版，Go 清单如实标记 `git_dirty: true`；这验证单机启动路径一致，不能算多机调度证据。

## 隔离目录修正

首轮试跑曾得到 1/18；逐次检查发现评测器复用同一个临时目录，而隔离工具尝试使用相同的 `step_1` 名称，导致后续 episode 的工具调用发生目录冲突。该首轮结果**无效，已撤回**。V4.5.8 将每条 episode 的隔离目录改为独立创建，并增加同一评测 scratch 连续执行两条任务的回归测试。修正后重新运行正式干净基线和四条件矩阵，分别得到 17/18 与 69/72；不能把 1/18 → 17/18 称作模型能力提升。

## 动作去重诊断

为了检验重复调用是否是主要问题，另加了仅在诊断时启用的 `--no-repeat-success` 开关：根据**已成功**的动作历史缩小下一步可选集合，不读取 oracle。相同 18 题干净评测从原始 17/18 降为 14/18。三个原本通过的中文任务回退：硬性去重改变了模型的可选动作及提示上下文，使其选错动作或输出被排除的动作。该开关不设为默认，也不作为训练改进。对照逐题记录见 `reports/v4_5_9_real_guarded_audit.json`。

## 复现与后续

本机已有权重时，以下命令生成新的原始评测文件；运行器拒绝覆盖旧文件：

```powershell
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_llm_eval `
  --protocol tasks/v4/real_csv_v1 `
  --model work/modelscope_deepseek_r1_1p5b `
  --adapter work/v4_llm_composition_sft100_seed20260921/adapter `
  --fault-modes none,transient_read,timeout,partial_write `
  --out work/v4_real_fault_repeat.json
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_real_model_audit `
  --evaluation work/v4_real_fault_repeat.json --out work/v4_real_fault_audit_repeat.json
```

V5 研究应针对“完成两步后何时 stop”和失败调用后的有序重试建立训练信号，再以来源完全未使用过的新公开数据预注册盲测。训练预算、随机种子和未见数据必须独立冻结；不能只在这 18 道题上调提示或使用 oracle 动作筛选后宣称改进。系统方面仍需硬资源限制与更强的进程树清理保证。
