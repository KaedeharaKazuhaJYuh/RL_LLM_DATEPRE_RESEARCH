"""Direct DeepSeek comparator on the frozen sequential validation protocol."""
import argparse
import json
import time
from pathlib import Path
from agent.llm import LLMClient
from research.io import append_jsonl,write_json
from research.v4_sequence_env import SequenceEnv


def run(protocol,out):
    protocol=Path(protocol);out=Path(out).resolve()
    if out.exists():raise FileExistsError('new output directory required')
    tasks=json.loads((protocol/'tasks.json').read_text(encoding='utf-8'))
    gold=json.loads((protocol/'oracle.json').read_text(encoding='utf-8'))
    client=LLMClient();out.mkdir(parents=True);rows=[];calls=0;usage={'prompt_tokens':0,'completion_tokens':0}
    for task in tasks:
        if task['split']!='validation':continue
        for fault in (False,True):
            env=SequenceEnv(task,gold[task['task_id']],out/task['task_id']/str(int(fault)),fault)
            api_error=None;repaired=0;episode_api=0;start=time.perf_counter();trace=[]
            while not env.done:
                obs=env.observation();calls+=1;episode_api+=1
                try:
                    decision=client.choose_step({**task,'fixed_bindings':True},obs,task['allowed_tools'])
                    repaired+=int(client.last_format_repaired)
                    env.step(decision['action'])
                    trace.append({'observation':obs,'action':decision['action']})
                except Exception as exc:
                    api_error=type(exc).__name__;env.decisions+=1;env.done=True
                for key in usage:usage[key]+=client.last_usage.get(key,0)
                append_jsonl(out/'requests.jsonl',{'task_id':task['task_id'],'fault':fault,'request':calls,
                    'usage':dict(client.last_usage),'response_id':client.last_response_id,
                    'error_type':api_error,'format_repaired':client.last_format_repaired})
            result=env.result()
            if api_error:result['passed']=False;result['reward']=-.05*env.calls-.01*max(1,env.decisions)
            row={'task_id':task['task_id'],'source_id':task['source_id'],'fault':fault,**result,
                 'api_requests':episode_api,'wall_seconds':time.perf_counter()-start,
                 'format_repairs':repaired,'error_type':api_error,'steps':trace}
            rows.append(row);append_jsonl(out/'episodes.jsonl',row)
            write_json(out/'summary.json',{'protocol':'v4-sequence-1','model':client.model,'temperature':client.temperature,
                'episodes':len(rows),'passed':sum(r['passed'] for r in rows),'api_requests':calls,'usage':usage,
                'api_failures':sum(r['error_type'] is not None for r in rows),
                'format_repairs':sum(r['format_repairs'] for r in rows),
                'mean_reward':sum(r['reward'] for r in rows)/len(rows),
                'mean_calls':sum(r['tool_calls'] for r in rows)/len(rows),'records':rows})
            if api_error and api_error not in ('JSONDecodeError','ValueError'):
                raise RuntimeError('API connectivity failure; partial results retained')
    return json.loads((out/'summary.json').read_text(encoding='utf-8'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--protocol',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();r=run(a.protocol,a.out);print(json.dumps({k:v for k,v in r.items() if k!='records'},indent=2))
