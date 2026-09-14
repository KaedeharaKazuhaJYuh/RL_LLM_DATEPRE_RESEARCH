"""Deterministic cluster bootstrap over held-out data sources."""
import argparse, json, random
from collections import defaultdict
from research.io import ROOT, write_json

def interval(values,seed=20260914,draws=10000):
    rng=random.Random(seed);n=len(values);samples=[]
    for _ in range(draws):samples.append(sum(values[rng.randrange(n)] for _ in range(n))/n)
    samples.sort();return [samples[int(.025*draws)],samples[min(draws-1,int(.975*draws))]]

def evaluate(source="reports/v3_real_recovery.json",out="reports/v3_source_bootstrap.json"):
    report=json.loads((ROOT/source).read_text(encoding="utf-8"));grouped=defaultdict(list)
    for row in report["records"]:grouped[row["source"]].append(row)
    learned=[];heuristic=[]
    for rows in grouped.values():
        learned.append(sum(r["execution_passed"] or (r["label"]=="escalate" and r["predicted_repair"]=="escalate") for r in rows)/len(rows))
        heuristic.append(sum(r["heuristic_execution_passed"] or (r["label"]=="escalate" and r["heuristic_repair"]=="escalate") for r in rows)/len(rows))
    result={"version":"3.4","unit":"held-out data source","sources":sorted(grouped),"draws":10000,
            "learned":{"source_rates":learned,"mean":sum(learned)/len(learned),"bootstrap_95":interval(learned)},
            "heuristic":{"source_rates":heuristic,"mean":sum(heuristic)/len(heuristic),"bootstrap_95":interval(heuristic)}}
    write_json(ROOT/out,result);return result

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",default="reports/v3_source_bootstrap.json");a=p.parse_args();print(json.dumps(evaluate(out=a.out),indent=2))
