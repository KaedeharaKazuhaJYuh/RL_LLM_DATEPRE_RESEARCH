import numpy as np
from agent.router import AgentState, rule_router
from agent.bandit import LinUCBBandit
from agent.contracts import actions_from_contract
from scripts.make_task_variants import make_wording_variant
from scripts.make_value_variant import VALUE_TRANSFORMS
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

def test_wording_variant_preserves_evaluation_fields():
    tasks = [{"task_id":"T01", "prompt":"识别字段类型", "contract":{"required_capabilities":["overview"]}, "dataset":{"uri":"data/sample.csv"}, "gold":{"answer_type":"structured"}, "constraints":{"max_tool_calls":4}}]
    variant = make_wording_variant(tasks)[0]
    assert variant["task_id"] == "T01"
    assert variant["contract"] == tasks[0]["contract"]
    assert variant["dataset"] == tasks[0]["dataset"]
    assert variant["gold"] == tasks[0]["gold"]
    assert variant["prompt"] != tasks[0]["prompt"]

def test_value_variant_transforms_only_declared_numeric_fields():
    assert VALUE_TRANSFORMS["sample.csv"]["revenue"]("100") == "122.00"
    assert VALUE_TRANSFORMS["churn.csv"]["tenure_months"]("3") == "4"
    assert VALUE_TRANSFORMS["students.csv"]["score"]("72") == "74.00"

