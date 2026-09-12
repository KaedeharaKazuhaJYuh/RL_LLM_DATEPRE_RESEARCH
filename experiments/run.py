import argparse, json
from pathlib import Path
from agent.state import RunState
from agent.policy import Policy
from agent.tools import execute_tool
from verifier import verify
from agent.llm import LLMClient
from agent.contracts import actions_from_contract
from agent.features import extract_dataset_features

def load_tasks(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def load_gold(path="tasks/gold_answers.json"):
    p=Path(path); return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def load_references(path="tasks/reference_outputs.json"):
    p=Path(path); return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def validation_for(task_id):
    n=int(task_id[1:])
    if n<=10: return {}
    groups=[("aggregation",12,15),("statistics",16,20),("time_series",21,25),("visualization",26,30),("features",31,35),("modeling",36,40),("decision",41,45),("robustness",46,50)]
    for op,lo,hi in groups:
        if lo<=n<=hi:
            fields={"aggregation":["monthly_sum","rows","columns"],"statistics":["numeric_summary","rows","columns"],"time_series":["time_column","ordered"],"visualization":["recommended_chart","x_candidates"],"features":["feature_candidates"],"modeling":["target_candidates","numeric_features"],"decision":["recommendation_basis"],"robustness":["recovery_checks"]}[op]
            return {"operation":op,"required_analysis":fields}
    return {}

def deterministic_action(task):
    prompt = task["prompt"]
    if "字段类型" in prompt or "行列数" in prompt: return "profile_schema"
    if "缺失率最高" in prompt: return "profile_missingness"
    if "类别的频数" in prompt: return "count_categories"
    if "重复行" in prompt: return "deduplicate"
    if "基本统计量" in prompt: return "describe_numeric"
    if "日期格式" in prompt: return "normalize_dates"
    if "异常值" in prompt: return "clip_outliers"
    if "缺失" in prompt and "最高" not in prompt: return "fill_missing"
    if "类别拼写" in prompt: return "normalize_categories"
    if int(task["task_id"][1:]) >= 12: return "task_analysis"
    if "按月份统计收入" in prompt: return "aggregate"
    return "stop"

LLM_ACTIONS = [
    "profile_schema", "profile_missingness", "count_categories", "deduplicate",
    "describe_numeric", "normalize_dates", "clip_outliers", "fill_missing",
    "normalize_categories", "aggregate", "task_analysis", "stop",
]

def allowed_llm_actions(task, task_action_mask=False, contract_action_mask=False):
    if contract_action_mask:
        return actions_from_contract(task) or ["stop"]
    if task_action_mask and int(task["task_id"][1:]) <= 11:
        return [deterministic_action(task)]
    return LLM_ACTIONS

def run_task(task, policy=None, llm=None, contract_protection=True, task_action_mask=False, contract_action_mask=False, run_metadata=None):
    # Read-only preflight profile. It is recorded as environment state, not an agent tool call.
    x=extract_dataset_features(task["dataset"]["uri"], task["difficulty"])
    state=RunState(task["task_id"], x, remaining_calls=task["constraints"]["max_tool_calls"])
    trace=[]; result={"answer": None, "evidence": []}; bandit_state=None; bandit_action=None
    while not state.done and state.remaining_calls>0:
        if llm:
            allowed_actions = allowed_llm_actions(task, task_action_mask, contract_action_mask)
            choice=llm.choose_action(task, state, allowed_actions)
            action=choice.get("action","stop")
            if action not in set(allowed_actions): action="stop"
            # Protect task contracts: later benchmark groups require task_analysis.
            if contract_protection and int(task["task_id"][1:]) >= 12 and action != "task_analysis": action="task_analysis"
        elif policy and policy.mode == "bandit":
            bandit_state = state.features.copy()
            bandit_action = policy.select(state)
            action = bandit_action
            if contract_protection and int(task["task_id"][1:]) >= 12 and action != "task_analysis": action="task_analysis"
        else:
            action=deterministic_action(task)
        if action == "stop": break
        tool=action if action in {"aggregate","profile_missingness","count_categories","deduplicate","describe_numeric","normalize_dates","clip_outliers","fill_missing","normalize_categories","task_analysis"} else "load_table" if action == "profile_schema" else action
        try:
            obs=execute_tool(tool,{"uri":task["dataset"]["uri"],"task_id":task["task_id"],"prompt":task["prompt"]})
            trace.append({"tool":tool,"action":action,"ok":True}); result["evidence"].append(obs)
            if action=="profile_schema": result["answer"]=obs["columns"]
            if action=="aggregate": result["answer"]=obs["totals"]
            if action in {"profile_missingness","count_categories","deduplicate","describe_numeric"}: result["answer"]=obs
            if action in {"normalize_dates","clip_outliers","fill_missing","normalize_categories"}: result["answer"]=obs
            if action == "task_analysis": result["answer"]=obs["operation"]; result["analysis"]=obs
            state.observe(action,obs)
            if action in {"profile_schema","aggregate","profile_missingness","count_categories","deduplicate","describe_numeric","normalize_dates","clip_outliers","fill_missing","normalize_categories","task_analysis"}: state.done=True
        except Exception as exc:
            trace.append({"tool":tool,"action":action,"ok":False,"error":str(exc)}); state.observe(action,{"error":str(exc)})
    checked=verify(result, task.get("gold",{}), trace, {**task["constraints"],"allowed_tools":task["allowed_tools"],"validation":validation_for(task["task_id"]),"reference":task.get("_reference",{})})
    if policy and policy.mode == "bandit" and bandit_action and bandit_state is not None:
        policy.update(bandit_action, bandit_state, checked["score"])
    record={"task_id":task["task_id"],"score":checked["score"],"passed":checked["passed"],"tool_calls":len(trace),"trace":trace,"checks":checked["checks"]}
    if run_metadata: record["run_metadata"]=run_metadata
    return record

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tasks",default="tasks/tasks.jsonl"); ap.add_argument("--mode",choices=["rule","bandit","llm"],default="rule"); ap.add_argument("--out",default="reports/results.jsonl"); ap.add_argument("--limit",type=int,default=0); ap.add_argument("--gold",default="tasks/gold_answers.json"); ap.add_argument("--references",default="tasks/reference_outputs.json"); ap.add_argument("--no-contract-protection",action="store_true"); ap.add_argument("--task-action-mask",action="store_true"); ap.add_argument("--contract-action-mask",action="store_true"); ap.add_argument("--seed",type=int,default=42); ap.add_argument("--temperature",type=float,default=None); args=ap.parse_args()
    if args.task_action_mask and args.contract_action_mask: ap.error("choose only one action-mask condition")
    actions=["profile_schema","profile_missingness","count_categories","deduplicate","describe_numeric","normalize_dates","clip_outliers","fill_missing","normalize_categories","aggregate","task_analysis","stop"]
    policy=Policy(actions,mode=args.mode,seed=args.seed) if args.mode != "llm" else None
    llm=LLMClient(temperature=args.temperature) if args.mode == "llm" else None
    run_metadata={"mode":args.mode,"run_index":args.seed,"contract_protection":not args.no_contract_protection,"task_action_mask":args.task_action_mask,"contract_action_mask":args.contract_action_mask,"tasks_path":args.tasks,"gold_path":args.gold,"references_path":args.references,"state_profile":"dataset_profile_v1_read_only"}
    if llm: run_metadata.update({"provider":llm.provider,"model":llm.model,"temperature":llm.temperature,"replicate_label":args.seed})
    tasks=load_tasks(args.tasks); gold=load_gold(args.gold); references=load_references(args.references)
    for t in tasks:
        if t["task_id"] in gold: t["gold"].update(gold[t["task_id"]])
        if t["task_id"] in references: t["_reference"] = references[t["task_id"]]
    tasks=tasks[:args.limit] if args.limit else tasks
    results=[]
    for i,t in enumerate(tasks,1):
        print(f"running {i}/{len(tasks)} {t['task_id']}", flush=True)
        results.append(run_task(t,policy,llm,not args.no_contract_protection,args.task_action_mask,args.contract_action_mask,run_metadata))
    p=Path(args.out); p.parent.mkdir(exist_ok=True); p.write_text("\n".join(json.dumps(r) for r in results)+"\n",encoding="utf-8"); print(f"completed {len(results)} tasks; passed={sum(r['passed'] for r in results)}")
if __name__ == "__main__": main()

