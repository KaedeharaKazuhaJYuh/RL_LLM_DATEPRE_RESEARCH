# 解释有效性与 actor/origin 复审入口

2026-10-16，0.5.0-dev。新表范围为 37 组：12 对既有响应的解释注释、24 个环境组三读取视图的迁移、一份内部科研结论清单。没有新 API 实跑，不把分组数当独立样本。

1. 固定本版 Git 提交并运行 `python -m faultda_bench.validity500.audit`。包内 manifest 提供逐文件哈希；哈希仅检测一致性，不能独立认证历史或人类身份。
2. 在旧 coherent_v38_deepseek.requests.jsonl 检查两种句子和原始响应，先独立判断 final receipt 能否合理指向最后 publish。再读 validity_v39_interpretation.json；原 lookup 主分数必须仍为 0/12、6/12，另一参照不能替换主分数。
3. 检查 explicit 的另一参照被标记不适用；核对自报事件是否为 publish，以及 request_id 是否绑定该位置。四条角色不一致与两条非 publication 索引应分别报告，不推断内部思维过程。
4. 核对 validity_v39_migration.json 的 neutral 视图：actor 范围与生成来源分开，72 条历史往返不变，责任事件和 stop 许可不变，私有效果没有重归责。active_actor 是 represented actor，不代表模型写出了这些动作。
5. 检查 origin 证据是否确实只匹配旧程序源；unknown 不能被模型自报或角色名字提升。模型 fact 回答不能证明工具历史的模型生成来源。评估该语义迁移是否足够明确；不同意见使用 change/reject 记录。
6. 检查 validity_v39_claims.json 是否将指代效果限定为接口有效性，是否把新机制、RL 增益、动作作者和独立科学接受留在未确立状态。

填写 validity_v39_review_template.json：真人姓名、亲自检查声明、完整提交 SHA；只填已亲自复核的组，允许部分返回。checks 表示该项已审查或已判断适用性，不代表必须赞同结论，意见写 verdict/comments。

`python -m faultda_bench.validity500.review --submission <返回文件> --output <新输出文件>` 仅校验范围、来源哈希、重复和完整性，不认证身份或自动登记科学接受。收到意见后还需核对具体发现；旧人工签字不扩展，新审阅仍 pending，科学 HOLD。
