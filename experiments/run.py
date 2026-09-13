"""Train on train sources; evaluate frozen policies on test sources."""
import argparse,hashlib,json,platform,statistics,time
import numpy as np
from research.io import ROOT,resolve,digest,write_json,append_jsonl
from research.runtime import load_bundle,run_task
from research.features import profile,encode
from research.policies import Policy
def code_digest():
    h=hashlib.sha256()
    for folder in ('agent','verifier','research','experiments'):
        for p in sorted((ROOT/folder).glob('*.py')):h.update(p.relative_to(ROOT).as_posix().encode());h.update(p.read_bytes())
    return h.hexdigest()
def summarize(rows):
    if not rows:raise ValueError('empty evaluation')
    return {'tasks':len(rows),'passed':sum(r['passed'] for r in rows),'pass_rate':sum(r['passed'] for r in rows)/len(rows),'mean_score':statistics.mean(r['score'] for r in rows),'mean_tool_calls':statistics.mean(r['tool_calls'] for r in rows),'mean_wall_seconds':statistics.mean(r['cost']['wall_seconds_including_profile'] for r in rows)}
def experiment(mode='rule',seed=1,epochs=6,out='reports/v2/rule_seed1.jsonl',tasks_path='tasks/v2/tasks.jsonl',oracle_path='tasks/v2/oracle.json',data_only=False):
    tasks,oracles=load_bundle(tasks_path,oracle_path);train=[t for t in tasks if t['split']=='train'];test=[t for t in tasks if t['split']=='test']
    if {t['source_id'] for t in train}&{t['source_id'] for t in test}:raise ValueError('source leakage')
    policy=Policy(mode,seed,data_only=data_only);rng=np.random.default_rng(seed);output=resolve(out);output.parent.mkdir(parents=True,exist_ok=True)
    if output.exists():raise FileExistsError(f'refusing overwrite: {output}')
    artifacts=ROOT/'artifacts'/output.parent.name/output.stem
    if artifacts.exists():raise FileExistsError(f'artifact namespace already exists: {artifacts}')
    train_log=artifacts/'train.jsonl';curve=[];start=time.perf_counter()
    if mode=='bandit':
        for epoch in range(epochs):
            rows=[]
            for index in rng.permutation(len(train)):
                t=train[int(index)];r=run_task(t,policy,oracles[t['task_id']],artifacts/'train'/str(epoch)/t['task_id'],training=True);append_jsonl(train_log,r);rows.append(r)
            curve.append({'epoch':epoch+1,**summarize(rows)})
    elif mode=='supervised':
        policy.fit_supervised([encode(t,profile(t['dataset']['uri']),data_only) for t in train],[oracles[t['task_id']]['training_action'] for t in train])
    training_seconds=time.perf_counter()-start
    metadata={'version':2,'mode':mode,'seed':seed,'epochs':epochs if mode=='bandit' else 0,'data_only':data_only,'code_sha256':code_digest(),'tasks_sha256':digest(resolve(tasks_path)),'oracle_sha256':digest(resolve(oracle_path)),'numpy':np.__version__,'python':platform.python_version(),'model':policy.llm.model if policy.llm else None,'temperature':policy.llm.temperature if policy.llm else None,'evaluation_split':'test','updates_during_evaluation':False,'contract_mask':False,'training_interactions':len(train)*epochs if mode=='bandit' else 0,'supervised_labels':len(train) if mode=='supervised' else 0,'training_wall_seconds':training_seconds,'train_log':str(train_log.relative_to(ROOT)) if mode=='bandit' else None}
    before=policy.b.copy();records=[]
    for t in test:
        r=run_task(t,policy,oracles[t['task_id']],artifacts/'test'/t['task_id']);r['run_metadata']=metadata;append_jsonl(output,r);records.append(r)
    if not np.array_equal(before,policy.b):raise AssertionError('test modified policy')
    artifacts.mkdir(parents=True,exist_ok=True);policy.save(artifacts/'policy.npz')
    summary={**summarize(records),'run_metadata':metadata,'training_curve':curve};write_json(output.with_suffix('.summary.json'),summary);return summary
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=['rule','random','majority','supervised','bandit','llm'],default='rule');p.add_argument('--seed',type=int,default=1);p.add_argument('--epochs',type=int,default=6);p.add_argument('--data-only',action='store_true');p.add_argument('--tasks',default='tasks/v2/tasks.jsonl');p.add_argument('--oracle',default='tasks/v2/oracle.json');p.add_argument('--out',default='reports/v2/rule_seed1.jsonl');a=p.parse_args()
    if a.epochs<1:p.error('epochs must be positive')
    print(json.dumps(experiment(a.mode,a.seed,a.epochs,a.out,a.tasks,a.oracle,a.data_only),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
