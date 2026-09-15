"""Contextual bandit over tools, conditioned on a frozen DeepSeek suggestion.

The provider's weights are never updated. Only executed training actions receive reward.
"""
import numpy as np
from agent.tools import ACTIONS
from research.features import DIM
from research.policies import Policy


class HybridPolicy(Policy):
    def __init__(self, suggestions, seed=1, warm_start=False):
        super().__init__('bandit', seed)
        self.suggestions = suggestions
        self.inv = np.repeat(np.eye(DIM+len(ACTIONS))[None,:,:], len(ACTIONS), axis=0)
        self.b = np.zeros((len(ACTIONS), DIM+len(ACTIONS)))
        self.weights = np.zeros((DIM+len(ACTIONS), len(ACTIONS)))
        if warm_start:
            # Fixed prior: initially prefer the suggested action, without treating it as verified reward.
            # Subsequent real rewards can override this preference. No oracle labels are read here.
            for i in range(len(ACTIONS)):
                self.b[i, DIM+i] = 1.0
        self.pending = None

    def select(self, task, x, allowed=None, training=False, state=None):
        hint = self.suggestions[task['task_id']]
        augmented = np.concatenate((x, np.eye(len(ACTIONS))[ACTIONS.index(hint)]))
        # ID is only a cache lookup; it never enters the learner's features.
        self.pending = augmented if training else None
        return super().select(task, augmented, allowed, training, state)

    def update(self, action, x, reward):
        if self.pending is None:
            raise RuntimeError('training selection required before update')
        super().update(action, self.pending, reward)
        self.pending = None
