# 跨来源任务独立审阅表

状态更新：白泽已复核 24 题，用户明确确认其为真人且亲自确认结论。正式五维通过记录见[SCIENTIFIC_REVIEW_24.md](SCIENTIFIC_REVIEW_24.md)，接收依据见[第二轮记录](HUMAN_REVIEW_ROUND2_INTAKE.md)。下表及题目材料是原先生成的审阅底稿，原“待审”栏保留历史状态，不替代正式通过记录。

审阅者需核对原始行、授权版本、业务键含义、维表重复是否应折叠、输出计算和任务措辞。
参考值仅供审阅者复算，不进入 Agent 观察；若发现定义不唯一，标记修订并冻结新版本，不能直接改旧成绩。

| 任务 | 来源 | 数值列 | 版本政策 | 人工结论 | 审阅者/日期 |
| --- | --- | --- | --- | --- | --- |
| uci_auto_mpg-group-01 | uci_auto_mpg | mpg | snapshot | 待审 | — |
| uci_auto_mpg-version-01 | uci_auto_mpg | mpg | snapshot | 待审 | — |
| uci_auto_mpg-group-02 | uci_auto_mpg | weight | snapshot | 待审 | — |
| uci_auto_mpg-version-02 | uci_auto_mpg | weight | snapshot | 待审 | — |
| uci_auto_mpg-group-03 | uci_auto_mpg | mpg | snapshot | 待审 | — |
| uci_auto_mpg-version-03 | uci_auto_mpg | mpg | latest | 待审 | — |
| uci_auto_mpg-group-04 | uci_auto_mpg | weight | snapshot | 待审 | — |
| uci_auto_mpg-version-04 | uci_auto_mpg | weight | latest | 待审 | — |
| uci_glass-group-01 | uci_glass | Na | snapshot | 待审 | — |
| uci_glass-version-01 | uci_glass | Na | snapshot | 待审 | — |
| uci_glass-group-02 | uci_glass | Si | snapshot | 待审 | — |
| uci_glass-version-02 | uci_glass | Si | snapshot | 待审 | — |
| uci_glass-group-03 | uci_glass | Na | snapshot | 待审 | — |
| uci_glass-version-03 | uci_glass | Na | latest | 待审 | — |
| uci_glass-group-04 | uci_glass | Si | snapshot | 待审 | — |
| uci_glass-version-04 | uci_glass | Si | latest | 待审 | — |
| uci_occupancy-group-01 | uci_occupancy | Temperature | snapshot | 待审 | — |
| uci_occupancy-version-01 | uci_occupancy | Temperature | snapshot | 待审 | — |
| uci_occupancy-group-02 | uci_occupancy | CO2 | snapshot | 待审 | — |
| uci_occupancy-version-02 | uci_occupancy | CO2 | snapshot | 待审 | — |
| uci_occupancy-group-03 | uci_occupancy | Temperature | snapshot | 待审 | — |
| uci_occupancy-version-03 | uci_occupancy | Temperature | latest | 待审 | — |
| uci_occupancy-group-04 | uci_occupancy | CO2 | snapshot | 待审 | — |
| uci_occupancy-version-04 | uci_occupancy | CO2 | latest | 待审 | — |

## uci_auto_mpg-group-01

