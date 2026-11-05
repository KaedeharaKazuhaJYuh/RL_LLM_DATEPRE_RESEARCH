"""Network-free proposal/outcome audit of the frozen 1.0.55 public archive."""

import argparse
import hashlib
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from .audit import digest, require
from .credit_live import parse_action
from .evidence_planner import INTERFACES
from .outcomes import classify
from .recovery_credit import fingerprint, save
from .tool_contracts import validate


def audit_archive(archive, expected_sha):
    archive = Path(archive)
    require(digest(archive) == expected_sha, "source archive hash mismatch")
    with zipfile.ZipFile(archive) as z:
        require(z.testzip() is None, "source archive CRC mismatch")
        def read(name):
            return json.loads(z.read(name))
        inventory = read("inventory.json")
        require(set(z.namelist()) == set(inventory) | {"inventory.json"}, "source archive inventory membership mismatch")
        for name, sha in inventory.items():
            require(hashlib.sha256(z.read(name)).hexdigest() == sha, "source archive member hash mismatch")
        protocol = read("protocol.json")
        for name, sha in protocol["code_sha256"].items():
            require(hashlib.sha256(z.read("source_snapshot/" + name)).hexdigest() == sha, "frozen runtime snapshot mismatch")
        rows = read("runs.json")
        records = [json.loads(line) for line in z.read("requests.jsonl").decode("utf-8").splitlines()]
        groups, proposals, outcomes, used = defaultdict(Counter), [], [], []
        for row in rows:
            require(hashlib.sha256(z.read(row["evidence"])).hexdigest() == row["evidence_sha256"], "source execution hash mismatch")
            execution = read(row["evidence"])
            require(execution["protocol_sha256"] == hashlib.sha256(z.read("protocol.json")).hexdigest(), "source protocol binding mismatch")
            vector = classify(execution)
            require(vector["task_completed"] == row["assessed_success"], "additive outcome disagrees with historical completion")
            key = (row["variant"], row["arm"])
            counts = groups[key]
            counts.update(executions=1, task_completed=int(vector["task_completed"] is True),
                          safe_escalation=int(vector["terminal_decision"]["label"] == "safe_escalation"),
                          actual_goal_satisfied=int(vector["private_world"]["goal_satisfied"] is True),
                          fault_activated=int(vector["repair_receipt_fault"]["activated"]),
                          tool_rejections=len(vector["rejections"]["tool"]), budget_rejections=len(vector["rejections"]["budget"]))
            for event, decision in zip(execution.get("dispatch", []), execution["decisions"] if row["arm"] != "rule_only" else [], strict=True):
                index = event["journal_index"]
                record = records[index]
                used.append(index)
                require(fingerprint(record) == event["record_sha256"] and event["canonical_observation_sha256"] == decision["public_observation_sha256"], "source response binding mismatch")
                if record["category"] != "received":
                    continue
                require(not record["response_redacted"], "source response requires redaction review")
                proposal, parse_error = parse_action(record["raw_response"], tuple(INTERFACES[row["interface"]].values()))
                require(proposal == record["parsed_action"] == event["advertised_proposal"] and parse_error == record["parse_error"], "source response parsing changed")
                view = json.loads(record["request_body"]["messages"][1]["content"])
                require(fingerprint(view) == event["view_sha256"] == record["observation_sha256"]
                        and fingerprint(record["request_body"]["messages"][0]["content"]) == event["system_prompt_sha256"], "source prompt binding mismatch")
                checked = validate(proposal, row["interface"])
                counts.update(proposals=1, schema_invalid=int(not checked["schema_valid"]))
                proposals.append({"run_id": row["run_id"], "journal_index": index, "request_index": record["request_index"],
                                  "source_parse_error": parse_error, "source_proposal_sha256": fingerprint(proposal), **checked})
            outcomes.append({"run_id": row["run_id"], "task_id": row["task_id"], "arm": row["arm"],
                             "interface": row["interface"], "variant": row["variant"], "source_execution_sha256": row["evidence_sha256"], **vector})
        require(sorted(used) == list(range(len(records))), "unbound or duplicated source response")
        require(len(rows) == 63 and len(proposals) == 207, "unexpected 1.0.55 source coverage")
        return {"version": "1.0.60", "date": "2026-10-25", "new_api_calls": 0, "new_model_trajectories": 0,
                "source_archive": archive.name, "source_archive_sha256": expected_sha,
                "source_inventory_members_verified": len(inventory), "original_model_trajectories": 54,
                "original_shared_rule_executions": 9, "original_responses_reparsed": len(proposals),
                "historical_completion_labels_changed": 0,
                "scope": "Posthoc input-contract and outcome-vector audit; no repaired proposals, counterfactual success claims or empirical efficacy trial.",
                "groups": [{"variant": k[0], "arm": k[1], **v} for k, v in sorted(groups.items())],
                "proposal_checks": proposals, "outcomes": outcomes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--archive", type=Path, default=Path("research/reliability_reset/evidence/1.0.55/deepseek-feasible-interface-1.0.55.zip"))
    parser.add_argument("--record", type=Path, default=Path("research/reliability_reset/evidence/1.0.55/PUBLIC_RECORD.json"))
    args = parser.parse_args()
    expected = json.loads(args.record.read_text(encoding="utf-8"))["sha256"]
    result = audit_archive(args.archive, expected)
    save(args.output, result)
    print(json.dumps({k: v for k, v in result.items() if k not in ("proposal_checks", "outcomes")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
