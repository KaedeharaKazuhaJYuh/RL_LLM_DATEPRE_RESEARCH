# V4.5.7 实施报告：计时与 Go 单机运行器

日期：2026-09-27（北京时间）。本轮把 [V5 三语言架构规划](V4_5_7_V5_ARCHITECTURE_PLAN.md)中的第一段做成可运行原型，不改变 V4.5.6 的训练结果。

## 已交付

- `research/stage_profile.py` 提供可选的分阶段墙钟计时，输出独立的 `v4-stage-profile-1` JSON。专家导出记录 CSV、工具、验证、观测和写入；冻结 LLM 评测另记录模型加载与生成。GPU 生成计时前后同步 CUDA，避免只测到异步提交。嵌套阶段不能直接相加。
- `orchestrator/cmd/localrunner` 是 Go 单机运行器。它只接受 `v4_export` 和 `v4_eval` 两种清单入口，以参数数组启动 Python，并为每次运行新建目录，保存配置、日志、计时和 `v4-local-result-1` 结果清单。结果清单记录 Git 提交及工作区是否修改、协议与可用的模型/适配器文件摘要、输出摘要、退出码和运行耗时。导出需有有效训练步骤和匹配的摘要；评测需为贪心评测且协议一致。运行失败时保留失败清单与日志。
- `.github/workflows/tests.yml` 增加独立 Go 测试任务；Python 原有验证保持不变。Go 单元测试覆盖清单入口限制和已存在目录不覆盖。

Go 运行器目前只管理**一个本机进程**。清单中的 `resource` 是作业类型约束，尚不是 GPU/CPU 的真正资源锁。它没有持久队列、租约、心跳、取消、重试或跨主机通信；不能称作分布式系统。

## 本机对照

本机使用现有 V4 组合协议、已保存的 DeepSeek 1.5B 与 SFT 适配器。两种入口都先手动运行，再由 Go 启动相同 Python 入口，运行产物保存在 Git 忽略的 `work/` 中。Go 1.27.1 官方 Windows 压缩包经官网 SHA-256 校验后放在本地 `work/go-portable/`，未加入仓库；模块仅使用标准库，`go.mod` 最低版本为 Go 1.22。

| 作业 | 手动与 Go 的结果核对 | 单次手动计时观察 |
| --- | --- | --- |
| 专家导出 | 384 条训练 episode、96 条开发 episode、1,728 条训练步骤；步骤文件 SHA-256 均为 `9470cf5cdbe088f7c1cc8aa0b5115ad4ebed15be990b26a0ee159484984073bf`，与此前协议基线一致 | 总计 10.97 秒；环境 step 7.45 秒，其中工具执行 4.24 秒；终态核验 2.09 秒；CSV 读取 0.73 秒 |
| 小样本 GPU 冻结评测 | 2 个任务 × 正常/故障，共 4 条执行，均通过；手动与 Go 的 JSON 逐字节相同，SHA-256 均为 `e21b2629dd7287fec57575bcc5759bb214ac6a1d846edabb9711ffb9d3d4f1b8` | 总计 17.53 秒；18 次生成 8.65 秒，模型加载 4.05 秒；环境 step 0.08 秒 |

后续 Go 复跑还记录模型权重 SHA-256 `58858233513d76b8703e72eed6ce16807b523328188e13329257fb9594462945` 和适配器权重 SHA-256 `867a6c91b74a1c4a8b233de6511977e7876008c17ace9df8bab12a877696c9ff`，结果 JSON 的摘要仍与手动运行一致。运行时工作区含本版未提交代码，清单如实标为 `git_dirty: true`；提交后重新运行可获得干净提交的来源记录。

这些计时是单次诊断数据，不是性能提升实验。专家导出里工具耗时值得进一步分析，但小样本 GPU 评测由模型加载与生成主导；不能据此决定马上重写工具，也不能拿两次作业墙钟差推断 Go 比手动更快。计时自身有开销，且 Windows 文件缓存、GPU 热态和模型初始化会影响数字。

## 复现入口

在仓库根目录，已有 Python 训练环境时可单独生成计时文件：

```powershell
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_llm_export `
  --protocol tasks/v4/llm_composition_v1 --out work/v4_5_7_manual_export `
  --profile-out work/v4_5_7_manual_export_profile.json
```

在 `orchestrator` 目录使用 Go 运行器；评测例子要求本地模型和适配器已存在。每次使用一个未存在的 `-run-dir`，避免覆盖旧证据。

```powershell
cd orchestrator
go test ./...
go run ./cmd/localrunner -manifest examples/v4_export.json `
  -python ..\work\.venv-v4-llm\Scripts\python.exe -repo .. `
  -run-dir ..\work\v4_5_7_go_export
go run ./cmd/localrunner -manifest examples/v4_eval_small.json `
  -python ..\work\.venv-v4-llm\Scripts\python.exe -repo .. `
  -run-dir ..\work\v4_5_7_go_eval
```

本机验证：Python 78 项测试、Go 单元测试均通过；导出与 GPU 小样本评测的手动/Go 产物核对通过。GitHub Actions 的 Go 任务将在代码手动推送后首次运行，目前不能称作线上 CI 已通过。

## 下一步门槛

1. 为一次固定 SFT、一次 GRPO 和完整冻结评测补齐分阶段计时及多次重复，区分生成、前反向、环境、验证、数据读取和写盘；固定种子、设备、协议与输入摘要。
2. 若工具处理在目标负载仍是主要成本，先做 Python/NumPy 对照，再选一项语义较简单的数值列工具制作 C++ 差分原型。要求完整流程收益达到规划门槛，不能只报告内核速度。
3. Go 下一阶段先补版本化清单校验、明确的资源独占和异常进程树清理，再做 SQLite 持久队列、租约与迟到结果保护。两台真实主机验证前不宣称多机调度完成。

系统吞吐与 RL 泛化分别验收。本次没有新增训练更新，也没有新的模型泛化成绩。

## 后续小型原生原型

V4.5.7 在上述单机验证后，另加入 `native/` 的 C++17 移动平均原型及 CMake 测试。这是独立代码，尚未绑定 Python，也不影响上述产物或计时。当前 Windows 主机未找到可用的 C++17 编译器；源码测试已纳入推送后的 GitHub Actions，尚未获得 CI 结果。浮点差分、完整流程性能与进程隔离等工作列入 [V4.5.8 计划](V4_5_8_PLAN.md)。
