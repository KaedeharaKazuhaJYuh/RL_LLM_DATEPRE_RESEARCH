import csv
from pathlib import Path

def load_table(uri):
    with Path(uri).open(newline="", encoding="utf-8") as f:
        rows=list(csv.DictReader(f))
    return {"rows": len(rows), "columns": list(rows[0]) if rows else [], "sample": rows[:3]}

def execute_tool(name, args):
    if name == "load_table": return load_table(args["uri"])
    raise ValueError(f"Unknown tool: {name}")

