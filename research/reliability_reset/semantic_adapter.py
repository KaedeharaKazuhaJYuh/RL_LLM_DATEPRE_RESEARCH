"""Run one historical group task through real CSV/SQLite tools, offline.

Both arms are programmatic development controls. No model results or held-out tasks.
"""

import argparse
import copy
import hashlib
import json
import shutil
import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from collections import Counter

from faultda_bench.semantic.environment import SemanticEnv, TOOLS
from faultda_bench.semantic.oracle import evaluate as original_evaluate
from faultda_bench.semantic.policies import choose
from faultda_bench.semantic.tasks import load

from .audit import digest, require
from . import __version__
from .semantic_facts import extract, rows_from_database


REPO = Path(__file__).resolve().parents[2]
CASES = {
    "healthy": {},
    "environment_error_repaired": {"semantic_fault": True},
    "publication_intervention": {},
    "duplicate_intervention": {},
    "version_intervention": {},
    "incorrect_final_intervention": {},
    "missing_value_boundary": {},
    "timeout_before_commit": {"commit_fault": True, "boundary": "before_commit"},
    "timeout_after_commit": {"commit_fault": True, "boundary": "after_commit"},
    "repair_ack_lost": {"semantic_fault": True, "commit_fault": True, "repair_ack_loss": True},
    "public_state_unknown": {"commit_fault": True, "evidence": "E2"},
    "capture_incomplete": {},
}


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.exists(), f"refusing to overwrite {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    return path


def run_episode(task, folder, case, system):
    env = SemanticEnv(task, folder, budget=6, **CASES[case])
    origin = "public_rule_program" if system == "public_rule" else "scripted_stress_program"
    capture = {"initial_records": rows_from_database(env.db), "initial_feedback": env.initial,
               "initialization": {"actor": "environment_setup", "origin": "environment_initialization",
                                  "feedback": env.initial, "initial_record_count": len(rows_from_database(env.db)),
                                  "scope": "environment_attempt_not_subject_action"},
               "driver_origin": origin, "capture_complete": True, "steps": []}
    initial_public = env.observation()

    def step(action, params=None):
        before = rows_from_database(env.db)
        env.step(action, params)
        history = env.history[-1]
        capture["steps"].append({"index": len(capture["steps"]), "actor": "subject", "actor_kind": "programmatic_driver", "origin": origin,
                                 **history, "before": before, "after": rows_from_database(env.db)})
        return history["response"]

    interventions = ("publication_intervention", "duplicate_intervention", "version_intervention", "incorrect_final_intervention")
    if case in interventions and system == "scripted_stress":
        inspection = step("inspect")
        revision = inspection["revision"]
        # Deliberately wrong then correct, using the same public tools and caps.
        version = inspection["catalog"]["snapshot"]
        rounds = (1,) if case == "incorrect_final_intervention" else (1, 2)
        for number in rounds:
            first = number == 1
            selected_version = inspection["catalog"]["latest"] if first and case == "version_intervention" else version
            deduplicate = not (first and case in ("publication_intervention", "incorrect_final_intervention"))
            mode = "append" if first and case == "duplicate_intervention" else "replace"
            staged = step("stage", {"version": selected_version, "deduplicate_keys": deduplicate, "closed": "left"})
            published = step("publish", {"stage_id": staged["stage_id"], "request_id": f"operation-{number}",
                                         "mode": mode, "expected_revision": revision})
            require(published.get("ok"), "controlled publication failed")
            revision = published["revision"]
            step("inspect")
        step("stop")
    else:
        while not env.terminal:
            observation = json.loads(json.dumps(env.observation()))
            action = choose(observation, "task_semantic")
            step(action["action"], action.get("params"))
    capture["terminal"] = env.terminal
    capture["reported_terminal"] = env.terminal
    if case == "capture_incomplete":
        # Explicit capture-loss control, not a claim that an omission was observed.
        capture["steps"] = capture["steps"][:1]
        capture["capture_complete"] = False
        capture["terminal"] = None
        capture["capture_limitation"] = "deliberately retained first step only; control"
    return env, capture, initial_public


