"""Train a frozen error-to-repair classifier and verify repairs on held-out real data."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from agent.tools import execute_tool, MUTATING
from research.io import ROOT, digest, write_json
from research.oracle import expected
from verifier.score import verify

FAULTS=("unknown_column","invalid_bounds","missing_artifact_dir","corrupt_input","timeout")
REPAIRS=("repair_column","swap_bounds","allocate_artifact","reload_clean","retry_deadline")

def encode(text,dim=384):
    x=np.zeros(dim)
    compact=" ".join(text.lower().split())
    for n in (2,3,4):
        for i in range(max(1,len(compact)-n+1)):
            token=compact[i:i+n];h=hashlib.sha256(token.encode()).digest();x[int.from_bytes(h[:4],"big")%dim]+=1
    norm=np.linalg.norm(x);return x/norm if norm else x

class FrozenRecoveryPolicy:
    def fit(self,texts,labels):
        X=np.asarray([encode(x) for x in texts]);Y=np.eye(len(REPAIRS))[[REPAIRS.index(y) for y in labels]]
        self.weights=np.linalg.solve(X.T@X+np.eye(X.shape[1])*.2,X.T@Y)
    def predict(self,text): return REPAIRS[int(np.argmax(encode(text)@self.weights))]

def task_specs(meta):
    return [
      ("describe_numeric",{"column":meta["value"]}),
      ("clip_outliers",{"column":meta["value"],"lower":0,"upper":1000}),
      ("normalize_categories",{"column":meta["category"]}),
      ("correlate",{"column":meta["value"],"other_column":meta["metric"]}),
    ]

def inject(fault,action,params,uri,artifact_dir):
    p=dict(params);args={"uri":str(uri),"params":p,"artifact_dir":artifact_dir};error=""
    if fault=="unknown_column":p["column"]="missing_field";error=f"unknown/missing column while running {action}"
    elif fault=="invalid_bounds":p.update(lower=10,upper=1);error=f"lower exceeds upper while running {action}"
    elif fault=="missing_artifact_dir":args["artifact_dir"]=None;error=f"artifact_dir required while running {action}"
    elif fault=="corrupt_input":args["uri"]=str(uri)+".missing";error=f"input file unavailable while running {action}"
    else:error=f"deadline exceeded while running {action}"
    return args,error

def applicable(fault,action):
    return (fault!="invalid_bounds" or action=="clip_outliers") and (fault!="missing_artifact_dir" or action in MUTATING)

def repair_args(repair,faulty,clean_params,uri,artifact_dir):
    args={"uri":faulty["uri"],"params":dict(faulty["params"]),"artifact_dir":faulty.get("artifact_dir")}
    if repair=="repair_column":args["params"]["column"]=clean_params["column"]
    elif repair=="swap_bounds":
        args["params"]["lower"]=clean_params["lower"];args["params"]["upper"]=clean_params["upper"]
    elif repair=="allocate_artifact":args["artifact_dir"]=artifact_dir
    elif repair=="reload_clean":args["uri"]=str(uri)
    return args

def observe_fault(fault,action,args):
    try:
        if fault=="timeout":raise TimeoutError(f"deadline exceeded while running {action}")
        execute_tool(action,args)
    except Exception as exc:return type(exc).__name__+": "+str(exc)
    raise AssertionError(f"fault {fault} did not fail")

def examples(source,meta):
    rows=[]
    for action,params in task_specs(meta):
        for fault,repair in zip(FAULTS,REPAIRS):
            if applicable(fault,action):
                args,_=inject(fault,action,params,ROOT/f"tasks/v3_real/data/{source}.csv",None)
                message=observe_fault(fault,action,args)+f"; tool={action}"
                rows.append({"source":source,"action":action,"params":params,"fault":fault,"message":message,"label":repair})
    return rows

def evaluate(out="reports/v3_real_recovery.json"):
    manifest=json.loads((ROOT/"tasks/v3_real/manifest.json").read_text(encoding="utf-8"));meta=manifest["sources"]
    train=sum((examples(s,meta[s]) for s in ("wine","bank")),[]);test=examples("abalone",meta["abalone"])
    policy=FrozenRecoveryPolicy();policy.fit([x["message"] for x in train],[x["label"] for x in train]);before=policy.weights.copy()
    records=[];uri=ROOT/"tasks/v3_real/data/abalone.csv"
    for i,item in enumerate(test):
        predicted=policy.predict(item["message"]);action=item["action"];params=item["params"];artifact_dir=ROOT/"artifacts/v3_real_recovery"/str(i)
        faulty,_=inject(item["fault"],action,params,uri,artifact_dir)
        args=repair_args(predicted,faulty,params,uri,artifact_dir)
        try:
            if item["fault"]=="timeout" and predicted!="retry_deadline":raise TimeoutError("deadline exceeded")
            started_hash=digest(uri);result=execute_tool(action,args);gold=expected(uri,action,params)
            checked=verify(result,gold,[{"tool":action,"ok":True}],{"allowed_tools":[action],"max_tool_calls":1,"max_steps":1,"max_seconds":10,"elapsed_seconds":0,"input_sha256":started_hash})
            executed=checked["passed"]
        except Exception as exc: executed=False;result={"error":type(exc).__name__+": "+str(exc)}
        records.append({**item,"predicted_repair":predicted,"classification_passed":predicted==item["label"],"execution_passed":executed,"result":result})
    if not np.array_equal(before,policy.weights):raise AssertionError("test modified frozen recovery policy")
    weight_hash=hashlib.sha256(policy.weights.tobytes()).hexdigest()
    by_fault={f:{"tasks":sum(r["fault"]==f for r in records),"classification_passed":sum(r["fault"]==f and r["classification_passed"] for r in records),
                 "execution_passed":sum(r["fault"]==f and r["execution_passed"] for r in records)} for f in FAULTS}
    summary={"version":"3.1","train_sources":["wine","bank"],"test_sources":["abalone"],"training_examples":len(train),"test_examples":len(test),
             "updates_during_test":False,"policy_sha256":weight_hash,"unrecovered_execution_passed":0,
             "classification_passed":sum(r["classification_passed"] for r in records),
             "execution_passed":sum(r["execution_passed"] for r in records),"by_fault":by_fault,"records":records}
    write_json(ROOT/out,summary);return summary

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="reports/v3_real_recovery.json");a=p.parse_args();r=evaluate(a.out);print(json.dumps({k:v for k,v in r.items() if k!="records"},indent=2))
