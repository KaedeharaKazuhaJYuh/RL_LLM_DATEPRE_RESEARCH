"""Audit cross-day traffic-profile stability in the public ServDeg record.

The Parquet data is scanned remotely with DuckDB HTTP range reads. Only
aggregate profiles are written; flow identities and row-level data are not
exported. The Zenodo record's published size and MD5 are pinned so a metadata
change fails closed instead of silently changing the study input.
"""

from __future__ import annotations

import argparse
import json
import statistics
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

import duckdb


RECORD_ID = "21983587"
RECORD_API = f"https://zenodo.org/api/records/{RECORD_ID}"
PINNED_FILES = {
    "MON.parquet": (500_075_664, "833e7b9c411358011bad3172ee541a55"),
    "TUE.parquet": (392_592_741, "59a3f0be0ad7ba2b453164ec8e551218"),
    "WED.parquet": (465_860_377, "34118976ffc59dd65177e66e92781525"),
    "THU.parquet": (418_849_580, "1cfd1741f677f9db66a7d2aadd832ef0"),
    "FRI.parquet": (359_826_572, "05cd998e5c2186cefd71eb0ca10a8196"),
}
PROFILE_COLUMNS = (
    "bidirectional_packets",
    "bidirectional_bytes",
    "bidirectional_duration_ms",
    "bidirectional_mean_piat_ms",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    request = urllib.request.Request(
        RECORD_API,
        headers={"User-Agent": "FaultDA-Bench public-data audit/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        record = json.load(response)

    files_by_name = {item["key"]: item for item in record["files"]}
    remote_files: dict[str, dict[str, Any]] = {}
    for name, (expected_size, expected_md5) in PINNED_FILES.items():
        item = files_by_name.get(name)
        if item is None:
            raise ValueError(f"Pinned Zenodo file is missing: {name}")
        actual_md5 = item["checksum"].removeprefix("md5:").lower()
        if item["size"] != expected_size or actual_md5 != expected_md5:
            raise ValueError(
                f"Zenodo metadata changed for {name}: "
                f"size={item['size']} md5={actual_md5}"
            )
        remote_files[name] = {
            "url": item["links"]["self"],
            "bytes": item["size"],
            "md5": actual_md5,
        }

    db = duckdb.connect()
    db.execute("INSTALL httpfs")
    db.execute("LOAD httpfs")
    db.execute("SET threads = 8")
    daily: list[dict[str, Any]] = []
    for name, source in remote_files.items():
        url = source["url"]
        feature_selects = []
        for column in PROFILE_COLUMNS:
            for quantile, value in (("p50", 0.50), ("p90", 0.90), ("p99", 0.99)):
                feature_selects.append(
                    f"quantile_cont({column}, {value}) AS {column}_{quantile}"
                )
            feature_selects.append(f"max({column}) AS {column}_max")
        overview = db.execute(
            """SELECT count(*) AS flow_count,
                      min(start_time_aggr), max(start_time_aggr),
                      count(DISTINCT location),
                      count(*) FILTER (WHERE protocol = 6),
                      count(*) FILTER (WHERE protocol <> 6),
                      count(*) FILTER (WHERE protocol IS NULL),
                      count(*) FILTER (WHERE list_contains(SDd, true)),
                      count(*) FILTER (WHERE list_contains(SDj, true)),
                      count(*) FILTER (WHERE SD_count > 0),
                      count(*) FILTER (WHERE SD_time > 0),
                      """ + ", ".join(feature_selects) + " FROM read_parquet(?)",
            [url],
        ).fetchone()
        flow_count = int(overview[0])
        quantiles: dict[str, dict[str, float]] = {}
        offset = 11
        for index, column in enumerate(PROFILE_COLUMNS):
            values = overview[offset + index * 4 : offset + (index + 1) * 4]
            quantiles[column] = {
                key: float(value)
                for key, value in zip(("p50", "p90", "p99", "max"), values)
            }
        daily.append(
            {
                "file": name,
                "source_bytes": source["bytes"],
                "source_md5_from_zenodo_metadata": source["md5"],
                "flow_count": flow_count,
                "first_seen": overview[1].isoformat(),
                "last_seen": overview[2].isoformat(),
                "location_count": int(overview[3]),
                "protocol_flow_counts": {
                    "tcp_protocol_6": int(overview[4]),
                    "other_protocols": int(overview[5]),
                    "null_protocol": int(overview[6]),
                },
                "rows_with_SDd": int(overview[7]),
                "rows_with_SDj": int(overview[8]),
                "rows_with_SD_sequences": int(overview[9]),
                "rows_with_SD_time": int(overview[10]),
                "flow_quantiles": quantiles,
            }
        )

    count_values = [row["flow_count"] for row in daily]
    load_cv = statistics.pstdev(count_values) / statistics.mean(count_values)
    result = {
        "protocol": "servdeg-five-day-crossday-profile-audit-v1",
        "generated_utc_date": date.today().isoformat(),
        "dataset": {
            "record": "https://zenodo.org/records/" + RECORD_ID,
            "record_api": RECORD_API,
            "license_as_stated_in_dataset_readme": "CC BY 4.0",
            "record_metadata_pinned": True,
            "analysis_mode": "remote DuckDB HTTP range reads; aggregate-only output",
            "raw_rows_exported": False,
        },
        "days": daily,
        "cross_day": {
            "day_count": len(daily),
            "flow_count_min": min(count_values),
            "flow_count_median": statistics.median(count_values),
            "flow_count_max": max(count_values),
            "flow_count_population_cv": load_cv,
            "all_flows_use_tcp_protocol_6_each_day": all(
                row["protocol_flow_counts"]["tcp_protocol_6"] == row["flow_count"]
                and row["protocol_flow_counts"]["other_protocols"] == 0
                and row["protocol_flow_counts"]["null_protocol"] == 0
                for row in daily
            ),
            "quantile_range_by_feature": {
                feature: {
                    quantile: {
                        "min": min(row["flow_quantiles"][feature][quantile] for row in daily),
                        "median": statistics.median(
                            row["flow_quantiles"][feature][quantile] for row in daily
                        ),
                        "max": max(row["flow_quantiles"][feature][quantile] for row in daily),
                    }
                    for quantile in ("p50", "p90", "p99", "max")
                }
                for feature in PROFILE_COLUMNS
            },
        },
        "interpretation_limits": [
            "Five weekdays come from one dormitory network and are not independent network deployments.",
            "Parquet records aggregated flows and service-degradation annotations, not packets or network-path root causes.",
            "The profiles can parameterize trace-derived synthetic background workloads, but do not constitute packet replay.",
            "Flow-level TCP profiles do not directly reproduce the UDP workload or packet-ID semantics of the NIKA experiment.",
            "Zenodo MD5 and byte counts are checked against the published record metadata; this remote range scan does not download and locally hash every source byte.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "days": len(daily),
                "flow_counts": {row["file"]: row["flow_count"] for row in daily},
                "flow_count_population_cv": load_cv,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
