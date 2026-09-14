"""Run bounded child processes and reject missing or partial results."""
import argparse, json, subprocess, sys, tempfile, time
from pathlib import Path
from research.io import ROOT, write_json

def run_case(mode,deadline=.15,sleep=.6,folder=None):
    base=Path(folder or tempfile.mkdtemp(prefix="v3_fault_"));target=base/f"{mode}.json"
    cmd=[sys.executable,"-m","research.v3_fault_worker","--mode",mode,"--output",str(target),"--sleep",str(sleep)]
    started=time.perf_counter();proc=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    killed=False
    try:stdout,stderr=proc.communicate(timeout=deadline)
    except subprocess.TimeoutExpired:
        killed=True;proc.kill();stdout,stderr=proc.communicate()
    elapsed=time.perf_counter()-started;valid=False;payload=None
    if target.exists():
        try:payload=json.loads(target.read_text(encoding="utf-8"));valid=payload.get("status")=="complete"
        except (json.JSONDecodeError,UnicodeDecodeError):pass
    passed=(mode=="success" and not killed and valid) or (mode=="timeout" and killed and not target.exists()) or (mode=="partial" and killed and target.exists() and not valid)
    return {"mode":mode,"deadline_seconds":deadline,"worker_sleep_seconds":sleep,"elapsed_seconds":elapsed,"killed":killed,
            "returncode":proc.returncode,"artifact_exists":target.exists(),"artifact_valid":valid,"payload":payload,"stdout":stdout,"stderr":stderr,"passed":passed}

def evaluate(trials=10,out="reports/v3_subprocess_faults.json"):
    records=[]
    with tempfile.TemporaryDirectory(prefix="v3_subprocess_") as d:
        for i in range(trials):
            for mode in ("success","timeout","partial"):records.append({"trial":i,**run_case(mode,folder=Path(d)/str(i))})
    result={"version":"3.4","trials":trials,"cases":len(records),"passed":sum(r["passed"] for r in records),
            "killed":sum(r["killed"] for r in records),"partial_artifacts_rejected":sum(r["mode"]=="partial" and r["passed"] for r in records),"records":records}
    write_json(ROOT/out,result);return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--trials",type=int,default=10);p.add_argument("--out",default="reports/v3_subprocess_faults.json");a=p.parse_args();r=evaluate(a.trials,a.out);print(json.dumps({k:v for k,v in r.items() if k!="records"},indent=2))
