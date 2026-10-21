# 0.5.65-dev VeriCost：延后的实跑协议（本版本未执行）

2026-10-21。**本版本 API 调用 0 次、花费 ¥0、下载 0 次。** 本文件不是实跑记录，而是把未来某一轮实跑
所依赖的价格、时段、预算与判定规则一次性记录下来，使那一轮不必重新推导，也不必在产生数字之后再补协议。
机器可读的同一份记录在 `faultda_bench/protocols/vericost_v1_prereg.json` 的 `live_protocol` 块与
`faultda_bench/protocols/vericost_v1_plan.json` 的 `live_protocol` 块中；本文件与那两个块逐值一致，
由 `tests/test_faultda_vericost565_prereg.py` 断言。

状态：`status: deferred_not_run`、`live_authorized: false`、`api_calls: 0`、`cny_spent: "0.000000"`。

## 1. 价格（CNY / 1M tokens，峰时价）

| 模型 | cache hit | cache miss | output |
| --- | --- | --- | --- |
| `deepseek-flash` | 0.04 | 2 | 8 |
| `deepseek-v4-pro` | 0.30 | 9 | 27 |

非峰时（off-peak）为**半价**。账本一律按峰时价记账，偏保守，因此任何预算判断都不会因为时段估计偏差而超支。

## 2. 峰时时段（修正记录，review-5 NIT 2）

峰时为**北京时间周一至周五 09:00–12:00 与 14:00–18:00**，并排除中国法定节假日
（`tz: Asia/Shanghai`，`peak_excludes: "CN public holidays"`）。其余全部时间（含周末与节假日）为非峰时，半价。

设计文档 §6.1/§6.2 的 `preferred_utc_window: ["16:30","00:30"]`（UTC）**作为错误值撤回**：它只覆盖非峰时的
一部分并且漏掉周末，与官方定义不是同一个时段。撤回后的字段形式为
`peak_windows_beijing: [["Mon-Fri","09:00","12:00"],["Mon-Fri","14:00","18:00"]]`，提示在当前时间**落入峰时**
时打印，而不是落在某个 UTC 窗口之外时打印。该 UTC 窗口值不出现在 `faultda_bench/vericost565/` 任何模块或
`faultda_bench/protocols/` 任何清单中（由测试断言）。

## 3. 价格来源与访问日期（不在实现期重新获取）

- 来源：`https://api-docs.deepseek.com/zh-cn/quick_start/pricing`
- 访问日期：**2026-10-20**，由**设计复审第 5 轮**读取并记录。
- `recorded_by: "design review 5; not re-fetched during implementation (no network use in this version)"`。
  本版本**不发起任何网络请求**，因此上表与第 2 节的时段**没有在实现期被重新核对**；这是公开的未解决项
  （OI-2，价格与时段在本沙箱内未经验证）。
- 因此唯一的键名为 `re_verify_before_live: true`（预注册与计划文件使用同一个键名，不再出现
  `re_verify_at_plan_freeze`）：在任何实跑之前必须重新读取定价页，并同时重新确认
  `thinking` / `reasoning_effort` 参数、`deepseek-v4-pro` 的模型 id 与 `/user/balance` 的响应结构。

## 4. 预算与授权（结转，未动用）

`floor_cny: "16.00"`、`cap_cny: "30.00"`。用户授权的 ¥30 **没有被撤回，也没有被使用**：本版本花费
¥0.000000。授权原样结转给未来的实跑版本，按本文件记录的协议使用。实跑所需的 provider 路径
（`client.py` 的预留/headroom/账本/余额下限、`prompts.py`、`mock.py`）在本版本**未实现**，这正是
`audit --no-network` 所断言的内容；实跑版本必须先实现并通过它们自己的测试。

## 5. 可复现性边界：thinking 模式忽略 temperature

在 thinking 模式下 provider **忽略 `temperature`**，因此 P1 的输出**不能通过重跑复现**。这一点可以接受的
前提是：P1 是探索性的，且回执通过 `--verify` 重放核对，而不是通过重跑复现。任何需要逐 token 复现的结论
不得建立在 thinking 模式输出之上。

与此相关的历史缺陷在本版本中**只记录、不修改**（两个文件都不在本版本的编辑允许清单内）：
`agent/llm.py` 从不设置 `thinking`，`faultda_bench/semantic/deepseek.py` 从不设置 `thinking` 且固定
`max_tokens = 800`、`temperature = 0`，并存在模型别名漂移；设计文档把后者记为 pilot_v12 截断的可能原因。
实跑版本必须在自己的新代码里处理 thinking 与 token 上限，而不是改动这两个文件。

## 6. 实跑假设（已预注册，`pending_live`，本版本不评估）

本版本**不产生任何 H1–H3 证据**，下列规则只是记录，不是结论。

- **H1.** 原始 LLM arm 相对精确 DP 留有可测 regret，且大于开发集选出的最佳固定规则。
  SUPPORTED 当且仅当 `q_raw < 0.025` 且 Holm 校正后 `p_H1 < 0.05`。
  **FALSIFIED 当且仅当点估计 `D ≤ 0` 或 `signflip_p([ε − regret_raw_c]) < 0.025`**（`θ_small = ε = 0.05`），
  否则 INCONCLUSIVE（review-5 NIT 7 修正：原先"`q_raw ≥ 0.025` 即 FALSIFIED"会把功效不足的零结果
  当成被否证）。
- **H2.** Q 门控的 hybrid arm 相对原始 arm 把 safe completion 提高至少 0.25，不损失效用，且不被
  `always_full_recompute` 或 `bf` 支配。
- **H3.** 在 `safe_stop` packet 上原始 arm 无公开支持地升级，合并率高于 0.30，且 `shared_numeric` 残差显著为正；
  由于每个残差非负，该条件恰为 **k ≥ 6** 个 cluster 残差为正（2⁻⁶ = 0.015625 < 0.025，而 2⁻⁵ = 0.03125 不是）。

Holm 家族为 {H1, H2, H3}，单侧 α = 0.05；O2 仍是独立的单次检验。
**Partial-A 规则（review-5 NIT 7 修正）**：可用配对数 **`< ceil((2/3) · planned_pairs)`** 时，H1 与 H2 上限为
INCONCLUSIVE，并标注功效不足。原文"`< ⌈2/3⌉ of planned pairs`"是错误写法。

## 7. 实跑前的前置条件（全部尚未满足）

1. 重新读取定价页，确认第 1–2 节的价格与时段（`re_verify_before_live`）。
2. 实现并测试 provider 路径与预算守卫（本版本故意不存在）。
3. 决定唯一研究主张（见 `CLAIM_DECISION_INPUT_0565.md`）；独立测试集是一次性的，在主张确定之前不得消耗。
4. 独立人审仍为 `not_arranged`，科学门仍为 HOLD；本文件不解除任何门。

本文件中的任何数字都不是本版本的结果。本版本的全部结果带
`split: development`、`seen_cluster: true`、`independent_test: false`、`generalization_claim: none`。
