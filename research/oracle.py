"""Independent NumPy/reference loops. Never imports agent tool implementations."""
import calendar,re
import numpy as np
from research.io import read_table
def expected(uri,op,p):
    cols,rows=read_table(uri);c=p.get("column");out=[dict(r) for r in rows]
    values=lambda col:np.array([float(r[col]) for r in rows if r[col]!=""],dtype=float)
    if op=="profile_schema":a={"columns":cols,"rows":len(rows)}
    elif op=="profile_missingness":a={col:sum(r[col]=="" for r in rows)/max(1,len(rows)) for col in cols}
    elif op=="count_categories":a={v:sum(r[c]==v for r in rows) for v in sorted({r[c] for r in rows})}
    elif op=="deduplicate":
        out=[]
        for r in rows:
            if r not in out:out.append(dict(r))
        a={"rows_before":len(rows),"rows_after":len(out),"removed":len(rows)-len(out)}
    elif op=="describe_numeric":
        v=values(c);a={"count":len(v),"min":float(np.min(v)),"max":float(np.max(v)),"mean":float(np.mean(v))}
    elif op=="normalize_dates":
        bad=count=0
        for r in out:
            raw=r[c];m=re.fullmatch(r"(\d{4})[-/](\d{2})(?:[-/](\d{2}))?",raw);v=""
            if m:
                y,mo,d=int(m[1]),int(m[2]),int(m[3] or 1)
                if 1<=y<=9999 and 1<=mo<=12 and 1<=d<=calendar.monthrange(y,mo)[1]:v=f"{y:04d}-{mo:02d}-{d:02d}"
            bad+=bool(raw and not v);count+=raw!=v;r[c]=v
        a={"rows":len(rows),"date_columns":[c],"invalid_dates":bad,"rows_changed":count}
    elif op=="clip_outliers":
        count=0
        for r in out:
            if r[c]=="":continue
            before=float(r[c]);after=float(np.clip(before,p["lower"],p["upper"]));count+=before!=after;r[c]=str(after)
        a={"rows":len(rows),"numeric_columns":[c],"outliers_detected":count,"rows_changed":count}
    elif op=="fill_missing":
        med=float(np.quantile(values(c),.5));count=0
        for r in out:
            if r[c]=="":r[c]=str(med);count+=1
        a={"rows":len(rows),"missing_cells_before":count,"missing_cells_after":0,"filled_cells":count}
    elif op=="normalize_categories":
        count=0
        for r in out:
            old=r[c];r[c]=old.strip().upper();count+=old!=r[c]
        a={"rows":len(rows),"category_columns":[c],"values_changed":count}
    elif op=="aggregate":
        g=p["group_by"];a={k:float(np.sum([float(r[c]) for r in rows if r[g]==k and r[c]!=""])) for k in sorted({r[g] for r in rows if r[c]!=""})}
    elif op=="correlate":
        pairs=np.array([[float(r[c]),float(r[p["other_column"]])] for r in rows if r[c]!="" and r[p["other_column"]]!=""])
        a={"correlation":float(np.corrcoef(pairs.T)[0,1]),"pairs":len(pairs)}
    elif op=="rolling_mean":
        v=values(c);w=p["window"];a={"values":[float(x) for x in np.convolve(v,np.ones(w)/w,mode="valid")]}
    else:raise ValueError("unknown operation")
    result={"expected":a,"tolerance":1e-6,"training_action":op}
    if op in {"deduplicate","normalize_dates","clip_outliers","fill_missing","normalize_categories"}:result.update(artifact_columns=cols,artifact_rows=out)
    return result
