import numpy as np
from .bandit import LinUCBBandit
from .router import AgentState, rule_router

class Policy:
    def __init__(self, actions, dim=10, mode="rule", alpha=1.0, seed=None):
        self.mode=mode; self.bandit=LinUCBBandit(dim, actions, alpha, np.random.default_rng(seed))
    def select(self, state):
        if self.mode == "rule":
            return rule_router(AgentState(missing_rate=state.features[2], numeric_columns=int(state.features[3]), remaining_calls=state.remaining_calls))
        return self.bandit.select(np.asarray(state.features, dtype=float))
    def update(self, action, state, reward):
        if self.mode == "bandit":
            features = state if isinstance(state, (list, tuple, np.ndarray)) else state.features
            self.bandit.update(action, np.asarray(features, dtype=float), reward)

