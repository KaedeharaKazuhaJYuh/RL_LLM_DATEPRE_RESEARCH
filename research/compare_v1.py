"""Common inputs + independent evaluator, with native v1 diagnostics separate."""
import argparse,json,subprocess,sys,statistics
from pathlib import Path
from research.io import ROOT,resolve,write_json,append_jsonl
from research.runtime import load_bundle,run_task
from research.policies import Policy
from verifier.score import verify

OLD_IDS={'profile_schema':'T01','profile_missingness':'T02','count_categories':'T03','deduplicate':'T06','describe_numeric':'T05','normalize_dates':'T07','clip_outliers':'T08','fill_missing':'T09','normalize_categories':'T10','aggregate':'T11','correlate':'T18','rolling_mean':'T23'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--v1-root',required=True);p.add_argument('--out-dir',default='reports/v2_comparison');a=p.parse_args()
    tasks,oracles=load_bundle();test=[t for t in tasks if t['split']=='test'];out=resolve(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    request=[]
    for task in test:
        t={**task,'dataset':{**task['dataset'],'uri':str(resolve(task['dataset']['uri']))}}
        request.append({'task':t,'legacy_task_id':OLD_IDS[oracles[t['task_id']]['training_action']]})
    scratch=ROOT/'work/comparison';write_json(scratch/'request.json',request)
    subprocess.run([sys.executable,str(ROOT/'scripts/v1_worker.py'),'--v1-root',a.v1_root,'--input',str(scratch/'request.json'),'--out',str(scratch/'v1.json')],check=True)
    data=json.loads((scratch/'v1.json').read_text(encoding='utf-8'));old={r['task_id']:r for r in data['common']};rows=[]
    for task in test:
        v1=old[task['task_id']]
        # Normalize only load_table naming; no analytical values are recomputed.
        trace=[{**t,'tool':'profile_schema' if t['tool']=='load_table' else t['tool']} for t in v1['trace']]
        checked=verify(v1['result'],oracles[task['task_id']],trace,{**task['constraints'],'input_sha256':task['dataset']['sha256'],'allowed_tools':task['allowed_tools'],'elapsed_seconds':v1['cost']['wall_seconds_including_profile']})
        v2=run_task(task,Policy('rule'),oracles[task['task_id']],ROOT/'artifacts/common'/task['task_id'])
        rows.append({'task_id':task['task_id'],'source_id':task['source_id'],'operation':oracles[task['task_id']]['training_action'],'v1':{**v1,**checked},'v2':v2})
    path=out/'common.jsonl'
    if path.exists():raise FileExistsError('comparison output already exists')
    for r in rows:append_jsonl(path,r)
    native=data['native'];summary={'v1_commit':'e59cbb5669f4d6e681fe51d38a60ab6d2cae6cb3','native_v1':{'tasks':50,'rule_passed':sum(r['passed'] for r in native['rule']),'bandit_passed_per_seed':[sum(r['passed'] for r in rs) for rs in native['bandit'].values()],'test_functions':native['tests']},'common':{'tasks':len(rows),'v1_passed':sum(r['v1']['passed'] for r in rows),'v2_passed':sum(r['v2']['passed'] for r in rows),'v1_mean_seconds':statistics.mean(r['v1']['cost']['wall_seconds_including_profile'] for r in rows),'v2_mean_seconds':statistics.mean(r['v2']['cost']['wall_seconds_including_profile'] for r in rows),'by_operation':{op:{'tasks':sum(r['operation']==op for r in rows),'v1_passed':sum(r['v1']['passed'] for r in rows if r['operation']==op),'v2_passed':sum(r['v2']['passed'] for r in rows if r['operation']==op)} for op in OLD_IDS}},'protocol':'72 held-out synthetic tasks, same CSV/prompt/one-call budget/oracle. v1 native runtime with original family IDs (privileged legacy information); only schema response shape normalized. Cleaning requires real artifact. No LLM calls. Measures system capability, not isolated policy learning.'}
    write_json(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
