"""Supervised softmax initialization and on-policy episodic REINFORCE."""
import hashlib
import numpy as np
from agent.tools import ACTIONS

CHOICES=ACTIONS+['stop']
DIM=4*129+len(ACTIONS)+3


def features(observation):
    x=np.zeros(DIM);history=observation['history']
    stage=min(3,sum(h['ok'] for h in history))
    text=''.join(observation['prompt'].lower().split());z=np.zeros(128)
    for n in (2,3):
        for i in range(max(0,len(text)-n+1)):
            k=int.from_bytes(hashlib.sha256(text[i:i+n].encode()).digest()[:4],'little')%128
            z[k]+=1
    z/=max(1,np.linalg.norm(z));offset=129*stage
    x[offset]=1;x[offset+1:offset+129]=z
    for h in history:
        if h['ok']:x[516+ACTIONS.index(h['action'])]+=1
    x[-3]=bool(history and not history[-1]['ok'])
    x[-2]=observation['remaining_calls']/3;x[-1]=observation['remaining_decisions']/4
    return x


class SequencePolicy:
    def __init__(self,seed=1):
        self.rng=np.random.default_rng(seed);self.weights=self.rng.normal(0,.005,(DIM,len(CHOICES)))

    def probs(self,x):
        z=x@self.weights;z-=z.max();p=np.exp(z);return p/p.sum()

    def select(self,obs,training=False):
        x=features(obs);p=self.probs(x)
        i=int(self.rng.choice(len(CHOICES),p=p)) if training else int(np.argmax(p))
        return CHOICES[i],(x,i,p)

    def fit(self,demos,epochs=160):
        X=np.array([features(d['observation']) for d in demos]);Y=np.eye(len(CHOICES))[[CHOICES.index(d['action']) for d in demos]]
        for _ in range(epochs):
            logits=X@self.weights;logits-=logits.max(axis=1,keepdims=True)
            p=np.exp(logits);p/=p.sum(axis=1,keepdims=True)
            self.weights+=.4*(X.T@(Y-p)/len(X)-.0001*self.weights)

    def reinforce(self,trajectory,total_reward,baseline,lr=.025):
        # Undiscounted episodic return; actions were sampled from the current policy.
        advantage=total_reward-baseline;gradient=np.zeros_like(self.weights)
        for x,i,p in trajectory:
            target=np.zeros(len(CHOICES));target[i]=1
            gradient+=np.outer(x,target-p)*advantage
        self.weights+=lr*gradient

    def fingerprint(self):return hashlib.sha256(self.weights.tobytes()).hexdigest()

    def batch_reinforce(self, episodes, baselines, demos, reference, lr=.1,
                        bc_weight=.2, kl_weight=.5, max_kl=.01):
        """One on-policy batch update, with optional training-state safeguards.

        Baselines must precede this batch. KL is reference||candidate on demos;
        the step bound is old||candidate on demos and sampled training states.
        This is regularized REINFORCE, not PPO.
        """
        gradient=np.zeros_like(self.weights)
        for (trajectory,reward),baseline in zip(episodes,baselines,strict=True):
            for x,i,p in trajectory:
                target=np.zeros(len(CHOICES));target[i]=1
                gradient+=np.outer(x,target-p)*(reward-baseline)/len(episodes)
        X=np.array([features(d['observation']) for d in demos])
        P=np.array([self.probs(x) for x in X])
        Q=np.array([reference.probs(x) for x in X])
        Y=np.eye(len(CHOICES))[[CHOICES.index(d['action']) for d in demos]]
        pg_norm=float(np.linalg.norm(gradient))
        gradient+=X.T@(bc_weight*(Y-P)+kl_weight*(Q-P))/len(X)
        norm=float(np.linalg.norm(gradient));gradient/=max(1.,norm)
        checks=np.vstack([X]+[np.array([s[0] for s in trajectory]) for trajectory,_ in episodes])
        old=self.weights.copy();oldp=np.array([self.probs(x) for x in checks])
        scale=1.;accepted=False;kl=0.
        for _ in range(20):
            self.weights=old+lr*scale*gradient
            newp=np.array([self.probs(x) for x in checks])
            kl=float(np.max(np.sum(oldp*np.log(np.maximum(oldp,1e-15)/np.maximum(newp,1e-15)),axis=1)))
            if np.isfinite(kl) and kl<=max_kl:accepted=True;break
            scale*=.5
        if not accepted:self.weights=old
        return {'pg_norm':pg_norm,'gradient_norm':norm,'accepted':accepted,
                'step_scale':scale,'max_training_state_step_kl':kl}
