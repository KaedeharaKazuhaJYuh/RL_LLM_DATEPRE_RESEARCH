"""Audit cross-granularity semantics in the public CESNET sparse-IP sample."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


EXPECTED_MD5 = "2c50d80fd8b78416a7f960d34e001638"
GAP_DENOMINATOR = 143_280


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--archive",
        type=Path,
        default=Path("work/cesnet_ts26_probe_2026_11_09/ip_addresses_sample_gaps_100_80.tar.gz"),
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path("work/cesnet_ts26_probe_2026_11_09/extracted/ip_addresses_sample_gaps_100_80"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research/reliability_reset/experiments/communication_telemetry/CESNET_MULTISCALE_PROBE_2026_11_09.json"),
    )
    args = parser.parse_args()

    digest = hashlib.md5()
    with args.archive.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    archive_md5 = digest.hexdigest()
    if archive_md5 != EXPECTED_MD5:
        raise SystemExit(f"Official archive checksum mismatch: {archive_md5}")

    identifiers = pd.read_csv(args.data_root / "identifiers.csv")["id_ip"].astype(int).tolist()
    time_10m_frame = pd.read_csv(args.data_root / "times/times_10_minutes.csv")
    time_day_frame = pd.read_csv(args.data_root / "times/times_1_day.csv")
    time_10m = dict(zip(time_10m_frame["id_time"], pd.to_datetime(time_10m_frame["time"], utc=True)))
    time_day = dict(zip(time_day_frame["id_time"], pd.to_datetime(time_day_frame["time"], utc=True)))

    all_rows: list[pd.DataFrame] = []
    additive_matches = {"n_flows": 0, "n_packets": 0, "n_bytes": 0}
    additive_mismatches = {"n_flows": 0, "n_packets": 0, "n_bytes": 0}
    observed_rows: list[int] = []
    observed_days: list[int] = []

    for ip in identifiers:
        ten = pd.read_csv(args.data_root / f"agg_10_minutes/{ip}.csv")
        daily = pd.read_csv(args.data_root / f"agg_1_day/{ip}.csv")
        observed_rows.append(len(ten))
        observed_days.append(len(daily))

        ten["utc_day"] = pd.to_datetime(ten["id_time"].map(time_10m), utc=True).dt.floor("D")
        ten["duration_flow_num"] = ten["avg_duration"] * ten["n_flows"]
        ten["tcp_packet_num"] = ten["tcp_udp_ratio_packets"] * ten["n_packets"]
        ten["tcp_byte_num"] = ten["tcp_udp_ratio_bytes"] * ten["n_bytes"]
        by_day = ten.groupby("utc_day", as_index=False).agg(
            n_windows_10m=("id_time", "size"),
            n_flows_10m=("n_flows", "sum"),
            n_packets_10m=("n_packets", "sum"),
            n_bytes_10m=("n_bytes", "sum"),
            avg_duration_unweighted_10m=("avg_duration", "mean"),
            duration_flow_num=("duration_flow_num", "sum"),
            tcp_ratio_unweighted_10m=("tcp_udp_ratio_packets", "mean"),
            tcp_byte_ratio_unweighted_10m=("tcp_udp_ratio_bytes", "mean"),
            tcp_packet_num=("tcp_packet_num", "sum"),
            tcp_byte_num=("tcp_byte_num", "sum"),
            n_packets_weight=("n_packets", "sum"),
            n_bytes_weight=("n_bytes", "sum"),
        )
        by_day["avg_duration_flow_weighted_10m"] = by_day["duration_flow_num"] / by_day["n_flows_10m"]
        by_day["tcp_ratio_packet_weighted_10m"] = by_day["tcp_packet_num"] / by_day["n_packets_weight"]
        by_day["tcp_ratio_byte_weighted_10m"] = by_day["tcp_byte_num"] / by_day["n_bytes_weight"]

        daily["utc_day"] = pd.to_datetime(daily["id_time"].map(time_day), utc=True)
        joined = by_day.merge(
            daily[["utc_day", "n_flows", "n_packets", "n_bytes", "avg_duration", "tcp_udp_ratio_packets", "tcp_udp_ratio_bytes"]],
            on="utc_day",
            how="inner",
            validate="one_to_one",
        )
        joined["id_ip"] = ip
        joined["duration_abs_diff"] = (joined["avg_duration_flow_weighted_10m"] - joined["avg_duration"]).abs()
        joined["duration_unweighted_abs_diff"] = (joined["avg_duration_unweighted_10m"] - joined["avg_duration"]).abs()
        joined["tcp_packet_unweighted_abs_diff"] = (joined["tcp_ratio_unweighted_10m"] - joined["tcp_udp_ratio_packets"]).abs()
        joined["tcp_byte_unweighted_abs_diff"] = (joined["tcp_byte_ratio_unweighted_10m"] - joined["tcp_udp_ratio_bytes"]).abs()
        joined["tcp_packet_abs_diff"] = (joined["tcp_ratio_packet_weighted_10m"] - joined["tcp_udp_ratio_packets"]).abs()
        joined["tcp_byte_abs_diff"] = (joined["tcp_ratio_byte_weighted_10m"] - joined["tcp_udp_ratio_bytes"]).abs()
        for metric in additive_matches:
            equal = joined[f"{metric}_10m"] == joined[metric]
            additive_matches[metric] += int(equal.sum())
            additive_mismatches[metric] += int((~equal).sum())
        all_rows.append(joined)

    result = pd.concat(all_rows, ignore_index=True)

    def distribution(column: str) -> dict[str, float | int]:
        series = result[column].dropna()
        return {
            "n": int(series.size),
            "median": round(float(series.quantile(0.50)), 6),
            "p90": round(float(series.quantile(0.90)), 6),
            "p95": round(float(series.quantile(0.95)), 6),
            "max": round(float(series.max()), 6),
            "fraction_gt_0_02": round(float((series > 0.02).mean()), 6),
            "fraction_gt_0_05": round(float((series > 0.05).mean()), 6),
        }

    tcp_candidates = result[(result["n_packets_10m"] >= 100) & (result["n_windows_10m"] >= 3)]
    duration_candidates = result[(result["n_flows_10m"] >= 100) & (result["n_windows_10m"] >= 3)]
    byte_candidate = result.loc[result["n_bytes_10m"].idxmax()]
    ratio_examples = tcp_candidates.nlargest(5, "tcp_packet_abs_diff")
    duration_examples = duration_candidates.nlargest(5, "duration_abs_diff")

    output = {
        "protocol": "cesnet-ts26-sparse-sample-cross-granularity-probe-v1",
        "date": "2026-11-09",
        "source": "Zenodo 21945629 ip_addresses_sample_gaps_100_80.tar.gz",
        "archive_md5": archive_md5,
        "sample": {
            "ip_series": len(identifiers),
            "time_slots_10_minutes": len(time_10m_frame),
            "time_slots_1_day": len(time_day_frame),
            "fixed_gap_denominator": GAP_DENOMINATOR,
            "observed_10m_rows_total": sum(observed_rows),
            "daily_entity_rows_total": sum(observed_days),
            "gap_ratio_min": round(1 - max(observed_rows) / GAP_DENOMINATOR, 6),
            "gap_ratio_median": round(1 - pd.Series(observed_rows).median() / GAP_DENOMINATOR, 6),
            "gap_ratio_max": round(1 - min(observed_rows) / GAP_DENOMINATOR, 6),
            "daily_entity_coverage_median": round(float(pd.Series(observed_days).median() / len(time_day_frame)), 6),
            "joined_entity_days": int(len(result)),
        },
        "daily_additive_counter_matches": additive_matches,
        "daily_additive_counter_mismatches": additive_mismatches,
        "stored_daily_vs_10m_derived_semantics": {
            "flow_weighted_avg_duration_abs_difference_seconds": distribution("duration_abs_diff"),
            "unweighted_10m_avg_duration_vs_daily_abs_difference_seconds": distribution("duration_unweighted_abs_diff"),
            "unweighted_10m_packet_ratio_vs_daily_abs_difference": distribution("tcp_packet_unweighted_abs_diff"),
            "unweighted_10m_byte_ratio_vs_daily_abs_difference": distribution("tcp_byte_unweighted_abs_diff"),
            "packet_weighted_tcp_ratio_abs_difference": distribution("tcp_packet_abs_diff"),
            "byte_weighted_tcp_ratio_abs_difference": distribution("tcp_byte_abs_diff"),
        },
        "illustrative_rows_selected_by_largest_discrepancy": {
            "packet_ratio": ratio_examples[["id_ip", "utc_day", "n_windows_10m", "n_packets_10m", "tcp_udp_ratio_packets", "tcp_ratio_unweighted_10m", "tcp_ratio_packet_weighted_10m", "tcp_packet_abs_diff"]].head(5).assign(utc_day=lambda df: df["utc_day"].astype(str)).round(6).to_dict("records"),
            "avg_duration": duration_examples[["id_ip", "utc_day", "n_windows_10m", "n_flows_10m", "avg_duration", "avg_duration_unweighted_10m", "avg_duration_flow_weighted_10m", "duration_abs_diff"]].head(5).assign(utc_day=lambda df: df["utc_day"].astype(str)).round(6).to_dict("records"),
            "additive_bytes": {"id_ip": int(byte_candidate["id_ip"]), "utc_day": str(byte_candidate["utc_day"]), "n_windows_10m": int(byte_candidate["n_windows_10m"]), "n_bytes_10m": int(byte_candidate["n_bytes_10m"]), "n_bytes": int(byte_candidate["n_bytes"])},
        },
        "interpretation_limit": "The sample is one high-gap stratum from one ISP dataset. Ratios and averages are rounded published metrics; weighted reconstructions are weighted means of reported values, not exact raw-packet or raw-flow ground truth. These are data-semantics diagnostics, not Agent results or independent task-family evidence.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sample": output["sample"], "mismatches": additive_mismatches, "ratio": output["stored_daily_vs_10m_derived_semantics"]["packet_weighted_tcp_ratio_abs_difference"], "duration": output["stored_daily_vs_10m_derived_semantics"]["flow_weighted_avg_duration_abs_difference_seconds"]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
