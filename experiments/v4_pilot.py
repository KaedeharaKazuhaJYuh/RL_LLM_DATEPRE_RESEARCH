"""Development-only paired DeepSeek / bandit / hybrid pilot. Never uses test split."""
import argparse
import hashlib
import json
import tempfile
import time
from pathlib import Path
import numpy as np
from agent.llm import LLMClient
from agent.tools import ACTIONS
from research.features import profile
from research.io import ROOT, append_jsonl, digest, write_json
from research.policies import Policy
from research.runtime import load_bundle, run_task
from research.v4_hybrid import HybridPolicy


def state_hash(policy):
    return hashlib.sha256(policy.inv.tobytes()+policy.b.tobytes()+policy.weights.tobytes()).hexdigest()


def subset(tasks, split, limit):
    # Public order only: no gold action is used to balance/select cases.
    return sorted((t for t in tasks if t['split'] == split), key=lambda t:t['task_id'])[:limit]


def run(client, out, limit=12, epochs=6, seeds=(1,2,3), live=True):
    if limit < 1 or epochs < 1 or not seeds:
        raise ValueError('positive limit/epochs and at least one seed required')
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError('choose a new output directory')
    tasks, gold = load_bundle()
    train, validation = subset(tasks,'train',limit), subset(tasks,'validation',limit)
    if not train or not validation:
        raise ValueError('nonempty development splits required')
    if {t['source_id'] for t in train} & {t['source_id'] for t in validation}:
        raise ValueError('source overlap')
    out.mkdir(parents=True)
    suggestions = {}; observations = []; by_id = {}
    manifest = {'phase':'V4 development pilot', 'live_api':live, 'test_split_used':False,
                'provider':'deepseek' if live else 'mock', 'model':getattr(client,'model','mock'),
                'temperature':getattr(client,'temperature',None), 'epochs':epochs,'seeds':list(seeds),
                'train_ids':[t['task_id'] for t in train], 'validation_ids':[t['task_id'] for t in validation],
                'tasks_sha256':digest(ROOT/'tasks/v2/tasks.jsonl'),
                'reward':'existing independent verifier score; only executed training action updated',
                'llm_weights_updated':False,'data_scope':'reused V2 development data; not V4 external test'}
    write_json(out/'manifest.json',manifest)
    for task in train+validation:
        dp = profile(task['dataset']['uri'])
        state = {'data_profile':dp, 'remaining_calls':task['constraints']['max_tool_calls'], 'history':[]}
        started = time.perf_counter()
        try:
            choice = client.choose(task,state,task['allowed_tools'])
            if choice['action'] not in task['allowed_tools']:
                raise ValueError('invalid provider action')
        except Exception as exc:
            # Keep paid successful observations, but never persist provider error bodies or secrets.
            write_json(out/'failure.json',{'stage':'suggestion_collection','completed':len(observations),
                                         'exception_type':type(exc).__name__})
            raise RuntimeError('DeepSeek collection stopped; inspect failure.json and configuration') from None
        suggestions[task['task_id']] = choice['action']
        row = {'task_id':task['task_id'],'split':task['split'],'action':choice['action'],
               'usage':dict(client.last_usage),'response_id':getattr(client,'last_response_id',None),
               'wall_seconds':time.perf_counter()-started}
        observations.append(row); by_id[task['task_id']]=row; append_jsonl(out/'suggestions.jsonl',row)
    records=[]; curves=[]; frozen=[]
    with tempfile.TemporaryDirectory(prefix='v4_pilot_') as temp:
        direct=Policy('rule')
        for task in validation:
            bounded={**task,'constraints':{**task['constraints'],'max_seconds':max(0,task['constraints']['max_seconds']-by_id[task['task_id']]['wall_seconds'])}}
            result=run_task(bounded,direct,gold[task['task_id']],Path(temp)/'direct'/task['task_id'],
                            forced_action=suggestions[task['task_id']])
            result['inference_seconds']=result['cost']['wall_seconds_including_profile']+by_id[task['task_id']]['wall_seconds']
            records.append({'method':'deepseek_direct','seed':None,**result})
        for seed in seeds:
            for name in ('bandit','deepseek_bandit'):
                policy=Policy('bandit',seed) if name=='bandit' else HybridPolicy(suggestions,seed)
                rng=np.random.default_rng(seed)
                for epoch in range(epochs):
                    successes=0
                    for i in rng.permutation(len(train)):
                        task=train[int(i)]
                        result=run_task(task,policy,gold[task['task_id']],Path(temp)/name/str(seed)/str(epoch)/task['task_id'],training=True)
                        successes+=int(result['passed'])
                        append_jsonl(out/'training.jsonl',{'method':name,'seed':seed,'epoch':epoch+1,
                                    'task_id':task['task_id'],'action':result['proposed_action'],
                                    'reward':result['score'],'passed':result['passed'],
                                    'action_probability':result['action_probability']})
                    curves.append({'method':name,'seed':seed,'epoch':epoch+1,'passed':successes,'tasks':len(train)})
                before=state_hash(policy)
                for task in validation:
                    api_seconds=by_id[task['task_id']]['wall_seconds'] if name=='deepseek_bandit' else 0
                    bounded={**task,'constraints':{**task['constraints'],'max_seconds':max(0,task['constraints']['max_seconds']-api_seconds)}}
                    result=run_task(bounded,policy,gold[task['task_id']],Path(temp)/name/str(seed)/'validation'/task['task_id'])
                    result['inference_seconds']=result['cost']['wall_seconds_including_profile']+api_seconds
                    records.append({'method':name,'seed':seed,**result})
                if state_hash(policy)!=before:
                    raise AssertionError('validation mutated learner')
                policy.save(out/f'{name}_seed{seed}.npz')
                frozen.append({'method':name,'seed':seed,'sha256':before})
        # Persist compact verified trajectories; scratch artifact paths are not retained as deliverables.
        for row in records:
            append_jsonl(out/'validation.jsonl',{k:row[k] for k in
                         ('method','seed','task_id','source_id','proposed_action','passed','score','tool_calls','termination_reason','inference_seconds')})
    summaries=[]
    for name,seed in [('deepseek_direct',None)]+[(m,s) for s in seeds for m in ('bandit','deepseek_bandit')]:
        rows=[r for r in records if r['method']==name and r['seed']==seed]
        summaries.append({'method':name,'seed':seed,'passed':sum(r['passed'] for r in rows),
                          'tasks':len(rows),'pass_rate':sum(r['passed'] for r in rows)/len(rows),
                          'mean_inference_seconds':sum(r['inference_seconds'] for r in rows)/len(rows)})
    result={**manifest,'results':summaries,'training_curve':curves,'frozen_policies':frozen,
            'api_requests':len(observations) if live else 0,
            'api_input_tokens':sum(r['usage'].get('prompt_tokens',0) for r in observations) if live else 0,
            'api_output_tokens':sum(r['usage'].get('completion_tokens',0) for r in observations) if live else 0,
            'api_wall_seconds':sum(r['wall_seconds'] for r in observations) if live else 0,
            'cost_currency':None,'note':'one shared frozen LLM suggestion per task; training seeds are not independent API repetitions'}
    write_json(out/'summary.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True)
    parser.add_argument('--limit',type=int,default=12)
    parser.add_argument('--epochs',type=int,default=6)
    args=parser.parse_args()
    result=run(LLMClient(),args.out,args.limit,args.epochs)
    print(json.dumps(result['results'],indent=2))


if __name__=='__main__':main()