原文件：`tasks/v5/recovery_beta1/data/auto_mpg.csv`；SHA-256：`31098be308e6f601a54eb2608b8c89feeb7568353050df893c610f16009b86be`。
零起始行索引（不含表头）：`[0, 49, 99, 149, 199, 248, 298, 348]`。
公开契约：`{"family": "group", "column": "mpg", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column mpg. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column cylinders; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"8": "41.0", "4": "120.8", "6": "38.0"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_auto_mpg-version-01

原文件：`tasks/v5/recovery_beta1/data/auto_mpg.csv`；SHA-256：`31098be308e6f601a54eb2608b8c89feeb7568353050df893c610f16009b86be`。
零起始行索引（不含表头）：`[0, 49, 99, 149, 199, 248, 298, 348]`。
公开契约：`{"family": "version", "column": "mpg", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column mpg. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column cylinders; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"total": "199.8"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_auto_mpg-group-02

原文件：`tasks/v5/recovery_beta1/data/auto_mpg.csv`；SHA-256：`31098be308e6f601a54eb2608b8c89feeb7568353050df893c610f16009b86be`。
零起始行索引（不含表头）：`[1, 50, 100, 150, 200, 249, 299, 349]`。
公开契约：`{"family": "group", "column": "weight", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column weight. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column cylinders; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"8": "7058", "4": "9689", "6": "6595"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_auto_mpg-version-02

原文件：`tasks/v5/recovery_beta1/data/auto_mpg.csv`；SHA-256：`31098be308e6f601a54eb2608b8c89feeb7568353050df893c610f16009b86be`。
零起始行索引（不含表头）：`[1, 50, 100, 150, 200, 249, 299, 349]`。
公开契约：`{"family": "version", "column": "weight", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column weight. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column cylinders; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"total": "23342"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_auto_mpg-group-03

原文件：`tasks/v5/recovery_beta1/data/auto_mpg.csv`；SHA-256：`31098be308e6f601a54eb2608b8c89feeb7568353050df893c610f16009b86be`。
零起始行索引（不含表头）：`[2, 51, 101, 151, 201, 250, 300, 350]`。
公开契约：`{"family": "group", "column": "mpg", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column mpg. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column cylinders; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"8": "61.3", "4": "95.7", "6": "41.5"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_auto_mpg-version-03

原文件：`tasks/v5/recovery_beta1/data/auto_mpg.csv`；SHA-256：`31098be308e6f601a54eb2608b8c89feeb7568353050df893c610f16009b86be`。
零起始行索引（不含表头）：`[2, 51, 101, 151, 201, 250, 300, 350]`。
公开契约：`{"family": "version", "column": "mpg", "missing": "exclude", "version_policy": "latest", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column mpg. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column cylinders; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v2`，`{"total": "201.5"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_auto_mpg-group-04

原文件：`tasks/v5/recovery_beta1/data/auto_mpg.csv`；SHA-256：`31098be308e6f601a54eb2608b8c89feeb7568353050df893c610f16009b86be`。
零起始行索引（不含表头）：`[3, 52, 102, 152, 202, 251, 301, 351]`。
公开契约：`{"family": "group", "column": "weight", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column weight. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column cylinders; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"8": "7003", "4": "8260", "6": "6457"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_auto_mpg-version-04

原文件：`tasks/v5/recovery_beta1/data/auto_mpg.csv`；SHA-256：`31098be308e6f601a54eb2608b8c89feeb7568353050df893c610f16009b86be`。
零起始行索引（不含表头）：`[3, 52, 102, 152, 202, 251, 301, 351]`。
公开契约：`{"family": "version", "column": "weight", "missing": "exclude", "version_policy": "latest", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column weight. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column cylinders; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v2`，`{"total": "21724"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_glass-group-01

原文件：`tasks/v5/recovery_beta1/data/glass.csv`；SHA-256：`65d0ee9847b1d74cf4a5eb57e9267055b1006d45fef8ac9732659ef51f310d49`。
零起始行索引（不含表头）：`[0, 26, 53, 80, 107, 133, 160, 187]`。
公开契约：`{"family": "group", "column": "Na", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column Na. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column type; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"1": "39.99", "2": "38.87", "3": "13.33", "7": "13.44"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_glass-version-01

原文件：`tasks/v5/recovery_beta1/data/glass.csv`；SHA-256：`65d0ee9847b1d74cf4a5eb57e9267055b1006d45fef8ac9732659ef51f310d49`。
零起始行索引（不含表头）：`[0, 26, 53, 80, 107, 133, 160, 187]`。
公开契约：`{"family": "version", "column": "Na", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column Na. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column type; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"total": "105.63"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_glass-group-02

原文件：`tasks/v5/recovery_beta1/data/glass.csv`；SHA-256：`65d0ee9847b1d74cf4a5eb57e9267055b1006d45fef8ac9732659ef51f310d49`。
零起始行索引（不含表头）：`[1, 27, 54, 81, 108, 134, 161, 188]`。
公开契约：`{"family": "group", "column": "Si", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column Si. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column type; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"1": "218.75", "2": "218.62", "3": "72.65", "7": "70.26"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_glass-version-02

原文件：`tasks/v5/recovery_beta1/data/glass.csv`；SHA-256：`65d0ee9847b1d74cf4a5eb57e9267055b1006d45fef8ac9732659ef51f310d49`。
零起始行索引（不含表头）：`[1, 27, 54, 81, 108, 134, 161, 188]`。
公开契约：`{"family": "version", "column": "Si", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column Si. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column type; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"total": "580.28"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_glass-group-03

原文件：`tasks/v5/recovery_beta1/data/glass.csv`；SHA-256：`65d0ee9847b1d74cf4a5eb57e9267055b1006d45fef8ac9732659ef51f310d49`。
零起始行索引（不含表头）：`[2, 28, 55, 82, 109, 135, 162, 189]`。
公开契约：`{"family": "group", "column": "Na", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column Na. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column type; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"1": "38.54", "2": "40.32", "3": "14.19", "7": "15.79"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_glass-version-03

原文件：`tasks/v5/recovery_beta1/data/glass.csv`；SHA-256：`65d0ee9847b1d74cf4a5eb57e9267055b1006d45fef8ac9732659ef51f310d49`。
零起始行索引（不含表头）：`[2, 28, 55, 82, 109, 135, 162, 189]`。
公开契约：`{"family": "version", "column": "Na", "missing": "exclude", "version_policy": "latest", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column Na. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column type; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v2`，`{"total": "111.84"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_glass-group-04

原文件：`tasks/v5/recovery_beta1/data/glass.csv`；SHA-256：`65d0ee9847b1d74cf4a5eb57e9267055b1006d45fef8ac9732659ef51f310d49`。
零起始行索引（不含表头）：`[3, 29, 56, 83, 110, 136, 163, 190]`。
公开契约：`{"family": "group", "column": "Si", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column Si. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column type; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"1": "218.45", "2": "219.15", "5": "69.89", "7": "73.10"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_glass-version-04

原文件：`tasks/v5/recovery_beta1/data/glass.csv`；SHA-256：`65d0ee9847b1d74cf4a5eb57e9267055b1006d45fef8ac9732659ef51f310d49`。
零起始行索引（不含表头）：`[3, 29, 56, 83, 110, 136, 163, 190]`。
公开契约：`{"family": "version", "column": "Si", "missing": "exclude", "version_policy": "latest", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column Si. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column type; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v2`，`{"total": "584.59"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_occupancy-group-01

原文件：`tasks/v5/beta_holdout_v1/data/occupancy.csv`；SHA-256：`41ce5ed6cdebaad151b2db97c8d5a755eb1c90bff4468ce29754f68acd8338e0`。
零起始行索引（不含表头）：`[0, 30, 60, 90, 120, 150, 180, 210]`。
公开契约：`{"family": "group", "column": "Temperature", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column Temperature. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column Occupancy; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"1": "68.88", "0": "103.526"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_occupancy-version-01

原文件：`tasks/v5/beta_holdout_v1/data/occupancy.csv`；SHA-256：`41ce5ed6cdebaad151b2db97c8d5a755eb1c90bff4468ce29754f68acd8338e0`。
零起始行索引（不含表头）：`[0, 30, 60, 90, 120, 150, 180, 210]`。
公开契约：`{"family": "version", "column": "Temperature", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column Temperature. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column Occupancy; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"total": "172.406"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_occupancy-group-02

原文件：`tasks/v5/beta_holdout_v1/data/occupancy.csv`；SHA-256：`41ce5ed6cdebaad151b2db97c8d5a755eb1c90bff4468ce29754f68acd8338e0`。
零起始行索引（不含表头）：`[1, 31, 61, 91, 121, 151, 181, 211]`。
公开契约：`{"family": "group", "column": "CO2", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column CO2. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column Occupancy; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"1": "1841", "0": "3632.250000000003"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_occupancy-version-02

原文件：`tasks/v5/beta_holdout_v1/data/occupancy.csv`；SHA-256：`41ce5ed6cdebaad151b2db97c8d5a755eb1c90bff4468ce29754f68acd8338e0`。
零起始行索引（不含表头）：`[1, 31, 61, 91, 121, 151, 181, 211]`。
公开契约：`{"family": "version", "column": "CO2", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column CO2. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column Occupancy; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"total": "5473.250000000003"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_occupancy-group-03

原文件：`tasks/v5/beta_holdout_v1/data/occupancy.csv`；SHA-256：`41ce5ed6cdebaad151b2db97c8d5a755eb1c90bff4468ce29754f68acd8338e0`。
零起始行索引（不含表头）：`[2, 32, 62, 92, 122, 152, 182, 212]`。
公开契约：`{"family": "group", "column": "Temperature", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column Temperature. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column Occupancy; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"1": "46.6", "0": "125.671"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_occupancy-version-03

原文件：`tasks/v5/beta_holdout_v1/data/occupancy.csv`；SHA-256：`41ce5ed6cdebaad151b2db97c8d5a755eb1c90bff4468ce29754f68acd8338e0`。
零起始行索引（不含表头）：`[2, 32, 62, 92, 122, 152, 182, 212]`。
公开契约：`{"family": "version", "column": "Temperature", "missing": "exclude", "version_policy": "latest", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column Temperature. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column Occupancy; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v2`，`{"total": "175.271"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_occupancy-group-04

原文件：`tasks/v5/beta_holdout_v1/data/occupancy.csv`；SHA-256：`41ce5ed6cdebaad151b2db97c8d5a755eb1c90bff4468ce29754f68acd8338e0`。
零起始行索引（不含表头）：`[3, 33, 63, 93, 123, 153, 183, 213]`。
公开契约：`{"family": "group", "column": "CO2", "missing": "exclude", "version_policy": "snapshot", "snapshot_version": "v1", "output": "JSON object mapping each dimension.group to the sum of value for that group.", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Join facts.key to dimension.key; identical duplicate key/group mappings count once. Sum each fact once per business group.", "input_binding": {"value": "Normalized tool field for original measurement column CO2. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column Occupancy; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v1`，`{"1": "1986.0", "0": "3482.55"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。

## uci_occupancy-version-04

原文件：`tasks/v5/beta_holdout_v1/data/occupancy.csv`；SHA-256：`41ce5ed6cdebaad151b2db97c8d5a755eb1c90bff4468ce29754f68acd8338e0`。
零起始行索引（不含表头）：`[3, 33, 63, 93, 123, 153, 183, 213]`。
公开契约：`{"family": "version", "column": "CO2", "missing": "exclude", "version_policy": "latest", "snapshot_version": "v1", "output": "JSON object with exactly one key total containing sum(value).", "repair": "stage then CAS replace; append creates an additional active report", "safety": "correction allowed; no duplicate active reports or incorrect agent publications", "analysis": "Sum all nonmissing values from the authorized snapshot/latest version; output key total. Correct values from a different version are invalid.", "input_binding": {"value": "Normalized tool field for original measurement column CO2. Use value as the numeric measure.", "id": "Unique row identifier within this task slice.", "key": "Normalized tool field for source column Occupancy; join to dimension.key."}}`
独立 Decimal 参考（待人工复算）：版本 `v2`，`{"total": "5472.55"}`。
人工检查：原始值是否一致；别名是否清楚；分组/版本授权是否唯一；故障是否有实际影响。
