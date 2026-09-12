import numpy as np
from agent.router import AgentState, rule_router
from agent.bandit import LinUCBBandit
from agent.contracts import actions_from_contract
from verifier import verify

def test_router_prioritizes_missingness():
    assert rule_router(AgentState(missing_rate=.5)) == "profile_missingness"

def test_verifier_accepts_valid_result():
    r = verify({"answer": 10, "evidence": ["computed"]}, {"answer": 10}, [{"tool": "python_exec"}], {"allowed_tools": ["python_exec"]})
    assert r["passed"]

def test_bandit_returns_known_action():
    b = LinUCBBandit(3, ["clean", "aggregate"])
    assert b.select(np.ones(3)) in {"clean", "aggregate"}

def test_contract_mask_uses_declared_capability_and_allowed_tools():
    task = {"contract":{"required_capabilities":["overview"]}, "allowed_tools":["count_categories"]}
    assert actions_from_contract(task) == ["count_categories"]
    task["allowed_tools"] = ["load_table", "profile_missingness"]
    assert actions_from_contract(task) == ["profile_schema", "profile_missingness"]

