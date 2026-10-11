# 复现与运行指南

所有命令从完整仓库根目录执行。基础环境需要 Python 3.11+；项目依赖中的 NumPy 版本由 `pyproject.toml` 固定。建议使用独立虚拟环境，执行：

```sh
python -m pip install -e .
```

模型权重和 GPU/NPU 运行时不是当前离线基准的必需项；仅安装 wheel 不包含全部任务和证据文件。

## 1. 离线核对现有证据

不访问模型 API，不需要 GPU：

```sh
python -m unittest tests.test_faultda_semantic tests.test_faultda_clarity -v
python -m faultda_bench.clarity.verify faultda_bench/reports/cross_source_v2_results.json
python -m faultda_bench.clarity.verify faultda_bench/reports/clarity_v2_comparison.json
```

上述核对哈希、试验覆盖和汇总。完整重建环境并逐动作比较工具响应及 oracle 判定：

```sh
python -m faultda_bench.clarity.verify faultda_bench/reports/cross_source_v2_results.json --replay
python -m faultda_bench.clarity.verify faultda_bench/reports/clarity_v2_comparison.json --replay
```

API 轨迹重放使用已记录动作，不会重新调用模型；它证明实现与记录一致，不证明重新采样能得到相同模型输出。

全仓库测试和版本元数据检查：

```sh
python -m unittest discover -s tests -v
python -m scripts.release_version --check
```

部分可选硬件/原生后端检查依赖本机安装，跳过情况应随本次结果记录。README 的 FaultDA 标题与继承的 V5 包版本分别管理，检查仍校验继承版本，不将基准开发编号写成模型版本。

## 2. 重新运行当前离线矩阵

```sh
python -m faultda_bench.clarity.offline --output work/cross_source_my_run.json
python -m faultda_bench.clarity.verify work/cross_source_my_run.json --replay
```

输出包含协议、汇总和压缩逐条记录。共有 24 个开发任务、2,304 次相关条件执行；按来源×意图查看，不能将执行次数当独立样本量。输出路径存在时程序拒绝覆盖，第二次运行请换新名称。

## 3. 可选 DeepSeek API 对照

使用环境变量 `DEEPSEEK_API_KEY` 或被忽略的 `.env.local` 配置凭据，`DEEPSEEK_MODEL` 可选。参考 [.env.example](../.env.example)，不要把真实密钥放入命令记录或提交。当前对照代码固定温度 0；不要把示例环境文件里的温度误认为实际实验参数。

```sh
python -m faultda_bench.clarity.compare --output work/clarity_my_run.json
python -m faultda_bench.clarity.verify work/clarity_my_run.json --replay
```

这一步会产生服务费用：24 episode，每条最多 8 请求，总上限 192，不自动重试。首次请求前保存模型、提示、顺序和代码哈希，结果中保留服务实际返回的模型标识。两臂说明长度不同，等请求预算不是等 token；旧成绩不能被新调用覆盖。

## 4. 第三开发版诊断

无需 API 即可重放本轮全部 96 条记录：

```sh
python -m unittest tests.test_faultda_evidence -v
python -m faultda_bench.evidence.verify faultda_bench/reports/evidence_v3_offline.json
python -m faultda_bench.evidence.verify faultda_bench/reports/evidence_v3_api.json
```

重新运行使用 `python -m faultda_bench.evidence.run --output work/evidence_new.json`；添加 `--api` 会进行付费 DeepSeek 调用，上限 24 次独立事实请求与 144 次动作请求。结果是带预设正确候选的条件诊断，不是自主端到端成功率。见[冻结协议](../faultda_bench/docs/EVIDENCE_V3_PROTOCOL.md)。

## 5. 第四开发版：语义与建议对照

```sh
python -m unittest tests.test_faultda_decision -v
python -m faultda_bench.decision.verify faultda_bench/reports/decision_v4_offline.json
python -m faultda_bench.decision.verify faultda_bench/reports/decision_v4_api.json
```

