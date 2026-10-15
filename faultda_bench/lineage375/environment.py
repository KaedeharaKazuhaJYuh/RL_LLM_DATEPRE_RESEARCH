"""A transport-obscured history witness and request-scoped transaction metadata."""
import copy
from contextlib import closing
import json
import sqlite3
from . import SEMANTICS_VERSION
from ..responsibility370.environment import ResponsibilityEnv,observation as prior_observation
from ..responsibility370.contract import CONTRACT as OLD_CONTRACT
from ..trust.policy import public_expected

CONTRACT=copy.deepcopy(OLD_CONTRACT)
CONTRACT['semantics_version']=SEMANTICS_VERSION
CONTRACT['receipt_lookup']='Within this controlled fixture, request ids are unique across all publish attempts and initial is reserved. Read the durable requests table in the same database transaction domain as the reports ledger: committed plus revision only. No numeric truth, fault mode or private evaluator is returned. Reused/missing publication ids cannot be certified by this witness contract.'

class WitnessEnv(ResponsibilityEnv):
    def __init__(self,task,folder,mode):
        if mode not in ('bad_never_committed','bad_committed'):raise ValueError('mode')
        self._witness_mode=mode;self._publish_attempts=0
        super().__init__(task,folder,initial_numeric_fault=True)
        self.budget=6
    def step(self,action,params=None):
        if self.terminal is not None:raise RuntimeError('episode ended')
        if action=='receipt_lookup':
            params={} if params is None else params
            self.cost['decisions']+=1;self.cost['checks']+=1
            if self.cost['decisions']>16 or self.cost['checks']>self.budget:
                self.terminal='budget_exceeded';r={'ok':False,'error':'budget exceeded; no effect applied'}
            else:
                request_id=params.get('request_id')
                matches=[h for h in self.history if h['action']=='publish' and h['params'].get('request_id')==request_id]
                if set(params)!={'request_id'} or type(request_id) is not str or not 0<len(request_id)<=80 or request_id=='initial' or len(matches)!=1:
                    r={'ok':False,'error':'receipt lookup requires one unique prior publication request id'}
                else:
                    with closing(sqlite3.connect(self.db)) as c:row=c.execute('SELECT revision FROM requests WHERE id=?',(request_id,)).fetchone()
                    r={'ok':True,'request_id':request_id,'committed':row is not None,'revision':row[0] if row else None}
            self.history.append({'action':action,'params':copy.deepcopy(params),'response':r})
            self.cost['response_bytes']+=len(json.dumps(r,ensure_ascii=False,allow_nan=False).encode())
            return self.observation()
        obscure=action=='publish' and self._publish_attempts<2
        if obscure:
            n=self._publish_attempts
            self._before_pending=self._witness_mode=='bad_never_committed' and n==0
            self.repair_ack_loss=not self._before_pending
        result=super().step(action,params)
        if action=='publish':self._publish_attempts+=1
        if obscure:
            # Transport may lose a successful acknowledgement or a rejected CAS response.
            old=self.history[-1]['response'];new={'ok':False,'error':'timeout'}
            encode=lambda x:json.dumps(x,ensure_ascii=False,allow_nan=False).encode()
            self.cost['response_bytes']+=len(encode(new))-len(encode(old))
            self.history[-1]['response']=new;self._before_pending=False;self.repair_ack_loss=False
        return self.observation()

def observation(env):
    obs=prior_observation(env);obs['responsibility_contract']=copy.deepcopy(CONTRACT)
    obs['responsibility_context']['semantics_version']=SEMANTICS_VERSION
    obs['tools']['receipt_lookup']='Read one unique prior publish request id: params request_id. Returns committed/revision from durable transaction metadata, no report values. Costs one check.'
    obs['reliability_contract']['limits']+=' In this witness, the first two publish replies can be lost, including a rejected CAS response. Request ids are globally unique for this fixture; receipt_lookup is a trusted, complete, durable read of that same ledger database.'
    return obs

def prepare(task,folder,mode):
    env=WitnessEnv(task,folder,mode)
    for action in ('inspect','inputs','catalog'):env.step(action)
    params=public_expected(observation(env))[0]
    env.step('stage',{**params,'closed':'both'})
    env.step('publish',{'stage_id':'1','request_id':'witness-bad','expected_revision':1,'mode':'replace'})
    env.step('stage',params)
    env.step('publish',{'stage_id':'2','request_id':'witness-good','expected_revision':1,'mode':'replace'})
    env.step('status')
    revision=env.history[-1]['response']['revision']
    env.step('publish',{'stage_id':'2','request_id':'witness-repair','expected_revision':revision,'mode':'replace'})
    env.step('inspect')
    env.model_start=len(env.history)
    return env
