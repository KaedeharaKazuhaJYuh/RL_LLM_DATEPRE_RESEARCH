# FaultDA-Bench：P0 开发研究

本目录是独立 `faultda-bench` 分支上的首阶段实现，继承 V5.0.15-beta.2 稳定代码。主规范为[用户提供的研究协议 v1](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V1.md)。当前实施协议 `0.1.0-p0`，尚未完成六来源 alpha.1 或正式 LLM 评测。

已实现真实 CSV 汇总报告的非幂等追加、SQLite 持久提交、相同超时观察下的状态对、付费且可失败的检查、不可确认时升级、执行层去重对照、独立 Decimal 验证和五项指标分母。Agent 只通过结构化 API 访问合法观察；这还不是不可信进程的安全沙箱。

[相关工作矩阵](docs/RELATED_WORK_MATRIX.md)发现 UndoBench/Verified Tool Calls 与原先故障恢复目标直接重叠，因此本次原型只作机制验证，不主张已确立新颖性。后续先验证数据语义、检查可用性和参数绑定方面是否存在具体增量。

运行：在完整仓库根目录使用已安装项目依赖的 Python。

```powershell
python -m unittest tests.test_faultda_p0 -v
python -m faultda_bench.history
python -m faultda_bench.probe
```

结果见 [P0 报告](reports/P0_START.md)和[逐 episode 审计](reports/p0_probe.json)。指标与故障语义见[具体实施协议](docs/P0_IMPLEMENTATION_PROTOCOL.md)。本次只有两份历史公开 CSV、一个报告意图和三种固定程序基线；没有 DeepSeek/API 分数，不能解释成 RL 提升。

历史注册表登记 106 个 source_id 字符串，全部 seen/development；这不是 106 个独立数据来源，别名、派生样本和原档案重复仍需人工审计。最终测试来源尚未选择或读取，后续另行一次性冻结。
