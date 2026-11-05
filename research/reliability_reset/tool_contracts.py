"""Versioned offline input contracts; preserve rejected proposals without repair.

These are local runtime contracts, not an empirical model intervention. Unknown
IDs, stale revisions and wrong analysis choices can pass syntax and fail later.
"""

import copy

from .audit import require
from .evidence_planner import INTERFACES
from .recovery_credit import ControllerStop, fingerprint


CONTRACT_VERSION = "tool-inputs-160-v1"
EMPTY = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}
PARAMETERS = {
    **{name: copy.deepcopy(EMPTY) for name in ("status", "inspect", "inputs", "catalog", "stop", "escalate")},
    "stage": {"type": "object", "required": ["version", "deduplicate_keys", "closed"], "additionalProperties": False,
              "properties": {"version": {"type": "string", "minLength": 1},
                             "deduplicate_keys": {"type": "boolean"}, "closed": {"type": "string", "enum": ["left", "both"]}}},
    "publish": {"type": "object", "required": ["stage_id", "request_id", "expected_revision", "mode"], "additionalProperties": False,
                "properties": {"stage_id": {"type": "string", "minLength": 1},
                               "request_id": {"type": "string", "minLength": 1, "maxLength": 80},
                               "expected_revision": {"type": "integer", "minimum": 0, "x-runtime-type": "python-int-not-bool-or-float"},
                               "mode": {"type": "string", "enum": ["replace", "append"]}}},
}


def schema(interface="canonical", available=None):
    mapping = INTERFACES[interface]
    names = tuple(mapping.values()) if available is None else tuple(available)
    require(names and len(names) == len(set(names)) and set(names) <= set(mapping.values()), "invalid advertised namespace")
    reverse = {v: k for k, v in mapping.items()}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "x-contract-version": CONTRACT_VERSION,
            "oneOf": [{"type": "object", "required": ["action", "params"], "additionalProperties": False,
                       "properties": {"action": {"const": name}, "params": copy.deepcopy(PARAMETERS[reverse[name]])}}
                      for name in names]}


def validate(proposal, interface="canonical", available=None):
    """No coercion, inferred defaults, private task lookup or proposal mutation."""
    mapping = INTERFACES[interface]
    names = tuple(mapping.values()) if available is None else tuple(available)
    require(len(names) == len(set(names)) and set(names) <= set(mapping.values()), "invalid validation namespace")
    reverse = {v: k for k, v in mapping.items()}
    errors = []

    def error(path, code):
        errors.append({"path": path, "code": code})

    if not isinstance(proposal, dict):
        error("$", "object_required")
    else:
        for key in ("action", "params"):
            if key not in proposal:
                error("$." + key, "required")
        for key in proposal:
            if key not in ("action", "params"):
                error("$." + str(key), "additional_property")
        action = proposal.get("action")
        if not isinstance(action, str) or action not in reverse:
            if "action" in proposal:
                error("$.action", "unknown_action")
        else:
            if action not in names:
                error("$.action", "not_currently_advertised")
            if "params" in proposal:
                params = proposal["params"]
                contract = PARAMETERS[reverse[action]]
                if not isinstance(params, dict):
                    error("$.params", "object_required")
                else:
                    for key in contract["required"]:
                        if key not in params:
                            error("$.params." + key, "required")
                    for key, value in params.items():
                        path = "$.params." + str(key)
                        spec = contract["properties"].get(key)
                        if spec is None:
                            error(path, "additional_property")
                            continue
                        kind = spec["type"]
                        valid_type = (isinstance(value, str) if kind == "string" else type(value) is bool if kind == "boolean" else type(value) is int)
                        if not valid_type:
                            error(path, "type_" + kind)
                            continue
                        if "enum" in spec and value not in spec["enum"]:
                            error(path, "enum")
                        if "minLength" in spec and len(value) < spec["minLength"]:
                            error(path, "min_length")
                        if "maxLength" in spec and len(value) > spec["maxLength"]:
                            error(path, "max_length")
                        if "minimum" in spec and value < spec["minimum"]:
                            error(path, "minimum")
    return {"contract_version": CONTRACT_VERSION, "original_proposal": copy.deepcopy(proposal),
            "schema_valid": not errors, "errors": errors,
            "semantic_correctness": "not_checked", "completion_claim": "not_evaluated"}


class PreservingSchemaGate:
    """Explicit opt-in offline adapter. Invalid attempts stop, never get repaired.

    The runner charges the controller decision; no tool or mutation is executed
    on schema rejection. A future live caller must retain its incurred API cost.
    Original proposals remain in events even when the legacy runner records a
    ControllerStop rather than an executed action. Old runners are unchanged.
    """
    def __init__(self, dispatcher):
        self.dispatcher = dispatcher
        self.events = []

    def __call__(self, observation, controller):
        proposal = self.dispatcher(observation, controller)
        checked = validate(proposal)
        self.events.append({"observation_sha256": fingerprint(observation), **checked,
                            "disposition": "forward_unchanged" if checked["schema_valid"] else "schema_rejected"})
        if not checked["schema_valid"]:
            raise ControllerStop("schema_rejected")
        return proposal
