# FaultDA-Bench 0.5.60-dev｜版本完整性冻结（acceptance_v47）

2026-10-20。[0.5.60 报告](RELEASE_0560.md)把"0.5.60 新文件尚未进入新的冻结目录（acceptance_v47），由所有者在发布时决定"列为未决项；所有者已决定冻结。本文件记录冻结范围、纳入与排除规则及其理由。科学门槛仍为 **HOLD**：没有实跑、没有 API 请求、没有重打分、没有新的科学主张，只做字节完整性工程。

## 冻结范围与计数

[`acceptance_v47.json`](../protocols/acceptance_v47.json) 是**增量**清单：

| 组成 | 份数 |
| --- | --- |
| [`acceptance_v46.json`](../protocols/acceptance_v46.json) 原有条目（原序、原哈希，一个未改） | 660 |
| 本版新增 | 30 |
| **合计** | **690** |

v46 以 `e592b097f2d07a02b66fe9e2551e84d23b5f14b3461bc1dd736b9db1a3b6dcda` 作为基线锚点固定在审计代码里，v47 的 `base_catalog_sha256` 必须与之相同。v46 从未被替换或削弱：`python -m faultda_bench.termination555.performance_audit` 仍报 `base_frozen_files_verified: 660` 与 `optimization_files_verified: 11`。

`files` 的键序**不是字典序**：先是 v46 的 660 条按 v46 自身顺序，然后 30 条新增按下表顺序追加，首条是上一份清单 `acceptance_v46.json`——与 v46 当年以 `acceptance_v45.json` 领头追加 11 条的做法一致。审计 `check_scope()` 直接断言这个顺序。

30 条新增：

1. 上一份清单：`faultda_bench/protocols/acceptance_v46.json`。
2. 0.5.55 版内优化证据（12 份）：[`performance555_v1.json`](../protocols/performance555_v1.json) 及其 11 份 `optimization_files`，按该清单自身的键序。此前它们只被 `termination555/performance_audit.py` 里的常量钉住，没有任何验收清单覆盖；本版补齐这个缺口，且不新增任何约束（CI 每次运行都已核对这 11 份哈希）。
3. 0.5.60 不确定性证据（10 份）：`stats560_inputs_v1.json`、`stats560/`（`__init__.py`、`core.py`、`audit.py`）、`tests/test_faultda_stats560.py`、[`UNCERTAINTY_0560.md`](../docs/UNCERTAINTY_0560.md)、[`stats560/summary.json`](stats560/summary.json)、[`stats560/summary.md`](stats560/summary.md)、[`RELEASE_0560.md`](RELEASE_0560.md)、[`RELEASE_0560_VALIDATION.json`](RELEASE_0560_VALIDATION.json)。
4. 0.5.60 版本完整性代码与文档（7 份）：`current_evidence/`（`__init__.py`、`runner.py`、`__main__.py`）、`release560/`（`__init__.py`、`audit.py`）、`tests/test_faultda_release560.py`、本文件。`tests/test_faultda_current_evidence.py` **不**冻结，理由见下节。

## 纳入规则

**一份文件进入冻结，当且仅当它是已发布版本的既成证据，或生产/验证该证据的代码与测试。**

证据必须在复核之后不再移动，这是冻结的全部目的；而产生证据的代码若可随意改动，证据就不可复现——所以两者一起冻结。v46 已经确立了这个惯例：它同时冻结 `faultda_bench/review530/audit.py` 和 `tests/test_faultda_review530.py`，并冻结了 60 份 `tests/*.py`。本版沿用，不发明新规则。

这个惯例有一处边界：v46 冻结的测试钉的都是**既成**证据，而既成证据不再变化，所以测试也不会变。断言某份**活文件**当前内容的测试不属于这一类——它必须随被守护的文件一起合法改动。`tests/test_faultda_current_evidence.py` 正是如此（它钉住登记表的模块数、排除数、审计数、审计 id 与上传路径），因此与登记表一同排除。

`.github/workflows/tests.yml` 与 `pyproject.toml` 本来就在 v46 的 660 份之内，因此 v47 里仍在 `files` 中，本版一个字节未改。

## 排除规则

**一份文件不进入冻结，当它记录的是项目的当前状态而非某个固定版本的证据，因而按设计每次发布都会变。**

理由：冻结用于证明证据没有在复核后被改动。活文档不承载证据，必须保持可编辑；清单若把活文档也哈希进去，下一个版本只要照常更新它就会让本审计失败——这是自己给自己制造的审计失败，而不是对完整性的保护。活文档的完整性由测试保证，不由哈希保证。

`excluded_living_documents` 的 12 项及其理由（审计断言每一项都存在于磁盘上、且都不在 `files` 里）：

