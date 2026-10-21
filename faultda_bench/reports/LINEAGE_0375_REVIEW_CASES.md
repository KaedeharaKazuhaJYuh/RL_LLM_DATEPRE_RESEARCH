# 0.3.75-dev 复审范围表

共 40 例：36 个已有责任反例、4 个新历史来源快照。先依据源数据和事件重算，再核对预置标签。未收到新签字；此表不代表已完成独立审阅。

行号为 JSON 数组的 0-based 索引；旧文件查看 rows，新文件查看 snapshots。具体 SHA256 以 review_v34_registry.json 和空白返回表为准。

| 案例 | 源文件 | 数组位置 | 公共证据版本 |
| --- | --- | ---: | --- |
| v33|utc_end|initial_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 0 | responsibility-v1 |
| v33|utc_end|initial_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 1 | responsibility-v1 |
| v33|utc_end|staged_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 2 | responsibility-v1 |
| v33|utc_end|staged_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 3 | responsibility-v1 |
| v33|utc_end|acknowledged_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 4 | responsibility-v1 |
| v33|utc_end|acknowledged_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 5 | responsibility-v1 |
| v33|utc_end|timeout_before | [responsibility_v33_results.json](responsibility_v33_results.json) | 6 | responsibility-v1 |
| v33|utc_end|timeout_after | [responsibility_v33_results.json](responsibility_v33_results.json) | 7 | responsibility-v1 |
| v33|utc_end|observed_after_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 8 | responsibility-v1 |
| v33|utc_end|repaired_after_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 9 | responsibility-v1 |
| v33|utc_end|unknown_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 10 | responsibility-v1 |
| v33|utc_end|unknown_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 11 | responsibility-v1 |
| v33|utc_end|timeout_wrong_before | [responsibility_v33_results.json](responsibility_v33_results.json) | 12 | responsibility-v1 |
| v33|utc_end|timeout_wrong_after | [responsibility_v33_results.json](responsibility_v33_results.json) | 13 | responsibility-v1 |
| v33|utc_end|resolved_wrong_before | [responsibility_v33_results.json](responsibility_v33_results.json) | 14 | responsibility-v1 |
| v33|utc_end|resolved_wrong_after | [responsibility_v33_results.json](responsibility_v33_results.json) | 15 | responsibility-v1 |
| v33|utc_end|model_wrong_repaired | [responsibility_v33_results.json](responsibility_v33_results.json) | 16 | responsibility-v1 |
| v33|utc_end|duplicate_append_repaired | [responsibility_v33_results.json](responsibility_v33_results.json) | 17 | responsibility-v1 |
| v33|plus8_end|initial_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 18 | responsibility-v1 |
| v33|plus8_end|initial_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 19 | responsibility-v1 |
| v33|plus8_end|staged_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 20 | responsibility-v1 |
| v33|plus8_end|staged_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 21 | responsibility-v1 |
| v33|plus8_end|acknowledged_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 22 | responsibility-v1 |
| v33|plus8_end|acknowledged_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 23 | responsibility-v1 |
| v33|plus8_end|timeout_before | [responsibility_v33_results.json](responsibility_v33_results.json) | 24 | responsibility-v1 |
| v33|plus8_end|timeout_after | [responsibility_v33_results.json](responsibility_v33_results.json) | 25 | responsibility-v1 |
| v33|plus8_end|observed_after_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 26 | responsibility-v1 |
| v33|plus8_end|repaired_after_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 27 | responsibility-v1 |
| v33|plus8_end|unknown_correct | [responsibility_v33_results.json](responsibility_v33_results.json) | 28 | responsibility-v1 |
| v33|plus8_end|unknown_wrong | [responsibility_v33_results.json](responsibility_v33_results.json) | 29 | responsibility-v1 |
| v33|plus8_end|timeout_wrong_before | [responsibility_v33_results.json](responsibility_v33_results.json) | 30 | responsibility-v1 |
| v33|plus8_end|timeout_wrong_after | [responsibility_v33_results.json](responsibility_v33_results.json) | 31 | responsibility-v1 |
| v33|plus8_end|resolved_wrong_before | [responsibility_v33_results.json](responsibility_v33_results.json) | 32 | responsibility-v1 |
| v33|plus8_end|resolved_wrong_after | [responsibility_v33_results.json](responsibility_v33_results.json) | 33 | responsibility-v1 |
| v33|plus8_end|model_wrong_repaired | [responsibility_v33_results.json](responsibility_v33_results.json) | 34 | responsibility-v1 |
| v33|plus8_end|duplicate_append_repaired | [responsibility_v33_results.json](responsibility_v33_results.json) | 35 | responsibility-v1 |
| v34|utc_end|bad_never_committed | [lineage_v34_results.json](lineage_v34_results.json) | 0 | responsibility-v1.1-receipt-witness |
| v34|utc_end|bad_committed | [lineage_v34_results.json](lineage_v34_results.json) | 1 | responsibility-v1.1-receipt-witness |
| v34|plus8_end|bad_never_committed | [lineage_v34_results.json](lineage_v34_results.json) | 2 | responsibility-v1.1-receipt-witness |
| v34|plus8_end|bad_committed | [lineage_v34_results.json](lineage_v34_results.json) | 3 | responsibility-v1.1-receipt-witness |
