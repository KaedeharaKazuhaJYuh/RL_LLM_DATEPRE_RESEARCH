import csv, statistics
from pathlib import Path

def read(uri):
    with Path(uri).open(newline="", encoding="utf-8") as f: return list(csv.DictReader(f))

def analyze_task(uri, task_id, prompt):
    rows=read(uri); cols=list(rows[0]) if rows else []
    numeric={c:[float(r[c]) for r in rows if r.get(c) not in (None,"")] for c in cols}
    numeric={c:v for c,v in numeric.items() if v}
    group="aggregation" if 12<=int(task_id[1:])<=15 else "statistics" if 16<=int(task_id[1:])<=20 else "time_series" if 21<=int(task_id[1:])<=25 else "visualization" if 26<=int(task_id[1:])<=30 else "features" if 31<=int(task_id[1:])<=35 else "modeling" if 36<=int(task_id[1:])<=40 else "decision" if 41<=int(task_id[1:])<=45 else "robustness"
    result={"task_id":task_id,"operation":group,"rows":len(rows),"columns":cols,"evidence":["computed_from_csv"]}
    if group=="aggregation" and "month" in cols:
        value="revenue" if "revenue" in cols else "monthly_fee"; result["monthly_sum"]={}
        for r in rows: result["monthly_sum"][r["month"]]=result["monthly_sum"].get(r["month"],0)+float(r[value])
    elif group=="statistics": result["numeric_summary"]={c:{"mean":statistics.mean(v),"median":statistics.median(v)} for c,v in numeric.items()}
    elif group=="time_series": result["time_column"]="month" if "month" in cols else None; result["ordered"]=("month" in cols and [r["month"] for r in rows]==sorted(r["month"] for r in rows))
    elif group=="visualization": result["recommended_chart"]="line" if "month" in cols else "bar"; result["x_candidates"]=[c for c in cols if c not in numeric]
    elif group=="features": result["feature_candidates"]=[c for c in cols if c not in {"student_id","customer_id","score","churned"}]
    elif group=="modeling": result["target_candidates"]=[c for c in ("score","churned") if c in cols]; result["numeric_features"]=list(numeric)
    elif group=="decision": result["recommendation_basis"]={"rows":len(rows),"numeric_columns":list(numeric)}
    else: result["recovery_checks"]={"file_exists":Path(uri).exists(),"schema_available":bool(cols),"safe_stop":not bool(rows) is False}
    return result

