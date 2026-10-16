# 0.5.0-dev：解释边界与 actor/origin 分离

2026-10-16。按版本规则跳过 0.4.*。本版只新增离线解释注释、可逆公开视图与内部结论清单；没有新的模型响应、权重或实验轨迹。旧代码、源观察、响应和主分数均冻结。

## 两个参照对象，不进行择优重评分

旧主参照始终为最后一个 receipt_lookup 指向的 publication。事后注释另计算最后一次已确认 publish 的事实，用来检查 final receipt 的另一种合理理解；不能将两种参照中得分较高者作为新主分数。

contextual 的另一理解仅标记 plausible_ambiguous_reference_not_independently_adjudicated，仍需独立裁决。explicit 明确指向最后 lookup，因此另一参照标记不适用，不能靠切换参照把它修成正确。旧 0/12、6/12 主分数原样保留。

另检查响应自报的 event_id 是否真实为 publish、是否与自报 request_id 匹配，再按该事件位置与旧边界核对 role。stage 或未绑定的事件不是合法 publication，角色标为不可评分，不从分母中偷偷删去。该注释没有证明模型内部思考或真实动作作者。

## 版本化中性 actor 视图

`responsibility-v2-neutral-actor` 是独立适配视图，不替换旧引擎：

| 旧字段/标签 | 新视图 |
| --- | --- |
| historical_agent_action | pre_handoff_actor |
| current_model_action | active_actor |
| current_model_start_history_index | actor_handoff_history_index |

environment_setup 不变。actor 只表示交接边界下的责任范围；生成来源另记为 scripted_fixture 或 unknown。model_api_tool_action 保留为未来来源类型，本适配器没有能确认它的正例证据。收到 API 事实回答不等于历史工具动作由模型生成。

origin 仅在观察与已固定程序执行源的观察哈希完全一致时识别为 scripted_fixture。自行写“模型生成”或保留旧 current_model_action 名称不能得到模型来源标记；不匹配的观察为 unknown。来源依据是本项目冻结程序记录的一致性，不是外部历史真实性或供应商认证。

新视图对 72 条既有读取对照执行 encode/decode：工具 history 不变，原样往返，当前正确性、已确认事件集合、stop 许可不变；原私有真值只记录原 SHA，不重归责物理效果。公开可能世界仍通过旧冻结规则计算后翻译词汇，未声称创造新推理算法。generation_contract/context 与语义版本严格检查，拒绝伪造来源、混用版本或键冲突。

## 科学结论和预算

validity_v39_claims.json 分别记录接口指代、目标/角色分离、程序环境、生成来源、RL/恢复机制五项结论的证据与限制。它是内部证据决策，不能代表独立科学接受或查新通过。没有新文献创新性确认。

本版 **NO_GO_LIVE，批准/实际新增 API 0**。中性词汇迁移不等于实验干预已获准；如果未来比较旧/新词汇，字段和说明同时变化，只能先作为接口有效性研究，不能直接当作单一机制或 RL 增益。新实跑需要能区分竞争解释的新问题、连贯对照、预先计划和预算，不能复用此前 GO。

统一验收会重放旧冻结协议（包含临时 CSV/SQLite 的程序重建）；这不是新增实验或模型工具行为。新增独立复审仍 pending，科学 HOLD。37 个复审组是 12 对旧响应注释、24 组三视图迁移和一份内部结论清单，不是 37 个独立任务。
