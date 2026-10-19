# 复现与运行指南

当前 **0.5.25-dev**：`python -m faultda_bench.review525.audit`；重点验证 `python -m unittest tests.test_faultda_review525 -v`。公开解析及比较前置校验见[本轮协议](../faultda_bench/docs/PREFLIGHT_0525_PROTOCOL.md)。无新增API或研究准入。以下版本记录保留各自历史范围。

最新（2026-10-19）：**0.5.20-dev** 依据用户转达审阅者明确同意，正式登记原 12 对指代裁决，保留歧义与异议。完成 R 与具体前作设置对照；暂停当前机制路线，保留工程诊断 Benchmark。新增 actor/来源/回执双事件只读接口，旧 72 条均为脚本派生，不是模型成绩；新接口独立人审 pending，科学 HOLD，API 0。

0.5.20 历史入口：`python -m faultda_bench.review520.audit`；[本轮复核指南](../faultda_bench/docs/REVIEW_0520_GUIDE.md)。以下旧 pending 为当时状态，不取消已登记裁决。

最新（2026-10-18）：**0.5.15-dev** 接收张雨田 12 对指代意见和四项设计 revise；原文明确不登记最终裁决，该项仍 pending。落实既有已见来源约束，新增血缘/祖先准入拦截与共同分母结构检查；否决 W4 主实验设计，未统计证伪模型假设。无新模型、来源、训练或 API，科学 HOLD。

0.5.15 历史入口：`python -m faultda_bench.review515.audit`；[本轮指南](../faultda_bench/docs/REVIEW_0515_GUIDE.md)列明原件、旧版本与新准入边界。下方均为历史入口与当时测试范围。

最新（2026-10-18）：**0.5.10-dev** 完成 12 对指代裁决材料、4 项设计审阅问题、空白返回模板与范围校验；实现区分安全完成/合理升级/错误终止的指标资格核对。72 条旧程序对照只有一个历史簇，不是新模型结果。新独立裁决与设计审阅仍 pending，HOLD，新增 API 0。

0.5.10 历史验收：`python -m faultda_bench.review510.audit`。人工填写与包内核对见[本轮指南](../faultda_bench/docs/REVIEW_0510_GUIDE.md)。本版完整仓库 527 项，包内子集 318 项，CI 选择 300 项；旧入口保留原范围。
[本版报告](../faultda_bench/reports/REVIEW_0510_RELEASE.md)。

最新（2026-10-17）：**0.5.05-dev** 接收张雨田 37 组人工技术复审，合理备选指代保留、最终裁决未进行；完成两类证据/决策假设、相关工作与强规则对照、跨任务准入草案。新设计未独立验收；科学 HOLD，新增 API 0。

0.5.05 历史验收：`python -m faultda_bench.review505.audit`。复核包解压后按[独立包入口](../faultda_bench/docs/REVIEW_START_HERE_0505.md)运行，无需可编辑安装。旧包的 496 项为完整仓库口径，旧包自身为 287 项，旧 CI 列表为 269 项；不要跨范围比较数量。新包根 `BUNDLE_VALIDATION.json` 记录其实际测试数。
[本版报告](../faultda_bench/reports/REVIEW_0505_RELEASE.md)。

最新（2026-10-16）：**0.5.0-dev 已完成**。保留旧 0/12、6/12 主分数，另注释 contextual 的 last-publish 合理解释（12/12，不替换主分数）；72 条 actor/origin 视图可逆迁移。496 项测试通过，新增 API 0。研究主张收束为接口/工程有效性，新独立复审 pending，科学 HOLD。下一版 0.5.05-dev 先整理复审、查新及可证伪竞争解释。
[本版报告](../faultda_bench/reports/VALIDITY_0500_RELEASE.md) · [复审指南](../faultda_bench/reports/VALIDITY_0500_REVIEW_GUIDE.md)。

0.5.0 历史验收：`python -m faultda_bench.validity500.audit`；注释/迁移单独重放：`python -m faultda_bench.validity500.suite`；37 组复审范围：`python -m faultda_bench.validity500.review`。均无 API 请求。本版仅派生只读视图，不改旧引擎或旧响应；新语义版本不直接送入旧责任入口。以下入口保留各历史版本的冻结范围。

0.3.95 历史验收：`python -m faultda_bench.coherent395.audit`；实际响应重放：`python -m faultda_bench.coherent395.pilot --verify faultda_bench/reports/coherent_v38_deepseek.json`；36 组复审范围：`python -m faultda_bench.coherent395.review`。源环境重建会创建临时真实 CSV/SQLite，所有动作均标记为程序脚本。24 次实跑已完成，无需重复付费；新执行必须重新明确计划与预算，不复用本次 GO 作为无界调用许可。旧输出不可覆盖。

0.3.90 历史离线入口：`python -m faultda_bench.probes390.suite`；复审范围核对：`python -m faultda_bench.probes390.review`。模块只有离线冻结/重放，无 live 入口；32 单元为未批准草案。合成事实变化不用于恢复任务终止评分。以下旧诊断入口保留原冻结范围。