上述验证无 API 调用，默认实际重放全部 48 条轨迹。重新运行可用 `python -m faultda_bench.decision.run --output work/decision_new.json`；添加 `--api` 将调用付费 DeepSeek，最多 12 次独立语义问答及 72 次动作请求，不重试。输出路径必须不存在。

规则建议不是自动执行器，语义问答答案不传入动作上下文。初态已经完成提交并提供 inspect，不是自主完整解题。人工审阅仍待完成，见[本轮协议](../faultda_bench/docs/DECISION_V4_PROTOCOL.md)与[结果报告](../faultda_bench/reports/DECISION_V4_RELEASE.md)。

## 6. 第五开发版：冻结历史归因套件

```sh
python -m unittest tests.test_faultda_regression_suite -v
python -m faultda_bench.regression.verify faultda_bench/reports/regression_v5_results.json
```

完整六条路径默认实际重放；重新生成使用 `python -m faultda_bench.regression.suite --output work/regression_new.json`，输出路径必须不存在。无 API/GPU 需求。

六条是预定错误注入的工程构造，不是 LLM 评测或独立任务增量。三个最终修好但不安全，三个因预算拒绝而保持错误。[协议](../faultda_bench/docs/REGRESSION_V5_PROTOCOL.md) · [结果](../faultda_bench/reports/REGRESSION_V5_RELEASE.md) · [人工复审表](../faultda_bench/reports/REGRESSION_V5_REVIEW.md)。旧实验命令继续保留在上述各节。

## 7. 历史版本与模型实验

| 范围 | 入口与说明 |
| --- | --- |
| FaultDA 首版 | `python -m faultda_bench.semantic.verify_results --replay`；[首版报告](../faultda_bench/reports/SEMANTIC_V1_RELEASE.md) |
| P0 | `python -m unittest tests.test_faultda_p0 -v`；[P0 协议](../faultda_bench/docs/P0_IMPLEMENTATION_PROTOCOL.md) |
| V3 | [最终审计](../reports/V3_FINAL_AUDIT.md)，按报告的历史协议运行 |
| V4/V5 训练与评测 | [V4 收尾](../reports/V4_5_10_V4_CLOSURE.md)、[V5 beta.2](../reports/V5_0_15_BETA_2.md)，需要报告指定的本地权重和依赖 |
| C++ / Go | [V5 alpha.2](../reports/V5_ALPHA_2.md)，属于可选系统路径 |
| Intel NPU | [NPU 接入](../reports/V4_NPU_ENABLEMENT.md)，使用独立依赖环境，不替换 CUDA 训练环境 |

历史命令应输出到新的 `work/` 路径。部分旧 CLI 默认写入原始报告位置，直接运行前应查看其帮助和对应协议，避免覆盖冻结证据。新旧评分不混用，模型权重不随源码仓库分发。

## 统一证据验收（0.2.25-dev）

完整仓库根目录运行 `python -m faultda_bench.acceptance.audit`，不需要 API、GPU 或网络。默认核对历史大套件的文件和汇总，并重放第三至第五开发版轨迹；加 `--full-replay` 也重放早期大套件。`--output work/acceptance.json` 只创建新文件，不覆盖已有证据。请勿加 `-O`，历史验证器使用断言。科学 HOLD 与人工待审不会冒充通过，也不阻止工程核验返回成功。详细边界见[验收协议](../faultda_bench/docs/ACCEPTANCE_V6_PROTOCOL.md)。

专项复审登记 `0.2.30-dev` 更新默认清单为 65 份文件；新增六例状态为通过，科学 HOLD 不变。历史第六版清单保留待审状态，详见[第七版协议](../faultda_bench/docs/ACCEPTANCE_V7_PROTOCOL.md)。

