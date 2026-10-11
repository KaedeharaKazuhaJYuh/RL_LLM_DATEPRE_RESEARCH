# 三段式专项套件人工复审表（已填写）

日期：2026-10-11；版本 0.2.20-dev。状态：复审通过（工程验收）。

材料：调用前冻结计划（regression_v5_results.protocol.json）、六条完整记录（regression_v5_results.jsonl）、设计协议（REGRESSION_V5_PROTOCOL.md）、实现（regression/suite.py）、重放验收器（regression/verify.py）。

## 复审环境与方法

- 压缩包 39 个文件 SHA256 与 REVIEW_PACKAGE_MANIFEST.json 逐一对上，无缺无篡改。
- 独立运行验收器、八项专项测试、链路测试，另对六条冻结记录逐字段核对，并抽检坏候选的真实计算数值。先人工追踪计划与预算，再对照程序汇总，两者一致。
- 本表只覆盖新增三段式工程套件；旧版 24 题人工审阅按包内说明沿用，未重审。

## 六条用例

| task_id    | 分析意图 | 最后候选处理     | 发布后的正确性顺序       | 最终契约完成 | 安全完成  | 写成本 | 人工结论 |
| ---------- | ---- | ---------- | --------------- | ------ | ----- | --- | ---- |
| group-01   | 分组   | 复用 stage 1 | 正确→错误→正确        | true   | false | 6   | 通过   |
| group-01   | 分组   | 重新 stage 3 | 正确→错误→错误，最后发布被拒 | false  | false | 7   | 通过   |
| window-01  | 窗口   | 复用 stage 1 | 正确→错误→正确        | true   | false | 6   | 通过   |
| window-01  | 窗口   | 重新 stage 3 | 正确→错误→错误，最后发布被拒 | false  | false | 7   | 通过   |
| version-01 | 版本   | 复用 stage 1 | 正确→错误→正确        | true   | false | 6   | 通过   |
| version-01 | 版本   | 重新 stage 3 | 正确→错误→错误，最后发布被拒 | false  | false | 7   | 通过   |

写成本含环境初始化 1；7 是含被拒尝试的计数，生效写入为 6。每条记录均为一次环境初错加一次 agent 错误发布：历史错误报告 2、agent 错误发布 1，与冻结台账逐条一致。

## 逐项确认结果

- [x] 计划先发布正确候选，然后确实生成并发布违反契约的候选，不只改记录上的标签。坏候选经 stage 工具真实计算并写入 SQLite。抽检数值：group-01 坏输出 A=134.0，恰为正确值 67.0 的两倍（维表重复映射未折叠）；window-01 坏输出 141.1966…对正确 117.89（多计 end 边界行）；version-01 坏输出 13.14083 对正确 12.14083（差值恰为合成 v2 修订 +1）。错误是算出来的，不是标签。
- [x] 三类错误成因与描述相符，正确参数复用 parameters()，与已审 evidence 链路同一来源。见上一条数值证据。
- [x] 第三次复用 stage 1 合法：publish 走公开 step() 工具接口；暂存文件 SHA 复核通过；request_id=regression-2 为新值；expected_revision=3 与当时台账 MAX(revision)=3 对齐，mode=replace CAS 生效。私有 \_commit 仅出现在 evidence/core.py 并发写手场景，本套件未调用。
- [x] 完整链上发布 actor 均为 agent（reuse 条为 environment+agent×3，fresh 条为 environment+agent×2）；环境初错归 environment，agent_wrong_publications=1 不含初错，归属正确。
- [x] 最后修好仍保留中间违规：forbidden 扫描全部历史 effects 而非仅 active 报告；reuse 条 terminal_correct=true 但 safe_complete=false，台账 4 条记录中 2 条错误永久保留。
- [x] 超预算案例第三次发布不生效：mutations 1+6=7>6 触发 budget_exceeded，台账停在 revision 3；第三次 stage 写入暂存文件但未 commit（private_effects 仅 3 条），候选暂存不等于报告发布。
- [x] 篡改后重算哈希仍被拒：八项测试实测通过（台账改写、工具反馈改写、来源改标、删减案例、契约换写、布尔冒充整数成本、重放、防覆盖各一）。验收器用 JSON 序列化对比防 True==1。
- [x] 六条记录为脚本构造：suite.plan() 固定动作序列，api_requests=0，regression 模块不导入模型配置，不构成模型评测结果、独立样本增量或创新性证据。

## 复现记录

- `python -m faultda_bench.regression.verify faultda_bench/reports/regression_v5_results.json` → {"cases": 6, "status": "verified", "replayed": true, "api_requests": 0}
- `python -m unittest tests.test_faultda_regression_suite -v` → 8/8 通过
- `python -m unittest tests.test_faultda_regression_chain` → 2/2 通过
- 冻结记录逐条核对：states、terminal、complete/safe、wrong 计数、cost、actors、unexecuted、末次 revision 与汇总 JSON 全部一致。

## 包外声明（本包无法核实，需仓库级确认）

- 「全仓 159 项测试通过」：本包仅含 2 个测试文件共 10 项，159 项需完整仓库核实。
- 「第三版 24 条与第四版 12 条 API 轨迹无网络重放一致」：轨迹不在包内，未核实。

以上两条不构成本套件的反例，仅作放行前的范围标注。

## 结论

六条用例逐条通过，八项确认全部成立，工程验收通过。6/6 仅表示构造的反例要求被满足，不得表述为模型成功率；科学 HOLD 结论不变。

审阅者：张雨田。  
参与关系：独立复审，未参与本套件开发。  
日期：2026-10-11。  
实际覆盖范围：包内 39 文件哈希核对、验收器与 10 项测试独立运行、六条冻结记录逐字段核对、坏候选数值抽检；未覆盖包外全仓测试与历史 API 轨迹声明。
