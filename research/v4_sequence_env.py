"""Versioned development tasks and final-state scoring for sequential control."""
import copy
import hashlib
import json
import time
from pathlib import Path
from agent.tools import ACTIONS, MUTATING, execute_tool
from research.io import ROOT, load_jsonl, digest, read_table, write_table, write_json
from research.stage_profile import scope
from research.oracle import expected
from research.v3_runtime import params_for
from verifier.score import verify, _same

SPECS = [
    (['deduplicate','profile_missingness'], '删除完全重复记录并保存，然后报告每列的缺失率。'),
    (['fill_missing','describe_numeric'], '用中位数填补 {value} 的空值并保存，然后报告该列的描述统计。'),
    (['normalize_categories','count_categories'], '去除 {category} 的首尾空格并统一为大写并保存，然后统计该列各类别频数。'),
    (['normalize_dates','aggregate'], '将 {date} 统一为 YYYY-MM-DD，无法解析值置空并保存，然后按 {date} 汇总 {value}，空数值跳过，空日期仍作为一组。'),
    (['clip_outliers','correlate'], '将 {value} 截断到 [0,100] 并保存，然后计算 {value} 与 {metric} 的相关系数。'),
    (['deduplicate','rolling_mean'], '删除完全重复记录并保存，然后按当前行序计算 {metric} 列的三期完整窗口移动平均。')]


def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    old=load_jsonl('tasks/v3/tasks.jsonl')
    sources=sorted({t['source_id'] for t in old if t['split']=='train'})[:6]
    tasks=[];gold={}
    for source in sources:
        base=next(t for t in old if t['source_id']==source)
        for index,(plan,text) in enumerate(SPECS):
            task=copy.deepcopy(base);p=task['params']
            tid=hashlib.sha256(f'v4-sequence-1/{source}/{index}'.encode()).hexdigest()[:16]
            task.update(task_id=tid,split='train' if source in sources[:4] else 'validation',
                        prompt=text.format(value=p['column'],category=p['category_column'],date=p['date_column'],metric=p['other_column'])+' 完成以上要求后必须选择 stop，不要进行额外清理。',
                        constraints={'max_steps':4,'max_tool_calls':3,'max_seconds':120})
            tasks.append(task);gold[tid]={'plan':plan}
    write_json(out/'tasks.json',tasks);write_json(out/'oracle.json',gold)
    write_json(out/'protocol.json',{'version':'v4-sequence-1','train_sources':sources[:4],'validation_sources':sources[4:],
        'shared_template_families':True,'external_test':False,'max_decisions':4,'max_tools':3,
        'parameter_mode':'identical public deterministic bindings for all policies',
        'success':'explicit stop + oracle final answer and table + original input unchanged',
        'reward':'success - 0.05 * tool_calls - 0.01 * decisions',
        'fault':'one simulated transient read failure before first tool; retry allowed',
        'tasks_sha256':digest(out/'tasks.json'),'oracle_sha256':digest(out/'oracle.json')})
    return tasks,gold


