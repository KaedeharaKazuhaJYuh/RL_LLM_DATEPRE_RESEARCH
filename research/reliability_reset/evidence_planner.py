"""Small exact evidence-cover planner over public read-tool contracts.

This module selects evidence queries, never numeric answers or publication actions.
"""

import copy
import itertools
import re

from faultda_bench.semantic.environment import TOOLS
from .audit import require


IDENTITY = {n: n for n in TOOLS}
OPAQUE = {**IDENTITY, "status": "query_d", "inspect": "query_b", "inputs": "query_a", "catalog": "query_c"}
INTERFACES = {"canonical": IDENTITY, "opaque": OPAQUE}

# Documented E0 capabilities. These metadata are visible to every transfer arm.
E0_CARDS = {
    "status": {"provides": ["ledger_revision", "active_count"], "checks": 1, "estimated_response_bytes": 128},
    "inspect": {"provides": ["ledger_revision", "active_count", "active_reports", "input_rows", "dimension", "version_catalog"],
                "checks": 1, "estimated_response_bytes": 4096},
    "inputs": {"provides": ["input_rows", "dimension"], "checks": 1, "estimated_response_bytes": 3072},
    "catalog": {"provides": ["version_catalog"], "checks": 1, "estimated_response_bytes": 128},
}


def public_view(observation, interface="canonical", structured=False):
    """Alias only action envelopes and tool-description references, not business data."""
    mapping = INTERFACES[interface]
    require(len(set(mapping.values())) == len(mapping), "tool aliases must be bijective")
    view = copy.deepcopy(observation)
    pattern = re.compile(r"\b(" + "|".join(re.escape(n) for n in mapping) + r")\b")
    view["tools"] = {mapping[n]: pattern.sub(lambda m: mapping[m.group()], desc)
                     for n, desc in observation["tools"].items()}
    for event in view["history"]:
        event["action"] = mapping.get(event["action"], event["action"])
    if structured:
        view["read_tool_contracts"] = {mapping[n]: copy.deepcopy(card) for n, card in E0_CARDS.items()}
    return view


def required_evidence(contract):
    fields = {"ledger_revision", "active_count", "active_reports", "input_rows", "version_catalog"}
    if contract["family"] == "group":
        fields.add("dimension")
    return fields


def observed_evidence(history, read_names):
    seen = set()
    # Use only successful read responses. Stage/publish do not verify report state.
    reads = set(read_names)
    names = {"revision": "ledger_revision", "active_count": "active_count", "records": "active_reports",
             "versions": "input_rows", "dimension": "dimension", "catalog": "version_catalog"}
    for event in history:
        response = event["response"]
        if event["action"] in reads and response.get("ok") is True:
            seen.update(label for key, label in names.items() if key in response)
    return seen


def plan_reads(cards, required, observed, budget):
    """Exact set-cover feasibility; lexicographically minimize checks, estimated bytes.

    Byte estimates are declared interface metadata, not measured test-state data.
    Exhaustive enumeration is intentionally limited to a small read-tool registry.
    """
    require(type(budget) is int and budget >= 0 and len(cards) <= 12, "invalid planning budget/registry")
    missing = set(required) - set(observed)
    for card in cards.values():
        require(type(card["checks"]) is int and card["checks"] > 0
                and type(card["estimated_response_bytes"]) is int and card["estimated_response_bytes"] >= 0,
                "invalid public tool cost")
    choices = []
    names = sorted(cards)
    for size in range(len(names) + 1):
        for subset in itertools.combinations(names, size):
            checks = sum(cards[n]["checks"] for n in subset)
            if checks > budget:
                continue
            coverage = set().union(*(set(cards[n]["provides"]) for n in subset))
            if missing <= coverage:
                byte_estimate = sum(cards[n]["estimated_response_bytes"] for n in subset)
                choices.append((checks, byte_estimate, subset))
    if not choices:
        return {"feasible": False, "missing_evidence": sorted(missing), "read_plan": [], "checks": None,
                "estimated_response_bytes": None}
    checks, byte_estimate, subset = min(choices)
    return {"feasible": True, "missing_evidence": sorted(missing), "read_plan": list(subset), "checks": checks,
            "estimated_response_bytes": byte_estimate}


def evidence_plan(view):
    return plan_reads(view["read_tool_contracts"], required_evidence(view["contract"]),
                      observed_evidence(view["history"], view["read_tool_contracts"]), view["remaining"]["checks"])
