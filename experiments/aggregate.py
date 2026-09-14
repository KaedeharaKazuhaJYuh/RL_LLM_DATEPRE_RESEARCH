"""Aggregate explicit homogeneous v2 logs; refuse legacy/mixed-condition records."""
import argparse,json,statistics
from pathlib import Path
def read(path):
    rows=[json.loads(x) for x in Path(path).read_text(encoding='utf-8').splitlines() if x.strip()]
    if not rows or any(r.get('schema_version')!=2 for r in rows):raise ValueError('nonempty v2 logs required')
    keys=('code_sha256','tasks_sha256','oracle_sha256','mode','data_only','evaluation_split')
    conditions={tuple(r.get('run_metadata',{}).get(k) for k in keys) for r in rows}
    if len(conditions)!=1 or any(v is None for v in next(iter(conditions))):raise ValueError('mixed/missing experiment metadata')
    return rows
def summarize(rows,method):
    return {'method':method,'tasks':len(rows),'passed':sum(r['passed'] for r in rows),'pass_rate':sum(r['passed'] for r in rows)/len(rows),'mean_score':statistics.mean(r['score'] for r in rows),'mean_tool_calls':statistics.mean(r['tool_calls'] for r in rows)}
def main():
    p=argparse.ArgumentParser();p.add_argument('files',nargs='+');p.add_argument('--out',required=True);a=p.parse_args()
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps([summarize(read(f),Path(f).stem) for f in a.files],indent=2),encoding='utf-8')
if __name__=='__main__':main()
