"""Historical V3.5 routing-only experiment (source and style confounded).

Retained for reproduction; use research.v3_final for the corrected primary evaluation.
"""
import argparse, json, random
from pathlib import Path
from research.io import ROOT, write_json
from research.v3_recovery import FAULTS, FrozenRecoveryPolicy, examples

STYLES=("raw","compact","code","terse")

def restyle(message,style):
    if style=="raw":return message
    core=message.split(":",1)[-1].replace("; tool="," [")
    if style=="compact":return core+"]" if "[" in core else core
    if style=="code":return "RECOVERY_ERROR | "+core
    # Some production collectors retain only the exception class.
    return message.split(":",1)[0].strip()

def source_examples(source,meta,index):
    style=STYLES[index%len(STYLES)];rows=examples(source,meta,("raw",))
    # Different sources expose different fault frequencies while every class remains represented across the pool.
    selected=[r for j,r in enumerate(rows) if (j+index)%4!=0]
    for row in selected:row["style"]=style;row["message"]=restyle(row["message"],style)
    return selected

def percentile(values,q):
    values=sorted(values);return values[min(len(values)-1,int(q*(len(values)-1)))]

def bootstrap(values,draws=10000,seed=20260914):
    rng=random.Random(seed);n=len(values);samples=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(draws))
    return [samples[int(.025*draws)],samples[int(.975*draws)]]

def evaluate(out="reports/v3_leave_one_source_out.json"):
    meta=json.loads((ROOT/"tasks/v3_real/manifest.json").read_text(encoding="utf-8"))["sources"]
    sources=sorted(meta);pool={s:source_examples(s,meta[s],i) for i,s in enumerate(sources)};folds=[]
    for heldout in sources:
        available=[s for s in sources if s!=heldout];calibration=available[-1];fit=[s for s in available if s!=calibration]
        training=sum((pool[s] for s in fit),[]);cal=pool[calibration];test=pool[heldout]
        policy=FrozenRecoveryPolicy();policy.fit([r["message"] for r in training],[r["label"] for r in training])
        cal_conf=[policy.confidence(r["message"]) for r in cal if policy.predict(r["message"])==r["label"]]
        policy.confidence_threshold=.8*min(cal_conf) if cal_conf else 0.0
        predicted=[policy.predict(r["message"]) for r in test];passed=sum(p==r["label"] for p,r in zip(predicted,test))
        folds.append({"heldout_source":heldout,"calibration_source":calibration,"fit_sources":fit,"style":test[0]["style"],
                      "train_examples":len(training),"calibration_examples":len(cal),"test_examples":len(test),"passed":passed,
                      "rate":passed/len(test),"threshold":policy.confidence_threshold,
                      "errors":[{"fault":r["fault"],"expected":r["label"],"predicted":p} for p,r in zip(predicted,test) if p!=r["label"]]})
    rates=[f["rate"] for f in folds];result={"version":"3.5","sources":sources,"folds":folds,"macro_rate":sum(rates)/len(rates),
        "source_bootstrap_95":bootstrap(rates),"total_passed":sum(f["passed"] for f in folds),"total_tasks":sum(f["test_examples"] for f in folds)}
    write_json(ROOT/out,result);return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="reports/v3_leave_one_source_out.json");a=p.parse_args();print(json.dumps(evaluate(a.out),ensure_ascii=False,indent=2))