def build(output):
    output = Path(output).resolve()
    require(not output.exists(), "adapter destination must be new")
    output.mkdir(parents=True)
    task = next(t for t in load() if t["id"] == "group-01")
    task = copy.deepcopy(task)
    # Explicit new engineering derivative: the historical manifest is untouched.
    task["versions"]["v2"][0]["value"] = str(Decimal(task["versions"]["v2"][0]["value"]) + Decimal(1))
    upstream = REPO / task["source_path"]
    require(digest(upstream) == task["source_sha256"], "historical source changed")
    task_manifest = REPO / "faultda_bench/protocols/semantic_tasks_v1.json"
    attribution = json.loads(task_manifest.read_text(encoding="utf-8"))["attribution"][task["source_id"]]
    contract = save(output / "contract.json", {"subject_actor": "subject",
        "subject_kind": "programmatic_driver",
        "forbidden_rules": ["incorrect_publication", "duplicate_active_reports"],
        "assessment_integrity_monitors": ["input_hash_consistency"],
        "task_contract": task["contract"],
        "termination_policy": "Evidence of supported termination is audited separately; an unsupported stop alone does not introduce a new contract violation. The original public task contract is unchanged.",
        "responsibility": "Environment initialization is not a current-subject action. The subject is a programmatic driver, not an LLM."})

    def ref(path):
        return {"path": path.relative_to(output).as_posix(), "sha256": digest(path)}

    manifest = {"schema_version": 1, "producer_version": __version__, "study_kind": "development", "run_origin": "programmatic_adapter_validation",
        "system_roles": {"public_rule": "existing public-observation rule", "scripted_stress": "deliberate fault control, not a model"},
        "families": {"historical_group_publication": {
            "lineage": {"source": task["source_id"], "task": task["id"], "split": "historical_development",
                        "source_sha256": task["source_sha256"], "task_manifest_sha256": digest(task_manifest),
                        "selection": task["selection"], "transformations": "Engineering derivative: existing eight-row slice and generated keys; v2 first value +1; missing_value_boundary blanks second value in both versions; synthetic workflow interventions. Not new source data."},
            "license": attribution, "independence_status": "pending"}}, "runs": []}
    (output / "native").mkdir()
    for case in CASES:
        instance_task = copy.deepcopy(task)
        if case == "missing_value_boundary":
            for version in instance_task["versions"]:
                instance_task["versions"][version][1]["value"] = ""
        public = None
        for system in ("public_rule", "scripted_stress"):
            run_id = f"{case}--{system}"
            env, capture, observation = run_episode(instance_task, output / "native" / run_id, case, system)
            capture["run_id"] = run_id
            original = original_evaluate(env)
            if public is None:
                public = save(output / "inputs" / (case + ".json"), observation)
            else:
                require(json.loads(public.read_text(encoding="utf-8")) == observation, "unmatched initial public observation")
            raw = output / "evidence" / run_id
            raw.mkdir(parents=True)
            spec = {"analysis": instance_task["contract"], "dimension": instance_task["dimension"], "catalog": instance_task["catalog"],
                    "initial_input_hashes": env.task["version_hashes"], "attribution": attribution}
            save(raw / "spec.json", spec)
            save(raw / "native_trace.json", capture)
            shutil.copyfile(upstream, raw / "upstream.csv")
            for version in task["versions"]:
                shutil.copyfile(env.folder / (version + ".csv"), raw / (version + ".csv"))
            with closing(sqlite3.connect(env.db)) as source, closing(sqlite3.connect(raw / "ledger.sqlite")) as target:
                source.backup(target)
            attachment_paths = [raw / name for name in ("spec.json", "native_trace.json", "upstream.csv", "v1.csv", "v2.csv", "ledger.sqlite")]
            attachments = [ref(p) for p in attachment_paths]
            facts, state_payload = extract(raw, run_id)
            trace = save(output / "runs" / run_id / "trace.json", {"run_id": run_id, "evidence": {},
                "native_trace_sha256": digest(raw / "native_trace.json"), "capture_complete": capture["capture_complete"],
                "terminal": facts["termination_action"], "reported_terminal": capture["reported_terminal"],
                "source": "attached native_trace.json; subject origin explicitly programmatic"})
            state = save(output / "runs" / run_id / "state.json", state_payload)
            binding = {"run_id": run_id, "public_input_sha256": digest(public), "contract_sha256": digest(contract)}
            outcome = save(output / "runs" / run_id / "outcome.json", {**binding,
                "implementation_id": "faultda_bench.semantic.oracle.evaluate:contract_complete",
                "evidence_origin": "unchanged_legacy_oracle", "success": original["contract_complete"],
                "original_result": original})
            fact_file = save(output / "runs" / run_id / "facts.json", {**binding, **facts,
                "implementation_id": f"reliability_reset.semantic_facts:{__version__}:Fraction+SQLite",
                "evidence_origin": "attached_CSV_SQLite_step_capture", "trace_sha256": digest(trace),
                "state_sha256": digest(state), "attachments_sha256": {r["path"]: r["sha256"] for r in attachments}})
            signature_data = {"steps": [{k: s[k] for k in ("actor", "action", "params", "response")} for s in capture["steps"]],
                              "records": state_payload["records"], "terminal": facts["termination_action"]}
            signature = hashlib.sha256(json.dumps(signature_data, sort_keys=True).encode()).hexdigest()
            manifest["runs"].append({"run_id": run_id, "family": "historical_group_publication",
                "task_id": task["id"] + ":" + case, "system": system, "seed": "0",
                "outcome": ref(outcome), "facts": ref(fact_file), "trace": ref(trace), "state": ref(state),
                "public_input": ref(public), "contract": ref(contract), "attachments": attachments,
                "tools": sorted(TOOLS), "budget": {"checks": 6, "mutations": 6, "decisions": 16},
                "behavior_signature": signature,
                "observed_behavior": {"subject_publications": sum(s["action"] == "publish" and len(s["after"]) > len(s["before"]) for s in capture["steps"]),
                                      "captured_steps": len(capture["steps"]), "termination_action": facts["termination_action"]},
                "usage": {k: env.cost[k] for k in ("checks", "mutations", "decisions")}})
    return save(output / "bundle.json", manifest)


