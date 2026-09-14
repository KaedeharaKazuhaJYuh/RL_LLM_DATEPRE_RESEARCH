"""Run bounded child processes and reject missing or partial results."""
import argparse, json, subprocess, sys, tempfile, time
from pathlib import Path
from research.io import ROOT, write_json

def run_case(mode,deadline=.15,sleep=.6,folder=None):
    base=Path(folder or tempfile.mkdtemp(prefix="v3_fault_"));base.mkdir(parents=True,exist_ok=True)
    # A fresh run directory prevents accepting a previous run's complete artifact.
    base=Path(tempfile.mkdtemp(prefix='run_',dir=base));target=base/f"{mode}.json"
    ready=base/'ready'
    cmd=[sys.executable,"-m","research.v3_fault_worker","--mode",mode,"--output",str(target),"--ready",str(ready),"--sleep",str(sleep)]
    started=time.perf_counter();proc=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    # Bound startup separately so interpreter startup latency cannot masquerade as a tool timeout.
    while not ready.exists() and proc.poll() is None and time.perf_counter()-started < 5:
        time.sleep(.005)
    startup_seconds=time.perf_counter()-started
    killed=False
    if not ready.exists() and proc.poll() is None:
        proc.kill();proc.communicate()
        raise TimeoutError('worker did not become ready within startup budget')
    try:stdout,stderr=proc.communicate(timeout=deadline)
    except subprocess.TimeoutExpired:
        killed=True;proc.kill();stdout,stderr=proc.communicate()
    elapsed=time.perf_counter()-started;valid=False;payload=None
    if target.exists():
        try:payload=json.loads(target.read_text(encoding="utf-8"));valid=isinstance(payload,dict) and payload.get("status")=="complete" and proc.returncode==0 and not killed
        except (json.JSONDecodeError,UnicodeDecodeError):pass
    passed=(mode=="success" and not killed and valid) or (mode=="timeout" and killed and not target.exists()) or (mode=="partial" and killed and target.exists() and not valid)
    return {"mode":mode,"deadline_seconds":deadline,"startup_seconds":startup_seconds,"worker_sleep_seconds":sleep,"elapsed_seconds":elapsed,"killed":killed,
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
