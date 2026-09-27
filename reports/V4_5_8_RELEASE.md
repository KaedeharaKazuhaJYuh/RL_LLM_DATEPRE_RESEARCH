# V4.5.8：公开真实 CSV 与隔离工具故障审计

日期：2026-09-27。此版为 V4 增加可复现的真实数据诊断与工具进程故障测试，不改变已有 V4.5.6 合成开发集成绩，也没有训练或改动模型权重。

## 冻结公开数据

`tasks/v4/real_csv_v1` 包含 3 个来源、每个 240 行的 CSV，共 18 道两步任务：每个来源各 3 种工具组合，每种有中文与英文同义改写。成对题目共享同一 CSV、参数与专家动作，只有表达语言变化。训练任务数为 0；全部是公开来源诊断题，`external_test=false`。这些来源在仓库 V3 阶段已经使用，因此**不是新来源的最终盲测**。

| 来源 | 原始作品与许可 | V4 选用数据 | SHA-256 |
| --- | --- | ---: | --- |
| Wine Quality | UCI，Cortez 等，DOI 10.24432/C56S3T，CC BY 4.0 | red wine 前 240 行 | `73e5c37d778b895723f846082ea3abbf76ff2abf49abfbe1335bc5fc10eac27e` |
| Abalone | UCI，Nash 等，DOI 10.24432/C55C7W，CC BY 4.0 | 前 240 行 | `357e7466e3966bd51bef9a586aa4565ed2041fe76855a93350a1e6b70f0e2053` |
| Wholesale customers | UCI，Cardoso，DOI 10.24432/C5030X，CC BY 4.0 | 前 240 行 | `7f3f4a4954a4a62704da0356014fde9cf1ed347ce89173018068e348e20a59de` |

原始下载 URL、档案摘要、源 CSV 摘要、所选列与任务摘要在 `manifest.json`。生成器先核对 V3 已冻结源表摘要，再复制到 V4 协议目录并核对列及行数；没有再次下载或随机改写原始数据。选用列不含姓名或直接身份标识；本版仅做列级检查，尚未做完整隐私审计。[Wine Quality 来源与许可](https://archive.ics.uci.edu/dataset/186/wine+quality)、[Abalone 来源与许可](https://archive.ics.uci.edu/dataset/1/abalone)、[Wholesale customers 来源与许可](https://archive.ics.uci.edu/dataset/292/wholesale+customers)。

## 故障与状态验收

可选 `isolated_tools` 路径将单次工具执行交给独立 Python 子进程。每条 episode 有独立目录，每次调用有独立 attempt 目录；父进程只在子进程正常退出、输入摘要不变、回复和产物大小受限、产物位于该 attempt 内、CSV 列/行/内容与摘要匹配，以及原有独立 oracle 验证通过后，才更新正式状态。超时与部分写入故障可重复注入；超时后尝试终止进程树，部分写入文件留在私有 attempt 目录供审计，不能被当作成功产物。

专家轨迹执行 18 题 × 正常、瞬时读取失败、超时、部分写入四条件，共 72 次，**72/72 通过**。每次故障后的首次调用失败时，正式 `current` 与输入摘要均保持不变；之后按相同专家计划重试。逐题记录见 `reports/v4_5_8_fault_matrix.json`。这验证的是专家计划及状态边界，不代表模型有同样的故障恢复率。

本阶段的子进程隔离是执行与文件状态隔离，**不是安全沙箱**。Windows 用 `taskkill /T /F`，POSIX 用进程组终止；尚未用 Windows Job Object 证明所有异常进程树都能清理，也未在 Windows 上实施硬内存限额。输出大小是在进程结束后核验，不是持续强制限制。这些限制需在实际多 worker 调度前处理。

## C++ 数值差分

使用官方 Zig 0.16.0 的便携式 Windows 工具链在本机编译 C++17 单元测试和独立 CLI；下载档案 SHA-256 与[官方索引](https://ziglang.org/download/index.json)一致。6 类差分输入全部通过 `abs_tol=rel_tol=1e-6`：3 个真实 CSV 数值列、1,000/100,000 行压力输入和大有限数边界。最大绝对误差在真实 CSV 上为约 `3.2e-11`。10 次重复中，240 行任务的独立 C++ CLI 中位数约 10–11 毫秒，Python 数值参考约 0.7–1.2 毫秒；100,000 行压力输入 CLI 约 0.45 秒、Python 约 0.73 秒。详细计时见 `reports/v4_5_8_native_differential.json`。

CLI 时间包含文本序列化、跨进程启动和解析；Python 参考计时只包含数值计算，**两者不是公平的完整工具性能比较**。现有真实任务规模下 C++ 原型没有可用的端到端收益证据，因此仍不接入 Python 工具，也不宣称加速。压力表不是泛化测试。

## 复现

已有固定协议可直接运行：

```powershell
work/.venv-v4-llm/Scripts/python.exe -m experiments.v4_real_fault_audit `
  --out work/v4_real_fault_repeat.json
work/.venv-v4-llm/Scripts/python.exe -m unittest discover -s tests -q
```

首次重新构建协议应选用**新目录**，以免覆盖冻结版本：

```powershell
work/.venv-v4-llm/Scripts/python.exe -c "from pathlib import Path; from research.v4_real_protocol import build; build(Path('work/new_protocol'))"
```

正式目录按设计拒绝覆盖。C++ 差分入口为 `experiments.v4_native_differential`，需先编译 `native/rolling_mean_cli.cpp`；仓库 CI 也会构建并运行 C++ 单元测试。

V4.5.9 将冻结现有 DeepSeek 适配器，在相同协议上分别评估干净执行与故障执行，并审计来源、语言和动作错误；研究结论与上述系统正确性分开报告。
