"""Single-step runtime. No hidden labels are supplied to the policy."""
import json,time,hashlib
from pathlib import Path
from agent.tools import ACTIONS,execute_tool
from research.io import resolve,digest,load_jsonl,read_table
from research.features import profile,encode
from verifier.score import verify

def load_bundle(tasks_path='tasks/v2/tasks.jsonl',oracle_path='tasks/v2/oracle.json'):
    tasks=load_jsonl(tasks_path);oracles=json.loads(resolve(oracle_path).read_text(encoding='utf-8'))
    ids=[t['task_id'] for t in tasks]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate task IDs')
    for t in tasks:
        if t.get('schema_version')!=2:raise ValueError('v2 requires schema_version 2; old benchmark is historical')
        if 'gold' in t or '_reference' in t:raise ValueError('public task contains oracle fields')
        if t['task_id'] not in oracles or 'expected' not in oracles[t['task_id']]:raise ValueError('missing oracle')
        if set(t['allowed_tools'])-set(ACTIONS):raise ValueError('unsupported allowed tool')
    return tasks,oracles

def run_task(task,policy,oracle,artifact_dir,training=False,forced_action=None):
    start=time.perf_counter();trace=[];result={};state={};next_state={};action=None;probability=None;features=None;error=None
    policy.last_usage={};policy.last_choice=None
    constraints=task['constraints'];input_hash=None
    try:
        path=resolve(task['dataset']['uri']);input_hash=digest(path)
        if input_hash!=task['dataset']['sha256']:raise ValueError('input hash mismatch')
        dp=profile(path)
        if dp['columns']!=task['dataset']['columns']:raise ValueError('input schema mismatch')
        features=encode(task,dp,policy.data_only)
        state={'prompt':task['prompt'],'params':task['params'],'data_profile':dp,'features':features.tolist(),'remaining_calls':constraints['max_tool_calls'],'history':[]}
        if constraints['max_tool_calls']<1 or constraints['max_steps']<1:raise ValueError('no action budget')
        action,probability=(forced_action,1.0) if forced_action else policy.select(task,features,task['allowed_tools'],training,state)
        if action not in task['allowed_tools']:raise ValueError('illegal proposed action')
        if time.perf_counter()-start>=constraints['max_seconds']:raise TimeoutError('deadline before tool')
        tool_start=time.perf_counter()
        result=execute_tool(action,{'uri':str(path),'params':task['params'],'artifact_dir':artifact_dir})
        elapsed=time.perf_counter()-start
        trace.append({'tool':action,'ok':True,'parameters':task['params'],'observation':result,'elapsed_seconds':time.perf_counter()-tool_start})
        next_state={**state,'remaining_calls':constraints['max_tool_calls']-1,'history':trace,'terminal':True}
        if elapsed>constraints['max_seconds']:raise TimeoutError('deadline exceeded')
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)
        if action and not trace:trace.append({'tool':action,'ok':False,'parameters':task['params'],'error':error})
        next_state={**state,'terminal':True,'error':error}
    elapsed=time.perf_counter()-start
    checked=verify(result,oracle,trace,{**constraints,'allowed_tools':task['allowed_tools'],'input_sha256':input_hash,'elapsed_seconds':elapsed})
    if error:checked['passed']=False;checked['score']=0.0
    if training and policy.mode=='bandit' and features is not None and action in ACTIONS:policy.update(action,features,checked['score'])
    return {'schema_version':2,'task_id':task['task_id'],'source_id':task['source_id'],'split':task['split'],'state':state,'proposed_action':action,'executed_action':trace[0]['tool'] if trace else None,'action_probability':probability,'intervention':None,'trace':trace,'result':result,'next_state':next_state,'terminal':True,'termination_reason':error or 'single_step_completed','reward_components':{'success':int(checked['passed']),'tool_cost_penalty':.05 if checked['passed'] else 0},**checked,'tool_calls':len(trace),'cost':{'wall_seconds_including_profile':elapsed,'llm_calls':int(policy.mode=='llm'),'input_tokens':policy.last_usage.get('prompt_tokens',0),'output_tokens':policy.last_usage.get('completion_tokens',0)},'mode':policy.mode,'training':training,'model_choice':policy.last_choice}
