"""Audit a local CESNET-TLS-Year22 XS HDF5 archive and emit reproducible counts.

Requires PyTables and NumPy. The script reads all table rows in bounded chunks,
so HDF5 filters are exercised without materializing the full archive in RAM.
It writes only aggregate counts and archive metadata, never flow-level records.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import tables


EXPECTED_BYTES = 2_692_800_942
DATAZOO_COMMIT = "85afe5613a9a1ea840d174d779042ee13f87b4e2"
SOURCE_URL = "https://liberouter.org/datazoo/download?bucket=cesnet-tls-year22&file=CESNET-TLS-Year22-XS.h5"
DECLARED_UNAVAILABLE_DATES = {
    "2022-01-28", "2022-01-29", "2022-01-30", "2022-12-12", "2022-12-13",
    "2022-12-29", "2022-12-30", "2022-12-31",
}
LABEL_BUDGETS = (50, 200, 1_000, 5_000, 10_000)
SPLIT_WEEKS = {
    "initialization": set(range(11, 15)),
    "development": set(range(15, 19)),
    "frozen_prequential": set(range(19, 52)),
    "partial_tail": {52},
    "measurement_change_stress": {10},
    "early_separate_period": set(range(1, 10)),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(8 * 1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--chunk-rows", type=int, default=25_000)
    args = parser.parse_args()
    path = args.archive.resolve()
    out_dir = args.out_dir.resolve()
    if not path.is_file():
        parser.error(f"archive does not exist: {path}")
    if args.chunk_rows < 1:
        parser.error("--chunk-rows must be positive")
    size = path.stat().st_size
    if size != EXPECTED_BYTES:
        parser.error(f"unexpected archive size: {size} != {EXPECTED_BYTES}")

    out_dir.mkdir(parents=True, exist_ok=True)
    date_rows: list[dict[str, object]] = []
    class_rows: list[dict[str, object]] = []
    weekly: dict[int, dict[str, object]] = {}
    phase_totals = {
        name: {"rows": 0, "active_apps": set(), "app_counts": Counter()}
        for name in SPLIT_WEEKS
    }
    phase_totals["pre_2022_iso_boundary"] = {"rows": 0, "active_apps": set(), "app_counts": Counter()}
    all_apps: Counter[int] = Counter()
    all_categories: Counter[int] = Counter()
    app_names: dict[int, str] | None = None
    category_names: dict[int, str] | None = None
    schema_fields: list[dict[str, object]] = []
    seen_dates: set[date] = set()
    total_rows = 0

    with tables.open_file(path, mode="r") as archive:
        tables_by_date = sorted(
            (node for node in archive.walk_nodes("/flows") if isinstance(node, tables.Table)),
            key=lambda node: node._v_name,
        )
        if not tables_by_date:
            raise RuntimeError("no per-date flow tables found under /flows")

        app_enum = dict(tables_by_date[0].get_enum("APP"))
        category_enum = dict(tables_by_date[0].get_enum("CATEGORY"))
        app_names = {int(value): str(name) for name, value in app_enum.items()}
        category_names = {int(value): str(name) for name, value in category_enum.items()}
        for name in tables_by_date[0].colnames:
            dtype = tables_by_date[0].dtype.fields[name][0]
            schema_fields.append({
                "field": name,
                "dtype": str(dtype.subdtype[0] if dtype.subdtype else dtype),
                "shape": list(dtype.subdtype[1]) if dtype.subdtype else [],
            })
        expected_fields = {"APP", "CATEGORY", "PPI", "PPI_LEN", "TIME_FIRST", "SRC_IP"}
        missing = expected_fields.difference(tables_by_date[0].colnames)
        if missing:
            raise RuntimeError(f"required fields missing from HDF table: {sorted(missing)}")

        print(f"tables={len(tables_by_date)} bytes={size} schema_fields={len(tables_by_date[0].colnames)}", flush=True)
        for index, table in enumerate(tables_by_date, start=1):
            if dict(table.get_enum("APP")) != app_enum or dict(table.get_enum("CATEGORY")) != category_enum:
                raise RuntimeError(f"APP enum mismatch at {table._v_pathname}")
            table_date = date.fromisoformat(table._v_name.removeprefix("D")[:4] + "-" + table._v_name[5:7] + "-" + table._v_name[7:9])
            seen_dates.add(table_date)
            counts_app: Counter[int] = Counter()
            counts_category: Counter[int] = Counter()
            ppi_hist = np.zeros(65_536, dtype=np.int64)
            ppi_zero = 0
            first_min = float("inf")
            first_max = float("-inf")
            rows_read = 0
            for start in range(0, table.nrows, args.chunk_rows):
                stop = min(start + args.chunk_rows, table.nrows)
                chunk = table.read(start=start, stop=stop)
                apps = chunk["APP"].astype(np.int32, copy=False)
                cats = chunk["CATEGORY"].astype(np.int32, copy=False)
                ppi = chunk["PPI_LEN"].astype(np.int64, copy=False)
                times = chunk["TIME_FIRST"].astype(np.float64, copy=False)
                counts_app.update({int(k): int(v) for k, v in zip(*np.unique(apps, return_counts=True))})
                counts_category.update({int(k): int(v) for k, v in zip(*np.unique(cats, return_counts=True))})
                if np.any(ppi < 0) or np.any(ppi >= len(ppi_hist)):
                    raise RuntimeError(f"PPI_LEN out of expected unsigned field bounds in {table._v_name}")
                ppi_hist += np.bincount(ppi, minlength=len(ppi_hist))
                ppi_zero += int(np.count_nonzero(ppi == 0))
                finite_times = times[np.isfinite(times)]
                if finite_times.size:
                    first_min = min(first_min, float(finite_times.min()))
                    first_max = max(first_max, float(finite_times.max()))
                rows_read += len(chunk)
            if rows_read != table.nrows:
                raise RuntimeError(f"row mismatch in {table._v_name}: read {rows_read}, expected {table.nrows}")

            iso_calendar = table_date.isocalendar()
            iso_year, week = iso_calendar.year, iso_calendar.week
            week_entry = weekly.setdefault((iso_year, week), {"rows": 0, "dates": 0, "app_counts": Counter(), "ppi_hist": np.zeros_like(ppi_hist)})
            week_entry["rows"] = int(week_entry["rows"]) + rows_read
            week_entry["dates"] = int(week_entry["dates"]) + 1
            week_entry["app_counts"].update(counts_app)
            week_entry["ppi_hist"] += ppi_hist
            for phase_name, weeks in SPLIT_WEEKS.items():
                if iso_year == 2022 and week in weeks:
                    phase = phase_totals[phase_name]
                    phase["rows"] += rows_read
                    phase["active_apps"].update(code for code, count in counts_app.items() if count)
                    phase["app_counts"].update(counts_app)
            if iso_year == 2021 and week == 52:
                phase = phase_totals["pre_2022_iso_boundary"]
                phase["rows"] += rows_read
                phase["active_apps"].update(code for code, count in counts_app.items() if count)
                phase["app_counts"].update(counts_app)
            all_apps.update(counts_app)
            all_categories.update(counts_category)
            date_rows.append({
                "date": table_date.isoformat(), "iso_year": iso_year, "iso_week": week, "rows": rows_read,
                "active_app_codes": sum(count > 0 for count in counts_app.values()),
                "ppi_len_zero": ppi_zero,
                "ppi_len_nonzero_fraction": (rows_read - ppi_zero) / rows_read if rows_read else 0.0,
                "ppi_len_median": _hist_quantile(ppi_hist, 0.50),
                "ppi_len_p95": _hist_quantile(ppi_hist, 0.95),
                "ppi_len_max": int(np.flatnonzero(ppi_hist)[-1]) if ppi_hist.sum() else 0,
                "time_first_min_epoch": None if first_min == float("inf") else first_min,
                "time_first_max_epoch": None if first_max == float("-inf") else first_max,
            })
            for app_code, app_name in sorted(app_names.items()):
                count = counts_app.get(app_code, 0)
                class_rows.append({"date": table_date.isoformat(), "iso_year": iso_year, "iso_week": week, "app_code": app_code,
                                   "app_name": app_name, "rows": count})
            total_rows += rows_read
            if index % 30 == 0 or index == len(tables_by_date):
                print(f"scanned_tables={index}/{len(tables_by_date)} flows={total_rows}", flush=True)

    actual_min = min(seen_dates)
    actual_max = max(seen_dates)
    expected_dates = {actual_min + timedelta(days=i) for i in range((actual_max - actual_min).days + 1)}
    missing_dates = sorted(expected_dates - seen_dates)
    full_calendar_missing = sorted(
        (date(2022, 1, 1) + timedelta(days=i)).isoformat()
        for i in range(365)
        if (date(2022, 1, 1) + timedelta(days=i)) not in seen_dates
    )
    if set(full_calendar_missing) != DECLARED_UNAVAILABLE_DATES:
        raise RuntimeError(
            "observed calendar gaps differ from the pinned DataZoo metadata: "
            f"observed={full_calendar_missing}; expected={sorted(DECLARED_UNAVAILABLE_DATES)}"
        )
    daily_path = out_dir / "CESNET_TLS_YEAR22_XS_DAILY_CENSUS_2026_11_10.csv"
    class_path = out_dir / "CESNET_TLS_YEAR22_XS_DATE_APP_COUNTS_2026_11_10.csv"
    week_path = out_dir / "CESNET_TLS_YEAR22_XS_WEEKLY_CENSUS_2026_11_10.csv"
    split_path = out_dir / "CESNET_TLS_YEAR22_XS_SPLIT_MANIFEST_2026_11_10.csv"
    manifest_path = out_dir / "CESNET_TLS_YEAR22_XS_CENSUS_2026_11_10.json"
    _write_csv(daily_path, date_rows)
    _write_csv(class_path, class_rows)

    weekly_rows: list[dict[str, object]] = []
    for (iso_year, week), item in sorted(weekly.items()):
        counts = item["app_counts"]
        hist = item["ppi_hist"]
        weekly_rows.append({
            "iso_year": iso_year, "iso_week": week, "dates_present": item["dates"], "rows": item["rows"],
            "active_app_codes": len(counts), "apps_with_lt_10": sum(0 < n < 10 for n in counts.values()),
            "apps_with_lt_50": sum(0 < n < 50 for n in counts.values()),
            "apps_with_lt_200": sum(0 < n < 200 for n in counts.values()),
            "ppi_len_nonzero_fraction": float(1 - hist[0] / hist.sum()) if hist.sum() else 0.0,
            "ppi_len_median": _hist_quantile(hist, 0.50), "ppi_len_p95": _hist_quantile(hist, 0.95),
            "ppi_len_max": int(np.flatnonzero(hist)[-1]) if hist.sum() else 0,
            **{f"expected_labeled_app_codes_at_{budget}": round(_expected_covered_classes(counts, int(item["rows"]), budget), 4)
               for budget in LABEL_BUDGETS},
        })
    _write_csv(week_path, weekly_rows)

    split_rows = []
    phase_for_week = {
        2022: {week: phase for phase, weeks in SPLIT_WEEKS.items() for week in weeks},
        2021: {52: "pre_2022_iso_boundary"},
    }
    for row in date_rows:
        split_rows.append({
            "date": row["date"], "iso_year": row["iso_year"], "iso_week": row["iso_week"],
            "phase": phase_for_week.get(int(row["iso_year"]), {}).get(int(row["iso_week"]), "not_in_candidate_windows"),
            "flows": row["rows"], "active_app_codes": row["active_app_codes"],
        })
    _write_csv(split_path, split_rows)

    phase_summary = {}
    for phase_name, phase in phase_totals.items():
        counts = phase["app_counts"]
        phase_summary[phase_name] = {
            "iso_year": 2021 if phase_name == "pre_2022_iso_boundary" else 2022,
            "weeks": [52] if phase_name == "pre_2022_iso_boundary" else sorted(SPLIT_WEEKS[phase_name]),
            "rows": phase["rows"],
            "active_app_codes": len(phase["active_apps"]),
            "apps_with_lt_10": sum(0 < n < 10 for n in counts.values()),
            "apps_with_lt_50": sum(0 < n < 50 for n in counts.values()),
            "apps_with_lt_200": sum(0 < n < 200 for n in counts.values()),
        }
    test_week_rows = [row for row in weekly_rows if row["iso_year"] == 2022 and 19 <= int(row["iso_week"]) <= 51]
    test_label_coverage = {
        str(budget): {
            "mean_expected_classes": round(float(np.mean([row[f"expected_labeled_app_codes_at_{budget}"] for row in test_week_rows])), 4),
            "min_expected_classes": round(float(min(row[f"expected_labeled_app_codes_at_{budget}"] for row in test_week_rows)), 4),
            "max_expected_classes": round(float(max(row[f"expected_labeled_app_codes_at_{budget}"] for row in test_week_rows)), 4),
        }
        for budget in LABEL_BUDGETS
    }
    manifest = {
        "dataset": "CESNET-TLS-Year22 XS HDF5",
        "archive_filename": path.name,
        "archive_bytes": size,
        "archive_sha256": sha256_file(path),
        "official_datazoo_download_url": SOURCE_URL,
        "datazoo_source_commit": DATAZOO_COMMIT,
        "tables": len(date_rows), "total_flows": total_rows,
        "first_date": actual_min.isoformat(), "last_date": actual_max.isoformat(),
        "missing_dates": [d.isoformat() for d in missing_dates],
        "full_calendar_missing_dates": full_calendar_missing,
        "officially_declared_missing_dates_match": True,
        "app_enum_count": len(app_names), "category_enum_count": len(category_names),
        "app_label_map_sha256": sha256_json({str(k): v for k, v in sorted(app_names.items())}),
        "category_label_map_sha256": sha256_json({str(k): v for k, v in sorted(category_names.items())}),
        "schema": schema_fields,
        "active_app_codes_overall": len(all_apps), "active_category_codes_overall": len(all_categories),
        "app_codes_overall": {str(k): {"name": app_names.get(k, "UNKNOWN"), "rows": v} for k, v in sorted(all_apps.items())},
        "category_codes_overall": {str(k): {"name": category_names.get(k, "UNKNOWN"), "rows": v} for k, v in sorted(all_categories.items())},
        "candidate_protocol_phase_counts": phase_summary,
        "frozen_prequential_weekly_label_coverage_expectation": test_label_coverage,
        "label_coverage_formula": "For each APP class with n rows in a week of N flows, sum 1-C(N-n,b)/C(N,b) over classes for a uniform sample of b labels without replacement.",
        "files": {
            "daily": {"name": daily_path.name, "sha256": sha256_file(daily_path)},
            "date_app_counts": {"name": class_path.name, "sha256": sha256_file(class_path)},
            "weekly": {"name": week_path.name, "sha256": sha256_file(week_path)},
            "split_manifest": {"name": split_path.name, "sha256": sha256_file(split_path)},
        },
        "data_handling": "Aggregate metadata only; no flow-level records or identifiers written.",
        "limitations": [
            "XS is a provider-randomized 10M scale, not the full 507M-flow archive.",
            "Published APP label proportions reflect provider sampling and do not estimate production traffic priors.",
            "Counts establish support only; they are not model performance or a scientific result.",
            "Field leakage and cross-date client-ID stability require separate audits before modeling.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"archive_sha256={manifest['archive_sha256']}")
    print(f"total_flows={total_rows} dates={len(date_rows)} missing_dates={len(missing_dates)}")
    print(f"active_app_codes={len(all_apps)} active_category_codes={len(all_categories)}")
    for name, phase in phase_summary.items():
        print(f"phase={name} rows={phase['rows']} active_apps={phase['active_app_codes']} <50={phase['apps_with_lt_50']}")
    print(f"split_manifest_sha256={manifest['files']['split_manifest']['sha256']}")
    print(f"wrote={manifest_path}")
    return 0


def _hist_quantile(histogram: np.ndarray, q: float) -> int:
    total = int(histogram.sum())
    if total == 0:
        return 0
    target = max(1, int(np.ceil(q * total)))
    return int(np.searchsorted(np.cumsum(histogram), target, side="left"))


def _expected_covered_classes(counts: Counter[int], population: int, budget: int) -> float:
    """Expected APP classes represented by a uniform sample without replacement."""
    if population <= 0 or budget <= 0:
        return 0.0
    budget = min(budget, population)
    expected = 0.0
    for count in counts.values():
        if count <= 0:
            continue
        if population - count < budget:
            expected += 1.0
            continue
        log_no_sample = (
            math.lgamma(population - count + 1)
            - math.lgamma(population - count - budget + 1)
            - math.lgamma(population + 1)
            + math.lgamma(population - budget + 1)
        )
        expected += 1.0 - math.exp(min(0.0, log_no_sample))
    return expected


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty census: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
