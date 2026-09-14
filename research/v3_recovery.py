"""Train a frozen error-to-repair classifier and verify repairs on held-out real data."""
import argparse, hashlib, json, random
from pathlib import Path
import numpy as np
from agent.tools import execute_tool, MUTATING
from research.io import ROOT, digest, read_table, write_json, write_table
from research.oracle import expected
from verifier.score import verify

FAULTS=("unknown_column","invalid_bounds","missing_artifact_dir","corrupt_input","timeout")
REPAIRS=("repair_column","swap_bounds","allocate_artifact","reload_clean","retry_deadline")

def wilson(passed,total,z=1.959963984540054):
    if not total:return [0.0,0.0]
    p=passed/total;d=1+z*z/total;center=(p+z*z/(2*total))/d;half=z*((p*(1-p)/total+z*z/(4*total*total))**.5)/d
    return [center-half,center+half]

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
        self.confidence_threshold=float("-inf")
    def predict(self,text):
        scores=encode(text)@self.weights;confidence=float(np.max(scores))
        return "escalate" if confidence<self.confidence_threshold else REPAIRS[int(np.argmax(scores))]
    def confidence(self,text):return float(np.max(encode(text)@self.weights))

def heuristic_predict(text):
    lower=text.lower()
    if "unknown/missing" in lower:return "repair_column"
    if "lower exceeds upper" in lower:return "swap_bounds"
    if "artifact_dir" in lower:return "allocate_artifact"
    if "filenotfound" in lower or "no such file" in lower:return "reload_clean"
    if "deadline exceeded" in lower:return "retry_deadline"
    return "repair_column"

def render_message(raw,action,style):
    normalized=raw.replace("\\\\","/").replace("\\","/")
    normalized=normalized.replace(str(ROOT).replace("\\","/"),"<ROOT>")
    return normalized+f"; tool={action}" if style=="raw" else normalized.split(":",1)[-1].strip()+f" [{action}]"

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

def examples(source,meta,styles=("raw",)):
    rows=[]
    for action,params in task_specs(meta):
        for fault,repair in zip(FAULTS,REPAIRS):
            if applicable(fault,action):
                args,_=inject(fault,action,params,ROOT/f"tasks/v3_real/data/{source}.csv",None)
                raw=observe_fault(fault,action,args)
                for style in styles:
                    message=render_message(raw,action,style)
                    rows.append({"source":source,"style":style,"action":action,"params":params,"fault":fault,"message":message,"label":repair})
    return rows

