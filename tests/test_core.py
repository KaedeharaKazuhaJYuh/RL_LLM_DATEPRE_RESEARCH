import numpy as np
from agent.router import AgentState, rule_router
from agent.bandit import LinUCBBandit
from agent.contracts import actions_from_contract
from scripts.make_task_variants import make_wording_variant
from scripts.make_value_variant import VALUE_TRANSFORMS
from agent.features import extract_dataset_features
from scripts.aggregate_seeds import summarize_labeled_replicates
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

def test_dataset_profile_observes_value_perturbation_without_schema_change():
    original = extract_dataset_features("data/sample.csv", "easy")
    variant = extract_dataset_features("tasks/variants/value_v1/data/sample.csv", "easy")
    assert len(original) == len(variant) == 10
    assert original[:7] == variant[:7]
    assert original[7:9] != variant[7:9]

def test_labeled_replicate_summary_keeps_explicit_order(tmp_path):
    first = tmp_path / "run0.jsonl"
    second = tmp_path / "run1.jsonl"
    first.write_text('{"passed": true, "score": 1.0, "tool_calls": 1}\n', encoding="utf-8")
    second.write_text('{"passed": false, "score": 0.2, "tool_calls": 2}\n', encoding="utf-8")
    summary = summarize_labeled_replicates([first, second], "demo")[0]
    assert summary["replicates"] == 2
    assert summary["pass_rate_mean"] == 0.5
    assert [row["replicate"] for row in summary["replicate_summaries"]] == [0, 1]

