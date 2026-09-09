import argparse, json
from pathlib import Path
from agent.state import RunState
from agent.policy import Policy
from agent.tools import execute_tool
from verifier import verify
from agent.llm import LLMClient

def load_tasks(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def load_gold(path="tasks/gold_answers.json"):
    p=Path(path); return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def run_task(task, policy=None, llm=None):
    # Initial feature vector: difficulty, rows, missing rate, numeric columns, then padding.
    x=[{"easy":0.0,"medium":0.5,"hard":1.0}[task["difficulty"]], 0.0, 0.0, 2.0]+[0.0]*6
    state=RunState(task["task_id"], x, remaining_calls=task["constraints"]["max_tool_calls"])
    trace=[]; result={"answer": None, "evidence": []}
    while not state.done and state.remaining_calls>0:
        if "字段类型" in task["prompt"] or "行列数" in task["prompt"]: action="profile_schema"
        elif "缺失率最高" in task["prompt"]: action="profile_missingness"
        elif "类别的频数" in task["prompt"]: action="count_categories"
        elif "重复行" in task["prompt"]: action="deduplicate"
        elif "基本统计量" in task["prompt"]: action="describe_numeric"
        elif "按月份统计收入" in task["prompt"]: action="aggregate"
        else: action=(llm.choose_action(task, state, ["profile_schema","profile_missingness","aggregate","stop"])["action"] if llm else policy.select(state))
        if action == "stop": break
        tool=action if action in {"aggregate","profile_missingness","count_categories","deduplicate","describe_numeric"} else "load_table" if action == "profile_schema" else action
        try:
            obs=execute_tool(tool,{"uri":task["dataset"]["uri"]})
            trace.append({"tool":tool,"action":action,"ok":True}); result["evidence"].append(obs)
            if action=="profile_schema": result["answer"]=obs["columns"]
            if action=="aggregate": result["answer"]=obs["totals"]
            if action in {"profile_missingness","count_categories","deduplicate","describe_numeric"}: result["answer"]=obs
            state.observe(action,obs)
            if action=="profile_schema": state.done=True
        except Exception as exc:
            trace.append({"tool":tool,"action":action,"ok":False,"error":str(exc)}); state.observe(action,{"error":str(exc)})
    checked=verify(result, task.get("gold",{}), trace, {**task["constraints"],"allowed_tools":task["allowed_tools"]})
    return {"task_id":task["task_id"],"score":checked["score"],"passed":checked["passed"],"tool_calls":len(trace),"trace":trace,"checks":checked["checks"]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--tasks",default="tasks/tasks.jsonl"); ap.add_argument("--mode",choices=["rule","bandit","llm"],default="rule"); ap.add_argument("--out",default="reports/results.jsonl"); ap.add_argument("--limit",type=int,default=0); ap.add_argument("--gold",default="tasks/gold_answers.json"); args=ap.parse_args()
    actions=["profile_schema","profile_missingness","clean","aggregate","visualize","model","explain","retry","stop"]
    policy=Policy(actions,mode=args.mode) if args.mode != "llm" else None
    llm=LLMClient() if args.mode == "llm" else None
    tasks=load_tasks(args.tasks); gold=load_gold(args.gold)
    for t in tasks:
        if t["task_id"] in gold: t["gold"].update(gold[t["task_id"]])
    tasks=tasks[:args.limit] if args.limit else tasks
    results=[]
    for i,t in enumerate(tasks,1):
        print(f"running {i}/{len(tasks)} {t['task_id']}", flush=True)
        results.append(run_task(t,policy,llm))
    p=Path(args.out); p.parent.mkdir(exist_ok=True); p.write_text("\n".join(json.dumps(r) for r in results)+"\n",encoding="utf-8"); print(f"completed {len(results)} tasks; passed={sum(r['passed'] for r in results)}")
if __name__ == "__main__": main()

