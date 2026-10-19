# 0.5.20-dev 聚焦复核指南

日期：2026-10-19。本包是完整证据子集，可独立解压运行；需要 Python 3.11+、NumPy 2.3.5，无需模型、GPU 或 API。

```sh
python -m unittest tests.test_faultda_review520_registration tests.test_faultda_review520_actor -v
python -m faultda_bench.review520.audit
python -m unittest discover -s tests -v
```

包内数量与全仓库分开计数，实际隔离验证在根 `BUNDLE_VALIDATION.json`；`REVIEW_MANIFEST.json` 绑定提交和文件摘要。保存自检时可添加 `--output work/my_result.json`，只能用新路径；不要覆盖冻结结果。

## 已登记与未登记

原 2026-10-18 Markdown 当时明确不登记最终裁决。2026-10-19 用户通过本对话明确转达审阅者同意正式登记，故新增 `reports/review520/consent_relay_2026_10_19.json` 与 `final_referent_registration.json`，保留所有 12 对意见及 actor 歧义。旧原件和旧 pending 接收记录不改，作为时间顺序保留。

转达记录是项目方逐字记录问题/用户回答，不是审阅者新签名或身份认证。正式登记仅覆盖原有 12 对指代裁决；四项设计 revise、新接口人审 pending、科学 HOLD、API 0 不受影响。无需重新索取该批意见或再询问是否愿意登记。

## 本轮只请审查两份材料

1. [问题 R 的逐项对照与路线决定](R_COMPARISON_0520.md)：是否正确区分已有覆盖、设置差异与尚未证明增量；若独立审阅仍不能指出非平凡增量，维持工程定位，不扩格。
2. [责任/来源接口契约](ACTOR_0520_PROTOCOL.md)：责任范围、真实动作来源、query/target 两类事件和重复请求歧义是否清楚，是否夹带策略答案。技术检查不替代这项人类有效性判断。

复查 `reports/review520/actor_views.json` 时，72 条都来自同一旧簇的脚本观察；无新模型调用/动作、物理执行或新来源。合成负例只存在于单元测试，不是独立科学样本。过去的模型响应不使用本接口重评分。

当前内部路线决定为暂停 R 机制主张、保留工程诊断 Benchmark；这不是已证伪所有 R 变体，也不是独立科学通过。没有已获准的未见任务设计或新 API 预算。只有具体设计审查通过，才讨论来源血缘、独立真值、健康对照、效应阈值与样本量计划。
