import argparse, json
from pathlib import Path

def read(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]

def summarize(rows, method):
    n=len(rows) or 1
    return {"method":method,"tasks":len(rows),"passed":sum(bool(x.get("passed")) for x in rows),
            "pass_rate":round(sum(bool(x.get("passed")) for x in rows)/n,4),
            "mean_score":round(sum(float(x.get("score",0)) for x in rows)/n,4),
            "mean_tool_calls":round(sum(int(x.get("tool_calls",0)) for x in rows)/n,4)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("files",nargs="+",help="result JSONL files"); ap.add_argument("--out",default="reports/summary.json"); args=ap.parse_args()
    summaries=[]
    for f in args.files:
        summaries.append(summarize(read(f),Path(f).stem.replace("_results", "")))
    Path(args.out).parent.mkdir(exist_ok=True); Path(args.out).write_text(json.dumps(summaries,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(summaries,ensure_ascii=False,indent=2))
if __name__ == "__main__": main()

