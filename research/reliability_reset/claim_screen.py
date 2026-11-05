"""Offline falsification screen over existing fault-exposure and public prefixes.

Not a recovery algorithm, a new task generator or an independent experiment.
"""

import argparse
import copy
import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path

from faultda_bench.semantic.policies import choose
from faultda_bench.semantic.tasks import REPO
from .audit import require
from .evidence_planner import INTERFACES
from .offline160 import audit_archive
from .outcomes import classify
from .recovery_credit import fingerprint, save


ARMS = ("matched_text", "soft_joint", "feasible_tools")


def after_timeout(execution, records, interface):
    """Recover the actual next public observation, never rebuild private truth."""
    positions = [i for i, s in enumerate(execution["steps"])
                 if s["action"] == "publish" and s["response"].get("error") == "timeout"]
    if not positions:
        return {"available": False, "reason": "fault_not_activated"}
    k = positions[0]
    # In the selected unassisted 1.0.55 traces, every prior decision is executed.
    require(all(d["kind"] == "tool_action" for d in execution["decisions"][:k + 1]), "prefix contains an unexecuted prior decision")
    if len(execution["dispatch"]) <= k + 1:
        return {"available": False, "reason": "no_recorded_post_fault_decision"}
    event, decision = execution["dispatch"][k + 1], execution["decisions"][k + 1]
    record = records[event["journal_index"]]
    if record["category"] != "received":
        return {"available": False, "reason": "post_fault_provider_missingness"}
    view = json.loads(record["request_body"]["messages"][1]["content"])
    reverse = {v: k for k, v in INTERFACES[interface].items()}
    canonical = copy.deepcopy(view)
    for field in ("decision_support", "read_tool_contracts", "action_schema"):
        canonical.pop(field, None)
    # Restore the original full namespace for comparison, not for model input.
    # Business parameters and response values are left byte-for-byte JSON-equal.
    canonical["tools"] = copy.deepcopy(execution["public_input"]["tools"])
    for step in canonical["history"]:
        step["action"] = reverse[step["action"]]
    require(set(canonical) == set(execution["public_input"]), "unexpected public view extension")
    require(fingerprint(canonical) == decision["public_observation_sha256"] == event["canonical_observation_sha256"], "canonical post-fault prefix mismatch")
    expected = [{name: s[name] for name in ("action", "params", "response")} for s in execution["steps"][:k + 1]]
    require(canonical["history"] == expected and fingerprint(view) == event["view_sha256"], "public prefix history mismatch")
    return {"available": True, "public_prefix_sha256": fingerprint(canonical), "public_observation": canonical,
            "source_journal_index": event["journal_index"], "next_original_proposal": decision["proposal"],
            "frozen_public_rule_proposal": choose(copy.deepcopy(canonical), "task_semantic"),
            "continuation_requests": sum(records[e["journal_index"]]["request_sent"] for e in execution["dispatch"][k + 1:]),
            "continuation_tokens": sum(records[e["journal_index"]].get("raw_response", {}).get("usage", {}).get("total_tokens", 0)
                                       for e in execution["dispatch"][k + 1:]),
            "rule_query_kind": "one offline public-rule decision; no execution, oracle input or new model call"}


def summarize(rows):
    index = {}
    for row in rows:
        key = (row["task_id"], row["interface"], row["arm"])
        require(key not in index, "duplicate planned exposure unit")
        require(row["arm"] in ARMS, "unexpected screen arm")
        require(all(type(row[k]) is bool for k in ("activated", "safe_escalation", "task_completed")), "missing or invalid screen outcome")
        index[key] = row
    units = sorted({(r["task_id"], r["interface"]) for r in rows})
    require(all((task, interface, arm) in index for task, interface in units for arm in ARMS), "unpaired planned exposure unit")
    totals = []
    for arm in ARMS:
        selected = [r for r in rows if r["arm"] == arm]
        active = [r for r in selected if r["activated"]]
        totals.append({"arm": arm, "planned": len(selected), "activated": len(active),
                       "safe_escalations_all_planned": sum(r["safe_escalation"] for r in selected),
                       "safe_escalations_after_activation": sum(r["safe_escalation"] for r in active),
                       "task_completed": sum(r["task_completed"] for r in selected),
                       "post_fault_prefix_available": sum(r["prefix"]["available"] for r in active),
                       "first_post_fault_actions": dict(Counter(r["prefix"]["next_original_proposal"]["action"] for r in active if r["prefix"]["available"]))})
    pairs = []
    for a, b in (("matched_text", "soft_joint"), ("soft_joint", "feasible_tools")):
        counts = Counter(planned_pairs=0, both_activated=0, exact_prefix_pairs=0,
                         activation_differs=0, different_or_missing_prefix=0,
                         escalation_increased_on_exact_prefix=0, escalation_decreased_on_exact_prefix=0,
                         completion_increased_on_exact_prefix=0, completion_decreased_on_exact_prefix=0)
        counts.update(immediate_escalation_increased_on_exact_prefix=0, immediate_escalation_decreased_on_exact_prefix=0,
                      left_continuation_requests_on_exact_prefix=0, right_continuation_requests_on_exact_prefix=0,
                      left_continuation_tokens_on_exact_prefix=0, right_continuation_tokens_on_exact_prefix=0)
        details = []
        for task, interface in units:
            left, right = index[(task, interface, a)], index[(task, interface, b)]
            counts["planned_pairs"] += 1
            counts["activation_differs"] += left["activated"] != right["activated"]
            if left["activated"] and right["activated"]:
                counts["both_activated"] += 1
                matched = (left["prefix"]["available"] and right["prefix"]["available"]
                           and left["prefix"]["public_prefix_sha256"] == right["prefix"]["public_prefix_sha256"])
                counts["exact_prefix_pairs" if matched else "different_or_missing_prefix"] += 1
                if matched:
                    la = left["prefix"]["next_original_proposal"]["action"] == "escalate"
                    ra = right["prefix"]["next_original_proposal"]["action"] == "escalate"
                    counts["immediate_escalation_increased_on_exact_prefix"] += ra and not la
                    counts["immediate_escalation_decreased_on_exact_prefix"] += la and not ra
                    for side, record in (("left", left), ("right", right)):
                        for cost in ("requests", "tokens"):
                            counts[f"{side}_continuation_{cost}_on_exact_prefix"] += record["prefix"]["continuation_" + cost]
                    for metric, label in (("safe_escalation", "escalation"), ("task_completed", "completion")):
                        counts[label + "_increased_on_exact_prefix"] += right[metric] and not left[metric]
                        counts[label + "_decreased_on_exact_prefix"] += left[metric] and not right[metric]
                details.append({"task_id": task, "interface": interface, "exact_prefix": bool(matched),
                                "left_prefix": left["prefix"].get("public_prefix_sha256"), "right_prefix": right["prefix"].get("public_prefix_sha256")})
        pairs.append({"comparison": b + "_vs_" + a, **counts, "pair_details": details})
    return {"totals": totals, "paired_descriptions": pairs,
            "interpretation": "All planned units retained. Activation-conditioned and exact-prefix subsets are post-treatment descriptive diagnostics, not randomized causal estimates or independent tasks."}


