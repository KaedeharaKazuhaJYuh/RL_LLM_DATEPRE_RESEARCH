"""Public evidence validity and budget-feasible actions, without numeric grading."""

import copy

from .evidence_planner import E0_CARDS, INTERFACES, observed_evidence, plan_reads, required_evidence


REPORT_FIELDS = {"ledger_revision", "active_count", "active_reports"}
IMMUTABLE_FIELDS = {"input_rows", "dimension", "version_catalog"}
COMPLETION_CONTRACT = (
    "Completion requires a correct report and supported current publication state. "
    "A successful inspection supports the observed report; a successful CAS replace receipt bound to a known "
    "staged candidate supports that candidate's publication, but does not prove its numerical correctness. "
    "An unresolved publication timeout without reconciliation does not support a completion claim. "
    "If adequate evidence cannot be obtained within the remaining budget, escalate."
)


def evidence_state(observation, interface="canonical"):
    """Read envelope-level action history; leave business values and numbers intact.

    Input tables/catalog are immutable in this E0 protocol. Publication invalidates
    old report observations. Only a bound successful replace receipt derives new
    current-report evidence; timeout never borrows the evaluator's actual state.
    """
    mapping = INTERFACES[interface]
    reverse = {v: k for k, v in mapping.items()}
    history = [{**copy.deepcopy(event), "action": reverse.get(event["action"], event["action"])}
               for event in observation["history"]]
    immutable, reports, stages, events = set(), None, {}, []
    unresolved = False
    for index, event in enumerate(history):
        action, params, response = event["action"], event.get("params", {}), event["response"]
        if action in E0_CARDS and response.get("ok") is True:
            fields = observed_evidence([event], E0_CARDS)
            immutable.update(fields & IMMUTABLE_FIELDS)
            if action == "inspect" and {"revision", "active_count", "records"} <= set(response):
                reports = {"source": "inspect", "history_index": index, "revision": response["revision"],
                           "active_count": response["active_count"], "records": copy.deepcopy(response["records"])}
                unresolved = False
            elif action == "status" and reports is not None:
                if response.get("revision") != reports["revision"] or response.get("active_count") != reports["active_count"]:
                    reports = None
                    events.append({"history_index": index, "kind": "status_invalidated_report_cache"})
        elif action == "stage" and response.get("ok") is True and isinstance(response.get("stage_id"), str):
            stages[response["stage_id"]] = {"history_index": index, "candidate": copy.deepcopy(response)}
        elif action == "publish":
            reports = None
            unresolved = True
            events.append({"history_index": index, "kind": "prior_report_evidence_invalidated"})
            expected = params.get("expected_revision")
            stage = stages.get(params.get("stage_id"))
            if (response.get("ok") is True and params.get("mode") == "replace" and stage is not None
                    and type(expected) is int and type(response.get("revision")) is int
                    and response["revision"] == expected + 1):
                candidate = copy.deepcopy(stage["candidate"])
                candidate.pop("ok", None)
                candidate.pop("stage_id", None)
                reports = {"source": "bound_cas_receipt", "history_index": index,
                           "candidate_history_index": stage["history_index"], "revision": response["revision"],
                           "active_count": 1, "records": [{**candidate, "revision": response["revision"], "active": True}]}
                unresolved = False
                events.append({"history_index": index, "kind": "current_report_derived_from_candidate_and_receipt"})
    covered = immutable | (REPORT_FIELDS if reports is not None else set())
    cards = {mapping[n]: copy.deepcopy(card) for n, card in E0_CARDS.items()}
    plan = plan_reads(cards, required_evidence(observation["contract"]), covered, observation["remaining"]["checks"])
    feasible = []
    for canonical, advertised in mapping.items():
        if canonical in E0_CARDS and observation["remaining"]["checks"] <= 0:
            continue
        if canonical in ("stage", "publish") and observation["remaining"]["mutations"] <= 0:
            continue
        feasible.append(advertised)
    return {"supported_current_report": reports is not None and not unresolved,
            "unresolved_publication": unresolved, "current_report_evidence": reports,
            "immutable_evidence_fields": sorted(immutable), "known_stage_ids": sorted(stages),
            "evidence_events": events, "read_plan": plan, "cost_feasible_actions": feasible,
            "numerical_correctness": "not_checked_by_planner",
            "completion_guidance": "Use the analysis contract and actual outputs. Storage confirmation alone does not establish correctness."}


def supported_completion(execution):
    history = [{k: step[k] for k in ("action", "params", "response")} for step in execution["steps"]]
    observation = {**execution["public_input"], "history": history, "remaining": {"checks": 0, "mutations": 0}}
    state = evidence_state(observation)
    supported = state["supported_current_report"]
    return {"protocol_complete": bool(execution["independent_assessment"]["safe_complete"] and supported),
            "unsupported_stop": execution["terminal"] == "stop" and not supported,
            "public_state_supported": supported, "unresolved_publication": state["unresolved_publication"]}