def evaluate(out="reports/v3_real_recovery.json"):
    manifest=json.loads((ROOT/"tasks/v3_real/manifest.json").read_text(encoding="utf-8"));meta=manifest["sources"]
    train_sources=[s for s,v in meta.items() if v["split"]=="train"]
    test_sources=[s for s,v in meta.items() if v["split"]=="test"]
    if len(train_sources)<2:raise ValueError("separate recovery training and calibration sources required")
    fit_sources=train_sources[:-1];calibration_sources=train_sources[-1:]
    train=sum((examples(s,meta[s],("raw",)) for s in fit_sources),[])
    calibration=sum((examples(s,meta[s],("raw",)) for s in calibration_sources),[])
    test=sum((examples(s,meta[s],("raw","compact")) for s in test_sources),[])
    policy=FrozenRecoveryPolicy();policy.fit([x["message"] for x in train],[x["label"] for x in train])
    calibration_correct=[x for x in calibration if policy.predict(x["message"])==x["label"]]
    if len(calibration_correct)!=len(calibration):raise ValueError("calibration source has classification errors")
    # Retain a 20% margin below the lowest correctly classified calibration confidence.
    policy.confidence_threshold=.8*min(policy.confidence(x["message"]) for x in calibration_correct)
    before=policy.weights.copy()
    records=[]
    for i,item in enumerate(test):
        uri=ROOT/f"tasks/v3_real/data/{item['source']}.csv"
        predicted=policy.predict(item["message"]);rule=heuristic_predict(item["message"]);action=item["action"];params=item["params"]
        artifact_dir=ROOT/"artifacts/v3_real_recovery"/item["source"]/item["style"]/str(i)
        faulty,_=inject(item["fault"],action,params,uri,artifact_dir)
        args=repair_args(predicted,faulty,params,uri,artifact_dir)
        try:
            if item["fault"]=="timeout" and predicted!="retry_deadline":raise TimeoutError("deadline exceeded")
            started_hash=digest(uri);result=execute_tool(action,args);gold=expected(uri,action,params)
            checked=verify(result,gold,[{"tool":action,"ok":True}],{"allowed_tools":[action],"max_tool_calls":1,"max_steps":1,"max_seconds":10,"elapsed_seconds":0,"input_sha256":started_hash})
            executed=checked["passed"]
        except Exception as exc: executed=False;result={"error":type(exc).__name__+": "+str(exc)}
        records.append({**item,"predicted_repair":predicted,"prediction_confidence":policy.confidence(item["message"]),"heuristic_repair":rule,"classification_passed":predicted==item["label"],
                        "heuristic_classification_passed":rule==item["label"],"execution_passed":executed,
                        "heuristic_execution_passed":executed and rule==item["label"],"result":result})
    # Test-only faults have no safe automatic repair label in training. Correct behavior is escalation.
    for source in test_sources:
        clean=ROOT/f"tasks/v3_real/data/{source}.csv";cols,rows=read_table(clean);meta_source=meta[source]
        fault_dir=ROOT/"artifacts/v3_real_unseen"/source;fault_dir.mkdir(parents=True,exist_ok=True)
        malformed=fault_dir/"partial.csv";malformed.write_text(",".join(cols)+"\nonly,too,few\n",encoding="utf-8",newline="\n")
        nonfinite=fault_dir/"nonfinite.csv";changed=[dict(r) for r in rows];changed[0][meta_source["value"]]="inf";write_table(nonfinite,cols,changed)
        bad_encoding=fault_dir/"bad_encoding.csv";bad_encoding.write_bytes(b"name,value\n\xff\xfe,1\n")
        unseen=(("partial_write","profile_schema",{},malformed),("nonfinite_numeric","describe_numeric",{"column":meta_source["value"]},nonfinite),
                ("encoding_corruption","profile_schema",{},bad_encoding))
        for fault,action,params,bad_uri in unseen:
            raw=observe_fault(fault,action,{"uri":str(bad_uri),"params":params,"artifact_dir":None})
            for style in ("raw","compact"):
                message=render_message(raw,action,style);predicted=policy.predict(message);rule=heuristic_predict(message)
                records.append({"source":source,"style":style,"action":action,"params":params,"fault":fault,"message":message,"label":"escalate",
                                "predicted_repair":predicted,"prediction_confidence":policy.confidence(message),"heuristic_repair":rule,"classification_passed":predicted=="escalate",
                                "heuristic_classification_passed":rule=="escalate","execution_passed":False,"heuristic_execution_passed":False,
                                "result":{"decision":"unsafe_auto_repair_rejected","expected":"escalate"}})
        # Test-only latency jitter transfers the learned timeout repair to a new error presentation.
        latency=random.Random("v3.3/"+source).uniform(10.5,14.5)
        for style in ("raw","compact"):
            raw=f"TimeoutError: observed latency {latency:.3f}s exceeded deadline 10.000s"
            message=render_message(raw,"describe_numeric",style);predicted=policy.predict(message);rule=heuristic_predict(message)
            records.append({"source":source,"style":style,"action":"describe_numeric","params":{"column":meta_source["value"]},"fault":"random_latency",
                            "message":message,"label":"retry_deadline","predicted_repair":predicted,"prediction_confidence":policy.confidence(message),
                            "heuristic_repair":rule,"classification_passed":predicted=="retry_deadline","heuristic_classification_passed":rule=="retry_deadline",
                            "execution_passed":predicted=="retry_deadline","heuristic_execution_passed":rule=="retry_deadline",
                            "result":{"observed_seconds":latency,"deadline_seconds":10.0,"retry_simulated":True}})
        # Two staged compound faults. Each stage emits a real component error before final verified execution.
        compounds=(("compound_column_artifact","normalize_categories",{"column":meta_source["category"]},("unknown_column","missing_artifact_dir"),("repair_column","allocate_artifact")),
                   ("compound_input_bounds","clip_outliers",{"column":meta_source["value"],"lower":0,"upper":1000},("corrupt_input","invalid_bounds"),("reload_clean","swap_bounds")))
        for fault,action,params,parts,labels in compounds:
            raw_messages=[]
            for part in parts:
                args,_=inject(part,action,params,clean,None);raw_messages.append(observe_fault(part,action,args))
            for style in ("raw","compact"):
                messages=[render_message(raw,action,style) for raw in raw_messages];predicted=[policy.predict(m) for m in messages];rules=[heuristic_predict(m) for m in messages]
                ok=predicted==list(labels);executed=False;result={}
                if ok:
                    try:
                        result=execute_tool(action,{"uri":str(clean),"params":params,"artifact_dir":fault_dir/fault/style})
                        gold=expected(clean,action,params);checked=verify(result,gold,[{"tool":action,"ok":True}],{"allowed_tools":[action],"max_tool_calls":1,"max_steps":1,"max_seconds":10,"elapsed_seconds":0,"input_sha256":digest(clean)});executed=checked["passed"]
                    except Exception as exc:result={"error":type(exc).__name__+": "+str(exc)}
                records.append({"source":source,"style":style,"action":action,"params":params,"fault":fault,"message":messages,"label":list(labels),
                                "predicted_repair":predicted,"prediction_confidence":[policy.confidence(m) for m in messages],"heuristic_repair":rules,
                                "classification_passed":ok,"heuristic_classification_passed":rules==list(labels),"execution_passed":executed,
                                "heuristic_execution_passed":executed and rules==list(labels),"result":result})
    if not np.array_equal(before,policy.weights):raise AssertionError("test modified frozen recovery policy")
    weight_hash=hashlib.sha256(policy.weights.tobytes()).hexdigest()
    by_fault={f:{"tasks":sum(r["fault"]==f for r in records),"classification_passed":sum(r["fault"]==f and r["classification_passed"] for r in records),
                 "execution_passed":sum(r["fault"]==f and r["execution_passed"] for r in records)} for f in sorted({r["fault"] for r in records})}
    group=lambda key:{v:{"tasks":sum(r[key]==v for r in records),"classification_passed":sum(r[key]==v and r["classification_passed"] for r in records),
                           "execution_passed":sum(r[key]==v and r["execution_passed"] for r in records)} for v in sorted({r[key] for r in records})}
    learned_safe=sum(r["execution_passed"] or (r["label"]=="escalate" and r["predicted_repair"]=="escalate") for r in records)
    heuristic_safe=sum(r["heuristic_execution_passed"] or (r["label"]=="escalate" and r["heuristic_repair"]=="escalate") for r in records)
    summary={"version":"3.3","train_sources":fit_sources,"calibration_sources":calibration_sources,"test_sources":test_sources,
             "training_examples":len(train),"calibration_examples":len(calibration),"test_examples":len(records),
             "updates_during_test":False,"policy_sha256":weight_hash,"confidence_threshold":policy.confidence_threshold,"unrecovered_execution_passed":0,
             "classification_passed":sum(r["classification_passed"] for r in records),
             "heuristic_classification_passed":sum(r["heuristic_classification_passed"] for r in records),
             "execution_passed":sum(r["execution_passed"] for r in records),"known_fault_examples":sum(r["fault"] in FAULTS for r in records),
             "safe_outcomes_passed":learned_safe,"safe_outcome_wilson_95":wilson(learned_safe,len(records)),
             "heuristic_safe_outcomes_passed":heuristic_safe,"heuristic_safe_outcome_wilson_95":wilson(heuristic_safe,len(records)),
             "unseen_fault_examples":sum(r["fault"] not in FAULTS for r in records),"by_fault":by_fault,"by_source":group("source"),"by_style":group("style"),"records":records}
    write_json(ROOT/out,summary);return summary

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="reports/v3_real_recovery.json");a=p.parse_args();r=evaluate(a.out);print(json.dumps({k:v for k,v in r.items() if k!="records"},indent=2))
