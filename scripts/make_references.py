import json
from pathlib import Path
from agent.analysis import analyze_task

root=Path(__file__).parents[1]
tasks=[json.loads(x) for x in (root/"tasks/tasks.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
refs={t["task_id"]:analyze_task(t["dataset"]["uri"],t["task_id"],t["prompt"]) for t in tasks if int(t["task_id"][1:])>=12}
(root/"tasks"/"reference_outputs.json").write_text(json.dumps(refs,ensure_ascii=False,indent=2),encoding="utf-8")
print(f"wrote {len(refs)} reference outputs")