`0.2.35-dev` 默认清单为 71 份冻结文件，统一入口另重建检查分配的 576 次运行。单独运行 `python -m faultda_bench.allocation.verify faultda_bench/reports/allocation_v8_results.json`；重新生成用 `python -m faultda_bench.allocation.suite --output work/new_allocation.json`，只接受新输出路径。本实验无模型调用，旧人工签字不覆盖新实验。

`0.2.50-dev` 统一入口核验 78 份冻结文件，另重建工具证据对照 144 次运行。单独运行 `python -m faultda_bench.surface.verify faultda_bench/reports/surface_v9_results.json`；重新生成用 `python -m faultda_bench.surface.suite --output work/new_surface.json`。新实验没有独立复审，暂存写成本计入结果，不表示总体等成本或模型提升。

`0.2.55-dev` 统一入口核验 86 份冻结文件，另重建计算工具缺陷对照 144 次运行。单独运行 `python -m faultda_bench.trust.verify faultda_bench/reports/trust_v10_results.json`；重新生成用 `python -m faultda_bench.trust.suite --output work/new_trust.json`。故障是真实计算结果加 1 的受控注入，不能把安全升级说成修复完成，旧人工签字不覆盖新实验。

`0.2.60-dev` 统一入口核验 94 份冻结文件，另重建模型诊断准备中的 36 条规则轨迹及公开提示哈希。运行 `python -m faultda_bench.pilot.verify faultda_bench/reports/pilot_v11_offline.json`；默认生成入口是离线，明确的 `--backend deepseek` 才使用已有本机凭据。实际九条件试跑命令及消耗、评分边界见[固定协议](../faultda_bench/docs/MODEL_PILOT_V11_PROTOCOL.md)。本轮没有真实 API 调用。

## 真实诊断接收：0.2.65-dev

已冻结真实结果，不需 API 或凭据即可运行 `python -m faultda_bench.pilot.verify faultda_bench/reports/pilot_v12_deepseek.json`。统一验收核对 97 份文件，并重放全部九条记录，含三条限额终止；接收版本 0.2.65-dev，实际执行协议仍为 0.2.60-dev。记录与消耗见[实际诊断报告](../faultda_bench/reports/MODEL_PILOT_V12_RELEASE.md)。上述 0.2.60-dev 的“没有真实调用”仅描述此前协议准备阶段。不得覆盖当前文件或将限额条件自动重试混入结果。

## 输出诊断：0.2.70-dev

离线运行 `python -m faultda_bench.formatdiag.verify faultda_bench/reports/format_v13_deepseek.json` 重建 24 个请求，统一入口核对 105 份冻结文件。原始响应正文没有保存，因此不能独立重放解析分类，也不认证供应商来源。四项网络替身测试与具体边界见[诊断协议](../faultda_bench/docs/FORMAT_V13_PROTOCOL.md)，实际成绩见[报告](../faultda_bench/reports/FORMAT_V13_RELEASE.md)。不要覆盖冻结计划或结果。

## 后续状态复核：0.2.75-dev

`python -m faultda_bench.followup.suite --verify faultda_bench/reports/followup_v14_deepseek.json` 重建六历史状态及十二请求，不联网。统一入口核验 112 份冻结文件。详见[接收报告](../faultda_bench/reports/FOLLOWUP_V14_RELEASE.md)。完整多步仅有设计冻结文件，尚无执行结果；不能用格式成功替代预算合法性或恢复成绩。

## 完整多步诊断：0.2.80-dev

`python -m faultda_bench.multistep.suite --verify faultda_bench/reports/multistep_v15_deepseek.json` 重放全部十八条工具反馈、效果与公开请求，不联网。统一核验 118 份冻结文件。真实 API 入口必须显式提供新 --protocol/--output 路径；单例 17 请求，全局最多 306，无重试，实际消耗见[报告](../faultda_bench/reports/MULTISTEP_V15_RELEASE.md)。旧设计文档仍保留当时“尚未运行”状态；本轮可执行协议及结果是后续证据。原响应未保存，分类不可独立重放；不以末尾升级覆盖先前错误发布。
