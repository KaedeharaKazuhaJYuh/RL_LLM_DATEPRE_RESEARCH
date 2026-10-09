# FaultDA-Bench：开发版本 0.2.05-dev

本轮完成[契约说明诊断与跨来源迭代](reports/CLARITY_V2_RELEASE.md)：三个历史来源各覆盖分组和版本分析，共 24 题、2,304 次离线执行。强组合基线在可观察、检查预算 4 时完成 96/96；仍未证实额外耦合失败机制。

DeepSeek 同题配对实跑 24 次：原说明和明确说明均完成 4/12，最终产物正确数分别为 12/12、10/12。明确了字段映射，但没有获得效果提升；旧结果完整保留。[实施协议](docs/CLARITY_V2_PROTOCOL.md)与[待人工审阅表](reports/CROSS_SOURCE_REVIEW.md)记录范围及未完成条件。来源交叉不等于全新来源泛化，第二模型家族仍待接入。

本轮复核（不调用 API）：

```powershell
python -m unittest tests.test_faultda_clarity -v
python -m faultda_bench.clarity.verify faultda_bench/reports/cross_source_v2_results.json --replay
python -m faultda_bench.clarity.verify faultda_bench/reports/clarity_v2_comparison.json --replay
```

重新运行请使用新输出路径；已有证据不能覆盖。`clarity.compare` 会调用已配置的 DeepSeek API，单次实验最多 192 个付费请求。

本目录位于独立 `faultda-bench` 分支，继承 V5.0.15-beta.2 稳定代码。以下保留[第一个开发版本 0.2.0-dev](reports/SEMANTIC_V1_RELEASE.md)的使用方法和结果：12 个历史公开数据派生任务、提交歧义与语义扰动的联合实验、CAS 产物修复、独立验证、六个程序基线及 DeepSeek 接入。它不是六来源 alpha 或最终确认基准。

离线完成 5,184 次相关条件执行；在检查预算 4 的可观察条件中，“通用恢复＋静态语义校验”完成 48/48，当前没有证据支持额外的联合失败机制。DeepSeek 小规模实跑完成 4/12；其余 8 次终态正确但选择升级。没有训练或 RL 提升结论，详见[结果与限制](reports/SEMANTIC_V1_RELEASE.md)。

[实施协议](docs/SEMANTIC_V1_PROTOCOL.md)定义状态、动作、证据预算和评分。Agent 只通过结构化工具 API 获取公开观察；这不是不可信代码的 OS 安全沙箱。新颖性仍按[研究协议 v2](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V2.md)和[查新复核](docs/OVERLAP_AUDIT_2026_10_09.md)检验。

运行：在完整仓库根目录使用已安装项目依赖的 Python。

```powershell
python -m unittest tests.test_faultda_semantic -v
python -m faultda_bench.semantic.verify_results
# 完整环境重放与评分复核，不调用 API：
python -m faultda_bench.semantic.verify_results --replay
# 以下会重新生成离线开发结果，不调用 API：
python -m faultda_bench.semantic.run --output work/semantic_rerun.json
# 可选：已配置 DEEPSEEK_API_KEY 时进行付费接入验证，最多 96 请求：
python -m faultda_bench.semantic.deepseek --output work/semantic_deepseek_rerun.json
```

旧 P0 `0.1.0-p0` 的[报告](reports/P0_START.md)、[84 次审计](reports/p0_probe.json)和[实施协议](docs/P0_IMPLEMENTATION_PROTOCOL.md)保持原样，可继续运行 `python -m faultda_bench.probe`。旧指标与新版本不混合汇总。[原始研究协议 v1](../reports/FAULTDA_BENCH_RESEARCH_PROTOCOL_V1.md)保留。

旧首版 12 个任务仅来自三个历史来源，且来源与意图混杂；本轮对其中两类意图补做来源交叉，但仍须独立人工审阅和全新来源确认。历史注册表中的 106 个 source_id 也不是 106 个独立来源。
