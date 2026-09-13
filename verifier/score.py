"""Fail-closed evaluation; no imports from agent implementations."""
import math
from pathlib import Path
from research.io import digest,read_table,resolve
def _same(a,b,tol=1e-6):
    if isinstance(b,dict):return isinstance(a,dict) and set(a)==set(b) and all(_same(a[k],v,tol) for k,v in b.items())
    if isinstance(b,list):return isinstance(a,list) and len(a)==len(b) and all(_same(x,y,tol) for x,y in zip(a,b))
    if isinstance(b,bool) or b is None:return type(a) is type(b) and a==b
    if isinstance(b,(int,float)):
        try:return not isinstance(a,bool) and math.isfinite(float(a)) and math.isclose(float(a),float(b),abs_tol=tol,rel_tol=tol)
        except (TypeError,ValueError):return False
    return type(a) is type(b) and a==b
def verify(result,gold,trace,constraints):
    if "expected" not in gold or gold['expected'] is None:raise ValueError("independent non-null oracle.expected required")
    ev=result.get("evidence",{});h=constraints.get("input_sha256")
    evidence=bool(h) and isinstance(ev,dict) and ev.get("input_sha256")==h and isinstance(ev.get("rows_read"),int)
    legal=bool(trace) and all(t.get("tool") in constraints.get("allowed_tools",[]) and t.get("ok") for t in trace)
    budget=0<len(trace)<=constraints.get("max_tool_calls",1) and len(trace)<=constraints.get("max_steps",1) and constraints.get("elapsed_seconds",0)<=constraints.get("max_seconds",60)
    artifact=True
    if "artifact_rows" in gold:
        try:
            a=result["artifact"];p=resolve(a["path"]);cols,rows=read_table(p)
            artifact=digest(p)==a["sha256"] and cols==gold["artifact_columns"] and _same(rows,gold["artifact_rows"])
        except (KeyError,OSError,ValueError,TypeError):artifact=False
    checks={"answer":_same(result.get("answer"),gold["expected"],gold.get("tolerance",1e-6)),"evidence":evidence,"artifact":artifact,"legal":legal,"budget":budget}
    passed=all(checks.values())
    return {"passed":passed,"score":1-.05*len(trace)/max(1,constraints.get("max_tool_calls",1)) if passed else 0.0,"checks":checks}
