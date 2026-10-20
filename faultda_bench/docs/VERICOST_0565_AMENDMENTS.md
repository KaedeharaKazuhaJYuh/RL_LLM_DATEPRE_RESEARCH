# VeriCost 0.5.65-dev 预注册修正记录（仅追加）

本文件与 `faultda_bench/protocols/vericost_v1_amendments.json` 配对，二者只允许追加，不允许修改或删除
已有条目。追加条目必须同时写入两个文件，`seq` 从 1 开始连续递增。

允许的 `kind`（见预注册 `amendment_policy.allowed_kinds`）：`mde_regret_units`、`k_power_table`、
`gate0_number_change`、`certificate_scope`、`post_eval_erratum`。前四种只在第一个最终评估产物出现之前有效；
之后只允许 `post_eval_erratum`，它可以新增 `analysis_erratum<k>.json`，但永远不能替换任何确认性输入或输出。

禁止修改的键：假设、阈值、arm 列表、指标、regime 网格、主 regime、epsilon。

条目字段：`seq`、`utc`、`kind`、`after_commit`、`text`、`changes`。

## 条目

（暂无条目。C_freeze 时此文件为空。）
