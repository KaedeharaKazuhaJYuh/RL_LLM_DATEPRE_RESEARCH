import csv, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def resolve(path):
    p=Path(path); return p if p.is_absolute() else ROOT/p
def digest(path,chunk_size=1024*1024):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(chunk_size),b''):value.update(chunk)
    return value.hexdigest()
def read_table(path):
    with resolve(path).open(encoding="utf-8",newline="") as f:
        r=csv.DictReader(f); cols=r.fieldnames
        if not cols or len(cols)!=len(set(cols)): raise ValueError("missing/duplicate CSV columns")
        rows=list(r)
    if any(None in r or any(v is None for v in r.values()) for r in rows): raise ValueError("inconsistent CSV width")
    return cols,rows
def write_table(path,cols,rows):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,lineterminator="\n");w.writeheader();w.writerows(rows)
def load_jsonl(path):
    return [json.loads(l) for l in resolve(path).read_text(encoding="utf-8").splitlines() if l.strip()]
def write_json(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8",newline="\n")
def append_jsonl(path,obj):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("a",encoding="utf-8",newline="\n") as f:f.write(json.dumps(obj,ensure_ascii=False,allow_nan=False)+"\n")
