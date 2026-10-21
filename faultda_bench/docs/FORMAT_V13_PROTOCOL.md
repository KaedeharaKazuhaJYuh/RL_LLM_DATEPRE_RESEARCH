# 动作输出诊断协议 · 0.2.70-dev

冻结日期：2026-10-11。原提示、可靠性说明和三个任务初始公开快照不变；不向模型提供故障标签、答案或环境对象。每个快照比较关闭推理与开启 low 推理，各用 800/2048 输出预算、重复两次，固定随机顺序共 24 请求。每请求是独立单步决策，**不执行返回的工具动作**。

程序先运行网络替身测试，再写入 [plan](../reports/format_v13_plan.json)，之后真实请求严格比对计划、代码和源数据哈希。端点 deepseek-flash、temperature=0、JSON 输出、45 秒超时、最多 24 次、无重试。关闭推理时不发送 reasoning_effort；开启时显式 low。参数依据 [DeepSeek 思考模式](https://api-docs.deepseek.com/guides/thinking_mode/)及 [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)，官方检索核查日期同上。

保留 finish_reason、是否 length、正文是否为空、正文哈希/字节数、推理正文字节数、合法动作、分类、usage、模型/响应编号、耗时及规范请求体哈希。不保存响应或推理正文，不记录凭据与异常消息。类别区分合法动作、空输出、JSON 错误（含重复键/非有限数）、schema 错误、响应结构异常、服务错误与未发送原因。合法 action/params 仅表示外层动作格式通过，并不保证工具参数或语义正确。

重建器独立核验公开快照、规范请求体、计划覆盖、动作结构和汇总。没有响应正文，因此**不能独立重放响应解析分类**，也不认证供应商来源；receipt 分类是执行时记录，不是事后可复算原始响应。测试通过不替代人工审阅。

初始快照不能覆盖先前失败的完整对话历史；两次重复不足以支持稳定性或显著性结论。不同推理模式的默认温度处理可能不同，本比较是服务配置的整体诊断。不得与上一轮自适应多步轨迹混池，不能声称恢复、RL 或创新性提升。

离线核验：`python -m faultda_bench.formatdiag.verify faultda_bench/reports/format_v13_deepseek.json`。冻结或重新调用必须使用新路径；默认不自动发起请求，显式提供 --protocol 与 --output 才真实调用。
