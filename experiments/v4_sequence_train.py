"""Train on expert development traces, then episodic rewards; frozen source holdout."""
import argparse
import copy
import json
import tempfile
from pathlib import Path
import numpy as np
from research.io import ROOT,append_jsonl,write_json
from research.v4_sequence_env import build,SequenceEnv
from research.v4_sequence_policy import SequencePolicy


def rollout(policy,task,gold,folder,fault=False,training=False):
    env=SequenceEnv(task,gold,folder,fault);trajectory=[];steps=[]
    while not env.done:
        obs=env.observation();action,cache=policy.select(obs,training)
        env.step(action);trajectory.append(cache)
        steps.append({'observation':obs,'action':action,'probability':float(cache[2][cache[1]])})
    result=env.result()
    for step in steps:step['return']=result['reward']
    return result,trajectory,steps


def run(out,epochs=20,seeds=(1,2,3)):
    out=Path(out).resolve()
    if out.exists():raise FileExistsError('new output directory required')
    tasks,gold=build(out/'protocol');train=[t for t in tasks if t['split']=='train'];validation=[t for t in tasks if t['split']=='validation']
    assert not {t['source_id'] for t in train}&{t['source_id'] for t in validation}
    demonstrations=[];records=[];curves=[]
    with tempfile.TemporaryDirectory(prefix='v4_sequence_') as scratch:
        for task in train:
            for fault in (False,True):
                env=SequenceEnv(task,gold[task['task_id']],scratch,fault)
                while not env.done:
                    obs=env.observation();done=sum(h['ok'] for h in env.history)
                    action=gold[task['task_id']]['plan'][done] if done<2 else 'stop'
                    env.step(action)
                    demonstrations.append({'task_id':task['task_id'],'source_id':task['source_id'],'split':'train',
                                           'condition':'fault' if fault else 'clean','observation':obs,'action':action})
                assert env.result()['passed']
        for d in demonstrations:append_jsonl(out/'supervised.jsonl',d)
        for seed in seeds:
            sft=SequencePolicy(seed);sft.fit(demonstrations)
            rl=copy.deepcopy(sft);baseline=0.
            rng=np.random.default_rng(seed)
            items=[(t,f) for t in train for f in (False,True)]
            for epoch in range(epochs):
                epoch_rows=[]
                for index in rng.permutation(len(items)):
                    task,fault=items[int(index)]
                    result,trajectory,steps=rollout(rl,task,gold[task['task_id']],scratch,fault,True)
                    rl.reinforce(trajectory,result['reward'],baseline)
                    baseline=.95*baseline+.05*result['reward']
                    row={'seed':seed,'epoch':epoch+1,'task_id':task['task_id'],'fault':fault,**result}
                    append_jsonl(out/'rl_rewards.jsonl',row);epoch_rows.append(row)
                    if epoch==epochs-1:append_jsonl(out/'rl_final_trajectories.jsonl',{**row,'steps':steps})
                curves.append({'seed':seed,'epoch':epoch+1,'pass_rate':sum(r['passed'] for r in epoch_rows)/len(epoch_rows),
                               'mean_reward':sum(r['reward'] for r in epoch_rows)/len(epoch_rows)})
            for name,policy in [('supervised',sft),('supervised_reinforce',rl)]:
                before=policy.fingerprint()
                for task in validation:
                    for fault in (False,True):
                        result,_,steps=rollout(policy,task,gold[task['task_id']],scratch,fault)
                        row={'method':name,'seed':seed,'task_id':task['task_id'],'fault':fault,**result}
                        records.append(row);append_jsonl(out/'validation.jsonl',{**row,'steps':steps})
                assert before==policy.fingerprint()
                np.savez(out/f'{name}_{seed}.npz',weights=policy.weights)
    groups=[]
    for seed in seeds:
        for method in ('supervised','supervised_reinforce'):
            rows=[r for r in records if r['seed']==seed and r['method']==method]
            groups.append({'method':method,'seed':seed,'passed':sum(r['passed'] for r in rows),'episodes':len(rows),
                'mean_reward':sum(r['reward'] for r in rows)/len(rows),
                'mean_calls':sum(r['tool_calls'] for r in rows)/len(rows),
                'extra_calls':sum(r['extra_calls'] for r in rows)})
    result={'protocol':'v4-sequence-1','algorithm':'SFT + on-policy episodic REINFORCE, undiscounted return, past-only moving baseline',
        'llm_weights_updated':False,'train_tasks':len(train),'validation_tasks':len(validation),'demonstration_steps':len(demonstrations),
        'training_episodes_per_seed':epochs*len(train)*2,'seeds':list(seeds),'results':groups,'curves':curves,
        'evaluation_updates':False,'records':records}
    write_json(out/'summary.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--epochs',type=int,default=20)
    a=p.parse_args();r=run(a.out,a.epochs);print(json.dumps(r['results'],indent=2))
