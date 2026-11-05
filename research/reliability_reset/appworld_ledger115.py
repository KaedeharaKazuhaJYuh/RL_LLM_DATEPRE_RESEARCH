"""Export a payload-free cost and outcome ledger from local AppWorld journals."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path


def read_jsonl(path: Path) -> tuple[list[dict], int]:
    if not path.exists():
        return [], 0
    rows, malformed = [], 0
    for line in path.read_text(encoding="utf8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            malformed += 1
    return rows, malformed


def export(input_root: Path, manifest: dict) -> tuple[dict, list[dict]]:
    cases, ledger = [], []
    for spec in manifest["attempts"]:
        attempt = spec["attempt"]
        journal_path = input_root / "journals" / attempt / "events.jsonl"
        status_path = input_root / "response-status" / f"{attempt}.jsonl"
        events, malformed = read_jsonl(journal_path)
        statuses, malformed_status = read_jsonl(status_path)
        requests = [row for row in events if row.get("kind") == "model_request"]
        models = {row["step"]: row for row in events if row.get("kind") == "model"}
        guards = {row["step"]: row for row in events
                  if row.get("kind") == "controller_stop" and row.get("reason") == "input_token_limit"}
        finals = [row for row in events if row.get("kind") == "final"]
        final = finals[-1] if finals else {}
        prefix = {key: spec[key] for key in ("arm", "task", "attempt", "role")}
        model_statuses = Counter()
        known_cost = 0.0
        known_cost_rows = 0
        unpriced_calls = 0
        for request in requests:
            step = request["step"]
            model = models.get(step)
            guard = guards.get(step)
            if guard or (model and model.get("error_type") == "input_token_limit"):
                status = "input_token_limit"
            elif model:
                status = model.get("status", "unknown")
            else:
                status = "unresolved"
            model_statuses[status] += 1
            model = model or {}
            usage = model.get("usage") or {}
            estimate = model.get("peak_estimate_usd")
            if estimate is not None:
                known_cost += estimate
                known_cost_rows += 1
            elif status != "input_token_limit":
                unpriced_calls += 1
            ledger.append({
                **prefix, "channel": "model", "step": step, "status": status,
                "timestamp_utc": request.get("timestamp_utc"),
                "prompt_bytes": request.get("prompt_bytes"),
                "input_tokens": usage.get("prompt_tokens", model.get("input_tokens", (guard or {}).get("input_tokens"))),
                "input_token_limit": model.get("input_token_limit", (guard or {}).get("input_token_limit")),
                "cache_hit_tokens": usage.get("prompt_cache_hit_tokens"),
                "cache_miss_tokens": usage.get("prompt_cache_miss_tokens"),
                "output_tokens": usage.get("completion_tokens", model.get("output_tokens")),
                "seconds": model.get("seconds"),
                "peak_gpu_bytes_cumulative": model.get("peak_gpu_bytes"),
                "peak_price_estimate_usd": estimate,
                "finish_reason": model.get("finish_reason"),
            })
        for row in events:
            if row.get("kind") == "tool":
                observation = row.get("observation") or {}
                ledger.append({**prefix, "channel": "tool", "step": row.get("step"),
                               "result": "exception" if "error" in observation else "returned",
                               "seconds": row.get("seconds")})
        terminal_status = None
        for row in statuses:
            ledger.append({**prefix, "channel": "sdk_http", "sdk_track": row.get("sdk_track"),
                           "status_code": row.get("status_code"), "seconds": row.get("seconds")})
            if row.get("app") == "supervisor" and row.get("api") == "show_active_task" and not row.get("sdk_track"):
                try:
                    status = json.loads(row.get("response_text", "null"))
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(status, dict):
                    terminal_status = status.get("status")
        cases.append({
            **prefix, "journal_present": journal_path.exists(), "complete": bool(final),
            "termination": final.get("termination") if final else "interrupted",
            "native_success": final.get("native_success"),
            "native_tests_passed": final.get("native_tests_passed"),
            "native_tests_total": final.get("native_tests_total"),
            "task_completed_signal": final.get("task_completed_signal"),
            "supervisor_status": terminal_status if terminal_status in ("success", "fail") else None,
            "safety_judgment": final.get("safety_judgment", "unknown"),
            "model_requests": len(requests), "model_statuses": dict(model_statuses),
            "known_peak_estimate_usd": round(known_cost, 8) if known_cost_rows else None,
            "unpriced_model_calls_or_unresolved": unpriced_calls,
            "tool_events": sum(row.get("kind") == "tool" for row in events),
            "sdk_http_events": len(statuses), "malformed_journal_lines": malformed,
            "malformed_status_lines": malformed_status,
        })
    arms = {}
    for name in sorted({row["arm"] for row in cases}):
        rows = [row for row in cases if row["arm"] == name]
        primary = [row for row in rows if row["role"] == "primary"]
        arms[name] = {
            "attempts": len(rows), "task_indices": len({row["task"] for row in rows}),
            "primary_attempts": len(primary), "primary_complete": sum(row["complete"] for row in primary),
            "primary_native_passes": sum(row["native_success"] is True for row in primary),
            "primary_native_failures": sum(row["native_success"] is False for row in primary),
            "primary_terminations": dict(Counter(row["termination"] for row in primary)),
            "primary_resource_censored": sum(row["termination"] in ("input_token_limit", "prompt_limit")
                                             for row in primary),
        }
    return {"version": manifest["version"], "arms": arms, "cases": cases}, ledger


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_root", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf8"))
    summary, ledger = export(args.input_root, manifest)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / "SUMMARY_115.json").open("x", encoding="utf8", newline="\n") as out:
        json.dump(summary, out, indent=2, ensure_ascii=False)
        out.write("\n")
    with (args.output_dir / "CALLS_115.jsonl").open("x", encoding="utf8", newline="\n") as out:
        for row in ledger:
            out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"Exported {len(summary['cases'])} attempts and {len(ledger)} payload-free call records.")


if __name__ == "__main__":
    main()
