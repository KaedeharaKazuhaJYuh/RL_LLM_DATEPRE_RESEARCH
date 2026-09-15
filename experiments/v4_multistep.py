"""Live development episodes with generated parameters, real state and terminal rewards.

Collects trajectories for later RL; does not update any policy or provider weights.
"""
import argparse
import json
import time
from pathlib import Path
from agent.llm import LLMClient
from agent.tools import execute_tool, MUTATING
from research.io import ROOT, digest, load_jsonl, write_json, append_jsonl, write_table
from research.features import profile
from research.oracle import expected
from research.v3_runtime import params_for
from verifier.score import verify


def summarize(out):
    out=Path(out)
    manifest=json.loads((out/'manifest.json').read_text(encoding='utf-8'))
    records=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(out.glob('*/*/episode.json'))]
    result={'model':manifest['model'],'temperature':manifest['temperature'],'episodes':len(records),
        'planned_episodes':len(manifest['ids'])*2,'development_only':True,'policy_updates':False,
        'by_condition':{c:{'passed':sum(r['passed'] for r in records if r['condition']==c),
            'episodes':sum(r['condition']==c for r in records),
            'injection_applied':sum(r['injection_applied'] for r in records if r['condition']==c),
            'response_or_api_failures':sum(r['api_error_type'] is not None for r in records if r['condition']==c)}
            for c in ('clean','injected_column')},
        'api_requests':sum(r['api_requests'] for r in records),
        'input_tokens_recorded':sum(r['api_input_tokens'] for r in records),
        'output_tokens_recorded':sum(r['api_output_tokens'] for r in records),
        'usage_may_be_incomplete':any(r['api_error_type'] for r in records),
        'records':records}
    write_json(out/'summary.json',result)
    return result


def reference(task, gold, folder):
    current=ROOT/task['dataset']['uri']
    final=None
    for i,action in enumerate(gold['plan']):
        final=expected(current,action,params_for(action,task))
        if 'artifact_rows' in final:
            current=folder/f'reference_{i}.csv'
            write_table(current,final['artifact_columns'],final['artifact_rows'])
    return final


def episode(task, gold, client, folder, inject=False, max_calls=3):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    current=ROOT/task['dataset']['uri'];initial=digest(current)
    if initial!=task['dataset']['sha256']:raise ValueError('input hash mismatch')
    history=[];trace=[];successful=[];last={};last_input=None;calls=0;api_calls=0;injected=False
    started=time.perf_counter();error=None
    for step in range(max_calls):
        if time.perf_counter()-started>=90:break
        state={'data_profile':profile(current),'history':history,'remaining_calls':max_calls-calls}
        api_calls+=1
        try:
            decision=client.choose_step(task,state,task['allowed_tools'])
        except Exception as exc:
            error=type(exc).__name__
            append_jsonl(folder/'api_failure.jsonl',{'exception_type':error,'request_index':api_calls})
            break
        action=decision.get('action')
        row={'step':step,'decision':decision,'usage':dict(client.last_usage),
             'response_id':getattr(client,'last_response_id',None)}
        if action=='stop':
            trace.append({**row,'stop':True});break
        calls+=1
        params=dict(decision.get('params',{}));before=digest(current)
        if inject and not injected and 'column' in params:
            params['column']='__injected_missing_column__';injected=True
        try:
            if action not in task['allowed_tools']:raise ValueError('forbidden tool')
            result=execute_tool(action,{'uri':str(current),'params':params,'artifact_dir':folder/f'step_{step}'})
            checked=verify(result,expected(current,action,params),[{'tool':action,'ok':True}],
                           {'allowed_tools':task['allowed_tools'],'max_steps':1,'max_tool_calls':1,
                            'max_seconds':90,'elapsed_seconds':time.perf_counter()-started,'input_sha256':before})
            if not checked['passed']:raise ValueError('tool output failed integrity check')
            last=result;last_input=before;successful.append(action)
            if action in MUTATING:current=Path(result['artifact']['path'])
            observation={'ok':True,'answer':result['answer'],'input_sha256':before,'output_sha256':digest(current)}
        except (ValueError,KeyError,OSError,TypeError) as exc:
            observation={'ok':False,'error':type(exc).__name__+': '+str(exc),'input_sha256':before}
        history.append({'action':action,'executed_params':params,'observation':observation})
        trace.append({**row,**history[-1]})
        append_jsonl(folder/'steps.jsonl',trace[-1])
    target=reference(task,gold,folder)
    check=verify(last,target,[{'tool':a,'ok':True} for a in successful],
                 {'allowed_tools':task['allowed_tools'],'max_steps':max_calls,'max_tool_calls':max_calls,
                  'max_seconds':90,'elapsed_seconds':time.perf_counter()-started,'input_sha256':last_input})
    passed=check['passed'] and successful==gold['plan'] and digest(ROOT/task['dataset']['uri'])==initial and error is None
    reward=int(passed)-.05*calls-.02*api_calls
    for row in trace:row['terminal_return']=reward
    result={'task_id':task['task_id'],'source_id':task['source_id'],'condition':'injected_column' if inject else 'clean',
            'injection_applied':injected,'passed':passed,'successful_actions':successful,'tool_calls':calls,
            'api_requests':api_calls,'api_input_tokens':sum(r['usage'].get('prompt_tokens',0) for r in trace),
            'api_output_tokens':sum(r['usage'].get('completion_tokens',0) for r in trace),
            'api_error_type':error,'reward':reward,'elapsed_seconds':time.perf_counter()-started,'trace':trace}
    write_json(folder/'episode.json',result)
    return result


