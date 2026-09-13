"""Parameterized operations: task IDs and private oracle are never used."""
import math, statistics
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
from research.io import ROOT,read_table,write_table,digest,resolve
DESCRIPTIONS={
"profile_schema":"Return columns and row count.",
"profile_missingness":"Missing fraction per column; empty strings are missing.",
"count_categories":"Count exact values in column.",
"deduplicate":"Remove identical rows and save resulting table.",
"describe_numeric":"Count/min/max/mean of nonempty column values.",
"normalize_dates":"Normalize YYYY-MM, YYYY-MM-DD, YYYY/MM/DD to YYYY-MM-DD; invalid to empty.",
"clip_outliers":"Clip numeric column to explicit lower/upper; save table.",
"fill_missing":"Fill empty numeric cells with column median; save table.",
"normalize_categories":"Strip whitespace and uppercase column; save table.",
"aggregate":"Sum column grouped by group_by; ignore empty numeric values.",
"correlate":"Pearson correlation on complete pairs: column, other_column.",
"rolling_mean":"Rolling mean of column in row order; full windows only."}
ACTIONS=list(DESCRIPTIONS)
MUTATING={"deduplicate","normalize_dates","clip_outliers","fill_missing","normalize_categories"}
REQUIRED={a:("column",) for a in ACTIONS}
REQUIRED.update(profile_schema=(),profile_missingness=(),deduplicate=(),aggregate=("column","group_by"),correlate=("column","other_column"))
def number(v):
    v=float(v)
    if not math.isfinite(v):raise ValueError("non-finite numeric value")
    return v
def execute_tool(name,args):
    if name=="load_table":name="profile_schema"
    if name not in ACTIONS:raise ValueError("unsupported tool: "+name)
    cols,rows=read_table(args["uri"]);p=dict(args.get("params",{}));c=p.get("column")
    for key in REQUIRED[name]:
        if p.get(key) not in cols:raise ValueError("unknown/missing "+key)
    changed=[dict(r) for r in rows]
    if name=="profile_schema":ans={"columns":cols,"rows":len(rows)}
    elif name=="profile_missingness":ans={c:sum(r[c]=="" for r in rows)/max(1,len(rows)) for c in cols}
    elif name=="count_categories":ans=dict(Counter(r[c] for r in rows))
    elif name=="deduplicate":
        seen=set();changed=[]
        for r in rows:
            k=tuple(r[c] for c in cols)
            if k not in seen:seen.add(k);changed.append(dict(r))
        ans={"rows_before":len(rows),"rows_after":len(changed),"removed":len(rows)-len(changed)}
    elif name=="describe_numeric":
        v=[number(r[c]) for r in rows if r[c]!=""]
        if not v:raise ValueError("no numeric values")
        ans={"count":len(v),"min":min(v),"max":max(v),"mean":statistics.mean(v)}
    elif name=="normalize_dates":
        bad=count=0
        for r in changed:
            value=r[c];normalized=""
            for fmt in ("%Y-%m-%d","%Y/%m/%d","%Y-%m"):
                try:normalized=datetime.strptime(value,fmt).strftime("%Y-%m-%d");break
                except ValueError:pass
            bad+=bool(value and not normalized);count+=value!=normalized;r[c]=normalized
        ans={"rows":len(rows),"date_columns":[c],"invalid_dates":bad,"rows_changed":count}
    elif name=="clip_outliers":
        lo,hi=number(p["lower"]),number(p["upper"])
        if lo>hi:raise ValueError("lower exceeds upper")
        count=0
        for r in changed:
            if r[c]=="":continue
            v=number(r[c]);out=min(hi,max(lo,v));count+=v!=out;r[c]=str(out)
        ans={"rows":len(rows),"numeric_columns":[c],"outliers_detected":count,"rows_changed":count}
    elif name=="fill_missing":
        v=[number(r[c]) for r in rows if r[c]!=""]
        if not v:raise ValueError("all values missing")
        median=statistics.median(v);count=0
        for r in changed:
            if r[c]=="":r[c]=str(median);count+=1
        ans={"rows":len(rows),"missing_cells_before":count,"missing_cells_after":0,"filled_cells":count}
    elif name=="normalize_categories":
        count=0
        for r in changed:
            v=r[c].strip().upper();count+=v!=r[c];r[c]=v
        ans={"rows":len(rows),"category_columns":[c],"values_changed":count}
    elif name=="aggregate":
        totals=defaultdict(float)
        for r in rows:
            if r[c]!="":totals[r[p["group_by"]]]+=number(r[c])
        ans=dict(totals)
    elif name=="correlate":
        pairs=[(number(r[c]),number(r[p["other_column"]])) for r in rows if r[c]!="" and r[p["other_column"]]!=""]
        if len(pairs)<2:raise ValueError("too few pairs")
        x,y=zip(*pairs);ans={"correlation":statistics.correlation(x,y),"pairs":len(pairs)}
    else:
        w=p.get("window",3)
        if not isinstance(w,int) or w<1:raise ValueError("invalid window")
        v=[number(r[c]) for r in rows]
        ans={"values":[statistics.mean(v[i-w+1:i+1]) for i in range(w-1,len(v))]}
    result={"answer":ans,"evidence":{"input_sha256":digest(resolve(args["uri"])),"rows_read":len(rows)}}
    if name in MUTATING:
        if not args.get("artifact_dir"):raise ValueError("artifact_dir required")
        target=Path(args["artifact_dir"])/"table.csv";write_table(target,cols,changed)
        path=target.resolve();stored=path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)
        result["artifact"]={"path":stored,"sha256":digest(target),"columns":cols,"rows":changed}
    return result