class SequenceEnv:
    def __init__(self,task,gold,folder,fault=False,profile=None):
        self.task=task;self.gold=gold;self.folder=Path(folder);self.folder.mkdir(parents=True,exist_ok=True)
        self.profile=profile
        limits=task.get('constraints',{})
        self.max_decisions=int(limits.get('max_steps',4))
        self.max_tool_calls=int(limits.get('max_tool_calls',3))
        self.max_seconds=float(limits.get('max_seconds',120))
        if self.max_decisions<1 or self.max_tool_calls<0 or self.max_seconds<=0:
            raise ValueError('invalid task constraints')
        self.current=ROOT/task['dataset']['uri'];self.initial=digest(self.current)
        if self.initial!=task['dataset']['sha256']:raise ValueError('input hash mismatch')
        self.history=[];self.last={};self.last_hash=None;self.calls=0;self.decisions=0
        self.fault=fault;self.injected=False;self.done=False;self.stopped=False
        self.started=time.perf_counter()

    def observation(self):
        with scope(self.profile,'csv_read'):
            cols,rows=read_table(self.current)
        return {'prompt':self.task['prompt'],'columns':cols,'rows':len(rows),
                'missing_cells':sum(v=='' for r in rows for v in r.values()),
                'history':copy.deepcopy(self.history),
                'remaining_calls':max(0,self.max_tool_calls-self.calls),
                'remaining_decisions':max(0,self.max_decisions-self.decisions),
                'parameter_bindings':{a:params_for(a,self.task) for a in ACTIONS}}

    def step(self,action):
        if self.done:raise RuntimeError('episode ended')
        if time.perf_counter()-self.started>self.max_seconds:
            self.done=True
            return self.observation()
        self.decisions+=1
        if action=='stop':self.done=True;self.stopped=True
        elif action not in self.task['allowed_tools'] or self.calls>=self.max_tool_calls:self.done=True
        else:
            self.calls+=1;before=digest(self.current)
            try:
                if self.fault and not self.injected:
                    self.injected=True
                    raise FileNotFoundError('simulated transient input read failure; retry allowed')
                p=params_for(action,self.task)
                with scope(self.profile,'tool_execute'):
                    result=execute_tool(action,{'uri':str(self.current),'params':p,'artifact_dir':self.folder/f'step_{self.decisions}'})
                with scope(self.profile,'tool_reference_and_verify'):
                    checked=verify(result,expected(self.current,action,p),[{'tool':action,'ok':True}],
                                   {'allowed_tools':ACTIONS,'input_sha256':before,'max_steps':1,'max_tool_calls':1})
                if not checked['passed']:raise ValueError('invalid tool artifact')
                self.last=result;self.last_hash=before
                if action in MUTATING:self.current=Path(result['artifact']['path'])
                self.history.append({'action':action,'ok':True,'answer':result['answer'],
                                     'input_sha256':before,'output_sha256':digest(self.current)})
            except (ValueError,KeyError,OSError,TypeError) as exc:
                self.history.append({'action':action,'ok':False,'error':type(exc).__name__+': '+str(exc)})
        if self.decisions>=self.max_decisions:self.done=True
        return self.observation()

    def result(self):
        if not self.done:raise RuntimeError('terminal scoring only')
        ref=ROOT/self.task['dataset']['uri'];target=None
        for i,action in enumerate(self.gold['plan']):
            with scope(self.profile,'result_reference'):
                target=expected(ref,action,params_for(action,self.task))
            if 'artifact_rows' in target:
                ref=self.folder/f'reference_{i}.csv'
                write_table(ref,target['artifact_columns'],target['artifact_rows'])
        with scope(self.profile,'csv_read'):
            cols,rows=read_table(self.current);refcols,refrows=read_table(ref)
        with scope(self.profile,'result_verify'):
            verified=verify(self.last,target,[{'tool':h['action'],'ok':True} for h in self.history if h['ok']],
                            {'allowed_tools':self.task['allowed_tools'],'input_sha256':self.last_hash,
                             'max_tool_calls':self.max_tool_calls,'max_steps':self.max_decisions})
        passed=bool(self.stopped and verified['passed'] and cols==refcols and _same(rows,refrows)
                    and digest(ROOT/self.task['dataset']['uri'])==self.initial
                    and time.perf_counter()-self.started<=self.max_seconds)
        successful_actions=[h['action'] for h in self.history if h['ok']]
        matched_prefix=0
        for actual,planned in zip(successful_actions,self.gold['plan']):
            if actual!=planned:break
            matched_prefix+=1
        progress=matched_prefix/max(1,len(self.gold['plan']))
        reward_spec=self.task.get('reward',{})
        success_weight=float(reward_spec.get('success',1.0))
        progress_weight=float(reward_spec.get('progress',0.0))
        tool_cost=float(reward_spec.get('tool_call_cost',.05))
        decision_cost=float(reward_spec.get('decision_cost',.01))
        reward=success_weight*float(passed)+progress_weight*progress-tool_cost*self.calls-decision_cost*self.decisions
        return {'passed':passed,'stopped':self.stopped,'tool_calls':self.calls,'decisions':self.decisions,
                'injection_applied':self.injected,'matched_prefix':matched_prefix,'progress':progress,
                'reward':reward,
                'extra_calls':max(0,self.calls-len(self.gold['plan'])-int(self.injected))}