本版诊断重放（零 API）：`python -m faultda_bench.postreceipt385.suite --verify faultda_bench/reports/postreceipt_v36_deepseek.json`；四对复审范围核对：`python -m faultda_bench.postreceipt385.review`。新增实跑不可覆盖冻结文件；本版既有四次请求已经完成，不必再次调用。入口的旧计划固定为本轮协议，不作为无界实验运行器。

历史统一验收：`python -m faultda_bench.validity500.audit`；本版真实交互重放：`python -m faultda_bench.receipt380.suite --verify faultda_bench/reports/receipt_v35_deepseek.json`；旧复审注册表核对：`python -m faultda_bench.lineage375.review`。均为离线，不发 API 请求；旧入口保留其冻结范围。


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

## 发布归因：0.2.85-dev

`python -m faultda_bench.publication.audit --verify faultda_bench/reports/publication_v16_audit.json` 重建 17 个发布前公开状态，不联网。统一核验 124 份文件。守卫对同一前缀的判断不是守卫后的完整模型结果；三臂仅为设计冻结，尚无真实对照分数。详见[报告](../faultda_bench/reports/PUBLICATION_V16_RELEASE.md)。

## 三臂真实对照：0.2.90-dev

`python -m faultda_bench.intervention.suite --verify faultda_bench/reports/intervention_v17_deepseek.json` 重放 54 条公开请求、拟动作/执行动作、工具反馈与评分，不联网。统一入口核验 130 份文件。设计文件保留上一版快照，可执行 plan/protocol 与本轮结果单独保存。两个清单臂守卫零触发；不能将离线拒绝测试当真实拦截成绩，或把升级改成完成。限制和消耗见[报告](../faultda_bench/reports/INTERVENTION_V17_RELEASE.md)。

## 数值与停止诊断：0.2.95-dev

`python -m faultda_bench.stopping.suite --verify faultda_bench/reports/stopping_v18_deepseek.json` 重建六个已读取公开状态、48 次独立请求、判断分数及单步效果，不联网。统一核验 136 份冻结文件。判断答案不传给动作调用，不能用独立探针建立同一次推理的因果链；stage 后非终态不能自动当完整任务失败。设置与消耗见[报告](../faultda_bench/reports/STOPPING_V18_RELEASE.md)。

## 窗口边界与接续决策：0.3.0-dev

当前统一入口为 `python -m faultda_bench.release030.audit`，核对 175 份文件，保留历史 acceptance-v18 并追加三个新实验。`--output work/acceptance_030.json` 只创建新文件；`--full-replay` 另重放早期大套件。旧 `faultda_bench.acceptance.audit` 仍只代表 0.2.95-dev，不能单独验收本版本。

三个新实验可分别离线重放，不需要凭据或网络：

```sh
python -m scripts.verify_rowdiag_v19 faultda_bench/reports/rowdiag_v19_deepseek.json
python -m faultda_bench.rowdiag.isolated --verify faultda_bench/reports/rowdiag_v20_deepseek.json
python -m faultda_bench.rowdiag.boundary --verify faultda_bench/reports/boundary_v21_deepseek.json
python -m unittest tests.test_faultda_rowdiag tests.test_faultda_rowdiag_isolated tests.test_faultda_boundary tests.test_faultda_release030 -v
```

新实验保存响应正文，可重新解析与分类；不认证供应商真实性。原 v19 动态清单用显式兼容入口固定原依赖集，代码与协议不修改。实跑只能显式给定新 `--freeze`、`--protocol`、`--output` 路径；现有计划/结果禁止覆盖。本版本共 84 次真实请求，单任务簇诊断，不以重复次数扩大样本。设置、成本与限制见[收尾报告](../faultda_bench/reports/ROWDIAG_030_RELEASE.md)。

## 三因素说明与时间表达：0.3.05-dev

最新统一入口为 `python -m faultda_bench.semantics305.audit`，核对 191 份文件，保留 0.3.0-dev 清单/代码并重放本版八条公开规则、十六次数值探针和三十二条模型轨迹。可用 `--output work/acceptance_0305.json` 创建新结果；`--full-replay` 追加早期大规模轨迹。验收不联网、不需要凭据，api_requests=0 仅表示验收没有调用，不否定历史实跑。

```sh
python -m faultda_bench.semantics305.suite --verify faultda_bench/reports/semantics_v22_deepseek.json
python -m unittest tests.test_faultda_semantics305 tests.test_faultda_semantics305_acceptance -v
```

实跑计划上限 240 请求，实际 144；仅使用当前已配置的 DeepSeek 凭据。若另行重跑，必须先生成新的 `--freeze` 文件，再明确给出新 `--protocol`/`--output`，不得覆盖或混入当前结果。完整设置与解释边界见[协议](../faultda_bench/docs/SEMANTICS_0305_PROTOCOL.md)和[结果](../faultda_bench/reports/SEMANTICS_0305_RELEASE.md)。

原 `.github/workflows/tests.yml` 是旧冻结证据的一部分，保持字节不变；新的 `.github/workflows/faultda-current.yml` 核验当前版本。新工作流和导航文档不进入不可改写的历史清单，后续版本可更新；公开复审时以固定 Git 提交核对工作流，不能声称本地验证已经通过远端 CI。