def validation_summary(bundle):
    """Agreement on engineered controls, with class balance and repeated paths."""
    from .audit import audit
    bundle = Path(bundle)
    result = audit(bundle)
    manifest = json.loads(bundle.read_text(encoding="utf-8"))
    indexed = {row["run_id"]: row for row in result["runs"]}
    confusion = Counter({"true_positive": 0, "true_negative": 0, "false_positive": 0, "false_negative": 0, "unknown": 0})
    terminal_known = terminal_agree = snapshot_known = snapshot_agree = 0
    signatures, positive_rules = {}, {}
    for run in manifest["runs"]:
        row = indexed[run["run_id"]]
        old = json.loads((bundle.parent / run["outcome"]["path"]).read_text(encoding="utf-8"))["original_result"]
        facts = json.loads((bundle.parent / run["facts"]["path"]).read_text(encoding="utf-8"))
        contract = json.loads((bundle.parent / run["contract"]["path"]).read_text(encoding="utf-8"))
        expected, observed = old["forbidden_effect"], row["confirmed_violation"]
        if observed is None:
            key = "unknown"
        elif observed:
            key = "true_positive" if expected else "false_positive"
        else:
            key = "false_negative" if expected else "true_negative"
        confusion[key] += 1
        if row["terminal_correct"] is not None:
            terminal_known += 1
            terminal_agree += int(row["terminal_correct"] == old["terminal_correct"])
        if row["snapshot_correct"] is not None:
            snapshot_known += 1
            snapshot_agree += int(row["snapshot_correct"] == old["terminal_correct"])
        signatures.setdefault(run["behavior_signature"], []).append(run["run_id"])
        for rule in contract["forbidden_rules"]:
            positive_rules.setdefault(rule, set())
        for event in facts["events"]:
            if event["actor"] == contract["subject_actor"] and event["violated"] is True and event["confirmed"]:
                positive_rules[event["rule"]].add(run["run_id"])
    known = len(indexed) - confusion["unknown"]
    return {"executions": len(indexed), "family_count": 1, "independent_sample_size": None,
            "unique_behavior_signatures": len(signatures), "behavior_groups": list(signatures.values()),
            "outcome_successes": sum(r["outcome_success"] for r in result["runs"]),
            "violation_agreement_with_legacy": dict(confusion),
            "always_negative_agreement_on_known": (confusion["true_negative"] + confusion["false_positive"]) / known if known else None,
            "terminal_comparable": terminal_known, "terminal_agree": terminal_agree,
            "terminal_unknown": len(indexed) - terminal_known,
            "snapshot_comparable": snapshot_known, "snapshot_agree": snapshot_agree,
            "snapshot_unknown": len(indexed) - snapshot_known,
            "snapshot_labels": dict(Counter(str(r["snapshot_correct"]) for r in result["runs"])),
            "positive_rule_execution_counts": {k: len(v) for k, v in positive_rules.items()},
            "note": "Legacy-relative engineering agreement on designed controls; no independent accuracy, power or generalization estimate."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(build(args.output))
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
