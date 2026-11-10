"""Summarize one licensed ServDeg Parquet day for workload feasibility."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb


parser = argparse.ArgumentParser()
parser.add_argument("parquet", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

digest = hashlib.sha256()
with args.parquet.open("rb") as source:
    for block in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(block)

db = duckdb.connect()
schema = db.execute(
    "DESCRIBE SELECT * FROM read_parquet(?)", [str(args.parquet)]
).fetchall()
overview = db.execute(
    """
    SELECT count(*) AS flows,
           min(start_time_aggr) AS first_seen,
           max(start_time_aggr) AS last_seen,
           count(DISTINCT location) AS locations,
           sum(CASE WHEN list_contains(SDd, true) THEN 1 ELSE 0 END) AS rows_with_SDd,
           sum(CASE WHEN list_contains(SDj, true) THEN 1 ELSE 0 END) AS rows_with_SDj,
           sum(CASE WHEN SD_count > 0 THEN 1 ELSE 0 END) AS rows_with_SD_sequences,
           sum(CASE WHEN SD_time > 0 THEN 1 ELSE 0 END) AS rows_with_SD_time
    FROM read_parquet(?)
    """,
    [str(args.parquet)],
).fetchone()

quantiles = {}
for column in (
    "bidirectional_packets",
    "bidirectional_bytes",
    "bidirectional_duration_ms",
    "bidirectional_mean_piat_ms",
):
    quantiles[column] = db.execute(
        f"""SELECT quantile_cont({column}, 0.5),
                   quantile_cont({column}, 0.9),
                   quantile_cont({column}, 0.99), max({column})
            FROM read_parquet(?)""",
        [str(args.parquet)],
    ).fetchone()

protocols = db.execute(
    """SELECT protocol, count(*) AS flow_count
       FROM read_parquet(?) GROUP BY protocol ORDER BY flow_count DESC""",
    [str(args.parquet)],
).fetchall()
applications = db.execute(
    """SELECT application_category_name, count(*) AS flow_count,
              sum(CASE WHEN SD_count > 0 THEN 1 ELSE 0 END) AS rows_with_SD_sequences
       FROM read_parquet(?) GROUP BY 1 ORDER BY flow_count DESC LIMIT 15""",
    [str(args.parquet)],
).fetchall()

result = {
    "source": {
        "record": "https://zenodo.org/records/21983587",
        "dataset_license": "CC BY 4.0, as stated in the record's README.md",
        "file": args.parquet.name,
        "file_bytes": args.parquet.stat().st_size,
        "sha256": digest.hexdigest(),
    },
    "schema_column_count": len(schema),
    "columns": [{"name": row[0], "type": row[1]} for row in schema],
    "overview": {
        "flow_count": overview[0],
        "first_seen": overview[1].isoformat(),
        "last_seen": overview[2].isoformat(),
        "location_count": overview[3],
        "rows_with_SDd": overview[4],
        "rows_with_SDj": overview[5],
        "rows_with_SD_sequences": overview[6],
        "rows_with_SD_time": overview[7],
    },
    "flow_quantiles_p50_p90_p99_max": {
        name: list(values) for name, values in quantiles.items()
    },
    "protocol_flow_counts": [
        {"protocol": row[0], "flow_count": row[1]} for row in protocols
    ],
    "top_application_categories": [
        {
            "category": row[0],
            "flow_count": row[1],
            "rows_with_SD_sequences": row[2],
        }
        for row in applications
    ],
    "scope_limits": [
        "This is a single daily Parquet file from one university dormitory network.",
        "The dataset contains flow and service-degradation measurements, not device/link root-cause ground truth.",
        "Feature summaries are not packet captures and cannot be described as exact packet replay.",
    ],
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"output": str(args.output), "overview": result["overview"]}, ensure_ascii=False))
