# 0.5.15-dev 复核入口

本包可独立解压运行，不需要旧主包、模型权重、GPU 或 API。使用 Python 3.11+ 与 NumPy 2.3.5，从解压根目录执行；不要用本机源码目录代替包内模块。

```sh
python -m unittest tests.test_faultda_review515_intake tests.test_faultda_review515_lineage tests.test_faultda_review515_panel -v
python -m faultda_bench.review515.audit
python -m unittest discover -s tests -v
```

第二条核对历史冻结与本轮接收/血缘；第三条仅运行本包所带测试，不等于完整仓库的继承 V5 覆盖。最终包的 `BUNDLE_VALIDATION.json` 记录隔离运行的实际数量，`REVIEW_MANIFEST.json` 记录所审提交与包内摘要。原输出不得覆盖；若要保存验收结果，给入口另加 `--output work/my_review.json` 并使用不存在的路径。

本轮已收到的原件位于 `faultda_bench/reports/review515/HUMAN_REVIEW_2026_10_18_ZHANG.md`。`intake.json` 是项目方转录，保存原文对最终裁决的限制，不是新签字；`qualification.json` 保存来源追溯及事实字段重算；`go_no_go.json` 绑定修订协议并维持 HOLD / NO_GO_LIVE。

请先核对[修订协议](REVIEW_0515_PROTOCOL.md)的意见处理表：

1. 指代意见与最终裁决分开登记；角色错误的措辞因果解释仅保留为候选。
2. 旧 manifest 保留历史标签，既有 seen/development 注册与本版可执行拦截共同控制未来资格；不能反推早期训练泄漏。
3. 新接口/责任规则须独立事前判定，所有臂共用资格与分母；不能看见错误后排除失败。新代码仅验证声明，不认证独立性或产生能力分数。
4. W4 因廉价绕过停止主实验，H* 未被统计证伪。待审 R 只是受限诊断问题，非已认可机制或增量。

原 12 对材料仍在 `reports/review510/review_packet.json`，空白返回模板原样保留。原审阅者若愿意登记最终裁决，请另外明确该意图及所审范围；不重复索取已返回四项意见，也不由项目代签。

新 0.5.15 修订尚未独立科学审阅。完整字段、测试通过、本地哈希和隔离包复现都不授权模型/API，不认证供应商、历史实验或审阅者身份。当前新增 API 授权和调用均为 0。