| 排除项 | 理由 |
| --- | --- |
| `README.md` | 活文档：每版重写；`scripts.release_version --check` 要求其标题跟随 `VERSION`。 |
| `faultda_bench/README.md` | 活文档：基准概览每版重写。 |
| [`CHANGELOG.md`](../../CHANGELOG.md) | 活文档：按定义每版新增一条。 |
| [`docs/PROJECT_HISTORY.md`](../../docs/PROJECT_HISTORY.md) | 活文档：每版追加。 |
| [`docs/REPRODUCIBILITY.md`](../../docs/REPRODUCIBILITY.md) | 活文档：工具链或入口一变，复现步骤就要改。 |
| `VERSION` | 发布状态文件：版本号唯一的改动点。 |
| `.gitattributes` | 活配置：每新增一份 Markdown 产物就要加一行 `text eol=lf`。 |
| `.github/workflows/faultda-current.yml` | 当前版本的活 CI 配置：必须保持可编辑，新版本才能加审计步骤。 |
| [`current_evidence_v1.json`](../protocols/current_evidence_v1.json) | 活登记表：当前证据作业的单一事实来源，每版都要新增测试模块与审计项。完整性由 `tests/test_faultda_current_evidence.py` 保证，不由哈希保证。 |
| `tests/test_faultda_current_evidence.py` | 活守卫：它钉住活登记表的当前内容（模块数、排除数、审计数、审计 id、上传路径），所以 0.5.65 登记自己的测试模块时必须改它。冻结它等于把登记表本身要避免的"自己给自己制造审计失败"上移一层——每次推送都会因为一次合法的登记而失败。 |
| `docs/en/FAULTDA_BENCH_OVERVIEW.md` | 活文档：`README.md` 的英文镜像，README 一改就要同步。它不承载证据——其引用的数字都在已冻结的 stats560 摘要里。 |
| `acceptance_v47.json` | 清单不能哈希自己；v48 会冻结它，与 v46 冻结 v45 的做法相同。 |

最后一项是 v6..v46 一直遵守的惯例：清单自身绝不出现在自己的 `files` 里，但会哈希所有更早的清单。**本文件也不记录 v47 清单自身的 sha256**：v47 哈希本文件，把清单哈希写进来就构成循环依赖，改一个就必须改另一个，两者都无法稳定。份数可以写，因为份数来自文件**清单**，在计算哈希之前就已确定。清单的实际哈希由 `python -m faultda_bench.release560.audit` 在运行时输出到 `catalog_sha256`。

## 登记表与防漂移守卫

同版本的 [`current_evidence_v1.json`](../protocols/current_evidence_v1.json) 成为当前证据 CI 作业的单一事实来源，`faultda-current.yml` 不再内联任何模块清单，改为调用 `python -m faultda_bench.current_evidence --list/--run-tests/--run-audits`。两道守卫：完整性测试要求每个 `tests/test_faultda_*.py` 要么登记、要么带类别与理由排除（原先 77 个文件中有 22 个静默缺失 CI）；YAML 守卫要求工作流不得重新内联清单、必须调用该入口，且上传清单与 `artifact.paths` 逐行相同。

v47 审计作为**第五项**审计登记进同一张表（`release560_freeze_v47`），因此每次 CI 运行都会重新核对这 690 份哈希。审计自身带四道守卫测试：干净树核验、被篡改的清单副本必须报错、拒绝写入任何冻结位置或 `work/` 之外的仓内路径、以及运行审计不修改任何一份被列文件。清单由 `--emit-manifest` 重新生成，测试断言已提交的字节与重新生成的字节完全相同——冻结因此永远可复现，而不是一份没人能再造的手工产物。

## 快照与活动数量（本版确立的原则）

**已冻结的产物可以记录一个快照；但绝不能把这个快照断言为等于某个活动中、会持续增长的数量。**

本版按此原则做了三件事：

1. [`RELEASE_0560.md`](RELEASE_0560.md) 与 [`RELEASE_0560_VALIDATION.json`](RELEASE_0560_VALIDATION.json) 的计数**自带日期**：新增 `counts_measured_at_commit` 与 `counts_are_point_in_time`，并在报告的验证表上方注明"实测于提交 `bffcab1` 的树"。冻结前这两份记录写的还是本版中途的 CI 形态（60 个模块、4 项审计、452/676/674），与最终发布的 61 个模块、5 项审计、459/683/681 相矛盾；本版在冻结窗口内按实测改正。一个声明了自己时点的快照不会过期，一个读起来像长期事实的数字一定会过期。
2. **不**添加"把 `current_ci_job_replay` 的计数断言等于登记表当前长度"的测试。该测试今天通过，而 0.5.65 登记一个新测试模块的当天就会失败——这与上文把 `tests/test_faultda_current_evidence.py` 排除出冻结所要避免的死锁完全同类，只是换一份文件把同一个耦合重新引入。两个"阻塞"级结论不可能靠同一个机制同时满足。
3. 保留登记表自身的漂移守卫作为正确的那一道：它断言**登记表与磁盘上的 `test_faultda_*.py` 自洽**（每份要么登记、要么带类别与理由排除）。它捕捉真正的失效模式——某一版忘记登记自己的测试——并且随仓库增长始终有效。

同理，本文件仍不记录 v47 清单自身的 sha256（见上节），两份发布记录里也都不含 v47 哈希，因此"记录被清单覆盖"不构成循环：先定稿计数，再对包含这两份记录的全部文件计算 v47。

## 边界

哈希只能证明字节没变。它不认证运行时环境、供应商实际看到的内容，也不认证任何隐藏世界的真值；公开相同、隐藏真值相反的世界依然可以共存。本次冻结不新增实验、不解除 HOLD、不构成独立人审，也不授权任何模型实验。`VERSION`（5.0.15-beta.2）与 `pyproject.toml` 未改。
