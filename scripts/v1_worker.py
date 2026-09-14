"""Isolated v1 adapter: capture native runtime outputs, never alter v1 files."""
import argparse,copy,hashlib,inspect,json,os,sys,tempfile,time
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--v1-root',required=True);p.add_argument('--input',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    root=Path(a.v1_root).resolve();request=json.loads(Path(a.input).read_text(encoding='utf-8'));output=Path(a.out).resolve()
    sys.path.insert(0,str(root));os.chdir(root)
    import experiments.run as old
    from agent.policy import Policy
    native_tasks=old.load_tasks('tasks/tasks.jsonl');gold=old.load_gold();refs=old.load_references()
    for t in native_tasks:t['gold'].update(gold.get(t['task_id'],{}));t['_reference']=refs.get(t['task_id'],{})
    native={};native['rule']=[old.run_task(t) for t in native_tasks]
    native['bandit']={}
    for seed in range(1,6):
        policy=Policy(old.LLM_ACTIONS,mode='bandit',seed=seed);native['bandit'][str(seed)]=[old.run_task(t,policy,contract_protection=False) for t in native_tasks]
    # Original tests, called directly because pytest is not required for v2.
    import importlib.util
    spec=importlib.util.spec_from_file_location('v1_tests',root/'tests/test_core.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);checks=[]
    for name,fn in inspect.getmembers(mod,inspect.isfunction):
        if not name.startswith('test_'):continue
        try:
            with tempfile.TemporaryDirectory() as d:
                fn(Path(d)) if 'tmp_path' in inspect.signature(fn).parameters else fn()
            checks.append({'name':name,'passed':True})
        except Exception as e:checks.append({'name':name,'passed':False,'error':type(e).__name__})
    native['tests']=checks
    cases=[];original=old.execute_tool
    for item in request:
        t=copy.deepcopy(item['task']);t['task_id']=item['legacy_task_id'];t['difficulty']='easy';t['gold']={}
        captured=[]
        def capture(name,args):
            result=original(name,args);captured.append((name,result));return result
        old.execute_tool=capture;start=time.perf_counter();record=None;error=None
        try:record=old.run_task(t,contract_protection=False)
        except Exception as e:error=type(e).__name__+': '+str(e)
        elapsed=time.perf_counter()-start
        result={}
        if captured:
            tool,obs=captured[-1]
            if tool=='load_table':answer={'columns':obs['columns'],'rows':obs['rows']}
            elif tool=='aggregate':answer=obs['totals']
            elif tool=='task_analysis':answer=obs['operation']
            else:answer=obs
            # This is a measured harness receipt, not fabricated analytical evidence.
            result={'answer':answer,'evidence':{'input_sha256':hashlib.sha256(Path(t['dataset']['uri']).read_bytes()).hexdigest(),'rows_read':0}}
            with Path(t['dataset']['uri']).open(encoding='utf-8',newline='') as f:result['evidence']['rows_read']=sum(1 for _ in __import__('csv').DictReader(f))
        cases.append({'task_id':item['task']['task_id'],'source_id':item['task']['source_id'],'result':result,'trace':record['trace'] if record else [],'cost':{'wall_seconds_including_profile':elapsed},'error':error})
    old.execute_tool=original;output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps({'native':native,'common':cases},ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':main()
