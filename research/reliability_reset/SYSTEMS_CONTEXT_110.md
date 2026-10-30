# 数据库与分布式系统背景补查｜1.0.10

日期：2026-10-23。范围：聚焦阅读以下一手资料的摘要、定义/概述与指明的文档章节，未复现这些系统或完成系统领域穷尽查新。

| 来源 | 本轮阅读与对应问题 | 对本项目的边界 |
| --- | --- | --- |
| [Herlihy & Wing, Linearizability, 1990，作者公开稿](https://www.cs.cmu.edu/~wing/publications/HerlihyWing90.pdf) | 摘要、引言；并发操作历史与抽象顺序语义 | CAS/revision 本身不是新机制。本项目单线程抓取没有完整并发区间与历史模型，不能声称验证线性一致性 |
| [Mohan et al., ARIES, 1992，IBM Research](https://research.ibm.com/publications/aries-a-transaction-recovery-method-supporting-fine-granularity-locking-and-partial-rollbacks-using-write-ahead-logging) | 官方论文记录及摘要范围，事务恢复与 WAL/部分回滚背景 | 本项目没有实现 ARIES，也没有证明新的数据库恢复协议 |
| [SQLite Atomic Commit](https://www.sqlite.org/atomiccommit.html) | §1、§8 原子提交与崩溃测试 | SQLite 的提交机制已有专门验证。当前故障是应用层返回/提交边界模拟；不是掉电、VFS 故障或磁盘恢复试验 |
| [SQLite WAL](https://www.sqlite.org/wal.html) | 概述、读写与文件相关限制 | 不把使用 SQLite 等同于启用/验证 WAL；本轮不改存储模式，也不作持久性性能结论 |
| [Porcupine 官方仓库](https://github.com/anishathalye/porcupine) | README 用法：可执行顺序模型、调用/返回历史及检查器 | 这类成熟工具需先有正确的历史与模型。未安装或执行 Porcupine，未用自制简化检查替代其保证 |

这次补查强化的推论是：任务语义、效果、回执和当前证据应分清；成熟事务与一致性概念不能被重命名为 Agent 创新。它没有证明本项目与所有数据库研究完全重叠，也没有为新的机制路线发放准入。

若未来有并发或崩溃研究提案，应先写出对象状态机、真实调用/返回边界、失败模型、持久性与允许历史，再判断是否适用已有检查器。只有在这些明确且有独立增量后，才讨论实验；本轮无此提案或实跑。
