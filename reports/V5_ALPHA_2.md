# V5.0.0-alpha.2：原生内核与持久实验队列

日期：2026-09-28。基于 `v5` 分支 alpha.1，目标是把已测得的 CPU 数值热点接入真实工具路径，同时将 Go 单机运行器扩展为可恢复的实验协调器。此版不修改 DeepSeek 权重、训练数据或 RL 策略，也不把系统加速解释为模型精度提升。

## C++ 接入与验收

`rolling_mean` 的 Python 循环是大表负载的 CPU 热点。现有 C++17 实现通过 `rolling_mean_c.cpp` 导出 C ABI，`agent/native_rolling.py` 使用 `ctypes` 调用；`agent/tools.py` 仅在 `V5_ROLLING_BACKEND=native` 时选择此后端，并要求 `V5_ROLLING_LIB` 指向已构建的库。缺库或非法数值会明确报错，不会悄悄退回 Python。默认仍为 Python。

本机 Windows 11、同一 Python 3.12 环境、同一 C++ DLL 上，对长度 0、短于窗口、窗口 1、常规序列、1000 项随机序列及 NaN/Inf 拒绝做逐项差分；公开真实 CSV 的完整 `SequenceEnv` episode 在两后端均通过。性能探针使用固定生成数据，不属于模型训练或盲测任务；每项串行运行三次，表内是中位数。原始机器可读结果及输入 SHA-256 见 [计时 JSON](v5_alpha2_native_benchmark.json)。

| 固定负载 | Python | 原生 | 加速比 |
| --- | ---: | ---: | ---: |
| 10 万数值，含 Python/FFI 边界 | 0.627 s | 0.0138 s | 45.35× |
| 100 万数值，含 Python/FFI 边界 | 6.322 s | 0.173 s | 36.46× |
| 10 万行完整 CSV 工具调用 | 0.820 s | 0.157 s | 5.23× |
| 10 万行进程内、含状态验证的 episode | 1.809 s | 1.208 s | 1.50× |
| 1 万行隔离进程、含状态验证的 episode | 0.570 s | 0.424 s | 1.34× |

最大逐项绝对差在 100 万项时为 `3.67e-11`；按 `rel_tol=1e-10, abs_tol=1e-10` 全部通过。1 千项的原生工具调用也快于 Python（0.00198 对 0.0112 秒），没有触发既定的小表回退门槛。大表完整 episode 超过既定 10% 提速门槛；这些结果仅在此机器和生成负载成立。隔离工具的回复上限仍为 2 MB，10 万行原生回复超过上限，故隔离 episode 只测 1 万行，没有放宽安全上限。alpha.1 的 48 题 LLM 评测主要耗时是模型生成，表规模小，不能由上表推导其端到端收益；默认后端保持 Python。

复现：在项目根目录运行 `cmake -S native -B build/native -DCMAKE_BUILD_TYPE=Release`、`cmake --build build/native --config Release`，将 `V5_ROLLING_LIB` 指向生成的 `rolling_mean_ffi` 共享库，再运行 `python -m unittest tests.test_v5_native_rolling -v` 与 `python -m research.v5_native_benchmark --out work/v5_native_recheck.json --repeats 3`。CI 在 Linux 编译共享库并运行原生集成测试。

## Go 队列语义与实测

`orchestrator/queue` 持久化任务快照；提交由 `submission_key` 与规范化任务配置去重，冲突请求被拒绝。协调器以操作系统文件锁保证同一状态只有一个写者，异常退出后锁自动释放。状态更新写到同目录临时文件、同步后原子替换。GPU/NPU 按 `device_id` 独占；当前 CPU 作为一个资源槽。工作进程周期性获取租约、启动既有白名单 `localrunner`、发送心跳，成功后以结果清单 SHA-256 提交。重复提交同一摘要幂等，不同摘要不能覆盖。

取消中的任务仍占设备，直到工作进程结束并确认停止；Windows 使用 Job Object 的 `KILL_ON_JOB_CLOSE` 终止运行器及其子进程，其他平台使用进程组。租约过期后标记 `lost` 并隔离设备；只有操作员**确认进程已停止**后，`/recover` 才允许重排，新的尝试得到不同令牌，旧令牌的迟到结果被拒绝。协调器只接受数值回环地址，不提供远程认证，因此 alpha.2 是**单机协调器**，不是已可安全部署的多机控制平面。NPU 评测复用既有 OpenVINO 入口；GPU 与 NPU 资源各有独立工作进程。

