"""Contextual bandit over tools, conditioned on a frozen DeepSeek suggestion.

The provider's weights are never updated. Only executed training actions receive reward.
"""
import numpy as np
from agent.tools import ACTIONS
from research.features import DIM
from research.policies import Policy


class HybridPolicy(Policy):
    def __init__(self, suggestions, seed=1):
        super().__init__('bandit', seed)
        self.suggestions = suggestions
        self.inv = np.repeat(np.eye(DIM+len(ACTIONS))[None,:,:], len(ACTIONS), axis=0)
        self.b = np.zeros((len(ACTIONS), DIM+len(ACTIONS)))
        self.weights = np.zeros((DIM+len(ACTIONS), len(ACTIONS)))
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
