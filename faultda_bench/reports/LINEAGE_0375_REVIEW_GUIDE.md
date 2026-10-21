# 0.3.75-dev 复审与返回说明

本版未收到新增独立人工签字；独立科学审阅 pending，HOLD。内部测试、空白表与自报姓名均不算已完成独立审阅。

1. 打开 review_v34_registry.json 与 review_v34_return_template.json。范围为 36 个已有责任反例和 4 个新历史来源快照；源文件/行号与每例 SHA256 绑定，来源表见 LINEAGE_0375_REVIEW_CASES.md。
2. 亲自核对 raw CSV 行、窗口契约、stage 内容、每次 publish 的 request_id/CAS revision；复算实际账本和公开可证明范围。准备脚本代表历史 Agent 的责任仍保留，不与环境初始错误混淆。
3. 核对两种历史的全部公共观察相同，当前 revision 3 且报告正确；私有账本仅其中一条有历史错误。检查额外 status/inspect 为什么仍不区分历史。
4. 核对 receipt_lookup 只查同 SQLite 数据库的请求元数据、只收费一次 check、无额外写入；唯一 id 和持久完整表是必要限制。新增证据权限不等于策略或模型增益。
5. 返回表填写姓名、真人/亲自复核声明、所审 Git 完整提交、总体技术意见；仅将亲自检查的 case checked 设为 true，并写 pass/change/reject 及问题。可移除未审案例或保留 checked=false/null，不必一次审完 40 例。
6. 接收校验命令：python -m faultda_bench.lineage375.review --validate-submission <返回JSON路径> --output <新的接收结果路径>。工具只校验范围和结构，提交 SHA 只验格式，不自行认证 Git 对象/身份；结合已有可信身份与亲自复核证据再登记范围。
7. 通过技术范围核对不等于科学原创性验收；不把 12 次程序执行称 API 或 RL 成绩。原签字不自动扩展到新案例。

统一离线入口：python -m faultda_bench.lineage375.audit。空表不能登记已审阅；任意提交均不能由校验器自动修改 HOLD。