def screen(archive, expected_sha):
    checked = audit_archive(archive, expected_sha)
    rows, catalog = [], {}
    with zipfile.ZipFile(archive) as z:
        policy_path = "faultda_bench/semantic/policies.py"
        frozen_policy = z.read("source_snapshot/" + policy_path).decode("utf-8").replace("\r\n", "\n")
        require((REPO / policy_path).read_text(encoding="utf-8") == frozen_policy, "public rule changed since the source freeze")
        runs = json.loads(z.read("runs.json"))
        records = [json.loads(line) for line in z.read("requests.jsonl").decode("utf-8").splitlines()]
        for row in runs:
            if row["variant"] != "lost_repair_receipt" or row["arm"] == "rule_only":
                continue
            execution = json.loads(z.read(row["evidence"]))
            vector = classify(execution)
            prefix = after_timeout(execution, records, row["interface"])
            if prefix["available"]:
                observation = prefix.pop("public_observation")
                catalog[prefix["public_prefix_sha256"]] = observation
            rows.append({"task_id": row["task_id"], "interface": row["interface"], "arm": row["arm"],
                         "source_run_id": row["run_id"], "source_execution_sha256": row["evidence_sha256"],
                         "activated": vector["repair_receipt_fault"]["activated"], "task_completed": vector["task_completed"],
                         "safe_escalation": vector["terminal_decision"]["label"] == "safe_escalation", "prefix": prefix})
    require(len(rows) == 18, "unexpected planned screen coverage")
    decision_records = [r["prefix"] for r in rows if r["prefix"]["available"]]
    result = {"version": "1.0.65", "date": "2026-10-25", "new_api_calls": 0, "new_task_families": 0,
            "new_model_trajectories": 0, "source_archive_sha256": expected_sha,
            "source_responses_reparsed": checked["original_responses_reparsed"],
            "frozen_public_rule_lf_sha256": hashlib.sha256(frozen_policy.encode("utf-8")).hexdigest(),
            "unique_public_prefixes": len(catalog), "post_fault_records": len(decision_records),
            "public_rule_escalation_proposals": sum(p["frozen_public_rule_proposal"]["action"] == "escalate" for p in decision_records),
            **summarize(rows), "rows": rows, "prefix_catalog": catalog,
            "screen_decision": "NO-GO for a new recovery-algorithm or calibrated-abstention claim on current evidence; no independent generalization or causal novelty established.",
            "limitations": ["Retrospective development-data screen, not preregistered confirmation.",
                            "Public-rule queries are decisions only, not new end-to-end executions or optimality proofs.",
                            "Equal public prefixes do not imply equal interface views or equal total computation.",
                            "Activation-conditioned rates cannot replace the full planned-unit outcomes.",
                            "No claim that another paper's experiments are invalid or that its authors omitted activation controls."]}
    for comparison in result["paired_descriptions"]:
        for pair in comparison["pair_details"]:
            if not pair["exact_prefix"]:
                if pair["left_prefix"] in catalog and pair["right_prefix"] in catalog:
                    pair["public_differences"] = differences(catalog[pair["left_prefix"]], catalog[pair["right_prefix"]])
                else:
                    pair["public_differences"] = None
    return result


def differences(left, right, path="$"):
    """Expose differences instead of silently normalizing business identifiers."""
    if type(left) is not type(right):
        return [{"path": path, "left": left, "right": right}]
    if isinstance(left, dict):
        result = []
        for name in sorted(set(left) | set(right)):
            if name not in left or name not in right:
                result.append({"path": path + "." + name, "left_present": name in left, "right_present": name in right})
            else:
                result.extend(differences(left[name], right[name], path + "." + name))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [{"path": path + ".length", "left": len(left), "right": len(right)}]
        return [d for i, (a, b) in enumerate(zip(left, right, strict=True)) for d in differences(a, b, path + f"[{i}]")]
    return [] if left == right else [{"path": path, "left": left, "right": right}]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--archive", type=Path, default=Path("research/reliability_reset/evidence/1.0.55/deepseek-feasible-interface-1.0.55.zip"))
    args = parser.parse_args()
    expected = json.loads(args.archive.with_name("PUBLIC_RECORD.json").read_text(encoding="utf-8"))["sha256"]
    result = screen(args.archive, expected)
    save(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("rows", "prefix_catalog")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
