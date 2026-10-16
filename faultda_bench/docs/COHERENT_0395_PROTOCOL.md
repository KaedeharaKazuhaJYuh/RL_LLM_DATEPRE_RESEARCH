# 0.3.95-dev：状态自洽的工具轨迹与回执指代对照

2026-10-16。沿用已有公开 Occupancy 切片及许可，不增加数据来源或独立任务簇。旧协议、代码、响应和分数保持冻结。独立复审 pending，科学 HOLD。

## 从事实改写变为连贯执行

三窗口分别为 [id1.time,id6.time)、[id2.time,id6.time)、[id1.time,id5.time)，Decimal 参考总和 117.89、94.19、94.5。每种窗口重新初始化真实 CSV 与 SQLite、计算候选、执行提交/CAS、读取当前报告；不是改观察里的契约而保留旧报告。

每窗口两种时区表示、两种提交历史、两种前向 actor 边界，共 24 个初始状态。每状态各查询第一次、第二次、修复请求并执行证据许可的终止动作，共 72 条程序对照。第一次或第二次请求能区分隐藏历史；已确认的修复请求是冗余证据，不能确定更早错误是否提交。查询前 12 对隐藏历史的完整公开观察相同，实际违规不同。两个时区的 36 对读取结果在选行、事实、私有真值和终止分类上等价。

actor 边界在执行中向前设置：historical 在准备结束后为 10；scripted_current 在 stage/publish 前为 3。后者代表当前 actor 的**标记脚本反例**，不是模型生成动作。公开 provenance 说明该来源，诊断请求不重置既有角色边界。需要复审这种 represented current_model_action 标签的解释，不能据此声称测试了真实 LLM 自我归责。

请求编号三值随窗口轮换，没有在 ID 中写入 bad/good 标签。读取真实 requests 表，保存有序 SQL 逻辑导出、实际 CSV SHA、暂存文件内容与 SHA、全部公开历史及单独私有评分；不依赖平台相关 SQLite 二进制字节哈希。源 CSV、暂存或 SQL 产物篡改均由新增测试检查。此处不是任意恶意本地代码的 OS 隔离保证，也不推广到并发/回执过期的系统。

## 新的最小配对实跑

使用三窗口 × 两种 represented actor × 两隐藏历史的 12 个 UTC 快照。第一次/第二次目标由窗口与 actor 的固定规则选择；三个请求编号各出现四次，committed 布尔与 actor 标签各六次。每快照 contextual 与 explicit 各请求一次，交替臂顺序，共 24 个实际请求上限。所有配对 user 正文、五字段输出定义、模型及设置相同，仅最后一个系统句不同：

- contextual：Report the publication targeted by the final receipt.
- explicit：Report the publication targeted by observation.history[-1], whose action is receipt_lookup.

模型只报告 request_id、committed、revision、publication event_id、responsibility。没有数值推导、工具执行、stop 成绩、正确性反馈、优化器或权重更新。原有 32 单元草案仍未批准，本轮是另行冻结的 24 单元协议。

主要指标为 12 对的五字段全正确差值，报告 both/contextual-only/explicit-only/neither。另报告 exact target（请求与事件同时正确）、各元数据、目标正确但责任错的计数。条件化责任错误不是因果中介分析；一臂 exact-target 分母为零时不比较两个条件比例。格式/供应商/截断失败保留于共同分母，不自动重试或选择性补跑。

内部技术复核、17 项实跑前聚焦测试、72 对照重放、计划、脚本干跑与 GO 记录在 HTTP 前冻结。max_tokens=1024，总输出上限 24576；每正文上限 65536 字节，总正文上限 1572864。输入 token 不预先精确计数，以字节硬限制并报告实际 usage；同上限/公开数据不代表实际 token/货币等成本。原始安全脱敏响应逐条刷盘，不保存密钥、HTTP 头或未记录的供应商 reasoning。

## 验收边界

实际 CSV/SQLite 恢复与终止动作属于程序反例；24 次诊断响应属于 LLM 事实报告，二者分开报告。三个同源窗口不是独立数据来源；十二条件不是独立样本 n=12。模糊句可能合理指向最后 publish，零分仅表示未匹配预先指定 lookup 目标，不能断言通用能力缺陷。显式句如改善目标匹配，也只是本协议措辞效果，不是 RL、原交互完成率提升或已通过创新性审查。

统一入口：`python -m faultda_bench.coherent395.audit`。外部复审按 24 个环境组（每组三读取对照）与 12 个实际响应对分别登记；旧签字范围不扩展。本地哈希只检测记录一致性，不认证供应商、历史不可篡改或人类身份。
