"""Predeclared batch/anchor ablation; never select checkpoints on validation."""
import argparse
import copy
import json
import tempfile
from pathlib import Path
import numpy as np
from experiments.v4_sequence_train import rollout
from research.io import ROOT,load_jsonl,write_json,append_jsonl
from research.v4_sequence_policy import SequencePolicy,features,CHOICES


def diagnostics(policy, reference, demos):
    X=[features(d['observation']) for d in demos]
    P=np.array([policy.probs(x) for x in X]);Q=np.array([reference.probs(x) for x in X])
    targets=np.array([CHOICES.index(d['action']) for d in demos])
    return {'expert_action_probability':float(P[np.arange(len(P)),targets].mean()),
            'expert_argmax_accuracy':float((P.argmax(1)==targets).mean()),
            'reference_kl':float(np.mean(np.sum(Q*np.log(np.maximum(Q,1e-15)/np.maximum(P,1e-15)),axis=1))),
            'weight_distance':float(np.linalg.norm(policy.weights-reference.weights))}


def run(out, previous, epochs=20):
    out=Path(out);previous=Path(previous)
    if out.exists():raise FileExistsError('new output directory required')
    out.mkdir(parents=True)
    tasks=json.loads((previous/'protocol/tasks.json').read_text(encoding='utf-8'))
    gold=json.loads((previous/'protocol/oracle.json').read_text(encoding='utf-8'))
    demos=load_jsonl(previous/'supervised.jsonl')
    train=[t for t in tasks if t['split']=='train'];validation=[t for t in tasks if t['split']=='validation']
    assert {d['source_id'] for d in demos}<={t['source_id'] for t in train}
    assert not {t['source_id'] for t in train}&{t['source_id'] for t in validation}
    configs={'batch_only':{'bc_weight':0.,'kl_weight':0.},
             'batch_anchored':{'bc_weight':.2,'kl_weight':.5}}
    manifest={'epochs':epochs,'seeds':[1,2,3],'batch_size':48,'lr':.1,'max_step_kl':.01,
              'configs':configs,'baseline':'past-only task and fault EMA; initial zero',
              'selection':'fixed final epoch; no validation tuning','llm_weights_updated':False}
    write_json(out/'manifest.json',manifest)
    results=[];diagnostic_rows=[]
    with tempfile.TemporaryDirectory(prefix='v4_stable_') as scratch:
        for seed in (1,2,3):
            sft=SequencePolicy(seed);sft.weights=np.load(previous/f'supervised_{seed}.npz')['weights']
            old=copy.deepcopy(sft);old.weights=np.load(previous/f'supervised_reinforce_{seed}.npz')['weights']
            for name,policy in [('supervised',sft),('original_reinforce',old)]:
                diagnostic_rows.append({'seed':seed,'method':name,**diagnostics(policy,sft,demos)})
            for method,config in configs.items():
                policy=copy.deepcopy(sft);baselines={};items=[(t,f) for t in train for f in (False,True)]
                rng=np.random.default_rng(seed)
                for epoch in range(epochs):
                    episodes=[];used_baselines=[];rows=[];keys=[]
                    for index in rng.permutation(len(items)):
                        task,fault=items[int(index)];key=(task['task_id'],fault)
                        result,trajectory,_=rollout(policy,task,gold[task['task_id']],scratch,fault,True)
                        episodes.append((trajectory,result['reward']));used_baselines.append(baselines.get(key,0.));keys.append(key)
                        rows.append(result)
                    update=policy.batch_reinforce(episodes,used_baselines,demos,sft,**config)
                    for key,(_,reward) in zip(keys,episodes):baselines[key]=.9*baselines.get(key,0.)+.1*reward
                    append_jsonl(out/'curves.jsonl',{'seed':seed,'method':method,'epoch':epoch+1,
                        'sampled_train_pass_rate':sum(r['passed'] for r in rows)/len(rows),
                        'sampled_train_reward':float(np.mean([r['reward'] for r in rows])),**update,**diagnostics(policy,sft,demos)})
                before=policy.fingerprint();eval_rows=[]
                for task in validation:
                    for fault in (False,True):
                        result,_,steps=rollout(policy,task,gold[task['task_id']],scratch,fault)
                        row={'seed':seed,'method':method,'task_id':task['task_id'],'fault':fault,**result}
                        eval_rows.append(row);append_jsonl(out/'validation.jsonl',{**row,'steps':steps})
                assert before==policy.fingerprint()
                diagnostic_rows.append({'seed':seed,'method':method,**diagnostics(policy,sft,demos)})
                results.append({'seed':seed,'method':method,'passed':sum(r['passed'] for r in eval_rows),
                    'episodes':len(eval_rows),'mean_reward':float(np.mean([r['reward'] for r in eval_rows])),
                    'mean_calls':float(np.mean([r['tool_calls'] for r in eval_rows]))})
                np.savez(out/f'{method}_{seed}.npz',weights=policy.weights)
                print(json.dumps(results[-1]),flush=True)
    summary={'manifest':manifest,'results':results,'diagnostics':diagnostic_rows,
             'original_summary':str(previous/'summary.json'),'training_episodes':epochs*48*3*len(configs)}
    write_json(out/'summary.json',summary)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True)
    p.add_argument('--previous',default=str(ROOT/'work/v4_sequence_train_001'))
    a=p.parse_args();run(a.out,a.previous)
