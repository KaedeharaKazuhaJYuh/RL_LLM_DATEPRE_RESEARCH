"""Compare five ServDeg aggregate-flow days and timestamp coverage with DuckDB."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import duckdb


parser = argparse.ArgumentParser()
parser.add_argument("--mon", type=Path, required=True, help="Locally verified MON.parquet")
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

files = {
    "MON": {
        "source": str(args.mon),
        "expected_bytes": 500075664,
        "expected_md5": "833e7b9c411358011bad3172ee541a55",
    },
    "TUE": {
        "source": "https://zenodo.org/api/records/21983587/files/TUE.parquet/content",
        "expected_bytes": 392592741,
        "expected_md5": "59a3f0be0ad7ba2b453164ec8e551218",
    },
    "WED": {
        "source": "https://zenodo.org/api/records/21983587/files/WED.parquet/content",
        "expected_bytes": 465860377,
        "expected_md5": "34118976ffc59dd65177e66e92781525",
    },
    "THU": {
        "source": "https://zenodo.org/api/records/21983587/files/THU.parquet/content",
        "expected_bytes": 418849580,
        "expected_md5": "1cfd1741f677f9db66a7d2aadd832ef0",
    },
    "FRI": {
        "source": "https://zenodo.org/api/records/21983587/files/FRI.parquet/content",
        "expected_bytes": 359826572,
        "expected_md5": "05cd998e5c2186cefd71eb0ca10a8196",
    },
}

db = duckdb.connect()
db.execute("INSTALL httpfs")
db.execute("LOAD httpfs")
result = {
    "record": "https://zenodo.org/records/21983587",
    "license": "CC BY 4.0, stated in the dataset README",
    "remote_file_integrity": "Parquet columns were read remotely via HTTP range requests; remote contents were not downloaded for local full-file hash verification.",
    "days": {},
}

for day, source in files.items():
    if day == "MON":
        digest = hashlib.md5()
        with Path(source["source"]).open("rb") as data:
            for block in iter(lambda: data.read(1024 * 1024), b""):
                digest.update(block)
        if Path(source["source"]).stat().st_size != source["expected_bytes"]:
            raise ValueError("MON.parquet byte length does not match Zenodo metadata")
        if digest.hexdigest() != source["expected_md5"]:
            raise ValueError("MON.parquet MD5 does not match Zenodo metadata")
        source["local_md5_verified"] = True
    row = db.execute(
        """
        SELECT count(*) AS flow_rows,
               sum(CASE WHEN start_time_aggr IS NULL THEN 1 ELSE 0 END) AS rows_missing_start_time,
               min(start_time_aggr) AS first_seen,
               max(start_time_aggr) AS last_seen,
               count(DISTINCT location) AS location_label_count,
               count(DISTINCT protocol) AS protocol_count,
               min(protocol) AS protocol_min,
               max(protocol) AS protocol_max,
               sum(CASE WHEN list_contains(SDd, true) THEN 1 ELSE 0 END) AS rows_with_SDd,
               sum(CASE WHEN list_contains(SDj, true) THEN 1 ELSE 0 END) AS rows_with_SDj,
               sum(CASE WHEN SD_count > 0 THEN 1 ELSE 0 END) AS rows_with_SD_sequences,
               quantile_cont(bidirectional_packets, 0.5) AS packets_p50,
               quantile_cont(bidirectional_packets, 0.9) AS packets_p90,
               quantile_cont(bidirectional_packets, 0.99) AS packets_p99,
               quantile_cont(bidirectional_bytes, 0.5) AS bytes_p50,
               quantile_cont(bidirectional_bytes, 0.9) AS bytes_p90,
               quantile_cont(bidirectional_bytes, 0.99) AS bytes_p99,
               quantile_cont(bidirectional_duration_ms, 0.5) AS duration_ms_p50,
               quantile_cont(bidirectional_duration_ms, 0.99) AS duration_ms_p99
        FROM read_parquet(?)
        """,
        [source["source"]],
    ).fetchone()
    columns = [item[0] for item in db.description]
    metrics = dict(zip(columns, row, strict=True))
    metrics["first_seen"] = metrics["first_seen"].isoformat()
    metrics["last_seen"] = metrics["last_seen"].isoformat()
    minute_rows = db.execute(
        """
        WITH minute_load AS (
            SELECT date_trunc('minute', start_time_aggr) AS minute,
                   count(*) AS flow_starts,
                   sum(bidirectional_packets) AS packet_total,
                   sum(bidirectional_bytes) AS byte_total
            FROM read_parquet(?)
            WHERE start_time_aggr IS NOT NULL
            GROUP BY minute
        )
        SELECT count(*) AS minute_bins,
               quantile_cont(flow_starts, 0.5) AS flow_starts_p50,
               quantile_cont(flow_starts, 0.9) AS flow_starts_p90,
               quantile_cont(flow_starts, 0.99) AS flow_starts_p99,
               max(flow_starts) AS flow_starts_max,
               quantile_cont(packet_total, 0.5) AS packet_total_p50,
               quantile_cont(packet_total, 0.9) AS packet_total_p90,
               quantile_cont(packet_total, 0.99) AS packet_total_p99,
               max(packet_total) AS packet_total_max,
               quantile_cont(byte_total, 0.5) AS byte_total_p50,
               quantile_cont(byte_total, 0.9) AS byte_total_p90,
               quantile_cont(byte_total, 0.99) AS byte_total_p99,
               max(byte_total) AS byte_total_max
        FROM minute_load
        """,
        [source["source"]],
    ).fetchone()
    minute_columns = [item[0] for item in db.description]
    minute_summary = dict(zip(minute_columns, minute_rows, strict=True))
    result["days"][day] = {
        **source,
        **metrics,
        "minute_load_of_flows_by_start_time": minute_summary,
    }

args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({day: row["flow_rows"] for day, row in result["days"].items()}))