def run(client,out,limit=6):
    if not 1<=limit<=6:raise ValueError('pilot limit must be between 1 and 6')
    out=Path(out).resolve()
    if out.exists():raise FileExistsError('choose new output directory')
    tasks=load_jsonl('tasks/v3/tasks.jsonl');selected=[];prompts=set()
    for task in sorted(tasks,key=lambda t:(t['source_id'],t['task_id'])):
        if task['split']=='train' and task['track']=='composition' and task['prompt'] not in prompts:
            selected.append(task);prompts.add(task['prompt'])
        if len(selected)==limit:break
    gold=json.loads((ROOT/'tasks/v3/oracle.json').read_text(encoding='utf-8'))
    out.mkdir(parents=True)
    write_json(out/'manifest.json',{'model':client.model,'temperature':client.temperature,
        'development_only':True,'tasks_sha256':digest(ROOT/'tasks/v3/tasks.jsonl'),
        'max_requests':len(selected)*6,'reward':'verified_success - 0.05*tool_calls - 0.02*api_requests',
        'policy_updates':False,'ids':[t['task_id'] for t in selected]})
    records=[]
    for task in selected:
        for inject in (False,True):
            row=episode(task,gold[task['task_id']],client,out/task['task_id']/str(int(inject)),inject)
            records.append(row)
            if row['api_error_type']:
                summarize(out)
                raise RuntimeError('API episode failed; completed records retained without automatic retry')
    result={'model':client.model,'temperature':client.temperature,'episodes':len(records),
            'development_only':True,'policy_updates':False,
            'by_condition':{condition:{'passed':sum(r['passed'] for r in records if r['condition']==condition),
                           'episodes':sum(r['condition']==condition for r in records)} for condition in ('clean','injected_column')},
            'api_requests':sum(r['api_requests'] for r in records),
            'input_tokens':sum(r['api_input_tokens'] for r in records),'output_tokens':sum(r['api_output_tokens'] for r in records),
            'records':records}
    write_json(out/'summary.json',result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);parser.add_argument('--limit',type=int,default=6)
    args=parser.parse_args();result=run(LLMClient(),args.out,args.limit)
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2))
