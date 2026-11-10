"""Recompute event-order labels and model rankings from public tau2 runs.

Input: a local tau2-bench checkout's data/tau2/results/final directory.
No agent, benchmark environment, model, or API is executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


MODELS = {
    "claude-3-7-sonnet-20250219": "Claude 3.7 Sonnet",
    "gpt-4.1-2025-04-14": "GPT-4.1",
    "gpt-4.1-mini-2025-04-14": "GPT-4.1 mini",
    "o4-mini-2025-04-16": "o4-mini",
}
MUTATING_TOOLS = {
    "retail": {
        "cancel_pending_order",
        "exchange_delivered_order_items",
        "modify_pending_order_address",
        "modify_pending_order_items",
        "modify_pending_order_payment",
        "modify_user_address",
        "return_delivered_order_items",
    },
    "airline": {
        "book_reservation",
        "cancel_reservation",
        "send_certificate",
        "update_reservation_baggages",
        "update_reservation_flights",
        "update_reservation_passengers",
    },
}
CONFIRM_RE = re.compile(
    r"\b(yes|yeah|yep|yup|sure|okay|confirm(?:ed)?|absolutely|definitely|"
    r"of course|go ahead|please proceed|do it|sounds good|let's do it)\b",
    re.IGNORECASE,
)


def classify_simulation(sim: dict, domain: str) -> tuple[float, bool]:
    """Return native reward and whether a write preceded any broad confirmation."""
    confirmed = False
    violated = False
    for message in sim.get("messages") or []:
        role = message.get("role")
        if role == "user":
            content = (message.get("content") or "").replace("###STOP###", "").strip()
            if content and CONFIRM_RE.search(content):
                confirmed = True
        elif role == "assistant":
            for call in message.get("tool_calls") or []:
                function = call.get("function") or {}
                name = function.get("name") or call.get("name")
                if name in MUTATING_TOOLS[domain] and not confirmed:
                    violated = True
    reward_info = sim.get("reward_info") or {}
    return float(reward_info.get("reward", 0.0)), violated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results_dir", type=Path)
    args = parser.parse_args()
    rows: dict[tuple[str, str], dict[str, int | str]] = {}
    all_versions: set[str] = set()
    inputs: list[dict[str, str | int]] = []

    for model_id, model_label in MODELS.items():
        config = "base" if model_id == "gpt-4.1-mini-2025-04-14" else "default"
        for domain in ("retail", "airline"):
            matches = list(
                args.results_dir.glob(f"{model_id}_{domain}_{config}_*_4trials.json")
            )
            if len(matches) != 1:
                raise SystemExit(
                    f"expected one frozen result for {model_id}/{domain}; found {len(matches)}"
                )
            path = matches[0]
            raw_bytes = path.read_bytes()
            raw = json.loads(raw_bytes)
            version = (raw.get("info") or {}).get("git_commit", "unknown")
            all_versions.add(version)
            row = {
                "model": model_label,
                "domain": domain,
                "source_file": path.name,
                "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
                "recorded_code_commit": version,
                "simulations": len(raw.get("simulations") or []),
                "native_pass": 0,
                "native_fail": 0,
                "confirmed_before_mutation_violation_pass": 0,
                "confirmed_before_mutation_violation_fail": 0,
                "adjusted_pass": 0,
            }
            for sim in raw.get("simulations") or []:
                reward, violation = classify_simulation(sim, domain)
                passed = reward == 1.0
                row["native_pass" if passed else "native_fail"] += 1
                if violation:
                    key = (
                        "confirmed_before_mutation_violation_pass"
                        if passed
                        else "confirmed_before_mutation_violation_fail"
                    )
                    row[key] += 1
                if passed and not violation:
                    row["adjusted_pass"] += 1
            rows[(model_label, domain)] = row
            inputs.append(
                {
                    "file": path.name,
                    "bytes": len(raw_bytes),
                    "sha256": hashlib.sha256(raw_bytes).hexdigest(),
                }
            )

    print(json.dumps({"recorded_code_commits": sorted(all_versions), "inputs": inputs}, indent=2))
    print("model,domain,native_pass,native_fail,viol_pass,viol_fail,adjusted_pass")
    for key in sorted(rows, key=lambda x: (x[1], x[0])):
        row = rows[key]
        print(
            f"{row['model']},{row['domain']},{row['native_pass']},{row['native_fail']},"
            f"{row['confirmed_before_mutation_violation_pass']},"
            f"{row['confirmed_before_mutation_violation_fail']},{row['adjusted_pass']}"
        )

    for domain in ("retail", "airline"):
        original = sorted(
            ((rows[(model, domain)]["native_pass"], model) for model in MODELS.values()),
            reverse=True,
        )
        adjusted = sorted(
            ((rows[(model, domain)]["adjusted_pass"], model) for model in MODELS.values()),
            reverse=True,
        )
        print(f"RANK {domain} native: " + " > ".join(model for _, model in original))
        print(f"RANK {domain} adjusted: " + " > ".join(model for _, model in adjusted))

    totals = defaultdict(int)
    for row in rows.values():
        for key in (
            "simulations",
            "native_pass",
            "native_fail",
            "confirmed_before_mutation_violation_pass",
            "confirmed_before_mutation_violation_fail",
            "adjusted_pass",
        ):
            totals[key] += int(row[key])
    print("TOTAL " + json.dumps(dict(totals), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
