import numpy as np
from agent.tools import ACTIONS
from research.features import DIM

KEYWORDS=[('profile_schema',('字段','行列数')),('profile_missingness',('缺失率',)),('count_categories',('频数','类别计数')),('deduplicate',('重复行',)),('describe_numeric',('基本统计量',)),('normalize_dates',('日期格式',)),('clip_outliers',('异常值',)),('fill_missing',('填补','填充')),('normalize_categories',('类别拼写',)),('aggregate',('总额','汇总')),('correlate',('相关系数',)),('rolling_mean',('移动平均',))]
class Policy:
    def __init__(self,mode='rule',seed=1,alpha=.5,data_only=False):
        self.mode=mode;self.rng=np.random.default_rng(seed);self.alpha=alpha;self.data_only=data_only
        self.last_usage={};self.last_choice=None;self.llm=None
        if mode=='llm':
            from agent.llm import LLMClient
            self.llm=LLMClient()
        self.inv=np.repeat(np.eye(DIM)[None,:,:],len(ACTIONS),axis=0);self.b=np.zeros((len(ACTIONS),DIM));self.weights=np.zeros((DIM,len(ACTIONS)))
    def select(self,task,x,allowed=None,training=False,state=None):
        allowed=allowed or ACTIONS
        if self.mode=='llm':
            self.last_choice=self.llm.choose(task,state,allowed);self.last_usage=self.llm.last_usage
            return self.last_choice['action'],None  # Provider does not expose action propensity.
        if self.mode=='rule':
            a=next((a for a,words in KEYWORDS if any(w in task['prompt'] for w in words)),'profile_schema')
            return (a if a in allowed else allowed[0]),1.0
        if self.mode in ('random','mask_only'):
            return str(self.rng.choice(allowed)),1/len(allowed)
        if self.mode=='majority':return 'profile_schema',1.0
        if self.mode=='supervised':scores=x@self.weights
        else:
            ix=np.einsum('aij,j->ai',self.inv,x);scores=np.sum(ix*self.b,axis=1)
            if training:scores+=self.alpha*np.sqrt(np.maximum(ix@x,0))
        ids=[ACTIONS.index(a) for a in allowed];best=max(scores[i] for i in ids);ties=[i for i in ids if np.isclose(scores[i],best,rtol=0,atol=1e-12)]
        choice=int(self.rng.choice(ties)) if training else ties[0]
        return ACTIONS[choice],1/len(ties) if training else 1.0
    def update(self,action,x,reward):
        i=ACTIONS.index(action);v=self.inv[i]@x;self.inv[i]-=np.outer(v,v)/(1+x@v);self.b[i]+=reward*x
    def fit_supervised(self,xs,actions):
        X=np.asarray(xs);Y=np.eye(len(ACTIONS))[[ACTIONS.index(a) for a in actions]]
        self.weights=np.linalg.solve(X.T@X+np.eye(DIM)*.1,X.T@Y)
    def save(self,path):np.savez(path,inv=self.inv,b=self.b,weights=self.weights)
    def load(self,path):
        with np.load(path,allow_pickle=False) as data:
            self.inv=data['inv'].copy();self.b=data['b'].copy();self.weights=data['weights'].copy()
