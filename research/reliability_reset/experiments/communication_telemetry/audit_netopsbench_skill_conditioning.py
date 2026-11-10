"""Audit skill content and tool use in a frozen NetOpsBench ATIF trace set."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-root", type=Path, required=True)
    parser.add_argument("--case-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.case_audit.open(encoding="utf-8-sig", newline="") as stream:
        cases = list(csv.DictReader(stream))
    traces = {path.parent.name: path for path in args.trace_root.rglob("trajectory-*.atif.json")}
    rows = []
    skill_hashes: set[str] = set()
    for case in cases:
        case_id = case["case_id"]
        if case_id not in traces:
            raise SystemExit(f"Missing ATIF trace for {case_id}")
        trace = json.loads(traces[case_id].read_text(encoding="utf-8"))
        skill_texts: list[str] = []
        tool_names: list[str] = []
        observation_texts: list[str] = []
        for step in trace.get("steps", []):
            calls = step.get("tool_calls", [])
            for call in calls:
                name = call.get("function_name", "")
                tool_names.append(name)
                if name != "read_file" or call.get("arguments", {}).get("file_path") != "/skills/network-diagnosis/SKILL.md":
                    continue
            for result in (step.get("observation") or {}).get("results", []):
                content = result.get("content", "")
                try:
                    decoded = json.loads(content)
                except (TypeError, json.JSONDecodeError):
                    observation_texts.append(str(content))
                    continue
                observation_texts.append(json.dumps(decoded, ensure_ascii=False))
                if any(call.get("function_name") == "read_file" and call.get("arguments", {}).get("file_path") == "/skills/network-diagnosis/SKILL.md" for call in calls):
                    text = decoded.get("content", "")
                    if isinstance(text, str):
                        skill_texts.append(text)

        skill = "\n".join(skill_texts)
        skill_hash = hashlib.sha256(skill.encode("utf-8")).hexdigest() if skill else ""
        bad_peer_as_visible = "bad peer as" in "\n".join(observation_texts).lower()
        if skill_hash:
            skill_hashes.add(skill_hash)
        scenario_family = re.sub(
            r"_(?:xs|small|medium|large|xlarge|fat-tree-k8|fat-tree-k12)_\d+$",
            "",
            case["scenario_id"],
        )
        rows.append(
            {
                "case_id": case_id,
                "scenario_family": scenario_family,
                "scale": case["scale"],
                "ground_truth_healthy": case["ground_truth_healthy"],
                "agent_correct_verdict": case["agent_correct_verdict"],
                "rule_correct_verdict": case["rule_correct_verdict"],
                "skill_read": bool(skill),
                "skill_sha256": skill_hash,
                "skill_mentions_bgp_label": "bgp_neighbor_misconfig" in skill,
                "skill_mentions_blackhole_label": "blackhole_route" in skill,
                "skill_gives_bgp_peer_check": "get_bgp_neighbor" in skill and "remote-AS" in skill,
                "skill_gives_bgp_location_rule": "location.device" in skill and "remote-AS" in skill,
                "bad_peer_as_visible": bad_peer_as_visible,
                "bad_peer_as_rule_correct": bad_peer_as_visible == (case["ground_truth_healthy"] == "False"),
                "tools_used": ";".join(sorted(set(tool_names))),
                "tool_call_count": len(tool_names),
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_family[str(row["scenario_family"])].append(row)
    summary = {
        "case_count": len(rows),
        "trace_count": len(traces),
        "cases_without_skill_read": sum(not row["skill_read"] for row in rows),
        "unique_skill_sha256_count": len(skill_hashes),
        "skill_sha256_values": sorted(skill_hashes),
        "bad_peer_as_trigger_rule": {
            "positive_predictions": sum(bool(row["bad_peer_as_visible"]) for row in rows),
            "true_positive": sum(bool(row["bad_peer_as_visible"]) and row["ground_truth_healthy"] == "False" for row in rows),
            "false_positive": sum(bool(row["bad_peer_as_visible"]) and row["ground_truth_healthy"] == "True" for row in rows),
            "false_negative": sum(not bool(row["bad_peer_as_visible"]) and row["ground_truth_healthy"] == "False" for row in rows),
            "true_negative": sum(not bool(row["bad_peer_as_visible"]) and row["ground_truth_healthy"] == "True" for row in rows),
        },
        "families": {
            family: {
                "n": len(group),
                "skill_read_n": sum(bool(row["skill_read"]) for row in group),
                "bgp_label_visible_n": sum(bool(row["skill_mentions_bgp_label"]) for row in group),
                "bgp_peer_guidance_visible_n": sum(bool(row["skill_gives_bgp_peer_check"]) for row in group),
                "agent_correct_n": sum(row["agent_correct_verdict"] == "True" for row in group),
                "one_bit_rule_correct_n": sum(row["rule_correct_verdict"] == "True" for row in group),
                "bad_peer_as_rule_hit_n": sum(bool(row["bad_peer_as_visible"]) for row in group),
                "bad_peer_as_rule_correct_n": sum(bool(row["bad_peer_as_rule_correct"]) for row in group),
            }
            for family, group in sorted(by_family.items())
        },
    }
    summary_path = args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
