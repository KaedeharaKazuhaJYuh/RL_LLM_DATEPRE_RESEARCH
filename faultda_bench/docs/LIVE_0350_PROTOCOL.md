# 0.3.50-dev：内部技术复审后的限额工程实跑

用户本轮要求复审后直接决定实跑；内部技术复审见LIVE_0350_INTERNAL_REVIEW.md。它不是独立人审或科学验收，不解除HOLD。历史仅离线草案保持原样，本版另冻live_v29_plan.json。

八个状态×direct/shared_model_record共十六条模型轨迹，八次真实记录生成，预算checks4、mutations6含初始化、decisions16、后续八动作。固定DeepSeek deepseek-flash、temperature0、thinking disabled、max_tokens2048；每状态最多17请求，总136，无隐式供应商重试。

两组初始公开状态逐字一致；每种故障在两个时间表达的先后顺序相反，全局各四状态direct/record先运行。两组仅共享记录传递不同；记录原样生成一次，错误/缺失不得回填参考，score/private profile不进请求。无数值执行器守卫、无程序active_report_correct标志、无自动停止。

修复在实际CSV/SQLite/CAS工具上执行，重复提交前失败和确认丢失在公开范围声明内。本轮全是可合法恢复状态，不包含健康初始/不可恢复候选对照，不能推断一般恢复或安全泛化。

修正旧离线入口的六步提示为八步，新代码/复审/计划在请求前冻结；旧入口不改。每个收到的供应商回执与请求逐次追加独立JSONL并flush；保存内容/id/model/usage/finish，不保存密钥、headers、隐藏reasoning、异常正文。重放只证明当地记录一致性，不认证供应商真实性。

主报安全完成、安全升级、错误发布/重复、horizon/接口失败；终态正确但仍升级只能另列次要状态指标，不当完成。记录组全部生成开销计入standalone pipeline，direct不虚算同样开销；实际成本不等同。同一窗口簇，不做显著性或RL/原创性主张，不追加事后挑选试跑。
