import numpy as np
from agent.router import AgentState, rule_router
from agent.bandit import LinUCBBandit
from verifier import verify

def test_router_prioritizes_missingness():
    assert rule_router(AgentState(missing_rate=.5)) == "profile_missingness"

def test_verifier_accepts_valid_result():
    r = verify({"answer": 10, "evidence": ["computed"]}, {"answer": 10}, [{"tool": "python_exec"}], {"allowed_tools": ["python_exec"]})
    assert r["passed"]

def test_bandit_returns_known_action():
    b = LinUCBBandit(3, ["clean", "aggregate"])
    assert b.select(np.ones(3)) in {"clean", "aggregate"}