本机验收：真实 1 题 GPU DeepSeek 作业由队列启动，attempt 1 成功，评测结果 1/1，队列登记的结果清单哈希为 `6fc2596d…edec7`，与文件一致。真实 1 题 Intel NPU OpenVINO 作业同样由队列启动，attempt 1 成功、结果 1/1，清单哈希为 `98d75429…91357`；其运行器墙钟为 83.29 秒，包含模型编译，不能直接与 GPU 任务比较。运行中取消测试里，最初的 Windows 普通进程树终止留下 Python 子进程；切换 Job Object 后重测，任务为 `cancelled`，按命令行查询没有残留该评测的 Python 进程。另用短租约模拟失联：任务进入 `lost` 时同设备第二任务无法获取；强制结束并重启协调器后状态仍是 `lost`；确认停止后重排为第 2 次尝试，旧令牌提交返回 400。成功结果的相同摘要重复提交保持 `succeeded`。Go 单元测试覆盖这些状态转换和 HTTP 路由。

启动示例（PowerShell，从项目根目录、已安装 Go 且本机模型存在）：

```powershell
Push-Location orchestrator
go build -o ../work/v5_coordinator.exe ./cmd/coordinator
go build -o ../work/v5_worker.exe ./cmd/worker
go build -o ../work/v5_localrunner.exe ./cmd/localrunner
Pop-Location
./work/v5_coordinator.exe -state work/v5_queue/state.json -listen 127.0.0.1:8765
```

另一个终端提交并启动 GPU worker：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/jobs -Method Post -ContentType application/json -InFile orchestrator/examples/v5_queue_gpu_small.json
$repo = (Resolve-Path .).Path
$pythonExe = (Resolve-Path work/.venv-v4-llm/Scripts/python.exe).Path
$runnerExe = (Resolve-Path work/v5_localrunner.exe).Path
./work/v5_worker.exe -server http://127.0.0.1:8765 -resource gpu -device-id gpu0 -python $pythonExe -repo $repo -runner $runnerExe -output-root "$repo/work/v5_queue/runs"
```

NPU 使用 [NPU 示例](../orchestrator/examples/v5_queue_npu_small.json)并把资源、设备及 Python 环境改为 `npu`、`intel0` 和已安装 OpenVINO GenAI 的环境。`GET /jobs` 可查看状态；`POST /jobs/{id}/cancel` 请求取消。仅在确认失联进程停止后，向 `POST /jobs/{id}/recover` 提交 `{"confirmed_stopped":true}`。本机模型路径仅是示例，使用前应改为实际安装位置。

## 验证与边界

本机验证：原生差分/真实 episode 2 项通过；默认 Python 测试套件 88 项通过（缺少显式库变量时跳过其中 2 项原生测试）；Go `test ./...` 和 `vet ./...` 通过，Linux 目标交叉编译通过；C++ 原有测试可执行程序通过；`research.benchmark` 通过。Go `test -race` 在当前便携 Go 工具链中因未启用 cgo 而未运行，CI 的 Linux 测试也只运行普通 `go test`。尚未测多机网络故障和长期运行的资源占用。

当前队列是单协调器、单机磁盘状态；没有远程认证、跨机设备探测、网络分区共识、产物上传或真正的分布式吞吐验收。持久化保留任务与最终哈希，但运行产物仍由本机目录管理；失联后的清理确认是人为操作。Windows Job Object 在启动后立即绑定子进程，仍应继续验证启动到绑定间的极短窗口。队列资源与清单尚未加入 GPU/NPU 显存预算或模型驻留调度。

后续 alpha 应先对全新任务模板和来源做冻结评测，专门训练 V4.5.10 的类别工具误选、故障后跳过重试和多余动作，再比较 RL 与 SFT 的配对结果。系统侧可加入有认证的远程工作节点、内容寻址产物仓库、可审计的失联清理协议及多机故障注入。C++ 后端只有在真实目标任务中复测端到端收益且不降低正确性时，才考虑调整默认策略。