## 公开一致性检查：0.3.10-dev

运行 `python -m faultda_bench.consistency310.suite` 复核八条旧响应和六个反例。最新统一入口 `python -m faultda_bench.consistency310.audit --output work/acceptance_0310.json`，保留全部旧证据并新增本版检查；不调用 API，不修订历史动作。详见 [收尾报告](../faultda_bench/reports/CONSISTENCY_0310_RELEASE.md)。


## 真实反馈与守卫：0.3.15-dev

当前统一入口：`python -m faultda_bench.feedback315.audit --output work/acceptance_0315.json`。独立重放：

```sh
python -m faultda_bench.feedback315.suite --verify faultda_bench/reports/feedback_v24_deepseek.json
python -m faultda_bench.feedback315.analysis
python -m unittest tests.test_faultda_feedback315 tests.test_faultda_feedback315_acceptance -v
```

验收不联网。历史真实请求共 130 次；计划上限 216。重新实跑必须先生成新的 `--freeze` 计划并指定独立 `--protocol`/`--output` 路径，旧结果禁止覆盖。checker 增加公开数据程序计算，guard 增加执行器拦截，不属于纯模型权限。原始响应及动作完整保存；本地时间不认证，来源真实性与独立复审未通过。见[协议](../faultda_bench/docs/FEEDBACK_0315_PROTOCOL.md)、[报告](../faultda_bench/reports/FEEDBACK_0315_RELEASE.md)。


## 共享记录与真实动作接续：0.3.20-dev

当前统一验收：`python -m faultda_bench.handoff320.audit --output work/acceptance_0320.json`，离线且不需要凭据。

```sh
python -m faultda_bench.handoff320.suite --verify faultda_bench/reports/handoff_v25_deepseek.json
python -m faultda_bench.handoff320.analysis
python -m unittest tests.test_faultda_handoff320 tests.test_faultda_handoff320_acceptance -v
```

历史记录源来自前版 none 组八条第一轮，未挑失败；本版新增 177 请求，上限 320。新实跑须先写独立 `--freeze` 计划，再指定新 `--protocol`/`--output` 路径，旧输出禁止覆盖。每次修订用当前实际状态，实际 JSON 进入后续独立动作请求，无守卫。timing 只校验有限非负，不认证历史性能。详见[协议](../faultda_bench/docs/HANDOFF_0320_PROTOCOL.md)、[报告](../faultda_bench/reports/HANDOFF_0320_RELEASE.md)。


## 可合法恢复状态：0.3.25-dev

当前统一入口：`python -m faultda_bench.recover325.audit --output work/acceptance_0325.json`。单独重放 `python -m faultda_bench.recover325.suite`，测试 `python -m unittest tests.test_faultda_recover325 tests.test_faultda_recover325_acceptance -v`。零 API；64条实际工具控制、九次旧发布的后验事实检查，不是新模型轨迹。结果禁止覆盖；旧材料保留，新的 design_only 草案未执行。参见[协议](../faultda_bench/docs/RECOVER_0325_PROTOCOL.md)、[报告](../faultda_bench/reports/RECOVER_0325_RELEASE.md)。


## 强策略资格核验：0.3.30-dev

当前入口 `python -m faultda_bench.qualify330.audit --output work/acceptance_0330.json`；单独 `python -m faultda_bench.qualify330.suite`，测试 `python -m unittest tests.test_faultda_qualify330 tests.test_faultda_qualify330_acceptance -v`。零API，72策略轨迹另两对歧义状态。新design_only草案未执行；旧草案不覆盖，独立复审pending。参见[协议](../faultda_bench/docs/QUALIFY_0330_PROTOCOL.md)、[报告](../faultda_bench/reports/QUALIFY_0330_RELEASE.md)。


## 离线可执行协议：0.3.35-dev

当前入口 `python -m faultda_bench.runtime335.audit --output work/acceptance_0335.json`。单独 `python -m faultda_bench.runtime335.suite --verify faultda_bench/reports/runtime_v28_dry.json`；演练须先写新--freeze计划，再指定新--dry-run/--output，旧输出不可覆盖。CLI无live/API入口，不创建供应商客户端；16条fixture轨迹不属于模型成绩。复审状态pending。见[协议](../faultda_bench/docs/RUNTIME_0335_PROTOCOL.md)、[报告](../faultda_bench/reports/RUNTIME_0335_RELEASE.md)。


## 技术复审后的工程实跑：0.3.50-dev

当前验收 `python -m faultda_bench.live350.audit --output work/acceptance_0350.json` 不联网。单独 `python -m faultda_bench.live350.suite --verify faultda_bench/reports/live_v29_deepseek.json` 和 `python -m faultda_bench.live350.analysis`。历史真实请求75、上限136。新实跑必须先freeze独立新计划，再给独立--protocol/--output；旧响应与JSONL不可覆盖。内部复审不解除科学HOLD。见[协议](../faultda_bench/docs/LIVE_0350_PROTOCOL.md)、[报告](../faultda_bench/reports/LIVE_0350_RELEASE.md)。
