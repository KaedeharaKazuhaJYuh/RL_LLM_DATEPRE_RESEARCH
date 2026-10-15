# 0.3.70-dev 独立复审入口

新增独立人工/科学审阅 pending，HOLD 不变。内部复核与程序测试不能替代外部审阅。

1. 对照 contract.py 与任务 observation 检查责任边界：environment_setup、historical_agent_action、current_model_action。初始错误不归责 Agent，但修复义务保留。
2. 从实际原始 CSV 行及半开窗口计算期望值；核对每个反例的预声明标签、公共证据评分和私有实际账本。尤其比较 timeout_wrong_before/after 与 resolved_wrong_before/after。
3. 核查 confirmed_violation / unresolved_risk / unknown 不混用；同 event_id 状态更新不重复计数，append 重复副作用修复后仍存在，dedup 无第二次实际提交。
4. 核查六组公共观察完全相同但私有实际不同；公开函数只接受序列化 observation。不得将 actual_correct 或私有故障类型喂给公开判定。
5. 核查历史错误修好不能抹除历史，当前模型新增动作单独归责；程序反例不计作模型实跑。
6. 旧 pre_evaluation 的 trace/private_effects 可能因共享列表含本次动作，迁移边界使用实际请求 JSON 中的 history。旧冻结记录不覆盖，旧动作/成本/分数保持，旧 risk 回答不强行解释为新定义。
7. 核查 NO-GO 与零请求预算：离线验证足以处理本版定义修订；没有必须付费辨别的新假设。pending 独立审阅不是唯一不跑理由。

统一离线入口：python -m faultda_bench.responsibility370.audit。
请记录真人姓名、日期、亲自核对的文件/案例、问题及结论；历史 24 题/6 条签字不覆盖本版。
