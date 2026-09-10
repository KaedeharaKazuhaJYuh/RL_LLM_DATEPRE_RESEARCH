import json, glob, statistics
from pathlib import Path

def load_tasks():
    return {json.loads(x)["task_id"]:json.loads(x) for x in Path("tasks/tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()}

def main():
    tasks=load_tasks(); summaries=[]
    for condition in ("raw","protected"):
        rows=[]
        for f in glob.glob(f"reports/matrix/llm_seed*_{condition}.jsonl"):
            rows += [json.loads(x) for x in Path(f).read_text(encoding="utf-8").splitlines() if x.strip()]
        scores=[]
        for r in rows:
            checks=r.get("checks",{}); correct=all(checks.get(k,False) for k in ("structure","answer","contract","reference"))
            evidence=any(t.get("ok") for t in r.get("trace",[])); budget=tasks[r["task_id"]]["constraints"]["max_tool_calls"]
            cost=max(0.0,1.0-len(r.get("trace",[]))/max(budget,1)); scores.append(.6*float(correct)+.2*float(evidence)+.2*cost)
        summaries.append({"condition":condition,"tasks":len(rows),"passed":sum(r.get("passed",False) for r in rows),"pass_rate":round(sum(r.get("passed",False) for r in rows)/len(rows),4),"mean_score":round(statistics.mean(scores),4),"mean_tool_calls":round(statistics.mean(len(r.get("trace",[])) for r in rows),4)})
    Path("reports/ablation_summary_v2.json").write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding="utf-8"); print(json.dumps(summaries,ensure_ascii=False,indent=2))
if __name__ == "__main__": main()

