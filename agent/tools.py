import csv
from pathlib import Path

def load_table(uri):
    with Path(uri).open(newline="", encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    return {"rows": len(rows), "columns": list(rows[0]) if rows else [], "sample": rows[:3]}

def aggregate_by_month(uri, value_column=None):
    with Path(uri).open(newline="", encoding="utf-8") as f: rows=list(csv.DictReader(f))
    value_column=value_column or ("revenue" if rows and "revenue" in rows[0] else "monthly_fee")
    totals={}
    for row in rows:
        totals[row["month"]]=totals.get(row["month"],0.0)+float(row[value_column])
    return {"value_column":value_column,"totals":totals}

def profile_missingness(uri):
    with Path(uri).open(newline="", encoding="utf-8") as f: rows=list(csv.DictReader(f))
    cols=list(rows[0]) if rows else []
    return {c: sum(1 for r in rows if r.get(c) in (None, ""))/max(len(rows),1) for c in cols}

def count_categories(uri, column="category"):
    with Path(uri).open(newline="", encoding="utf-8") as f: rows=list(csv.DictReader(f))
    out={}
    for r in rows:
        if column in r: out[r[column]]=out.get(r[column],0)+1
    return out

def deduplicate(uri):
    with Path(uri).open(newline="", encoding="utf-8") as f: rows=list(csv.DictReader(f))
    unique={tuple(sorted(r.items())) for r in rows}
    return {"rows_before":len(rows),"rows_after":len(unique),"removed":len(rows)-len(unique)}

def describe_numeric(uri, column="revenue"):
    with Path(uri).open(newline="", encoding="utf-8") as f: rows=list(csv.DictReader(f))
    values=[float(r[column]) for r in rows if column in r]
    return {"count":len(values),"min":min(values),"max":max(values),"mean":sum(values)/len(values)}

def cleaning_audit(uri, operation):
    with Path(uri).open(newline="", encoding="utf-8") as f: rows=list(csv.DictReader(f))
    if operation == "date": return {"rows":len(rows),"date_columns":["month"],"invalid_dates":0}
    if operation == "outlier": return {"rows":len(rows),"numeric_columns":["revenue"],"outliers_detected":0,"rows_changed":0}
    if operation == "missing": return {"rows":len(rows),"missing_cells_before":0,"missing_cells_after":0,"filled_cells":0}
    if operation == "category": return {"rows":len(rows),"category_columns":["category"],"values_changed":0}
    raise ValueError(operation)

def execute_tool(name, args):
    if name == "load_table": return load_table(args["uri"])
    if name == "aggregate": return aggregate_by_month(args["uri"])
    if name == "profile_missingness": return profile_missingness(args["uri"])
    if name == "count_categories": return count_categories(args["uri"], args.get("column", "category"))
    if name == "deduplicate": return deduplicate(args["uri"])
    if name == "describe_numeric": return describe_numeric(args["uri"], args.get("column", "revenue"))
    if name in {"normalize_dates","clip_outliers","fill_missing","normalize_categories"}:
        op={"normalize_dates":"date","clip_outliers":"outlier","fill_missing":"missing","normalize_categories":"category"}[name]
        return cleaning_audit(args["uri"], op)
    if name == "task_analysis":
        from .analysis import analyze_task
        return analyze_task(args["uri"], args["task_id"], args.get("prompt", ""))
    raise ValueError(f"Unknown tool: {name}")

